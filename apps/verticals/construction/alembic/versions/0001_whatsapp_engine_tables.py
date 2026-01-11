"""WhatsApp Engine Tables

Revision ID: 0001_whatsapp_engine
Revises: 0000_initial
Create Date: 2026-01-11

Creates tables owned by the WhatsApp Messaging Engine:
- whatsapp_tenant_bindings: Maps tenants to WhatsApp Business accounts
- whatsapp_conversations: Tracks conversation state with customers  
- whatsapp_messages: Stores all inbound/outbound messages
- whatsapp_optouts: Tracks customers who opted out
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '0001_whatsapp_engine'
down_revision = '0000_initial'
branch_labels = None
depends_on = None


def upgrade():
    # =========================================================================
    # WHATSAPP TENANT BINDINGS
    # =========================================================================
    
    op.create_table(
        'whatsapp_tenant_bindings',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(50), server_default='meta', nullable=False),
        sa.Column('phone_number_id', sa.String(100), nullable=False),
        sa.Column('waba_id', sa.String(100), nullable=False),
        sa.Column('display_number', sa.String(20), nullable=False),
        sa.Column('access_token_encrypted', sa.Text(), nullable=True),
        sa.Column('webhook_verify_token', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('config', JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('phone_number_id', name='uq_whatsapp_bindings_phone_number_id')
    )
    op.create_index('idx_whatsapp_bindings_tenant_id', 'whatsapp_tenant_bindings', ['tenant_id'])
    op.create_index('idx_whatsapp_bindings_tenant_active', 'whatsapp_tenant_bindings', ['tenant_id', 'is_active'])
    op.create_index('idx_whatsapp_bindings_phone_number_id', 'whatsapp_tenant_bindings', ['phone_number_id'])

    # =========================================================================
    # WHATSAPP CONVERSATIONS
    # =========================================================================
    
    op.create_table(
        'whatsapp_conversations',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('status', sa.String(20), server_default='active', nullable=False),
        sa.Column('current_state', sa.String(50), nullable=True),
        sa.Column('assigned_user_id', UUID(as_uuid=True), nullable=True),
        sa.Column('last_message_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_inbound_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_outbound_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('message_count', sa.String(10), server_default='0', nullable=False),
        sa.Column('context', JSONB(), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'customer_phone', name='uq_whatsapp_conversations_tenant_phone')
    )
    op.create_index('idx_whatsapp_conversations_tenant_id', 'whatsapp_conversations', ['tenant_id'])
    op.create_index('idx_whatsapp_conversations_tenant_status', 'whatsapp_conversations', ['tenant_id', 'status'])
    op.create_index('idx_whatsapp_conversations_tenant_last_message', 'whatsapp_conversations', ['tenant_id', 'last_message_at'])
    op.create_index('idx_whatsapp_conversations_customer_phone', 'whatsapp_conversations', ['customer_phone'])

    # =========================================================================
    # WHATSAPP MESSAGES
    # =========================================================================
    
    op.create_table(
        'whatsapp_messages',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', UUID(as_uuid=True), nullable=False),
        sa.Column('direction', sa.String(3), nullable=False),
        sa.Column('provider_message_id', sa.String(100), nullable=True),
        sa.Column('message_type', sa.String(20), server_default='text', nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('content_json', JSONB(), server_default='{}', nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False),
        sa.Column('status_updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_code', sa.String(50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('template_name', sa.String(100), nullable=True),
        sa.Column('reply_to_message_id', sa.String(100), nullable=True),
        sa.Column('triggered_by_event_id', UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['whatsapp_conversations.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('provider_message_id', name='uq_whatsapp_messages_provider_id')
    )
    op.create_index('idx_whatsapp_messages_tenant_id', 'whatsapp_messages', ['tenant_id'])
    op.create_index('idx_whatsapp_messages_conversation_id', 'whatsapp_messages', ['conversation_id'])
    op.create_index('idx_whatsapp_messages_tenant_conversation', 'whatsapp_messages', ['tenant_id', 'conversation_id'])
    op.create_index('idx_whatsapp_messages_tenant_direction', 'whatsapp_messages', ['tenant_id', 'direction'])
    op.create_index('idx_whatsapp_messages_tenant_status', 'whatsapp_messages', ['tenant_id', 'status'])
    op.create_index('idx_whatsapp_messages_tenant_created', 'whatsapp_messages', ['tenant_id', 'created_at'])
    op.create_index('idx_whatsapp_messages_provider_message_id', 'whatsapp_messages', ['provider_message_id'])

    # =========================================================================
    # WHATSAPP OPT-OUTS
    # =========================================================================
    
    op.create_table(
        'whatsapp_optouts',
        sa.Column('id', UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('customer_phone', sa.String(20), nullable=False),
        sa.Column('reason', sa.String(50), nullable=False),
        sa.Column('original_message_id', sa.String(100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('reactivated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('tenant_id', 'customer_phone', name='uq_whatsapp_optouts_tenant_phone')
    )
    op.create_index('idx_whatsapp_optouts_tenant_id', 'whatsapp_optouts', ['tenant_id'])
    op.create_index('idx_whatsapp_optouts_tenant_active', 'whatsapp_optouts', ['tenant_id', 'is_active'])
    op.create_index('idx_whatsapp_optouts_customer_phone', 'whatsapp_optouts', ['customer_phone'])

    # =========================================================================
    # WHATSAPP PROCESSED EVENTS (for idempotency)
    # =========================================================================
    
    op.create_table(
        'whatsapp_processed_events',
        sa.Column('event_id', UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('result', JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('event_id')
    )
    op.create_index('idx_whatsapp_processed_events_tenant', 'whatsapp_processed_events', ['tenant_id'])
    op.create_index('idx_whatsapp_processed_events_tenant_date', 'whatsapp_processed_events', ['tenant_id', 'processed_at'])


def downgrade():
    op.drop_table('whatsapp_processed_events')
    op.drop_table('whatsapp_optouts')
    op.drop_table('whatsapp_messages')
    op.drop_table('whatsapp_conversations')
    op.drop_table('whatsapp_tenant_bindings')

