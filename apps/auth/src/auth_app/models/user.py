from sqlalchemy import Boolean, Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from basecore.db import Base
from auth_app.models.base import BaseModelMixin


class User(Base, BaseModelMixin):
    """User model - represents a user within a tenant."""

    __tablename__ = "users"

    tenant_id = Column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nome = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="vendedor")  # admin, vendedor
    ativo = Column(Boolean, default=True)

    tenant = relationship("Tenant", back_populates="users")







