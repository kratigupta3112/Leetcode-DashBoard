from __future__ import annotations

from pathlib import Path

import httpx


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    out = root / "public" / "index.html"
    url = "https://raw.githubusercontent.com/0xku/leetcode-compensation/master/index.html"

    html = httpx.get(url, timeout=30).text

    # Our dashboard is served at /public/index.html, data sits in /data/
    html = html.replace("fetch('data/final_data.json')", "fetch('../data/dashboard_data.json')")
    html = html.replace('fetch(\"data/final_data.json\")', 'fetch(\"../data/dashboard_data.json\")')

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html)} bytes)")


if __name__ == "__main__":
    main()

