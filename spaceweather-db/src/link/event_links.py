"""
Build event_links rows with time-window heuristics.

  Flare → CME:  CME starts within ±6 h of flare peak.
  CME   → Storm: storm onset 24–96 h after CME (typical Sun–Earth transit).

Confidence is a simple temporal-proximity score in [0, 1]:
  - Flare→CME: 1 / (1 + |Δhours|)
  - CME→Storm: 1 / (1 + |Δhours − 60h| / 24h),
    centred on a 60-hour nominal transit time.

Note on time comparisons: we use julianday() arithmetic rather than string
BETWEEN, because SQLite's datetime() modifier returns space-separated
'YYYY-MM-DD HH:MM:SS' while the DONKI feed uses ISO 'YYYY-MM-DDTHH:MMZ'.
String comparison across those formats mis-sorts; julianday() converts both
to a numeric Julian Day and compares cleanly.
"""

from __future__ import annotations

from src.db import get_connection


FLARE_TO_CME_SQL = """
INSERT OR REPLACE INTO event_links
    (source_type, source_id, target_type, target_id, confidence, method)
SELECT
    'flare', f.flr_id,
    'cme',   c.cme_id,
    1.0 / (1.0 + ABS((julianday(c.start_time) - julianday(f.peak_time)) * 24.0)),
    'directional_-0.5h_+6h'
FROM flares f
JOIN cmes c
  ON (julianday(c.start_time) - julianday(f.peak_time)) * 24.0 BETWEEN -0.5 AND 6.0
"""

CME_TO_STORM_SQL = """
INSERT OR REPLACE INTO event_links
    (source_type, source_id, target_type, target_id, confidence, method)
SELECT
    'cme',   c.cme_id,
    'storm', g.gst_id,
    1.0 / (1.0 + ABS((julianday(g.start_time) - julianday(c.start_time)) * 24.0 - 60.0) / 24.0),
    'transit_24_96h'
FROM cmes c
JOIN geomagnetic_storms g
  ON (julianday(g.start_time) - julianday(c.start_time)) * 24.0 BETWEEN 24.0 AND 96.0
"""


def build() -> int:
    """Build/refresh event_links. Returns delta in row count."""
    with get_connection() as conn:
        before = conn.execute("SELECT COUNT(*) FROM event_links").fetchone()[0]
        conn.execute(FLARE_TO_CME_SQL)
        conn.execute(CME_TO_STORM_SQL)
        after = conn.execute("SELECT COUNT(*) FROM event_links").fetchone()[0]
    delta = after - before
    print(f"[link] built {delta} new links (total now {after})")
    return delta


if __name__ == "__main__":
    build()
