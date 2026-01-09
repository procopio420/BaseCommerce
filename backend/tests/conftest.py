"""
Configuração de testes para pytest

Fornece fixtures comuns para todos os testes.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from basecore.db import Base, get_db
from basecore.security import get_password_hash
from app.main import app
from app.models.cliente import Cliente
from app.models.obra import Obra
from app.models.produto import Produto
from app.models.tenant import Tenant
from app.models.user import User

# Banco de dados em memória para testes
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Cria banco de dados limpo para cada teste"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Cria cliente de teste FastAPI"""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def tenant(db):
    """Cria tenant de teste"""
    tenant = Tenant(
        nome="Loja Teste",
        cnpj="12345678000190",
        email="teste@loja.com",
        telefone="1234567890",
        endereco="Rua Teste, 123",
        ativo=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
def user(db, tenant):
    """Cria usuário de teste (admin)"""
    user = User(
        tenant_id=tenant.id,
        nome="Admin Teste",
        email="admin@teste.com",
        password_hash=get_password_hash("senha123"),
        role="admin",
        ativo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(client, user):
    """Retorna headers de autenticação para testes"""
    # Login para obter token
    response = client.post("/api/v1/auth/login", json={"email": user.email, "password": "senha123"})
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def cliente(db, tenant):
    """Cria cliente de teste"""
    cliente = Cliente(
        tenant_id=tenant.id,
        tipo="PJ",
        nome="Construtora Teste",
        documento="12345678000199",
        email="cliente@teste.com",
        telefone="9876543210",
        endereco="Rua Cliente, 456",
        cidade="Barra Mansa",
        estado="RJ",
        cep="27300000",
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@pytest.fixture(scope="function")
def obra(db, tenant, cliente):
    """Cria obra de teste"""
    obra = Obra(
        tenant_id=tenant.id,
        cliente_id=cliente.id,
        nome="Obra Teste",
        endereco="Rua Obra, 789",
        cidade="Volta Redonda",
        estado="RJ",
        ativa=True,
    )
    db.add(obra)
    db.commit()
    db.refresh(obra)
    return obra


@pytest.fixture(scope="function")
def produto(db, tenant):
    """Cria produto de teste"""
    produto = Produto(
        tenant_id=tenant.id,
        codigo="PROD-001",
        nome="Cimento CP II",
        descricao="Cimento Portland CP II",
        unidade="KG",
        preco_base=Decimal("32.00"),
        ativo=True,
    )
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto
