"""Rule-based extraction of India INR compensation offers from forum posts."""

from __future__ import annotations

import re
from typing import Any

from salarytracker.config import INDIA_KEYWORDS

FIELD_ALIASES = {
    "company": ("company", "org", "organisation", "organization", "employer"),
    "role": ("role", "designation", "position", "level", "title", "band"),
    "location": ("location", "loc", "city", "office"),
    "yoe": (
        "yoe",
        "years of experience",
        "experience",
        "exp",
        "total work exp",
        "work exp",
        "total experience",
    ),
    "base": ("base", "fixed", "base salary", "fixed pay", "base pay"),
    "total": (
        "total",
        "ctc",
        "compensation",
        "tc",
        "package",
        "total compensation",
        "total ctc",
        "annual ctc",
        "current compensation",
        "previous compensation",
    ),
}

NON_COMP_HINTS = (
    "study buddy",
    "looking for a switch",
    "practice system design",
    "resume review",
    "leetcode premium",
    "how many problems",
    "interview experience only",
)

CURRENCY_NON_INR = re.compile(
    r"\b(usd|\$|eur|€|gbp|£|cad|aud|sgd|chf)\b",
    re.IGNORECASE,
)

AMOUNT_PATTERN = re.compile(
    r"(?:₹\s*)?(?P<amount>\d+(?:\.\d+)?)\s*(?:lpa|lac|lakh|lakhs|l\b)?",
    re.IGNORECASE,
)
KV_LINE = re.compile(
    r"^\s*(?P<key>[A-Za-z][A-Za-z \-/]+?)\s*[:=\-]\s*(?P<value>.+?)\s*$"
)
OFFER_HEADER = re.compile(
    r"^\s*(?:offer|option)\s*\d+\s*[:.\-]\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)
JOURNEY_LPA = re.compile(
    r"(?:at|→|to)\s+(?:₹\s*)?(\d+(?:\.\d+)?)\s*(?:lpa|lac|lakh|L\b)",
    re.IGNORECASE,
)


def _clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\u00a0", " ")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\*\*", "", text)
    return text


def _looks_like_comp_post(text: str) -> bool:
    lowered = text.lower()
    if any(hint in lowered for hint in NON_COMP_HINTS):
        return False
    has_money = bool(re.search(r"(lpa|lac|lakh|₹|\binr\b|\d+\s*l\b)", lowered))
    if not has_money:
        return False
    india_signal = any(k in lowered for k in INDIA_KEYWORDS)
    comp_signal = any(
        token in lowered
        for token in ("base", "ctc", "compensation", "offer", "salary", "lpa", "package")
    )
    if CURRENCY_NON_INR.search(text) and not re.search(r"\b(inr|₹|lpa|lac)\b", lowered):
        return comp_signal and india_signal
    return india_signal or ("india" in lowered and comp_signal)


def _normalize_key(raw: str) -> str | None:
    key = raw.strip().lower().replace("_", " ")
    key = re.sub(r"\s+", " ", key)
    for canonical, aliases in FIELD_ALIASES.items():
        if key == canonical or key in aliases:
            return canonical
        if key.endswith(f" {canonical}") or key.startswith(f"{canonical} "):
            return canonical
    return None


def _parse_amount(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = raw.strip().lower()
    if re.search(r"\b(usd|\$|eur|€|k\s*usd)\b", cleaned):
        return None
    match = AMOUNT_PATTERN.search(cleaned)
    if not match:
        return None
    value = float(match.group("amount"))
    if value <= 0 or value > 500:
        return None
    return value


def _parse_yoe(raw: str) -> float | None:
    if not raw:
        return None
    cleaned = raw.strip().lower()
    if any(word in cleaned for word in ("fresher", "new grad", "0 yoe", "0yoe")):
        return 0.0
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if not match:
        return None
    value = float(match.group(1))
    return value if 0 <= value <= 40 else None


def _extract_kv_pairs(text: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    for line in text.split("\n"):
        match = KV_LINE.match(line.strip())
        if not match:
            continue
        canonical = _normalize_key(match.group("key"))
        if canonical:
            pairs[canonical] = match.group("value").strip()
    return pairs


def _split_offer_sections(text: str) -> list[str]:
    parts = OFFER_HEADER.split(text)
    if len(parts) > 1:
        sections = [part.strip() for part in parts if part.strip()]
        return sections

    chunks = re.split(
        r"\n\s*(?:offer|option)\s*\d+\s*[:.\-]?\s*",
        text,
        flags=re.IGNORECASE,
    )
    if len(chunks) > 1:
        return [chunk.strip() for chunk in chunks if chunk.strip()]
    return [text]


def _infer_company_role(section: str, title: str) -> tuple[str | None, str | None]:
    company = None
    role = None
    header = re.search(
        r"(?:offer\s*\d+\s*[:.\-]\s*)?([A-Za-z0-9&.\- ]{2,40}?)\s+(AMTS|SDE\s*\d+|SSE|MTS\s*\d+|L\d+)",
        section,
        re.IGNORECASE,
    )
    if header:
        company = header.group(1).strip()
        role = header.group(2).strip()
    if not company:
        title_match = re.search(
            r"\|\s*([A-Za-z0-9&.\- ]+?)\s*\|\s*([A-Za-z0-9 ]+?)\s*\|",
            title,
        )
        if title_match:
            company, role = title_match.group(1).strip(), title_match.group(2).strip()
    return company, role


def _offer_from_section(section: str, fallback_title: str) -> dict[str, Any] | None:
    pairs = _extract_kv_pairs(section)
    company = pairs.get("company")
    role = pairs.get("role")
    location = pairs.get("location", "")
    yoe = _parse_yoe(pairs.get("yoe", ""))

    inferred_company, inferred_role = _infer_company_role(section, fallback_title)
    company = company or inferred_company
    role = role or inferred_role

    base = _parse_amount(pairs.get("base", ""))
    total = _parse_amount(pairs.get("total", ""))

    if not base and not total:
        amounts = [
            _parse_amount(match.group(0))
            for match in AMOUNT_PATTERN.finditer(section)
        ]
        amounts = [a for a in amounts if a is not None]
        if amounts:
            base = amounts[0]
            total = amounts[-1] if len(amounts) > 1 else amounts[0]

    if not company or (base is None and total is None):
        return None

    if total is None:
        total = base
    if base is None:
        base = total

    return {
        "compensation_post": True,
        "currency": "INR",
        "company": company.strip(),
        "role": (role or "N/A").strip(),
        "location": location.strip(),
        "yoe": yoe,
        "base": base,
        "total": total,
    }


def _parse_journey_post(post: dict[str, Any], body: str) -> list[dict[str, Any]]:
    """Extract the latest compensation milestone from career journey writeups."""
    matches = list(JOURNEY_LPA.finditer(body))
    if len(matches) < 2:
        return []
    total = float(matches[-1].group(1))
    title = post.get("title", "")
    company = "Career Journey"
    if "principal" in body.lower():
        role = "Principal Engineer"
    elif "lead" in body.lower():
        role = "Lead Engineer"
    else:
        role = "Senior Software Engineer"
    return [
        {
            "compensation_post": True,
            "currency": "INR",
            "company": company,
            "role": role,
            "location": "",
            "yoe": None,
            "base": total,
            "total": total,
        }
    ]


def parse_post(post: dict[str, Any]) -> list[dict[str, Any]]:
    body = _clean_text(f"{post.get('title', '')}\n{post.get('content') or post.get('summary', '')}")
    if not _looks_like_comp_post(body):
        return []

    offers: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for section in _split_offer_sections(body):
        offer = _offer_from_section(section, post.get("title", ""))
        if not offer:
            continue
        key = (
            offer["company"].lower(),
            offer["role"].lower(),
            offer.get("base"),
            offer.get("total"),
            offer.get("location", "").lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        offers.append(offer)

    if not offers:
        offers = _parse_journey_post(post, body)

    return offers
