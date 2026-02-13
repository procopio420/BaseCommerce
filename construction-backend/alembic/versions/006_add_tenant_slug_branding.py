"""Add tenant slug and branding table

Revision ID: 006
Revises: 005
Create Date: 2026-01-08

Adds:
- slug column to tenants table for subdomain-based resolution
- tenant_branding table for white-label customization
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add slug column to tenants table
    # First add as nullable, then backfill, then make non-nullable
    op.add_column(
        "tenants",
        sa.Column("slug", sa.String(63), nullable=True),
    )

    # Backfill slug from nome (lowercase, replace spaces with hyphens)
    op.execute(
        """
        UPDATE tenants
        SET slug = LOWER(REGEXP_REPLACE(TRIM(nome), '[^a-zA-Z0-9]+', '-', 'g'))
        WHERE slug IS NULL
        """
    )

    # Make slug non-nullable and add unique constraint and index
    op.alter_column("tenants", "slug", nullable=False)
    op.create_unique_constraint("uq_tenants_slug", "tenants", ["slug"])
    op.create_index("idx_tenants_slug", "tenants", ["slug"])

    # Create tenant_branding table
    op.create_table(
        "tenant_branding",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=False, server_default="#1a73e8"),
        sa.Column("secondary_color", sa.String(7), nullable=False, server_default="#ea4335"),
        sa.Column("feature_flags", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("idx_tenant_branding_tenant_id", "tenant_branding", ["tenant_id"])

    # Create default branding for existing tenants
    op.execute(
        """
        INSERT INTO tenant_branding (id, tenant_id, logo_url, primary_color, secondary_color, feature_flags)
        SELECT gen_random_uuid(), id, NULL, '#1a73e8', '#ea4335', '{}'::jsonb
        FROM tenants
        WHERE NOT EXISTS (
            SELECT 1 FROM tenant_branding WHERE tenant_branding.tenant_id = tenants.id
        )
        """
    )


def downgrade() -> None:
    # Drop tenant_branding table
    op.drop_index("idx_tenant_branding_tenant_id", table_name="tenant_branding")
    op.drop_table("tenant_branding")

    # Remove slug from tenants
    op.drop_index("idx_tenants_slug", table_name="tenants")
    op.drop_constraint("uq_tenants_slug", "tenants", type_="unique")
    op.drop_column("tenants", "slug")







