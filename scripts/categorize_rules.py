#!/usr/bin/env python3
"""Split a monolithic GEMINI.md into categorized Markdown knowledge files."""

from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class CategorySpec:
    name: str
    hosts: tuple[str, ...] = ()
    project_files: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    match_terms: tuple[str, ...] = ()


CATEGORY_SPECS: tuple[CategorySpec, ...] = (
    CategorySpec(
        name="arch-aur",
        project_files=("PKGBUILD", ".SRCINFO", "install.sh"),
        keywords=("paru", "pacman", "aur", "pkgbuild", "srcinfo", "makepkg", "man1"),
        match_terms=("paru", "pkgbuild", ".srcinfo", "aur", "makepkg", "man1"),
    ),
    CategorySpec(
        name="git-repos",
        project_files=(".git", "README.md", ".github/workflows"),
        keywords=("github", "repo", "readme", "workflow", "codeql", "sarif", "fork", "license", "workflows"),
        match_terms=("autonomous repository", "agentic public repo", "foreign repository", "workflows", "manual installation", "pre-existing tooling", "project directory structure", "codeql", "descriptive commits"),
    ),
    CategorySpec(
        name="saas-billing",
        project_files=("package.json", "next.config.js", "next.config.mjs", "vercel.json", "supabase"),
        keywords=("stripe", "polar", "lemon squeezy", "supabase", "vercel", "nextjs", "monetization", "sponsorship", "checkout", "webhook"),
        match_terms=("next.js", "supabase", "lemon squeezy", "vercel", "monetization", "design_system_monetization"),
    ),
    CategorySpec(
        name="jules-automation",
        project_files=(".jules", ".Jules"),
        keywords=("jules", "jules-vanager", "jules-listener", "jules-hud", "jules-tui", "pr"),
        match_terms=("jules task offloading", "jules_manager", "jules-vanager"),
    ),
    CategorySpec(
        name="desktop-theming",
        project_files=(".desktop", "app.asar"),
        keywords=("hyprland", "caelestia", "desktop", "icon", "theme", "asar", "pkill", "vlfstatus", "reprosight", "ui", "gui"),
        match_terms=("visual & runtime refresh", "desktop entry", "icon theme", "reprosight", "vlfstatus", "client-side & gui"),
    ),
    CategorySpec(
        name="spreadsheets",
        project_files=("*.csv", "*.xlsx", "*.ods"),
        keywords=("spreadsheet", "sheet", "gsheets", "csv", "xlsx", "excel", "formula"),
        match_terms=("spreadsheet", "sheet automation"),
    ),
    CategorySpec(
        name="cli-security",
        project_files=("mcp_config.json",),
        keywords=("bash", "tty", "secret", "pat", "token", "chmod", "rsync", "mcp", "chromium", "chrome", "arg_max", "passphrase"),
        match_terms=("script security", "secret isolation", "sensitive input", "bash script robustness", "cli argument limits", "browser-agnostic", "duplicate process", "mcp configuration", "large file copy", "script idempotency", "multi-shell"),
    ),
    CategorySpec(
        name="learning-meta",
        keywords=("learn", "synclearn", "compliance", "audit", "gemini.md", "budget"),
        match_terms=("continuous learning", "rule compaction", "compliance", "planning mode", "deterministic scripted calculation"),
    ),
)

CORE_KEEP_TERMS: tuple[str, ...] = (
    "autonomous execution & anti-delegation",
    "markdown file link url encoding",
    "private configuration vault synchronization",
    "developer persona & single-author",
    "clean copyable text formatting",
)


def classify_bullet(block: str) -> str:
    lower = block.lower()
    header = block.splitlines()[0].lower() if block.splitlines() else ""
    if any(term in header for term in CORE_KEEP_TERMS):
        return "core"
    for spec in CATEGORY_SPECS:
        if any(term in header or term in lower[:300] for term in spec.match_terms):
            return spec.name
    return "general"


def parse_gemini_md(text: str) -> tuple[list[str], dict[str, list[str]], dict[str, str]]:
    """Return (core_blocks, categorized_bullets, host_scopes)."""
    core_blocks: list[str] = []
    categories: dict[str, list[str]] = {}
    host_scopes: dict[str, str] = {}

    # Split out Machine-Specific section if present
    machine_split = re.split(r"(?m)^## .*Machine-Specific.*$", text, maxsplit=1)
    universal_part = machine_split[0]
    machine_part = machine_split[1] if len(machine_split) > 1 else ""

    # Parse top-level bullets in universal_part
    bullets = re.findall(r"(?ms)^- \*\*[^*\n]+\*\*:.*?(?=^- \*\*|^---|\Z)", universal_part)
    for bullet in bullets:
        cat = classify_bullet(bullet)
        if cat == "core":
            core_blocks.append(bullet.strip())
        else:
            categories.setdefault(cat, []).append(bullet.strip())

    # Parse ### Scope: Host <name> blocks
    if machine_part.strip():
        scopes = re.split(r"(?m)^(?=### Scope:\s*Host\s+)", machine_part.strip())
        for scope in scopes:
            scope = scope.strip()
            if not scope:
                continue
            m = re.match(r"### Scope:\s*Host\s+`?([A-Za-z0-9._-]+)`?", scope)
            if m:
                host = m.group(1).lower()
                host_scopes[host] = scope
            else:
                categories.setdefault("general", []).append(scope)

    return core_blocks, categories, host_scopes


def render_category_file(
    category: str,
    body_blocks: list[str],
    spec: CategorySpec | None = None,
    host: str | None = None,
) -> str:
    hosts = [host] if host else list(spec.hosts if spec else ())
    project_files = list(spec.project_files if spec else ())
    keywords = list(spec.keywords if spec else (category,))
    fm_lines = [
        "---",
        f"category: {category}",
        f"hosts: [{', '.join(hosts)}]",
        f"project_files: [{', '.join(project_files)}]",
        f"keywords: [{', '.join(keywords)}]",
        "---",
        "",
        f"# Knowledge Base: {category}",
        "",
    ]
    return "\n".join(fm_lines) + "\n\n".join(body_blocks).strip() + "\n"


def render_slim_gemini(core_blocks: list[str], category_names: list[str]) -> str:
    index_lines = "\n".join(f"- `{name}` -> `knowledge/{name}.md`" for name in sorted(category_names))
    return (
        "# Core Agent Rules\n\n"
        "Universal every-turn invariants. Domain, host, and workflow rules live in `knowledge/*.md` "
        "and are injected automatically by `kb_router.py`.\n\n"
        + "\n\n".join(core_blocks)
        + "\n\n## Knowledge Base Lookup Fallback\n\n"
        "- If a task pivots to a domain not yet in context, read the matching `knowledge/<category>.md` "
        "or run `python3 ~/.gemini/config/scripts/kb_router.py --query \"<topic>\"`.\n"
        "- For Agensi on-demand skills (`code-reviewer`, `env-doctor`, `skill-creator`, "
        "`pr-description-writer`, `prompt-engineer`, `humanize-writing`), see `knowledge/agensi-skills.md` "
        "and call `get_skill(slug)`.\n\n"
        "## Category Index\n\n"
        + index_lines
        + "\n"
    )


def categorize_file(
    source: Path,
    out_dir: Path,
    apply: bool = False,
) -> dict[str, int]:
    text = source.read_text(encoding="utf-8")
    core_blocks, categories, host_scopes = parse_gemini_md(text)
    spec_map = {s.name: s for s in CATEGORY_SPECS}

    outputs: dict[Path, str] = {}
    kb_dir = out_dir / "knowledge"
    all_cat_names: list[str] = []

    for cat, blocks in sorted(categories.items()):
        all_cat_names.append(cat)
        outputs[kb_dir / f"{cat}.md"] = render_category_file(cat, blocks, spec=spec_map.get(cat))

    for host, scope_text in sorted(host_scopes.items()):
        cat = f"host-{host}"
        all_cat_names.append(cat)
        outputs[kb_dir / f"{cat}.md"] = render_category_file(cat, [scope_text], host=host)

    slim_text = render_slim_gemini(core_blocks, all_cat_names)
    outputs[out_dir / "GEMINI.slim.md" if not apply else out_dir / "GEMINI.md"] = slim_text

    if apply:
        kb_dir.mkdir(parents=True, exist_ok=True)
        for path, content in outputs.items():
            path.write_text(content, encoding="utf-8")

    return {
        "source_bytes": len(text.encode("utf-8")),
        "slim_bytes": len(slim_text.encode("utf-8")),
        "category_count": len(all_cat_names),
        **{p.name: len(c.encode("utf-8")) for p, c in outputs.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Categorize GEMINI.md into knowledge/*.md files.")
    parser.add_argument("--source", type=Path, default=Path.home() / ".gemini/config/GEMINI.md")
    parser.add_argument("--out-dir", type=Path, default=Path.home() / ".gemini/config")
    parser.add_argument("--apply", action="store_true", help="Write knowledge/*.md and replace GEMINI.md")
    args = parser.parse_args()

    stats = categorize_file(args.source, args.out_dir, apply=args.apply)
    mode = "APPLIED" if args.apply else "DRY-RUN"
    print(f"[{mode}] source={stats['source_bytes']} B -> slim={stats['slim_bytes']} B across {stats['category_count']} categories")
    for k, v in stats.items():
        if k not in ("source_bytes", "slim_bytes", "category_count"):
            print(f"  {k}: {v} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
