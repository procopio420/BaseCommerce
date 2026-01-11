# Edge Droplet HTTPS Setup

Este documento descreve a configuração HTTPS no droplet edge, incluindo checklist de configuração, validação e troubleshooting.

## Visão Geral

O edge droplet usa Nginx com Cloudflare Origin Certificates para fornecer HTTPS. A configuração suporta:

- HTTP (porta 80): Redireciona para HTTPS (exceto `/health`)
- HTTPS (porta 443): Serve todo o tráfego com SSL/TLS
- Cloudflare Full (strict) mode: Requer certificado válido no origin server

## Arquitetura

```
Cloudflare (Full strict) 
    ↓ HTTPS (443)
Origin Server (191.252.120.36)
    ↓ Nginx (443) com Cloudflare Origin Certificate
    ↓ Proxy para serviços internos
Auth Service, Vertical Services
```

## Checklist de Configuração

### 1. Pré-requisitos

- [ ] Certificados Cloudflare Origin em `infra/origin.pem` e `infra/origin.key`
- [ ] Firewall UFW configurado (portas 22, 80, 443)
- [ ] Docker e Docker Compose instalados
- [ ] Variáveis de ambiente configuradas (`.env`)

### 2. Configuração de Firewall

**No servidor (edge droplet):**

```bash
# Verificar status
sudo ufw status

# Se porta 443 não estiver aberta:
sudo ufw allow 443/tcp
sudo ufw reload
```

**Status esperado:**
```
Status: active
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### 3. Configuração de Certificados SSL

**Opção 1: Usando CLI (Recomendado)**

```bash
# Auto-detecta certificados em infra/origin.pem e infra/origin.key
basec ssl setup edge
```

O comando faz:
- Upload automático dos certificados
- Ajuste de permissões (600 para key, 644 para cert)
- Validação dos certificados
- Teste da configuração nginx
- Reinício do nginx

**Opção 2: Manual**

```bash
# No servidor
cd /opt/basecommerce/edge
mkdir -p nginx/ssl

# Upload dos certificados (usar scp ou basec ssh)
# Depois ajustar permissões
chmod 600 nginx/ssl/origin.key
chmod 644 nginx/ssl/origin.pem

# Reiniciar nginx
docker compose restart nginx
```

### 4. Configuração do Cloudflare

No painel Cloudflare (https://dash.cloudflare.com/):

1. Selecionar domínio: `basecommerce.com.br`
2. SSL/TLS → Overview
3. SSL/TLS encryption mode: **Full (strict)**
4. Verificar que Origin Certificate está configurado para:
   - `*.basecommerce.com.br`
   - `basecommerce.com.br`

### 5. Verificação da Configuração Nginx

**Verificar se nginx está escutando na porta 443:**

```bash
# No servidor
sudo ss -tlnp | grep :443
# ou
sudo netstat -tlnp | grep :443
```

**Status esperado:**
```
LISTEN 0      511          0.0.0.0:443         0.0.0.0:*    users:(("docker-proxy",pid=...))
```

**Verificar configuração nginx:**

```bash
# No servidor
docker exec basecommerce-nginx nginx -t
```

**Status esperado:**
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Comandos de Validação

### Validação Local (no servidor)

```bash
# 1. Testar HTTPS local
curl -k -I https://localhost/health

# Esperado: HTTP/2 200
# Headers: Strict-Transport-Security, Content-Type: application/json

# 2. Verificar certificado local
openssl s_client -connect localhost:443 -servername localhost < /dev/null 2>/dev/null | grep -E "subject=|issuer=|Verify return code"

# 3. Verificar logs nginx
docker logs basecommerce-nginx 2>&1 | grep -i ssl
# Não deve mostrar erros SSL
```

### Validação via IP Público

```bash
# 1. Testar HTTPS via IP
curl -k -I https://191.252.120.36/health

# Esperado: HTTP/2 200
# Headers: Strict-Transport-Security

# 2. Verificar certificado via IP
openssl s_client -connect 191.252.120.36:443 -servername test.basecommerce.com.br < /dev/null 2>/dev/null | grep -E "subject=|issuer=|Verify return code"

# Esperado: Verify return code: 0 (ok)
```

### Validação via Domínio (Cloudflare)

```bash
# 1. Testar HTTPS via domínio
curl -I https://test.basecommerce.com.br/health

# Esperado: HTTP/2 200
# Headers: Strict-Transport-Security, Content-Type: application/json

# 2. Verificar headers completos
curl -vI https://test.basecommerce.com.br/health 2>&1 | grep -E "HTTP/|Strict-Transport-Security|Content-Type"

# Esperado:
# < HTTP/2 200
# < strict-transport-security: max-age=31536000; includeSubDomains; preload
# < content-type: application/json

# 3. Testar redirect HTTP → HTTPS
curl -I http://test.basecommerce.com.br/health

# Esperado: HTTP/1.1 301
# Header: Location: https://test.basecommerce.com.br/health
```

## Checklist Final de Validação

Execute estes comandos para validar completamente a configuração:

```bash
# === 1. Firewall ===
sudo ufw status | grep 443
# ✅ Deve mostrar: 443/tcp ALLOW

# === 2. Porta 443 Escutando ===
sudo ss -tlnp | grep :443
# ✅ Deve mostrar processo escutando na porta 443

# === 3. Certificados Presentes ===
ls -la /opt/basecommerce/edge/nginx/ssl/
# ✅ Deve mostrar origin.pem e origin.key com permissões corretas

# === 4. Configuração Nginx Válida ===
docker exec basecommerce-nginx nginx -t
# ✅ Deve mostrar: "configuration file ... test is successful"

# === 5. HTTPS Local ===
curl -k -I https://localhost/health
# ✅ Deve retornar: HTTP/2 200

# === 6. HTTPS via IP ===
curl -k -I https://191.252.120.36/health
# ✅ Deve retornar: HTTP/2 200

# === 7. HTTPS via Domínio ===
curl -I https://test.basecommerce.com.br/health
# ✅ Deve retornar: HTTP/2 200

# === 8. Headers SSL ===
curl -I https://test.basecommerce.com.br/health | grep -i strict-transport
# ✅ Deve mostrar: Strict-Transport-Security header

# === 9. Logs sem Erros ===
docker logs basecommerce-nginx 2>&1 | tail -50 | grep -i error
# ✅ Não deve mostrar erros SSL ou certificado
```

## Troubleshooting

### Erro: HTTP 521 (Cloudflare "Web Server Is Down")

**Causa:** Cloudflare não consegue conectar ao origin server via HTTPS.

**Soluções:**

1. **Verificar porta 443 aberta no firewall:**
   ```bash
   sudo ufw status | grep 443
   sudo ufw allow 443/tcp && sudo ufw reload
   ```

2. **Verificar nginx escutando na porta 443:**
   ```bash
   sudo ss -tlnp | grep :443
   docker compose ps nginx
   ```

3. **Verificar certificados presentes:**
   ```bash
   ls -la /opt/basecommerce/edge/nginx/ssl/
   docker exec basecommerce-nginx ls -la /etc/nginx/ssl/
   ```

4. **Verificar logs nginx:**
   ```bash
   docker logs basecommerce-nginx 2>&1 | tail -100
   ```

5. **Verificar Cloudflare SSL mode:**
   - Acesse: https://dash.cloudflare.com/
   - SSL/TLS → Overview
   - Deve estar em **"Full (strict)"**

### Erro: "SSL certificate not found" no nginx

**Causa:** Certificados não estão no caminho correto ou com permissões incorretas.

**Solução:**

```bash
# Verificar certificados
docker exec basecommerce-nginx ls -la /etc/nginx/ssl/

# Se faltarem, fazer upload novamente
basec ssl setup edge

# Ou manualmente
chmod 600 /opt/basecommerce/edge/nginx/ssl/origin.key
chmod 644 /opt/basecommerce/edge/nginx/ssl/origin.pem
docker compose restart nginx
```

### Erro: "Connection refused" ao testar HTTPS

**Causa:** Porta 443 não está aberta ou nginx não está escutando.

**Solução:**

```bash
# Verificar firewall
sudo ufw status
sudo ufw allow 443/tcp

# Verificar se nginx está rodando
docker compose ps nginx

# Verificar se porta está mapeada no docker-compose
cat docker-compose.yml | grep "443:443"
```

### Erro: "Certificate verify failed" no openssl

**Causa:** Certificado não corresponde ao hostname ou está expirado.

**Solução:**

```bash
# Verificar certificado
openssl x509 -in /opt/basecommerce/edge/nginx/ssl/origin.pem -text -noout | grep -E "Subject:|DNS:"

# Deve mostrar:
# Subject: CN=*.basecommerce.com.br
# DNS:*.basecommerce.com.br, DNS:basecommerce.com.br

# Verificar expiração
openssl x509 -in /opt/basecommerce/edge/nginx/ssl/origin.pem -noout -enddate
```

### Redirect Loop (HTTP → HTTPS infinito)

**Causa:** Cloudflare está forçando HTTPS, mas origin está redirecionando de volta.

**Solução:**

- Verificar se `/health` endpoint não redireciona (deve retornar 200 direto)
- Verificar se Cloudflare SSL mode está correto
- Verificar se não há múltiplas camadas de redirect

## Manutenção

### Renovação de Certificados

Cloudflare Origin Certificates têm validade longa (até 15 anos), mas podem ser renovados:

1. Gerar novo certificado no Cloudflare dashboard
2. Fazer download do novo `origin.pem` e `origin.key`
3. Atualizar arquivos em `infra/origin.pem` e `infra/origin.key`
4. Executar: `basec ssl setup edge`
5. Verificar: `basec ssl check edge`

### Monitoramento

**Verificar logs nginx regularmente:**

```bash
# Últimas 100 linhas
docker logs basecommerce-nginx --tail 100

# Filtrar erros SSL
docker logs basecommerce-nginx 2>&1 | grep -i ssl

# Monitorar em tempo real
docker logs -f basecommerce-nginx
```

**Verificar expiração de certificado:**

```bash
openssl x509 -in /opt/basecommerce/edge/nginx/ssl/origin.pem -noout -enddate
```

## Referências

- [Cloudflare Origin Certificates](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)
- [Nginx SSL Configuration](https://nginx.org/en/docs/http/configuring_https_servers.html)
- [BaseCommerce Edge README](../envs/production/edge/README.md)
- [SSL CLI Usage](../envs/production/edge/SSL_CLI_USAGE.md)


