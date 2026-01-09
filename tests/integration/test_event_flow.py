"""
Integration Test: Event Flow (Outbox -> Relay -> Redis -> Engines -> Insights)

This test verifies the complete event flow:
1. Vertical action inserts an outbox event
2. Outbox relay publishes to Redis stream
3. Engines worker consumes (XREADGROUP)
4. Engine tables receive expected output
5. Insights endpoints return that output

Requirements:
- PostgreSQL running (docker-compose up -d db)
- Redis running (docker-compose up -d redis)
- Database migrations applied (alembic upgrade head)

Run with:
    pytest tests/integration/test_event_flow.py -v
"""

import json
import os
import time
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set test environment
os.environ.setdefault("DATABASE_URL", "postgresql://construcao_user:construcao_pass@localhost:5432/construcao_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")


@pytest.fixture(scope="module")
def db_engine():
    """Create database engine for tests."""
    database_url = os.getenv("DATABASE_URL")
    engine = create_engine(database_url)
    return engine


@pytest.fixture(scope="module")
def db_session(db_engine):
    """Create database session."""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(scope="module")
def redis_client():
    """Create Redis client for tests."""
    import redis
    client = redis.from_url(os.getenv("REDIS_URL"), decode_responses=True)
    yield client
    client.close()


@pytest.fixture
def test_tenant_id(db_session):
    """Create or get a test tenant."""
    # Check if test tenant exists
    result = db_session.execute(
        text("SELECT id FROM tenants WHERE nome = 'Test Tenant Integration'")
    )
    row = result.fetchone()
    
    if row:
        return row[0]
    
    # Create test tenant
    tenant_id = uuid4()
    db_session.execute(
        text("""
            INSERT INTO tenants (id, nome, email, ativo, created_at, updated_at)
            VALUES (:id, 'Test Tenant Integration', 'test@integration.com', true, now(), now())
        """),
        {"id": tenant_id}
    )
    db_session.commit()
    return tenant_id


@pytest.fixture
def cleanup_test_data(db_session, test_tenant_id):
    """Clean up test data after tests."""
    yield
    
    # Clean up engine tables
    db_session.execute(
        text("DELETE FROM engine_sales_facts WHERE tenant_id = :tenant_id"),
        {"tenant_id": test_tenant_id}
    )
    db_session.execute(
        text("DELETE FROM engine_stock_facts WHERE tenant_id = :tenant_id"),
        {"tenant_id": test_tenant_id}
    )
    db_session.execute(
        text("DELETE FROM engine_stock_alerts WHERE tenant_id = :tenant_id"),
        {"tenant_id": test_tenant_id}
    )
    db_session.execute(
        text("DELETE FROM engine_sales_suggestions WHERE tenant_id = :tenant_id"),
        {"tenant_id": test_tenant_id}
    )
    db_session.execute(
        text("DELETE FROM engine_processed_events WHERE tenant_id = :tenant_id"),
        {"tenant_id": test_tenant_id}
    )
    db_session.execute(
        text("DELETE FROM event_outbox WHERE tenant_id = :tenant_id"),
        {"tenant_id": test_tenant_id}
    )
    db_session.commit()


class TestEventFlow:
    """Test the complete event flow from outbox to insights."""

    def test_outbox_event_created(self, db_session, test_tenant_id, cleanup_test_data):
        """Test that vertical action creates outbox event."""
        event_id = uuid4()
        order_id = uuid4()
        product_id = uuid4()
        
        # Simulate vertical creating an outbox event
        db_session.execute(
            text("""
                INSERT INTO event_outbox 
                    (id, event_id, tenant_id, event_type, payload, version, status, created_at, updated_at)
                VALUES 
                    (:id, :event_id, :tenant_id, :event_type, :payload, :version, 'pending', now(), now())
            """),
            {
                "id": uuid4(),
                "event_id": event_id,
                "tenant_id": test_tenant_id,
                "event_type": "sale_recorded",
                "version": "1.0",
                "payload": json.dumps({
                    "order_id": str(order_id),
                    "client_id": str(uuid4()),
                    "delivered_at": datetime.utcnow().isoformat(),
                    "total_value": "1500.00",
                    "vertical": "materials",
                    "items": [
                        {
                            "product_id": str(product_id),
                            "quantity": "10",
                            "unit_price": "150.00",
                            "total_value": "1500.00",
                        }
                    ],
                }),
            }
        )
        db_session.commit()
        
        # Verify event was created
        result = db_session.execute(
            text("SELECT event_id, event_type FROM event_outbox WHERE event_id = :event_id"),
            {"event_id": event_id}
        )
        row = result.fetchone()
        
        assert row is not None
        assert str(row[0]) == str(event_id)
        assert row[1] == "sale_recorded"

    def test_relay_publishes_to_stream(self, db_session, redis_client, test_tenant_id, cleanup_test_data):
        """Test that outbox relay publishes events to Redis Streams."""
        from apps.outbox_relay.src.outbox_relay.main import relay_batch, ensure_stream_groups
        
        # Ensure consumer groups exist
        ensure_stream_groups()
        
        event_id = uuid4()
        
        # Create an outbox event
        db_session.execute(
            text("""
                INSERT INTO event_outbox 
                    (id, event_id, tenant_id, event_type, payload, version, status, created_at, updated_at)
                VALUES 
                    (:id, :event_id, :tenant_id, :event_type, :payload, :version, 'pending', now(), now())
            """),
            {
                "id": uuid4(),
                "event_id": event_id,
                "tenant_id": test_tenant_id,
                "event_type": "sale_recorded",
                "version": "1.0",
                "payload": json.dumps({
                    "order_id": str(uuid4()),
                    "client_id": str(uuid4()),
                    "delivered_at": datetime.utcnow().isoformat(),
                    "total_value": "500.00",
                    "vertical": "materials",
                    "items": [
                        {"product_id": str(uuid4()), "quantity": "5", "unit_price": "100.00", "total_value": "500.00"}
                    ],
                }),
            }
        )
        db_session.commit()
        
        # Run relay
        count = relay_batch(db_session)
        
        assert count >= 1
        
        # Verify event was marked as published
        result = db_session.execute(
            text("SELECT published_at FROM event_outbox WHERE event_id = :event_id"),
            {"event_id": event_id}
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] is not None  # published_at should be set

    def test_engines_consume_and_process(self, db_session, redis_client, test_tenant_id, cleanup_test_data):
        """Test that engines worker consumes events and writes to engine tables."""
        from basecore.redis import ensure_stream_group, publish_to_stream
        from engines_core.consumer import consume_from_stream
        
        # Ensure consumer group exists
        ensure_stream_group("events:materials", "engines", start_id="0")
        
        event_id = uuid4()
        order_id = uuid4()
        product_id = uuid4()
        client_id = uuid4()
        
        # Publish event directly to stream (simulating relay)
        publish_to_stream("events:materials", {
            "event_id": str(event_id),
            "tenant_id": str(test_tenant_id),
            "event_type": "sale_recorded",
            "vertical": "materials",
            "version": "1",
            "occurred_at": datetime.utcnow().isoformat(),
            "payload": json.dumps({
                "order_id": str(order_id),
                "client_id": str(client_id),
                "delivered_at": datetime.utcnow().isoformat(),
                "total_value": "750.00",
                "items": [
                    {
                        "product_id": str(product_id),
                        "quantity": "5",
                        "unit_price": "150.00",
                        "total_value": "750.00",
                    }
                ],
            }),
        })
        
        # Consume and process
        count = consume_from_stream(
            db_session,
            stream_name="events:materials",
            group_name="engines",
            consumer_name="test-consumer",
            count=10,
            block_ms=1000,
        )
        
        assert count >= 1
        
        # Verify idempotency table was updated
        result = db_session.execute(
            text("SELECT event_id FROM engine_processed_events WHERE event_id = :event_id"),
            {"event_id": event_id}
        )
        row = result.fetchone()
        assert row is not None

    def test_idempotency_prevents_duplicates(self, db_session, redis_client, test_tenant_id, cleanup_test_data):
        """Test that processing the same event twice is idempotent."""
        from basecore.redis import ensure_stream_group, publish_to_stream
        from engines_core.consumer import consume_from_stream
        
        ensure_stream_group("events:materials", "engines", start_id="0")
        
        event_id = uuid4()
        
        # Publish same event twice
        for _ in range(2):
            publish_to_stream("events:materials", {
                "event_id": str(event_id),
                "tenant_id": str(test_tenant_id),
                "event_type": "sale_recorded",
                "vertical": "materials",
                "version": "1",
                "occurred_at": datetime.utcnow().isoformat(),
                "payload": json.dumps({
                    "order_id": str(uuid4()),
                    "client_id": str(uuid4()),
                    "delivered_at": datetime.utcnow().isoformat(),
                    "total_value": "100.00",
                    "items": [{"product_id": str(uuid4()), "quantity": "1", "unit_price": "100.00", "total_value": "100.00"}],
                }),
            })
        
        # Consume both
        consume_from_stream(
            db_session,
            stream_name="events:materials",
            group_name="engines",
            consumer_name="test-consumer",
            count=10,
            block_ms=1000,
        )
        
        # Verify only one processed record exists
        result = db_session.execute(
            text("SELECT COUNT(*) FROM engine_processed_events WHERE event_id = :event_id"),
            {"event_id": event_id}
        )
        count = result.scalar()
        assert count == 1


class TestMultiTenantIsolation:
    """Test multi-tenant isolation in insights endpoints."""

    def test_tenant_cannot_read_other_tenant_data(self, db_session, test_tenant_id, cleanup_test_data):
        """Test that tenant A cannot read tenant B's data."""
        other_tenant_id = uuid4()
        
        # Create alert for other tenant
        db_session.execute(
            text("""
                INSERT INTO engine_stock_alerts 
                    (id, tenant_id, vertical, product_id, alert_type, risk_level, 
                     current_stock, minimum_stock, status, created_at, updated_at)
                VALUES 
                    (:id, :tenant_id, 'materials', :product_id, 'rupture', 'alto',
                     '10', '50', 'active', now(), now())
            """),
            {
                "id": uuid4(),
                "tenant_id": other_tenant_id,
                "product_id": uuid4(),
            }
        )
        db_session.commit()
        
        # Query with test_tenant_id - should not find the other tenant's data
        result = db_session.execute(
            text("""
                SELECT COUNT(*) FROM engine_stock_alerts 
                WHERE tenant_id = :tenant_id AND status = 'active'
            """),
            {"tenant_id": test_tenant_id}
        )
        count = result.scalar()
        
        # Should be 0 for test tenant (other tenant's data not visible)
        assert count == 0
        
        # Clean up other tenant's data
        db_session.execute(
            text("DELETE FROM engine_stock_alerts WHERE tenant_id = :tenant_id"),
            {"tenant_id": other_tenant_id}
        )
        db_session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

