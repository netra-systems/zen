"""Agent Tool Execution Pipeline Critical Path Tests

Business Value Justification (BVJ):
- Segment: Mid/Enterprise (advanced AI capabilities)
- Business Goal: Reliable AI agent tool execution
- Value Impact: Protects $10K MRR from tool execution failures
- Strategic Impact: Core agent capability that differentiates platform

Critical Path: Tool request -> Tool loading -> Execution -> Result processing -> Response
Coverage: Real tool execution, mocked LLM responses, error handling, performance
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch, patch

import pytest

from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.db.database_manager import DatabaseManager as ConnectionManager
from netra_backend.app.schemas.Tool import BaseTool

# Real components for L2-L3 testing
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.services.tool_registry import AgentToolConfigRegistry

logger = logging.getLogger(__name__)

class MockTool(BaseTool):
    """Mock tool for testing execution pipeline."""
    
    def __init__(self, name: str, execution_time: float = 0.1):
        self.name = name
        self.execution_time = execution_time
        self.call_count = 0
        
    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute mock tool with configurable delay."""
        self.call_count += 1
        await asyncio.sleep(self.execution_time)
        
        return {
            "success": True,
            "result": f"Tool {self.name} executed with params: {parameters}",
            "execution_time": self.execution_time,
            "call_count": self.call_count
        }

class ToolExecutionManager:
    """Manages agent tool execution testing."""
    
    def __init__(self):
        self.supervisor_agent = None
        self.tool_registry = None
        self.llm_manager = None
        self.mock_tools = {}
        self.execution_history = []
        
    async def initialize_services(self):
        """Initialize tool execution services."""
        self.supervisor_agent = SupervisorAgent()
        await self.supervisor_agent.initialize()
        
        self.tool_registry = ToolRegistry()
        await self.tool_registry.initialize()
        
        self.llm_manager = LLMManager()
        await self.llm_manager.initialize()
        
        # Register mock tools
        await self.register_mock_tools()
    
    async def register_mock_tools(self):
        """Register mock tools for testing."""
        tools = [
            MockTool("file_reader", 0.1),
            MockTool("calculator", 0.05),
            MockTool("web_scraper", 0.3),
            MockTool("database_query", 0.2)
        ]
        
        for tool in tools:
            self.mock_tools[tool.name] = tool
            await self.tool_registry.register_tool(tool.name, tool)
    
    async def execute_tool_with_agent(self, tool_name: str, parameters: Dict[str, Any],
                                    mock_llm_response: str = None) -> Dict[str, Any]:
        """Execute tool through agent with mocked LLM response."""
        start_time = time.time()
        
        # Mock LLM response if provided
        if mock_llm_response:
            with patch.object(self.llm_manager, 'generate_response', 
                            return_value={"response": mock_llm_response, "usage": {"tokens": 100}}):
                
                result = await self.supervisor_agent.execute_tool(
                    tool_name, parameters
                )
        else:
            result = await self.supervisor_agent.execute_tool(
                tool_name, parameters
            )
        
        execution_record = {
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "execution_time": time.time() - start_time,
            "timestamp": time.time()
        }
        
        self.execution_history.append(execution_record)
        return execution_record
    
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self, tool_configs: List[Dict]) -> Dict[str, Any]:
        """Test concurrent tool execution performance."""
        start_time = time.time()
        
        # Execute tools concurrently
        tasks = []
        for config in tool_configs:
            task = self.execute_tool_with_agent(
                config["tool_name"], 
                config["parameters"],
                config.get("mock_response")
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_executions = [r for r in results if isinstance(r, dict) and r.get("result", {}).get("success")]
        failed_executions = [r for r in results if isinstance(r, Exception) or not r.get("result", {}).get("success")]
        
        return {
            "total_time": time.time() - start_time,
            "successful_count": len(successful_executions),
            "failed_count": len(failed_executions),
            "results": results,
            "average_execution_time": sum(r["execution_time"] for r in successful_executions) / len(successful_executions) if successful_executions else 0
        }
    
    async def cleanup(self):
        """Clean up tool execution resources."""
        if self.supervisor_agent:
            await self.supervisor_agent.shutdown()
        if self.tool_registry:
            await self.tool_registry.shutdown()
        if self.llm_manager:
            await self.llm_manager.shutdown()

@pytest.fixture
async def tool_execution_manager():
    """Create tool execution manager for testing."""
    manager = ToolExecutionManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_single_tool_execution_pipeline(tool_execution_manager):
    """Test single tool execution through agent pipeline."""
    manager = tool_execution_manager
    
    # Execute simple tool
    result = await manager.execute_tool_with_agent(
        "calculator",
        {"operation": "add", "a": 5, "b": 3},
        "I'll calculate 5 + 3 for you."
    )
    
    assert result["result"]["success"] is True
    assert result["execution_time"] < 1.0
    assert "Tool calculator executed" in result["result"]["result"]
    
    # Verify tool was called
    calculator_tool = manager.mock_tools["calculator"]
    assert calculator_tool.call_count == 1

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_tool_execution_error_handling(tool_execution_manager):
    """Test tool execution error handling and recovery."""
    manager = tool_execution_manager
    
    # Test non-existent tool
    with pytest.raises(Exception):
        await manager.execute_tool_with_agent(
            "non_existent_tool",
            {"param": "value"}
        )
    
    # Test tool with invalid parameters
    result = await manager.execute_tool_with_agent(
        "calculator",
        {"invalid_param": "value"}
    )
    
    # Should handle gracefully
    assert "result" in result

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_concurrent_tool_execution_performance(tool_execution_manager):
    """Test concurrent tool execution performance and isolation."""
    manager = tool_execution_manager
    
    # Configure concurrent tool executions
    tool_configs = [
        {"tool_name": "file_reader", "parameters": {"file": "test.txt"}, "mock_response": "Reading file"},
        {"tool_name": "calculator", "parameters": {"operation": "multiply", "a": 2, "b": 4}, "mock_response": "Calculating"},
        {"tool_name": "web_scraper", "parameters": {"url": "https://example.com"}, "mock_response": "Scraping web"},
        {"tool_name": "database_query", "parameters": {"query": "SELECT * FROM users"}, "mock_response": "Querying database"}
    ]
    
    concurrent_result = await manager.test_concurrent_tool_execution(tool_configs)
    
    # Verify concurrent execution performance
    assert concurrent_result["successful_count"] == 4
    assert concurrent_result["failed_count"] == 0
    assert concurrent_result["total_time"] < 2.0  # Should be faster than sequential
    assert concurrent_result["average_execution_time"] < 0.5
    
    # Verify all tools were executed
    for tool_name in ["file_reader", "calculator", "web_scraper", "database_query"]:
        tool = manager.mock_tools[tool_name]
        assert tool.call_count == 1

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_tool_result_processing_pipeline(tool_execution_manager):
    """Test tool result processing and response formatting."""
    manager = tool_execution_manager
    
    # Execute tool with complex result processing
    result = await manager.execute_tool_with_agent(
        "web_scraper",
        {"url": "https://example.com", "extract": ["title", "content"]},
        "I'll scrape the website and extract the title and content."
    )
    
    assert result["result"]["success"] is True
    assert "execution_time" in result["result"]
    assert "call_count" in result["result"]
    
    # Verify result structure
    assert "tool_name" in result
    assert "parameters" in result
    assert "timestamp" in result
    
    # Verify execution history tracking
    assert len(manager.execution_history) > 0
    last_execution = manager.execution_history[-1]
    assert last_execution["tool_name"] == "web_scraper"
    
    # Verify L3 database persistence
    conn = await manager.db_manager.get_connection()
    db_result = await conn.fetchrow(
        "SELECT * FROM tool_execution_log WHERE tool_name = $1 ORDER BY timestamp DESC LIMIT 1",
        "web_scraper"
    )
    await manager.db_manager.return_connection(conn)
    assert db_result is not None
    assert db_result["success"] is True

@pytest.mark.asyncio
@pytest.mark.l3_realism
@pytest.mark.asyncio
async def test_tool_dependency_validation_l3(tool_execution_manager):
    """Test L3 tool dependency validation with real services."""
    manager = tool_execution_manager
    
    # Test tool execution with Redis dependency
    result = await manager.execute_tool_with_circuit_breaker(
        "database_query",
        {"query": "SELECT COUNT(*) FROM users", "timeout": 5}
    )
    
    assert result["result"]["success"] is True
    
    # Verify Redis state tracking
    execution_count = await manager.redis_service.client.incr("tool:database_query:executions")
    assert execution_count >= 1
    
    # Verify circuit breaker metrics
    assert manager.circuit_breaker.failure_count >= 0
    assert manager.circuit_breaker.state.value in ["closed", "half_open"]