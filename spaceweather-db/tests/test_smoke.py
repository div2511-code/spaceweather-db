"""Smoke tests — run with: pytest -v"""

import os
import sqlite3
import tempfile

import pytest


def test_schema_creates_all_tables():
    """schema.sql should produce the five expected tables."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tf:
        path = tf.name
    try:
        with open("schema.sql") as f:
            schema = f.read()
        conn = sqlite3.connect(path)
        conn.executescript(schema)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )}
        conn.close()
        assert tables == {"flares", "cmes", "geomagnetic_storms", "solar_wind", "event_links"}
    finally:
        os.unlink(path)


def test_flares_upsert_idempotent():
    """Inserting the same flr_id twice should keep one row."""
    from src.db import get_connection
    from src.ingest.donki_flares import upsert

    db_path = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    os.environ["SWDB_PATH"] = db_path
    try:
        with open("schema.sql") as f:
            schema = f.read()
        conn = sqlite3.connect(db_path)
        conn.executescript(schema)
        conn.close()

        sample = [{
            "flrID": "2024-05-10T01:22:00-FLR-001",
            "beginTime": "2024-05-10T01:22Z",
            "peakTime": "2024-05-10T01:45Z",
            "endTime": "2024-05-10T02:05Z",
            "classType": "X1.0",
            "sourceLocation": "N15W30",
            "activeRegionNum": 13664,
            "link": "https://example.com",
        }]
        upsert(sample)
        upsert(sample)  # second call should not duplicate

        with get_connection() as conn:
            (count,) = conn.execute("SELECT COUNT(*) FROM flares").fetchone()
        assert count == 1
    finally:
        os.unlink(db_path)
        os.environ.pop("SWDB_PATH", None)
