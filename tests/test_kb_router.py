from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import categorize_rules  # noqa: E402
import kb_router  # noqa: E402


def test_categorize_and_route(tmp_path: Path) -> None:
    sample_gemini = tmp_path / "GEMINI.md"
    sample_gemini.write_text(
        "## Universal Preferences\n\n"
        "- **Autonomous Execution & Anti-Delegation Invariant**: Do it yourself.\n\n"
        "- **Package Management**: Always use `paru` and update `PKGBUILD` and `.SRCINFO`.\n\n"
        "- **Lemon Squeezy Webhook Secret Limit**: Max 40 chars on Stripe or Lemon Squeezy.\n\n"
        "## Machine-Specific Environment Scopes\n\n"
        "### Scope: Host `Vinux`\n"
        "- **Compositor**: Hyprland on Vinux.\n\n"
        "### Scope: Host `Laptop`\n"
        "- **Battery**: TLP on Laptop.\n",
        encoding="utf-8",
    )

    stats = categorize_rules.categorize_file(sample_gemini, tmp_path, apply=True)
    assert stats["slim_bytes"] > 0
    kb_dir = tmp_path / "knowledge"
    assert (kb_dir / "arch-aur.md").exists()
    assert (kb_dir / "saas-billing.md").exists()
    assert (kb_dir / "host-vinux.md").exists()
    assert (kb_dir / "host-laptop.md").exists()

    ws = tmp_path / "pkg_ws"
    ws.mkdir()
    (ws / "PKGBUILD").write_text("pkgname=demo\n", encoding="utf-8")

    db_path = tmp_path / "kb.sqlite"
    hits = kb_router.route_categories(
        kb_dir,
        db_path,
        query="update PKGBUILD and paru",
        workspaces=[str(ws)],
        hostname="Vinux",
        max_chars=5000,
        top_k=3,
    )
    cats = [c for c, _, _ in hits]
    assert "arch-aur" in cats
    assert "host-vinux" in cats
    assert "host-laptop" not in cats


def test_max_chars_cap_and_hook(tmp_path: Path, monkeypatch) -> None:
    kb_dir = tmp_path / "knowledge"
    kb_dir.mkdir()
    (kb_dir / "saas-billing.md").write_text(
        "---\ncategory: saas-billing\nhosts: []\nproject_files: [package.json]\nkeywords: [stripe, webhook]\n---\n\n"
        + ("stripe webhook rule. " * 200),
        encoding="utf-8",
    )
    db_path = tmp_path / "kb.sqlite"
    hits = kb_router.route_categories(kb_dir, db_path, query="stripe webhook", max_chars=400, top_k=2)
    assert len(hits) == 1
    assert len(hits[0][2]) <= 400

    monkeypatch.setattr(sys, "stdin", StringIO(json.dumps({"prompt": "fix stripe webhook"})))
    buf = StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    kb_router.run_hook(kb_dir, db_path, max_chars=400)
    out = json.loads(buf.getvalue())
    assert "injectSteps" in out
    assert "saas-billing" in out["injectSteps"][0]["ephemeralMessage"]
