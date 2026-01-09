"""
Engines Core - Horizontal Engines Runtime

This package is completely independent from any vertical domain code.
It provides:
- Event contracts (envelope, types)
- Engine-owned persistence models
- Engine implementations
- Event handlers routing

Verticals communicate with engines ONLY via:
- DB outbox (transactional event publishing)
- Redis Streams event bus (via relay)
- Engine-owned read model tables (queried by vertical APIs)

NO imports from vertical code (models, schemas, services, etc.) are allowed.
"""

