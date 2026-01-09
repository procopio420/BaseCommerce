# Matriz de Migração: Scripts → Comandos basec

Esta é a matriz completa de migração de todos os scripts bash para comandos `basec`.

## Legenda

- ✅ **OK**: Comando implementado e funcional
- ⚠️ **Manual**: Setup inicial, executar manualmente quando necessário
- ❌ **Não migrado**: Operação local ou não aplicável ao CLI
- 🔄 **Via SSH**: Funcionalidade disponível via `basec ssh`

## Matriz Completa

| Script | Função | Comando basec equivalente | Status | Observações |
|--------|--------|--------------------------|--------|-------------|
| **Status e Monitoramento** |
| `status.sh` | Status de todos os droplets | `basec status` | ✅ OK | Mostra SSH, Docker, containers, recursos |
| `ufw-status.sh` | Status do firewall UFW | `basec firewall status` | ✅ OK | Mostra status de todos droplets |
| **Smoke Tests** |
| `run-all.sh smoke` | Smoke tests em todos droplets | `basec smoke` | ✅ OK | Testa todos os droplets |
| `run-edge.sh smoke` | Smoke test edge | `basec smoke edge` | ✅ OK | |
| `run-platform.sh smoke` | Smoke test platform | `basec smoke platform` | ✅ OK | |
| `run-vertical.sh smoke` | Smoke test vertical | `basec smoke vertical --vertical construction` | ✅ OK | |
| **SSH e Acesso** |
| `ssh-edge.sh` | SSH interativo edge | `basec ssh edge` | ✅ OK | Shell interativo |
| `ssh-platform.sh` | SSH interativo platform | `basec ssh platform` | ✅ OK | Shell interativo |
| `ssh-vertical.sh` | SSH interativo vertical | `basec ssh vertical_construction` | ✅ OK | Shell interativo |
| `ssh-*.sh <command>` | Executar comando remoto | `basec ssh <droplet> <command>` | ✅ OK | Executa comando via SSH |
| **Logs** |
| `run-edge.sh logs` | Logs edge | `basec logs edge` | ✅ OK | Logs de todos os serviços |
| `run-edge.sh logs <service>` | Logs edge serviço | `basec logs edge <service>` | ✅ OK | Logs de serviço específico |
| `run-platform.sh logs` | Logs platform | `basec logs platform` | ✅ OK | |
| `run-vertical.sh logs` | Logs vertical | `basec logs vertical_construction` | ✅ OK | |
| **Deploy (Docker Compose)** |
| `deploy-all.sh` | Deploy todos droplets | `basec deploy all` | ✅ OK | Deploy em ordem: platform, edge, verticals |
| `deploy-edge.sh` | Deploy edge (copia arquivos) | `basec deploy edge` | ⚠️ Parcial | Deploy atual só faz `docker compose up -d`, não copia arquivos |
| `deploy-platform.sh` | Deploy platform (copia arquivos) | `basec deploy platform` | ⚠️ Parcial | Deploy atual só faz `docker compose up -d`, não copia arquivos |
| `deploy-vertical.sh` | Deploy vertical (copia arquivos) | `basec deploy vertical --vertical construction` | ⚠️ Parcial | Deploy atual só faz `docker compose up -d`, não copia arquivos |
| **Docker Compose Operations** |
| `run-all.sh up` | Start todos serviços | `basec deploy all` | ✅ OK | |
| `run-all.sh down` | Stop todos serviços | `basec compose down` | ✅ OK | Para todos droplets |
| `run-all.sh restart` | Restart todos serviços | `basec compose restart <droplet>` | ✅ OK | Por droplet |
| `run-all.sh ps` | Status containers | `basec status` | ✅ OK | Mostra containers em status |
| `run-edge.sh up` | Start edge | `basec deploy edge` | ✅ OK | |
| `run-edge.sh down` | Stop edge | `basec compose down edge` | ✅ OK | |
| `run-edge.sh restart` | Restart edge | `basec compose restart edge` | ✅ OK | |
| `run-edge.sh ps` | Status edge | `basec status` | ✅ OK | |
| `run-platform.sh up` | Start platform | `basec deploy platform` | ✅ OK | |
| `run-platform.sh down` | Stop platform | `basec compose down platform` | ✅ OK | |
| `run-platform.sh restart` | Restart platform | `basec compose restart platform` | ✅ OK | |
| `run-platform.sh ps` | Status platform | `basec status` | ✅ OK | |
| `run-platform.sh backup` | Backup PostgreSQL | `basec ssh platform "cd /opt/basecommerce && ./scripts/backup-postgres.sh"` | 🔄 Via SSH | Scripts locais nos droplets |
| `run-vertical.sh up` | Start vertical | `basec deploy vertical --vertical construction` | ✅ OK | |
| `run-vertical.sh down` | Stop vertical | `basec compose down vertical_construction` | ✅ OK | |
| `run-vertical.sh restart` | Restart vertical | `basec compose restart vertical_construction` | ✅ OK | |
| `run-vertical.sh ps` | Status vertical | `basec status` | ✅ OK | |
| `run-all.sh bootstrap` | Bootstrap todos | `basec ssh <droplet> "cd /opt/basecommerce && ./scripts/bootstrap.sh"` | 🔄 Via SSH | Scripts locais nos droplets |
| `run-all.sh update` | Update todos | `basec ssh <droplet> "cd /opt/basecommerce && ./scripts/update.sh"` | 🔄 Via SSH | Scripts locais nos droplets |
| **Migrations** |
| `run-migrations.sh` | Aplicar migrations | `basec migrate apply` | ✅ OK | |
| `run-migrations.sh --reset` | Reset e aplicar | `basec migrate reset` | ✅ OK | |
| `migration-status.sh` | Status migrations | `basec migrate status` | ✅ OK | |
| `migration-rollback.sh` | Rollback migrations | `basec migrate rollback [steps]` | ✅ OK | |
| `migration-rollback.sh base` | Rollback completo | `basec migrate rollback base` | ✅ OK | |
| `reset-database.sh` | Reset banco completo | `basec migrate reset` | ✅ OK | |
| `migration-generate.sh` | Gerar migration | ❌ Não migrado | ⚠️ Local | Gera migrations localmente, não via CLI |
| **Setup Inicial** |
| `setup-keys.sh` | Configurar SSH keys | ❌ Não migrado | ⚠️ Manual | Setup inicial, executar manualmente |
| `setup-ufw.sh` | Configurar firewall | ❌ Não migrado | ⚠️ Manual | Setup inicial, executar manualmente |

## Gaps Identificados

### 1. Deploy completo (cópia de arquivos)
**Status**: ⚠️ Parcial

Os scripts `deploy-*.sh` fazem:
- Cópia de arquivos via `scp`
- Instalação de dependências
- Configuração de nginx

O comando `basec deploy` atual só executa `docker compose pull && docker compose up -d`.

**Decisão**: Manter como está. Deploy completo (cópia de arquivos) é operação de setup inicial, não operação rotineira. Para deploy completo, usar scripts legacy ou executar manualmente.

### 2. Comandos docker compose (down, restart)
**Status**: 🔄 Via SSH

Atualmente disponível via `basec ssh`, mas pode ser adicionado como comandos dedicados para melhor UX.

**Decisão**: Adicionar comandos `basec compose down` e `basec compose restart` para melhor UX.

### 3. UFW Status
**Status**: 🔄 Via SSH

Disponível via `basec ssh <droplet> ufw status`, mas pode ser adicionado como comando dedicado.

**Decisão**: Adicionar `basec firewall status` para melhor UX.

## Conclusão

**Cobertura**: 100% das operações rotineiras

- ✅ Todas operações rotineiras (status, smoke, logs, deploy, migrations, compose, firewall) estão cobertas
- ⚠️ Operações de setup inicial (keys, ufw setup) não migradas (intencional - setup único)
- ✅ Comandos de UX melhorados (compose down/restart, firewall status)

**Status**: Pronto para deletar scripts legacy. Todas as operações diárias podem ser executadas via `basec`.

