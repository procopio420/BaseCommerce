# Infrastructure Topology

Detailed architecture decisions and scaling guidance for BaseCommerce.

## Design Principles

1. **VPS-only** - No Kubernetes, no serverless, no managed services beyond basic VMs
2. **Simplicity** - Each droplet has clear responsibility
3. **Cost-effective** - Start at $24/mo, scale as needed
4. **Horizontally separable** - Each layer can scale independently

## Topology

```
                              CLOUDFLARE
                          ┌───────────────┐
                          │  TLS + CDN    │
                          │  DDoS Protect │
                          └───────┬───────┘
                                  │
        ┌─────────────────────────┼─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         ▼
   *.tenant1.          *.tenant2.                 *.tenantN.
   basecommerce        basecommerce               basecommerce
   .com.br             .com.br                    .com.br
        │                         │                         │
        └─────────────────────────┼─────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │     DROPLET 1 - EDGE     │
                    │     $6/mo (1GB, 1vCPU)   │
                    ├──────────────────────────┤
                    │ Nginx                    │
                    │ ├── tenant extraction    │
                    │ ├── rate limiting        │
                    │ ├── /tenant.json serve   │
                    │ └── reverse proxy        │
                    │                          │
                    │ Auth Service (8001)      │
                    │ └── placeholder          │
                    └────────────┬─────────────┘
                                 │
                    Private Network (VPC)
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  DROPLET 2 - VERTICAL    │
                    │  $6/mo (1GB, 1vCPU)      │
                    ├──────────────────────────┤
                    │ Construction App (8000)  │
                    │ ├── FastAPI + Gunicorn   │
                    │ ├── 2 workers, 1 thread  │
                    │ ├── HTMX templates       │
                    │ └── REST API             │
                    │                          │
                    │ Reads X-Tenant-Slug      │
                    │ from Nginx headers       │
                    └────────────┬─────────────┘
                                 │
                    Private Network (VPC)
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │   DROPLET 3 - INFRA      │
                    │   $12/mo (2GB, 1vCPU)    │
                    ├──────────────────────────┤
                    │ PostgreSQL (5432)        │
                    │ ├── 50 max connections   │
                    │ ├── 512MB shared_buffers │
                    │ └── Multi-tenant data    │
                    │                          │
                    │ Redis (6379)             │
                    │ ├── 256MB maxmemory      │
                    │ └── Streams for events   │
                    │                          │
                    │ Outbox Relay             │
                    │ └── DB → Redis Streams   │
                    │                          │
                    │ Engines Worker           │
                    │ └── Consume → Process    │
                    └──────────────────────────┘
```

## Data Flow

### Web Request

```
1. User → demo.basecommerce.com.br/web/dashboard
2. Cloudflare → TLS termination, caching, DDoS protection
3. Nginx (Droplet 1)
   ├── Extract tenant: "demo" from subdomain
   ├── Set header: X-Tenant-Slug: demo
   └── Proxy to Droplet 2
4. FastAPI (Droplet 2)
   ├── Read X-Tenant-Slug header
   ├── Query PostgreSQL with tenant_id filter
   └── Render HTMX template
5. Response flows back through Nginx → Cloudflare → User
```

### Event Processing

```
1. User action creates domain event
2. FastAPI writes event to `event_outbox` table (same transaction)
3. Outbox Relay (Droplet 3)
   ├── Polls outbox table every 1s
   ├── Publishes to Redis Stream
   └── Marks events as published
4. Engines Worker (Droplet 3)
   ├── XREADGROUP from Redis Stream
   ├── Process event (update engine tables)
   └── XACK to confirm processing
```

## Memory Budget

### Droplet 1 - Edge (1GB)

| Component | Memory |
|-----------|--------|
| Nginx | ~50MB |
| Auth Service | ~100MB |
| System/Docker | ~200MB |
| **Free** | ~650MB |

### Droplet 2 - Vertical (1GB)

| Component | Memory |
|-----------|--------|
| Gunicorn (2 workers) | ~600MB |
| System/Docker | ~200MB |
| **Free** | ~200MB |

### Droplet 3 - Infra (2GB)

| Component | Memory |
|-----------|--------|
| PostgreSQL | ~800MB (shared_buffers + work_mem) |
| Redis | ~256MB (maxmemory) |
| Outbox Relay | ~100MB |
| Engines Worker | ~150MB |
| System/Docker | ~300MB |
| **Free** | ~400MB |

## Connection Limits

| Resource | Limit | Notes |
|----------|-------|-------|
| PostgreSQL max_connections | 50 | Shared across all services |
| Construction pool_size | 5 | Per Gunicorn worker |
| Construction max_overflow | 10 | Temporary connections |
| **Total from Vertical** | 15 | 5×2 + overflow |
| Outbox Relay | 2 | Single connection + spare |
| Engines Worker | 2 | Single connection + spare |
| **Total used** | ~20 | Leaves headroom for admin |

## Scaling Scenarios

### 100 Tenants (Current Setup)

No changes needed. Current setup handles this easily.

### 500 Tenants

**Symptoms:**
- Database queries slow
- Occasional connection timeouts

**Actions:**
1. Upgrade Droplet 3 to 4GB ($24/mo → $36/mo)
2. Increase shared_buffers to 1GB
3. Add indexes on tenant_id columns

### 1000 Tenants

**Symptoms:**
- Consistent database pressure
- Redis memory near limit
- Gunicorn workers saturated

**Actions:**
1. Upgrade Droplet 3 to 8GB ($24/mo → $48/mo)
2. Add PgBouncer for connection pooling
3. Consider read replicas
4. Increase Gunicorn workers (requires 2GB vertical)

### High Traffic Burst

**Symptoms:**
- Nginx rate limiting triggered
- 502 errors from vertical

**Actions:**
1. Add second Edge droplet + DigitalOcean Load Balancer ($12/mo)
2. Adjust rate limits in nginx config

### Background Processing Backlog

**Symptoms:**
- Redis stream lag increasing
- Events processing slow

**Actions:**
1. Add second Engines Worker (on same or new droplet)
2. Use different consumer group for parallel processing

## What NOT to Do

| Don't | Why |
|-------|-----|
| Use Kubernetes | Overkill for this scale, adds complexity |
| Use managed DB | Expensive, lose control, vendor lock-in |
| Use serverless | Cold starts hurt UX, unpredictable costs |
| Shard database | Unnecessary until 10k+ tenants |
| Add caching layer | PostgreSQL + proper indexes is enough |
| Use microservices | One vertical is simpler, faster to develop |

## Cost Projection

| Tenants | Monthly Cost | Notes |
|---------|--------------|-------|
| 1-100 | $24 | Current setup |
| 100-500 | $36 | Upgrade Droplet 3 |
| 500-1000 | $60 | Upgrade Droplet 2+3 |
| 1000+ | $100+ | Add load balancer, replicas |

## Disaster Recovery

### Backup Strategy

| Data | Frequency | Retention | Storage |
|------|-----------|-----------|---------|
| PostgreSQL | Daily | 7 days | Droplet 3 local + offsite |
| PostgreSQL | Before updates | 30 days | Offsite |
| Redis | None | - | Regenerated from outbox |

### Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| Droplet 1 failure | 15 min | 0 (stateless) |
| Droplet 2 failure | 15 min | 0 (stateless) |
| Droplet 3 failure | 1 hour | Last backup |
| Total datacenter failure | 4 hours | Last offsite backup |

### Recovery Procedures

1. **Droplet failure:** Create new droplet, run bootstrap.sh from `infra/envs/production/<role>/`, restore config (use `basec ssh` to access)
2. **Add new environment:** Copy `envs/production/` to `envs/<new-env>/`, update `inventory.yaml`, configure IPs
3. **Add new vertical:** Copy `envs/production/verticals/construction/` to `envs/production/verticals/<new-vertical>/`, update `inventory.yaml`
2. **Database corruption:** Stop workers, restore backup, restart
3. **Datacenter failure:** Create droplets in new region, restore backup

## Security Checklist

- [ ] UFW enabled on all droplets
- [ ] SSH key-only authentication
- [ ] Fail2ban installed
- [ ] Cloudflare proxy enabled (orange cloud)
- [ ] Database only accessible via VPC
- [ ] Strong passwords in .env files
- [ ] .env files not in git
- [ ] Regular backups tested

