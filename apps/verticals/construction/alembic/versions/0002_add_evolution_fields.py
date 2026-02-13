"""Add Evolution API fields to WhatsApp bindings

Revision ID: 0002_evolution_fields
Revises: 0001_whatsapp_engine
Create Date: 2026-01-11

Adds fields to support Evolution API provider:
- instance_name: Evolution instance identifier
- api_key: Evolution API key (encrypted)
- api_url: Evolution API base URL

Also makes phone_number_id and waba_id nullable (not required for Evolution).
"""

from alembic import op
import sqlalchemy as sa

revision = '0002_evolution_fields'
down_revision = '0001_whatsapp_engine'
branch_labels = None
depends_on = None


def upgrade():
    # Make Meta fields nullable (Evolution doesn't need them)
    op.alter_column('whatsapp_tenant_bindings', 'phone_number_id',
                    existing_type=sa.String(100),
                    nullable=True)
    op.alter_column('whatsapp_tenant_bindings', 'waba_id',
                    existing_type=sa.String(100),
                    nullable=True)

    # Add Evolution API fields
    op.add_column('whatsapp_tenant_bindings',
        sa.Column('instance_name', sa.String(100), nullable=True))
    op.add_column('whatsapp_tenant_bindings',
        sa.Column('api_key', sa.Text(), nullable=True))
    op.add_column('whatsapp_tenant_bindings',
        sa.Column('api_url', sa.String(255), nullable=True))

    # Add unique constraint for instance_name
    op.create_unique_constraint(
        'uq_whatsapp_bindings_instance_name',
        'whatsapp_tenant_bindings',
        ['instance_name']
    )

    # Add index for provider type
    op.create_index(
        'idx_whatsapp_bindings_provider',
        'whatsapp_tenant_bindings',
        ['provider']
    )

    # Add index for instance_name lookup
    op.create_index(
        'idx_whatsapp_bindings_instance_name',
        'whatsapp_tenant_bindings',
        ['instance_name']
    )


def downgrade():
    op.drop_index('idx_whatsapp_bindings_instance_name', table_name='whatsapp_tenant_bindings')
    op.drop_index('idx_whatsapp_bindings_provider', table_name='whatsapp_tenant_bindings')
    op.drop_constraint('uq_whatsapp_bindings_instance_name', 'whatsapp_tenant_bindings', type_='unique')
    
    op.drop_column('whatsapp_tenant_bindings', 'api_url')
    op.drop_column('whatsapp_tenant_bindings', 'api_key')
    op.drop_column('whatsapp_tenant_bindings', 'instance_name')

    # Restore NOT NULL constraints (if needed)
    # Note: This might fail if there are NULL values
    op.alter_column('whatsapp_tenant_bindings', 'waba_id',
                    existing_type=sa.String(100),
                    nullable=False)
    op.alter_column('whatsapp_tenant_bindings', 'phone_number_id',
                    existing_type=sa.String(100),
                    nullable=False)




