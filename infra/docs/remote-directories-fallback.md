# Fallback Automático de Diretórios Remotos

## Problema

Os droplets em produção podem ter duas estruturas diferentes:

1. **Nova estrutura** (por role): `/opt/basecommerce/<role>/`
2. **Estrutura legada**: `/opt/basecommerce/` (tudo em um diretório)

## Solução: Fallback Automático

O `DockerCompose` detecta automaticamente qual estrutura existe:

```python
from basec.docker import DockerCompose
from basec.inventory import get_droplet

droplet = get_droplet("edge")
docker = DockerCompose(droplet)

# A propriedade remote_dir faz a detecção automática:
print(docker.remote_dir)
# Se /opt/basecommerce/edge existe: "/opt/basecommerce/edge"
# Se não existe, mas /opt/basecommerce existe: "/opt/basecommerce"
```

## Como Funciona

1. **Primeira verificação**: Tenta encontrar `docker-compose.yml` no diretório preferido
   - Edge: `/opt/basecommerce/edge/docker-compose.yml`
   - Platform: `/opt/basecommerce/platform/docker-compose.yml`
   - Vertical: `/opt/basecommerce/verticals/<name>/docker-compose.yml`

2. **Fallback**: Se não encontrar, tenta estrutura legada
   - `/opt/basecommerce/docker-compose.yml`

3. **Erro**: Se nenhum existir, levanta `RuntimeError` informativo

## Cache

O diretório detectado é cacheado em `self._remote_dir` para evitar múltiplas verificações SSH.

## Migração Gradual

Isso permite migração gradual:

1. **Fase 1**: Droplets usam `/opt/basecommerce/` (legacy) - CLI funciona via fallback
2. **Fase 2**: Migrar droplets para nova estrutura criando diretórios por role
3. **Fase 3**: CLI automaticamente usa nova estrutura quando disponível

## Exemplo de Uso

```python
# O CLI sempre funciona, independente da estrutura
docker = DockerCompose(get_droplet("edge"))

# Primeira chamada: detecta e cacheia
containers = docker.ps()  # Usa /opt/basecommerce/ ou /opt/basecommerce/edge

# Chamadas subsequentes: usa cache
docker.logs()  # Usa mesmo diretório detectado
docker.up()    # Usa mesmo diretório detectado
```

## Verificar Qual Estrutura Está Sendo Usada

```bash
# Via CLI (mensagens de erro mostram o diretório)
basec logs edge
# Se erro, mostra: "Directory: /opt/basecommerce/edge" ou "/opt/basecommerce"

# Via Python
from basec.docker import DockerCompose
from basec.inventory import get_droplet

docker = DockerCompose(get_droplet("edge"))
print(docker.remote_dir)  # Mostra qual diretório está sendo usado
```

## Forçar Uso de Diretório Específico

Se necessário, você pode forçar um diretório específico:

```python
from basec.inventory import DropletConfig

droplet = DropletConfig(
    ip="192.168.1.1",
    role="edge",
    remote_dir="/custom/path"  # Força uso deste diretório
)

docker = DockerCompose(droplet)
# Sempre usará /custom/path (sem fallback)
```




