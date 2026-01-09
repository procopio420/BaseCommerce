# Development: Local

**Environment**: Development  
**Type**: Local (simulates all 3 droplets in one)  
**Location**: `infra/envs/development/local/`

## Services

This environment simulates the entire production stack locally using Docker Compose:

- **Nginx** - Edge reverse proxy
- **Auth** - Authentication service
- **Construction** - Construction vertical app
- **PostgreSQL** - Database
- **Redis** - Event streams

## Ports

- **80** (HTTP) - Access via `*.localhost` subdomains
- **8000** (Construction) - Direct access
- **8001** (Auth) - Direct access
- **5432** (PostgreSQL) - Direct access
- **6379** (Redis) - Direct access

## Quick Start

```bash
# 1. Start all services
docker compose up -d

# 2. Verify
./smoke-test.sh

# 3. Access
open http://demo.localhost/web/dashboard
```

## Usage

Access applications via subdomain:

- `http://demo.localhost` - Demo tenant
- `http://localhost` - Default (no tenant)

## Environment Variables

All services use default development values. See `docker-compose.yml` for configuration.

## Operations

```bash
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f

# Restart
docker compose restart
```

## Differences from Production

- All services run on one machine
- No SSH required
- Simplified networking
- Development secrets (not for production)
- No UFW/firewall configuration needed
