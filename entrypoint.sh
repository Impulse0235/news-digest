#!/bin/bash
set -e

DB_PATH="/app/data/state.db"
CONFIG_DIR="/app/config"
DEFAULTS_DIR="/app/defaults"
ROLE="${ROLE:-worker}"   # only the "owner" container initializes; others wait

echo "[entrypoint] Checking bundle state (role: $ROLE)..."

if [ "$ROLE" = "owner" ]; then
  # --- Database: create schema only if this is a genuinely fresh bundle ---
  if [ ! -f "$DB_PATH" ]; then
    echo "[entrypoint] No database found at $DB_PATH — initializing schema"
    python src/db.py --init
  else
    echo "[entrypoint] Existing database found — leaving it untouched"
  fi

  # --- Config: copy factory defaults only for files that don't already exist ---
  # This means a fresh bundle self-populates, but an existing bundle's edits
  # (your real feed list, your real keywords) are never overwritten.
  if [ ! -f "$CONFIG_DIR/feeds.yaml" ]; then
    echo "[entrypoint] No feeds.yaml found — copying default"
    cp "$DEFAULTS_DIR/feeds.yaml" "$CONFIG_DIR/feeds.yaml"
  fi

  if [ ! -f "$CONFIG_DIR/alerts.yaml" ]; then
    echo "[entrypoint] No alerts.yaml found — copying default"
    cp "$DEFAULTS_DIR/alerts.yaml" "$CONFIG_DIR/alerts.yaml"
  fi
else
  # A non-owner container (e.g. news-web) never writes to the bundle on
  # startup — it just waits for the owner to finish, avoiding any chance
  # of two containers touching the same SQLite file at the same instant.
  echo "[entrypoint] Waiting for the owner container to initialize the bundle..."
  tries=0
  until [ -f "$DB_PATH" ] && [ -f "$CONFIG_DIR/feeds.yaml" ] && [ -f "$CONFIG_DIR/alerts.yaml" ]; do
    tries=$((tries + 1))
    if [ "$tries" -gt 30 ]; then
      echo "[entrypoint] Timed out waiting — starting anyway"
      break
    fi
    sleep 1
  done
fi

echo "[entrypoint] Bundle ready. Starting: $*"
exec "$@"
