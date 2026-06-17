from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_PATHS = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "CHANGELOG.md",
    ROOT / "ROADMAP.md",
]
MARKDOWN_PATHS.extend(sorted((ROOT / "docs").rglob("*.md")))
MARKDOWN_PATHS.extend(sorted((ROOT / "examples").rglob("*.md")))
MARKDOWN_PATHS.extend(sorted((ROOT / "validation").rglob("*.md")))
MARKDOWN_PATHS.extend(sorted((ROOT / "templates").rglob("*.md")))
MARKDOWN_PATHS.extend(sorted((ROOT / "assets").rglob("*.md")))

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    missing: list[str] = []
    for path in MARKDOWN_PATHS:
        text = path.read_text(encoding="utf-8")
        for raw_target in LINK_PATTERN.findall(text):
            if raw_target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target = raw_target.split("#", 1)[0]
            if not target or raw_target.startswith("/"):
                continue
            resolved = (path.parent / target).resolve()
            if not resolved.exists():
                missing.append(f"{path.relative_to(ROOT)} -> {raw_target}")

    if missing:
        for item in missing:
            print(f"MISSING {item}", file=sys.stderr)
        return 1

    print("All workspace markdown links resolved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
