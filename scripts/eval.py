"""CLI: python scripts/eval.py [--pack hello] [--case hello_smoke] [--no-judge]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evals import case as case_mod  # noqa: E402
from evals import runner, report  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack", help="Only run cases for this pack")
    ap.add_argument("--case", help="Only run the case with this id")
    ap.add_argument("--no-judge", action="store_true", help="Skip LLM-judge assertions")
    ap.add_argument("--no-write", action="store_true", help="Don't write results JSONL")
    args = ap.parse_args()

    cases = case_mod.discover_cases(pack=args.pack, case_id=args.case)
    if not cases:
        print("No cases matched.")
        return 1

    print(f"Running {len(cases)} case(s){' (judge disabled)' if args.no_judge else ''}...\n")

    suite = runner.run_suite(
        cases,
        use_judge=not args.no_judge,
        on_case_done=report.print_case_result,
    )

    print()
    report.print_summary(suite)

    if not args.no_write:
        path = report.write_results_jsonl(suite)
        print(f"Wrote results to {path}")

    return 0 if suite.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
