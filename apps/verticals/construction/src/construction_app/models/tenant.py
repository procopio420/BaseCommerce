"""Tenant model - minimal version for construction app compatibility.

Note: Tenant model is primarily managed by auth service.
This is a minimal model for local compatibility only.
"""

from sqlalchemy import Boolean, Column, String, Text

from basecore.db import Base
from construction_app.models.base import BaseModelMixin


class Tenant(Base, BaseModelMixin):
    """Tenant model - minimal version for construction app compatibility."""

    __tablename__ = "tenants"

    nome = Column(String(255), nullable=False)
    slug = Column(String(63), unique=True, nullable=False, index=True)
    cnpj = Column(String(18), unique=True)
    email = Column(String(255), nullable=False)
    telefone = Column(String(20))
    endereco = Column(Text)
    ativo = Column(Boolean, default=True)

    # Note: No relationships - Tenant is managed by auth service






