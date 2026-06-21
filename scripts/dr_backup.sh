#!/usr/bin/env bash
# Backup PostgreSQL for DR drill (local / pilot). No secrets in repo.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-$ROOT_DIR/backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUTPUT="$BACKUP_DIR/ai_examinator_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "Creating backup at $OUTPUT"
docker compose -f "$ROOT_DIR/docker-compose.yml" exec -T postgres \
  pg_dump -U ai_examinator -d ai_examinator --no-owner --no-acl \
  | gzip > "$OUTPUT"

echo "Backup complete: $OUTPUT"
echo "Verify with: gzip -t $OUTPUT"
