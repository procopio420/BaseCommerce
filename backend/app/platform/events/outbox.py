"""
Outbox Pattern - Escrita e Leitura de Eventos

Implementa o padrão Outbox para garantir entrega de eventos em transações.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session, relationship

from basecore.db import Base
from app.models.base import BaseModelMixin
from app.platform.events.types import EventType


class OutboxStatus(str, Enum):
    """Status dos eventos no outbox"""

    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"

    def __str__(self) -> str:
        return self.value


class EventOutbox(Base, BaseModelMixin):
    """
    Tabela de outbox para eventos.

    Implementa o padrão Outbox para garantir entrega de eventos em transações.
    Eventos são escritos na mesma transação do write principal e processados assincronamente.
    """

    __tablename__ = "event_outbox"

    tenant_id = Column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    event_type = Column(String(100), nullable=False, index=True)
    event_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True, default=uuid4)
    status = Column(String(20), nullable=False, default=OutboxStatus.PENDING, index=True)
    payload = Column(JSONB, nullable=False)
    version = Column(String(20), nullable=False, default="1.0")
    processed_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)

    tenant = relationship("Tenant", backref="event_outbox")

    __table_args__ = (
        Index("idx_event_outbox_tenant_status", "tenant_id", "status"),
        Index("idx_event_outbox_status_created", "status", "created_at"),
    )


def write_event(
    db: Session,
    event_type: EventType,
    tenant_id: UUID,
    payload: dict,
    version: str = "1.0",
) -> EventOutbox:
    """
    Escreve evento no outbox.

    Esta função DEVE ser chamada dentro da mesma transação do write principal
    para garantir atomicidade (outbox pattern).

    Args:
        db: Sessão do banco de dados (deve estar em uma transação)
        event_type: Tipo do evento (enum EventType)
        tenant_id: UUID do tenant (isolamento multi-tenant)
        payload: Payload do evento (dicionário JSON-serializable)
        version: Versão do contrato do evento (default: "1.0")

    Returns:
        EventOutbox: Evento criado no outbox

    Raises:
        ValueError: Se payload não for JSON-serializable
    """
    event_id = uuid4()

    # Valida que estamos em uma transação
    if not db.in_transaction():
        raise RuntimeError("write_event deve ser chamado dentro de uma transação")

    event = EventOutbox(
        tenant_id=tenant_id,
        event_type=str(event_type),
        event_id=event_id,
        status=OutboxStatus.PENDING,
        payload=payload,
        version=version,
        retry_count=0,
    )

    db.add(event)
    # NÃO faz commit aqui - commit deve ser feito pela transação principal
    db.flush()  # Garante que ID é gerado

    return event


def get_pending_events(
    db: Session,
    limit: int = 100,
    tenant_id: UUID | None = None,
) -> list[EventOutbox]:
    """
    Busca eventos pendentes do outbox.

    Args:
        db: Sessão do banco de dados
        limit: Limite de eventos a retornar (default: 100)
        tenant_id: Opcional - filtrar por tenant específico

    Returns:
        List[EventOutbox]: Lista de eventos pendentes
    """
    query = db.query(EventOutbox).filter(EventOutbox.status == OutboxStatus.PENDING)

    if tenant_id:
        query = query.filter(EventOutbox.tenant_id == tenant_id)

    # Ordena por data de criação (FIFO)
    query = query.order_by(EventOutbox.created_at.asc())

    return query.limit(limit).all()


def mark_processing(db: Session, event_id: UUID) -> EventOutbox | None:
    """
    Marca evento como processando.

    Args:
        db: Sessão do banco de dados
        event_id: UUID do evento

    Returns:
        EventOutbox: Evento atualizado ou None se não encontrado
    """
    event = (
        db.query(EventOutbox)
        .filter(EventOutbox.event_id == event_id, EventOutbox.status == OutboxStatus.PENDING)
        .with_for_update()
        .first()
    )  # Lock pessimista para evitar processamento duplicado

    if not event:
        return None

    event.status = OutboxStatus.PROCESSING
    db.commit()
    db.refresh(event)

    return event


def mark_processed(db: Session, event_id: UUID) -> EventOutbox | None:
    """
    Marca evento como processado com sucesso.

    Args:
        db: Sessão do banco de dados
        event_id: UUID do evento

    Returns:
        EventOutbox: Evento atualizado ou None se não encontrado
    """
    event = (
        db.query(EventOutbox)
        .filter(EventOutbox.event_id == event_id, EventOutbox.status == OutboxStatus.PROCESSING)
        .first()
    )

    if not event:
        return None

    event.status = OutboxStatus.PROCESSED
    event.processed_at = datetime.utcnow()
    db.commit()
    db.refresh(event)

    return event


def mark_failed(
    db: Session,
    event_id: UUID,
    error_message: str,
    max_retries: int = 3,
) -> EventOutbox | None:
    """
    Marca evento como falhado.

    Se retry_count < max_retries, marca como PENDING novamente para retry.
    Caso contrário, marca como FAILED definitivamente.

    Args:
        db: Sessão do banco de dados
        event_id: UUID do evento
        error_message: Mensagem de erro
        max_retries: Número máximo de tentativas (default: 3)

    Returns:
        EventOutbox: Evento atualizado ou None se não encontrado
    """
    event = db.query(EventOutbox).filter(EventOutbox.event_id == event_id).first()

    if not event:
        return None

    event.retry_count += 1
    event.error_message = error_message

    if event.retry_count >= max_retries:
        event.status = OutboxStatus.FAILED
        event.failed_at = datetime.utcnow()
    else:
        # Retry: marca como PENDING novamente
        event.status = OutboxStatus.PENDING
        event.error_message = f"{error_message} (retry {event.retry_count}/{max_retries})"

    db.commit()
    db.refresh(event)

    return event
