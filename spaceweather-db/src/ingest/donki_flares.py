"""
Ingest NASA DONKI solar flare (FLR) events into the local SQLite database.

DONKI = Database Of Notifications, Knowledge, Information.
API docs: https://api.nasa.gov  (search "DONKI")
Endpoint: https://api.nasa.gov/DONKI/FLR?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD

Get a free API key at https://api.nasa.gov and export NASA_API_KEY.
DEMO_KEY works for light use (low rate limit).
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import requests

from src.db import get_connection

DONKI_FLR_URL = "https://api.nasa.gov/DONKI/FLR"


def _api_key() -> str:
    return os.environ.get("NASA_API_KEY", "DEMO_KEY")


def fetch(start: str, end: str, api_key: str | None = None) -> list[dict]:
    """Fetch flare events between two ISO dates (YYYY-MM-DD) inclusive."""
    params = {"startDate": start, "endDate": end, "api_key": api_key or _api_key()}
    r = requests.get(DONKI_FLR_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json() or []


def upsert(events: list[dict]) -> int:
    """Insert or replace flare rows by flrID. Returns row count."""
    sql = """
        INSERT OR REPLACE INTO flares (
            flr_id, begin_time, peak_time, end_time, class_type,
            source_location, active_region_num, link
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = [
        (
            e.get("flrID"),
            e.get("beginTime"),
            e.get("peakTime"),
            e.get("endTime"),
            e.get("classType"),
            e.get("sourceLocation"),
            e.get("activeRegionNum"),
            e.get("link"),
        )
        for e in events
        if e.get("flrID")
    ]
    if not rows:
        return 0
    with get_connection() as conn:
        conn.executemany(sql, rows)
    return len(rows)


def run(since: str | None = None, until: str | None = None) -> int:
    """Top-level convenience: fetch + upsert. Returns rows inserted."""
    since = since or (date.today() - timedelta(days=30)).isoformat()
    until = until or date.today().isoformat()
    events = fetch(since, until)
    n = upsert(events)
    print(f"[flares] {since} → {until}: {n} events ingested")
    return n


if __name__ == "__main__":
    run()
