"""
Shared fixtures and data models for real services tests.
All functions ≤8 lines per requirements.
"""

import os

import pytest
from pydantic import BaseModel


class Thread(BaseModel):
    """Model for thread creation"""
    title: str
    user_id: str


class MessageCreate(BaseModel):
    """Model for message creation"""
    thread_id: str
    user_id: str
    content: str
    role: str = "user"


def _has_any_real_services_enabled() -> bool:
    """Check if any real services are enabled"""
    return any([
        os.environ.get("ENABLE_REAL_LLM_TESTING") == "true",
        os.environ.get("ENABLE_REAL_DB_TESTING") == "true",
        os.environ.get("ENABLE_REAL_REDIS_TESTING") == "true",
        os.environ.get("ENABLE_REAL_CLICKHOUSE_TESTING") == "true"
    ])


# Test markers for different service types
pytestmark = [
    pytest.mark.real_services,
    pytest.mark.real_llm,
    pytest.mark.real_database,
    pytest.mark.real_redis,
    pytest.mark.real_clickhouse,
    pytest.mark.e2e
]

# Skip tests if real services not enabled
skip_if_no_real_services = pytest.mark.skipif(
    not _has_any_real_services_enabled(),
    reason="Real service tests disabled. Set ENABLE_REAL_LLM_TESTING=true or database/redis/clickhouse env vars"
)

# Database-specific skip conditions
skip_if_no_database = pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_DB_TESTING") != "true",
    reason="Real database tests disabled. Set ENABLE_REAL_DB_TESTING=true to run"
)

skip_if_no_redis = pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_REDIS_TESTING") != "true",
    reason="Real Redis tests disabled. Set ENABLE_REAL_REDIS_TESTING=true to run"
)

skip_if_no_clickhouse = pytest.mark.skipif(
    os.environ.get("ENABLE_REAL_CLICKHOUSE_TESTING") != "true",
    reason="Real ClickHouse tests disabled. Set ENABLE_REAL_CLICKHOUSE_TESTING=true to run"
)


def get_test_user_id() -> str:
    """Get test user ID"""
    return "test_user_123"


def get_test_thread_data() -> dict:
    """Get test thread data"""
    return {
        "title": "Test Thread",
        "user_id": get_test_user_id()
    }


def get_test_message_data(thread_id: str) -> dict:
    """Get test message data"""
    return {
        "thread_id": thread_id,
        "user_id": get_test_user_id(),
        "content": "Test message content",
        "role": "user"
    }