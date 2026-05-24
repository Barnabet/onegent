"""
CI check + writer for docs/tool-catalog.md and docs/skill-catalog.md.

Usage:
  python scripts/check_catalog.py            # check (fails if stale)
  python scripts/check_catalog.py --write    # regenerate the docs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime import catalog_gen  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write the catalog files instead of checking")
    args = ap.parse_args()

    root = catalog_gen.repo_root()
    targets = {
        root / "docs" / "tool-catalog.md": catalog_gen.render_tool_catalog(),
        root / "docs" / "skill-catalog.md": catalog_gen.render_skill_catalog(),
    }

    if args.write:
        for path, content in targets.items():
            path.write_text(content, encoding="utf-8")
            print(f"wrote {path.relative_to(root)}")
        return 0

    stale = []
    for path, content in targets.items():
        current = path.read_text(encoding="utf-8") if path.is_file() else ""
        if current.strip() != content.strip():
            stale.append(path.relative_to(root))

    if stale:
        print("Catalog out of date. Run: python scripts/check_catalog.py --write")
        for s in stale:
            print(f"  - {s}")
        return 1

    print("Catalogs are up to date.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
