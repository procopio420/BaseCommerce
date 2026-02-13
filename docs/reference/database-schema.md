# Schema do Banco de Dados

## Estrutura Multi-tenant

Todas as tabelas possuem `tenant_id` para isolamento.

## Tabelas

### 1. tenants

```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    nome VARCHAR(255) NOT NULL,
    cnpj VARCHAR(18) UNIQUE,
    email VARCHAR(255) NOT NULL,
    telefone VARCHAR(20),
    endereco TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ativo BOOLEAN DEFAULT TRUE
);
```

### 2. users (Usuários da loja)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'vendedor', -- admin, vendedor
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, email)
);
```

### 3. clientes

```sql
CREATE TABLE clientes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    tipo VARCHAR(2) NOT NULL, -- 'PF' ou 'PJ'
    nome VARCHAR(255) NOT NULL,
    documento VARCHAR(20) NOT NULL, -- CPF ou CNPJ
    email VARCHAR(255),
    telefone VARCHAR(20),
    endereco TEXT,
    cidade VARCHAR(100),
    estado VARCHAR(2),
    cep VARCHAR(10),
    observacoes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, documento)
);
```

### 4. obras

```sql
CREATE TABLE obras (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nome VARCHAR(255) NOT NULL,
    endereco TEXT,
    cidade VARCHAR(100),
    estado VARCHAR(2),
    observacoes TEXT,
    ativa BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 5. produtos

```sql
CREATE TABLE produtos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    codigo VARCHAR(50),
    nome VARCHAR(255) NOT NULL,
    descricao TEXT,
    unidade VARCHAR(20) NOT NULL, -- 'UN', 'KG', 'M', 'M2', 'M3'
    preco_base DECIMAL(10, 2) NOT NULL,
    ativo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tenant_id, codigo)
);

CREATE INDEX idx_produtos_tenant_ativo ON produtos(tenant_id, ativo);
```

### 6. historico_precos

```sql
CREATE TABLE historico_precos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    produto_id UUID NOT NULL REFERENCES produtos(id) ON DELETE CASCADE,
    preco DECIMAL(10, 2) NOT NULL,
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usuario_id UUID REFERENCES users(id)
);
```

### 7. cotacoes

```sql
CREATE TABLE cotacoes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cliente_id UUID NOT NULL REFERENCES clientes(id),
    obra_id UUID REFERENCES obras(id),
    numero VARCHAR(50) NOT NULL, -- Gerado automaticamente
    status VARCHAR(20) NOT NULL DEFAULT 'rascunho', -- rascunho, enviada, aprovada, convertida, cancelada
    desconto_percentual DECIMAL(5, 2) DEFAULT 0,
    observacoes TEXT,
    validade_dias INTEGER DEFAULT 7,
    usuario_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enviada_em TIMESTAMP,
    aprovada_em TIMESTAMP,
    convertida_em TIMESTAMP,
    UNIQUE(tenant_id, numero)
);

CREATE INDEX idx_cotacoes_tenant_status ON cotacoes(tenant_id, status);
CREATE INDEX idx_cotacoes_cliente ON cotacoes(tenant_id, cliente_id);
CREATE INDEX idx_cotacoes_created ON cotacoes(tenant_id, created_at);
```

### 8. cotacao_itens

```sql
CREATE TABLE cotacao_itens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cotacao_id UUID NOT NULL REFERENCES cotacoes(id) ON DELETE CASCADE,
    produto_id UUID NOT NULL REFERENCES produtos(id),
    quantidade DECIMAL(10, 3) NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL, -- Preço na hora da cotação
    desconto_percentual DECIMAL(5, 2) DEFAULT 0,
    valor_total DECIMAL(10, 2) NOT NULL, -- quantidade * preco_unitario * (1 - desconto/100)
    observacoes TEXT,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cotacao_itens_cotacao ON cotacao_itens(tenant_id, cotacao_id);
```

### 9. pedidos

```sql
CREATE TABLE pedidos (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    cotacao_id UUID REFERENCES cotacoes(id), -- NULL se criado direto
    cliente_id UUID NOT NULL REFERENCES clientes(id),
    obra_id UUID REFERENCES obras(id),
    numero VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pendente', -- pendente, em_preparacao, saiu_entrega, entregue, cancelado
    desconto_percentual DECIMAL(5, 2) DEFAULT 0,
    observacoes TEXT,
    usuario_id UUID REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    entregue_em TIMESTAMP,
    UNIQUE(tenant_id, numero)
);

CREATE INDEX idx_pedidos_tenant_status ON pedidos(tenant_id, status);
CREATE INDEX idx_pedidos_cliente ON pedidos(tenant_id, cliente_id);
CREATE INDEX idx_pedidos_created ON pedidos(tenant_id, created_at);
```

### 10. pedido_itens

```sql
CREATE TABLE pedido_itens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    pedido_id UUID NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
    produto_id UUID NOT NULL REFERENCES produtos(id),
    quantidade DECIMAL(10, 3) NOT NULL,
    preco_unitario DECIMAL(10, 2) NOT NULL,
    desconto_percentual DECIMAL(5, 2) DEFAULT 0,
    valor_total DECIMAL(10, 2) NOT NULL,
    observacoes TEXT,
    ordem INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_pedido_itens_pedido ON pedido_itens(tenant_id, pedido_id);
```

## Relacionamentos

```
tenant (1) ── (N) users
tenant (1) ── (N) clientes
tenant (1) ── (N) produtos
tenant (1) ── (N) cotacoes
tenant (1) ── (N) pedidos

cliente (1) ── (N) obras
cliente (1) ── (N) cotacoes
cliente (1) ── (N) pedidos

cotacao (1) ── (N) cotacao_itens
cotacao (1) ── (1) pedido (quando convertida)

pedido (1) ── (N) pedido_itens

produto (1) ── (N) cotacao_itens
produto (1) ── (N) pedido_itens
produto (1) ── (N) historico_precos
```

## Versionamento de Cotações

Para histórico, cada modificação da cotação gera um novo registro com timestamp em `updated_at`.
O campo `numero` permanece o mesmo para permitir rastreabilidade.

## Conversão Cotação → Pedido

1. Cotação deve estar com status 'aprovada'
2. Copia todos os itens da cotação para o pedido
3. Marca cotação como 'convertida'
4. Gera número único de pedido

