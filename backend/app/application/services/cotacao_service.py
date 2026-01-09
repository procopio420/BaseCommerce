"""
Serviço de aplicação para cotações

Orquestra a criação, edição e gestão de cotações.
Não contém lógica de domínio (fica no domínio), apenas orquestra.

NOTE: Engine logic removed - all engine processing happens via events.
Sales suggestions are available via /insights/sales/suggestions endpoints.
"""

import logging
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.cotacao.exceptions import (
    CotacaoNaoPodeSerAprovadaException,
    CotacaoNaoPodeSerEditadaException,
    CotacaoNaoPodeSerEnviadaException,
)
from app.domain.cotacao.validators import (
    calcular_valor_total_item,
    validar_cotacao_para_envio,
)
from app.models.cliente import Cliente
from app.models.cotacao import Cotacao, CotacaoItem
from app.models.obra import Obra
from app.models.produto import Produto

logger = logging.getLogger(__name__)


class CotacaoService:
    """Serviço de aplicação para gestão de cotações"""

    def __init__(self, db: Session):
        self.db = db

    def gerar_numero_cotacao(self, tenant_id: UUID) -> str:
        """
        Gera número sequencial de cotação para o tenant.

        Formato: COT-001, COT-002, etc.
        """
        ultima_cotacao = (
            self.db.query(Cotacao)
            .filter(Cotacao.tenant_id == tenant_id)
            .order_by(Cotacao.created_at.desc())
            .first()
        )

        if ultima_cotacao and ultima_cotacao.numero:
            try:
                ultimo_numero = int(ultima_cotacao.numero.split("-")[-1])
                novo_numero = ultimo_numero + 1
            except (ValueError, IndexError):
                novo_numero = 1
        else:
            novo_numero = 1

        return f"COT-{novo_numero:03d}"

    def criar_cotacao(
        self,
        tenant_id: UUID,
        cliente_id: UUID,
        usuario_id: UUID,
        itens: list,
        obra_id: UUID | None = None,
        desconto_percentual: Decimal = Decimal("0"),
        observacoes: str | None = None,
        validade_dias: int = 7,
    ) -> Cotacao:
        """
        Cria nova cotação.

        Validações:
        - Cliente deve existir
        - Obra deve existir e pertencer ao cliente (se fornecida)
        - Produtos devem existir e estar ativos
        - Deve ter pelo menos 1 item

        Note: Sales suggestions are available via /insights/sales/complementary/{product_id}
        """
        # Valida cliente
        cliente = (
            self.db.query(Cliente)
            .filter(Cliente.id == cliente_id, Cliente.tenant_id == tenant_id)
            .first()
        )

        if not cliente:
            raise ValueError("Cliente não encontrado")

        # Valida obra se fornecida
        if obra_id:
            obra = (
                self.db.query(Obra)
                .filter(
                    Obra.id == obra_id, Obra.tenant_id == tenant_id, Obra.cliente_id == cliente_id
                )
                .first()
            )

            if not obra:
                raise ValueError("Obra não encontrada ou não pertence ao cliente")

        # Valida produtos e cria itens
        cotacao_itens = []
        for idx, item_data in enumerate(itens):
            produto = (
                self.db.query(Produto)
                .filter(
                    Produto.id == item_data["produto_id"],
                    Produto.tenant_id == tenant_id,
                    Produto.ativo is True,
                )
                .first()
            )

            if not produto:
                raise ValueError(f"Produto {item_data['produto_id']} não encontrado ou inativo")

            # Usa preço do produto se não fornecido ou se fornecido mas é 0
            preco_unitario_fornecido = item_data.get("preco_unitario")
            if preco_unitario_fornecido is None or preco_unitario_fornecido == 0:
                preco_unitario = produto.preco_base
            else:
                preco_unitario = preco_unitario_fornecido
            desconto_item = item_data.get("desconto_percentual", Decimal("0"))

            valor_total = calcular_valor_total_item(
                item_data["quantidade"], preco_unitario, desconto_item
            )

            cotacao_itens.append(
                {
                    "produto": produto,
                    "quantidade": item_data["quantidade"],
                    "preco_unitario": preco_unitario,
                    "desconto_percentual": desconto_item,
                    "valor_total": valor_total,
                    "observacoes": item_data.get("observacoes"),
                    "ordem": item_data.get("ordem", idx),
                }
            )

        if not cotacao_itens:
            raise ValueError("Cotação deve ter pelo menos um item")

        # Cria cotação
        numero = self.gerar_numero_cotacao(tenant_id)

        cotacao = Cotacao(
            tenant_id=tenant_id,
            cliente_id=cliente_id,
            obra_id=obra_id,
            numero=numero,
            status="rascunho",
            desconto_percentual=desconto_percentual,
            observacoes=observacoes,
            validade_dias=validade_dias,
            usuario_id=usuario_id,
        )

        self.db.add(cotacao)
        self.db.flush()

        # Cria itens
        for item_data in cotacao_itens:
            item = CotacaoItem(
                tenant_id=tenant_id,
                cotacao_id=cotacao.id,
                produto_id=item_data["produto"].id,
                quantidade=item_data["quantidade"],
                preco_unitario=item_data["preco_unitario"],
                desconto_percentual=item_data["desconto_percentual"],
                valor_total=item_data["valor_total"],
                observacoes=item_data["observacoes"],
                ordem=item_data["ordem"],
            )
            self.db.add(item)

        self.db.commit()
        self.db.refresh(cotacao)

        return cotacao

    def atualizar_cotacao(
        self,
        cotacao_id: UUID,
        tenant_id: UUID,
        itens: list | None = None,
        desconto_percentual: Decimal | None = None,
        observacoes: str | None = None,
        validade_dias: int | None = None,
    ) -> Cotacao:
        """
        Atualiza cotação (apenas se for rascunho).

        Validações:
        - Cotação deve existir
        - Cotação deve estar em rascunho
        - Se itens fornecidos, produtos devem existir e estar ativos
        """
        cotacao = (
            self.db.query(Cotacao)
            .filter(Cotacao.id == cotacao_id, Cotacao.tenant_id == tenant_id)
            .first()
        )

        if not cotacao:
            raise ValueError("Cotação não encontrada")

        if cotacao.status != "rascunho":
            raise CotacaoNaoPodeSerEditadaException(
                "Apenas cotações em rascunho podem ser editadas"
            )

        # Atualiza campos básicos
        if desconto_percentual is not None:
            cotacao.desconto_percentual = desconto_percentual

        if observacoes is not None:
            cotacao.observacoes = observacoes

        if validade_dias is not None:
            cotacao.validade_dias = validade_dias

        # Se itens fornecidos, substitui todos os itens
        if itens is not None:
            # Remove itens antigos
            self.db.query(CotacaoItem).filter(
                CotacaoItem.cotacao_id == cotacao_id, CotacaoItem.tenant_id == tenant_id
            ).delete()

            # Cria novos itens
            for idx, item_data in enumerate(itens):
                produto = (
                    self.db.query(Produto)
                    .filter(
                        Produto.id == item_data["produto_id"],
                        Produto.tenant_id == tenant_id,
                        Produto.ativo is True,
                    )
                    .first()
                )

                if not produto:
                    raise ValueError(f"Produto {item_data['produto_id']} não encontrado ou inativo")

                preco_unitario_fornecido = item_data.get("preco_unitario")
                if preco_unitario_fornecido is None or preco_unitario_fornecido == 0:
                    preco_unitario = produto.preco_base
                else:
                    preco_unitario = preco_unitario_fornecido
                desconto_item = item_data.get("desconto_percentual", Decimal("0"))

                valor_total = calcular_valor_total_item(
                    item_data["quantidade"], preco_unitario, desconto_item
                )

                item = CotacaoItem(
                    tenant_id=tenant_id,
                    cotacao_id=cotacao.id,
                    produto_id=produto.id,
                    quantidade=item_data["quantidade"],
                    preco_unitario=preco_unitario,
                    desconto_percentual=desconto_item,
                    valor_total=valor_total,
                    observacoes=item_data.get("observacoes"),
                    ordem=item_data.get("ordem", idx),
                )
                self.db.add(item)

        self.db.commit()
        self.db.refresh(cotacao)

        return cotacao

    def enviar_cotacao(self, cotacao_id: UUID, tenant_id: UUID) -> Cotacao:
        """
        Envia cotação (muda status para 'enviada').

        Validações:
        - Cotação deve existir
        - Cotação deve estar em rascunho
        - Cotação deve ter pelo menos 1 item
        """
        cotacao = (
            self.db.query(Cotacao)
            .filter(Cotacao.id == cotacao_id, Cotacao.tenant_id == tenant_id)
            .first()
        )

        if not cotacao:
            raise ValueError("Cotação não encontrada")

        if cotacao.status != "rascunho":
            raise CotacaoNaoPodeSerEnviadaException(
                "Apenas cotações em rascunho podem ser enviadas"
            )

        # Valida cotação para envio (deve ter itens)
        validar_cotacao_para_envio(cotacao.itens, cotacao.desconto_percentual)

        cotacao.status = "enviada"
        cotacao.enviada_em = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cotacao)

        return cotacao

    def aprovar_cotacao(self, cotacao_id: UUID, tenant_id: UUID) -> Cotacao:
        """
        Aprova cotação (muda status para 'aprovada').

        Validações:
        - Cotação deve existir
        - Cotação deve estar enviada
        """
        cotacao = (
            self.db.query(Cotacao)
            .filter(Cotacao.id == cotacao_id, Cotacao.tenant_id == tenant_id)
            .first()
        )

        if not cotacao:
            raise ValueError("Cotação não encontrada")

        if cotacao.status != "enviada":
            raise CotacaoNaoPodeSerAprovadaException("Apenas cotações enviadas podem ser aprovadas")

        cotacao.status = "aprovada"
        cotacao.aprovada_em = datetime.utcnow()

        self.db.commit()
        self.db.refresh(cotacao)

        return cotacao

    def cancelar_cotacao(self, cotacao_id: UUID, tenant_id: UUID) -> Cotacao:
        """
        Cancela cotação.

        Validações:
        - Cotação deve existir
        - Cotação não pode estar convertida
        """
        cotacao = (
            self.db.query(Cotacao)
            .filter(Cotacao.id == cotacao_id, Cotacao.tenant_id == tenant_id)
            .first()
        )

        if not cotacao:
            raise ValueError("Cotação não encontrada")

        if cotacao.status == "convertida":
            raise CotacaoNaoPodeSerEditadaException(
                "Não é possível cancelar uma cotação já convertida em pedido"
            )

        cotacao.status = "cancelada"

        self.db.commit()
        self.db.refresh(cotacao)

        return cotacao
