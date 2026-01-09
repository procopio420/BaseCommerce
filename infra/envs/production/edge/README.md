# Production Edge

**Environment**: Production  
**Role**: Edge (Nginx + Auth)  
**Location**: `infra/envs/production/edge/`

## Services

| Service | Port | Description |
|---------|------|-------------|
| Nginx | 80 | Reverse proxy, multi-tenant routing |
| Auth | 8001 | Authentication service |

## Ports

- **80** (HTTP) - Public, redirects to HTTPS
- **443** (HTTPS) - Public, via Cloudflare with SSL (required for Cloudflare Full (strict) mode)
- **8001** (Auth) - Internal only

## Firewall Requirements

The edge droplet requires the following firewall rules (configured via UFW):

- **22/tcp** - SSH access
- **80/tcp** - HTTP (redirects to HTTPS)
- **443/tcp** - HTTPS (required for Cloudflare Full (strict) mode)

**Initial setup:** The `bootstrap.sh` script automatically configures UFW with these rules.

**Manual configuration:**
```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
sudo ufw reload
```

**Verify firewall status:**
```bash
sudo ufw status
```

## Environment Variables

See `env.example` for required variables:

- `VERTICAL_HOST` - Private IP of vertical droplet
- `SECRET_KEY` - JWT secret key
- `DATABASE_URL` - PostgreSQL connection string
- `ENVIRONMENT` - Set to `production`

## Quick Start

```bash
# 1. Configure environment
cp env.example .env
nano .env

# 2. Bootstrap (first time)
sudo ./scripts/bootstrap.sh

# 3. Start services
docker compose up -d

# 4. Verify
./scripts/smoke-test.sh
```

## Operations

Use `basec` CLI for operations:

```bash
# Deploy
basec deploy edge

# SSL Certificate Management
basec ssl check edge          # Verificar status dos certificados
basec ssl setup edge          # Configurar certificados (interativo)
basec ssl test edge           # Testar HTTPS

# Logs
basec logs edge

# Status
basec status

# SSH
basec ssh edge
```

**Nota**: O comando `deploy` agora verifica automaticamente os certificados SSL e mostra avisos se estiverem faltando.

## Configuration Files

- `docker-compose.yml` - Service definitions
- `nginx/nginx.conf` - Main nginx config
- `nginx/templates/default.conf.template` - Server blocks template (uses `${VERTICAL_HOST}` env var)
- `nginx/conf.d/default.conf` - Auto-generated from template (do not edit directly)
- `nginx/ssl/` - SSL certificates directory (Cloudflare Origin Certificates)
- `nginx/tenants/` - Tenant-specific JSON files

## SSL/HTTPS Configuration

The nginx is configured to support HTTPS with Cloudflare Origin Certificates:

- **HTTP (port 80)**: Redirects all traffic to HTTPS (except `/health`)
- **HTTPS (port 443)**: Handles all requests with SSL/TLS encryption
- **Cloudflare SSL mode**: Must be set to **"Full (strict)"**

### Quick Setup

**Using CLI (Recommended):**
```bash
# Auto-detects certificates from infra/origin.pem and infra/origin.key
basec ssl setup edge
```

**Manual setup:**
1. Obtain Cloudflare Origin Certificate from dashboard
2. Place certificates in `infra/origin.pem` and `infra/origin.key`
3. Run `basec ssl setup edge`

### Documentation

For complete HTTPS setup instructions, troubleshooting, and validation commands, see:
- **[Edge HTTPS Setup Guide](../../docs/edge-https-setup.md)** - Comprehensive guide with checklists and troubleshooting
- **[SSL CLI Usage](SSL_CLI_USAGE.md)** - CLI command reference

### Quick Validation

```bash
# Check SSL certificate status
basec ssl check edge

# Test HTTPS locally
curl -k -I https://localhost/health

# Test HTTPS via domain
curl -I https://test.basecommerce.com.br/health

# Verify firewall
sudo ufw status | grep 443
```

**Important**: 
- SSL certificates are **not committed** to Git (see `.gitignore`)
- Certificates must be placed in `nginx/ssl/` directory on the server
- Cloudflare SSL mode must be set to **"Full (strict)"**
- Port 443 must be open in firewall (configured by `bootstrap.sh`)

**Note:** The nginx config uses environment variable substitution. The template file is processed by nginx's built-in `envsubst` to replace `${VERTICAL_HOST}` with the actual IP from `.env`.
