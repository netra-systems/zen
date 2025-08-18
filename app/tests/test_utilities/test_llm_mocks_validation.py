"""
Validation tests for LLM mock utilities to ensure proper functionality.
Quick smoke tests to verify the module works as expected.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock
from app.tests.test_utilities.llm_mocks import (
    create_mock_llm_manager,
    with_basic_responses,
    with_structured_responses,
    with_agent_responses,
    with_error_responses,
    with_tool_calls,
    with_performance_mocks,
    create_streaming_mock,
    create_metrics_mock,
    LLMResponseBuilder
)


def test_create_mock_llm_manager():
    """Test basic LLM manager creation."""
    manager = create_mock_llm_manager()
    assert hasattr(manager, 'call_llm')
    assert hasattr(manager, 'ask_llm')
    assert hasattr(manager, 'ask_structured_llm')


@pytest.mark.asyncio
async def test_basic_responses():
    """Test basic response configuration."""
    manager = create_mock_llm_manager()
    manager = with_basic_responses(manager, content="Test content", tool_calls=[])
    
    result = await manager.call_llm("test prompt")
    assert result["content"] == "Test content"
    assert result["tool_calls"] == []


@pytest.mark.asyncio
async def test_structured_responses():
    """Test structured response configuration."""
    manager = create_mock_llm_manager()
    manager = with_structured_responses(manager, data={"category": "test", "result": "mock"})
    
    result = await manager.ask_structured_llm("test prompt", "test_config", None)
    assert hasattr(result, 'category')
    assert result.category == "test"


@pytest.mark.asyncio
async def test_agent_responses():
    """Test agent-specific response configuration."""
    manager = create_mock_llm_manager()
    manager = with_agent_responses(manager, agent_type="supervisor")
    
    result = await manager.ask_llm("test prompt")
    data = json.loads(result)
    assert "routing_decision" in data


@pytest.mark.asyncio
async def test_error_responses():
    """Test error response configuration."""
    manager = create_mock_llm_manager()
    manager = with_error_responses(manager, error_type="timeout")
    
    with pytest.raises(asyncio.TimeoutError):
        await manager.call_llm("test prompt")


@pytest.mark.asyncio
async def test_tool_calls():
    """Test tool call response configuration."""
    manager = create_mock_llm_manager()
    tools = [{"name": "test_tool", "args": {"param": "value"}}]
    manager = with_tool_calls(manager, tools=tools)
    
    result = await manager.call_llm("test prompt")
    assert result["tool_calls"] == tools


def test_metrics_mock():
    """Test metrics mock creation."""
    metrics = create_metrics_mock(success_rate=0.9, avg_latency=150)
    assert metrics["success_rate"] == 0.9
    assert metrics["average_latency_ms"] == 150
    assert "timestamp" in metrics


def test_llm_response_builder():
    """Test LLM response builder creation."""
    builder = LLMResponseBuilder()
    assert hasattr(builder, 'llm_manager')
    assert hasattr(builder.llm_manager, 'call_llm')


@pytest.mark.asyncio
async def test_streaming_mock():
    """Test streaming mock configuration."""
    manager = create_mock_llm_manager()
    chunks = ["Hello", " World"]
    manager = create_streaming_mock(manager, chunks=chunks)
    
    # Collect streaming results
    results = []
    async for chunk in manager.astream("test prompt"):
        results.append(chunk.content)
    
    assert "Hello" in results
    assert " World" in results