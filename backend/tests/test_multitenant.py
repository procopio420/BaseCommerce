"""
Testes de multi-tenant

Garante que um tenant não pode acessar dados de outro tenant.
Isolamento total entre tenants é crítico para segurança.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi import status


@pytest.fixture(scope="function")
def tenant2(db):
    """Cria segundo tenant de teste"""
    from app.models.tenant import Tenant

    tenant = Tenant(
        nome="Loja Teste 2",
        cnpj="98765432000111",
        email="teste2@loja.com",
        telefone="0987654321",
        endereco="Rua Teste 2, 456",
        ativo=True,
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    return tenant


@pytest.fixture(scope="function")
def user2(db, tenant2):
    """Cria segundo usuário de teste (admin)"""
    from basecore.security import get_password_hash
    from app.models.user import User

    user = User(
        tenant_id=tenant2.id,
        nome="Admin Teste 2",
        email="admin2@teste.com",
        password_hash=get_password_hash("senha456"),
        role="admin",
        ativo=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers2(client, user2):
    """Retorna headers de autenticação do segundo tenant"""
    response = client.post(
        "/api/v1/auth/login", json={"email": user2.email, "password": "senha456"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def cliente2(db, tenant2):
    """Cria cliente do segundo tenant"""
    from app.models.cliente import Cliente

    cliente = Cliente(
        tenant_id=tenant2.id,
        tipo="PF",
        nome="Cliente Teste 2",
        documento="12345678900",
        email="cliente2@teste.com",
        telefone="1111111111",
        endereco="Rua Cliente 2, 789",
        cidade="Barra Mansa",
        estado="RJ",
        cep="27300000",
    )
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return cliente


@pytest.fixture(scope="function")
def produto2(db, tenant2):
    """Cria produto do segundo tenant"""
    from app.models.produto import Produto

    produto = Produto(
        tenant_id=tenant2.id,
        codigo="PROD-002",
        nome="Produto Teste 2",
        descricao="Descrição do produto 2",
        unidade="UN",
        preco_base=Decimal("50.00"),
        ativo=True,
    )
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


def test_tenant1_nao_pode_acessar_cliente_tenant2(client, auth_headers, cliente2):
    """Testa que tenant 1 não pode acessar cliente do tenant 2"""
    response = client.get(f"/api/v1/clientes/{cliente2.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant2_nao_pode_acessar_cliente_tenant1(client, auth_headers2, cliente):
    """Testa que tenant 2 não pode acessar cliente do tenant 1"""
    response = client.get(f"/api/v1/clientes/{cliente.id}", headers=auth_headers2)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant1_nao_pode_listar_clientes_tenant2(client, auth_headers, cliente2):
    """Testa que tenant 1 não lista clientes do tenant 2"""
    response = client.get("/api/v1/clientes/", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    clientes = response.json()

    # Verifica que nenhum cliente do tenant 2 está na lista
    cliente_ids = [c["id"] for c in clientes]
    assert str(cliente2.id) not in cliente_ids


def test_tenant1_nao_pode_acessar_produto_tenant2(client, auth_headers, produto2):
    """Testa que tenant 1 não pode acessar produto do tenant 2"""
    response = client.get(f"/api/v1/produtos/{produto2.id}", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant1_nao_pode_usar_produto_tenant2_em_cotacao(client, auth_headers, cliente, produto2):
    """Testa que tenant 1 não pode criar cotação com produto do tenant 2"""
    cotacao_data = {
        "cliente_id": str(cliente.id),
        "desconto_percentual": "0",
        "validade_dias": 7,
        "itens": [
            {
                "produto_id": str(produto2.id),
                "quantidade": "10",
                "preco_unitario": "50.00",
                "desconto_percentual": "0",
                "ordem": 0,
            }
        ],
    }

    response = client.post("/api/v1/cotacoes/", json=cotacao_data, headers=auth_headers)

    # Deve falhar porque produto não pertence ao tenant 1
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant1_nao_pode_acessar_cotacao_tenant2(
    client, auth_headers, auth_headers2, cliente2, produto2
):
    """Testa que tenant 1 não pode acessar cotação criada pelo tenant 2"""
    # Tenant 2 cria uma cotação
    cotacao_data = {
        "cliente_id": str(cliente2.id),
        "desconto_percentual": "0",
        "validade_dias": 7,
        "itens": [
            {
                "produto_id": str(produto2.id),
                "quantidade": "5",
                "preco_unitario": "50.00",
                "desconto_percentual": "0",
                "ordem": 0,
            }
        ],
    }

    response = client.post("/api/v1/cotacoes/", json=cotacao_data, headers=auth_headers2)

    assert response.status_code == status.HTTP_201_CREATED
    cotacao_id = response.json()["id"]

    # Tenant 1 tenta acessar cotação do tenant 2
    response = client.get(f"/api/v1/cotacoes/{cotacao_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant1_nao_pode_listar_cotacoes_tenant2(
    client, auth_headers, auth_headers2, cliente2, produto2
):
    """Testa que tenant 1 não lista cotações do tenant 2"""
    # Tenant 2 cria uma cotação
    cotacao_data = {
        "cliente_id": str(cliente2.id),
        "desconto_percentual": "0",
        "validade_dias": 7,
        "itens": [
            {
                "produto_id": str(produto2.id),
                "quantidade": "5",
                "preco_unitario": "50.00",
                "desconto_percentual": "0",
                "ordem": 0,
            }
        ],
    }

    response = client.post("/api/v1/cotacoes/", json=cotacao_data, headers=auth_headers2)

    assert response.status_code == status.HTTP_201_CREATED
    cotacao_id = response.json()["id"]

    # Tenant 1 lista cotações
    response = client.get("/api/v1/cotacoes/", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    cotacoes = response.json()

    # Verifica que nenhuma cotação do tenant 2 está na lista
    cotacao_ids = [c["id"] for c in cotacoes]
    assert cotacao_id not in cotacao_ids


def test_tenant1_nao_pode_editar_cotacao_tenant2(
    client, auth_headers, auth_headers2, cliente2, produto2
):
    """Testa que tenant 1 não pode editar cotação do tenant 2"""
    # Tenant 2 cria uma cotação
    cotacao_data = {
        "cliente_id": str(cliente2.id),
        "desconto_percentual": "0",
        "validade_dias": 7,
        "itens": [
            {
                "produto_id": str(produto2.id),
                "quantidade": "5",
                "preco_unitario": "50.00",
                "desconto_percentual": "0",
                "ordem": 0,
            }
        ],
    }

    response = client.post("/api/v1/cotacoes/", json=cotacao_data, headers=auth_headers2)

    assert response.status_code == status.HTTP_201_CREATED
    cotacao_id = response.json()["id"]

    # Tenant 1 tenta editar cotação do tenant 2
    update_data = {"observacoes": "Tentativa de edição não autorizada"}

    response = client.put(f"/api/v1/cotacoes/{cotacao_id}", json=update_data, headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant1_nao_pode_converter_cotacao_tenant2(
    client, auth_headers, auth_headers2, cliente2, produto2
):
    """Testa que tenant 1 não pode converter cotação do tenant 2"""
    # Tenant 2 cria, envia e aprova uma cotação
    cotacao_data = {
        "cliente_id": str(cliente2.id),
        "desconto_percentual": "0",
        "validade_dias": 7,
        "itens": [
            {
                "produto_id": str(produto2.id),
                "quantidade": "5",
                "preco_unitario": "50.00",
                "desconto_percentual": "0",
                "ordem": 0,
            }
        ],
    }

    response = client.post("/api/v1/cotacoes/", json=cotacao_data, headers=auth_headers2)

    assert response.status_code == status.HTTP_201_CREATED
    cotacao_id = response.json()["id"]

    # Envia e aprova com tenant 2
    response = client.post(f"/api/v1/cotacoes/{cotacao_id}/enviar", headers=auth_headers2)
    assert response.status_code == status.HTTP_200_OK

    response = client.post(f"/api/v1/cotacoes/{cotacao_id}/aprovar", headers=auth_headers2)
    assert response.status_code == status.HTTP_200_OK

    # Tenant 1 tenta converter cotação do tenant 2
    response = client.post(f"/api/v1/pedidos/from-cotacao/{cotacao_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant1_nao_pode_acessar_pedido_tenant2(
    client, auth_headers, auth_headers2, cliente2, produto2
):
    """Testa que tenant 1 não pode acessar pedido do tenant 2"""
    # Tenant 2 cria, envia e aprova uma cotação e converte em pedido
    cotacao_data = {
        "cliente_id": str(cliente2.id),
        "desconto_percentual": "0",
        "validade_dias": 7,
        "itens": [
            {
                "produto_id": str(produto2.id),
                "quantidade": "5",
                "preco_unitario": "50.00",
                "desconto_percentual": "0",
                "ordem": 0,
            }
        ],
    }

    response = client.post("/api/v1/cotacoes/", json=cotacao_data, headers=auth_headers2)

    cotacao_id = response.json()["id"]

    response = client.post(f"/api/v1/cotacoes/{cotacao_id}/enviar", headers=auth_headers2)

    response = client.post(f"/api/v1/cotacoes/{cotacao_id}/aprovar", headers=auth_headers2)

    response = client.post(f"/api/v1/pedidos/from-cotacao/{cotacao_id}", headers=auth_headers2)

    assert response.status_code == status.HTTP_201_CREATED
    pedido_id = response.json()["id"]

    # Tenant 1 tenta acessar pedido do tenant 2
    response = client.get(f"/api/v1/pedidos/{pedido_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "não encontrado" in response.json()["detail"].lower()


def test_tenant1_nao_pode_listar_pedidos_tenant2(
    client, auth_headers, auth_headers2, cliente2, produto2
):
    """Testa que tenant 1 não lista pedidos do tenant 2"""
    # Tenant 2 cria pedido (via cotação)
    cotacao_data = {
        "cliente_id": str(cliente2.id),
        "desconto_percentual": "0",
        "validade_dias": 7,
        "itens": [
            {
                "produto_id": str(produto2.id),
                "quantidade": "5",
                "preco_unitario": "50.00",
                "desconto_percentual": "0",
                "ordem": 0,
            }
        ],
    }

    response = client.post("/api/v1/cotacoes/", json=cotacao_data, headers=auth_headers2)

    cotacao_id = response.json()["id"]

    response = client.post(f"/api/v1/cotacoes/{cotacao_id}/enviar", headers=auth_headers2)

    response = client.post(f"/api/v1/cotacoes/{cotacao_id}/aprovar", headers=auth_headers2)

    response = client.post(f"/api/v1/pedidos/from-cotacao/{cotacao_id}", headers=auth_headers2)

    assert response.status_code == status.HTTP_201_CREATED
    pedido_id = response.json()["id"]

    # Tenant 1 lista pedidos
    response = client.get("/api/v1/pedidos/", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    pedidos = response.json()

    # Verifica que nenhum pedido do tenant 2 está na lista
    pedido_ids = [p["id"] for p in pedidos]
    assert pedido_id not in pedido_ids
