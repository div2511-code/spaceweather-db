"""
plot_timeline.py — render a flare / CME / storm timeline for a date range.

Two stacked panels sharing the time x-axis:
  Top    — flares as scatter on a log peak-flux scale, with A/B/C/M/X labels
  Bottom — CMEs as vertical bars at start time, height = plane-of-sky speed
  Both   — geomagnetic storms drawn as semi-transparent vertical bands
           (24 h wide, colour intensity by Kp)

Saves a PNG to docs/timeline.png by default.

Examples:
    python scripts/plot_timeline.py --since 2024-05-01 --until 2024-05-31
    python scripts/plot_timeline.py --since 2024-05-01 --until 2024-05-31 \
                                    --out docs/may2024.png
"""

from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch


# -- Visual tokens ------------------------------------------------------------

CLASS_EXPONENT = {"A": -8, "B": -7, "C": -6, "M": -5, "X": -4}
CLASS_COLOR = {
    "A": "#9ca3af",  # cool grey
    "B": "#60a5fa",  # blue
    "C": "#facc15",  # yellow
    "M": "#fb923c",  # orange
    "X": "#ef4444",  # red
}
HALO_COLOR = "#1f2937"      # near-black
NON_HALO_COLOR = "#64748b"  # slate — visible even at low speeds


def kp_color(kp: float) -> str:
    if kp >= 8:
        return "#dc2626"   # extreme — red
    if kp >= 6:
        return "#f97316"   # severe — orange
    if kp >= 5:
        return "#facc15"   # minor/moderate — yellow
    return "#cbd5e1"       # below storm threshold — light grey


# -- Parsers ------------------------------------------------------------------

def parse_flare_class(cls: str | None) -> tuple[str | None, float | None]:
    """'X1.6' → ('X', 1.6e-4 W/m^2). Returns (None, None) on bad input."""
    if not cls or len(cls) < 2:
        return None, None
    letter = cls[0].upper()
    if letter not in CLASS_EXPONENT:
        return None, None
    try:
        multiplier = float(cls[1:])
    except ValueError:
        return None, None
    return letter, multiplier * 10 ** CLASS_EXPONENT[letter]


def parse_iso(t: str | None) -> datetime | None:
    """Parse DONKI's 'YYYY-MM-DDTHH:MM[:SS][Z]' into a naive datetime."""
    if not t:
        return None
    t = t.rstrip("Z")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(t, fmt)
        except ValueError:
            pass
    return None


# -- DB ----------------------------------------------------------------------

def fetch(db: str, since: str, until: str):
    """Pull flares, CMEs, storms within [since 00:00, until 23:59]."""
    lo, hi = f"{since}T00:00:00", f"{until}T23:59:59"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    flares = conn.execute(
        "SELECT peak_time, class_type FROM flares "
        "WHERE peak_time BETWEEN ? AND ? ORDER BY peak_time",
        (lo, hi),
    ).fetchall()
    cmes = conn.execute(
        "SELECT start_time, speed_kmps, is_halo FROM cmes "
        "WHERE start_time BETWEEN ? AND ? AND speed_kmps IS NOT NULL "
        "ORDER BY start_time",
        (lo, hi),
    ).fetchall()
    storms = conn.execute(
        "SELECT start_time, kp_index FROM geomagnetic_storms "
        "WHERE start_time BETWEEN ? AND ? AND kp_index IS NOT NULL "
        "ORDER BY start_time",
        (lo, hi),
    ).fetchall()
    conn.close()
    return flares, cmes, storms


# -- Plot ---------------------------------------------------------------------

def plot(flares, cmes, storms, out: Path, title: str) -> None:
    fig, (ax_f, ax_c) = plt.subplots(
        2, 1,
        figsize=(11, 6),
        sharex=True,
        gridspec_kw={"height_ratios": [3, 2], "hspace": 0.1},
        layout="constrained",
    )

    # Storm bands first so they sit behind the markers
    for s in storms:
        t = parse_iso(s["start_time"])
        if t is None:
            continue
        col = kp_color(s["kp_index"])
        for ax in (ax_f, ax_c):
            ax.axvspan(t, t + timedelta(hours=24), color=col, alpha=0.20, zorder=0)

    # Flare scatter — log peak flux on the y-axis
    for f in flares:
        t = parse_iso(f["peak_time"])
        letter, flux = parse_flare_class(f["class_type"])
        if t is None or flux is None:
            continue
        ax_f.scatter(t, flux, s=55, c=CLASS_COLOR[letter],
                     edgecolor="black", linewidth=0.5, zorder=3)

    ax_f.set_yscale("log")
    ax_f.set_ylim(1e-8, 1e-3)
    ax_f.set_yticks([1e-8, 1e-7, 1e-6, 1e-5, 1e-4])
    ax_f.set_yticklabels(["A", "B", "C", "M", "X"])
    ax_f.set_ylabel("Flare class")
    ax_f.grid(True, axis="y", alpha=0.3, zorder=1)

    # CME bars — 1-hour-wide vertical bars in date-unit width (1 hour ≈ 1/24 day)
    bar_w = 1 / 24
    for c in cmes:
        t = parse_iso(c["start_time"])
        if t is None:
            continue
        col = HALO_COLOR if c["is_halo"] else NON_HALO_COLOR
        ax_c.bar(t, c["speed_kmps"], width=bar_w, color=col,
                 edgecolor="none", zorder=3)

    max_cme = max((c["speed_kmps"] for c in cmes), default=1000) or 1000
    ax_c.set_ylim(0, max(2500, max_cme * 1.1))
    ax_c.set_ylabel("CME speed (km/s)")
    ax_c.set_xlabel("Date (UTC)")
    ax_c.grid(True, axis="y", alpha=0.3, zorder=1)

    # Date axis formatting
    ax_c.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_c.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate()

    # Title + legend
    fig.suptitle(title, fontsize=12)
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", label="X-class flare",
               markerfacecolor=CLASS_COLOR["X"], markeredgecolor="black", markersize=8),
        Line2D([0], [0], marker="o", color="w", label="M-class",
               markerfacecolor=CLASS_COLOR["M"], markeredgecolor="black", markersize=8),
        Line2D([0], [0], marker="o", color="w", label="C-class",
               markerfacecolor=CLASS_COLOR["C"], markeredgecolor="black", markersize=8),
        Patch(facecolor=HALO_COLOR, label="Halo CME"),
        Patch(facecolor=NON_HALO_COLOR, label="Non-halo CME"),
        Patch(facecolor="#dc2626", alpha=0.25, label="Storm Kp ≥ 8"),
        Patch(facecolor="#f97316", alpha=0.25, label="Storm Kp 6–7"),
        Patch(facecolor="#facc15", alpha=0.25, label="Storm Kp 5"),
    ]
    ax_f.legend(
        handles=legend_elements, loc="upper left",
        ncol=2, fontsize=8, framealpha=0.95,
    )

    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"saved {out}  ({len(flares)} flares, {len(cmes)} CMEs, {len(storms)} storms)")


# -- Entry point --------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Render a space-weather timeline plot.")
    ap.add_argument("--db", default="spaceweather.db")
    ap.add_argument("--since", required=True, help="YYYY-MM-DD")
    ap.add_argument("--until", required=True, help="YYYY-MM-DD")
    ap.add_argument("--out", default="docs/timeline.png")
    ap.add_argument("--title", default=None)
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    flares, cmes, storms = fetch(args.db, args.since, args.until)
    title = args.title or f"Space weather timeline:  {args.since} → {args.until}"
    plot(flares, cmes, storms, out, title)


if __name__ == "__main__":
    main()
