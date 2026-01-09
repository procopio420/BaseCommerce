#!/bin/bash
# Smoke test for Droplet 3 - Shared Infrastructure
# Verifies all services are running and healthy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=== Droplet 3 Smoke Test ==="
echo ""

FAILED=0

# Test PostgreSQL
echo -n "PostgreSQL... "
if docker exec basecommerce-postgres pg_isready -U basecommerce > /dev/null 2>&1; then
    VERSION=$(docker exec basecommerce-postgres psql -U basecommerce -t -c "SELECT version();" | head -1 | xargs)
    echo "✓ OK ($VERSION)"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test PostgreSQL can execute queries
echo -n "PostgreSQL queries... "
if docker exec basecommerce-postgres psql -U basecommerce -c "SELECT 1;" > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test Redis
echo -n "Redis... "
if docker exec basecommerce-redis redis-cli ping > /dev/null 2>&1; then
    VERSION=$(docker exec basecommerce-redis redis-cli INFO server | grep redis_version | cut -d: -f2 | tr -d '\r')
    echo "✓ OK (v$VERSION)"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test Redis Streams capability
echo -n "Redis Streams... "
if docker exec basecommerce-redis redis-cli XINFO HELP > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test Outbox Relay container
echo -n "Outbox Relay... "
if docker compose ps outbox-relay 2>/dev/null | grep -q "Up"; then
    echo "✓ Running"
else
    echo "✗ NOT RUNNING"
    FAILED=1
fi

# Test Engines Worker container
echo -n "Engines Worker... "
if docker compose ps engines-worker 2>/dev/null | grep -q "Up"; then
    echo "✓ Running"
else
    echo "✗ NOT RUNNING"
    FAILED=1
fi

# Memory check
echo ""
echo "=== Resource Usage ==="
echo -n "PostgreSQL memory: "
docker stats --no-stream --format "{{.MemUsage}}" basecommerce-postgres 2>/dev/null || echo "N/A"
echo -n "Redis memory: "
docker exec basecommerce-redis redis-cli INFO memory 2>/dev/null | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "N/A"

# Disk usage
echo ""
echo "=== Disk Usage ==="
df -h /var/lib/docker | tail -1

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo "=== All Tests Passed ✓ ==="
    exit 0
else
    echo "=== Some Tests Failed ✗ ==="
    exit 1
fi

