# Environments Guide

Guia completo sobre ambientes e como gerenciá-los.

## Ambientes Disponíveis

### Production

Ambiente de produção em uso.

- **Localização**: `infra/envs/production/`
- **Droplets**: IPs reais configurados em `inventory.yaml`
- **Uso**: `basec deploy edge` (default)

### Staging

Ambiente de staging para testes antes de produção.

- **Localização**: `infra/envs/staging/`
- **Droplets**: IPs placeholder em `inventory.yaml` (preencher quando criar)
- **Uso**: `basec deploy edge --env staging`

### Development

Ambiente de desenvolvimento local.

- **Localização**: `infra/envs/development/local/`
- **Tipo**: Docker Compose local (não requer droplets)
- **Uso**: `cd infra/envs/development/local && docker compose up -d`

## Adicionando um Novo Ambiente

Para criar um novo ambiente (ex: `staging2`):

1. **Copiar estrutura de production:**

```bash
cd infra/envs
cp -r production staging2
```

2. **Atualizar `inventory.yaml`:**

```yaml
staging2:
  edge:
    ip: ""  # TODO: Preencher com IP real
    user: root
    role: edge
    # ...
  platform:
    ip: ""  # TODO: Preencher com IP real
    # ...
  vertical_construction:
    ip: ""  # TODO: Preencher com IP real
    # ...
```

3. **Atualizar env.example em cada pasta:**

```bash
# Em cada pasta (edge, platform, verticals/construction)
nano env.example
# Ajustar IPs, secrets, etc.
```

4. **Validar:**

```bash
basec status --env staging2
```

## Adicionando uma Nova Vertical

Para adicionar uma nova vertical (ex: `retail`) em production:

1. **Copiar estrutura de construction:**

```bash
cd infra/envs/production/verticals
cp -r construction retail
```

2. **Atualizar `inventory.yaml`:**

```yaml
production:
  # ... existing droplets ...
  vertical_retail:
    ip: "10.0.0.0"  # IP do novo droplet
    user: root
    role: vertical
    vertical: retail
    hostname: "vps-xxx.example.com"
    description: Retail vertical (FastAPI)
```

3. **Ajustar `docker-compose.yml` e `env.example`:**

```bash
cd infra/envs/production/verticals/retail
nano docker-compose.yml  # Ajustar service name se necessário
nano env.example  # Ajustar variáveis específicas
```

4. **Deploy:**

```bash
basec deploy vertical --vertical retail
```

## Estrutura de Pastas por Ambiente

Cada ambiente segue a mesma estrutura:

```
<env>/
├── edge/
│   ├── docker-compose.yml
│   ├── env.example
│   ├── nginx/
│   ├── scripts/
│   └── README.md
├── platform/
│   ├── docker-compose.yml
│   ├── env.example
│   ├── postgres/
│   ├── redis/
│   ├── scripts/
│   └── README.md
└── verticals/
    └── <vertical-name>/
        ├── docker-compose.yml
        ├── env.example
        ├── scripts/
        └── README.md
```

## Inventory.yaml Structure

O `inventory.yaml` suporta múltiplos ambientes:

```yaml
production:
  edge:
    ip: "191.252.120.36"
    # ...
  platform:
    ip: "191.252.120.182"
    # ...
  vertical_construction:
    ip: "191.252.120.176"
    # ...

staging:
  edge:
    ip: ""  # Placeholder
    # ...
  # ...

# Backward compatibility (defaults to production)
droplets:
  edge:
    ip: "191.252.120.36"
    # ...
```

## CLI com Múltiplos Ambientes

Todos os comandos do CLI suportam `--env`:

```bash
# Status
basec status --env production
basec status --env staging

# Deploy
basec deploy edge --env production
basec deploy edge --env staging

# Smoke tests
basec smoke --env production
basec smoke --env staging

# Logs
basec logs edge --env production
basec logs edge --env staging
```

## Boas Práticas

1. **Sempre use `--env` explicitamente** em scripts automatizados
2. **Production é default** - comandos sem `--env` usam production
3. **Staging deve espelhar production** - mesma topologia, dados isolados
4. **Development é local** - não requer inventory.yaml
5. **IPs vazios são ignorados** - staging pode ter placeholders até criar droplets

## Troubleshooting

### Erro: "No droplets configured for environment 'staging'"

- Verifique se `staging` existe em `inventory.yaml`
- Verifique se os IPs não estão vazios (ou remova temporariamente do inventory)

### Erro: "Environment 'staging' not found"

- Verifique se `infra/envs/staging/` existe
- Verifique se as pastas `edge/`, `platform/`, `verticals/` existem

### Comando funciona em production mas não em staging

- Verifique se os IPs estão preenchidos em `inventory.yaml`
- Verifique se os droplets existem e estão acessíveis via SSH



