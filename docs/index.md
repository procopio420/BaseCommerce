# Documentation Index

BaseCommerce documentation organized by category.

## Architecture

System design, component interactions, and data flow.

- [Overview](architecture/overview.md) - System architecture and core principles
- [Components](architecture/components.md) - Component responsibilities and structure
- [Event-Driven](architecture/event-driven.md) - Event-driven architecture and Outbox Pattern
- [Frontend](architecture/frontend.md) - HTMX frontend architecture

## Infrastructure

Deployment, VPS setup, and infrastructure configuration.

- [Services](infrastructure/services.md) - PostgreSQL, Redis, Nginx components
- [Development](infrastructure/development.md) - Local development setup
- [Deployment](infrastructure/deployment.md) - Production deployment guide
- [Scaling](infrastructure/scaling.md) - Scalability analysis and scaling strategies
- [Topology](infrastructure/topology.md) - Infrastructure topology and design decisions

## Multi-Tenancy

Tenant isolation, routing, and JWT claims.

- [Routing](multi-tenancy/routing.md) - Subdomain-based routing and tenant resolution

## Engines

Engine contracts, event handling, and intelligence modules.

- [API Contracts](engines/api-contracts.md) - Engine API specifications
- [Stock](engines/stock.md) - Stock Intelligence engine
- [Sales](engines/sales.md) - Sales Intelligence engine
- [Pricing](engines/pricing.md) - Pricing & Supplier Intelligence engine
- [Delivery](engines/delivery.md) - Delivery & Fulfillment engine

## Product

Domain model, user flows, and product roadmap.

- [Vision](product/vision.md) - Product vision and goals
- [Domain Model](product/domain-model.md) - Domain entities and relationships
- [User Roles](product/user-roles.md) - User roles and permissions
- [Core Flows](product/core-flows.md) - Main user flows
- [Modules & Phases](product/modules-phases.md) - Product roadmap
- [Non-Goals](product/non-goals.md) - What we're not building
- [Risks](product/risks.md) - Assumptions and risks
- [Metrics](product/metrics.md) - Success metrics

## Reference

Database schema, event contracts, and API specifications.

- [Database Schema](reference/database-schema.md) - Complete database schema
- [Event Contracts](reference/event-contracts.md) - Event type definitions
- [UX Flow](reference/ux-flow.md) - User experience flow
- [WhatsApp](reference/whatsapp.md) - WhatsApp messaging integration

## Quick Start

1. Read [Architecture Overview](architecture/overview.md) for system design
2. Follow [Development Setup](infrastructure/development.md) for local development
3. Review [Multi-Tenancy Routing](multi-tenancy/routing.md) for tenant isolation
4. Check [Event-Driven Architecture](architecture/event-driven.md) for event flow

