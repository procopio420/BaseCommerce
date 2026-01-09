# Docker Compose Helper

Documentação do helper `DockerCompose` para operações remotas via SSH.

## Visão Geral

O `DockerCompose` é um wrapper Python que executa comandos `docker compose` remotamente via SSH. Ele abstrai a complexidade de conexão SSH e formatação de comandos.

## Uso Básico

```python
from basec.docker import DockerCompose
from basec.inventory import get_droplet

# Obter configuração do droplet
droplet = get_droplet("edge")

# Criar instância do helper
docker = DockerCompose(droplet)

# Executar comandos
docker.pull()
docker.up(detach=True, pull=True)
containers = docker.ps()
```

## Remote Directory

O diretório remoto é determinado automaticamente baseado no role do droplet:

- **Edge**: `/opt/basecommerce/edge`
- **Platform**: `/opt/basecommerce/platform`
- **Vertical**: `/opt/basecommerce/verticals/<vertical_name>`

O `DropletConfig` calcula automaticamente o `remote_dir` via `get_remote_dir()`. Você pode sobrescrever isso definindo `remote_dir` explicitamente:

```python
droplet = DropletConfig(
    ip="192.168.1.1",
    role="edge",
    remote_dir="/custom/path"  # Opcional - sobrescreve o padrão
)
```

**Importante**: Cada droplet deve ter seu próprio diretório remoto. Isso permite múltiplos ambientes e isolamento entre serviços.

## Métodos Principais

### `ps() -> list[dict[str, str]]`

Lista containers em execução.

```python
containers = docker.ps()
# [
#   {
#     "name": "basecommerce-nginx",
#     "status": "Up 2 hours",
#     "service": "nginx",
#     "ports": "0.0.0.0:80->80/tcp"
#   },
#   ...
# ]
```

### `logs(service=None, follow=False, tail=100) -> None`

Visualiza logs de containers.

```python
# Últimas 100 linhas de todos os serviços
docker.logs()

# Últimas 50 linhas de um serviço específico
docker.logs(service="nginx", tail=50)

# Seguir logs em tempo real (streaming)
docker.logs(service="nginx", follow=True, tail=100)
```

**Nota**: Quando `follow=True`:
- Usa `execute_stream()` com PTY para melhor compatibilidade
- Streaming em tempo real via SSH
- Pode ser interrompido com Ctrl+C
- Fallback automático para polling em ambientes sem PTY (CI)

### `pull() -> None`

Atualiza imagens Docker.

```python
docker.pull()
```

### `up(detach=True, pull=False, remove_orphans=True) -> None`

Inicia serviços.

```python
# Iniciar sem atualizar imagens
docker.up(detach=True)

# Atualizar imagens e iniciar
docker.up(detach=True, pull=True)

# Sem remover containers órfãos
docker.up(detach=True, remove_orphans=False)
```

### `down() -> None`

Para e remove containers.

```python
docker.down()
```

### `restart(service=None) -> None`

Reinicia serviços.

```python
# Reiniciar todos os serviços
docker.restart()

# Reiniciar serviço específico
docker.restart(service="nginx")
```

### `exec(service, command, capture_output=True) -> str`

Executa comando dentro de um container.

```python
# Comando como string
output = docker.exec("nginx", "nginx -t")

# Comando como lista (recomendado para segurança)
output = docker.exec("nginx", ["nginx", "-t"])

# Comando com argumentos complexos
output = docker.exec("postgres", ["psql", "-U", "basecommerce", "-c", "SELECT 1;"])
```

**Segurança**: Use lista de strings quando possível para evitar problemas de quoting.

### `stats() -> list[dict[str, str]]`

Obtém estatísticas de uso de recursos.

```python
stats = docker.stats()
# [
#   {
#     "name": "basecommerce-nginx",
#     "cpu": "0.50%",
#     "memory": "15MiB / 1GiB",
#     "memory_percent": "1.50%",
#     "net_io": "1.2kB / 856B",
#     "block_io": "0B / 0B"
#   },
#   ...
# ]
```

## Tratamento de Erros

O helper levanta `RuntimeError` quando comandos falham (via `_run_compose`):

```python
from basec.docker import DockerCompose

try:
    docker.up()
except RuntimeError as e:
    print(f"Erro: {e}")
    # A mensagem inclui:
    # - Comando executado
    # - Exit code
    # - Últimos 500 chars de stderr
    # - Diretório remoto
```

**Importante**: `_run_compose()` sempre levanta exceção quando `exit_code != 0`. Nunca retorna silenciosamente.

## Timeout

Por padrão, comandos têm timeout de 300 segundos (5 minutos) via `SSHClientWrapper.default_command_timeout`. Você pode ajustar isso:

```python
# Ajustar timeout padrão do SSH wrapper
SSHClientWrapper.default_command_timeout = 600  # 10 minutos

# Ou passar timeout específico (se exposto no método)
# docker._run_compose("command", timeout=600)
```

**Nota**: O timeout é aplicado por comando SSH. Comandos longos (como `docker compose up`) podem precisar de timeout maior.

## Exemplos Completos

### Deploy Completo

```python
from basec.docker import DockerCompose
from basec.inventory import get_droplet

droplet = get_droplet("edge")
docker = DockerCompose(droplet)

# Pull e start
docker.up(detach=True, pull=True, remove_orphans=True)

# Verificar status
containers = docker.ps()
print(f"Containers rodando: {len(containers)}")

# Ver logs
docker.logs(service="nginx", tail=50)
```

### Executar Migrations

```python
docker = DockerCompose(get_droplet("vertical_construction"))

# Executar migration
output = docker.exec(
    "construction",
    ["alembic", "upgrade", "head"]
)
print(output)
```

### Monitoramento

```python
docker = DockerCompose(get_droplet("platform"))

# Status
containers = docker.ps()
for c in containers:
    print(f"{c['service']}: {c['status']}")

# Stats
stats = docker.stats()
for s in stats:
    print(f"{s['name']}: CPU {s['cpu']}, Memory {s['memory']}")
```

## Boas Práticas

1. **Use lista de strings em `exec()`**: Mais seguro que strings com espaços
2. **Sempre use `pull=True` em deploys**: Garante imagens atualizadas
3. **Use `remove_orphans=True`**: Remove containers órfãos automaticamente
4. **Capture erros**: Sempre trate `DockerComposeError` adequadamente
5. **Use `follow=True` com cuidado**: Logs seguidos bloqueiam até Ctrl+C

## Compatibilidade

- Docker Compose v2+ (comando `docker compose`)
- Python 3.11+
- Requer SSH configurado e chave em `infra/deploy_key`

