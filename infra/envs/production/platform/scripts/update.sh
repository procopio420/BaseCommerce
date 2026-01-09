#!/bin/bash
# Update script for Droplet 3 - Shared Infrastructure
# Pulls latest images and restarts services with zero downtime

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== BaseCommerce Droplet 3 Update ==="
echo "Updating shared infrastructure services..."
echo ""

# Backup before update
echo "[1/5] Creating pre-update backup..."
./scripts/backup-postgres.sh

echo "[2/5] Pulling latest images..."
docker compose pull

echo "[3/5] Restarting workers (zero downtime for DB/Redis)..."
docker compose up -d --no-deps outbox-relay engines-worker

echo "[4/5] Checking service health..."
sleep 5

# Check postgres
if docker exec basecommerce-postgres pg_isready -U basecommerce > /dev/null 2>&1; then
    echo "  ✓ PostgreSQL healthy"
else
    echo "  ✗ PostgreSQL unhealthy!"
    exit 1
fi

# Check redis
if docker exec basecommerce-redis redis-cli ping > /dev/null 2>&1; then
    echo "  ✓ Redis healthy"
else
    echo "  ✗ Redis unhealthy!"
    exit 1
fi

# Check workers are running
if docker compose ps outbox-relay | grep -q "Up"; then
    echo "  ✓ Outbox Relay running"
else
    echo "  ✗ Outbox Relay not running!"
fi

if docker compose ps engines-worker | grep -q "Up"; then
    echo "  ✓ Engines Worker running"
else
    echo "  ✗ Engines Worker not running!"
fi

echo "[5/5] Cleaning up old images..."
docker image prune -f

echo ""
echo "=== Update Complete ==="
echo "Run ./scripts/smoke-test.sh for full verification"

