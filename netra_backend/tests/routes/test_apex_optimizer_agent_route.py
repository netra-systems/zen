import sys
from pathlib import Path
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import asyncio

import pytest
from fastapi.testclient import TestClient
from netra_backend.app.schemas import DataSource, RequestModel, TimeRange, Workload

from netra_backend.app.config import get_config
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.main import app
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import json

@pytest.mark.parametrize("prompt", [
    "I need to reduce costs but keep quality the same. For feature X, I can accept a latency of 500ms. For feature Y, I need to maintain the current latency of 200ms.",
])
@pytest.mark.asyncio
async def test_apex_optimizer_agent(prompt: str):
    # Create a mock supervisor
    # Mock: Generic component isolation for controlled unit testing
    mock_supervisor = mock_supervisor_instance  # Initialize appropriate service
    # Mock: Async component isolation for testing without real async operations
    mock_supervisor.run = AsyncMock(return_value = {"status": "completed"})
    
    # Override the dependency
    from netra_backend.app.routes.agent_route import get_agent_supervisor
    app.dependency_overrides[get_agent_supervisor] = lambda: mock_supervisor
    
    # Create test client
    client = TestClient(app)
    
    request_model = RequestModel(
        user_id = "test_user",
        query = prompt,
        workloads = [
            Workload(
                run_id = "test_run",
                query = prompt,
                data_source = DataSource(source_table = "test_table"),
                time_range = TimeRange(start_time = "2025-01-01T00:00:00Z", end_time = "2025-01-02T00:00:00Z"),
),
],
)
    response = client.post("/api/agent/run_agent", json = request_model.model_dump())
    assert response.status_code == 200
    result = response.json()
    assert "run_id" in result
    assert result["status"] == "started"
    assert isinstance(result["run_id"], str)
    
    # Clean up the override
    app.dependency_overrides.clear()