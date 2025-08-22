"""E2E test fixtures and configuration."""

import pytest
import asyncio
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

# Basic test setup fixtures
@pytest.fixture
async def mock_agent_service():
    """Mock agent service for E2E tests."""
    mock_service = AsyncMock()
    mock_service.process_message.return_value = {
        "response": "Test response",
        "metadata": {"test": True}
    }
    return mock_service

@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager for E2E tests."""
    mock_manager = MagicMock()
    mock_manager.send_message = AsyncMock()
    mock_manager.broadcast = AsyncMock()
    return mock_manager

@pytest.fixture
def model_selection_setup():
    """Basic setup for model selection tests."""
    return {
        "mock_llm_service": AsyncMock(),
        "mock_database": AsyncMock(),
        "test_config": {"environment": "test"}
    }

# Real LLM testing configuration
@pytest.fixture
def real_llm_config():
    """Configuration for real LLM testing."""
    return {
        "enabled": False,  # Default to disabled
        "timeout": 30.0,
        "max_retries": 3
    }
