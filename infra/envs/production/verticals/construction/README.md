# Production Vertical: Construction

**Environment**: Production  
**Role**: Vertical (Construction App)  
**Location**: `infra/envs/production/verticals/construction/`

## Services

| Service | Port | Description |
|---------|------|-------------|
| Construction | 8000 | FastAPI application with Gunicorn |

## Ports

- **8000** (App) - Internal only, accessible from Edge

## Environment Variables

See `env.example` for required variables:

- `INFRA_HOST` - Private IP of platform droplet
- `POSTGRES_PASSWORD` - Database password
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - Application secret key
- `ENVIRONMENT` - Set to `production`

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
basec deploy vertical --vertical construction

# Logs
basec logs vertical_construction

# Status
basec status

# SSH
basec ssh vertical_construction

# Migrations
basec migrate status
basec migrate apply
```

## Configuration Files

- `docker-compose.yml` - Service definitions

## Database Migrations

Migrations are managed via `basec migrate` commands. The Alembic configuration is in the application code.
