"""Parse interview experience posts from LeetCode discuss content."""

from __future__ import annotations

import re
from typing import Any

INTERVIEW_HINTS = (
    "interview experience",
    "interview exp",
    "interview process",
    "interview round",
    "interview journey",
    "onsite",
    "oa round",
    "hackerrank",
    "technical round",
    "hiring manager",
    "culture fit",
    "final round",
)

SKIP_HINTS = (
    "study buddy",
    "how many problems",
    "compensation",
    " salary",
    "ctc",
    "lpa",
    "offer comparison",
    "which offer",
    "leetcode premium",
)

OUTCOME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("offer", re.compile(r"\b(got the offer|received offer|offer accepted|selected|cleared all rounds)\b", re.I)),
    ("reject", re.compile(r"\b(rejected|rejection|did not make|failed|unsuccessful|no offer)\b", re.I)),
    ("ongoing", re.compile(r"\b(scheduled|upcoming|waiting for|in process|awaiting)\b", re.I)),
]

ROLE_PATTERN = re.compile(
    r"\b(SDE\s*\d*|SSE|MTS\s*\d*|L\d{1,2}|IC\d|"
    r"Software Engineer[^|,\n]{0,30}|"
    r"Senior Member of Technical Staff|"
    r"Member of Technical Staff|"
    r"Frontend Engineer|Backend Engineer|"
    r"Full\s*stack)\b",
    re.I,
)

YOE_PATTERN = re.compile(
    r"(?:yoe|years?\s+of\s+experience|experience)\s*[:=\-]?\s*(\d+(?:\.\d+)?)",
    re.I,
)

COMPANY_SUFFIX = re.compile(
    r"\s*[\|\-–]\s*.*$",
)
INTERVIEW_TAIL = re.compile(
    r"\s+(interview experience|interview exp|interview|experience|exp)\s*$",
    re.I,
)


def _clean(text: str) -> str:
    return re.sub(r"<[^>]+>", " ", text or "").replace("\r\n", "\n")


def is_interview_post(post: dict[str, Any]) -> bool:
    text = _clean(f"{post.get('title', '')}\n{post.get('content') or post.get('summary', '')}").lower()
    if any(h in text for h in SKIP_HINTS):
        if not any(h in text for h in INTERVIEW_HINTS):
            return False
    if "interview experience" in (post.get("title") or "").lower():
        return True
    return any(h in text for h in INTERVIEW_HINTS)


def _extract_company(title: str) -> str:
    raw = title.strip()
    raw = COMPANY_SUFFIX.sub("", raw)
    raw = INTERVIEW_TAIL.sub("", raw).strip()

    # "Google L4" -> Google; "Amazon SDE2" -> Amazon
    parts = re.split(r"\s+[\|\-–]\s+", raw)
    head = parts[0].strip()

    # Remove trailing role/level tokens
    head = re.sub(
        r"\s+(SDE\s*\d*|SSE|MTS\s*\d*|L\d{1,2}|IC\d|Frontend|Backend|Full\s*Stack).*$",
        "",
        head,
        flags=re.I,
    ).strip()

    if len(head) < 2:
        return "Unknown"
    if len(head) > 48:
        head = head[:48].strip()
    return head.title()


def _extract_role(title: str, body: str) -> str:
    for source in (title, body[:500]):
        match = ROLE_PATTERN.search(source)
        if match:
            return match.group(1).strip()
    return "N/A"


def _extract_yoe(body: str) -> float | None:
    match = YOE_PATTERN.search(body)
    if match:
        return float(match.group(1))
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*\+?\s*years?\b", body, re.I)
    if match:
        value = float(match.group(1))
        return value if 0 <= value <= 40 else None
    return None


def _extract_outcome(text: str) -> str:
    for label, pattern in OUTCOME_PATTERNS:
        if pattern.search(text):
            return label
    return "unknown"


def _extract_round_count(body: str) -> int | None:
    headers = re.findall(r"^#+\s*round\s*(\d+)", body, re.I | re.M)
    if headers:
        return max(int(n) for n in headers)
    numbered = re.findall(r"\bround\s*(\d+)\b", body, re.I)
    if numbered:
        return max(int(n) for n in numbered)
    return None


def parse_interview_post(post: dict[str, Any]) -> dict[str, Any] | None:
    if not is_interview_post(post):
        return None

    title = post.get("title") or ""
    body = _clean(post.get("content") or post.get("summary") or "")
    full_text = f"{title}\n{body}"

    company = _extract_company(title)
    if company.lower() in {"unknown", "need help", "getting rejections"}:
        # Try first bold company-like token in body
        multi = re.search(
            r"interviewed with\s+([A-Za-z0-9&.\- ]{2,30})",
            full_text,
            re.I,
        )
        if multi:
            company = multi.group(1).strip().title()

    return {
        "id": int(post["id"]),
        "date": post.get("created_at"),
        "company": company,
        "role": _extract_role(title, body),
        "yoe": _extract_yoe(full_text),
        "outcome": _extract_outcome(full_text),
        "rounds": _extract_round_count(body),
        "title": title,
        "summary": (post.get("summary") or body[:280]).strip(),
        "url": post.get("url") or f"https://leetcode.com/discuss/post/{post['id']}",
        "upvotes": post.get("upvotes", 0),
        "comments": post.get("comment_count", 0),
    }
