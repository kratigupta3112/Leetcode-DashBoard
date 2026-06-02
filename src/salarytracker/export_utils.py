"""Write dashboard JSON for local dev and GitHub Pages."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, indent=2, ensure_ascii=False)


def write_dashboard_json(primary: Path, public_mirror: Path, rows: list[dict[str, Any]]) -> int:
    write_json(primary, rows)
    write_json(public_mirror, rows)
    return len(rows)
