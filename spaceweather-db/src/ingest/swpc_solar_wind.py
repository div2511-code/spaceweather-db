"""
Ingest NOAA SWPC real-time solar wind. STUB — day-4 stretch goal.

Feeds:
  https://services.swpc.noaa.gov/text/ace-magnetometer.txt   (Bz, Bt)
  https://services.swpc.noaa.gov/text/ace-swepam.txt         (speed, density)

Both are fixed-width text. The C parser in src/parser/swpc_parse.c reads them.
Call into the C library via ctypes from this module.
"""

from __future__ import annotations


def run(since: str | None = None, until: str | None = None) -> int:
    print("[solar_wind] TODO: day 4 — fetch SWPC text, parse via libswpc.so")
    return 0


if __name__ == "__main__":
    run()
