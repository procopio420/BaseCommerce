# Multi-Tenancy

## Estrategia

**Subdomain-based multi-tenancy** com dados isolados por `tenant_id` em todas as tabelas.

## Arquitetura Centralizada

O Auth Service e o owner dos modelos de Tenant, User e TenantBranding. Os verticais (ex: Construction) nao tem esses modelos - usam apenas os claims do JWT.

```
┌─────────────────────────────────────────────────────────────────┐
│                         Auth Service                             │
│                                                                  │
│  Modelos:                      Endpoints:                        │
│  - Tenant                      - /auth/login                     │
│  - User                        - /tenant.json                    │
│  - TenantBranding              - /auth/me                        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 │ JWT com claims:
                                 │ - sub (user_id)
                                 │ - tenant_id
                                 │ - email
                                 │ - role
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Vertical                                 │
│                                                                  │
│  Extrai UserClaims do JWT (sem query ao banco)                   │
│  Todas as queries usam tenant_id do JWT                          │
└─────────────────────────────────────────────────────────────────┘
```

## Fluxo de Resolucao

```
1. Usuario acessa: lojadoze.basecommerce.com.br
                              │
                              ▼
2. Nginx extrai subdomain: lojadoze
                              │
                              ▼
3. Nginx injeta header: X-Tenant-Slug: lojadoze
                              │
                              ▼
4. Se nao autenticado, redireciona para /auth/login
                              │
                              ▼
5. Auth Service busca tenant no banco por slug
                              │
                              ▼
6. Auth Service cria JWT com tenant_id nos claims
                              │
                              ▼
7. Vertical extrai tenant_id do JWT
                              │
                              ▼
8. Todas as queries filtram por tenant_id
```

## Configuracao Nginx

```nginx
# Extrai tenant do subdomain
map $host $tenant_slug {
    ~^(?<subdomain>[^.]+)\.basecommerce\.com\.br$ $subdomain;
    ~^(?<subdomain>[^.]+)\.localhost$ $subdomain;
    default "";
}

server {
    listen 80;
    server_name *.basecommerce.com.br *.localhost localhost;
    
    # Tenant JSON servido pelo Auth Service
    location = /tenant.json {
        proxy_pass http://auth_service/tenant.json;
        proxy_set_header X-Tenant-Slug $tenant_slug;
    }
    
    # Login redireciona para Auth Service
    location = /web/login {
        return 302 /auth/login;
    }
    
    # Auth endpoints
    location /auth/ {
        proxy_pass http://auth_service/;
        proxy_set_header X-Tenant-Slug $tenant_slug;
    }
    
    # Vertical
    location / {
        proxy_pass http://construction:8000;
        proxy_set_header X-Tenant-Slug $tenant_slug;
    }
}
```

## JWT Claims

O JWT gerado pelo Auth Service contem:

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "email": "user@example.com",
  "role": "admin",
  "exp": 1234567890
}
```

## UserClaims no Vertical

O vertical extrai os claims do JWT sem fazer query ao banco:

```python
@dataclass
class UserClaims:
    id: UUID
    tenant_id: UUID
    email: str
    role: str


async def get_current_user(credentials: HTTPAuthorizationCredentials) -> UserClaims:
    token = credentials.credentials
    payload = decode_access_token(token)
    
    return UserClaims(
        id=UUID(payload["sub"]),
        tenant_id=UUID(payload["tenant_id"]),
        email=payload["email"],
        role=payload["role"],
    )
```

## Tenant Branding

O branding e servido dinamicamente pelo Auth Service via `/tenant.json`:

```json
{
  "slug": "lojadoze",
  "name": "Loja do Zé",
  "logo_url": "https://...",
  "primary_color": "#1a73e8",
  "secondary_color": "#ea4335",
  "features": {
    "cotacoes": true,
    "pedidos": true
  }
}
```

A configuracao e armazenada no banco:

```sql
CREATE TABLE tenant_branding (
    tenant_id UUID PRIMARY KEY REFERENCES tenants(id),
    logo_url VARCHAR(500),
    primary_color VARCHAR(7) DEFAULT '#1a73e8',
    secondary_color VARCHAR(7) DEFAULT '#ea4335',
    feature_flags JSONB DEFAULT '{}'
);
```

## Desenvolvimento Local

### Sem Subdomain

Acesse diretamente `http://localhost:8000/web/dashboard`.
O sistema funciona sem tenant especifico (modo desenvolvimento).

### Com Subdomain

1. Adicione ao `/etc/hosts`:
```
127.0.0.1 demo.localhost
```

2. Inicie os servicos:
```bash
cd infra/envs/development/local
docker compose up -d
```

3. Acesse: `http://demo.localhost/auth/login`

O middleware resolve `demo` como slug via header X-Tenant-Slug.

## Isolamento de Dados

**TODAS** as queries de dados de negocio filtram por `tenant_id`:

```python
cotacoes = (
    db.query(Cotacao)
    .filter(Cotacao.tenant_id == user.tenant_id)  # Do JWT claims
    .order_by(Cotacao.created_at.desc())
    .all()
)
```

**Engines** tambem respeitam `tenant_id` nos eventos:

```python
envelope = EventEnvelope(
    event_id=uuid4(),
    event_type="sale_recorded",
    tenant_id=tenant_id,  # Sempre presente
    payload={...}
)
```

## Criacao de Novo Tenant

A criacao de tenant e feita diretamente no banco (ou futuramente via admin panel no Auth Service):

```python
from auth_app.models import Tenant, TenantBranding, User
from basecore.security import get_password_hash

# 1. Criar tenant
tenant = Tenant(
    nome="Nova Loja",
    slug="novaloja",  # Subdomain
    cnpj="12.345.678/0001-90",
    email="contato@novaloja.com",
    ativo=True
)
db.add(tenant)
db.commit()

# 2. Criar branding (opcional)
branding = TenantBranding(
    tenant_id=tenant.id,
    primary_color="#1a73e8"
)
db.add(branding)
db.commit()

# 3. Criar usuario admin
user = User(
    tenant_id=tenant.id,
    nome="Admin",
    email="admin@novaloja.com",
    password_hash=get_password_hash("senha123"),
    role="admin",
    ativo=True
)
db.add(user)
db.commit()
```

Apos isso, o tenant pode acessar via `novaloja.basecommerce.com.br`.
