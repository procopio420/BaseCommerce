#!/bin/bash
# End-to-End Smoke Test for Local Development
# Validates all services are running and communicating correctly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== BaseCommerce E2E Smoke Test ==="
echo ""
echo "Testing local development environment..."
echo ""

FAILED=0
WARNINGS=0

# Helper function for tests
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected="${3:-}"
    
    echo -n "$name... "
    
    RESPONSE=$(curl -sf "$url" 2>/dev/null || echo "")
    
    if [[ -z "$RESPONSE" ]]; then
        echo "✗ FAILED (no response)"
        return 1
    fi
    
    if [[ -n "$expected" ]] && ! echo "$RESPONSE" | grep -q "$expected"; then
        echo "✗ FAILED (unexpected response)"
        return 1
    fi
    
    echo "✓ OK"
    return 0
}

# ==========================================================================
# INFRASTRUCTURE (Droplet 3)
# ==========================================================================
echo "--- Infrastructure Services ---"

echo -n "PostgreSQL... "
if docker exec local-postgres pg_isready -U basecommerce > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

echo -n "Redis... "
if docker exec local-redis redis-cli ping > /dev/null 2>&1; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

echo -n "Outbox Relay... "
if docker compose ps outbox-relay 2>/dev/null | grep -q "Up\|running"; then
    echo "✓ Running"
else
    echo "⚠ NOT RUNNING"
    WARNINGS=$((WARNINGS + 1))
fi

echo -n "Engines Worker... "
if docker compose ps engines-worker 2>/dev/null | grep -q "Up\|running"; then
    echo "✓ Running"
else
    echo "⚠ NOT RUNNING"
    WARNINGS=$((WARNINGS + 1))
fi

echo ""

# ==========================================================================
# VERTICAL (Droplet 2)
# ==========================================================================
echo "--- Construction Vertical ---"

test_endpoint "Health endpoint" "http://localhost:8000/health" "ok" || FAILED=1
test_endpoint "OpenAPI docs" "http://localhost:8000/docs" "swagger" || FAILED=1

echo ""

# ==========================================================================
# EDGE (Droplet 1)
# ==========================================================================
echo "--- Edge Services ---"

test_endpoint "Nginx health" "http://localhost/health" "edge" || FAILED=1
test_endpoint "Auth service" "http://localhost/auth/health" "ok" || FAILED=1
test_endpoint "Tenant JSON (default)" "http://localhost/tenant.json" "Local Development" || FAILED=1

echo ""

# ==========================================================================
# MULTI-TENANT ROUTING
# ==========================================================================
echo "--- Multi-Tenant Routing ---"

echo -n "Demo tenant JSON... "
DEMO_TENANT=$(curl -sf -H "Host: demo.localhost" "http://localhost/tenant.json" 2>/dev/null || echo "")
if echo "$DEMO_TENANT" | grep -q '"slug":"demo"'; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

echo -n "X-Tenant-Slug header... "
# This would need the vertical to echo back the header, skipping for now
echo "○ SKIPPED (requires app support)"

echo ""

# ==========================================================================
# DATABASE CONNECTIVITY
# ==========================================================================
echo "--- Database Connectivity ---"

echo -n "Vertical → PostgreSQL... "
DB_TEST=$(docker exec local-construction python -c "
from sqlalchemy import create_engine, text
import os
try:
    e = create_engine(os.environ.get('DATABASE_URL', ''))
    with e.connect() as c:
        c.execute(text('SELECT 1'))
    print('OK')
except Exception as ex:
    print(f'FAIL: {ex}')
" 2>&1 || echo "CONTAINER_ERROR")

if [[ "$DB_TEST" == "OK" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED ($DB_TEST)"
    FAILED=1
fi

echo -n "Vertical → Redis... "
REDIS_TEST=$(docker exec local-construction python -c "
import redis
import os
try:
    r = redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379'))
    r.ping()
    print('OK')
except Exception as ex:
    print(f'FAIL: {ex}')
" 2>&1 || echo "CONTAINER_ERROR")

if [[ "$REDIS_TEST" == "OK" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED ($REDIS_TEST)"
    FAILED=1
fi

echo ""

# ==========================================================================
# RESOURCE USAGE
# ==========================================================================
echo "--- Resource Usage ---"
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
    local-postgres local-redis local-construction local-nginx local-auth 2>/dev/null || echo "Could not get stats"

echo ""

# ==========================================================================
# SUMMARY
# ==========================================================================
echo "=========================================="
if [[ $FAILED -eq 0 ]] && [[ $WARNINGS -eq 0 ]]; then
    echo "✓ All tests passed!"
    echo ""
    echo "Access the application:"
    echo "  - Dashboard: http://demo.localhost/web/dashboard"
    echo "  - API Docs:  http://localhost/docs"
    echo "  - Health:    http://localhost/health"
    exit 0
elif [[ $FAILED -eq 0 ]]; then
    echo "✓ Core tests passed with $WARNINGS warning(s)"
    echo ""
    echo "Access the application:"
    echo "  - Dashboard: http://demo.localhost/web/dashboard"
    echo "  - API Docs:  http://localhost/docs"
    exit 0
else
    echo "✗ $FAILED test(s) failed, $WARNINGS warning(s)"
    echo ""
    echo "Check logs with:"
    echo "  docker compose logs -f"
    exit 1
fi

