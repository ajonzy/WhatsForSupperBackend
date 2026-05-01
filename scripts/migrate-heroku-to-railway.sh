#!/usr/bin/env bash
# Copy Heroku Postgres to Railway Postgres (needs pg_dump / pg_restore).
# Usage:
#   export SOURCE_DATABASE_URL="postgres://..."
#   export TARGET_DATABASE_URL="postgresql://..."
#   bash scripts/migrate-heroku-to-railway.sh
set -euo pipefail

if [[ -z "${SOURCE_DATABASE_URL:-}" || -z "${TARGET_DATABASE_URL:-}" ]]; then
  echo "Set SOURCE_DATABASE_URL and TARGET_DATABASE_URL." >&2
  exit 1
fi

DUMP="$(mktemp).dump"
trap 'rm -f "$DUMP"' EXIT

echo "Dumping source..."
pg_dump "$SOURCE_DATABASE_URL" -Fc --no-acl --no-owner -f "$DUMP"

echo "Restoring to target..."
set +e
pg_restore --no-acl --no-owner -d "$TARGET_DATABASE_URL" "$DUMP"
rc=$?
set -e
if [[ $rc -ne 0 ]]; then
  echo "pg_restore exited $rc (warnings are common). Verify target DB." >&2
fi
