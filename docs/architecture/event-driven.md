# Event-Driven Architecture

The platform uses the **Outbox Pattern** to ensure reliable event delivery.

## Event Flow

```
Vertical (write)
      │
      ▼
┌─────────────────┐
│  Same transaction│
│  - INSERT order  │
│  - INSERT outbox │
│  COMMIT          │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Outbox Relay    │
│  (polling DB)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Redis Streams  │
│  (event bus)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Engines Worker │
│  (XREADGROUP)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Engine Tables  │
│  (engine-owned) │
└─────────────────┘
```

## Publishing Events (Vertical)

```python
from construction_app.platform.events.publisher import publish_event

# In the same transaction as the main write
with db.begin():
    pedido = Pedido(...)
    db.add(pedido)
    
    publish_event(
        db=db,
        event_type="sale_recorded",
        tenant_id=tenant_id,
        payload={
            "pedido_id": str(pedido.id),
            "cliente_id": str(pedido.cliente_id),
            "itens": [...],
            "valor_total": float(pedido.valor_total),
        }
    )
    # COMMIT happens here - both or neither
```

## Consuming Events (Engines)

The worker in `apps/engines/` consumes events via Redis Streams:

```python
# engines_core/consumer.py

messages = read_from_stream(
    stream_name="events:materials",
    group_name="engines",
    consumer_name="engines-worker",
    count=10,
    block_ms=5000,
)

for msg_id, data in messages:
    envelope = parse_stream_message(msg_id, data)
    result = handle_event(db, envelope)  # Routes to handler
    ack_message(stream_name, group_name, msg_id)
```

## Event Types

| Event | When | Payload |
|-------|------|---------|
| `quote_created` | Quote created | quote_id, cliente_id, items |
| `quote_converted` | Quote → Order | quote_id, pedido_id |
| `sale_recorded` | Order created | pedido_id, items, valor_total |
| `order_delivered` | Order delivered | pedido_id, delivery_date |

## Available Engines

### Stock Intelligence

**Responsibility**: WHAT to buy, WHEN to buy, HOW MUCH to buy

- Consumes: `sale_recorded`, `order_delivered`
- Produces: Stockout alerts, reorder suggestions
- Tables: `engine_stock_*`

### Sales Intelligence

**Responsibility**: Increase sale value

- Consumes: `sale_recorded`, `quote_created`
- Produces: Complementary product suggestions
- Tables: `engine_sales_*`

### Pricing & Supplier Intelligence

**Responsibility**: FROM WHOM to buy, AT WHAT COST

- Consumes: Supplier events (future)
- Produces: Supplier comparison, base cost
- Tables: `engine_pricing_*`

### Delivery & Fulfillment

**Responsibility**: Order → Delivery → Confirmation

- Consumes: `order_delivered`
- Produces: Routes, status, delivery proof
- Tables: `engine_delivery_*`

## Idempotency

Events are processed idempotently:

```sql
CREATE TABLE engine_processed_events (
    event_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    processed_at TIMESTAMP DEFAULT now(),
    result JSONB
);
```

Before processing:
```python
if is_event_processed(db, event_id):
    return  # Skip - already processed

# Process...

mark_event_processed(db, event_id, tenant_id, event_type, result)
```

## Isolation Rules

1. **Engines do NOT import verticals**
   ```python
   # WRONG
   from construction_app.models import Pedido
   
   # CORRECT
   from engines_core.contracts.envelope import EventEnvelope
   from basecore.db import get_db
   ```

2. **Engines use only**:
   - `packages/basecore/` (db, redis, settings)
   - `packages/engines_core/` (handlers, contracts)

3. **Engine data in own tables**:
   - Prefix `engine_*`
   - Never modify vertical tables

## Debugging

### View pending events

```sql
SELECT * FROM event_outbox 
WHERE status = 'pending' 
ORDER BY created_at DESC 
LIMIT 10;
```

### View events processed by engines

```sql
SELECT * FROM engine_processed_events 
ORDER BY processed_at DESC 
LIMIT 10;
```

### Worker logs

```bash
docker-compose logs -f engines-worker
```
