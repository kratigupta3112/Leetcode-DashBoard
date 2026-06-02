"""Sync interview experiences from LeetCode discuss/interview-experience."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from salarytracker import (
    DATA_DIR,
    INTERVIEW_DATA_FILE,
    INTERVIEW_PARSED_FILE,
    INTERVIEW_POSTS_FILE,
)
from salarytracker.config import REQUEST_DELAY_SEC
from salarytracker.fetch import BATCH_SIZE, INTERVIEW_TAG, _to_record, enrich_posts, fetch_post_page
from salarytracker.interview_parse import parse_interview_post


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_ids(path: Path) -> set[int]:
    if not path.exists():
        return set()
    ids: set[int] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                ids.add(int(json.loads(line)["id"]))
    return ids


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def fetch_interview_posts(max_posts: int = 500) -> int:
    _ensure_data_dir()
    known = _load_ids(INTERVIEW_POSTS_FILE)
    fetched = 0

    for skip in range(0, max_posts, BATCH_SIZE):
        nodes, total = fetch_post_page(skip=skip, first=BATCH_SIZE, tag_slug=INTERVIEW_TAG)
        if not nodes:
            break

        batch = [_to_record(node) for node in nodes]
        batch = [p for p in batch if p["id"] not in known]
        if not batch:
            if skip + BATCH_SIZE >= total:
                break
            await asyncio.sleep(REQUEST_DELAY_SEC)
            continue

        await enrich_posts(batch, tag_slug=INTERVIEW_TAG)
        _append_jsonl(INTERVIEW_POSTS_FILE, batch)
        for post in batch:
            known.add(post["id"])
        fetched += len(batch)
        print(f"[interview] Fetched {len(batch)} (skip={skip}, total={total})")

        if skip + BATCH_SIZE >= min(max_posts, total):
            break
        await asyncio.sleep(REQUEST_DELAY_SEC)

    return fetched


def parse_interviews() -> tuple[int, int]:
    _ensure_data_dir()
    parsed_ids = _load_ids(INTERVIEW_PARSED_FILE)
    parsed_count = 0
    skipped = 0

    if not INTERVIEW_POSTS_FILE.exists():
        return 0, 0

    with INTERVIEW_POSTS_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            post = json.loads(line)
            post_id = int(post["id"])
            if post_id in parsed_ids:
                continue

            record = parse_interview_post(post)
            if not record:
                _append_jsonl(
                    INTERVIEW_PARSED_FILE,
                    [{"id": post_id, "skip": True}],
                )
                skipped += 1
            else:
                _append_jsonl(INTERVIEW_PARSED_FILE, [record])
                parsed_count += 1
            parsed_ids.add(post_id)

    return parsed_count, skipped


def export_interview_data() -> int:
    rows: list[dict[str, Any]] = []
    if INTERVIEW_PARSED_FILE.exists():
        with INTERVIEW_PARSED_FILE.open("r", encoding="utf-8") as handle:
            for line in handle:
                rec = json.loads(line)
                if rec.get("skip"):
                    continue
                rows.append(rec)

    rows.sort(key=lambda r: r.get("date") or "", reverse=True)
    with INTERVIEW_DATA_FILE.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    return len(rows)


async def run_interview_sync(max_posts: int = 500) -> None:
    started = time.time()
    fetched = await fetch_interview_posts(max_posts=max_posts)
    parsed, skipped = parse_interviews()
    count = export_interview_data()
    elapsed = time.time() - started
    print(
        f"[interview] Done in {elapsed:.1f}s — fetched={fetched}, "
        f"parsed={parsed}, skipped={skipped}, dashboard_rows={count}"
    )
