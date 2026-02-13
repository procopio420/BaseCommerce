# Architecture Overview

BaseCommerce is a multi-tenant, multi-vertical SaaS platform for commerce. Each vertical (e.g., construction materials) has its own application that consumes reusable horizontal engines.

## Logical Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx                                    │
│              (Reverse Proxy + Multi-tenant Routing)              │
│         *.basecommerce.com.br → X-Tenant-Slug header             │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP
              ┌──────────────┴──────────────┐
              ▼                             ▼
┌──────────────────────┐     ┌──────────────────────────────────────┐
│    Auth Service      │     │           Verticals Layer            │
│    (FastAPI :8001)   │     │                                      │
│                      │     │   ┌──────────────────────────────┐   │
│  - /auth/login       │     │   │  Construction Vertical       │   │
│  - /auth/logout      │     │   │  (FastAPI :8000)              │   │
│  - /auth/me          │     │   │                              │   │
│  - /tenant.json      │     │   │  - /api/v1/* (REST)          │   │
│                      │     │   │  - /web/*    (HTMX)          │   │
│  Owns:               │     │   └──────────────────────────────┘   │
│  - Tenant model      │     │                                      │
│  - User model        │     │   Uses: UserClaims from JWT          │
│  - TenantBranding    │     │   (no User/Tenant models)            │
└──────────────────────┘     └──────────────────────────────────────┘
              │                             │
              └──────────────┬──────────────┘
                             │ Events (Outbox Pattern)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Event Infrastructure                           │
│                                                                  │
│   ┌────────────────┐       ┌────────────────┐                   │
│   │  Outbox Relay  │ ───→  │ Redis Streams  │                   │
│   │  (DB Polling)  │       │ (Event Bus)    │                   │
│   └────────────────┘       └───────┬────────┘                   │
│                                    │                             │
└────────────────────────────────────┼────────────────────────────┘
                                     │ XREADGROUP
                                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Horizontal Engines                             │
│                                                                  │
│   ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │
│   │ Stock          │  │ Pricing &      │  │ Delivery &     │   │
│   │ Intelligence   │  │ Supplier       │  │ Fulfillment    │   │
│   └────────────────┘  └────────────────┘  └────────────────┘   │
│                                                                  │
│   ┌────────────────┐                                            │
│   │ Sales          │                                            │
│   │ Intelligence   │                                            │
│   └────────────────┘                                            │
│                                                                  │
│   - Consume events via Redis Streams                            │
│   - Write to engine-owned tables                                │
│   - Do NOT import vertical code                                 │
└────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      PostgreSQL                                  │
│                 (Multi-tenant by tenant_id)                      │
│                                                                  │
│   - Auth tables (tenants, users, tenant_branding)              │
│   - Vertical tables (cotacoes, pedidos, etc.)                   │
│   - Engine tables (engine_*, suggestions, alerts)               │
│   - Event outbox for Outbox Pattern                             │
└─────────────────────────────────────────────────────────────────┘
```

## Core Principles

1. **Verticals do NOT import engines** - Communication via events only
2. **Engines do NOT import verticals** - Only use basecore + engines_core
3. **Tenant resolved by Nginx** - X-Tenant-Slug header
4. **Events are the only communication** - Outbox Pattern ensures delivery
5. **VPS-only** - No Kubernetes, no serverless

## Auth Service

The Auth Service is centralized and responsible for:

- **Authentication**: Login/logout via JWT
- **Tenant Resolution**: Endpoint `/tenant.json` returns tenant branding
- **User Management**: Tenant, User, TenantBranding models

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | GET | Login page (HTML) |
| `/auth/login` | POST | Login JSON, returns JWT |
| `/auth/login/form` | POST | Login form, sets cookie |
| `/auth/logout` | GET | Clear cookie, redirect |
| `/auth/me` | GET | User info (Bearer/cookie) |
| `/tenant.json` | GET | Branding (via X-Tenant-Slug) |
| `/auth/validate` | GET | Validate token |

### Login Flow

```
1. User accesses /web/dashboard
2. Nginx redirects /web/login → /auth/login
3. Auth Service renders login page
4. User submits form to /auth/login/form
5. Auth Service validates credentials
6. Auth Service creates JWT with claims:
   - sub: user_id
   - tenant_id: tenant_id
   - email: user_email
   - role: user_role
7. Auth Service sets httponly cookie
8. Redirect to /web/dashboard
9. Vertical extracts claims from JWT (no database query)
```

## Domain Entities

### Tenant (Store)
- Represents a store or client company
- Each tenant has complete data isolation
- Resolved via subdomain (e.g., `store.basecommerce.com.br`)
- **Managed by Auth Service**

### User
- User within a tenant
- Roles: admin, vendedor (salesperson)
- **Managed by Auth Service**

### Cliente (Customer)
- PF (Individual) or PJ (Company)
- Linked to a tenant
- Can have multiple obras (construction sites)

### Obra (Construction Site - Optional)
- Linked to a customer
- Allows differentiated pricing per site

### Produto (Product)
- Store product catalog
- Base price per product
- Linked to tenant

### Cotacao (Quote)
- List of products with quantities
- Price rules applied
- Status: draft → sent → approved → converted
- Versioned history

### Pedido (Order)
- Converted from a quote
- Represents a confirmed order
- Basic delivery status

## Data Flow

1. **Quote Creation**
   - Select customer (and optionally obra)
   - Add products with quantities
   - Apply price rules (discount)
   - Save as draft

2. **Quote Sending**
   - Mark status as "sent"
   - Customer views (future feature)

3. **Approval**
   - Customer approves (manual or future system)

4. **Order Conversion**
   - One-click converts approved quote to order
   - Order inherits all quote items
   - Event emitted to engines (via outbox)

## Multi-Tenancy

**Strategy**: Subdomain + JWT Claims + Middleware

- Nginx resolves subdomain and injects `X-Tenant-Slug` header
- Auth Service resolves tenant from header and generates JWT
- JWT contains `tenant_id` in claims
- Vertical extracts `tenant_id` from JWT (no database query)
- All queries filtered by `tenant_id`

## Event-Driven Architecture

**Pattern**: Outbox Pattern + Redis Streams

1. Vertical writes event to `event_outbox` table (same transaction)
2. Outbox Relay polls and publishes to Redis Streams
3. Engines consume via XREADGROUP (consumer groups)
4. Idempotency guaranteed via `engine_processed_events`

## Security

- JWT for authentication (created by Auth Service)
- Tenant isolation via JWT claims
- Data validation on all inputs
- HttpOnly cookies for web
- HTTPS in production
- Auth Service centralizes user management
