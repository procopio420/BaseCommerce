#!/bin/bash
# Smoke test for Droplet 2 - Construction Vertical
# Verifies application is running and healthy

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Note: We don't source .env here because it may contain special characters
# Docker Compose will load it automatically when needed

echo "=== Droplet 2 Smoke Test ==="
echo ""

FAILED=0

# Test container running
echo -n "Container running... "
if docker compose ps construction 2>/dev/null | grep -q "Up"; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test health endpoint
echo -n "Health endpoint... "
HEALTH=$(curl -sf http://localhost:8000/health 2>/dev/null || echo "")
if [[ -n "$HEALTH" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test OpenAPI docs
echo -n "OpenAPI docs... "
if curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test database connectivity
echo -n "Database connection... "
DB_TEST=$(docker exec basecommerce-construction python -c "
from sqlalchemy import create_engine, text
import os
try:
    e = create_engine(os.environ.get('DATABASE_URL', ''))
    with e.connect() as c:
        c.execute(text('SELECT 1'))
        print('OK')
except Exception as ex:
    print(f'FAIL: {ex}')
" 2>&1)
if [[ "$DB_TEST" == "OK" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED ($DB_TEST)"
    FAILED=1
fi

# Test Redis connectivity
echo -n "Redis connection... "
REDIS_TEST=$(docker exec basecommerce-construction python -c "
import redis
import os
try:
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    r.ping()
    print('OK')
except Exception as ex:
    print(f'FAIL: {ex}')
" 2>&1)
if [[ "$REDIS_TEST" == "OK" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED ($REDIS_TEST)"
    FAILED=1
fi

# Memory usage
echo ""
echo "=== Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" basecommerce-construction

# Disk usage
echo ""
echo "=== Disk Usage ==="
df -h / | tail -1

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo "=== All Tests Passed ✓ ==="
    exit 0
else
    echo "=== Some Tests Failed ✗ ==="
    exit 1
fi

