#!/bin/bash
# Smoke test for Droplet 1 - Edge
# Verifies nginx and auth service are running

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# Load env
if [[ -f .env ]]; then
    source .env
fi

echo "=== Droplet 1 Smoke Test ==="
echo ""

FAILED=0

# Test nginx container
echo -n "Nginx running... "
if docker compose ps nginx 2>/dev/null | grep -q "Up"; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test auth container
echo -n "Auth service running... "
if docker compose ps auth 2>/dev/null | grep -q "Up"; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test nginx config
echo -n "Nginx config valid... "
if docker exec basecommerce-nginx nginx -t 2>&1 | grep -q "successful"; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test health endpoint
echo -n "Health endpoint... "
HEALTH=$(curl -sf http://localhost/health 2>/dev/null || echo "")
if [[ -n "$HEALTH" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test auth service
echo -n "Auth health... "
AUTH_HEALTH=$(curl -sf http://localhost/auth/health 2>/dev/null || echo "")
if [[ -n "$AUTH_HEALTH" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test tenant.json
echo -n "Tenant JSON (default)... "
TENANT=$(curl -sf http://localhost/tenant.json 2>/dev/null || echo "")
if [[ -n "$TENANT" ]]; then
    echo "✓ OK"
else
    echo "✗ FAILED"
    FAILED=1
fi

# Test connection to Droplet 2
if [[ -n "${VERTICAL_HOST:-}" ]]; then
    echo -n "Droplet 2 connectivity... "
    if curl -sf "http://${VERTICAL_HOST}:8000/health" > /dev/null 2>&1; then
        echo "✓ OK"
    else
        echo "✗ FAILED (check if Droplet 2 is running)"
        FAILED=1
    fi
fi

# Test HTTPS endpoint (skip if certificates not configured)
echo -n "HTTPS endpoint... "
HTTPS_HEALTH=$(curl -k -sf https://localhost/health 2>/dev/null || echo "")
if [[ -n "$HTTPS_HEALTH" ]]; then
    echo "✓ OK"
    # Verify Strict-Transport-Security header
    echo -n "HTTPS HSTS header... "
    HSTS_HEADER=$(curl -k -sI https://localhost/health 2>/dev/null | grep -i "strict-transport-security" || echo "")
    if [[ -n "$HSTS_HEADER" ]]; then
        echo "✓ OK"
    else
        echo "⚠ WARNING (HSTS header missing)"
    fi
else
    echo "⚠ SKIPPED (certificates may not be configured - run 'basec ssl setup edge')"
fi

# Nginx status (internal only, 403 is expected from outside)
echo ""
echo "=== Nginx Status ==="
NGINX_STATUS=$(curl -s http://localhost/nginx-status 2>/dev/null || echo "")
if [[ -n "$NGINX_STATUS" ]] && ! echo "$NGINX_STATUS" | grep -q "403\|Forbidden"; then
    echo "$NGINX_STATUS"
else
    echo "Status endpoint is internal-only (403 expected from external access)"
fi

# Resource usage
echo ""
echo "=== Resource Usage ==="
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" basecommerce-nginx basecommerce-auth

echo ""
if [[ $FAILED -eq 0 ]]; then
    echo "=== All Tests Passed ✓ ==="
    exit 0
else
    echo "=== Some Tests Failed ✗ ==="
    exit 1
fi

