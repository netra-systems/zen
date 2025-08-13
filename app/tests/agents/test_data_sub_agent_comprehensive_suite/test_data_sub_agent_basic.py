"""
Basic tests for DataSubAgent class - initialization, caching, and data fetching
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from app.agents.data_sub_agent import DataSubAgent


class TestDataSubAgentBasic:
    """Test basic DataSubAgent methods"""
    
    def test_initialization(self, mock_dependencies):
        """Test DataSubAgent initialization"""
        mock_llm_manager, mock_tool_dispatcher = mock_dependencies
        
        with patch('app.agents.data_sub_agent.RedisManager') as mock_redis:
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
        
        with patch('app.agents.data_sub_agent.RedisManager') as mock_redis:
            mock_redis.side_effect = Exception("Redis connection failed")
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            
        assert agent.redis_manager == None
        
    @pytest.mark.asyncio
    async def test_get_cached_schema_success(self, agent):
        """Test getting cached schema information"""
        with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.execute_query = AsyncMock(return_value=[
                ("column1", "String"),
                ("column2", "Int32")
            ])
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            # Clear the cache first
            agent._get_cached_schema.cache_clear()
            
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
            agent._get_cached_schema.cache_clear()
            
            result = await agent._get_cached_schema("test_table")
            
        assert result == None
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_with_cache_hit(self, agent):
        """Test fetching ClickHouse data with cache hit"""
        agent.redis_manager = Mock()
        agent.redis_manager.get = AsyncMock(return_value='[{"col1": "value1"}]')
        
        result = await agent._fetch_clickhouse_data("SELECT * FROM test", "cache_key")
        
        assert result == [{"col1": "value1"}]
        agent.redis_manager.get.assert_called_once_with("cache_key")
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_cache_miss(self, agent):
        """Test fetching ClickHouse data with cache miss"""
        agent.redis_manager = Mock()
        agent.redis_manager.get = AsyncMock(return_value=None)
        agent.redis_manager.set = AsyncMock()
        
        with patch('app.agents.data_sub_agent.create_workload_events_table_if_missing', new_callable=AsyncMock):
            with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
                mock_result = Mock()
                mock_result._fields = ["col1", "col2"]
                
                mock_client_instance = AsyncMock()
                mock_client_instance.execute_query = AsyncMock(return_value=[
                    ("value1", "value2"),
                    ("value3", "value4")
                ])
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                result = await agent._fetch_clickhouse_data("SELECT * FROM test", "cache_key")
                
        assert len(result) == 2
        assert result[0] == {0: "value1", 1: "value2"}
        agent.redis_manager.set.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_no_cache(self, agent):
        """Test fetching ClickHouse data without caching"""
        agent.redis_manager = None
        
        with patch('app.agents.data_sub_agent.create_workload_events_table_if_missing', new_callable=AsyncMock):
            with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.execute_query = AsyncMock(return_value=[])
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                result = await agent._fetch_clickhouse_data("SELECT * FROM test")
                
        assert result == []
        
    @pytest.mark.asyncio
    async def test_fetch_clickhouse_data_error(self, agent):
        """Test fetching ClickHouse data with error"""
        with patch('app.agents.data_sub_agent.create_workload_events_table_if_missing', new_callable=AsyncMock):
            with patch('app.agents.data_sub_agent.get_clickhouse_client') as mock_client:
                mock_client_instance = AsyncMock()
                mock_client_instance.execute_query = AsyncMock(side_effect=Exception("Query failed"))
                mock_client.return_value.__aenter__.return_value = mock_client_instance
                
                result = await agent._fetch_clickhouse_data("SELECT * FROM test")
                
        assert result == None
        
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