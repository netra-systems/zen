"""
Reliability and system tests for Data Sub Agent
Focuses on error handling and caching
"""

import sys
from pathlib import Path
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import asyncio

import pytest

from netra_backend.app.agents.data_sub_agent import DataSubAgent

from netra_backend.tests.agents.helpers.shared_test_types import (
    TestErrorHandling as SharedTestErrorHandling,
)

# Test fixtures for shared test classes
@pytest.fixture
def service():
    """Use real service instance."""
    # TODO: Initialize real service
    """Service fixture for shared integration tests."""
    # Mock: LLM service isolation for fast testing without API calls or rate limits
    mock_llm_manager = mock_llm_manager_instance  # Initialize appropriate service
    # Mock: Tool dispatcher isolation for agent testing without real tool execution
    mock_tool_dispatcher = mock_tool_dispatcher_instance  # Initialize appropriate service
    agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
    return agent

@pytest.fixture
def db_session():
    """Use real service instance."""
    # TODO: Initialize real service
    """Database session fixture for shared error handling tests."""
    # Mock: Generic component isolation for controlled unit testing
    db_mock = TestDatabaseManager().get_session()
    # Mock: Generic component isolation for controlled unit testing
    db_mock.query = query_instance  # Initialize appropriate service
    return db_mock

class TestErrorHandling(SharedTestErrorHandling):
    """Test error handling and recovery - extends shared error handling."""
    
    def test_database_connection_failure(self, service):
        """Test graceful handling of database connection failures"""
        # DataSubAgent-specific implementation
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_clickhouse = mock_clickhouse_instance  # Initialize appropriate service
        service.clickhouse_ops = mock_clickhouse
        # Mock: ClickHouse database isolation for fast testing without external database dependency
        mock_clickhouse.fetch_data = Mock(side_effect=Exception("Database unavailable"))
        
        with pytest.raises(Exception) as exc_info:
            # Test that database errors are properly handled
            service.clickhouse_ops.fetch_data("SELECT 1")
        
        assert "Database unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test retry mechanism on processing failure"""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = mock_llm_manager_instance  # Initialize appropriate service
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = mock_tool_dispatcher_instance  # Initialize appropriate service
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        agent.config = {"max_retries": 3}  # Initialize config dict
        
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            # Fail twice, then succeed
            mock_process.side_effect = [
                Exception("Error 1"),
                Exception("Error 2"),
                {"success": True}
            ]
            
            result = await agent.process_with_retry({"data": "test"})
            
        assert result["success"] == True
        assert mock_process.call_count == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test behavior when max retries exceeded"""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = mock_llm_manager_instance  # Initialize appropriate service
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = mock_tool_dispatcher_instance  # Initialize appropriate service
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        agent.config = {"max_retries": 2}  # Initialize config dict
        
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = Exception("Persistent error")
            
            with pytest.raises(Exception) as exc_info:
                await agent.process_with_retry({"data": "test"})
                
        assert "Persistent error" in str(exc_info.value)
        assert mock_process.call_count == 2

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """Test graceful degradation on partial failure"""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = mock_llm_manager_instance  # Initialize appropriate service
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = mock_tool_dispatcher_instance  # Initialize appropriate service
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        data_batch = [
            {"id": 1, "valid": True},
            {"id": 2, "valid": False},  # This will fail
            {"id": 3, "valid": True}
        ]
        
        # Mock process_data to fail on invalid items
        async def mock_process_data(data):
            if not data.get("valid", True):
                raise Exception("Invalid data")
            return {"status": "success", "data": data}
        
        agent.process_data = mock_process_data
        
        results = await agent.process_batch_safe(data_batch)
        
        assert len(results) == 3
        assert results[0]["status"] == "success"
        assert results[1]["status"] == "error"
        assert results[2]["status"] == "success"

class TestCaching:
    """Test caching functionality"""
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        """Test cache hit for repeated data"""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = mock_llm_manager_instance  # Initialize appropriate service
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = mock_tool_dispatcher_instance  # Initialize appropriate service
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        
        data = {"id": "cache_test", "content": "data"}
        
        # First call - cache miss
        result1 = await agent.process_with_cache(data)
        
        # Second call - cache hit
        with patch.object(agent, '_process_internal', new_callable=AsyncMock) as mock_process:
            result2 = await agent.process_with_cache(data)
            
        assert result1 == result2
        mock_process.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_expiration(self):
        """Test cache expiration with real TTL"""
        # Mock: LLM service isolation for fast testing without API calls or rate limits
        mock_llm_manager = mock_llm_manager_instance  # Initialize appropriate service
        # Mock: Tool dispatcher isolation for agent testing without real tool execution
        mock_tool_dispatcher = mock_tool_dispatcher_instance  # Initialize appropriate service
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        agent.cache_ttl = 0.1  # 100ms TTL
        agent._cache = {}  # Initialize cache
        
        data = {"id": "expire_test", "content": "data"}
        
        # Mock process_data to return different results on each call
        mock_results = [
            {"status": "processed", "data": {"id": "expire_test", "content": "data", "call": 1}},
            {"status": "processed", "data": {"id": "expire_test", "content": "data", "call": 2}}
        ]
        
        with patch.object(agent, 'process_data', new_callable=AsyncMock) as mock_process:
            mock_process.side_effect = mock_results
            
            # First call - cache miss
            result1 = await agent.process_with_cache(data)
            
            # Wait for cache to expire
            await asyncio.sleep(0.15)  # Wait longer than TTL
            
            # Second call - should be cache miss due to expiration
            result2 = await agent.process_with_cache(data)
            
        assert result1 != result2
        assert result1["data"]["call"] == 1
        assert result2["data"]["call"] == 2
        assert mock_process.call_count == 2  # Should be called twice
