from sqlalchemy import Boolean, Column, String, Text
from sqlalchemy.orm import relationship

from basecore.db import Base
from auth_app.models.base import BaseModelMixin


class Tenant(Base, BaseModelMixin):
    """Tenant model - represents a customer organization."""

    __tablename__ = "tenants"

    nome = Column(String(255), nullable=False)
    slug = Column(String(63), unique=True, nullable=False, index=True)  # subdomain identifier
    cnpj = Column(String(18), unique=True)
    email = Column(String(255), nullable=False)
    telefone = Column(String(20))
    endereco = Column(Text)
    ativo = Column(Boolean, default=True)

    # Relationship to branding
    branding = relationship("TenantBranding", back_populates="tenant", uselist=False)
    users = relationship("User", back_populates="tenant")



