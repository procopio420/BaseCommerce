# Deployment Guide

## Overview

BaseCommerce uses a 3-droplet VPS architecture (~$24/month):

| Droplet | Function | Cost |
|---------|----------|------|
| Edge | Nginx + Auth | $6/mo |
| Vertical | Construction App | $6/mo |
| Infra | PostgreSQL + Redis + Workers | $12/mo |

**Complete infrastructure documentation:** See `infra/README.md`

## Quick Start

### Local Development

```bash
cd infra/envs/development/local
docker compose up -d
./smoke-test.sh

# Access
open http://demo.localhost/web/dashboard
open http://localhost/docs
```

### Production

Follow the complete guide in `infra/README.md`. Summary:

1. Create 3 DigitalOcean droplets with VPC
2. Configure Cloudflare DNS
3. Deploy in order: Droplet 3 → 2 → 1

```bash
# On each droplet
git clone <repo>
cd basecommerce/infra/envs/production/<role>
sudo ./scripts/bootstrap.sh
cp env.example .env && nano .env
docker compose up -d
./scripts/smoke-test.sh
```

**Or use the CLI `basec`:**

```bash
# Deploy via CLI (recommended)
basec deploy all
basec smoke
```

## Database Migrations

```bash
cd apps/verticals/construction

# Create new migration
PYTHONPATH=src alembic revision --autogenerate -m "description"

# Apply migrations
PYTHONPATH=src alembic upgrade head

# Revert last migration
PYTHONPATH=src alembic downgrade -1
```

## First Tenant and User

```python
# Execute inside container or with PYTHONPATH=src
from sqlalchemy.orm import Session
from auth_app.models import Tenant, User
from auth_app.core.database import SessionLocal
from basecore.security import get_password_hash

db = SessionLocal()

# Create tenant
tenant = Tenant(
    nome='Example Store',
    slug='exemplo',  # access via exemplo.basecommerce.com.br
    cnpj='12.345.678/0001-90',
    email='store@exemplo.com',
    ativo=True
)
db.add(tenant)
db.commit()

# Create admin user
user = User(
    tenant_id=tenant.id,
    nome='Admin',
    email='admin@exemplo.com',
    password_hash=get_password_hash('senha123'),
    role='admin',
    ativo=True
)
db.add(user)
db.commit()

print(f'Access: https://{tenant.slug}.basecommerce.com.br')
print(f'Login: {user.email} / senha123')
```

## Security

- **NEVER** commit `.env` with real credentials
- Use strong passwords for production
- Cloudflare manages HTTPS (Full/Strict)
- Configure cookies as `secure=True` in production
- Redis and PostgreSQL only accessible via VPC

## Reference Files

| File | Description |
|------|-------------|
| `infra/README.md` | Complete infrastructure guide |
| `infra/topology.md` | Architecture decisions and scaling |
| `infra/envs/production/edge/` | Edge/Nginx configuration (production) |
| `infra/envs/production/verticals/construction/` | Vertical configuration (production) |
| `infra/envs/production/platform/` | DB/Redis configuration (production) |
| `infra/envs/development/local/` | Local development environment |
| `infra/envs/README.md` | Environment structure |
