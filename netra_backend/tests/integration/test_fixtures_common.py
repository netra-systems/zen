"""
Common fixtures and utilities for integration tests.
Extracted from oversized test_critical_missing_integration.py
"""

import pytest
import asyncio
import uuid
import tempfile
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from unittest.mock import Mock, AsyncMock

from netra_backend.app.db.models_postgres import User, Thread, Message, Run
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from netra_backend.app.db.base import Base
from ws_manager import WebSocketManager
from netra_backend.app.core.circuit_breaker import CircuitBreaker


@pytest.fixture
async def test_database():
    """Setup test database for integration testing"""
    db_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    db_url = f"sqlite+aiosqlite:///{db_file.name}"
    engine = create_async_engine(db_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    session = async_session()
    yield {"session": session, "engine": engine, "db_file": db_file.name}
    
    await session.close()
    await engine.dispose()
    os.unlink(db_file.name)


@pytest.fixture
def mock_infrastructure():
    """Setup mock infrastructure components"""
    llm_manager = Mock()
    llm_manager.call_llm = AsyncMock(return_value={"content": "test response"})
    ws_manager = WebSocketManager()
    cache_service = Mock()
    cache_service.get = AsyncMock(return_value=None)
    cache_service.set = AsyncMock(return_value=True)
    
    return {
        "llm_manager": llm_manager,
        "ws_manager": ws_manager,
        "cache_service": cache_service
    }


async def create_test_user_with_oauth(db_setup):
    """Create test user with OAuth credentials"""
    user = User(
        id=str(uuid.uuid4()),
        email="test@example.com",
        oauth_provider="google",
        is_active=True
    )
    db_setup["session"].add(user)
    await db_setup["session"].commit()
    return user


async def setup_circuit_breakers_for_chain(service_chain):
    """Setup circuit breakers for each service"""
    breakers = {}
    for service_name in service_chain:
        breakers[service_name] = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=30,
            expected_exception=Exception
        )
    return breakers


async def setup_clickhouse_mock():
    """Setup ClickHouse mock for transaction testing"""
    ch_mock = Mock()
    ch_mock.execute = AsyncMock()
    ch_mock.begin_transaction = AsyncMock()
    ch_mock.commit = AsyncMock()
    ch_mock.rollback = AsyncMock()
    return ch_mock


def create_test_optimization_data():
    """Create test optimization data for caching"""
    return {
        "optimization_id": str(uuid.uuid4()),
        "gpu_config": {"tensor_parallel": True, "batch_size": 32},
        "performance_metrics": {"latency_p95": 250, "throughput": 1200},
        "cost_savings": 0.35,
        "updated_at": datetime.utcnow().isoformat()
    }


async def verify_state_preservation(original, recovered):
    """Verify state was preserved across reconnection"""
    assert original["state"]["active_threads"] == recovered["state"]["active_threads"]
    assert original["state"]["pending_messages"] == recovered["state"]["pending_messages"]