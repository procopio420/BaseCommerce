# Guia de Redeploy Completo (Clean Redeploy)

Este guia explica como fazer um redeploy completo do zero, garantindo que todos os arquivos estejam atualizados.

## Quando Usar Redeploy Completo

Use redeploy completo quando:
- Arquivos de configuração no servidor estão desatualizados
- Mudanças críticas no nginx/docker-compose não foram aplicadas
- Você precisa garantir que tudo está sincronizado com o repositório
- Troubleshooting de problemas de configuração

## Método 1: Usando CLI (Recomendado)

O comando `basec redeploy` faz tudo automaticamente:

```bash
# Redeploy completo do edge (com confirmação)
basec redeploy edge

# Redeploy completo sem confirmação (force)
basec redeploy edge --force

# Redeploy sem reconstruir imagens (mais rápido)
basec redeploy edge --no-rebuild

# Redeploy de tudo (edge, platform, verticals)
basec redeploy all --force
```

### O que o comando faz:

1. **Para e remove containers**
   ```bash
   docker compose down
   ```

2. **Remove imagens antigas** (se `--rebuild`)
   ```bash
   docker compose down --rmi all --volumes --remove-orphans
   ```

3. **Atualiza código do repositório**
   ```bash
   git fetch --all
   git reset --hard origin/main  # ou origin/master
   ```

4. **Sincroniza arquivos de configuração**
   - `docker-compose.yml`
   - `nginx/nginx.conf`
   - `nginx/templates/default.conf.template`
   - Scripts (`bootstrap.sh`, `smoke-test.sh`, etc.)

5. **Reconstrói imagens** (se `--rebuild`)
   ```bash
   docker compose build --no-cache auth
   docker compose pull
   ```

6. **Inicia serviços**
   ```bash
   docker compose up -d --remove-orphans
   ```

## Método 2: Manual (Passo a Passo)

Se preferir fazer manualmente ou o CLI não estiver disponível:

### No Servidor (via SSH)

```bash
# 1. Conectar ao servidor
basec ssh edge
# ou
ssh -i infra/deploy_key root@191.252.120.36

# 2. Ir para o diretório do projeto
cd /opt/basecommerce/edge

# 3. Parar e remover containers
docker compose down

# 4. Remover imagens antigas (opcional)
docker compose down --rmi all --volumes --remove-orphans

# 5. Limpar imagens órfãs
docker image prune -f

# 6. Atualizar código do git
git fetch --all
git reset --hard origin/main  # ou origin/master se usar master
# Se não for repositório git, pule para passo 7

# 7. Sincronizar arquivos manualmente (se necessário)
# Use scp ou basec deploy para fazer upload dos arquivos

# 8. Reconstruir imagens (se necessário)
docker compose build --no-cache auth
docker compose pull

# 9. Verificar configuração
docker compose config

# 10. Testar configuração nginx (antes de subir)
docker compose run --rm nginx nginx -t

# 11. Subir serviços
docker compose up -d --remove-orphans

# 12. Verificar logs
docker compose logs -f nginx
```

## Método 3: Redeploy via Deploy Normal (Mais Suave)

Se você só quer atualizar arquivos sem destruir tudo:

```bash
# Deploy normal sincroniza arquivos automaticamente
basec deploy edge

# Isso faz:
# - git pull (se for repositório git)
# - Sync de arquivos nginx críticos
# - Rebuild do auth service
# - Restart dos serviços
```

## Verificação Pós-Redeploy

Após o redeploy, sempre verifique:

```bash
# 1. Verificar containers rodando
basec ssh edge "cd /opt/basecommerce/edge && docker compose ps"

# 2. Verificar nginx config
basec ssh edge "cd /opt/basecommerce/edge && docker compose exec nginx nginx -t"

# 3. Testar endpoints
basec smoke edge

# 4. Verificar logs
basec logs edge nginx

# 5. Testar HTTPS (se aplicável)
basec ssl check edge
```

## Troubleshooting

### Problema: "git reset failed" ou "not a git repository"

**Solução:** O servidor não é um repositório git. Use o deploy normal que sincroniza arquivos:
```bash
basec deploy edge
```

Ou sincronize manualmente:
```bash
# No servidor, criar estrutura se não existir
mkdir -p /opt/basecommerce/edge/nginx/templates

# Do local, fazer upload dos arquivos
basec ssh edge "mkdir -p /opt/basecommerce/edge/nginx/templates"
# Depois use o deploy normal para sincronizar
```

### Problema: Containers não sobem após redeploy

**Verificar:**
```bash
# Logs dos containers
docker compose logs

# Configuração do compose
docker compose config

# Erros específicos do nginx
docker compose logs nginx | grep -i error
```

**Solução comum:**
```bash
# Verificar se .env está correto
cat .env

# Verificar se VERTICAL_HOST está setado
grep VERTICAL_HOST .env

# Verificar permissões
ls -la nginx/ssl/
```

### Problema: Nginx ainda usando configuração antiga

**Verificar:**
```bash
# Ver qual arquivo está sendo usado
docker compose exec nginx ls -la /etc/nginx/conf.d/

# Ver conteúdo do arquivo gerado
docker compose exec nginx cat /etc/nginx/conf.d/default.conf

# Verificar se template existe
ls -la nginx/templates/

# Forçar recriação do container
docker compose up -d --force-recreate nginx
```

**Solução:**
```bash
# Remover arquivo gerado antigo (se existir)
rm -f nginx/conf.d/default.conf

# Recriar container
docker compose up -d --force-recreate nginx

# Verificar se template foi processado
docker compose exec nginx nginx -t
```

### Problema: Certificados SSL perdidos após redeploy

**Solução:**
```bash
# Os certificados devem estar preservados, mas verificar
ls -la nginx/ssl/

# Se faltarem, reconfigurar
basec ssl setup edge
```

**Nota:** Certificados SSL não são afetados pelo `docker compose down` pois estão em volumes montados. Mas se você fez `--volumes`, precisará reconfigurar.

## Comandos Rápidos

```bash
# Redeploy rápido (sem rebuild)
basec redeploy edge --no-rebuild --force

# Redeploy completo (com rebuild)
basec redeploy edge --rebuild --force

# Redeploy e verificar
basec redeploy edge --force && basec smoke edge

# Redeploy tudo
basec redeploy all --force
```

## Comparação: Deploy vs Redeploy

| Operação | `basec deploy` | `basec redeploy` |
|----------|----------------|------------------|
| Para containers | Não (restart) | Sim (down) |
| Remove containers | Não | Sim |
| Remove imagens | Não | Opcional (--rebuild) |
| Git pull | Sim | Sim (hard reset) |
| Sync arquivos | Parcial (nginx críticos) | Completo (edge) |
| Rebuild imagens | Auth apenas | Tudo (opcional) |
| Quando usar | Deploy normal | Quando precisa garantir sync total |

## Recomendações

1. **Use `basec deploy` para deploys normais** - mais rápido e seguro
2. **Use `basec redeploy` quando:**
   - Arquivos no servidor estão desatualizados
   - Mudanças críticas não foram aplicadas
   - Troubleshooting de configuração
   - Primeira vez configurando servidor

3. **Sempre verifique após redeploy:**
   ```bash
   basec smoke edge
   basec ssl check edge  # se usar HTTPS
   ```

4. **Backup antes de redeploy completo:**
   - Certificados SSL: `tar -czf ssl-backup.tar.gz nginx/ssl/`
   - Arquivos .env: copiar para local seguro

## Arquivos Preservados

Os seguintes arquivos **não são afetados** pelo redeploy:
- `nginx/ssl/` - Certificados SSL (a menos que use `--volumes`)
- `.env` - Variáveis de ambiente
- Volumes Docker (dados de banco, etc.)

**Atenção:** Se usar `docker compose down --volumes`, volumes serão removidos!






