"""Optional LLM parsing when an OpenAI-compatible endpoint is configured."""

from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from salarytracker.config import Settings

SYSTEM_PROMPT = """You extract structured India software-engineer compensation offers from LeetCode forum posts.
Return ONLY valid JSON: an array of objects with keys:
company, role, location, yoe, base, total, currency.
Use INR only. Skip non-compensation posts. Use null for unknown numeric fields.
Split multiple offers in one post into multiple objects."""


def parse_post_with_llm(post: dict[str, Any], settings: Settings) -> list[dict[str, Any]]:
    if not settings.llm_enabled:
        return []

    client_kwargs: dict[str, Any] = {}
    if settings.llm_base_url:
        client_kwargs["base_url"] = settings.llm_base_url
    if settings.llm_api_key:
        client_kwargs["api_key"] = settings.llm_api_key
    client = OpenAI(**client_kwargs)

    text = f"{post.get('title', '')}\n\n{post.get('content') or post.get('summary', '')}"
    response = client.chat.completions.create(
        model=settings.llm_model,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text[:12000]},
        ],
    )
    content = response.choices[0].message.content or "[]"
    match = re.search(r"\[[\s\S]*\]", content)
    if not match:
        return []
    raw = json.loads(match.group(0))
    offers: list[dict[str, Any]] = []
    for item in raw:
        offers.append(
            {
                "compensation_post": True,
                "currency": item.get("currency") or "INR",
                "company": item.get("company") or "",
                "role": item.get("role") or "N/A",
                "location": item.get("location") or "",
                "yoe": item.get("yoe"),
                "base": item.get("base"),
                "total": item.get("total") or item.get("base"),
            }
        )
    return offers
