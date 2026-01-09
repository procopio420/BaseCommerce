# Guia de Deploy

## Visão Geral

BaseCommerce usa uma arquitetura de 3 droplets VPS (~$24/mês):

| Droplet | Função | Custo |
|---------|--------|-------|
| Edge | Nginx + Auth | $6/mo |
| Vertical | Construction App | $6/mo |
| Infra | PostgreSQL + Redis + Workers | $12/mo |

**Documentação completa de infraestrutura:** [`infra/README.md`](../infra/README.md)

## Quick Start

### Desenvolvimento Local

```bash
cd infra/envs/development/local
docker compose up -d
./smoke-test.sh

# Acesse
open http://demo.localhost/web/dashboard
open http://localhost/docs
```

### Produção

Siga o guia completo em [`infra/README.md`](../infra/README.md). Resumo:

1. Crie 3 droplets DigitalOcean com VPC
2. Configure Cloudflare DNS
3. Deploy na ordem: Droplet 3 → 2 → 1

```bash
# Em cada droplet
git clone <repo>
cd basecommerce/infra/envs/production/<role>
sudo ./scripts/bootstrap.sh
cp env.example .env && nano .env
docker compose up -d
./scripts/smoke-test.sh
```

**Ou use o CLI `basec`:**

```bash
# Deploy via CLI (recomendado)
basec deploy all
basec smoke
```

## Desenvolvimento Local (Sem Docker)

### Backend (Vertical Construction)

```bash
cd apps/verticals/construction
python -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install -e ../../../packages/basecore
pip install -e ../../../packages/engines_core

# Configure .env
DATABASE_URL=postgresql://user:pass@localhost:5432/basecommerce_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=dev-secret-key

# Migrations
PYTHONPATH=src alembic upgrade head

# Servidor
PYTHONPATH=src uvicorn construction_app.main:app --reload
```

## Migrações do Banco de Dados

```bash
cd apps/verticals/construction

# Criar nova migração
PYTHONPATH=src alembic revision --autogenerate -m "descrição"

# Aplicar migrações
PYTHONPATH=src alembic upgrade head

# Reverter última migração
PYTHONPATH=src alembic downgrade -1
```

## Primeiro Tenant e Usuário

```python
# Execute dentro do container ou com PYTHONPATH=src
from sqlalchemy.orm import Session
from construction_app.core.database import SessionLocal
from construction_app.core.security import get_password_hash
from construction_app.models.tenant import Tenant
from construction_app.models.user import User

db = SessionLocal()

# Criar tenant
tenant = Tenant(
    nome='Loja Exemplo',
    slug='exemplo',  # acesse via exemplo.basecommerce.com.br
    cnpj='12.345.678/0001-90',
    email='loja@exemplo.com',
    ativo=True
)
db.add(tenant)
db.commit()

# Criar usuário admin
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

print(f'Acesse: https://{tenant.slug}.basecommerce.com.br')
print(f'Login: {user.email} / senha123')
```

## Segurança

- **NUNCA** commite `.env` com credenciais reais
- Use senhas fortes para produção
- Cloudflare gerencia HTTPS (Full/Strict)
- Configure cookies como `secure=True` em produção
- Redis e PostgreSQL só acessíveis via VPC

## Arquivos de Referência

| Arquivo | Descrição |
|---------|-----------|
| [`infra/README.md`](../infra/README.md) | Guia completo de infraestrutura |
| [`infra/topology.md`](../infra/topology.md) | Decisões de arquitetura e scaling |
| [`infra/envs/production/edge/`](../infra/envs/production/edge/) | Configuração do Edge/Nginx (production) |
| [`infra/envs/production/verticals/construction/`](../infra/envs/production/verticals/construction/) | Configuração do Vertical (production) |
| [`infra/envs/production/platform/`](../infra/envs/production/platform/) | Configuração de DB/Redis (production) |
| [`infra/envs/development/local/`](../infra/envs/development/local/) | Ambiente local de desenvolvimento |
| [`infra/envs/README.md`](../infra/envs/README.md) | Estrutura de ambientes |
