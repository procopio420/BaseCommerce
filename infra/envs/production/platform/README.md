# Production Platform

**Environment**: Production  
**Role**: Platform (PostgreSQL + Redis + Workers)  
**Location**: `infra/envs/production/platform/`

## Services

| Service | Port | Description |
|---------|------|-------------|
| PostgreSQL | 5432 | Primary database (multi-tenant) |
| Redis | 6379 | Event streams (Redis Streams) |
| Outbox Relay | - | DB → Redis event publisher |
| Engines Worker | - | Event consumer and processor |

## Ports

- **5432** (PostgreSQL) - Internal only, accessible from Edge and Verticals
- **6379** (Redis) - Internal only, accessible from Edge and Verticals

## Environment Variables

See `env.example` for required variables:

- `POSTGRES_PASSWORD` - Database password
- `POSTGRES_USER` - Database user (default: basecommerce)
- `POSTGRES_DB` - Database name (default: basecommerce)
- `REDIS_URL` - Redis connection string
- `DATABASE_URL` - PostgreSQL connection string

## Quick Start

```bash
# 1. Configure environment
cp env.example .env
nano .env  # Set POSTGRES_PASSWORD

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
basec deploy platform

# Logs
basec logs platform

# Status
basec status

# SSH
basec ssh platform

# Backups (via SSH)
basec ssh platform "cd /opt/basecommerce && ./scripts/backup-postgres.sh"
```

## Configuration Files

- `docker-compose.yml` - Service definitions
- `postgres/postgresql.conf` - PostgreSQL configuration
- `redis/redis.conf` - Redis configuration

## Backups

Backups are stored in `/opt/basecommerce/backups/` on the droplet with 7-day retention.
