#!/usr/bin/env bash
# Restore PostgreSQL from DR backup into a fresh database (DR drill only).
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup.sql.gz>"
  exit 1
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_FILE="$1"
TARGET_DB="${TARGET_DB:-ai_examinator_dr_restore}"

if [[ ! -f "$BACKUP_FILE" ]]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "Restoring $BACKUP_FILE to database $TARGET_DB (destructive to target DB)"
docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
  psql -U ai_examinator -d postgres -c "DROP DATABASE IF EXISTS ${TARGET_DB};"
docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
  psql -U ai_examinator -d postgres -c "CREATE DATABASE ${TARGET_DB};"
gzip -dc "$BACKUP_FILE" | docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
  psql -U ai_examinator -d "$TARGET_DB"

echo "Restore complete. Validate with:"
echo "  docker compose exec postgres psql -U ai_examinator -d $TARGET_DB -c '\\dt'"
