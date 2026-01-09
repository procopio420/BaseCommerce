#!/bin/bash
# PostgreSQL restore script
# Restores from compressed SQL dump

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

# Check arguments
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <backup-file.sql.gz>"
    echo ""
    echo "Available backups:"
    ls -lh "$BACKUP_DIR"/backup-*.sql.gz 2>/dev/null || echo "No backups found"
    exit 1
fi

BACKUP_FILE="$1"

# Handle relative path
if [[ ! -f "$BACKUP_FILE" ]] && [[ -f "$BACKUP_DIR/$BACKUP_FILE" ]]; then
    BACKUP_FILE="$BACKUP_DIR/$BACKUP_FILE"
fi

if [[ ! -f "$BACKUP_FILE" ]]; then
    echo "ERROR: Backup file not found: $BACKUP_FILE"
    exit 1
fi

echo "=== PostgreSQL Restore ==="
echo "Source: $BACKUP_FILE"
echo "Database: $POSTGRES_DB"
echo ""
echo "WARNING: This will DROP and recreate the database!"
echo "Press Ctrl+C to cancel, or Enter to continue..."
read -r

# Stop workers to prevent writes
echo "[1/4] Stopping workers..."
docker compose stop outbox-relay engines-worker

# Drop and recreate database
echo "[2/4] Recreating database..."
docker exec basecommerce-postgres psql -U "$POSTGRES_USER" -d postgres -c "
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$POSTGRES_DB' AND pid <> pg_backend_pid();
"
docker exec basecommerce-postgres psql -U "$POSTGRES_USER" -d postgres -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
docker exec basecommerce-postgres psql -U "$POSTGRES_USER" -d postgres -c "CREATE DATABASE $POSTGRES_DB;"

# Restore backup
echo "[3/4] Restoring backup..."
gunzip -c "$BACKUP_FILE" | docker exec -i basecommerce-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Restart workers
echo "[4/4] Starting workers..."
docker compose start outbox-relay engines-worker

echo ""
echo "=== Restore Complete ==="
echo "Verify with: ./scripts/smoke-test.sh"

