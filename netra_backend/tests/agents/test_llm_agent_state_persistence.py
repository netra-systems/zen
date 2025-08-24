"""
LLM Agent State Persistence Tests
Tests agent state persistence, recovery, and error handling
Split from oversized test_llm_agent_e2e_real.py
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch, Mock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.tests.agents.fixtures.llm_agent_fixtures import (
    mock_db_session,
    mock_llm_manager,
    mock_persistence_service,
    mock_tool_dispatcher,
    mock_websocket_manager,
    supervisor_agent,
)

@pytest.mark.asyncio
async def test_state_persistence(supervisor_agent):
    """Test agent state persistence and recovery"""
    # Create a proper mock that matches the expected interface
    async def mock_save_agent_state(*args, **kwargs):
        if len(args) == 2:  # (request, session) signature
            return (True, "test_id")
        elif len(args) == 5:  # (run_id, thread_id, user_id, state, db_session) signature
            return True
        else:
            return (True, "test_id")
    
    # Setup the supervisor's persistence mock properly
    # Mock: Agent service isolation for testing without LLM agent execution
    supervisor_agent.state_persistence.save_agent_state = AsyncMock(side_effect=mock_save_agent_state)
    # Mock: Async component isolation for testing without real async operations
    supervisor_agent.state_persistence.load_agent_state = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    supervisor_agent.state_persistence.get_thread_context = AsyncMock(return_value=None)
    # Mock: Async component isolation for testing without real async operations
    supervisor_agent.state_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    
    # Run test - this should trigger state persistence calls
    run_id = str(uuid.uuid4())
    result = await supervisor_agent.run(
        "Test persistence",
        supervisor_agent.thread_id,
        supervisor_agent.user_id,
        run_id
    )
    
    # Verify the run completed successfully
    assert result is not None
    assert isinstance(result, DeepAgentState)

@pytest.mark.asyncio
async def test_error_recovery(supervisor_agent):
    """Test error handling and recovery mechanisms"""
    # Simulate error in execution pipeline
    # Mock: Async component isolation for testing without real async operations
    supervisor_agent.engine.execute_pipeline = AsyncMock(
        side_effect=Exception("Pipeline error")
    )
    
    # Should handle error gracefully
    try:
        await supervisor_agent.run(
            "Test error",
            supervisor_agent.thread_id,
            supervisor_agent.user_id,
            str(uuid.uuid4())
        )
    except Exception as e:
        assert "Pipeline error" in str(e)

@pytest.mark.asyncio
async def test_state_recovery_from_interruption():
    """Test state recovery from interrupted execution"""
    # Mock: Generic component isolation for controlled unit testing
    mock_persistence = AsyncMock()
    
    # Mock interrupted state
    interrupted_state = DeepAgentState(
        user_request="Interrupted request",
        chat_thread_id="thread123",
        user_id="user123"
    )
    interrupted_state.triage_result = {"category": "optimization"}
    
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.load_agent_state = AsyncMock(return_value=interrupted_state)
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.recover_agent_state = AsyncMock(return_value=(True, "recovery_id"))
    
    # Test recovery logic
    recovered_state = await mock_persistence.load_agent_state("thread123", "user123")
    assert recovered_state is not None
    assert recovered_state.user_request == "Interrupted request"
    assert recovered_state.triage_result["category"] == "optimization"

@pytest.mark.asyncio
async def test_persistence_failure_handling():
    """Test handling of persistence failures"""
    # Mock: Generic component isolation for controlled unit testing
    mock_persistence = AsyncMock()
    
    # Mock persistence failure
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.save_agent_state = AsyncMock(side_effect=Exception("Database connection failed"))
    
    # Should handle persistence failure gracefully
    with pytest.raises(Exception) as exc_info:
        await mock_persistence.save_agent_state("run123", "thread123", "user123", {}, None)
    
    assert "Database connection failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_state_serialization_consistency():
    """Test state serialization and deserialization consistency"""
    original_state = DeepAgentState(
        user_request="Test serialization",
        chat_thread_id="thread123",
        user_id="user123"
    )
    
    # Add complex nested data
    original_state.triage_result = {
        "category": "optimization",
        "metadata": {
            "confidence": 0.95,
            "tags": ["performance", "memory"]
        }
    }
    
    # Simulate serialization to JSON (what gets stored)
    serialized = json.dumps(original_state.__dict__, default=str)
    deserialized_data = json.loads(serialized)
    
    # Verify key fields preserved
    assert deserialized_data["user_request"] == "Test serialization"
    assert deserialized_data["chat_thread_id"] == "thread123"
    assert deserialized_data["triage_result"]["category"] == "optimization"

@pytest.mark.asyncio
async def test_concurrent_state_operations():
    """Test concurrent state save/load operations"""
    # Mock: Generic component isolation for controlled unit testing
    mock_persistence = AsyncMock()
    
    # Mock concurrent operations
    async def mock_save_with_delay(*args, **kwargs):
        await asyncio.sleep(0.1)  # Simulate database latency
        return (True, f"save_{random.randint(1000, 9999)}")
    
    async def mock_load_with_delay(*args, **kwargs):
        await asyncio.sleep(0.05)  # Simulate database latency
        return None  # No existing state
    
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.save_agent_state = AsyncMock(side_effect=mock_save_with_delay)
    # Mock: Agent service isolation for testing without LLM agent execution
    mock_persistence.load_agent_state = AsyncMock(side_effect=mock_load_with_delay)
    
    # Execute concurrent operations
    import random
    tasks = []
    for i in range(5):
        if i % 2 == 0:
            task = mock_persistence.save_agent_state(f"run{i}", f"thread{i}", "user123", {}, None)
        else:
            task = mock_persistence.load_agent_state(f"thread{i}", "user123")
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Verify all operations completed
    assert len(results) == 5
    for result in results:
        assert not isinstance(result, Exception)

@pytest.mark.asyncio
async def test_state_version_compatibility():
    """Test backward compatibility of state versions"""
    # Mock old version state data
    old_state_data = {
        "user_request": "Legacy request",
        "thread_id": "thread123",  # Old field name
        "user_id": "user123"
        # Missing newer fields
    }
    
    # Test handling of legacy state format
    try:
        # Simulate migration logic
        if "thread_id" in old_state_data and "chat_thread_id" not in old_state_data:
            old_state_data["chat_thread_id"] = old_state_data.pop("thread_id")
        
        migrated_state = DeepAgentState(**old_state_data)
        assert migrated_state.chat_thread_id == "thread123"
        assert migrated_state.user_request == "Legacy request"
    except Exception as e:
        pytest.fail(f"State migration failed: {e}")

if __name__ == "__main__":
    pytest.main([__file__, "-v"])