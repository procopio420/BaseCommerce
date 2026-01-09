# Remote Directories por Droplet

Documentação sobre como os diretórios remotos são organizados por droplet.

## Visão Geral

Cada droplet tem seu próprio diretório remoto onde o `docker-compose.yml` e arquivos de configuração são armazenados. Isso permite:

- **Isolamento**: Cada serviço tem seu próprio diretório
- **Múltiplos ambientes**: Fácil gerenciar staging/production
- **Organização**: Estrutura clara e previsível

## Estrutura Padrão

Os diretórios são determinados automaticamente pelo `DropletConfig` baseado no role, com **fallback automático** para estrutura legada:

| Role | Diretório Preferido | Fallback Legacy |
|------|---------------------|-----------------|
| `edge` | `/opt/basecommerce/edge` | `/opt/basecommerce/` |
| `platform` | `/opt/basecommerce/platform` | `/opt/basecommerce/` |
| `vertical` | `/opt/basecommerce/verticals/<vertical_name>` | `/opt/basecommerce/` |

**Importante**: O `DockerCompose` detecta automaticamente qual estrutura existe no droplet:
1. Tenta usar o diretório preferido (nova estrutura)
2. Se não existir, usa o fallback legacy (`/opt/basecommerce/`)
3. Se nenhum existir, levanta erro informativo

Isso permite migração gradual sem quebrar droplets existentes.

## Exemplos

### Edge Droplet

```python
from basec.inventory import DropletConfig

droplet = DropletConfig(
    ip="192.168.1.1",
    role="edge"
)

print(droplet.get_remote_dir())
# Output: /opt/basecommerce/edge
```

### Platform Droplet

```python
droplet = DropletConfig(
    ip="192.168.1.2",
    role="platform"
)

print(droplet.get_remote_dir())
# Output: /opt/basecommerce/platform
```

### Vertical Droplet

```python
droplet = DropletConfig(
    ip="192.168.1.3",
    role="vertical",
    vertical="construction"
)

print(droplet.get_remote_dir())
# Output: /opt/basecommerce/verticals/construction
```

## Customização

Você pode sobrescrever o diretório padrão definindo `remote_dir` explicitamente:

```python
droplet = DropletConfig(
    ip="192.168.1.1",
    role="edge",
    remote_dir="/custom/path/to/edge"
)

print(droplet.get_remote_dir())
# Output: /custom/path/to/edge
```

## Uso no DockerCompose

O `DockerCompose` helper usa automaticamente o `remote_dir` do droplet:

```python
from basec.docker import DockerCompose
from basec.inventory import get_droplet

droplet = get_droplet("edge")
docker = DockerCompose(droplet)

# Todos os comandos são executados em:
# cd /opt/basecommerce/edge && docker compose ...
docker.ps()
docker.logs()
docker.up()
```

## Estrutura de Arquivos no Droplet

Cada diretório remoto deve conter:

```
/opt/basecommerce/<role>/
├── docker-compose.yml
├── .env
├── nginx/          # (apenas edge)
│   ├── nginx.conf
│   └── conf.d/
├── postgres/        # (apenas platform)
│   └── postgresql.conf
├── redis/           # (apenas platform)
│   └── redis.conf
└── scripts/         # Scripts locais do droplet
    ├── bootstrap.sh
    ├── update.sh
    └── smoke-test.sh
```

## Múltiplos Ambientes

Para suportar múltiplos ambientes (production, staging), você pode:

1. **Usar diretórios diferentes por ambiente**:
   ```python
   # Production
   droplet_prod = DropletConfig(
       ip="192.168.1.1",
       role="edge",
       remote_dir="/opt/basecommerce/production/edge"
   )
   
   # Staging
   droplet_staging = DropletConfig(
       ip="192.168.1.2",
       role="edge",
       remote_dir="/opt/basecommerce/staging/edge"
   )
   ```

2. **Ou manter mesma estrutura e usar variáveis de ambiente**:
   - Mesmo diretório (`/opt/basecommerce/edge`)
   - Diferentes arquivos `.env` por ambiente
   - Gerenciado via `basec deploy --env <env>`

## Boas Práticas

1. **Sempre use `get_remote_dir()`**: Não hardcode paths
2. **Mantenha consistência**: Use a mesma estrutura em todos os droplets
3. **Documente customizações**: Se usar `remote_dir` customizado, documente o motivo
4. **Isolamento**: Cada vertical deve ter seu próprio diretório

## Fallback Automático

O CLI detecta automaticamente qual estrutura existe:

1. **Tenta estrutura nova** (`/opt/basecommerce/<role>`)
2. **Se não existir, tenta legacy** (`/opt/basecommerce/`)
3. **Se nenhuma existir, levanta erro informativo**

Isso permite migração gradual sem quebrar droplets existentes.

## Troubleshooting

### Erro: "No such file or directory"

Verifique se o diretório remoto existe no droplet:

```bash
# Verificar estrutura nova
basec ssh edge "ls -la /opt/basecommerce/edge"

# Verificar estrutura legacy
basec ssh edge "ls -la /opt/basecommerce"
```

### Erro: "docker-compose.yml not found"

O arquivo `docker-compose.yml` deve estar no diretório remoto:

```bash
# Estrutura nova
basec ssh edge "cat /opt/basecommerce/edge/docker-compose.yml"

# Estrutura legacy
basec ssh edge "cat /opt/basecommerce/docker-compose.yml"
```

### Verificar qual diretório está sendo usado

O CLI mostra o diretório usado nas mensagens de erro. Você também pode verificar:

```python
from basec.docker import DockerCompose
from basec.inventory import get_droplet

droplet = get_droplet("edge")
docker = DockerCompose(droplet)
print(docker.remote_dir)  # Mostra qual diretório está sendo usado
```

### Diretório incorreto

Verifique o `remote_dir` calculado:

```python
from basec.inventory import get_droplet

droplet = get_droplet("edge")
print(droplet.get_remote_dir())
```

