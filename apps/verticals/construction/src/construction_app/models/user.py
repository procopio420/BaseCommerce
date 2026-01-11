"""User model - minimal version for construction app compatibility.

Note: User model is primarily managed by auth service.
This is a minimal model for local compatibility only.
"""

from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID

from basecore.db import Base
from construction_app.models.base import BaseModelMixin


class User(Base, BaseModelMixin):
    """User model - minimal version for construction app compatibility."""

    __tablename__ = "users"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="vendedor")  # admin, vendedor
    ativo = Column(Boolean, default=True)

    # Note: No relationship with Tenant - managed by auth service



