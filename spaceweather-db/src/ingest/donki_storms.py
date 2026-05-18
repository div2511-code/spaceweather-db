"""
Ingest NASA DONKI GST (geomagnetic storm) events into the local SQLite database.

Endpoint: https://api.nasa.gov/DONKI/GST?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD
allKpIndex[] is a list of timed Kp observations; we take the peak as the
representative value for the storm.
"""

from __future__ import annotations

import os
from datetime import date, timedelta

import requests

from src.db import get_connection

DONKI_GST_URL = "https://api.nasa.gov/DONKI/GST"


def _api_key() -> str:
    return os.environ.get("NASA_API_KEY", "DEMO_KEY")


def _peak_kp(e: dict) -> tuple[float | None, str | None]:
    """Return (peak_kp, observed_time_at_peak) or (None, None)."""
    obs = e.get("allKpIndex") or []
    if not obs:
        return None, None
    peak = max(obs, key=lambda o: o.get("kpIndex") or -1)
    return peak.get("kpIndex"), peak.get("observedTime")


def fetch(start: str, end: str, api_key: str | None = None) -> list[dict]:
    params = {"startDate": start, "endDate": end,
              "api_key": api_key or _api_key()}
    r = requests.get(DONKI_GST_URL, params=params, timeout=30)
    r.raise_for_status()
    return r.json() or []


def upsert(events: list[dict]) -> int:
    sql = """
        INSERT OR REPLACE INTO geomagnetic_storms (
            gst_id, start_time, kp_index, observed_time, link
        ) VALUES (?, ?, ?, ?, ?)
    """
    rows = []
    for e in events:
        if not e.get("gstID"):
            continue
        kp, obs_time = _peak_kp(e)
        rows.append((
            e.get("gstID"),
            e.get("startTime"),
            kp,
            obs_time,
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
    print(f"[storms] {since} → {until}: {n} events ingested")
    return n


if __name__ == "__main__":
    run()
