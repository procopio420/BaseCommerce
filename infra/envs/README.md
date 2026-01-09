# Environments

Estrutura de ambientes do BaseCommerce.

## Estrutura

```
envs/
├── production/          # Ambiente de produção
│   ├── edge/            # Nginx + Auth
│   ├── platform/        # PostgreSQL + Redis + Workers
│   └── verticals/       # Aplicações verticais
│       └── construction/ # Vertical Construction
│
├── development/         # Ambientes de desenvolvimento
│   └── local/           # Desenvolvimento local (Docker Compose)
│
└── staging/             # Futuro: ambiente de staging
    └── ...
```

## Ambientes Disponíveis

### Production

Ambiente de produção rodando em droplets VPS.

- **Edge**: `envs/production/edge/`
- **Platform**: `envs/production/platform/`
- **Verticals**: `envs/production/verticals/<name>/`

### Staging

Ambiente de staging para testes antes de produção. Mesma topologia de production.

- **Edge**: `envs/staging/edge/`
- **Platform**: `envs/staging/platform/`
- **Verticals**: `envs/staging/verticals/<name>/`

**Nota**: IPs são placeholders em `inventory.yaml`. Preencher quando criar droplets de staging.

### Development

Ambiente de desenvolvimento local.

- **Local**: `envs/development/local/` - Simula toda a stack em Docker Compose

## Uso com CLI

O CLI `basec` suporta múltiplos ambientes via `--env`:

```bash
# Production (default)
basec deploy edge
basec deploy platform
basec deploy vertical --vertical construction
basec status
basec smoke

# Staging
basec deploy edge --env staging
basec deploy platform --env staging
basec deploy vertical --vertical construction --env staging
basec status --env staging
basec smoke --env staging

# Development (local Docker Compose)
cd infra/envs/development/local
docker compose up -d
```

**Nota**: Para desenvolvimento local, use Docker Compose diretamente (não requer inventory.yaml).

## Adicionando Novo Ambiente

1. Criar pasta em `envs/<env-name>/`
2. Copiar estrutura de `production/` como base
3. Ajustar configurações específicas do ambiente
4. Atualizar `inventory.yaml` se necessário (para ambientes remotos)

## Convenções

- Cada ambiente tem sua própria estrutura de pastas
- Configurações são isoladas por ambiente
- Scripts locais (`scripts/`) são específicos de cada ambiente
- `docker-compose.yml` e `env.example` em cada pasta

