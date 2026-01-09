# Staging Edge

**Environment**: Staging  
**Role**: Edge (Nginx + Auth)  
**Location**: `infra/envs/staging/edge/`

## Services

| Service | Port | Description |
|---------|------|-------------|
| Nginx | 80 | Reverse proxy, multi-tenant routing |
| Auth | 8001 | Authentication service |

## Ports

- **80** (HTTP) - Public, via Cloudflare
- **8001** (Auth) - Internal only

## Environment Variables

See `env.example` for required variables:

- `VERTICAL_HOST` - Private IP of staging vertical droplet
- `SECRET_KEY` - JWT secret key (use different from production)
- `DATABASE_URL` - PostgreSQL connection string (staging database)
- `ENVIRONMENT` - Set to `staging`

## Quick Start

```bash
# 1. Configure environment
cp env.example .env
nano .env  # Set VERTICAL_HOST, SECRET_KEY, DATABASE_URL

# 2. Bootstrap (first time)
sudo ./scripts/bootstrap.sh

# 3. Start services
docker compose up -d

# 4. Verify
./scripts/smoke-test.sh
```

## Operations

Use `basec` CLI for operations:

```bash
# Deploy
basec deploy edge --env staging

# Logs
basec logs edge --env staging

# Status
basec status --env staging

# SSH
basec ssh edge --env staging
```

## Configuration Files

- `docker-compose.yml` - Service definitions
- `nginx/nginx.conf` - Main nginx config
- `nginx/conf.d/default.conf` - Server blocks
- `nginx/tenants/` - Tenant-specific JSON files

## Differences from Production

- Uses staging database
- Different SECRET_KEY
- May use different domain/subdomain
- Same architecture, different environment variables
