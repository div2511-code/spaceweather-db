# spaceweather-db

A local SQLite archive of **NASA DONKI** and **NOAA SWPC** space-weather events,
with a Python CLI for cross-referencing solar flares, coronal mass ejections
(CMEs), and geomagnetic storms.

> Built alongside an MSc thesis on *Magnetohydrostatic Equilibria of Coronal
> Holes and Active Regions* - the solar source regions that produce the events
> catalogued here.

**Requires:** Python 3.10+. Optional: `gcc` for the C parser (stretch goal).

## What it does

```
                NASA DONKI                NOAA SWPC
              (events API)            (real-time text feeds)
                    |                          |
                    v                          v
              ingest/donki_*.py        ingest/swpc_solar_wind.py
                              \        /
                               v      v
                    +------------------------+
                    |   SQLite (schema.sql)  |
                    |  flares · cmes ·       |
                    |  storms · solar_wind · |
                    |  event_links           |
                    +------------------------+
                              |
                              v
                       cli/sw.py  ──>  query · chain · link
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Initialise the database from the schema (no external sqlite3 CLI needed)
python -c "import sqlite3; sqlite3.connect('spaceweather.db').executescript(open('schema.sql').read())"

# Pull the last 30 days of solar flares from NASA DONKI
python -m src.cli.sw ingest flares

# Query X-class flares since 2024
python -m src.cli.sw query flares --class X --since 2024-01-01
```

`DEMO_KEY` works for light use. For real volume, get a free key in 30 seconds
at <https://api.nasa.gov> and export it:

```bash
export NASA_API_KEY=your-key-here
```

## A real example - the May 2024 Gannon storm sequence

The strongest solar event of cycle 25 so far was the AR 13664 sequence in May
2024, culminating in an X8.7 flare on 14 May. Ingesting that window and
querying the chain reproduces the canonical flare → CME → storm tree:

```bash
python -m src.cli.sw ingest flares --since 2024-05-01 --until 2024-05-31
python -m src.cli.sw ingest cmes   --since 2024-05-01 --until 2024-05-31
python -m src.cli.sw ingest storms --since 2024-05-01 --until 2024-05-31
python -m src.cli.sw link build

python -m src.cli.sw chain --from-flare 2024-05-14T16:46:00-FLR-001
```

```
FLARE  2024-05-14T16:51Z  class=X8.7  id=2024-05-14T16:46:00-FLR-001
  └─ CME    2024-05-14T17:00Z  v=2119.0 km/s  id=2024-05-14T17:00:00-CME-001
      └─ STORM  2024-05-16T06:00Z  Kp=6.0  id=2024-05-16T06:00:00-GST-001
      └─ STORM  2024-05-17T18:00Z  Kp=6.0  id=2024-05-17T18:00:00-GST-001
  └─ CME    2024-05-14T17:30Z  v=1199.0 km/s  id=2024-05-14T17:30:00-CME-001
      └─ STORM  2024-05-16T06:00Z  Kp=6.0  id=2024-05-16T06:00:00-GST-001
      └─ STORM  2024-05-17T18:00Z  Kp=6.0  id=2024-05-17T18:00:00-GST-001
  └─ CME    2024-05-14T17:48Z  v=1292.0 km/s  id=2024-05-14T17:48:00-CME-001
      └─ STORM  2024-05-16T06:00Z  Kp=6.0  id=2024-05-16T06:00:00-GST-001
      └─ STORM  2024-05-17T18:00Z  Kp=6.0  id=2024-05-17T18:00:00-GST-001
```

## Schema

Five tables, all defined in [`schema.sql`](./schema.sql):

| Table | Rows of |
|---|---|
| `flares` | DONKI FLR events - solar flares with class, source location, AR number |
| `cmes` | DONKI CME events - start time, plane-of-sky speed, halo flag |
| `geomagnetic_storms` | DONKI GST events - peak observed Kp index |
| `solar_wind` | NOAA SWPC real-time solar wind (Bz, \|B\|, speed, density) |
| `event_links` | Polymorphic chain table: `flare -> cme`, `cme -> storm`, etc. |

Two design choices worth noting:

- **`event_links` is polymorphic.** Rather than a separate junction table per
  pair (`flare_cme`, `cme_storm`, ...), one table with `(source_type, source_id,
  target_type, target_id)` columns covers every relation. It trades a little
  type-safety for a lot of flexibility - adding new event types doesn't change
  the schema.
- **The flare -> CME link is directional.** A CME observed before the flare peak
  can't physically be the flare's ejection, so the heuristic requires the CME
  to start between 30 minutes before and 6 hours after the flare peak. This
  rules out the backwards-causality matches that a naive +/- 6 h window produces.

The `chain` query above is a self-join across two link types in one SQL
statement, with `julianday()` time arithmetic for the time-window predicates.

## CLI overview

```
sw ingest {flares|cmes|storms}   [--since YYYY-MM-DD] [--until YYYY-MM-DD]
sw query  flares                 [--class X|M|C|B] [--since DATE] [--limit N]
sw query  storms                 [--kpmin N] [--limit N]
sw link   build
sw chain                         --from-flare <flr_id>
```

## Limitations

- `event_links` is heuristic, not curated. Time-window matching over-links
  during active periods - the X8.7 example above associates 3 CMEs with 2
  storms, when in reality at most one CME drove each storm. The `confidence`
  column is meant to let consumers rank candidates, but the table is not
  ground-truth event association.
- `DEMO_KEY` is rate-limited to 30 requests/hour - multi-year backfills need a
  personal NASA API key.
- DONKI completeness drops further back in time; pre-2010 data are sparse.

## Why this project

Solar flares and CMEs originate in **active regions** - concentrated magnetic
flux complexes whose magnetohydrostatic equilibria are the subject of the
thesis this repo accompanies. The geomagnetic storms in the `storms` table are
the geospace consequence of the same magnetic structures studied in that work.
Building a relational store of these events sat naturally alongside the physics
side of the thesis.

## License

MIT
