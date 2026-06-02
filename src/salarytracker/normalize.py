"""Normalize company, role, and location labels for the dashboard."""

from __future__ import annotations

import re

ROLE_SHORT = {"sde", "sse", "mts", "ic", "smt", "smt2", "smt1", "sde1", "sde2", "sde3"}


def title_case_company(name: str) -> str:
    cleaned = re.sub(r"\s+", " ", name.strip())
    if not cleaned:
        return "N/A"
    parts = []
    for token in cleaned.split():
        if token.isupper() and len(token) <= 4:
            parts.append(token)
        else:
            parts.append(token[:1].upper() + token[1:].lower())
    return " ".join(parts)


def normalize_role(role: str) -> str:
    cleaned = role.strip()
    if not cleaned:
        return "N/A"
    parts = cleaned.split()
    if len(parts) == 1 and parts[0].lower() in ROLE_SHORT:
        return parts[0].upper()
    if len(parts) == 2 and parts[1].isdigit() and len(parts[0]) <= 5:
        return f"{parts[0].upper()} {parts[1]}"
    return cleaned.title()


def normalize_location(location: str) -> str:
    if not location:
        return ""
    mapping = {
        "bangalore": "Bengaluru",
        "bengaluru": "Bengaluru",
        "gurgaon": "Gurugram",
        "gurugram": "Gurugram",
        "hyd": "Hyderabad",
        "blr": "Bengaluru",
    }
    key = location.strip().lower()
    return mapping.get(key, location.strip().title())


def to_dashboard_row(post_id: int, created_at: str, offer: dict) -> dict:
    return {
        "id": post_id,
        "date": created_at,
        "location": normalize_location(offer.get("location") or ""),
        "company": title_case_company(offer.get("company") or "N/A"),
        "role": normalize_role(offer.get("role") or "N/A"),
        "yoe": offer.get("yoe"),
        "base": offer.get("base"),
        "total": offer.get("total"),
    }
