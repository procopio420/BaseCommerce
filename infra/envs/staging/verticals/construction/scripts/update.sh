#!/bin/bash
# Update script for Droplet 2 - Construction Vertical
# Rebuilds and restarts the application

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== BaseCommerce Droplet 2 Update ==="
echo "Updating construction vertical..."
echo ""

echo "[1/5] Pulling latest code..."
# Assumes git repo is cloned to parent directory
# cd ../../.. && git pull && cd -

echo "[2/5] Building new image..."
docker compose build

echo "[3/5] Stopping old container..."
docker compose down

echo "[4/5] Starting new container..."
docker compose up -d

echo "[5/5] Waiting for health check..."
sleep 10

# Check health
if curl -sf http://localhost:8000/health > /dev/null; then
    echo "✓ Application healthy"
else
    echo "✗ Application unhealthy!"
    docker compose logs --tail=50
    exit 1
fi

echo ""
echo "Cleaning up old images..."
docker image prune -f

echo ""
echo "=== Update Complete ==="
echo "Run ./scripts/smoke-test.sh for full verification"

