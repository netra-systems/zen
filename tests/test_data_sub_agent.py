"""Comprehensive test suite for DataSubAgent with full coverage."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, UTC
import json

from app.agents.data_sub_agent.agent import DataSubAgent
from app.agents.state import DeepAgentState
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher


@pytest.fixture
def mock_llm_manager():
    """Mock LLM manager for testing."""
    mock = MagicMock(spec=LLMManager)
    mock.ask_structured_llm = AsyncMock()
    mock.ask_llm = AsyncMock()
    return mock


@pytest.fixture
def mock_tool_dispatcher():
    """Mock tool dispatcher for testing."""
    return MagicMock(spec=ToolDispatcher)


@pytest.fixture
def mock_redis_manager():
    """Mock Redis manager for testing."""
    mock = MagicMock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.exists = AsyncMock(return_value=False)
    return mock


@pytest.fixture
def mock_clickhouse_ops():
    """Mock ClickHouse operations."""
    mock = MagicMock()
    mock.get_table_schema = AsyncMock()
    mock.fetch_data = AsyncMock()
    return mock


@pytest.fixture
def mock_query_builder():
    """Mock query builder."""
    mock = MagicMock()
    mock.build_performance_metrics_query = MagicMock(return_value="SELECT * FROM test")
    mock.build_anomaly_detection_query = MagicMock(return_value="SELECT * FROM anomalies")
    return mock


@pytest.fixture
def mock_analysis_engine():
    """Mock analysis engine."""
    mock = MagicMock()
    mock.calculate_statistics = MagicMock()
    mock.detect_trend = MagicMock()
    mock.detect_anomalies = MagicMock()
    return mock


@pytest.fixture
def data_agent(mock_llm_manager, mock_tool_dispatcher):
    """Create DataSubAgent instance for testing."""
    with patch('app.agents.data_sub_agent.agent.RedisManager') as mock_redis_cls:
        mock_redis_cls.return_value = MagicMock()
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
        agent.ws_manager = MagicMock()
        agent.ws_manager.send_agent_update = AsyncMock()
        return agent


@pytest.fixture
def sample_state():
    """Sample agent state for testing."""
    # Create mock state to avoid Pydantic forward ref issues
    mock_state = MagicMock()
    mock_state.user_request = "Analyze performance metrics for workload optimization"
    mock_state.metadata = {}
    mock_state.step_count = 1
    return mock_state


@pytest.fixture
def sample_performance_data():
    """Sample performance data from ClickHouse."""
    return [
        {
            "time_bucket": "2024-01-01 12:00:00",
            "event_count": 100,
            "latency_p50": 50.0,
            "latency_p95": 95.0,
            "avg_throughput": 1000.0,
            "error_rate": 2.5,
            "total_cost": 15.75
        },
        {
            "time_bucket": "2024-01-01 12:01:00", 
            "event_count": 120,
            "latency_p50": 55.0,
            "latency_p95": 100.0,
            "avg_throughput": 1200.0,
            "error_rate": 1.8,
            "total_cost": 18.90
        }
    ]


class TestDataSubAgentInitialization:
    """Test DataSubAgent initialization and dependency setup."""
    
    def test_agent_initialization_success(self, mock_llm_manager, mock_tool_dispatcher):
        """Test successful agent initialization."""
        with patch('app.agents.data_sub_agent.agent.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            assert agent.name == "DataSubAgent"
            assert agent.llm_manager == mock_llm_manager
            assert agent.tool_dispatcher == mock_tool_dispatcher
            assert agent.query_builder is not None
            assert agent.analysis_engine is not None
            assert agent.clickhouse_ops is not None

    def test_redis_initialization_failure(self, mock_llm_manager, mock_tool_dispatcher):
        """Test handling of Redis initialization failure."""
        with patch('app.agents.data_sub_agent.agent.RedisManager', side_effect=Exception("Redis error")):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            assert agent.redis_manager is None

    def test_reliability_wrapper_initialization(self, mock_llm_manager, mock_tool_dispatcher):
        """Test reliability wrapper is properly initialized."""
        with patch('app.agents.data_sub_agent.agent.RedisManager'):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            assert agent.reliability is not None
            assert hasattr(agent.reliability, 'circuit_breaker')


class TestCachingOperations:
    """Test caching and schema operations."""
    
    async def test_get_cached_schema_miss(self, data_agent, mock_clickhouse_ops):
        """Test schema cache miss and population."""
        data_agent.clickhouse_ops = mock_clickhouse_ops
        schema = {"columns": [{"name": "id", "type": "Int64"}]}
        mock_clickhouse_ops.get_table_schema.return_value = schema
        
        result = await data_agent._get_cached_schema("test_table")
        assert result == schema
        assert hasattr(data_agent, '_schema_cache')

    async def test_get_cached_schema_hit(self, data_agent):
        """Test schema cache hit."""
        data_agent._schema_cache = {"test_table": {"cached": True}}
        
        result = await data_agent._get_cached_schema("test_table")
        assert result == {"cached": True}

    async def test_fetch_clickhouse_data_with_cache(self, data_agent, mock_clickhouse_ops):
        """Test ClickHouse data fetching with cache."""
        data_agent.clickhouse_ops = mock_clickhouse_ops
        data_agent.redis_manager = MagicMock()
        test_data = [{"id": 1, "value": "test"}]
        mock_clickhouse_ops.fetch_data.return_value = test_data
        
        result = await data_agent._fetch_clickhouse_data("SELECT 1", "test_key")
        assert result == test_data
        mock_clickhouse_ops.fetch_data.assert_called_once()


class TestDataOperations:
    """Test core data processing operations."""
    
    async def test_execute_with_valid_state(self, data_agent, sample_state):
        """Test execution with valid state."""
        with patch.object(data_agent, 'clickhouse_ops'), \
             patch('app.agents.data_sub_agent.agent.ExecutionEngine') as mock_engine_cls, \
             patch('app.agents.data_sub_agent.agent.DataOperations'), \
             patch('app.agents.data_sub_agent.agent.MetricsAnalyzer'):
            
            mock_engine = MagicMock()
            mock_engine.execute_analysis = AsyncMock()
            mock_engine_cls.return_value = mock_engine
            
            await data_agent.execute(sample_state, "test-run-id", True)
            mock_engine.execute_analysis.assert_called_once()

    async def test_execute_with_streaming_updates(self, data_agent, sample_state):
        """Test execution with streaming updates enabled."""
        with patch.object(data_agent, 'clickhouse_ops'), \
             patch('app.agents.data_sub_agent.agent.ExecutionEngine') as mock_engine_cls, \
             patch('app.agents.data_sub_agent.agent.DataOperations'), \
             patch('app.agents.data_sub_agent.agent.MetricsAnalyzer'):
            
            mock_engine = MagicMock()
            mock_engine.execute_analysis = AsyncMock()
            mock_engine_cls.return_value = mock_engine
            
            await data_agent.execute(sample_state, "test-run-id", True)
            call_args = mock_engine.execute_analysis.call_args[0]
            assert call_args[2] is True  # stream_updates parameter


class TestWebSocketUpdates:
    """Test WebSocket update functionality."""
    
    async def test_send_update_success(self, data_agent):
        """Test successful WebSocket update sending."""
        update = {"status": "processing", "progress": 50}
        
        await data_agent._send_update("test-run-id", update)
        data_agent.ws_manager.send_agent_update.assert_called_once_with(
            "test-run-id", "DataSubAgent", update
        )

    async def test_send_update_failure_handling(self, data_agent):
        """Test WebSocket update failure handling."""
        data_agent.ws_manager.send_agent_update.side_effect = Exception("WS error")
        update = {"status": "error"}
        
        # Should not raise exception
        await data_agent._send_update("test-run-id", update)

    async def test_send_update_no_ws_manager(self, data_agent):
        """Test update sending when WebSocket manager is not available."""
        delattr(data_agent, 'ws_manager')
        update = {"status": "test"}
        
        # Should not raise exception
        await data_agent._send_update("test-run-id", update)


class TestHealthAndCircuitBreaker:
    """Test health monitoring and circuit breaker functionality."""
    
    def test_get_health_status(self, data_agent):
        """Test health status retrieval."""
        mock_status = {"status": "healthy", "uptime": 3600}
        data_agent.reliability.get_health_status = MagicMock(return_value=mock_status)
        
        result = data_agent.get_health_status()
        assert result == mock_status

    def test_get_circuit_breaker_status(self, data_agent):
        """Test circuit breaker status retrieval."""
        mock_status = {"state": "closed", "failure_count": 0}
        data_agent.reliability.circuit_breaker.get_status = MagicMock(return_value=mock_status)
        
        result = data_agent.get_circuit_breaker_status()
        assert result == mock_status


class TestErrorHandling:
    """Test error handling scenarios."""
    
    async def test_schema_retrieval_error(self, data_agent):
        """Test schema retrieval error handling."""
        # Mock the clickhouse_ops to return None (as it does when handling errors)
        data_agent.clickhouse_ops.get_table_schema = AsyncMock(return_value=None)
        
        result = await data_agent._get_cached_schema("test_table")
        assert result is None

    async def test_execution_with_missing_dependencies(self, data_agent, sample_state):
        """Test execution with missing dependencies."""
        data_agent.clickhouse_ops = None
        
        with pytest.raises(Exception):
            await data_agent.execute(sample_state, "test-run-id")


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    async def test_empty_cache_key(self, data_agent, mock_clickhouse_ops):
        """Test data fetching with empty cache key."""
        data_agent.clickhouse_ops = mock_clickhouse_ops
        test_data = [{"result": "data"}]
        mock_clickhouse_ops.fetch_data.return_value = test_data
        
        result = await data_agent._fetch_clickhouse_data("SELECT 1", None)
        assert result == test_data

    async def test_schema_cache_with_none_result(self, data_agent, mock_clickhouse_ops):
        """Test schema caching when query returns None."""
        data_agent.clickhouse_ops = mock_clickhouse_ops
        mock_clickhouse_ops.get_table_schema.return_value = None
        
        result = await data_agent._get_cached_schema("nonexistent_table")
        assert result is None
        assert not hasattr(data_agent, '_schema_cache') or \
               "nonexistent_table" not in getattr(data_agent, '_schema_cache', {})

    def test_initialization_with_none_redis(self, mock_llm_manager, mock_tool_dispatcher):
        """Test initialization when Redis manager is None."""
        with patch('app.agents.data_sub_agent.agent.RedisManager', side_effect=Exception()):
            agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            assert agent.redis_manager is None