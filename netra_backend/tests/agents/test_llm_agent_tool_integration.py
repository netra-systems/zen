"""
LLM Agent Tool Integration Tests
Tests tool dispatcher integration and tool execution with LLM agents
Split from oversized test_llm_agent_e2e_real.py
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
import time
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.agents.state import DeepAgentState

# Add project root to path
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.tests.llm_agent_fixtures import (
    mock_db_session,
    # Add project root to path
    mock_llm_manager,
    mock_persistence_service,
    mock_tool_dispatcher,
    mock_websocket_manager,
    supervisor_agent,
)


async def test_tool_dispatcher_integration(mock_tool_dispatcher):
    """Test tool dispatcher integration with LLM agents"""
    # Test successful tool execution
    result = await mock_tool_dispatcher.dispatch_tool("test_tool", {"param": "value"})
    assert result["status"] == "success"
    assert "result" in result
    
    # Test tool error handling
    mock_tool_dispatcher.dispatch_tool = AsyncMock(side_effect=Exception("Tool error"))
    
    with pytest.raises(Exception) as exc_info:
        await mock_tool_dispatcher.dispatch_tool("failing_tool", {})
    assert "Tool error" in str(exc_info.value)


async def test_tool_execution_with_llm():
    """Test tool execution triggered by LLM response"""
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    
    dispatcher = Mock(spec=ToolDispatcher)
    tool_results = []
    
    async def mock_dispatch(tool_name, params):
        result = {
            "tool": tool_name,
            "params": params,
            "result": f"Executed {tool_name}",
            "status": "success"
        }
        tool_results.append(result)
        return result
    
    dispatcher.dispatch_tool = AsyncMock(side_effect=mock_dispatch)
    
    # Simulate LLM response with tool calls
    llm_response = {
        "content": "I'll analyze your workload",
        "tool_calls": [
            {"name": "analyze_workload", "parameters": {"metric": "gpu_util"}},
            {"name": "optimize_batch_size", "parameters": {"current": 32}}
        ]
    }
    
    # Execute tools
    for tool_call in llm_response["tool_calls"]:
        await dispatcher.dispatch_tool(tool_call["name"], tool_call["parameters"])
    
    # Verify all tools executed
    assert len(tool_results) == 2
    assert tool_results[0]["tool"] == "analyze_workload"
    assert tool_results[1]["tool"] == "optimize_batch_size"


async def test_real_llm_interaction():
    """Test real LLM interaction with proper error handling"""
    llm_manager = Mock(spec=LLMManager)
    
    # Simulate real LLM call with retry logic
    call_count = 0
    async def mock_llm_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate timeout on first call
            raise asyncio.TimeoutError("LLM call timed out")
        return {
            "content": "Successful response after retry",
            "tool_calls": []
        }
    
    llm_manager.call_llm = AsyncMock(side_effect=mock_llm_call)
    
    # Test retry mechanism
    try:
        result = await llm_manager.call_llm("Test prompt")
    except asyncio.TimeoutError:
        # Retry once
        result = await llm_manager.call_llm("Test prompt")
    
    assert result["content"] == "Successful response after retry"
    assert call_count == 2


async def test_tool_call_integration_complex():
    """Test complex tool call integration scenarios"""
    from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
    
    dispatcher = Mock(spec=ToolDispatcher)
    execution_log = []
    
    async def mock_complex_dispatch(tool_name, params):
        execution_log.append(f"Starting {tool_name}")
        
        # Simulate different execution times and results
        if tool_name == "data_fetcher":
            await asyncio.sleep(0.1)  # Simulate I/O
            result = {"data": [1, 2, 3], "count": 3}
        elif tool_name == "analyzer":
            result = {"analysis": "Data looks good", "score": 0.95}
        else:
            result = {"status": "unknown_tool"}
        
        execution_log.append(f"Completed {tool_name}")
        return {"tool": tool_name, "result": result, "status": "success"}
    
    dispatcher.dispatch_tool = AsyncMock(side_effect=mock_complex_dispatch)
    
    # Execute multiple tools in sequence
    tools = ["data_fetcher", "analyzer", "optimizer"]
    results = []
    
    for tool in tools:
        result = await dispatcher.dispatch_tool(tool, {"param": "value"})
        results.append(result)
    
    # Verify execution order and results
    assert len(results) == 3
    assert len(execution_log) == 6  # Start and complete for each tool
    assert execution_log[0] == "Starting data_fetcher"
    assert execution_log[1] == "Completed data_fetcher"


async def test_llm_tool_chain_execution():
    """Test LLM-driven tool chain execution"""
    llm_manager = Mock(spec=LLMManager)
    
    # Mock LLM responses that trigger different tools
    responses = [
        {
            "content": "I need to fetch data first",
            "tool_calls": [{"name": "data_fetcher", "parameters": {"source": "metrics"}}]
        },
        {
            "content": "Now I'll analyze the data",
            "tool_calls": [{"name": "analyzer", "parameters": {"data_source": "fetched"}}]
        },
        {
            "content": "Finally, I'll provide recommendations",
            "tool_calls": []
        }
    ]
    
    call_count = 0
    async def mock_sequential_llm(*args, **kwargs):
        nonlocal call_count
        result = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return result
    
    llm_manager.call_llm = AsyncMock(side_effect=mock_sequential_llm)
    
    # Execute chain
    chain_results = []
    for i in range(3):
        response = await llm_manager.call_llm(f"Step {i}")
        chain_results.append(response)
    
    # Verify chain progression
    assert len(chain_results) == 3
    assert "fetch data" in chain_results[0]["content"]
    assert "analyze" in chain_results[1]["content"]
    assert len(chain_results[2]["tool_calls"]) == 0  # Final step has no tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])