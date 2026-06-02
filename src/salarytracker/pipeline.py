"""End-to-end sync: fetch -> parse -> export dashboard JSON."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from salarytracker import DASHBOARD_FILE, DATA_DIR, PARSED_FILE, POSTS_FILE
from salarytracker.config import REQUEST_DELAY_SEC, Settings
from salarytracker.fetch import BATCH_SIZE, COMPENSATION_TAG, _to_record, enrich_posts, fetch_post_page
from salarytracker.normalize import to_dashboard_row
from salarytracker.parse_heuristic import parse_post as parse_heuristic
from salarytracker.parse_llm import parse_post_with_llm


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_existing_ids(path: Path) -> set[int]:
    if not path.exists():
        return set()
    ids: set[int] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            ids.add(int(record["id"]))
    return ids


def _append_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    if not records:
        return
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _should_skip_post(post: dict[str, Any]) -> bool:
    return post.get("downvotes", 0) > post.get("upvotes", 0)


def _parse_post(post: dict[str, Any], settings: Settings) -> list[dict[str, Any]]:
    if settings.llm_enabled:
        offers = parse_post_with_llm(post, settings)
        if offers:
            return offers
    return parse_heuristic(post)


def _valid_offer(offer: dict[str, Any]) -> bool:
    if not offer.get("compensation_post"):
        return False
    if offer.get("currency", "INR") != "INR":
        return False
    if not offer.get("company"):
        return False
    return offer.get("base") is not None or offer.get("total") is not None


async def fetch_and_store(max_posts: int = 500) -> int:
    _ensure_data_dir()
    known_ids = _load_existing_ids(POSTS_FILE)
    fetched = 0

    for skip in range(0, max_posts, BATCH_SIZE):
        nodes, total = fetch_post_page(skip=skip, first=BATCH_SIZE, tag_slug=COMPENSATION_TAG)
        if not nodes:
            break

        batch = [_to_record(node) for node in nodes]
        batch = [post for post in batch if post["id"] not in known_ids]
        if not batch:
            if skip + BATCH_SIZE >= total:
                break
            await asyncio.sleep(REQUEST_DELAY_SEC)
            continue

        await enrich_posts(batch, tag_slug=COMPENSATION_TAG)
        _append_jsonl(POSTS_FILE, batch)
        for post in batch:
            known_ids.add(post["id"])
        fetched += len(batch)
        print(f"Fetched {len(batch)} posts (skip={skip}, total available={total})")

        if skip + BATCH_SIZE >= min(max_posts, total):
            break
        await asyncio.sleep(REQUEST_DELAY_SEC)

    return fetched


def parse_all(settings: Settings | None = None) -> tuple[int, int]:
    settings = settings or Settings.from_env()
    _ensure_data_dir()
    parsed_ids = _load_existing_ids(PARSED_FILE)
    parsed_count = 0
    skipped_count = 0

    if not POSTS_FILE.exists():
        return 0, 0

    with POSTS_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            post = json.loads(line)
            post_id = int(post["id"])
            if post_id in parsed_ids:
                continue

            if _should_skip_post(post):
                _append_jsonl(
                    PARSED_FILE,
                    [{"id": post_id, "created_at": post["created_at"], "skip": True}],
                )
                parsed_ids.add(post_id)
                skipped_count += 1
                continue

            offers = _parse_post(post, settings)
            if not offers:
                _append_jsonl(
                    PARSED_FILE,
                    [{"id": post_id, "created_at": post["created_at"], "skip": True}],
                )
                parsed_ids.add(post_id)
                skipped_count += 1
                continue

            for offer in offers:
                if not _valid_offer(offer):
                    continue
                _append_jsonl(
                    PARSED_FILE,
                    [
                        {
                            "id": post_id,
                            "created_at": post["created_at"],
                            "skip": False,
                            **offer,
                        }
                    ],
                )
                parsed_count += 1
            parsed_ids.add(post_id)

    return parsed_count, skipped_count


def export_dashboard() -> int:
    rows: list[dict[str, Any]] = []
    if not PARSED_FILE.exists():
        with DASHBOARD_FILE.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, indent=2)
        return 0

    with PARSED_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            record = json.loads(line)
            if record.get("skip"):
                continue
            rows.append(
                to_dashboard_row(
                    post_id=int(record["id"]),
                    created_at=record["created_at"],
                    offer=record,
                )
            )

    rows.sort(key=lambda row: row["date"], reverse=True)
    with DASHBOARD_FILE.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)
    return len(rows)


async def run_sync(max_posts: int = 500, settings: Settings | None = None) -> None:
    settings = settings or Settings.from_env()
    started = time.time()
    fetched = await fetch_and_store(max_posts=max_posts)
    parsed, skipped = parse_all(settings=settings)
    count = export_dashboard()
    elapsed = time.time() - started
    print(
        f"Done in {elapsed:.1f}s — fetched={fetched}, parsed_offers={parsed}, "
        f"skipped_posts={skipped}, dashboard_rows={count}"
    )
