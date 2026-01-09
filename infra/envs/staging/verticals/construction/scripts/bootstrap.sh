#!/bin/bash
# Bootstrap script for Droplet 2 - Construction Vertical
# Run once on fresh droplet

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== BaseCommerce Droplet 2 Bootstrap ==="
echo "This will set up the construction vertical droplet."
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
    echo "UFW configured. Add Edge droplet rule after creating Droplet 1:"
    echo "  sudo ufw allow from DROPLET_1_IP to any port 8000"
    echo "  sudo ufw enable"

    echo "[4/4] System setup complete."
    echo ""
    echo "Next steps (as regular user):"
    echo "  1. cd $PROJECT_DIR"
    echo "  2. cp env.example .env"
    echo "  3. Edit .env with infrastructure host and secrets"
    echo "  4. docker compose up -d"
    exit 0
fi

# Non-root setup
cd "$PROJECT_DIR"

echo "[1/4] Checking environment file..."
if [[ ! -f .env ]]; then
    if [[ -f env.example ]]; then
        cp env.example .env
        echo ".env created from env.example"
        echo "IMPORTANT: Edit .env and configure:"
        echo "  - INFRA_HOST (Droplet 3 private IP)"
        echo "  - POSTGRES_PASSWORD (same as Droplet 3)"
        echo "  - SECRET_KEY (generate new random key)"
        exit 1
    else
        echo "ERROR: env.example not found"
        exit 1
    fi
fi

echo "[2/4] Validating environment..."
source .env
if [[ -z "${INFRA_HOST:-}" ]]; then
    echo "ERROR: INFRA_HOST not set"
    exit 1
fi
if [[ "${SECRET_KEY:-}" == *"CHANGE_ME"* ]] || [[ -z "${SECRET_KEY:-}" ]]; then
    echo "ERROR: SECRET_KEY not set or still default value"
    exit 1
fi

echo "[3/4] Testing connectivity to Droplet 3..."
if timeout 5 bash -c "echo >/dev/tcp/${INFRA_HOST}/5432" 2>/dev/null; then
    echo "✓ PostgreSQL reachable at ${INFRA_HOST}:5432"
else
    echo "⚠ Cannot reach PostgreSQL at ${INFRA_HOST}:5432"
    echo "  Make sure Droplet 3 is running and UFW allows this IP"
fi

echo "[4/4] Building Docker image..."
docker compose build

echo ""
echo "=== Bootstrap Complete ==="
echo "Start services with: docker compose up -d"
echo "Verify with: ./scripts/smoke-test.sh"

