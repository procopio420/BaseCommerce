from sqlalchemy import Boolean, Column, String, Text

from basecore.db import Base
from app.models.base import BaseModelMixin


class Tenant(Base, BaseModelMixin):
    __tablename__ = "tenants"

    nome = Column(String(255), nullable=False)
    cnpj = Column(String(18), unique=True)
    email = Column(String(255), nullable=False)
    telefone = Column(String(20))
    endereco = Column(Text)
    ativo = Column(Boolean, default=True)
