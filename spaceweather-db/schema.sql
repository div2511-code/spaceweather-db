- "- spaceweather-db schema
-- Run with: sqlite3 spaceweather.db < schema.sql

PRAGMA foreign_keys = ON;

-- =============================================================================
-- Solar flares (NASA DONKI FLR feed)
-- =============================================================================
CREATE TABLE IF NOT EXISTS flares (
    flr_id              TEXT PRIMARY KEY,
    begin_time          TEXT NOT NULL,
    peak_time           TEXT NOT NULL,
    end_time            TEXT,
    class_type          TEXT,                       -- e.g. "X1.0", "M5.2", "C3.1"
    source_location     TEXT,                       -- e.g. "N15W30"
    active_region_num   INTEGER,                    -- NOAA AR number
    link                TEXT,                       -- canonical DONKI link
    fetched_at          TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_flares_peak  ON flares(peak_time);
CREATE INDEX IF NOT EXISTS idx_flares_class ON flares(class_type);

-- =============================================================================
-- Coronal mass ejections (NASA DONKI CME feed)
-- =============================================================================
CREATE TABLE IF NOT EXISTS cmes (
    cme_id              TEXT PRIMARY KEY,
    start_time          TEXT NOT NULL,
    speed_kmps          REAL,                       -- plane-of-sky speed
    source_location     TEXT,
    is_halo             INTEGER,                    -- 0/1
    note                TEXT,
    link                TEXT,
    fetched_at          TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_cmes_start ON cmes(start_time);

-- =============================================================================
-- Geomagnetic storms (NASA DONKI GST feed)
-- =============================================================================
CREATE TABLE IF NOT EXISTS geomagnetic_storms (
    gst_id              TEXT PRIMARY KEY,
    start_time          TEXT NOT NULL,
    kp_index            REAL,                       -- peak observed Kp
    observed_time       TEXT,
    link                TEXT,
    fetched_at          TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_storms_start ON geomagnetic_storms(start_time);
CREATE INDEX IF NOT EXISTS idx_storms_kp    ON geomagnetic_storms(kp_index);

-- =============================================================================
-- Solar wind time-series (NOAA SWPC real-time feeds)
-- =============================================================================
CREATE TABLE IF NOT EXISTS solar_wind (
    timestamp           TEXT PRIMARY KEY,           -- ISO 8601 UTC
    bz_gsm              REAL,                       -- nT, GSM frame
    bt                  REAL,                       -- nT, total |B|
    speed_kmps          REAL,
    density_pcc         REAL,                       -- protons / cm^3
    temperature_k       REAL
);
CREATE INDEX IF NOT EXISTS idx_sw_ts ON solar_wind(timestamp);

-- =============================================================================
-- Event chain links — polymorphic edge table.
-- source_type/target_type in ('flare', 'cme', 'storm').
-- Populated by src/link/event_links.py with time-window heuristics.
-- =============================================================================
CREATE TABLE IF NOT EXISTS event_links (
    source_type         TEXT NOT NULL,
    source_id           TEXT NOT NULL,
    target_type         TEXT NOT NULL,
    target_id           TEXT NOT NULL,
    confidence          REAL,                       -- 0.0 – 1.0
    method              TEXT,                       -- e.g. 'time_window_6h'
    PRIMARY KEY (source_type, source_id, target_type, target_id)
);
CREATE INDEX IF NOT EXISTS idx_links_source ON event_links(source_type, source_id);
CREATE INDEX IF NOT EXISTS idx_links_target ON event_links(target_type, target_id);
