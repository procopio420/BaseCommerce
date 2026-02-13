# Contratos de Eventos

## Versão: 2.4 - Plataforma Foundations

**Data**: Janeiro 2026

---

## 📋 Visão Geral

Este documento define todos os eventos que podem ser publicados pela plataforma, seus payloads e contratos.

**Princípios**:
- Eventos são imutáveis (append-only)
- Payloads são versionados
- Eventos incluem `tenant_id` para isolamento
- Eventos incluem `event_id` e `timestamp` para rastreabilidade

---

## 🎯 Categorias de Eventos

### Eventos do Vertical "Materiais de Construção"

Estes eventos são publicados quando ações importantes acontecem no vertical.

#### 1. `quote_created`

**Descrição**: Cotação foi criada

**Publicado por**: Vertical Materiais (CotacaoService)

**Quando**: Após criar cotação com sucesso

**Payload**:
```json
{
  "event_type": "quote_created",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "timestamp": "2026-01-15T10:30:00Z",
  "version": "1.0",
  "payload": {
    "quote_id": "uuid",
    "client_id": "uuid",
    "user_id": "uuid",
    "work_id": "uuid | null",
    "total_value": "1000.50",
    "discount_percentage": "5.00",
    "items_count": 3,
    "items": [
      {
        "product_id": "uuid",
        "quantity": "10.000",
        "unit_price": "32.00",
        "total_value": "320.00"
      }
    ]
  }
}
```

**Consumidores**: 
- Sales Intelligence Engine (para análise de padrões de compra)

---

#### 2. `quote_converted`

**Descrição**: Cotação foi convertida em pedido

**Publicado por**: Vertical Materiais (PedidoService)

**Quando**: Após converter cotação em pedido com sucesso (na mesma transação)

**Payload**:
```json
{
  "event_type": "quote_converted",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "timestamp": "2026-01-15T10:35:00Z",
  "version": "1.0",
  "payload": {
    "quote_id": "uuid",
    "order_id": "uuid",
    "client_id": "uuid",
    "user_id": "uuid",
    "work_id": "uuid | null",
    "total_value": "950.48",
    "converted_at": "2026-01-15T10:35:00Z",
    "items": [
      {
        "product_id": "uuid",
        "quantity": "10.000",
        "unit_price": "32.00",
        "total_value": "320.00"
      }
    ]
  }
}
```

**Consumidores**:
- Sales Intelligence Engine (para registrar venda)
- Delivery & Fulfillment Engine (para planejar entrega)

---

#### 3. `sale_recorded`

**Descrição**: Venda foi registrada (pedido entregue)

**Publicado por**: Vertical Materiais (PedidoService)

**Quando**: Após marcar pedido como "entregue"

**Payload**:
```json
{
  "event_type": "sale_recorded",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "timestamp": "2026-01-15T14:00:00Z",
  "version": "1.0",
  "payload": {
    "order_id": "uuid",
    "quote_id": "uuid | null",
    "client_id": "uuid",
    "work_id": "uuid | null",
    "delivered_at": "2026-01-15T14:00:00Z",
    "total_value": "950.48",
    "items": [
      {
        "product_id": "uuid",
        "quantity": "10.000",
        "unit_price": "32.00",
        "total_value": "320.00"
      }
    ]
  }
}
```

**Consumidores**:
- Stock Intelligence Engine (para atualizar estoque)
- Sales Intelligence Engine (para análise de vendas)

---

#### 4. `order_status_changed`

**Descrição**: Status do pedido foi alterado

**Publicado por**: Vertical Materiais (PedidoService)

**Quando**: Após atualizar status do pedido

**Payload**:
```json
{
  "event_type": "order_status_changed",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "timestamp": "2026-01-15T12:00:00Z",
  "version": "1.0",
  "payload": {
    "order_id": "uuid",
    "old_status": "em_preparacao",
    "new_status": "saiu_entrega",
    "changed_at": "2026-01-15T12:00:00Z",
    "changed_by": "uuid | null"
  }
}
```

**Consumidores**:
- Delivery & Fulfillment Engine (quando `new_status = "saiu_entrega"`)

---

### Eventos Futuros (Não Implementados na Fase 2.4)

#### 5. `product_price_updated` (Futuro)

**Descrição**: Preço de produto foi atualizado

**Publicado por**: Vertical Materiais (ProdutoService)

**Quando**: Após atualizar preço de produto

**Payload**:
```json
{
  "event_type": "product_price_updated",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "timestamp": "2026-01-15T09:00:00Z",
  "version": "1.0",
  "payload": {
    "product_id": "uuid",
    "old_price": "32.00",
    "new_price": "35.00",
    "updated_by": "uuid"
  }
}
```

**Consumidores**:
- Pricing & Supplier Intelligence Engine (para análise de variação)

---

#### 6. `stock_updated` (Futuro)

**Descrição**: Estoque foi atualizado manualmente

**Publicado por**: Vertical Materiais ou Stock Intelligence Engine

**Quando**: Após atualização manual de estoque

**Payload**:
```json
{
  "event_type": "stock_updated",
  "event_id": "uuid",
  "tenant_id": "uuid",
  "timestamp": "2026-01-15T11:00:00Z",
  "version": "1.0",
  "payload": {
    "product_id": "uuid",
    "old_quantity": "100.000",
    "new_quantity": "150.000",
    "movement_type": "entrada",
    "reason": "compra_fornecedor",
    "updated_by": "uuid"
  }
}
```

**Consumidores**:
- Stock Intelligence Engine (para recalcular alertas)

---

## 📝 Estrutura de Evento (Contrato Base)

Todos os eventos seguem esta estrutura:

```json
{
  "event_type": "string (required)",
  "event_id": "uuid (required)",
  "tenant_id": "uuid (required)",
  "timestamp": "ISO 8601 datetime (required)",
  "version": "string (required, ex: '1.0')",
  "payload": {
    // Event-specific payload
  }
}
```

### Campos Obrigatórios

- **`event_type`**: Tipo do evento (enum fixo)
- **`event_id`**: UUID único do evento
- **`tenant_id`**: UUID do tenant (isolamento multi-tenant)
- **`timestamp`**: Quando o evento foi criado (ISO 8601)
- **`version`**: Versão do contrato do evento (para evolução)
- **`payload`**: Dados específicos do evento (varia por tipo)

---

## 🔄 Versionamento de Eventos

### Regras de Versionamento

1. **Breaking Changes**: Incrementa versão major (1.0 → 2.0)
   - Remoção de campo obrigatório
   - Mudança de tipo de campo
   - Mudança de estrutura de payload

2. **Non-Breaking Changes**: Incrementa versão minor (1.0 → 1.1)
   - Adição de campo opcional
   - Mudança de documentação
   - Melhoria de formato

3. **Patches**: Incrementa versão patch (1.0.0 → 1.0.1)
   - Correções de bugs
   - Ajustes menores

### Compatibilidade

- **Handlers devem suportar múltiplas versões** do mesmo evento
- **Novos campos opcionais** não quebram handlers antigos
- **Handlers devem validar versão** antes de processar

---

## 🎯 Event Types (Enum)

```python
# app/platform/events/types.py

class EventType(str, Enum):
    # Vertical Materiais de Construção
    QUOTE_CREATED = "quote_created"
    QUOTE_CONVERTED = "quote_converted"
    SALE_RECORDED = "sale_recorded"
    ORDER_STATUS_CHANGED = "order_status_changed"
    
    # Futuros
    PRODUCT_PRICE_UPDATED = "product_price_updated"
    STOCK_UPDATED = "stock_updated"
```

---

## 📊 Matriz de Consumo (Eventos → Engines)

| Evento | Stock Intelligence | Sales Intelligence | Pricing & Supplier | Delivery & Fulfillment |
|--------|-------------------|-------------------|-------------------|----------------------|
| `quote_created` | ❌ | ✅ | ❌ | ❌ |
| `quote_converted` | ❌ | ✅ | ❌ | ✅ |
| `sale_recorded` | ✅ | ✅ | ❌ | ❌ |
| `order_status_changed` | ❌ | ❌ | ❌ | ✅ (se "saiu_entrega") |

---

## 🧪 Exemplos de Uso

### Publicar Evento (Vertical)

```python
from app.platform.events.publisher import publish_event

# Na mesma transação do write principal
publish_event(
    event_type=EventType.QUOTE_CONVERTED,
    tenant_id=tenant_id,
    payload={
        "quote_id": str(cotacao.id),
        "order_id": str(pedido.id),
        # ... resto do payload
    }
)
```

### Processar Evento (Engine Handler)

```python
from app.platform.events.types import EventType

@event_handler(EventType.SALE_RECORDED)
def handle_sale_recorded(tenant_id: UUID, payload: dict):
    # Atualiza estoque baseado nos itens vendidos
    for item in payload["items"]:
        update_stock(
            tenant_id=tenant_id,
            product_id=item["product_id"],
            quantity=-item["quantity"]  # Reduz estoque
        )
```

---

## ✅ Checklist de Validação

Para adicionar um novo evento:

- [ ] Evento está documentado neste arquivo
- [ ] Payload está definido em JSON
- [ ] Versão está especificada
- [ ] `tenant_id` está incluído
- [ ] Evento foi adicionado ao enum `EventType`
- [ ] Handler(s) foram criados para os engines consumidores
- [ ] Testes foram criados para publicação e consumo

---

**Versão**: 1.0  
**Data**: Janeiro 2026  
**Status**: 📋 Contratos Iniciais - Implementação em Progresso

