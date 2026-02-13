# Development Setup

## Quick Start (Docker Compose)

```bash
# Start all services
cd infra/envs/development/local
docker compose up -d

# Run migrations
docker compose exec construction alembic upgrade head

# Access local tenant
open http://demo.localhost/web/login
```

Add to `/etc/hosts`:
```
127.0.0.1 demo.localhost
```

## Manual Setup (Without Docker)

### 1. Environment Configuration

#### Construction Vertical

1. Navigate to vertical directory:
```bash
cd apps/verticals/construction
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt

# Install shared packages
pip install -e ../../../packages/basecore
pip install -e ../../../packages/engines_core
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your settings:
# - DATABASE_URL
# - SECRET_KEY (generate random key)
# - REDIS_URL
```

### 2. Database and Redis Configuration

#### Option A: Docker (Recommended)

1. Use docker-compose to start PostgreSQL and Redis:
```bash
# At project root
docker-compose up -d db redis
```

#### Option B: Local PostgreSQL and Redis

1. Install PostgreSQL 15+ and Redis 7+
2. Create database:
```sql
CREATE DATABASE basecommerce_db;
CREATE USER basecommerce_user WITH PASSWORD 'basecommerce_pass';
GRANT ALL PRIVILEGES ON DATABASE basecommerce_db TO basecommerce_user;
```

3. Configure variables in .env:
```
DATABASE_URL=postgresql://basecommerce_user:basecommerce_pass@localhost:5432/basecommerce_db
REDIS_URL=redis://localhost:6379/0
```

### 3. Run Migrations

1. In vertical directory:
```bash
cd apps/verticals/construction
PYTHONPATH=src alembic upgrade head
```

This creates all necessary tables in the database.

### 4. Create First Tenant and User

Execute script to create tenant, branding, and initial user:

```bash
cd apps/verticals/construction
PYTHONPATH=src python -c "
from sqlalchemy.orm import Session
from auth_app.models import Tenant, TenantBranding, User
from auth_app.core.database import SessionLocal
from basecore.security import get_password_hash

db = SessionLocal()

# Create tenant with slug (used in subdomain)
tenant = Tenant(
    nome='Example Store',
    slug='exemplo',  # For local dev, access via exemplo.localhost:8000
    cnpj='12.345.678/0001-90',
    email='store@exemplo.com',
    telefone='(24) 1234-5678',
    ativo=True
)
db.add(tenant)
db.commit()
db.refresh(tenant)

# Create branding (optional)
branding = TenantBranding(
    tenant_id=tenant.id,
    logo_url=None,  # Logo URL or None
    primary_color='#1a73e8',
    secondary_color='#ea4335',
    feature_flags={}
)
db.add(branding)
db.commit()

# Create admin user
user = User(
    tenant_id=tenant.id,
    nome='Administrator',
    email='admin@exemplo.com',
    password_hash=get_password_hash('senha123'),
    role='admin',
    ativo=True
)
db.add(user)
db.commit()

print(f'Tenant created: {tenant.nome} (slug: {tenant.slug})')
print(f'User created: {user.email}')
print(f'Password: senha123')
"
```

### 5. Start Server

```bash
cd apps/verticals/construction
PYTHONPATH=src uvicorn construction_app.main:app --reload
```

Server available at: http://localhost:8000

### 6. First Access

#### Local Development

For local development, access directly:
- http://localhost:8000/web/login

System works without subdomain in development mode.

#### With Subdomain (Optional)

To test with local subdomain, add to `/etc/hosts`:
```
127.0.0.1 exemplo.localhost
```

Access:
- http://exemplo.localhost:8000/web/login

#### Credentials

Login with:
- Email: admin@exemplo.com
- Password: senha123

## Troubleshooting

### Database Connection Error

- Verify PostgreSQL is running
- Verify DATABASE_URL is correct
- Verify user has permissions

### Redis Connection Error

- Verify Redis is running
- Verify REDIS_URL is correct

### Migration Error

- Ensure database is empty or using test database
- Verify all dependencies are installed

### Authentication Error

- Verify SECRET_KEY is configured
- Verify `access_token` cookie is being sent
- In production, verify `secure` cookies and HTTPS are configured

### Tenant Not Found

- Verify tenant exists with correct slug
- Verify tenant is active (`ativo=True`)
- For local dev without subdomain, system works normally

### Import Error (ModuleNotFoundError)

- Ensure PYTHONPATH includes `src` directory:
```bash
export PYTHONPATH=src
# or
PYTHONPATH=src uvicorn construction_app.main:app --reload
```
