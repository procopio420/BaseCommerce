# Contratos de Engines (APIs Internas)

## Versão: 2.4 - Plataforma Foundations

**Data**: Janeiro 2026

---

## 📋 Visão Geral

Este documento define os contratos de API dos engines (interfaces, DTOs, versionamento).

**Princípios**:
- APIs são internas (admin-only)
- Contratos são versionados
- DTOs são claros e bem definidos
- Engines podem evoluir independentemente

---

## 🔧 Stock Intelligence Engine

### Base Path
`/api/v1/engines/stock`

### Port (Interface)
`app.core_engines.stock_intelligence.ports.StockIntelligencePort`

### Event Handlers

#### `handle_sale_recorded`

**Evento Consumido**: `sale_recorded`

**Handler**: `app.platform.engines.stock_intelligence.handlers.handle_sale_recorded`

**Lógica**:
- Recebe payload do evento `sale_recorded`
- Para cada item, reduz estoque atual
- Recalcula alertas de risco
- Atualiza histórico de vendas

**Payload Esperado**:
```json
{
  "order_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": "10.000",
      "unit_price": "32.00",
      "total_value": "320.00"
    }
  ]
}
```

### API Endpoints

#### `GET /alerts`

**Descrição**: Retorna alertas de risco de estoque

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant
- `risk_level` (optional): `low`, `medium`, `high`
- `product_ids` (optional): Lista de UUIDs de produtos

**Response**:
```json
{
  "alerts": [
    {
      "produto_id": "uuid",
      "tipo": "risco_ruptura",
      "nivel_risco": "high",
      "estoque_atual": "5.000",
      "estoque_minimo_calculado": "50.000",
      "dias_ate_ruptura": 2,
      "explicacao": "Estoque muito baixo para demanda atual"
    }
  ]
}
```

#### `GET /suggestions`

**Descrição**: Retorna sugestões de reposição

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant
- `product_ids` (optional): Lista de UUIDs de produtos

**Response**:
```json
{
  "suggestions": [
    {
      "produto_id": "uuid",
      "quantidade_sugerida": "100.000",
      "estoque_atual": "5.000",
      "estoque_minimo_calculado": "50.000",
      "explicacao": "Reposição baseada em média de vendas e lead time"
    }
  ]
}
```

#### `POST /update-stock`

**Descrição**: Atualiza estoque manualmente

**Autenticação**: Admin-only

**Request Body**:
```json
{
  "tenant_id": "uuid",
  "produto_id": "uuid",
  "quantidade_atual": "150.000",
  "tipo_movimento": "entrada",
  "observacoes": "Compra de fornecedor"
}
```

**Response**:
```json
{
  "success": true,
  "estoque": {
    "produto_id": "uuid",
    "quantidade_atual": "150.000"
  }
}
```

#### `GET /abc-analysis`

**Descrição**: Retorna análise ABC de produtos

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "analysis": [
    {
      "produto_id": "uuid",
      "classe": "A",
      "valor_total_vendido": "50000.00",
      "percentual_do_total": "70.00",
      "quantidade_vendida": "1000.000"
    }
  ]
}
```

#### `POST /configure-parameters`

**Descrição**: Configura parâmetros de reposição

**Autenticação**: Admin-only

**Request Body**:
```json
{
  "tenant_id": "uuid",
  "produto_id": "uuid",
  "lead_time_dias": 7,
  "estoque_seguranca_percentual": "20.00",
  "estoque_minimo_manual": "50.000",
  "estoque_maximo_manual": "200.000"
}
```

**Response**:
```json
{
  "success": true
}
```

---

## 💡 Sales Intelligence Engine

### Base Path
`/api/v1/engines/sales`

### Port (Interface)
`app.core_engines.sales_intelligence.ports.SalesIntelligencePort`

### Event Handlers

#### `handle_quote_created`

**Evento Consumido**: `quote_created`

**Handler**: `app.platform.engines.sales_intelligence.handlers.handle_quote_created`

**Lógica**:
- Analisa produtos na cotação
- Atualiza histórico de cotações para análise de padrões

**Payload Esperado**:
```json
{
  "quote_id": "uuid",
  "client_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": "10.000",
      "unit_price": "32.00"
    }
  ]
}
```

#### `handle_quote_converted`

**Evento Consumido**: `quote_converted`

**Handler**: `app.platform.engines.sales_intelligence.handlers.handle_quote_converted`

**Lógica**:
- Registra venda no histórico
- Atualiza padrões de compra
- Prepara sugestões futuras

**Payload Esperado**:
```json
{
  "quote_id": "uuid",
  "order_id": "uuid",
  "client_id": "uuid",
  "items": [
    {
      "product_id": "uuid",
      "quantity": "10.000",
      "unit_price": "32.00",
      "total_value": "320.00"
    }
  ]
}
```

#### `handle_sale_recorded`

**Evento Consumido**: `sale_recorded`

**Handler**: `app.platform.engines.sales_intelligence.handlers.handle_sale_recorded`

**Lógica**:
- Finaliza registro de venda
- Atualiza análise de padrões de compra
- Recalcula produtos complementares

**Payload Esperado**: Mesmo de `handle_quote_converted`

### API Endpoints

#### `POST /suggestions`

**Descrição**: Retorna sugestões de produtos

**Autenticação**: Admin-only

**Request Body**:
```json
{
  "tenant_id": "uuid",
  "contexto": "criando_cotacao",
  "cliente_id": "uuid",
  "produtos_no_carrinho": [
    {
      "produto_id": "uuid",
      "quantidade": "10.000"
    }
  ]
}
```

**Response**:
```json
{
  "suggestions": [
    {
      "produto_sugerido_id": "uuid",
      "tipo": "complementar",
      "frequencia": "75.50",
      "prioridade": "alta",
      "explicacao": "75% dos clientes que compram este produto também compram X"
    }
  ]
}
```

#### `GET /complementary/{produto_id}`

**Descrição**: Retorna produtos complementares

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "products": [
    {
      "produto_sugerido_id": "uuid",
      "frequencia": "75.50",
      "prioridade": "alta",
      "explicacao": "..."
    }
  ]
}
```

#### `GET /bundles`

**Descrição**: Retorna bundles sugeridos

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "bundles": [
    {
      "bundle_id": "uuid",
      "produtos": ["uuid", "uuid"],
      "frequencia": "60.00",
      "explicacao": "Estes 2 produtos são vendidos juntos em 60% das vendas"
    }
  ]
}
```

#### `GET /patterns`

**Descrição**: Retorna padrões de compra

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant
- `cliente_id` (optional): UUID do cliente

**Response**:
```json
{
  "patterns": [
    {
      "produtos": ["uuid", "uuid"],
      "frequencia": "50.00",
      "total_vendas": 10
    }
  ]
}
```

---

## 💰 Pricing & Supplier Intelligence Engine

### Base Path
`/api/v1/engines/pricing`

### Port (Interface)
`app.core_engines.pricing_supplier.ports.PricingSupplierPort`

### Event Handlers

**Nenhum handler na Fase 2.4** (engines ainda não consome eventos de preço)

### API Endpoints

#### `POST /register-price`

**Descrição**: Registra preço de fornecedor

**Autenticação**: Admin-only

**Request Body**:
```json
{
  "tenant_id": "uuid",
  "fornecedor_id": "uuid",
  "produto_id": "uuid",
  "preco": "30.00",
  "condicoes": {
    "quantidade_minima": "100.000",
    "prazo_pagamento": 30
  }
}
```

**Response**:
```json
{
  "success": true
}
```

#### `GET /compare/{produto_id}`

**Descrição**: Compara fornecedores para um produto

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "produto_id": "uuid",
  "fornecedores": [
    {
      "fornecedor_id": "uuid",
      "nome": "Fornecedor A",
      "preco": "30.00",
      "quantidade_minima": "100.000",
      "prazo_pagamento": 30
    }
  ]
}
```

#### `GET /suggest/{produto_id}`

**Descrição**: Sugere fornecedor mais vantajoso

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "produto_id": "uuid",
  "fornecedor_sugerido_id": "uuid",
  "motivo": "Menor preço para quantidade desejada",
  "preco": "30.00"
}
```

#### `GET /base-cost/{produto_id}`

**Descrição**: Retorna custo base de um produto

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "produto_id": "uuid",
  "custo_base": "28.50",
  "calculado_em": "2026-01-15T10:00:00Z"
}
```

#### `GET /price-alerts`

**Descrição**: Retorna alertas de variação de preço

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "alerts": [
    {
      "produto_id": "uuid",
      "fornecedor_id": "uuid",
      "variacao_percentual": "10.00",
      "preco_anterior": "30.00",
      "preco_atual": "33.00",
      "data_variacao": "2026-01-15T09:00:00Z"
    }
  ]
}
```

#### `GET /price-trend/{produto_id}/{fornecedor_id}`

**Descrição**: Retorna tendência de preço

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "produto_id": "uuid",
  "fornecedor_id": "uuid",
  "tendencia": "ascendente",
  "precos": [
    {
      "preco": "30.00",
      "data": "2026-01-01T00:00:00Z"
    }
  ]
}
```

---

## 🚚 Delivery & Fulfillment Engine

### Base Path
`/api/v1/engines/delivery`

### Port (Interface)
`app.core_engines.delivery_fulfillment.ports.DeliveryFulfillmentPort`

### Event Handlers

#### `handle_quote_converted`

**Evento Consumido**: `quote_converted`

**Handler**: `app.platform.engines.delivery_fulfillment.handlers.handle_quote_converted`

**Lógica**:
- Prepara dados para planejamento futuro de entrega
- Não executa planejamento imediato (aguarda status "saiu_entrega")

**Payload Esperado**: Mesmo de Sales Intelligence

#### `handle_order_status_changed`

**Evento Consumido**: `order_status_changed`

**Handler**: `app.platform.engines.delivery_fulfillment.handlers.handle_order_status_changed`

**Lógica**:
- Se `new_status = "saiu_entrega"`, planeja rotas
- Agrupa pedidos por rota
- Atualiza status de entrega

**Payload Esperado**:
```json
{
  "order_id": "uuid",
  "old_status": "em_preparacao",
  "new_status": "saiu_entrega"
}
```

### API Endpoints

#### `POST /plan-routes`

**Descrição**: Planeja rotas de entrega

**Autenticação**: Admin-only

**Request Body**:
```json
{
  "pedidos": [
    {
      "tenant_id": "uuid",
      "pedido_id": "uuid",
      "cliente_id": "uuid",
      "endereco_entrega": {
        "logradouro": "Rua Teste",
        "numero": "123",
        "cidade": "Barra Mansa",
        "estado": "RJ",
        "cep": "27300000"
      },
      "produtos": [
        {
          "produto_id": "uuid",
          "quantidade": "10.000",
          "peso": "0.000"
        }
      ]
    }
  ]
}
```

**Response**:
```json
{
  "routes": [
    {
      "route_id": "uuid",
      "pedidos": ["uuid"],
      "estimated_distance": "50.5",
      "estimated_time": "60"
    }
  ]
}
```

#### `POST /update-status`

**Descrição**: Atualiza status de entrega

**Autenticação**: Admin-only

**Request Body**:
```json
{
  "tenant_id": "uuid",
  "pedido_id": "uuid",
  "status": "entregue",
  "observacoes": "Entrega realizada com sucesso"
}
```

**Response**:
```json
{
  "success": true
}
```

#### `GET /status/{pedido_id}`

**Descrição**: Retorna status de entrega

**Autenticação**: Admin-only

**Query Parameters**:
- `tenant_id` (required): UUID do tenant

**Response**:
```json
{
  "pedido_id": "uuid",
  "status": "entregue",
  "updated_at": "2026-01-15T14:00:00Z"
}
```

---

## 🔐 Segurança e Acesso

### Autenticação

- Todos os endpoints requerem autenticação JWT
- Apenas usuários com role `admin` podem acessar

### Rate Limiting (Futuro)

- Limite por tenant: 100 requests/minuto
- Limite global: 1000 requests/minuto
- Headers de rate limit serão incluídos na resposta

### Versionamento

- Versão atual: `v1`
- Versões futuras: `/api/v2/engines/*`
- Versões antigas mantidas por 6 meses após deprecation

---

## 📊 Versionamento de Contratos

### Regras

1. **Breaking Changes**: Incrementa versão major (`v1` → `v2`)
   - Mudança de estrutura de request/response
   - Remoção de endpoint
   - Mudança de comportamento esperado

2. **Non-Breaking Changes**: Mantém versão atual
   - Adição de campo opcional
   - Novos endpoints
   - Melhorias de performance

### Compatibilidade

- **Verticals devem especificar versão** ao chamar API
- **Engines mantêm suporte** para versões anteriores (6 meses)
- **Deprecation warnings** enviados via headers

---

**Versão**: 1.0  
**Data**: Janeiro 2026  
**Status**: 📋 Contratos Iniciais - Implementação em Progresso

