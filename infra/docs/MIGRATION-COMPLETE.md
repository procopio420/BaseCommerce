# Migração Completa: Scripts → CLI basec

✅ **MIGRAÇÃO CONCLUÍDA**

Todos os scripts bash operacionais foram substituídos pelo CLI Python `basec`.

## Status

- ✅ **100% das operações rotineiras cobertas**
- ✅ **Scripts legacy deletados** (`infra/scripts_legacy/` removido)
- ✅ **Documentação atualizada**
- ✅ **Novos comandos implementados**: `compose`, `firewall`

## Comandos Disponíveis

```bash
# Status e monitoramento
basec status
basec firewall status

# Smoke tests
basec smoke
basec smoke edge
basec smoke platform
basec smoke vertical --vertical construction

# SSH
basec ssh edge
basec ssh platform
basec ssh vertical_construction
basec ssh edge "docker ps"

# Logs
basec logs edge
basec logs edge nginx --follow
basec logs platform postgres

# Deploy
basec deploy all
basec deploy edge
basec deploy platform
basec deploy vertical --vertical construction

# Docker Compose
basec compose down edge
basec compose down  # Todos
basec compose restart edge
basec compose restart platform nginx

# Migrations
basec migrate status
basec migrate apply
basec migrate rollback 1
basec migrate rollback base
basec migrate reset --yes

# Tenants
basec tenants list
basec tenants create <slug> --nome "Nome" --email email@exemplo.com
basec tenants disable <slug>
basec tenants enable <slug>
```

## Matriz de Migração

Veja [migration-matrix.md](migration-matrix.md) para a matriz completa de migração.

## O que não foi migrado (e por quê)

- **`setup-keys.sh`**: Setup inicial de SSH keys (executar manualmente uma vez)
- **`setup-ufw.sh`**: Configuração inicial de firewall (executar manualmente uma vez)
- **`migration-generate.sh`**: Gera migrations localmente (não via CLI)

Estes são operações de setup inicial ou locais, não operações rotineiras.

## Scripts Locais nos Droplets

Os scripts em `/opt/basecommerce/scripts/` nos droplets (bootstrap.sh, update.sh, smoke-test.sh, backup-postgres.sh) são **scripts locais** e continuam sendo usados. Eles não fazem parte do CLI de infraestrutura.

## Próximos Passos

1. ✅ Migração completa
2. ✅ Scripts legacy deletados
3. ✅ Documentação atualizada
4. 🔄 Validar em ambiente de produção
5. 🔄 Treinar equipe no uso do CLI







