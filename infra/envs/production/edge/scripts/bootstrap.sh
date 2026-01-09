#!/bin/bash
# Bootstrap script for Droplet 1 - Edge
# Run once on fresh droplet

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== BaseCommerce Droplet 1 Bootstrap ==="
echo "This will set up the edge/nginx droplet."
echo ""

# Check if running as root for system setup
if [[ $EUID -eq 0 ]]; then
    echo "[1/4] Installing Docker..."
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
    else
        echo "Docker already installed."
    fi

    echo "[2/4] Installing Docker Compose..."
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        apt-get update
        apt-get install -y docker-compose-plugin
    else
        echo "Docker Compose already installed."
    fi

    echo "[3/4] Configuring UFW..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp
    ufw allow 80/tcp
    ufw allow 443/tcp  # HTTPS (443) - Required for Cloudflare Full (strict) mode
    echo "UFW configured for edge droplet."

    echo "[4/4] System setup complete."
    echo ""
    echo "Next steps (as regular user):"
    echo "  1. cd $PROJECT_DIR"
    echo "  2. cp env.example .env"
    echo "  3. Edit .env with VERTICAL_HOST and SECRET_KEY"
    echo "  4. docker compose up -d"
    exit 0
fi

# Non-root setup
cd "$PROJECT_DIR"

echo "[1/5] Checking environment file..."
if [[ ! -f .env ]]; then
    if [[ -f env.example ]]; then
        cp env.example .env
        echo ".env created from env.example"
        echo "IMPORTANT: Edit .env and configure:"
        echo "  - VERTICAL_HOST (Droplet 2 private IP)"
        echo "  - SECRET_KEY (generate new random key)"
        exit 1
    else
        echo "ERROR: env.example not found"
        exit 1
    fi
fi

echo "[2/5] Validating environment..."
source .env
if [[ -z "${VERTICAL_HOST:-}" ]]; then
    echo "ERROR: VERTICAL_HOST not set"
    exit 1
fi
if [[ "${SECRET_KEY:-}" == *"CHANGE_ME"* ]] || [[ -z "${SECRET_KEY:-}" ]]; then
    echo "ERROR: SECRET_KEY not set or still default value"
    exit 1
fi

echo "[3/5] Checking nginx template..."
if grep -q 'VERTICAL_IP_HERE' nginx/templates/default.conf.template; then
    echo "WARNING: nginx template still has VERTICAL_IP_HERE placeholder"
    echo "Template should use \${VERTICAL_HOST} syntax (already fixed in current version)"
elif ! grep -q '\${VERTICAL_HOST}' nginx/templates/default.conf.template; then
    echo "WARNING: nginx template missing \${VERTICAL_HOST} placeholder"
    echo "Template should use \${VERTICAL_HOST} for environment variable substitution"
fi

echo "[4/5] Testing connectivity to Droplet 2..."
if curl -sf "http://${VERTICAL_HOST}:8000/health" > /dev/null 2>&1; then
    echo "✓ Droplet 2 reachable at ${VERTICAL_HOST}:8000"
else
    echo "⚠ Cannot reach Droplet 2 at ${VERTICAL_HOST}:8000"
    echo "  Make sure Droplet 2 is running and allows connections from this IP"
fi

echo "[5/5] Testing nginx config..."
docker compose run --rm nginx nginx -t

echo ""
echo "=== Bootstrap Complete ==="
echo "Start services with: docker compose up -d"
echo "Verify with: ./scripts/smoke-test.sh"

