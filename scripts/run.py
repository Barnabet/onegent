"""CLI: python scripts/run.py --pack <pack> "<user message>" """

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Make repo importable when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator import supervisor  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", required=True, help="Pack name (filename in packs/ without .yaml)")
    ap.add_argument("--user", default="local", help="User id for audit log")
    ap.add_argument("--verbose", action="store_true", help="Print every event")
    ap.add_argument("message", help="The user message")
    args = ap.parse_args()

    def on_event(ev: dict) -> None:
        if args.verbose:
            print(f"[event] {json.dumps(ev, default=str)[:400]}")

    result = supervisor.run(
        pack_name=args.pack,
        user_message=args.message,
        user_id=args.user,
        on_event=on_event,
        timeout=120.0,
    )

    print("=" * 60)
    print(f"run_id: {result.run_id}")
    if result.error:
        print(f"ERROR: {result.error}")
        return 1
    print(f"stats: {result.stats}")
    print("-" * 60)
    print(result.final_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
