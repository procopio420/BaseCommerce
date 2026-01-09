# BaseCommerce Infrastructure CLI

CLI profissional em Python para gerenciar a infraestrutura do BaseCommerce. Substitui os scripts bash existentes por um comando único, consistente e extensível.

## Filosofia

O CLI foi projetado com os seguintes princípios:

1. **Fonte única da verdade**: `inventory.yaml` contém toda a configuração de droplets
2. **Idempotência**: Todos os comandos são seguros para reexecução
3. **Extensibilidade**: Estrutura modular preparada para futura TUI (Textual)
4. **Consistência**: Interface unificada para todas as operações
5. **Orquestração**: CLI apenas orquestra SSH, Docker e APIs - não refatora aplicações

## Instalação

### Ambiente Virtual (Recomendado)

```bash
cd infra/cli

# Criar ambiente virtual
python -m venv .venv

# Ativar ambiente virtual
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows

# Instalar CLI
pip install -e .
```

O comando `basec` estará disponível após a instalação (com o ambiente virtual ativado).

**Nota**: Requer Python 3.11+.

## Configuração

### Inventory

O arquivo `infra/inventory.yaml` é a fonte única da verdade. Exemplo:

```yaml
droplets:
  edge:
    ip: 191.252.120.36
    user: root
    role: edge
  
  platform:
    ip: 191.252.120.182
    user: root
    role: platform
  
  vertical_construction:
    ip: 191.252.120.176
    user: root
    role: vertical
    vertical: construction
```

### SSH Key

O CLI usa `infra/deploy_key` para autenticação SSH. Certifique-se de que a chave existe e tem permissões corretas:

```bash
chmod 600 infra/deploy_key
```

## Comandos

### Status

Mostra status de todos os droplets:

```bash
basec status
```

Exibe:
- Conectividade SSH
- Status Docker
- Containers rodando
- Uso de recursos (CPU/RAM/Disk)

### Smoke Tests

Executa testes de validação:

```bash
# Testar todos os droplets
basec smoke

# Testar apenas edge
basec smoke edge

# Testar apenas platform
basec smoke platform

# Testar vertical específico
basec smoke vertical --vertical construction
```

### Logs

Visualiza logs de containers:

```bash
# Logs de todos os serviços
basec logs edge

# Logs de serviço específico
basec logs edge nginx

# Seguir logs em tempo real
basec logs edge nginx --follow

# Últimas 50 linhas
basec logs edge --tail 50
```

### Deploy

Faz deploy de serviços:

```bash
# Deploy de todos os droplets (ordem: platform, edge, verticals)
basec deploy all

# Deploy apenas edge
basec deploy edge

# Deploy apenas platform
basec deploy platform

# Deploy vertical específico
basec deploy vertical --vertical construction
```

### Tenants

Gerencia tenants:

```bash
# Listar todos os tenants
basec tenants list

# Criar novo tenant
basec tenants create novotenant \
  --nome "Nova Loja" \
  --email contato@novaloja.com \
  --cnpj "12.345.678/0001-90" \
  --vertical construction

# Desativar tenant
basec tenants disable novotenant

# Reativar tenant
basec tenants enable novotenant
```

## Estrutura do Código

```
infra/cli/
├── pyproject.toml          # Dependências e entrypoint
├── basec/
│   ├── __init__.py
│   ├── main.py            # Entrypoint Typer
│   ├── inventory.py       # Leitura de inventory.yaml
│   ├── ssh.py             # Wrapper SSH (Paramiko)
│   ├── docker.py          # Helpers docker compose (refatorado)
│   ├── output.py          # Helpers Rich
│   ├── status.py          # Comando status
│   ├── smoke.py           # Smoke tests
│   ├── logs.py            # Logs
│   ├── deploy.py          # Deploy
│   ├── tenants.py         # Gerenciamento de tenants
│   ├── ssh_cmd.py         # Comando SSH
│   ├── migrate.py         # Migrations
│   ├── compose.py         # Docker Compose operations
│   └── firewall.py        # Firewall status
└── README.md
```

### Docker Compose Helper

O helper `DockerCompose` foi refatorado para ser mais robusto:

- **Remote directories**: Determinados automaticamente por role via `DropletConfig.get_remote_dir()`
  - Edge: `/opt/basecommerce/edge`
  - Platform: `/opt/basecommerce/platform`
  - Vertical: `/opt/basecommerce/verticals/<name>`
- **Error handling**: `RuntimeError` sempre levantado quando `exit_code != 0` (nunca silencioso)
- **Security**: `exec()` aceita `list[str]` e usa `shlex.join()` para quoting seguro
- **Formatos corretos**: `ps()` e `stats()` usam `--format '{{json .}}'` e parse linha a linha
- **Logs streaming**: `logs(follow=True)` usa `execute_stream()` com PTY, fallback para polling
- **Deploy melhorado**: `up()` com `pull` e `remove_orphans` opcionais
- **Timeouts**: Configuráveis via `SSHClientWrapper.default_command_timeout`

Veja [docker-compose-helper.md](docker-compose-helper.md) e [remote-directories.md](remote-directories.md) para documentação completa.

## Adicionando Novos Comandos

1. **Criar módulo** em `basec/`:

```python
# basec/novo_comando.py
import typer

app = typer.Typer()

@app.command()
def acao():
    """Descrição do comando."""
    # Implementação
    pass
```

2. **Registrar em `main.py`**:

```python
from basec import novo_comando

app.add_typer(novo_comando.app, name="novo-comando")
```

3. **Usar helpers existentes**:
   - `basec.inventory` - Acesso ao inventory
   - `basec.ssh` - Operações SSH
   - `basec.docker` - Operações Docker
   - `basec.output` - Output formatado

## Preparação para TUI

A estrutura atual está preparada para futura TUI com Textual:

- **Módulos isolados**: Cada comando é um módulo independente
- **Funções puras**: Quando possível, lógica separada de I/O
- **Output abstraído**: `output.py` pode ser substituído por widgets Textual

Para adicionar TUI no futuro:

1. Criar `basec/tui/` com widgets Textual
2. Manter comandos CLI funcionando
3. TUI chama as mesmas funções dos módulos

## Matriz de Migração: Scripts → Comandos basec

Esta tabela mapeia todos os scripts bash antigos para os novos comandos `basec`:

| Script Antigo | Comando basec | Status | Notas |
|--------------|---------------|--------|-------|
| **Status e Monitoramento** |
| `status.sh` | `basec status` | ✅ Implementado | Mostra status de todos os droplets |
| `ufw-status.sh` | `basec ssh <droplet> ufw status` | ✅ Implementado | Via SSH |
| **Smoke Tests** |
| `run-all.sh smoke` | `basec smoke` | ✅ Implementado | Testa todos os droplets |
| `run-all.sh` (outros) | `basec <comando>` | ✅ Implementado | Ver comandos individuais abaixo |
| **SSH e Acesso** |
| `ssh-edge.sh` | `basec ssh edge` | ✅ Implementado | Shell interativo |
| `ssh-platform.sh` | `basec ssh platform` | ✅ Implementado | Shell interativo |
| `ssh-vertical.sh` | `basec ssh vertical_construction` | ✅ Implementado | Shell interativo |
| `ssh-*.sh <command>` | `basec ssh <droplet> <command>` | ✅ Implementado | Executa comando remoto |
| **Logs** |
| `run-edge.sh logs` | `basec logs edge` | ✅ Implementado | Logs de todos os serviços |
| `run-edge.sh logs <service>` | `basec logs edge <service>` | ✅ Implementado | Logs de serviço específico |
| `run-platform.sh logs` | `basec logs platform` | ✅ Implementado | |
| `run-vertical.sh logs` | `basec logs vertical_construction` | ✅ Implementado | |
| **Deploy** |
| `deploy-all.sh` | `basec deploy all` | ✅ Implementado | Deploy em ordem: platform, edge, verticals |
| `deploy-edge.sh` | `basec deploy edge` | ✅ Implementado | |
| `deploy-platform.sh` | `basec deploy platform` | ✅ Implementado | |
| `deploy-vertical.sh` | `basec deploy vertical --vertical construction` | ✅ Implementado | |
| **Docker Compose** |
| `run-edge.sh up` | `basec deploy edge` | ✅ Implementado | |
| `run-edge.sh down` | `basec ssh edge "cd /opt/basecommerce && docker compose down"` | ✅ Implementado | Via SSH |
| `run-edge.sh restart` | `basec ssh edge "cd /opt/basecommerce && docker compose restart"` | ✅ Implementado | Via SSH |
| `run-edge.sh ps` | `basec status` | ✅ Implementado | Mostra containers em status |
| `run-platform.sh <cmd>` | `basec ssh platform "cd /opt/basecommerce && docker compose <cmd>"` | ✅ Implementado | Via SSH |
| `run-vertical.sh <cmd>` | `basec ssh vertical_construction "cd /opt/basecommerce && docker compose <cmd>"` | ✅ Implementado | Via SSH |
| **Migrations** |
| `run-migrations.sh` | `basec migrate apply` | ✅ Implementado | Aplica migrations pendentes |
| `run-migrations.sh --reset` | `basec migrate reset` | ✅ Implementado | Reseta banco e aplica migrations |
| `migration-status.sh` | `basec migrate status` | ✅ Implementado | Status atual das migrations |
| `migration-rollback.sh` | `basec migrate rollback [steps]` | ✅ Implementado | Rollback de migrations |
| `migration-rollback.sh base` | `basec migrate rollback base` | ✅ Implementado | Rollback completo |
| `reset-database.sh` | `basec migrate reset` | ✅ Implementado | Reseta banco completamente |
| **Setup (Deprecated)** |
| `setup-keys.sh` | ❌ Não migrado | ⚠️ Manual | Setup inicial, executar manualmente |
| `setup-ufw.sh` | ❌ Não migrado | ⚠️ Manual | Configuração de firewall, executar manualmente |
| `migration-generate.sh` | ❌ Não migrado | ⚠️ Local | Gera migrations localmente, não via CLI |

### Legenda

- ✅ **Implementado**: Comando disponível no `basec`
- ⚠️ **Manual**: Operação de setup inicial, executar manualmente quando necessário
- ❌ **Não migrado**: Script não será migrado (setup inicial ou operação local)

### Migração Completa

Todos os scripts bash antigos foram substituídos pelo CLI `basec`. Veja [migration-matrix.md](migration-matrix.md) para a matriz completa de migração.

## Exit Codes

- `0` - Sucesso
- `1` - Erro de execução
- `2` - Uso incorreto (Typer padrão)
- `130` - Interrupção (Ctrl+C)

## Troubleshooting

### Erro de conexão SSH

Verifique:
- `infra/deploy_key` existe e tem permissões corretas
- IP do droplet está correto em `inventory.yaml`
- Firewall permite conexão SSH

### Erro ao executar docker compose

Verifique:
- Docker está rodando no droplet remoto
- Diretório `/opt/basecommerce` existe
- `docker-compose.yml` está presente

### Tenant não aparece após criação

- Verifique logs do Auth Service: `basec logs edge auth`
- Confirme que tenant foi criado: `basec tenants list`
- Verifique DNS (wildcard deve estar configurado)

## Dependências

- Python 3.12+
- typer[all] - CLI framework
- rich - Output formatado
- pydantic - Validação de dados
- paramiko - SSH client
- pyyaml - Leitura de YAML

## Desenvolvimento

```bash
# Instalar em modo desenvolvimento
cd infra/cli
pip install -e .

# Executar diretamente
python -m basec.main status

# Ou via entrypoint
basec status
```

## Roadmap

- [ ] TUI com Textual
- [ ] Comandos de backup/restore
- [ ] Monitoramento de métricas
- [ ] Integração com alertas
- [ ] Suporte a múltiplos ambientes (staging/prod)

