#!/bin/bash
# Update script for Droplet 1 - Edge
# Pulls latest images and reloads nginx

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== BaseCommerce Droplet 1 Update ==="
echo "Updating edge services..."
echo ""

echo "[1/4] Pulling latest images..."
docker compose pull

echo "[2/4] Validating nginx config..."
docker compose run --rm nginx nginx -t

echo "[3/4] Restarting services..."
docker compose up -d

echo "[4/4] Reloading nginx (zero downtime)..."
docker exec basecommerce-nginx nginx -s reload

echo ""
echo "Cleaning up old images..."
docker image prune -f

echo ""
echo "=== Update Complete ==="
echo "Run ./scripts/smoke-test.sh for verification"

