#!/usr/bin/env python3
"""Deterministic SQLite FTS5 + host/workspace router for categorized knowledge/*.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KB_DIR = Path.home() / ".gemini/config/knowledge"
DEFAULT_DB_PATH = Path.home() / ".cache/agv-syncengine/kb.sqlite"


@dataclass(frozen=True)
class KnowledgeDoc:
    category: str
    path: Path
    mtime_ns: int
    hosts: tuple[str, ...]
    project_files: tuple[str, ...]
    keywords: tuple[str, ...]
    body: str


def _parse_list_field(raw: str) -> tuple[str, ...]:
    inner = raw.strip().strip("[]")
    if not inner:
        return ()
    return tuple(item.strip().strip("'\"") for item in inner.split(",") if item.strip())


def parse_knowledge_file(path: Path) -> KnowledgeDoc:
    text = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    meta[k.strip()] = v.strip()
            body = parts[2].strip()
    return KnowledgeDoc(
        category=meta.get("category", path.stem),
        path=path,
        mtime_ns=path.stat().st_mtime_ns,
        hosts=tuple(h.lower() for h in _parse_list_field(meta.get("hosts", ""))),
        project_files=_parse_list_field(meta.get("project_files", "")),
        keywords=tuple(k.lower() for k in _parse_list_field(meta.get("keywords", ""))),
        body=body,
    )


def ensure_index(kb_dir: Path, db_path: Path, force: bool = False) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        "CREATE TABLE IF NOT EXISTS meta (category TEXT PRIMARY KEY, path TEXT, mtime_ns INTEGER, hosts TEXT, project_files TEXT, keywords TEXT, body TEXT)"
    )
    conn.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(category, keywords, body, tokenize='porter unicode61')"
    )

    files = sorted(kb_dir.glob("*.md")) if kb_dir.exists() else []
    existing = {row[0]: row[1] for row in conn.execute("SELECT category, mtime_ns FROM meta")}
    docs = [parse_knowledge_file(f) for f in files]
    current_map = {d.category: d.mtime_ns for d in docs}

    if force or existing != current_map:
        conn.execute("DELETE FROM meta")
        conn.execute("DELETE FROM kb_fts")
        for d in docs:
            conn.execute(
                "INSERT INTO meta VALUES (?, ?, ?, ?, ?, ?, ?)",
                (d.category, str(d.path), d.mtime_ns, ",".join(d.hosts), ",".join(d.project_files), ",".join(d.keywords), d.body),
            )
            conn.execute(
                "INSERT INTO kb_fts VALUES (?, ?, ?)",
                (d.category, " ".join(d.keywords), d.body),
            )
        conn.commit()
    return conn


def _tokenize_fts_query(query: str) -> str:
    tokens = re.findall(r"[A-Za-z0-9_]{2,}", query.lower())
    if not tokens:
        return ""
    # Deduplicate preserving order, join with OR for broad recall ranked by BM25
    seen: list[str] = []
    for tok in tokens[:24]:
        if tok not in seen:
            seen.append(tok)
    return " OR ".join(f'"{t}"' for t in seen)


def route_categories(
    kb_dir: Path,
    db_path: Path,
    query: str = "",
    workspaces: list[str] | None = None,
    hostname: str | None = None,
    max_chars: int = 8000,
    top_k: int = 2,
) -> list[tuple[str, float, str]]:
    """Return [(category, score, excerpt)] capped by max_chars."""
    if not kb_dir.exists():
        return []

    conn = ensure_index(kb_dir, db_path)
    host = (hostname or socket.gethostname()).lower()
    ws_paths = [Path(w) for w in (workspaces or []) if Path(w).exists()]

    scores: dict[str, float] = {}
    bodies: dict[str, str] = {}

    for cat, hosts_csv, pfiles_csv, kw_csv, body in conn.execute(
        "SELECT category, hosts, project_files, keywords, body FROM meta"
    ):
        bodies[cat] = body
        score = 0.0
        hosts = [h for h in hosts_csv.split(",") if h]
        if host in hosts:
            score += 5.0
        elif hosts:
            # Explicit host-scoped file for a different host: never auto-inject unless queried
            score -= 10.0

        pfiles = [p for p in pfiles_csv.split(",") if p]
        for ws in ws_paths:
            for marker in pfiles:
                if "*" in marker:
                    if any(ws.glob(marker)):
                        score += 3.0
                        break
                elif (ws / marker).exists():
                    score += 3.0
                    break

        q_lower = query.lower()
        for kw in kw_csv.split(","):
            if kw and kw in q_lower:
                score += 2.0

        scores[cat] = score

    fts_q = _tokenize_fts_query(query)
    if fts_q:
        try:
            for cat, bm25_rank in conn.execute(
                "SELECT category, bm25(kb_fts, 2.0, 1.5, 1.0) FROM kb_fts WHERE kb_fts MATCH ? ORDER BY bm25(kb_fts)",
                (fts_q,),
            ):
                # bm25() in SQLite FTS5 is negative (more negative = better match)
                scores[cat] = scores.get(cat, 0.0) + max(0.0, -bm25_rank)
        except sqlite3.OperationalError:
            pass

    conn.close()

    ranked = sorted(
        ((cat, sc) for cat, sc in scores.items() if sc > 0.5),
        key=lambda item: item[1],
        reverse=True,
    )[:top_k]

    results: list[tuple[str, float, str]] = []
    used = 0
    for cat, sc in ranked:
        body = bodies.get(cat, "")
        remaining = max_chars - used
        if remaining <= 200:
            break
        snippet = body[:remaining]
        used += len(snippet)
        results.append((cat, round(sc, 2), snippet))
    return results


def run_hook(kb_dir: Path, db_path: Path, max_chars: int) -> None:
    try:
        ctx = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print(json.dumps({}))
        return

    query = ctx.get("prompt") or ctx.get("userMessage") or ""
    workspaces = ctx.get("workspacePaths") or []
    hits = route_categories(kb_dir, db_path, query=query, workspaces=workspaces, max_chars=max_chars)
    if not hits:
        print(json.dumps({}))
        return

    blocks = [f"### [{cat}] (score={sc})\n{txt}" for cat, sc, txt in hits]
    msg = "[KB Router: matched categories]\n\n" + "\n\n---\n\n".join(blocks)
    print(json.dumps({"injectSteps": [{"ephemeralMessage": msg}]}))


def main() -> int:
    parser = argparse.ArgumentParser(description="Route prompt/host/workspace signals to knowledge/*.md.")
    parser.add_argument("--kb-dir", type=Path, default=DEFAULT_KB_DIR)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--query", default="", help="Prompt or topic to look up")
    parser.add_argument("--workspace", action="append", default=[], help="Workspace path(s)")
    parser.add_argument("--max-chars", type=int, default=8000)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild FTS5 index")
    parser.add_argument("--hook", action="store_true", help="Run as Antigravity PreInvocation hook")
    args = parser.parse_args()

    if args.rebuild:
        conn = ensure_index(args.kb_dir, args.db, force=True)
        conn.close()
        print(f"Rebuilt index at {args.db}")
        return 0

    if args.hook:
        run_hook(args.kb_dir, args.db, args.max_chars)
        return 0

    hits = route_categories(
        args.kb_dir,
        args.db,
        query=args.query,
        workspaces=args.workspace or [os.getcwd()],
        max_chars=args.max_chars,
        top_k=args.top_k,
    )
    for cat, sc, txt in hits:
        print(f"=== {cat} (score={sc}, {len(txt)} chars) ===")
        print(txt[:400] + ("..." if len(txt) > 400 else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
