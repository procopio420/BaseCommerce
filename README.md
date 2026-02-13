# BaseCommerce

Multi-tenant vertical SaaS platform designed for commerce verticals (starting with construction materials). Built with event-driven architecture, modular engines, and tenant isolation at infrastructure level.

## Core Principles

- Vertical-first architecture
- Multi-tenant by design
- Event-driven domain logic
- Modular engines
- Operational simplicity (VPS-friendly)

## Architecture Overview

The platform follows a layered architecture with clear separation between verticals (domain-specific applications) and horizontal engines (reusable intelligence modules).

**API Layer**: FastAPI serves both REST APIs (`/api/v1/*`) and HTMX web interfaces (`/web/*`). The Auth Service centralizes authentication and tenant management.

**Tenant-Aware Routing**: Nginx extracts tenant slug from subdomain and injects `X-Tenant-Slug` header. All downstream services use JWT claims containing `tenant_id` for data isolation.

**PostgreSQL as Source of Truth**: All business data stored in PostgreSQL with row-level tenant isolation via `tenant_id` in every table.

**Redis Streams for Domain Events**: Event-driven communication between verticals and engines via Redis Streams, using the Outbox Pattern for reliability.

**Outbox Pattern for Reliability**: Events are written to `event_outbox` table in the same transaction as business data, then relayed to Redis Streams by the Outbox Relay service.

**Engines as Async Domain Processors**: Horizontal engines (Stock, Sales, Pricing, Delivery) consume events and write to engine-owned tables, never importing vertical code.

```
┌─────────────┐
│   Nginx     │ *.basecommerce.com.br → X-Tenant-Slug
└──────┬──────┘
       │
   ┌───┴───┐
   ▼       ▼
┌──────┐ ┌──────────────┐
│ Auth │ │ Construction │
│ :8001│ │   :8000      │
└───┬──┘ └──────┬───────┘
    │           │
    └─────┬─────┘
          │ Events (Outbox)
          ▼
    ┌──────────┐
    │PostgreSQL│
    └────┬─────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌──────────────┐
│Outbox  │ │ Redis Streams│
│Relay   │ └──────┬───────┘
└────────┘         │
                  ▼
            ┌──────────┐
            │  Engines │
            │  Worker  │
            └──────────┘
```

## Project Structure

```
apps/
  engines/              # Event consumer worker
  outbox-relay/         # DB → Redis Streams relay
  verticals/
    construction/       # Construction materials vertical

packages/
  basecore/            # Shared infrastructure (db, redis, security)
  engines_core/        # Engine logic and contracts

infra/
  nginx/               # Multi-tenant Nginx configuration
  envs/                # Environment-specific deployments
  cli/                 # Infrastructure CLI (basec)
```

**Separation of Concerns**:
- Verticals own domain models and business logic
- Engines own intelligence and analytics
- BaseCore provides shared infrastructure
- No cross-imports between verticals and engines (communication via events only)

## Multi-Tenancy Model

**Tenant Identification**: Subdomain-based routing (e.g., `acme.basecommerce.com.br`). Nginx extracts subdomain and injects `X-Tenant-Slug` header.

**Isolation Strategy**: Row-level security via `tenant_id` in all tables. Auth Service centralizes tenant/user management. Verticals extract `tenant_id` from JWT claims (no database queries for tenant resolution).

**Vertical Integration**: Verticals are tenant-aware by default. Each vertical implements domain-specific models but shares the same tenant isolation mechanism.

## Development Setup

```bash
# Start all services
docker-compose up -d

# Run migrations
docker-compose exec construction alembic upgrade head

# Access local tenant
open http://demo.localhost/web/login
```

**Service Names**:
- `postgres`: PostgreSQL database
- `redis`: Redis for event streams
- `construction`: Construction vertical (FastAPI)
- `auth`: Auth service
- `nginx`: Reverse proxy
- `outbox-relay`: Event relay service
- `engines-worker`: Event consumer

**Local Tenant Access**: Add to `/etc/hosts`:
```
127.0.0.1 demo.localhost
```

Then access `http://demo.localhost/web/login`. Default credentials are created via migration scripts.

## Deployment Model

**VPS-First Deployment**: Platform runs on DigitalOcean droplets (~$24/month for 3 droplets). No Kubernetes, no serverless.

**Nginx Multi-Tenant Config**: Edge droplet runs Nginx with subdomain-based routing. All traffic flows through Nginx which injects tenant headers.

**Reverse Proxy Setup**: Nginx proxies to Auth Service (`:8001`) and Vertical apps (`:8000`). Internal services communicate via private network.

**Environment Isolation**: Separate environments (production, staging, development) with isolated databases and Redis instances.

**Scaling**: Horizontal scaling by adding more vertical droplets behind load balancer. Engines scale independently. Database can be upgraded or moved to managed service.

## Why This Architecture?

**Vertical SaaS**: Each commerce vertical (construction, retail, food) has unique domain models but shares common intelligence engines. This allows rapid vertical expansion while maintaining code reuse.

**Multi-Tenant from Day One**: Row-level isolation prevents data leakage and simplifies operations. No per-tenant infrastructure overhead.

**Event-Driven**: Decouples verticals from engines, enabling independent deployment and scaling. Outbox Pattern ensures reliability without distributed transactions.

**Modular Engines**: Engines are reusable across verticals. Stock Intelligence works for construction materials, retail inventory, and food supplies with the same logic.

**VPS-Friendly Infrastructure**: Avoids Kubernetes complexity for a platform that doesn't need it. Simple Docker Compose deployments, straightforward monitoring, predictable costs. Scale when needed, not before.

## Documentation

Deep documentation lives under `/docs` organized by category:

- **Architecture**: System design, component interactions, data flow
- **Infrastructure**: Deployment, VPS setup, Nginx configuration
- **Multi-Tenancy**: Tenant isolation, routing, JWT claims
- **Engines**: Engine contracts, event handling, intelligence modules
- **Product**: Domain model, user flows, roadmap
- **Reference**: Database schema, event contracts, API specifications

See [docs/index.md](docs/index.md) for the complete documentation structure.

## Stack

Python 3.11 · FastAPI · HTMX · PostgreSQL · Redis Streams · Nginx · VPS
