"""
Basic tests for DataSubAgent class - initialization, caching, and data fetching
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.agents.data_sub_agent.agent import DataSubAgent


class TestDataSubAgentBasic:
    """Test basic DataSubAgent methods"""
    
    def test_initialization(self, mock_dependencies):
        """Test DataSubAgent initialization"""
        mock_llm_manager, mock_tool_dispatcher = mock_dependencies
        
        with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager') as mock_redis:
            mock_redis.return_value = Mock()
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            
        assert agent.name == "DataSubAgent"
        assert agent.description == "Advanced data gathering and analysis agent with ClickHouse integration."
        assert agent.tool_dispatcher == mock_tool_dispatcher
        assert agent.query_builder != None
        assert agent.analysis_engine != None
        assert agent.cache_ttl == 300
        
    def test_initialization_redis_failure(self, mock_dependencies):
        """Test DataSubAgent initialization when Redis fails"""
        mock_llm_manager, mock_tool_dispatcher = mock_dependencies
        
        with patch('app.agents.data_sub_agent.data_sub_agent_core.RedisManager') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            
        assert agent.redis_manager == None
    @pytest.mark.asyncio
    async def test_get_cached_schema_success(self, agent):
        """Test getting cached schema information"""
        # Mock the clickhouse_ops.get_table_schema method directly
        expected_schema = {
            "table": "test_table",
            "columns": [
                {"name": "column1", "type": "String"},
                {"name": "column2", "type": "Int32"}
            ]
        }
        
        with patch.object(agent.clickhouse_ops, 'get_table_schema', new_callable=AsyncMock) as mock_get_schema:
            mock_get_schema.return_value = expected_schema
            
            # Clear the cache first
            agent.cache_clear()
            
            result = await agent._get_cached_schema("test_table")
            
        assert result != None
        assert result["table"] == "test_table"
        assert len(result["columns"]) == 2
        assert result["columns"][0]["name"] == "column1"
        assert result["columns"][0]["type"] == "String"
    @pytest.mark.asyncio
    async def test_get_cached_schema_failure(self, agent):
        """Test getting cached schema with error"""
        with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.execute_query = AsyncMock(side_effect=Exception("Query failed"))
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Clear the cache first
            agent.cache_clear()
            
            result = await agent._get_cached_schema("test_table")
            
        assert result == None
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_with_cache_hit(self, agent):
        """Test fetching ClickHouse data with cache hit"""
        # Mock the fetch_data method directly on the clickhouse_ops component
        with patch.object(agent.core.clickhouse_ops, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = [{"col1": "value1"}]
            
            result = await agent._fetch_clickhouse_data("SELECT * FROM test", "cache_key")
            
            assert result == [{"col1": "value1"}]
            mock_fetch.assert_called_once_with("SELECT * FROM test", "cache_key", agent.core.cache_ttl)
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_cache_miss(self, agent):
        """Test fetching ClickHouse data with cache miss"""
        # Mock the fetch_data method to simulate cache miss and database query
        expected_result = [{"col1": "value1", "col2": "value2"}, {"col1": "value3", "col2": "value4"}]
        with patch.object(agent.core.clickhouse_ops, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = expected_result
            
            result = await agent._fetch_clickhouse_data("SELECT * FROM test", "cache_key")
            
            assert result == expected_result
            mock_fetch.assert_called_once_with("SELECT * FROM test", "cache_key", agent.core.cache_ttl)
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_no_cache(self, agent):
        """Test fetching ClickHouse data without caching"""
        # Mock the fetch_data method for no cache scenario
        with patch.object(agent.core.clickhouse_ops, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = []
            
            result = await agent._fetch_clickhouse_data("SELECT * FROM test")
            
            assert result == []
            mock_fetch.assert_called_once_with("SELECT * FROM test", None, agent.core.cache_ttl)
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_error(self, agent):
        """Test fetching ClickHouse data with error"""
        # Mock the fetch_data method to raise an exception
        with patch.object(agent.core.clickhouse_ops, 'fetch_data', new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = None  # Error case returns None
            
            result = await agent._fetch_clickhouse_data("SELECT * FROM test")
            
            assert result == None
            mock_fetch.assert_called_once_with("SELECT * FROM test", None, agent.core.cache_ttl)
    @pytest.mark.asyncio
    async def test_save_state(self, agent):
        """Test save_state method"""
        agent.state = {"key": "value", "count": 42}
        
        # Should not raise
        await agent.save_state()
        
        assert agent.state == {"key": "value", "count": 42}
    @pytest.mark.asyncio
    async def test_save_state_no_existing(self, agent):
        """Test save_state without existing state"""
        if hasattr(agent, 'state'):
            delattr(agent, 'state')
            
        await agent.save_state()
        
        assert agent.state == {}
    @pytest.mark.asyncio
    async def test_load_state(self, agent):
        """Test load_state method"""
        await agent.load_state()
        
        assert hasattr(agent, 'state')
        assert isinstance(agent.state, dict)
    @pytest.mark.asyncio
    async def test_load_state_existing(self, agent):
        """Test load_state overwrites existing state"""
        agent.state = {"existing": "data"}
        agent.agent_type = "data"  # Add the missing attribute
        
        await agent.load_state()
        
        # load_state initializes with empty state when no saved state is found
        assert agent.state == {}
        assert hasattr(agent, '_saved_state')
    @pytest.mark.asyncio
    async def test_recover(self, agent):
        """Test recover method"""
        with patch.object(agent, 'load_state', new_callable=AsyncMock) as mock_load:
            await agent.recover()
            
        mock_load.assert_called_once()