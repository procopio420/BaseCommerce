# System Components

Platform components and their responsibilities.

## Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         NGINX                                    │
│              *.basecommerce.com.br → X-Tenant-Slug               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      VERTICAIS                                   │
│                                                                  │
│   Construction Vertical (apps/verticals/construction/)          │
│   ├── API REST (/api/v1/*)                                      │
│   ├── Web HTMX (/web/*)                                         │
│   └── Domain (cotacoes, pedidos, clientes, produtos)            │
│                                                                  │
│   Future: food, retail, etc.                                    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Events (Outbox Pattern)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EVENT INFRASTRUCTURE                          │
│                                                                  │
│   Outbox Relay (DB → Redis Streams)                             │
│   Redis Streams (Event Bus)                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ XREADGROUP
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  HORIZONTAL ENGINES                              │
│                                                                  │
│   Stock Intelligence    - WHAT/WHEN/HOW MUCH to buy              │
│   Sales Intelligence    - Sales suggestions                     │
│   Pricing & Supplier    - FROM WHOM to buy, AT WHAT COST        │
│   Delivery & Fulfillment - Order → Delivery → Confirmation      │
│                                                                  │
│   Write to engine-owned tables, do NOT import verticals         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      POSTGRESQL                                  │
│              Multi-tenant by tenant_id in all tables            │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
basecommerce/
├── apps/
│   ├── auth/                    # Auth service
│   ├── engines/                 # Event consumer worker
│   ├── outbox-relay/            # Relay DB → Redis Streams
│   └── verticals/
│       └── construction/        # Construction materials vertical
├── packages/
│   ├── basecore/               # Shared infrastructure
│   └── engines_core/           # Engine logic
├── infra/
│   └── nginx/                  # Multi-tenant Nginx config
└── docs/                       # Documentation
```

## Component Responsibilities

### Nginx
- Subdomain extraction and tenant routing
- Header injection (X-Tenant-Slug)
- Reverse proxy to Auth Service and Verticals
- Rate limiting and security

### Auth Service
- User authentication (JWT generation)
- Tenant and user management
- Tenant branding configuration
- `/tenant.json` endpoint for frontend

### Verticals
- Domain-specific business logic
- REST API endpoints (`/api/v1/*`)
- HTMX web interface (`/web/*`)
- Event publishing (Outbox Pattern)

### Outbox Relay
- Polls `event_outbox` table
- Publishes events to Redis Streams
- Ensures reliable event delivery

### Redis Streams
- Event bus for async communication
- Consumer groups for parallel processing
- Message persistence and replay

### Engines Worker
- Consumes events from Redis Streams
- Routes to appropriate engine handlers
- Writes to engine-owned tables
- Idempotent processing

### Engines
- **Stock Intelligence**: Inventory management and reorder suggestions
- **Sales Intelligence**: Cross-sell and upsell recommendations
- **Pricing & Supplier**: Supplier comparison and cost optimization
- **Delivery & Fulfillment**: Order fulfillment and delivery tracking

### PostgreSQL
- Source of truth for all business data
- Row-level tenant isolation
- Event outbox table
- Engine-owned tables
