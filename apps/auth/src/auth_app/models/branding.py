from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from auth_app.models.base import BaseModelMixin


class TenantBranding(Base, BaseModelMixin):
    """Tenant branding configuration for white-label support."""

    __tablename__ = "tenant_branding"

    tenant_id = Column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    logo_url = Column(String(500), nullable=True)
    primary_color = Column(String(7), default="#1a73e8")  # hex color
    secondary_color = Column(String(7), default="#ea4335")  # hex color
    feature_flags = Column(JSON, default=dict)  # e.g., {"show_insights": true}

    # Relationship back to tenant
    tenant = relationship("Tenant", back_populates="branding")


