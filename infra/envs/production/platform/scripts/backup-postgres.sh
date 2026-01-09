#!/bin/bash
# PostgreSQL backup script
# Creates compressed SQL dump with timestamp

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"

# Load environment
cd "$PROJECT_DIR"
if [[ -f .env ]]; then
    source .env
fi

POSTGRES_USER="${POSTGRES_USER:-basecommerce}"
POSTGRES_DB="${POSTGRES_DB:-basecommerce}"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
BACKUP_FILE="$BACKUP_DIR/backup-${TIMESTAMP}.sql.gz"

echo "=== PostgreSQL Backup ==="
echo "Database: $POSTGRES_DB"
echo "Target: $BACKUP_FILE"
echo ""

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

# Create backup
echo "Creating backup..."
docker exec basecommerce-postgres pg_dump \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --format=plain \
    --no-owner \
    --no-privileges \
    | gzip > "$BACKUP_FILE"

# Verify backup
if [[ -f "$BACKUP_FILE" ]] && [[ -s "$BACKUP_FILE" ]]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✓ Backup created: $BACKUP_FILE ($SIZE)"
else
    echo "✗ Backup failed!"
    exit 1
fi

# Cleanup old backups (keep last 7 days)
echo ""
echo "Cleaning up old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -name "backup-*.sql.gz" -mtime +7 -delete

# List remaining backups
echo ""
echo "Current backups:"
ls -lh "$BACKUP_DIR"/backup-*.sql.gz 2>/dev/null || echo "No backups found"

echo ""
echo "=== Backup Complete ==="

