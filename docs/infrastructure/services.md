# Infrastructure Services

## Overview

The platform runs on VPS (DigitalOcean droplets) without Kubernetes or serverless.

## Components

### PostgreSQL

- Version: 15+
- Multi-tenant: all tables have `tenant_id`
- Can be managed (DO Managed Database) or self-hosted

### Redis

- Version: 7+
- Uses:
  - Redis Streams for events (event bus)
  - Session cache (future)
- Append-only enabled for persistence

### Nginx

- Multi-tenant reverse proxy
- Resolves tenant via subdomain
- Injects `X-Tenant-Slug` header
- Configuration: `infra/nginx/nginx.conf`

### Droplets (Deployment Architecture)

```
┌─────────────────┐     ┌─────────────────┐
│   Nginx         │     │   PostgreSQL    │
│   (1 droplet)   │     │   (1 droplet    │
│   or integrated │     │    or managed)  │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       │
┌─────────────────┐              │
│  Construction   │◄─────────────┘
│  Vertical       │              │
│  (1 droplet)    │◄─────────────┤
└────────┬────────┘              │
         │                       │
         ▼                       │
┌─────────────────┐              │
│  Engines Worker │◄─────────────┘
│  (1 droplet     │
│   or same)      │
└─────────────────┘
```

## Minimum Configuration (Development)

A single droplet can run all services:

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (port 5432)
- Redis (port 6379)
- Nginx (port 80)
- Construction vertical (port 8000)
- Outbox Relay
- Engines Worker

## Production Configuration

### Droplet for Vertical (4GB+ RAM)

```bash
docker run -d -p 8000:8000 \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  -e SECRET_KEY=... \
  basecommerce-construction
```

### Droplet for Engines (2GB+ RAM)

```bash
docker run -d \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  -e SECRET_KEY=... \
  basecommerce-engines
```

### Nginx (On vertical droplet or separate)

See `infra/nginx/nginx.conf` for complete configuration.

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| DATABASE_URL | PostgreSQL connection string | postgresql://user:pass@host:5432/db |
| REDIS_URL | Redis connection string | redis://host:6379/0 |
| SECRET_KEY | JWT key | (generate randomly) |
| ALGORITHM | JWT algorithm | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Token expiration | 1440 |
| CORS_ORIGINS | Allowed origins | http://localhost |

## Monitoring

### Logs

- Vertical: container stdout (docker logs)
- Nginx: `/var/log/nginx/access.log` and `error.log`
- PostgreSQL: container logs or managed service logs

### Health Checks

- Vertical: `GET /health` → `{"status": "ok"}`
- Engines: event processing logs

### Metrics (Future)

- Prometheus + Grafana
- Events processed metrics
- Endpoint response times
