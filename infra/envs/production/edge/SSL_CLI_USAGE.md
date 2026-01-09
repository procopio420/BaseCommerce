# Uso do CLI para Configurar SSL

O CLI agora inclui comandos automatizados para configurar e verificar certificados SSL.

## Comandos Disponíveis

### 1. Verificar Status dos Certificados

```bash
# Verificar se certificados SSL estão configurados corretamente
basec ssl check edge
```

**O que faz:**
- Verifica se os arquivos `origin.pem` e `origin.key` existem
- Valida permissões (chave deve ter 600)
- Testa se os certificados são válidos
- Testa configuração do nginx
- Testa endpoint HTTPS

### 2. Configurar Certificados (Automático)

```bash
# Se os arquivos origin.pem e origin.key existem em infra/, são detectados automaticamente
basec ssl setup edge
```

**Auto-detecção:**
- Se `infra/origin.pem` e `infra/origin.key` existem, são usados automaticamente
- Não precisa passar flags ou colar conteúdo
- Faz upload automático
- Ajusta permissões
- Valida certificados
- Testa configuração nginx
- Reinicia nginx

### 3. Configurar Certificados (Interativo)

```bash
# Se não há arquivos em infra/, entra no modo interativo
basec ssl setup edge
```

**Modo Interativo (quando arquivos não são encontrados):**
1. O comando pede para colar o certificado (origin.pem)
2. Depois pede para colar a chave privada (origin.key)
3. Faz upload automático
4. Ajusta permissões
5. Valida certificados
6. Testa configuração nginx
7. Reinicia nginx

**Como obter os certificados:**
- Acesse: https://dash.cloudflare.com/
- Selecione domínio: `basecommerce.com.br`
- SSL/TLS → Origin Server → Create Certificate
- Configure hostnames: `*.basecommerce.com.br`, `basecommerce.com.br`
- Copie Origin Certificate e Private Key

### 4. Configurar Certificados (de Arquivos Específicos)

```bash
# Usar arquivos locais de certificado em outros locais
basec ssl setup edge --cert ./certificates/origin.pem --key ./certificates/origin.key
```

**Quando usar:**
- Você já tem os certificados salvos localmente
- Scripts automatizados
- CI/CD pipelines

### 5. Testar HTTPS

```bash
# Testar configuração SSL/HTTPS
basec ssl test edge

# Testar domínio específico
basec ssl test edge --domain test.basecommerce.com.br
```

**O que faz:**
- Testa HTTPS localmente (localhost)
- Testa via domínio público
- Mostra informações do certificado

## Integração com Deploy

O comando `basec deploy edge` agora **verifica automaticamente** os certificados SSL:

- ✅ Se certificados estão OK: mostra mensagem de sucesso
- ⚠️ Se certificados estão faltando: mostra aviso (mas não falha o deploy)
- 🔧 Sugere rodar `basec ssl setup edge` se necessário

**Exemplo de output:**
```
Deploying: edge (191.252.120.36)
...
⚠ SSL certificates not configured: Missing certificate files: origin.pem, origin.key
  Run 'basec ssl setup edge' to configure SSL certificates
  Or set up manually following SETUP_SSL.md
```

## Fluxo de Trabalho Recomendado

### Primeira Configuração

```bash
# 1. Deploy normal (certificados ainda não configurados)
basec deploy edge

# 2. Obter certificados do Cloudflare (dashboard)

# 3. Configurar SSL via CLI
basec ssl setup edge
# [Colar certificado quando pedido]
# [Colar chave privada quando pedido]

# 4. Verificar
basec ssl check edge

# 5. Configurar Cloudflare para "Full (strict)"
# [No painel Cloudflare]
```

### Deploy Subsequente

```bash
# Deploy normal - certificados já estão configurados
basec deploy edge
# ✅ Certificates valid (expires: Jan 18 2041)
```

### Renovação de Certificados

```bash
# 1. Obter novo certificado do Cloudflare

# 2. Configurar novamente (sobrescreve os antigos)
basec ssl setup edge

# 3. Verificar
basec ssl check edge
```

## Exemplos de Uso

### Setup Completo

```bash
# 1. Deploy
basec deploy edge

# 2. Verificar status (deve mostrar que faltam certificados)
basec ssl check edge

# 3. Configurar (interativo)
basec ssl setup edge
# [Seguir prompts]

# 4. Verificar novamente (deve mostrar OK)
basec ssl check edge

# 5. Testar
basec ssl test edge
```

### Usando Arquivos Locais

```bash
# Salvar certificados localmente primeiro
cat > /tmp/origin.pem << 'EOF'
-----BEGIN CERTIFICATE-----
...
-----END CERTIFICATE-----
EOF

cat > /tmp/origin.key << 'EOF'
-----BEGIN PRIVATE KEY-----
...
-----END PRIVATE KEY-----
EOF

# Configurar usando arquivos
basec ssl setup edge --cert /tmp/origin.pem --key /tmp/origin.key
```

## Troubleshooting

### Erro: "Certificate validation failed"
- Verifique se o certificado começa com `-----BEGIN CERTIFICATE-----`
- Verifique se a chave começa com `-----BEGIN` (pode ser `PRIVATE KEY` ou `RSA PRIVATE KEY`)
- Certifique-se de copiar os certificados completos (incluindo BEGIN/END)

### Erro: "Nginx configuration test failed"
- Verifique logs: `basec logs edge nginx`
- Verifique se o template está correto
- Execute: `basec ssh edge "docker exec basecommerce-nginx nginx -t"`

### Certificados não funcionam após setup
- Verifique Cloudflare SSL mode: deve estar em "Full (strict)"
- Aguarde alguns minutos para propagar
- Teste diretamente: `curl -k https://test.basecommerce.com.br/health`

## Comandos Rápidos

```bash
# Status rápido
basec ssl check edge

# Setup interativo
basec ssl setup edge

# Teste
basec ssl test edge

# Deploy com verificação automática
basec deploy edge
```

