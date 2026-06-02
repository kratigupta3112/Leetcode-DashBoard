"""CLI entrypoint for salary sync."""

from __future__ import annotations

import argparse
import asyncio

from salarytracker.config import Settings
from salarytracker.interview_pipeline import run_interview_sync
from salarytracker.pipeline import export_dashboard, parse_all, run_sync


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync LeetCode dashboard data")
    parser.add_argument(
        "--max-posts",
        type=int,
        default=300,
        help="Maximum number of forum posts to fetch from LeetCode",
    )
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Skip fetch; re-parse existing posts.jsonl",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Only rebuild dashboard_data.json from parsed posts",
    )
    parser.add_argument(
        "command",
        nargs="?",
        default="comp",
        choices=["comp", "interview-sync"],
        help="comp = compensation sync (default), interview-sync = interview experiences",
    )
    args = parser.parse_args()
    settings = Settings.from_env()

    if args.command == "interview-sync":
        asyncio.run(run_interview_sync(max_posts=args.max_posts))
        return

    if args.export_only:
        count = export_dashboard()
        print(f"Exported {count} dashboard rows")
        return

    if args.parse_only:
        parsed, skipped = parse_all(settings=settings)
        count = export_dashboard()
        print(f"Parsed offers={parsed}, skipped={skipped}, dashboard_rows={count}")
        return

    asyncio.run(run_sync(max_posts=args.max_posts, settings=settings))


if __name__ == "__main__":
    main()
