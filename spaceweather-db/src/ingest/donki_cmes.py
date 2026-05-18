"""
Ingest NASA DONKI CME (coronal mass ejection) events into the local SQLite
database.

Endpoint: https://api.nasa.gov/DONKI/CME?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
Speed and halo flag live inside the nested cmeAnalyses[] list.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import requests

from src.db import get_connection

DONKI_CME_URL = "https://api.nasa.gov/DONKI/CME"


def _api_key() -> str:
    return os.environ.get("NASA_API_KEY", "DEMO_KEY")


def _extract_cme_fields(e: dict) -> tuple[float | None, bool]:
    """Return (speed_kmps, is_halo) from the best available analysis."""
    analyses = e.get("cmeAnalyses") or []
    if not analyses:
        return None, False
    # Prefer the analysis flagged most accurate; fall back to the first.
    best = next((a for a in analyses if a.get("isMostAccurate")), analyses[0])
    speed = best.get("speed")
    is_halo = (best.get("type") == "Halo") or (
        (best.get("halfAngle") or 0) >= 90)
    return speed, is_halo


def fetch(start: str, end: str, api_key: str | None = None) -> list[dict]:
    params = {"startDate": start, "endDate": end,
              "api_key": api_key or _api_key()}
    r = requests.get(DONKI_CME_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json() or []


def upsert(events: list[dict]) -> int:
    sql = """
        INSERT OR REPLACE INTO cmes (
            cme_id, start_time, speed_kmps, source_location, is_halo, note, link
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    rows = []
    for e in events:
        if not e.get("activityID"):
            continue
        speed, is_halo = _extract_cme_fields(e)
        rows.append((
            e.get("activityID"),
            e.get("startTime"),
            speed,
            e.get("sourceLocation"),
            1 if is_halo else 0,
            e.get("note"),
            e.get("link"),
        ))
    if not rows:
        return 0
    with get_connection() as conn:
        conn.executemany(sql, rows)
    return len(rows)


def run(since: str | None = None, until: str | None = None) -> int:
    since = since or (date.today() - timedelta(days=30)).isoformat()
    until = until or date.today().isoformat()
    events = fetch(since, until)
    n = upsert(events)
    print(f"[cmes] {since} → {until}: {n} events ingested")
    return n


if __name__ == "__main__":
    run()
