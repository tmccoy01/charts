#!/usr/bin/env bash
set -euo pipefail

# Run from repo root (works from cron)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

COMPOSE_BIN="docker-compose"
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  # Prefer docker compose v2 if available
  COMPOSE_BIN="docker compose"
fi

log() {
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

log "Starting weekly FAA chart update"

# 1) Download (idempotent; should skip already-downloaded files)
log "Downloading charts (container: updater)"
$COMPOSE_BIN run --rm updater

# 2) Only process if a new chart cycle exists
CHARTS_DIR="$REPO_ROOT/mapserv/charts"
STATE_DIR="$REPO_ROOT/.state"
LAST_CYCLE_FILE="$STATE_DIR/last_chart_cycle"
mkdir -p "$STATE_DIR"

# The downloader organizes charts as: charts/<type>/<YYYYMMDD>/...
# Detect the newest cycle across all chart types.
LATEST_CYCLE=""
if [ -d "$CHARTS_DIR" ]; then
  LATEST_CYCLE="$({
    find "$CHARTS_DIR" -mindepth 2 -maxdepth 2 -type d 2>/dev/null | awk -F/ '{print $NF}'
  } | grep -E '^[0-9]{8}$' | sort | tail -1)"
fi

if [ -z "$LATEST_CYCLE" ]; then
  log "No chart cycle directories found under $CHARTS_DIR; skipping processing"
  exit 0
fi

LAST_CYCLE=""
if [ -f "$LAST_CYCLE_FILE" ]; then
  LAST_CYCLE="$(cat "$LAST_CYCLE_FILE" || true)"
fi

if [ "$LATEST_CYCLE" = "$LAST_CYCLE" ]; then
  log "No new chart cycle detected ($LATEST_CYCLE); skipping processing"
  exit 0
fi

log "New chart cycle detected: $LAST_CYCLE -> $LATEST_CYCLE"

# 3) Process charts into MapServer-ready outputs
log "Processing charts (container: mapserver)"
$COMPOSE_BIN exec -T mapserver perl /home/mapserv/bin/makemap3.pl

# 4) Cleanup old cycles + raw download artifacts
# Keep only the newest N cycles per chart type to save disk.
KEEP_CYCLES="${KEEP_CYCLES:-1}"
log "Cleanup: keep newest $KEEP_CYCLES cycle(s) per chart type"

# Allow list of file extensions we keep inside cycle directories.
# Goal: keep processed rasters + any minimal sidecars/indexes.
KEEP_EXT_RE='\.(tif|tiff|tfw|prj|ovr|aux\.xml|xml|aref|bref|shp|shx|dbf|qix|cpg|sbn|sbx)$'

cleanup_type_dir() {
  local type_dir="$1"
  [ -d "$type_dir" ] || return 0

  # Find cycle dirs like 20251127
  mapfile -t cycles < <(find "$type_dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | grep -E '^[0-9]{8}$' | sort)
  local count="${#cycles[@]}"
  if [ "$count" -le "$KEEP_CYCLES" ]; then
    return 0
  fi

  local delete_count=$((count - KEEP_CYCLES))
  for ((i=0; i<delete_count; i++)); do
    local old_cycle="${cycles[$i]}"
    local old_path="$type_dir/$old_cycle"
    if [[ "$old_cycle" =~ ^[0-9]{8}$ ]] && [ -d "$old_path" ]; then
      log "Removing old cycle: $old_path"
      rm -rf "$old_path"
    fi
  done

  # For remaining cycles, remove raw downloads/non-essential files.
  mapfile -t keep_cycles < <(find "$type_dir" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | grep -E '^[0-9]{8}$' | sort | tail -n "$KEEP_CYCLES")
  for cycle in "${keep_cycles[@]}"; do
    local cycle_path="$type_dir/$cycle"
    # Always delete zips after processing
    find "$cycle_path" -type f -name '*.zip' -print -delete 2>/dev/null || true

    # Delete anything that isn't in the allowlist
    # (Keep rasters + sidecars; remove metadata/html/etc.)
    while IFS= read -r -d '' f; do
      if ! [[ "$f" =~ $KEEP_EXT_RE ]]; then
        rm -f "$f"
      fi
    done < <(find "$cycle_path" -type f -print0 2>/dev/null)
  done
}

# Apply cleanup to sectional-only (+ misc if present)
for t in sec misc; do
  cleanup_type_dir "$CHARTS_DIR/$t"
done

# Clear work dir (always safe to regenerate)
if [ -d "$CHARTS_DIR/work" ]; then
  log "Clearing work dir: $CHARTS_DIR/work"
  rm -rf "$CHARTS_DIR/work"/* || true
fi

# 5) Clear MapProxy cache (safe; forces fresh tiles for new cycle)
CLEAR_CACHE="${CLEAR_CACHE:-1}"
if [ "$CLEAR_CACHE" = "1" ]; then
  log "Clearing MapProxy cache volume (/cache)"
  # Cache is always safe to clear; it will be regenerated on-demand.
  $COMPOSE_BIN exec -T mapproxy sh -c 'rm -rf /cache/*' || true
fi

# 6) Mark cycle as processed
printf '%s' "$LATEST_CYCLE" > "$LAST_CYCLE_FILE"

# 7) Restart services (safe; ensures new configs/caches are picked up)
log "Restarting services"
$COMPOSE_BIN restart mapserver mapproxy

log "Weekly FAA chart update complete (processed cycle $LATEST_CYCLE)"
