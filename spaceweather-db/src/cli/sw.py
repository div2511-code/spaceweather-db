"""
sw — Space Weather DB CLI.

Examples:
    python -m src.cli.sw ingest flares
    python -m src.cli.sw ingest flares --since 2024-01-01 --until 2024-12-31
    python -m src.cli.sw query flares --class X --since 2024-01-01
    python -m src.cli.sw query storms --kpmin 7
    python -m src.cli.sw chain --from-flare <flr_id>
"""

from __future__ import annotations

import argparse
import sys

from src.db import get_connection
from src.ingest import donki_flares, donki_cmes, donki_storms, swpc_solar_wind
from src.link import event_links


# -----------------------------------------------------------------------------
# ingest
# -----------------------------------------------------------------------------
INGESTORS = {
    "flares": donki_flares.run,
    "cmes":   donki_cmes.run,
    "storms": donki_storms.run,
    "wind":   swpc_solar_wind.run,
}


def cmd_ingest(args: argparse.Namespace) -> int:
    fn = INGESTORS[args.feed]
    fn(since=args.since, until=args.until)
    return 0


# -----------------------------------------------------------------------------
# query
# -----------------------------------------------------------------------------
def cmd_query_flares(args: argparse.Namespace) -> int:
    sql = "SELECT flr_id, peak_time, class_type, source_location, active_region_num FROM flares WHERE 1=1"
    params: list = []
    if args.class_:
        sql += " AND class_type LIKE ?"
        params.append(args.class_ + "%")
    if args.since:
        sql += " AND peak_time >= ?"
        params.append(args.since)
    sql += " ORDER BY peak_time DESC LIMIT ?"
    params.append(args.limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        print("No matching flares.")
        return 0
    print(f"{'peak_time':<25} {'class':<6} {'source':<10} {'AR':<8} flr_id")
    print("-" * 90)
    for r in rows:
        print(f"{r['peak_time']:<25} {r['class_type'] or '?':<6} "
              f"{r['source_location'] or '?':<10} {str(r['active_region_num'] or '?'):<8} "
              f"{r['flr_id']}")
    return 0


def cmd_query_storms(args: argparse.Namespace) -> int:
    sql = "SELECT gst_id, start_time, kp_index FROM geomagnetic_storms WHERE 1=1"
    params: list = []
    if args.kpmin is not None:
        sql += " AND kp_index >= ?"
        params.append(args.kpmin)
    sql += " ORDER BY start_time DESC LIMIT ?"
    params.append(args.limit)

    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()

    if not rows:
        print("No matching storms. (Did you implement donki_storms.py yet?)")
        return 0
    for r in rows:
        print(f"{r['start_time']:<25} Kp={r['kp_index']:<5} {r['gst_id']}")
    return 0


# -----------------------------------------------------------------------------
# chain — the showpiece JOIN query
# -----------------------------------------------------------------------------
CHAIN_SQL = """
SELECT
    f.flr_id, f.peak_time, f.class_type,
    c.cme_id, c.start_time AS cme_start, c.speed_kmps,
    g.gst_id, g.start_time AS gst_start, g.kp_index
FROM flares f
LEFT JOIN event_links el_fc
    ON el_fc.source_type = 'flare' AND el_fc.source_id = f.flr_id
   AND el_fc.target_type = 'cme'
LEFT JOIN cmes c
    ON c.cme_id = el_fc.target_id
LEFT JOIN event_links el_cg
    ON el_cg.source_type = 'cme' AND el_cg.source_id = c.cme_id
   AND el_cg.target_type = 'storm'
LEFT JOIN geomagnetic_storms g
    ON g.gst_id = el_cg.target_id
WHERE f.flr_id = ?
"""


def cmd_chain(args: argparse.Namespace) -> int:
    with get_connection() as conn:
        rows = conn.execute(CHAIN_SQL, [args.from_flare]).fetchall()
    if not rows:
        print(f"No flare with flr_id={args.from_flare}")
        return 1

    # The LEFT JOIN returns one row per (flare, cme, storm) combination.
    # The flare details are identical across all rows — print the header once,
    # then group storms under each unique CME.
    first = rows[0]
    print(
        f"FLARE  {first['peak_time']}  class={first['class_type']}  id={first['flr_id']}")

    cmes: dict = {}  # cme_id -> {"start": ..., "speed": ..., "storms": [...]}
    for r in rows:
        if not r["cme_id"]:
            continue
        cme = cmes.setdefault(r["cme_id"], {
            "start": r["cme_start"], "speed": r["speed_kmps"], "storms": [],
        })
        if r["gst_id"] and not any(s[0] == r["gst_id"] for s in cme["storms"]):
            cme["storms"].append((r["gst_id"], r["gst_start"], r["kp_index"]))

    for cme_id, d in cmes.items():
        print(f"  └─ CME    {d['start']}  v={d['speed']} km/s  id={cme_id}")
        for gst_id, gst_start, kp in d["storms"]:
            print(f"      └─ STORM  {gst_start}  Kp={kp}  id={gst_id}")
    return 0


# -----------------------------------------------------------------------------
# link
# -----------------------------------------------------------------------------
def cmd_link(_args: argparse.Namespace) -> int:
    event_links.build()
    return 0


# -----------------------------------------------------------------------------
# main
# -----------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sw", description="Space Weather DB CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    # ingest
    pi = sub.add_parser("ingest", help="Pull from a feed into the DB")
    pi.add_argument("feed", choices=list(INGESTORS.keys()))
    pi.add_argument("--since", help="ISO date YYYY-MM-DD (default: 30 days ago)")
    pi.add_argument("--until", help="ISO date YYYY-MM-DD (default: today)")
    pi.set_defaults(func=cmd_ingest)

    # query
    pq = sub.add_parser("query", help="Query the DB")
    pqs = pq.add_subparsers(dest="entity", required=True)

    pqf = pqs.add_parser("flares")
    pqf.add_argument("--class", dest="class_", help="Class prefix: X / M / C / B")
    pqf.add_argument("--since", help="ISO date YYYY-MM-DD")
    pqf.add_argument("--limit", type=int, default=50)
    pqf.set_defaults(func=cmd_query_flares)

    pqg = pqs.add_parser("storms")
    pqg.add_argument("--kpmin", type=float, help="Minimum Kp index")
    pqg.add_argument("--limit", type=int, default=50)
    pqg.set_defaults(func=cmd_query_storms)

    # chain
    pc = sub.add_parser("chain", help="Trace flare → CME → storm")
    pc.add_argument("--from-flare", required=True, help="flr_id to trace from")
    pc.set_defaults(func=cmd_chain)

    # link
    pl = sub.add_parser("link", help="Rebuild event_links")
    plsub = pl.add_subparsers(dest="action", required=True)
    plb = plsub.add_parser("build")
    plb.set_defaults(func=cmd_link)

    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
