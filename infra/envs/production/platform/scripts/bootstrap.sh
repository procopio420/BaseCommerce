#!/bin/bash
# Bootstrap script for Droplet 3 - Shared Infrastructure
# Run once on fresh droplet

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== BaseCommerce Droplet 3 Bootstrap ==="
echo "This will set up the shared infrastructure droplet."
echo ""

# Check if running as root for system setup
if [[ $EUID -eq 0 ]]; then
    echo "[1/5] Installing Docker..."
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
    else
        echo "Docker already installed."
    fi

    echo "[2/5] Installing Docker Compose..."
    if ! command -v docker &> /dev/null || ! docker compose version &> /dev/null; then
        apt-get update
        apt-get install -y docker-compose-plugin
    else
        echo "Docker Compose already installed."
    fi

    echo "[3/5] Configuring UFW..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp
    # Note: Add rules for droplet-2 IP after it's created
    echo "UFW configured. Add PostgreSQL/Redis rules after creating Droplet 2:"
    echo "  sudo ufw allow from DROPLET_2_IP to any port 5432"
    echo "  sudo ufw allow from DROPLET_2_IP to any port 6379"
    echo "  sudo ufw enable"

    echo "[4/5] Creating directories..."
    mkdir -p "$PROJECT_DIR/backups"
    chmod 700 "$PROJECT_DIR/backups"

    echo "[5/5] System setup complete."
    echo ""
    echo "Next steps (as regular user):"
    echo "  1. cd $PROJECT_DIR"
    echo "  2. cp .env.example .env"
    echo "  3. Edit .env with secure passwords"
    echo "  4. docker compose up -d"
    exit 0
fi

# Non-root setup
cd "$PROJECT_DIR"

echo "[1/4] Checking environment file..."
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
        echo ".env created from .env.example"
        echo "IMPORTANT: Edit .env and set secure passwords!"
        exit 1
    else
        echo "ERROR: .env.example not found"
        exit 1
    fi
fi

echo "[2/4] Validating environment..."
source .env
if [[ "${POSTGRES_PASSWORD:-}" == "CHANGE_ME_STRONG_PASSWORD" ]] || [[ -z "${POSTGRES_PASSWORD:-}" ]]; then
    echo "ERROR: POSTGRES_PASSWORD not set or still default value"
    echo "Edit .env and set a secure password"
    exit 1
fi

echo "[3/4] Creating backup directory..."
mkdir -p backups

echo "[4/4] Pulling Docker images..."
docker compose pull

echo ""
echo "=== Bootstrap Complete ==="
echo "Start services with: docker compose up -d"
echo "Verify with: ./scripts/smoke-test.sh"

