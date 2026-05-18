#!/usr/bin/env bash
# Nightly refresh: pull last 7 days of events and rebuild event_links.
# Suggested cron entry (run nightly at 03:00):
#   0 3 * * *  /path/to/spaceweather-db/scripts/refresh.sh >> /var/log/swdb.log 2>&1

set -euo pipefail

cd "$(dirname "$0")/.."
source .venv/bin/activate 2>/dev/null || true

SINCE=$(date -u -d '7 days ago' +%Y-%m-%d 2>/dev/null || date -u -v-7d +%Y-%m-%d)

echo "[$(date -u +%FT%TZ)] refreshing events since ${SINCE}"

python -m src.cli.sw ingest flares  --since "${SINCE}"
python -m src.cli.sw ingest cmes    --since "${SINCE}"   # TODO: implement
python -m src.cli.sw ingest storms  --since "${SINCE}"   # TODO: implement
python -m src.cli.sw link build                          # TODO: implement

echo "[$(date -u +%FT%TZ)] refresh complete"
