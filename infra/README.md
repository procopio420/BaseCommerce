# BaseCommerce Infrastructure

Infrastructure as Code for the BaseCommerce platform.

## Overview

The platform runs on 3 DigitalOcean droplets with a total cost of ~$24/month:

| Droplet | Purpose | Spec | Cost |
|---------|---------|------|------|
| **Edge** | Nginx + Auth | 1GB, 1vCPU | $6/mo |
| **Vertical** | Construction app | 1GB, 1vCPU | $6/mo |
| **Infra** | PostgreSQL + Redis + Workers | 2GB, 1vCPU | $12/mo |

## Architecture

```
                         INTERNET
                            │
                            ▼
                    ┌───────────────┐
                    │   CLOUDFLARE  │
                    │   (TLS/CDN)   │
                    └───────┬───────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                    DROPLET 1 - EDGE                           │
│                                                               │
│   ┌─────────────┐        ┌─────────────┐                     │
│   │    Nginx    │───────▶│    Auth     │                     │
│   │    (:80)    │        │   (:8001)   │                     │
│   └──────┬──────┘        └─────────────┘                     │
│          │                                                    │
│          │ X-Tenant-Slug header                              │
└──────────┼────────────────────────────────────────────────────┘
           │
           ▼
┌───────────────────────────────────────────────────────────────┐
│                  DROPLET 2 - VERTICAL                         │
│                                                               │
│   ┌─────────────────────────────────────────────────────┐    │
│   │              Construction App                        │    │
│   │              FastAPI + HTMX                         │    │
│   │              (:8000)                                │    │
│   └─────────────────────────┬───────────────────────────┘    │
│                             │                                 │
└─────────────────────────────┼─────────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                   DROPLET 3 - INFRA                           │
│                                                               │
│   ┌──────────────┐    ┌──────────────┐                       │
│   │  PostgreSQL  │    │    Redis     │                       │
│   │   (:5432)    │    │   (:6379)    │                       │
│   └──────┬───────┘    └──────┬───────┘                       │
│          │                   │                                │
│          │    ┌──────────────┼──────────────┐                │
│          │    │              │              │                │
│          ▼    ▼              ▼              ▼                │
│   ┌─────────────────┐  ┌─────────────────────┐              │
│   │  Outbox Relay   │  │   Engines Worker    │              │
│   └─────────────────┘  └─────────────────────┘              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
infra/
├── README.md                  # This file
├── topology.md                # Detailed architecture decisions
├── inventory.yaml             # Infrastructure inventory (source of truth)
├── deploy_key                 # SSH key for deployments
│
├── envs/                      # Environment-specific configurations
│   ├── production/            # Production environment
│   │   ├── edge/              # Nginx + Auth
│   │   ├── platform/          # PostgreSQL + Redis + Workers
│   │   └── verticals/         # Vertical applications
│   │       └── construction/  # Construction vertical
│   ├── staging/               # Staging environment (same topology as production)
│   │   ├── edge/
│   │   ├── platform/
│   │   └── verticals/
│   │       └── construction/
│   └── development/           # Development environments
│       └── local/              # Local development (simulates 3 droplets)
│
├── cli/                       # BaseCommerce CLI (basec)
│   └── basec/                 # CLI implementation
│
└── docs/                      # Documentation
    ├── ci-cd.md              # CI/CD documentation
    ├── infra-cli.md
    ├── migration-matrix.md
    └── MIGRATION-COMPLETE.md
```

## Environments

The infrastructure supports multiple environments:

| Environment | Purpose | Location |
|-------------|---------|----------|
| **production** | Live production environment | `envs/production/` |
| **staging** | Pre-production testing | `envs/staging/` |
| **development** | Local development | `envs/development/local/` |

Each environment has the same structure:
- `edge/` - Nginx + Auth service
- `platform/` - PostgreSQL + Redis + Workers
- `verticals/<name>/` - Vertical applications

### Using Different Environments

The CLI `basec` supports `--env` flag for all commands:

```bash
# Production (default)
basec status
basec deploy edge

# Staging
basec status --env staging
basec deploy edge --env staging
basec smoke --env staging

# Development (local Docker Compose)
cd infra/envs/development/local
docker compose up -d
```

See [envs/README.md](envs/README.md) for detailed environment documentation.

## Deployment Order

Always deploy in this order:

1. **Droplet 3 (Infra)** - Database and Redis must be available first
2. **Droplet 2 (Vertical)** - Connects to Droplet 3
3. **Droplet 1 (Edge)** - Routes traffic to Droplet 2

## Infrastructure CLI

**⚠️ IMPORTANTE**: Todos os scripts bash foram substituídos pelo CLI Python `basec`.

### Instalação do CLI

```bash
cd infra/cli
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Uso Rápido

```bash
# Status de todos os droplets
basec status

# Smoke tests
basec smoke

# Deploy
basec deploy all

# Logs
basec logs edge nginx --follow

# SSH
basec ssh edge

# Migrations
basec migrate status
basec migrate apply
```

**Documentação completa**: Veja [docs/infra-cli.md](docs/infra-cli.md)

## CI/CD

BaseCommerce usa GitHub Actions para CI/CD completo:

- **PR Checks**: Valida código (lint, tests, build) em pull requests
- **Deploy Staging**: Deploy automático ao push em `develop`
- **Deploy Production**: Deploy automático ao push em `main` com rollback automático

**Imagens Docker**: Publicadas no GHCR (`ghcr.io/procopio420/basecommerce`)

**Deploy via CLI**: Todos os deploys usam `basec deploy` com versionamento por tags SHA.

**Documentação completa**: Veja [docs/ci-cd.md](docs/ci-cd.md)

### Quick Deploy via CI/CD

```bash
# Deploy automático para staging
git push origin develop

# Deploy automático para production
git push origin main

# Deploy manual via GitHub Actions UI
# Actions → Deploy Staging/Production → Run workflow
```

## Quick Deploy Guide

### Prerequisites

1. Create 3 DigitalOcean droplets with private networking enabled
2. Configure Cloudflare DNS:
   - A record: `*.basecommerce.com.br` → Droplet 1 public IP
   - SSL mode: **Flexible** (permite HTTP no servidor, HTTPS no Cloudflare)
   - ⚠️ Para usar "Full (strict)", configure SSL no nginx primeiro (veja edge/CLOUDFLARE_FIX.md)

### Droplet 3 (Infra)

```bash
# SSH into droplet
ssh root@DROPLET_3_IP

# Clone repo
git clone https://github.com/yourrepo/basecommerce.git
cd basecommerce/infra/envs/production/platform

# Run bootstrap as root
sudo ./scripts/bootstrap.sh

# Configure and start
cp env.example .env
nano .env  # Set POSTGRES_PASSWORD
docker compose up -d
./scripts/smoke-test.sh
```

### Droplet 2 (Vertical)

```bash
ssh root@DROPLET_2_IP

git clone https://github.com/yourrepo/basecommerce.git
cd basecommerce/infra/envs/production/verticals/construction

sudo ./scripts/bootstrap.sh

cp env.example .env
nano .env  # Set INFRA_HOST, POSTGRES_PASSWORD, SECRET_KEY
docker compose up -d
./scripts/smoke-test.sh
```

### Droplet 1 (Edge)

```bash
ssh root@DROPLET_1_IP

git clone https://github.com/yourrepo/basecommerce.git
cd basecommerce/infra/envs/production/edge

sudo ./scripts/bootstrap.sh

cp env.example .env
nano .env  # Set VERTICAL_HOST, SECRET_KEY

# Update nginx config with actual IP
sed -i 's/${VERTICAL_HOST}/10.0.0.2/g' nginx/conf.d/default.conf

docker compose up -d
./scripts/smoke-test.sh
```

## Security

### Firewall (UFW)

| Droplet | Open Ports |
|---------|------------|
| Edge | 22 (SSH), 80 (HTTP) |
| Vertical | 22 (SSH), 8000 (internal only) |
| Infra | 22 (SSH), 5432 + 6379 (internal only) |

### Network Isolation

- Use DigitalOcean VPC for internal communication
- Only Droplet 1 (Edge) is publicly accessible
- All internal traffic uses private IPs

### TLS

- Cloudflare handles TLS termination
- Internal traffic between droplets is unencrypted (VPC)
- Consider Tailscale/WireGuard for additional security

## Monitoring

Use o CLI `basec` para monitoramento:

```bash
# Status de todos os droplets
basec status

# Logs em tempo real
basec logs edge nginx --follow
basec logs platform postgres --follow

# Smoke tests
basec smoke
```

Ou manualmente em cada droplet:

```bash
# On each droplet
docker compose ps
docker stats
docker compose logs -f
```

## Backups

Backups são executados via SSH no Droplet 3 (scripts locais nos droplets):

```bash
# Manual backup via CLI
basec ssh platform "cd /opt/basecommerce && ./scripts/backup-postgres.sh"

# Restore via CLI
basec ssh platform "cd /opt/basecommerce && ./scripts/restore-postgres.sh backup-2024-01-01.sql.gz"
```

**Nota**: Os scripts `backup-postgres.sh` e `restore-postgres.sh` são scripts locais nos droplets (em `/opt/basecommerce/scripts/`), não fazem parte do CLI.

Backups are stored in `./backups/` with 7-day retention.

## Scaling

See [topology.md](topology.md) for detailed scaling guidance.

| Bottleneck | Solution |
|------------|----------|
| Database connections | Add PgBouncer |
| Database performance | Upgrade Droplet 3 to 4GB |
| Web traffic | Add second Edge droplet + load balancer |
| Background processing | Add second Engines Worker |

## Local Development

```bash
cd infra/envs/development/local
docker compose up -d
./smoke-test.sh

# Access
open http://demo.localhost/web/dashboard
```

