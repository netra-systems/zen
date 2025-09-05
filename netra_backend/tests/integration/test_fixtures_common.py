"""
Common fixtures and utilities for integration tests.
Extracted from oversized test_critical_missing_integration.py
"""

from netra_backend.app.websocket_core import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import asyncio
import os
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.db.base import Base

from netra_backend.app.db.models_postgres import Message, Run, Thread, User
from netra_backend.app.websocket_core import WebSocketManager

@pytest.fixture

@pytest.mark.asyncio
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

    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager = Mock()

    # Mock: LLM provider isolation to prevent external API usage and costs
    llm_manager.call_llm = AsyncMock(return_value={"content": "test response"})

    ws_manager = WebSocketManager()

    # Mock: Generic component isolation for controlled unit testing
    cache_service = Mock()

    # Mock: Async component isolation for testing without real async operations
    cache_service.get = AsyncMock(return_value=None)

    # Mock: Async component isolation for testing without real async operations
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

    # Mock: Generic component isolation for controlled unit testing
    ch_mock = Mock()

    # Mock: Generic component isolation for controlled unit testing
    ch_mock.execute = AsyncMock()

    # Mock: Generic component isolation for controlled unit testing
    ch_mock.begin_transaction = AsyncMock()

    # Mock: Generic component isolation for controlled unit testing
    ch_mock.commit = AsyncMock()

    # Mock: Generic component isolation for controlled unit testing
    ch_mock.rollback = AsyncMock()

    return ch_mock

def create_test_optimization_data():

    """Create test optimization data for caching"""

    return {

        "optimization_id": str(uuid.uuid4()),

        "gpu_config": {"tensor_parallel": True, "batch_size": 32},

        "performance_metrics": {"latency_p95": 250, "throughput": 1200},

        "cost_savings": 0.35,

        "updated_at": datetime.now(timezone.utc).isoformat()

    }

async def verify_state_preservation(original, recovered):

    """Verify state was preserved across reconnection"""

    assert original["state"]["active_threads"] == recovered["state"]["active_threads"]

    assert original["state"]["pending_messages"] == recovered["state"]["pending_messages"]