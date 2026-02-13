# Scalability Analysis

## Assumptions

- **Up to 1000 tenants** (construction materials stores)
- **Geographic concentration**: Brazil, Sul Fluminense initially
- **Traffic**: Low to medium per tenant (5-50 active users per store)
- **Heavy use of async events**
- **VPS-only**: DigitalOcean droplets, no Kubernetes

## Main Question

> **Can this architecture handle 1000 clients?**

**Answer: YES**, with headroom for most scenarios. See detailed analysis below.

---

## Analysis by Component

### 1. Nginx (Reverse Proxy)

**Capacity**: A single Nginx can handle **10,000+ requests/second**.

**For 1000 tenants**:
- Assuming 50 active users per tenant = 50,000 users
- Assuming 1 request every 10 seconds per user = 5,000 req/s (peak)
- Nginx handles this easily

**Droplets needed**: 1 (can be on same droplet as vertical)

**Bottleneck**: NO

### 2. Vertical Construction (FastAPI)

**Capacity**:
- FastAPI is async, very efficient
- A 4GB droplet can handle **500-1000 requests/second**

**For 1000 tenants**:
- Estimated traffic: 500-2000 req/s at peak
- 1 4GB droplet handles this

**When to scale horizontally**:
- If average response > 200ms consistently
- If CPU > 80% for prolonged periods

**Droplets needed**: 1 (up to ~500 tenants), 2-3 (1000 tenants with margin)

**Bottleneck**: LOW RISK

### 3. Engines Worker (Redis Streams Consumer)

**Capacity**:
- Async processing, doesn't affect user latency
- One worker processes **100-500 events/second**

**For 1000 tenants**:
- Estimated events: ~10,000-50,000 events/day
- = ~0.5-2 events/second (average)
- Peaks: maybe 10-20 events/second
- 1 worker handles this easily

**When to scale**:
- If event backlog > 10,000 pending
- If processing delay > 5 minutes

**Droplets needed**: 1 (shared or dedicated 2GB)

**Bottleneck**: NO

### 4. Redis Streams (Event Bus)

**Capacity**:
- Redis Streams can handle **100,000+ messages/second**
- Memory: ~100 bytes per event

**For 1000 tenants**:
- 50,000 events/day = ~5MB/day of memory (without long retention)
- 1GB Redis droplet is more than sufficient

**Bottleneck**: NO

### 5. PostgreSQL (Database)

**Capacity**:
- Depends on queries and indexes
- 4-8GB droplet can handle **1000-5000 queries/second** (simple queries)

**For 1000 tenants**:
- Simple queries with index on `tenant_id`: very fast
- All filters by tenant_id are indexed

**Critical indexes**:
```sql
CREATE INDEX idx_cotacoes_tenant_status ON cotacoes(tenant_id, status);
CREATE INDEX idx_pedidos_tenant_status ON pedidos(tenant_id, status);
CREATE INDEX idx_clientes_tenant ON clientes(tenant_id);
```

**When to scale**:
- If query time > 100ms consistently
- If active connections > 100 for long periods
- If disk > 80%

**Droplets needed**: 1 managed database (4-8GB) or dedicated droplet

**Bottleneck**: MEDIUM RISK (most likely point of attention)

### 6. Auth

**Current situation**: Auth integrated in vertical (JWT)

**For 1000 tenants**:
- JWT is stateless, no pressure on auth
- Token validation is local (decode only)

**Single point of failure**: NO (each vertical validates its own token)

**Bottleneck**: NO

---

## Resource Summary

### Minimum Configuration (up to 200 tenants)

| Component | Droplet | RAM | Cost/month (DO) |
|-----------|---------|-----|------------------|
| Vertical + Nginx | 1 | 4GB | ~$24 |
| Engines + Relay | 1 | 2GB | ~$12 |
| PostgreSQL | Managed | 2GB | ~$25 |
| Redis | 1 | 1GB | ~$6 |
| **Total** | 3-4 | 9GB | **~$67** |

### Recommended Configuration (up to 500 tenants)

| Component | Droplet | RAM | Cost/month (DO) |
|-----------|---------|-----|------------------|
| Vertical + Nginx | 1 | 4GB | ~$24 |
| Engines + Relay | 1 | 2GB | ~$12 |
| PostgreSQL | Managed | 4GB | ~$50 |
| Redis | 1 | 1GB | ~$6 |
| **Total** | 3-4 | 11GB | **~$92** |

### Configuration for 1000 tenants

| Component | Droplet | RAM | Cost/month (DO) |
|-----------|---------|-----|------------------|
| Nginx | 1 | 2GB | ~$12 |
| Vertical | 2 | 4GB each | ~$48 |
| Engines | 1 | 2GB | ~$12 |
| Relay | 1 | 1GB | ~$6 |
| PostgreSQL | Managed | 8GB | ~$100 |
| Redis | 1 | 2GB | ~$12 |
| **Total** | 6-7 | ~25GB | **~$190** |

---

## Where It Breaks First?

**Order of pressure** (most likely to least likely):

1. **PostgreSQL** - Complex queries or data volume
2. **Vertical (FastAPI)** - Too many concurrent requests
3. **Engines Worker** - Event backlog
4. **Redis** - Unlikely before 10,000 tenants
5. **Nginx** - Unlikely before 100,000 tenants

---

## What to Scale First?

### If PostgreSQL becomes bottleneck:
1. Add read replicas
2. Increase RAM of managed database
3. Optimize queries (EXPLAIN ANALYZE)
4. Consider partitioning by tenant_id (unlikely necessary)

### If Vertical becomes bottleneck:
1. Add second droplet
2. Load balancer (Nginx upstream with multiple backends)
3. No code changes needed (stateless)

### If Engines become bottleneck:
1. Add more workers (same consumer group)
2. Redis Streams supports multiple consumers natively
3. Just start more worker instances

---

## What NOT to Do Now

1. **Kubernetes** - Unnecessary complexity for < 5,000 tenants
2. **Database sharding** - tenant_id index is sufficient
3. **CDC (Change Data Capture)** - Outbox pattern works well
4. **External message broker** - Redis Streams is sufficient
5. **Service mesh** - Direct communication is simpler
6. **Distributed cache** - Local cache or simple Redis is enough
7. **Multiple databases per tenant** - Isolation by tenant_id is sufficient

---

## Metrics to Monitor

### Critical Alerts

| Metric | Threshold | Action |
|-------|-----------|--------|
| P95 Latency | > 500ms | Investigate |
| Vertical CPU | > 80% for 5min | Scale |
| DB Connections | > 80 | Increase pool |
| Pending events | > 5000 | Add worker |
| DB Disk | > 80% | Increase disk |

### Recommended Dashboards

- Requests/second per endpoint
- Latency P50/P95/P99
- Events processed/minute
- Active connections to DB
- Memory usage per service

---

## Conclusion

**Current architecture supports 1000 clients with headroom.**

- Infrastructure costs: ~$100-200/month
- No need for Kubernetes
- No need for sharding
- Simple horizontal scaling when needed

**First point of attention**: PostgreSQL (monitor queries and indexes)

**When to rethink architecture**: > 5,000 tenants or very different use cases
