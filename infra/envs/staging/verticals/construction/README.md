# Staging Vertical: Construction

**Environment**: Staging  
**Role**: Vertical (Construction App)  
**Location**: `infra/envs/staging/verticals/construction/`

## Services

| Service | Port | Description |
|---------|------|-------------|
| Construction | 8000 | FastAPI application with Gunicorn |

## Ports

- **8000** (App) - Internal only, accessible from Edge

## Environment Variables

See `env.example` for required variables:

- `INFRA_HOST` - Private IP of staging platform droplet
- `POSTGRES_PASSWORD` - Database password (staging database)
- `DATABASE_URL` - PostgreSQL connection string (staging)
- `REDIS_URL` - Redis connection string (staging)
- `SECRET_KEY` - Application secret key (use different from production)
- `ENVIRONMENT` - Set to `staging`

## Quick Start

```bash
# 1. Configure environment
cp env.example .env
nano .env  # Set INFRA_HOST, POSTGRES_PASSWORD, SECRET_KEY

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
basec deploy vertical --vertical construction --env staging

# Logs
basec logs vertical_construction --env staging

# Status
basec status --env staging

# SSH
basec ssh vertical_construction --env staging

# Migrations
basec migrate status --env staging
basec migrate apply --env staging
```

## Configuration Files

- `docker-compose.yml` - Service definitions

## Database Migrations

Migrations are managed via `basec migrate` commands. The Alembic configuration is in the application code.

## Differences from Production

- Connects to staging database
- Different SECRET_KEY
- Same application code, different environment
