"""Initial schema - Construction Vertical

Revision ID: 0001_initial
Revises: 
Create Date: 2026-01-09

Complete database schema including:
- Auth tables (tenants, users, tenant_branding)
- Core tables (clientes, obras, produtos, historico_precos)
- Transaction tables (cotacoes, cotacao_itens, pedidos, pedido_itens)
- Inventory tables (estoque, fornecedores, fornecedor_precos)
- Event sourcing (event_outbox)
- Engine tables (alerts, suggestions, facts, routes)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON, JSONB

revision = '0000_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # AUTH TABLES
    # =========================================================================
    
    op.create_table(
        'tenants',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('slug', sa.String(63), nullable=False),
        sa.Column('cnpj', sa.String(18), nullable=True),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('telefone', sa.String(20), nullable=True),
        sa.Column('endereco', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('cnpj')
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'])

    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('role', sa.String(50), server_default='vendedor', nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_users_email', 'users', ['email'])

    op.create_table(
        'tenant_branding',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('primary_color', sa.String(7), server_default='#1a73e8', nullable=True),
        sa.Column('secondary_color', sa.String(7), server_default='#ea4335', nullable=True),
        sa.Column('feature_flags', JSON(), server_default='{}', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id')
    )
    op.create_index('ix_tenant_branding_tenant_id', 'tenant_branding', ['tenant_id'])

    # =========================================================================
    # CORE TABLES
    # =========================================================================
    
    op.create_table(
        'clientes',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tipo', sa.String(2), nullable=False),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('documento', sa.String(20), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('telefone', sa.String(20), nullable=True),
        sa.Column('endereco', sa.Text(), nullable=True),
        sa.Column('cidade', sa.String(100), nullable=True),
        sa.Column('estado', sa.String(2), nullable=True),
        sa.Column('cep', sa.String(10), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    op.create_index('ix_clientes_tenant_id', 'clientes', ['tenant_id'])
    op.create_index('idx_clientes_tenant_documento', 'clientes', ['tenant_id', 'documento'], unique=True)

    op.create_table(
        'obras',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('cliente_id', UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('endereco', sa.Text(), nullable=True),
        sa.Column('cidade', sa.String(100), nullable=True),
        sa.Column('estado', sa.String(2), nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('ativa', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id'], ondelete='CASCADE')
    )
    op.create_index('ix_obras_tenant_id', 'obras', ['tenant_id'])
    op.create_index('ix_obras_cliente_id', 'obras', ['cliente_id'])

    op.create_table(
        'produtos',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('codigo', sa.String(50), nullable=True),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('unidade', sa.String(20), nullable=False),
        sa.Column('preco_base', sa.Numeric(10, 2), nullable=False),
        sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    op.create_index('ix_produtos_tenant_id', 'produtos', ['tenant_id'])
    op.create_index('idx_produtos_tenant_ativo', 'produtos', ['tenant_id', 'ativo'])
    op.create_index('idx_produtos_tenant_codigo', 'produtos', ['tenant_id', 'codigo'], unique=True)

    op.create_table(
        'historico_precos',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('produto_id', UUID(as_uuid=True), nullable=False),
        sa.Column('preco', sa.Numeric(10, 2), nullable=False),
        sa.Column('usuario_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='CASCADE')
    )
    op.create_index('ix_historico_precos_tenant_id', 'historico_precos', ['tenant_id'])
    op.create_index('ix_historico_precos_produto_id', 'historico_precos', ['produto_id'])
    op.create_index('ix_historico_precos_usuario_id', 'historico_precos', ['usuario_id'])

    # =========================================================================
    # TRANSACTION TABLES
    # =========================================================================
    
    op.create_table(
        'cotacoes',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('cliente_id', UUID(as_uuid=True), nullable=False),
        sa.Column('obra_id', UUID(as_uuid=True), nullable=True),
        sa.Column('numero', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), server_default='rascunho', nullable=False),
        sa.Column('desconto_percentual', sa.Numeric(5, 2), server_default='0', nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('validade_dias', sa.Integer(), server_default='7', nullable=True),
        sa.Column('usuario_id', UUID(as_uuid=True), nullable=True),
        sa.Column('enviada_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('aprovada_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('convertida_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.ForeignKeyConstraint(['obra_id'], ['obras.id'])
    )
    op.create_index('ix_cotacoes_tenant_id', 'cotacoes', ['tenant_id'])
    op.create_index('ix_cotacoes_usuario_id', 'cotacoes', ['usuario_id'])
    op.create_index('idx_cotacoes_tenant_status', 'cotacoes', ['tenant_id', 'status'])
    op.create_index('idx_cotacoes_cliente', 'cotacoes', ['tenant_id', 'cliente_id'])
    op.create_index('idx_cotacoes_created', 'cotacoes', ['tenant_id', 'created_at'])
    op.create_index('idx_cotacoes_tenant_numero', 'cotacoes', ['tenant_id', 'numero'], unique=True)

    op.create_table(
        'cotacao_itens',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('cotacao_id', UUID(as_uuid=True), nullable=False),
        sa.Column('produto_id', UUID(as_uuid=True), nullable=False),
        sa.Column('quantidade', sa.Numeric(10, 3), nullable=False),
        sa.Column('preco_unitario', sa.Numeric(10, 2), nullable=False),
        sa.Column('desconto_percentual', sa.Numeric(5, 2), server_default='0', nullable=True),
        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('ordem', sa.Integer(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cotacao_id'], ['cotacoes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'])
    )
    op.create_index('ix_cotacao_itens_tenant_id', 'cotacao_itens', ['tenant_id'])
    op.create_index('idx_cotacao_itens_cotacao', 'cotacao_itens', ['tenant_id', 'cotacao_id'])

    op.create_table(
        'pedidos',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('cotacao_id', UUID(as_uuid=True), nullable=True),
        sa.Column('cliente_id', UUID(as_uuid=True), nullable=False),
        sa.Column('obra_id', UUID(as_uuid=True), nullable=True),
        sa.Column('numero', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), server_default='pendente', nullable=False),
        sa.Column('desconto_percentual', sa.Numeric(5, 2), server_default='0', nullable=True),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('usuario_id', UUID(as_uuid=True), nullable=True),
        sa.Column('entregue_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['cotacao_id'], ['cotacoes.id']),
        sa.ForeignKeyConstraint(['cliente_id'], ['clientes.id']),
        sa.ForeignKeyConstraint(['obra_id'], ['obras.id'])
    )
    op.create_index('ix_pedidos_tenant_id', 'pedidos', ['tenant_id'])
    op.create_index('ix_pedidos_usuario_id', 'pedidos', ['usuario_id'])
    op.create_index('idx_pedidos_tenant_status', 'pedidos', ['tenant_id', 'status'])
    op.create_index('idx_pedidos_cliente', 'pedidos', ['tenant_id', 'cliente_id'])
    op.create_index('idx_pedidos_created', 'pedidos', ['tenant_id', 'created_at'])
    op.create_index('idx_pedidos_tenant_numero', 'pedidos', ['tenant_id', 'numero'], unique=True)

    op.create_table(
        'pedido_itens',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('pedido_id', UUID(as_uuid=True), nullable=False),
        sa.Column('produto_id', UUID(as_uuid=True), nullable=False),
        sa.Column('quantidade', sa.Numeric(10, 3), nullable=False),
        sa.Column('preco_unitario', sa.Numeric(10, 2), nullable=False),
        sa.Column('desconto_percentual', sa.Numeric(5, 2), server_default='0', nullable=True),
        sa.Column('valor_total', sa.Numeric(10, 2), nullable=False),
        sa.Column('observacoes', sa.Text(), nullable=True),
        sa.Column('ordem', sa.Integer(), server_default='0', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['pedido_id'], ['pedidos.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'])
    )
    op.create_index('ix_pedido_itens_tenant_id', 'pedido_itens', ['tenant_id'])
    op.create_index('idx_pedido_itens_pedido', 'pedido_itens', ['tenant_id', 'pedido_id'])

    # =========================================================================
    # INVENTORY TABLES
    # =========================================================================
    
    op.create_table(
        'estoque',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('produto_id', UUID(as_uuid=True), nullable=False),
        sa.Column('quantidade_atual', sa.Numeric(10, 3), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='CASCADE'),
        sa.CheckConstraint('quantidade_atual >= 0', name='ck_estoque_quantidade_nao_negativa')
    )
    op.create_index('idx_estoque_tenant_produto', 'estoque', ['tenant_id', 'produto_id'], unique=True)
    op.create_index('idx_estoque_tenant', 'estoque', ['tenant_id'])
    op.create_index('idx_estoque_produto', 'estoque', ['produto_id'])
    op.create_index('idx_estoque_tenant_quantidade', 'estoque', ['tenant_id', 'quantidade_atual'])

    op.create_table(
        'fornecedores',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('nome', sa.String(255), nullable=False),
        sa.Column('documento', sa.String(20), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('telefone', sa.String(20), nullable=True),
        sa.Column('endereco', sa.Text(), nullable=True),
        sa.Column('ativo', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE')
    )
    op.create_index('idx_fornecedores_tenant_ativo', 'fornecedores', ['tenant_id', 'ativo'])
    op.create_index('idx_fornecedores_tenant_documento', 'fornecedores', ['tenant_id', 'documento'], unique=True)

    op.create_table(
        'fornecedor_precos',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('fornecedor_id', UUID(as_uuid=True), nullable=False),
        sa.Column('produto_id', UUID(as_uuid=True), nullable=False),
        sa.Column('preco', sa.Numeric(10, 2), nullable=False),
        sa.Column('quantidade_minima', sa.Numeric(10, 3), nullable=True),
        sa.Column('prazo_pagamento', sa.Numeric(5, 0), nullable=True),
        sa.Column('valido', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['fornecedor_id'], ['fornecedores.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['produto_id'], ['produtos.id'], ondelete='CASCADE'),
        sa.CheckConstraint('preco > 0', name='ck_fornecedor_precos_preco_positivo')
    )
    op.create_index('idx_fornecedor_precos_tenant_fornecedor_produto', 'fornecedor_precos', ['tenant_id', 'fornecedor_id', 'produto_id'])
    op.create_index('idx_fornecedor_precos_tenant_produto', 'fornecedor_precos', ['tenant_id', 'produto_id'])
    op.create_index('idx_fornecedor_precos_valido', 'fornecedor_precos', ['tenant_id', 'valido'])
    op.create_index('idx_fornecedor_precos_created_at', 'fornecedor_precos', ['created_at'])
    op.create_index('idx_fornecedor_precos_tenant_produto_valido_created', 'fornecedor_precos', ['tenant_id', 'produto_id', 'valido', 'created_at'])

    # =========================================================================
    # EVENT SOURCING
    # =========================================================================
    
    op.create_table(
        'event_outbox',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('event_id', UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('payload', JSONB(), nullable=False),
        sa.Column('version', sa.String(20), server_default='1.0', nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('idx_event_outbox_event_type', 'event_outbox', ['event_type'])
    op.create_index('idx_event_outbox_status', 'event_outbox', ['status'])
    op.create_index('idx_event_outbox_tenant_status', 'event_outbox', ['tenant_id', 'status'])
    op.create_index('idx_event_outbox_status_created', 'event_outbox', ['status', 'created_at'])
    op.create_index('idx_event_outbox_published', 'event_outbox', ['published_at'], postgresql_where=sa.text('published_at IS NULL'))

    # =========================================================================
    # ENGINE TABLES
    # =========================================================================
    
    op.create_table(
        'engine_processed_events',
        sa.Column('event_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('result', JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('idx_processed_events_tenant_date', 'engine_processed_events', ['tenant_id', 'processed_at'])

    op.create_table(
        'engine_stock_alerts',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('risk_level', sa.String(20), nullable=False),
        sa.Column('current_stock', sa.String(50), nullable=False),
        sa.Column('minimum_stock', sa.String(50), nullable=False),
        sa.Column('days_until_rupture', sa.String(20), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('payload', JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_stock_alerts_tenant_product', 'engine_stock_alerts', ['tenant_id', 'product_id'])
    op.create_index('idx_stock_alerts_tenant_status', 'engine_stock_alerts', ['tenant_id', 'status'])
    op.create_index('idx_stock_alerts_tenant_created', 'engine_stock_alerts', ['tenant_id', 'created_at'])

    op.create_table(
        'engine_replenishment_suggestions',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('suggested_quantity', sa.String(50), nullable=False),
        sa.Column('current_stock', sa.String(50), nullable=False),
        sa.Column('minimum_stock', sa.String(50), nullable=False),
        sa.Column('maximum_stock', sa.String(50), nullable=False),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('payload', JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_replenishment_tenant_product', 'engine_replenishment_suggestions', ['tenant_id', 'product_id'])
    op.create_index('idx_replenishment_tenant_status', 'engine_replenishment_suggestions', ['tenant_id', 'status'])
    op.create_index('idx_replenishment_tenant_created', 'engine_replenishment_suggestions', ['tenant_id', 'created_at'])

    op.create_table(
        'engine_sales_suggestions',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('suggestion_type', sa.String(50), nullable=False),
        sa.Column('source_product_id', UUID(as_uuid=True), nullable=True),
        sa.Column('suggested_product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('frequency', sa.String(20), nullable=True),
        sa.Column('priority', sa.String(20), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('payload', JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sales_suggestions_tenant_source', 'engine_sales_suggestions', ['tenant_id', 'source_product_id'])
    op.create_index('idx_sales_suggestions_tenant_type', 'engine_sales_suggestions', ['tenant_id', 'suggestion_type'])
    op.create_index('idx_sales_suggestions_tenant_created', 'engine_sales_suggestions', ['tenant_id', 'created_at'])

    op.create_table(
        'engine_supplier_price_alerts',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', UUID(as_uuid=True), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('current_price', sa.String(50), nullable=False),
        sa.Column('reference_price', sa.String(50), nullable=True),
        sa.Column('price_change_percent', sa.String(20), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('payload', JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_supplier_alerts_tenant_product', 'engine_supplier_price_alerts', ['tenant_id', 'product_id'])
    op.create_index('idx_supplier_alerts_tenant_supplier', 'engine_supplier_price_alerts', ['tenant_id', 'supplier_id'])
    op.create_index('idx_supplier_alerts_tenant_created', 'engine_supplier_price_alerts', ['tenant_id', 'created_at'])

    op.create_table(
        'engine_delivery_routes',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('route_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('route_name', sa.String(200), nullable=True),
        sa.Column('total_orders', sa.String(10), nullable=False),
        sa.Column('total_distance_km', sa.String(20), nullable=True),
        sa.Column('estimated_duration_minutes', sa.String(20), nullable=True),
        sa.Column('order_ids', JSONB(), nullable=False),
        sa.Column('route_sequence', JSONB(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('payload', JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.String(20), server_default='planned', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_delivery_routes_tenant_date', 'engine_delivery_routes', ['tenant_id', 'route_date'])
    op.create_index('idx_delivery_routes_tenant_status', 'engine_delivery_routes', ['tenant_id', 'status'])
    op.create_index('idx_delivery_routes_tenant_created', 'engine_delivery_routes', ['tenant_id', 'created_at'])

    op.create_table(
        'engine_sales_facts',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('order_id', UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', UUID(as_uuid=True), nullable=True),
        sa.Column('quantity', sa.Numeric(15, 4), nullable=False),
        sa.Column('unit_price', sa.Numeric(15, 4), nullable=False),
        sa.Column('total_value', sa.Numeric(15, 4), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_id', UUID(as_uuid=True), nullable=False),
        sa.Column('payload', JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('idx_sales_facts_tenant_product_date', 'engine_sales_facts', ['tenant_id', 'product_id', 'occurred_at'])
    op.create_index('idx_sales_facts_tenant_client', 'engine_sales_facts', ['tenant_id', 'client_id'])
    op.create_index('idx_sales_facts_tenant_order', 'engine_sales_facts', ['tenant_id', 'order_id'])
    op.create_index('idx_sales_facts_tenant_created', 'engine_sales_facts', ['tenant_id', 'created_at'])

    op.create_table(
        'engine_stock_facts',
        sa.Column('id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('vertical', sa.String(50), server_default='materials', nullable=False),
        sa.Column('product_id', UUID(as_uuid=True), nullable=False),
        sa.Column('movement_type', sa.String(20), nullable=False),
        sa.Column('quantity_delta', sa.Numeric(15, 4), nullable=False),
        sa.Column('quantity_after', sa.Numeric(15, 4), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_id', UUID(as_uuid=True), nullable=False),
        sa.Column('reference_id', UUID(as_uuid=True), nullable=True),
        sa.Column('payload', JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('idx_stock_facts_tenant_product_date', 'engine_stock_facts', ['tenant_id', 'product_id', 'occurred_at'])
    op.create_index('idx_stock_facts_tenant_type', 'engine_stock_facts', ['tenant_id', 'movement_type'])
    op.create_index('idx_stock_facts_tenant_created', 'engine_stock_facts', ['tenant_id', 'created_at'])


def downgrade():
    # Engine tables
    op.drop_table('engine_stock_facts')
    op.drop_table('engine_sales_facts')
    op.drop_table('engine_delivery_routes')
    op.drop_table('engine_supplier_price_alerts')
    op.drop_table('engine_sales_suggestions')
    op.drop_table('engine_replenishment_suggestions')
    op.drop_table('engine_stock_alerts')
    op.drop_table('engine_processed_events')
    
    # Event sourcing
    op.drop_table('event_outbox')
    
    # Inventory tables
    op.drop_table('fornecedor_precos')
    op.drop_table('fornecedores')
    op.drop_table('estoque')
    
    # Transaction tables
    op.drop_table('pedido_itens')
    op.drop_table('pedidos')
    op.drop_table('cotacao_itens')
    op.drop_table('cotacoes')
    
    # Core tables
    op.drop_table('historico_precos')
    op.drop_table('produtos')
    op.drop_table('obras')
    op.drop_table('clientes')
    
    # Auth tables
    op.drop_table('tenant_branding')
    op.drop_table('users')
    op.drop_table('tenants')

