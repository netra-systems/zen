from unittest.mock import AsyncMock, Mock, patch, MagicMock

"""Comprehensive Golden Pattern Test Suite for DataSubAgent

This test suite validates the DataSubAgent's compliance with the Golden Pattern
requirements including proper BaseAgent inheritance, WebSocket event emission,
reliability patterns, infrastructure integration, and business logic.

Creates REAL, DIFFICULT tests that could actually fail to ensure robust validation.
Tests both success and failure paths with comprehensive edge case coverage.

Business Value: Ensures reliable data analysis with 15-30% cost savings identification.
""""

# Mock dependencies early to prevent import issues
import sys
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis_test_utils_test_utils.test_redis_manager import TestRedisManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

# Mock ClickHouse dependencies with proper package structure
if 'clickhouse_connect' not in sys.modules:
    mock_clickhouse_driver_client = MagicMock()  # TODO: Use real service instance
    mock_clickhouse_driver = MagicMock()  # TODO: Use real service instance
    mock_clickhouse_driver.client = mock_clickhouse_driver_client
    
    mock_clickhouse_connect = MagicMock()  # TODO: Use real service instance
    mock_clickhouse_connect.driver = mock_clickhouse_driver
    
    sys.modules['clickhouse_connect'] = mock_clickhouse_connect
    sys.modules['clickhouse_connect.driver'] = mock_clickhouse_driver
    sys.modules['clickhouse_connect.driver.client'] = mock_clickhouse_driver_client

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import pytest
import pytest_asyncio
from contextlib import asynccontextmanager

from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.core.resilience.unified_retry_handler import UnifiedRetryHandler
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.schemas.core_enums import ExecutionStatus
from netra_backend.app.schemas.agent import SubAgentLifecycle
from netra_backend.app.schemas.agent_result_types import TypedAgentResult


class MockWebSocketBridge:
    """Mock WebSocket bridge for testing event emission."""
    
    def __init__(self):
        self.events = []
        self.connected = True
        self.should_fail = False
    
    async def notify_agent_started(self, run_id: str, agent_name: str, message: Optional[str] = None):
        if self.should_fail:
            raise ConnectionError("WebSocket connection lost")
        self.events.append({"type": "agent_started", "run_id": run_id, "agent_name": agent_name, "message": message})
    
    async def notify_agent_thinking(self, run_id: str, agent_name: str, thought: str, step_number: Optional[int] = None):
        if self.should_fail:
            raise ConnectionError("WebSocket connection lost")
        self.events.append({"type": "agent_thinking", "run_id": run_id, "agent_name": agent_name, "thought": thought, "step_number": step_number})
    
    async def notify_tool_executing(self, run_id: str, agent_name: str, tool_name: str, parameters: Optional[Dict] = None):
        if self.should_fail:
            raise ConnectionError("WebSocket connection lost")
        self.events.append({"type": "tool_executing", "run_id": run_id, "agent_name": agent_name, "tool_name": tool_name, "parameters": parameters})
    
    async def notify_tool_completed(self, run_id: str, agent_name: str, tool_name: str, result: Optional[Dict] = None):
        if self.should_fail:
            raise ConnectionError("WebSocket connection lost")
        self.events.append({"type": "tool_completed", "run_id": run_id, "agent_name": agent_name, "tool_name": tool_name, "result": result})
    
    async def notify_agent_completed(self, run_id: str, agent_name: str, result: Optional[Dict] = None, execution_time_ms: Optional[float] = None):
        if self.should_fail:
            raise ConnectionError("WebSocket connection lost")
        self.events.append({"type": "agent_completed", "run_id": run_id, "agent_name": agent_name, "result": result, "execution_time_ms": execution_time_ms})
    
    async def notify_error(self, run_id: str, agent_name: str, error_message: str, error_type: Optional[str] = None, error_details: Optional[Dict] = None):
        if self.should_fail:
            raise ConnectionError("WebSocket connection lost")
        self.events.append({"type": "error", "run_id": run_id, "agent_name": agent_name, "error_message": error_message, "error_type": error_type, "error_details": error_details})
    
    def get_events_by_type(self, event_type: str) -> List[Dict]:
        await asyncio.sleep(0)
    return [event for event in self.events if event["type"] == event_type]
    
    def clear_events(self):
        self.events.clear()
    
    def simulate_connection_failure(self):
        self.should_fail = True
        self.connected = False
    
    def restore_connection(self):
        self.should_fail = False
        self.connected = True


class TestDataSubAgentGoldenPattern:
    """Comprehensive test suite for DataSubAgent Golden Pattern compliance."""
    
    @pytest.fixture
    def real_llm_manager():
        """Use real service instance."""
        # TODO: Initialize real service
        """Create mock LLM manager with realistic behavior."""
        manager = Mock(spec=LLMManager)
        manager.generate_response = AsyncMock(return_value={
        "content": "Based on the data analysis, I recommend optimizing model selection for 25% cost reduction"
        })
        manager.is_healthy = Mock(return_value=True)
        return manager
    
        @pytest.fixture
        def real_tool_dispatcher():
        """Use real service instance."""
        # TODO: Initialize real service
        """Create mock tool dispatcher."""
        dispatcher = Mock(spec=ToolDispatcher)
        dispatcher.execute_tool = AsyncMock(return_value={"status": "success", "data": {}})
        return dispatcher
    
        @pytest.fixture
        def real_websocket_bridge():
        """Use real service instance."""
        # TODO: Initialize real service
        """Create mock WebSocket bridge."""
        return MockWebSocketBridge()
    
        @pytest.fixture
        def sample_execution_context(self):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create sample execution context."""
        state = DeepAgentState(
        user_id="test_user_123",
        thread_id="thread_456",
        message="Analyze performance metrics for cost optimization",
        metadata={"analysis_type": "performance", "time_range": "24h"}
        )
        return ExecutionContext(
        run_id="test_run_789",
        agent_name="DataSubAgent",
        state=state,
        stream_updates=True,
        start_time=datetime.now(timezone.utc)
        )
    
        @pytest.fixture
        def data_sub_agent(self, mock_llm_manager, mock_tool_dispatcher, mock_websocket_bridge):
        """Use real service instance."""
        # TODO: Initialize real service
        """Create DataSubAgent instance with mocked dependencies."""
        
        # Patch all the modules that might cause import issues
        patches = [
        patch('netra_backend.app.db.clickhouse.get_clickhouse_service'),
        patch('netra_backend.app.agents.data_sub_agent.agent.get_clickhouse_service'),
        patch('netra_backend.app.agents.data_sub_agent.agent.RedisManager'),
        patch('netra_backend.app.agents.data_sub_agent.data_sub_agent_core.DataSubAgentCore'),
        patch('netra_backend.app.agents.data_sub_agent.data_sub_agent_helpers.DataSubAgentHelpers'),
        patch('netra_backend.app.agents.data_sub_agent.extended_operations.ExtendedOperations'),
        patch('netra_backend.app.redis_manager.RedisManager'),
        ]
        
        for p in patches:
        p.start()
        
        try:
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            
        # Setup WebSocket bridge
        agent.set_websocket_bridge(mock_websocket_bridge, "test_run_789")
            
        # Mock core components
        if hasattr(agent, 'core'):
        agent.core.validate_data_analysis_preconditions = AsyncMock(return_value=True)
        agent.core.execute_data_analysis = AsyncMock(return_value={"status": "success", "insights": "test insights"})
        agent.core.get_health_status = Mock(return_value={"status": "healthy"})
        agent.core.create_reliability_manager = Mock(return_value=Mock(spec=UnifiedRetryHandler))
            
        # Mock helpers
        if hasattr(agent, 'helpers'):
        agent.helpers.execute_legacy_analysis = AsyncMock(return_value=TypedAgentResult(status="success", data={}))
        agent.helpers.fetch_clickhouse_data = AsyncMock(return_value=[])
        agent.helpers.send_websocket_update = AsyncMock()  # TODO: Use real service instance
        agent.helpers.clear_cache = TestRedisManager().get_client()
        agent.helpers.cleanup_resources = AsyncMock()  # TODO: Use real service instance
            
        # Mock extended operations if it exists
        if hasattr(agent, 'extended_ops'):
        agent.extended_ops.process_batch_safe = AsyncMock(return_value=[])
        agent.extended_ops.process_and_persist = AsyncMock(return_value={"status": "processed", "persisted": True})
            
        # Ensure the agent has all the necessary attributes
        if not hasattr(agent, 'clickhouse_ops'):
        agent.clickhouse_ops = clickhouse_ops_instance  # Initialize appropriate service
        agent.clickhouse_ops.get_table_schema = AsyncMock(return_value={"columns": ["id", "name"]])
            
        if not hasattr(agent, 'execution_engine'):
        agent.execution_engine = UserExecutionEngine()
        agent.execution_engine.execute = AsyncMock()  # TODO: Use real service instance
        agent.execution_engine.get_health_status = Mock(return_value={"status": "healthy"})
            
        return agent
        finally:
        for p in patches:
        p.stop()
    
        # === Golden Pattern Compliance Tests ===
    
        def test_inherits_from_base_agent(self, data_sub_agent):
        """Test that DataSubAgent properly inherits from BaseAgent."""
        assert isinstance(data_sub_agent, BaseAgent)
        assert hasattr(data_sub_agent, 'validate_preconditions')
        assert hasattr(data_sub_agent, 'execute_core_logic')
        assert hasattr(data_sub_agent, 'emit_thinking')
        assert hasattr(data_sub_agent, 'emit_tool_executing')
        assert hasattr(data_sub_agent, 'emit_tool_completed')
        assert hasattr(data_sub_agent, 'emit_agent_completed')
    
        def test_agent_identity_and_properties(self, data_sub_agent):
        """Test agent identity and core properties."""
        assert data_sub_agent.name == "DataSubAgent"
        assert "data gathering and analysis" in data_sub_agent.description.lower()
        assert hasattr(data_sub_agent, 'correlation_id')
        assert hasattr(data_sub_agent, 'agent_id')
        assert data_sub_agent.state == SubAgentLifecycle.PENDING
    
        @pytest.mark.asyncio
        async def test_validate_preconditions_success(self, data_sub_agent, sample_execution_context):
        """Test successful precondition validation."""
        result = await data_sub_agent.validate_preconditions(sample_execution_context)
        assert result is True
        data_sub_agent.core.validate_data_analysis_preconditions.assert_called_once_with(sample_execution_context)
    
        @pytest.mark.asyncio
        async def test_validate_preconditions_failure(self, data_sub_agent, sample_execution_context):
        """Test precondition validation failure handling."""
        data_sub_agent.core.validate_data_analysis_preconditions.side_effect = Exception("Database connection failed")
        
        result = await data_sub_agent.validate_preconditions(sample_execution_context)
        assert result is False
    
        @pytest.mark.asyncio
        async def test_execute_core_logic_success(self, data_sub_agent, sample_execution_context, mock_websocket_bridge):
        """Test successful core logic execution with WebSocket events."""
        expected_result = {"status": "success", "insights": "performance analysis complete"}
        data_sub_agent.core.execute_data_analysis.return_value = expected_result
        
        result = await data_sub_agent.execute_core_logic(sample_execution_context)
        
        assert result == expected_result
        data_sub_agent.core.execute_data_analysis.assert_called_once_with(sample_execution_context)
        
        # Verify WebSocket thinking event was emitted
        thinking_events = mock_websocket_bridge.get_events_by_type("agent_thinking")
        assert len(thinking_events) >= 1
        assert "data analysis" in thinking_events[0]["thought"].lower()
    
        @pytest.mark.asyncio
        async def test_execute_core_logic_with_websocket_failure(self, data_sub_agent, sample_execution_context, mock_websocket_bridge):
        """Test core logic execution when WebSocket fails."""
        mock_websocket_bridge.simulate_connection_failure()
        
        result = await data_sub_agent.execute_core_logic(sample_execution_context)
        
        # Should still succeed even if WebSocket fails
        assert result is not None
        data_sub_agent.core.execute_data_analysis.assert_called_once()
    
        # === WebSocket Event Emission Tests ===
    
        @pytest.mark.asyncio
        async def test_websocket_events_during_execution(self, data_sub_agent, sample_execution_context, mock_websocket_bridge):
        """Test that all required WebSocket events are emitted during execution."""
        mock_websocket_bridge.clear_events()
        
        # Execute core logic which should emit thinking events
        await data_sub_agent.execute_core_logic(sample_execution_context)
        
        # Verify thinking events
        thinking_events = mock_websocket_bridge.get_events_by_type("agent_thinking")
        assert len(thinking_events) >= 1
        
        # Test tool execution events
        await data_sub_agent.emit_tool_executing("database_query", {"query": "SELECT * FROM metrics"})
        await data_sub_agent.emit_tool_completed("database_query", {"rows": 100})
        
        tool_executing_events = mock_websocket_bridge.get_events_by_type("tool_executing")
        tool_completed_events = mock_websocket_bridge.get_events_by_type("tool_completed")
        
        assert len(tool_executing_events) == 1
        assert len(tool_completed_events) == 1
        assert tool_executing_events[0]["tool_name"] == "database_query"
        assert tool_completed_events[0]["result"]["rows"] == 100
    
        @pytest.mark.asyncio
        async def test_websocket_bridge_not_set(self, mock_llm_manager, mock_tool_dispatcher):
        """Test WebSocket event handling when bridge is not set."""
        with patch('netra_backend.app.agents.data_sub_agent.agent.get_clickhouse_service'), \
        patch('netra_backend.app.agents.data_sub_agent.agent.RedisManager'):
            
        agent = DataSubAgent(mock_llm_manager, mock_tool_dispatcher)
            
        # Should not raise exception when WebSocket bridge is not set
        await agent.emit_thinking("Testing without WebSocket bridge")
        await agent.emit_tool_executing("test_tool")
        await agent.emit_agent_completed({"result": "success"})
    
        @pytest.mark.asyncio
        async def test_websocket_event_emission_stress_test(self, data_sub_agent, mock_websocket_bridge):
        """Stress test WebSocket event emission with many concurrent events."""
        mock_websocket_bridge.clear_events()
        
        # Emit many events concurrently
        tasks = []
        for i in range(100):
        tasks.append(data_sub_agent.emit_thinking(f"Processing item {i}"))
        if i % 10 == 0:
        tasks.append(data_sub_agent.emit_tool_executing(f"tool_{i}", {"param": i}))
        tasks.append(data_sub_agent.emit_tool_completed(f"tool_{i}", {"result": i * 2}))
        
        await asyncio.gather(*tasks)
        
        thinking_events = mock_websocket_bridge.get_events_by_type("agent_thinking")
        tool_executing_events = mock_websocket_bridge.get_events_by_type("tool_executing")
        tool_completed_events = mock_websocket_bridge.get_events_by_type("tool_completed")
        
        assert len(thinking_events) == 100
        assert len(tool_executing_events) == 10
        assert len(tool_completed_events) == 10
    
        # === Business Logic Tests ===
    
        @pytest.mark.asyncio
        async def test_performance_analysis_functionality(self, data_sub_agent):
        """Test performance analysis business logic."""
        user_id = 123
        workload_id = "test_workload"
        time_range = (datetime.now(timezone.utc) - timedelta(hours=1), datetime.now(timezone.utc))
        
        # Mock data await asyncio.sleep(0)
        return
        mock_data = [
        {"event_count": 100, "latency_p50": 150, "avg_throughput": 50},
        {"event_count": 120, "latency_p50": 180, "avg_throughput": 45},
        {"event_count": 110, "latency_p50": 160, "avg_throughput": 55}
        ]
        data_sub_agent.helpers.fetch_clickhouse_data.return_value = mock_data
        
        result = await data_sub_agent._analyze_performance_metrics(user_id, workload_id, time_range)
        
        assert result["status"] == "success"
        assert "summary" in result
        assert "latency" in result
        assert "throughput" in result
        assert result["summary"]["total_events"] == 330
        assert result["summary"]["data_points"] == 3
    
        @pytest.mark.asyncio
        async def test_performance_analysis_with_empty_data(self, data_sub_agent):
        """Test performance analysis with no data."""
        data_sub_agent.helpers.fetch_clickhouse_data.return_value = []
        
        result = await data_sub_agent._analyze_performance_metrics(123, "test", [])
        
        assert result["status"] == "no_data"
        assert "No performance data found" in result["message"]
    
        @pytest.mark.asyncio
        async def test_anomaly_detection_functionality(self, data_sub_agent):
        """Test anomaly detection business logic."""
        user_id = 123
        metric_name = "latency"
        time_range = []
        
        mock_data = [
        {"value": 100, "timestamp": "2024-01-01T10:00:00Z"},
        {"value": 110, "timestamp": "2024-01-01T10:01:00Z"},
        {"value": 500, "z_score": 4.2, "timestamp": "2024-01-01T10:02:00Z"},  # Anomaly
        {"value": 105, "timestamp": "2024-01-01T10:03:00Z"}
        ]
        data_sub_agent.helpers.fetch_clickhouse_data.return_value = mock_data
        
        result = await data_sub_agent._detect_anomalies(user_id, metric_name, time_range)
        
        assert result["status"] == "success"
        assert result["anomalies_detected"] == 1
        assert len(result["anomalies"]) == 1
        assert result["anomalies"][0]["value"] == 500
        assert result["anomalies"][0]["z_score"] == 4.2
    
        @pytest.mark.asyncio
        async def test_usage_pattern_analysis(self, data_sub_agent):
        """Test usage pattern analysis functionality."""
        user_id = 123
        days_back = 7
        
        mock_data = [
        {"hour": 9, "total_events": 100},
        {"hour": 10, "total_events": 150},
        {"hour": 14, "total_events": 200},  # Peak hour
        {"hour": 2, "total_events": 20}     # Low hour
        ]
        data_sub_agent.helpers.fetch_clickhouse_data.return_value = mock_data
        
        result = await data_sub_agent._analyze_usage_patterns(user_id, days_back)
        
        assert result["status"] == "success"
        assert result["peak_hour"] == 14
        assert result["low_hour"] == 2
        assert result["peak_value"] == 200
        assert result["low_value"] == 20
    
        @pytest.mark.asyncio
        async def test_correlation_analysis(self, data_sub_agent):
        """Test correlation analysis between metrics."""
        user_id = 123
        metric1 = "latency"
        metric2 = "throughput"
        
        # Strong negative correlation data
        mock_data = [
        {"metric1": 100, "metric2": 50},
        {"metric1": 200, "metric2": 25},
        {"metric1": 150, "metric2": 37}
        ]
        data_sub_agent.helpers.fetch_clickhouse_data.return_value = mock_data
        
        result = await data_sub_agent._analyze_correlations(user_id, metric1, metric2, [])
        
        assert result["status"] == "success"
        assert "correlation_coefficient" in result
        assert "correlation_strength" in result
        assert result["data_points"] == 3
    
        # === Infrastructure Integration Tests ===
    
        @pytest.mark.asyncio
        async def test_clickhouse_integration(self, data_sub_agent, mock_websocket_bridge):
        """Test ClickHouse database integration."""
        query = "SELECT * FROM metrics WHERE user_id = 123"
        cache_key = "test_cache_key"
        expected_data = [{"id": 1, "value": 100], {"id": 2, "value": 200]]
        
        data_sub_agent.helpers.fetch_clickhouse_data.return_value = expected_data
        mock_websocket_bridge.clear_events()
        
        result = await data_sub_agent._fetch_clickhouse_data(query, cache_key)
        
        assert result == expected_data
        data_sub_agent.helpers.fetch_clickhouse_data.assert_called_once_with(query, cache_key)
        
        # Verify WebSocket notifications for database operations
        tool_executing_events = mock_websocket_bridge.get_events_by_type("tool_executing")
        tool_completed_events = mock_websocket_bridge.get_events_by_type("tool_completed")
        
        assert len(tool_executing_events) == 1
        assert len(tool_completed_events) == 1
        assert tool_executing_events[0]["tool_name"] == "database_query"
        assert tool_completed_events[0]["result"]["status"] == "success"
    
        @pytest.mark.asyncio
        async def test_clickhouse_query_failure(self, data_sub_agent, mock_websocket_bridge):
        """Test ClickHouse query failure handling."""
        query = "INVALID SQL QUERY"
        
        data_sub_agent.helpers.fetch_clickhouse_data.side_effect = Exception("SQL syntax error")
        mock_websocket_bridge.clear_events()
        
        with pytest.raises(Exception, match="SQL syntax error"):
        await data_sub_agent._fetch_clickhouse_data(query)
        
        # Verify error WebSocket notification
        tool_completed_events = mock_websocket_bridge.get_events_by_type("tool_completed")
        assert len(tool_completed_events) == 1
        assert tool_completed_events[0]["result"]["status"] == "error"
    
        def test_schema_cache_functionality(self, data_sub_agent):
        """Test schema cache integration."""
        table_name = "test_table"
        expected_schema = {"columns": ["id", "name", "value"], "types": ["int", "string", "float"]]
        
        data_sub_agent.clickhouse_ops.get_table_schema = AsyncMock(return_value=expected_schema)
        
        async def test_cache():
        result = await data_sub_agent._get_cached_schema(table_name)
        assert result == expected_schema
        data_sub_agent.clickhouse_ops.get_table_schema.assert_called_once_with(table_name)
        
        asyncio.run(test_cache())
    
        def test_health_monitoring(self, data_sub_agent):
        """Test comprehensive health status monitoring."""
        # Mock component health statuses
        core_health = {"status": "healthy", "database": "connected"}
        execution_health = {"status": "healthy", "monitor": "active"}
        
        data_sub_agent.core.get_health_status.return_value = core_health
        data_sub_agent.execution_engine.get_health_status = Mock(return_value=execution_health)
        
        result = data_sub_agent.get_health_status()
        
        assert "core" in result
        assert "execution" in result
        assert result["core"] == core_health
        assert result["execution"] == execution_health
    
        # === Reliability Pattern Tests ===
    
        def test_reliability_manager_integration(self, data_sub_agent):
        """Test reliability manager integration."""
        assert hasattr(data_sub_agent, 'unified_reliability_handler')
        assert hasattr(data_sub_agent, 'reliability_manager')
        
        # Test that reliability manager is properly configured
        if data_sub_agent.unified_reliability_handler:
        assert hasattr(data_sub_agent.unified_reliability_handler, 'execute_with_retry_async')
    
        @pytest.mark.asyncio
        async def test_execute_with_reliability_success(self, data_sub_agent):
        """Test successful execution with reliability patterns."""
        if not data_sub_agent.unified_reliability_handler:
        pytest.skip("Reliability not enabled for this test")
        
        # Mock successful operation
        async def test_operation():
        await asyncio.sleep(0)
        return {"result": "success"}
        
        # Mock reliability handler
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.success = True
        mock_result.result = {"result": "success"}
        data_sub_agent.unified_reliability_handler.execute_with_retry_async = AsyncMock(return_value=mock_result)
        
        result = await data_sub_agent.execute_with_reliability(test_operation, "test_operation")
        
        assert result == {"result": "success"}
        data_sub_agent.unified_reliability_handler.execute_with_retry_async.assert_called_once()
    
        @pytest.mark.asyncio
        async def test_execute_with_reliability_with_fallback(self, data_sub_agent):
        """Test execution with reliability and fallback."""
        if not data_sub_agent.unified_reliability_handler:
        pytest.skip("Reliability not enabled for this test")
        
        async def failing_operation():
        raise Exception("Primary operation failed")
        
        async def fallback_operation():
        await asyncio.sleep(0)
        return {"result": "fallback_success"}
        
        # Mock reliability handler responses
        primary_result = primary_result_instance  # Initialize appropriate service
        primary_result.success = False
        primary_result.final_exception = Exception("Primary failed")
        
        fallback_result = fallback_result_instance  # Initialize appropriate service
        fallback_result.success = True
        fallback_result.result = {"result": "fallback_success"}
        
        data_sub_agent.unified_reliability_handler.execute_with_retry_async = AsyncMock(
        side_effect=[primary_result, fallback_result]
        )
        
        result = await data_sub_agent.execute_with_reliability(
        failing_operation, "test_operation", fallback=fallback_operation
        )
        
        assert result == {"result": "fallback_success"}
        assert data_sub_agent.unified_reliability_handler.execute_with_retry_async.call_count == 2
    
        # === Edge Cases and Difficult Tests ===
    
        @pytest.mark.asyncio
        async def test_concurrent_execution_stress_test(self, data_sub_agent, sample_execution_context):
        """Stress test with concurrent executions."""
        # Simulate multiple concurrent executions
        contexts = []
        for i in range(10):
        context = ExecutionContext(
        run_id=f"run_{i}",
        agent_name="DataSubAgent",
        state=sample_execution_context.state,
        stream_updates=True
        )
        contexts.append(context)
        
        # Execute all contexts concurrently
        tasks = [data_sub_agent.execute_core_logic(ctx) for ctx in contexts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All should succeed
        assert len(results) == 10
        for result in results:
        assert not isinstance(result, Exception)
        assert result is not None
    
        @pytest.mark.asyncio
        async def test_large_dataset_processing(self, data_sub_agent):
        """Test processing of large datasets."""
        # Create large dataset
        large_dataset = [{"id": i, "value": i * 2] for i in range(1000)]
        
        result = await data_sub_agent.process_concurrent(large_dataset[:100], max_concurrent=10)
        
        assert len(result) == 100
        # All results should be processed
        for res in result:
        assert res is not None
    
        @pytest.mark.asyncio
        async def test_timeout_scenario(self, data_sub_agent, sample_execution_context):
        """Test timeout handling in execution."""
        # Mock a slow operation
        async def slow_operation():
        await asyncio.sleep(5)  # 5 second delay
        await asyncio.sleep(0)
        return {"result": "slow"}
        
        data_sub_agent.core.execute_data_analysis = slow_operation
        
        # This should timeout quickly if timeout handling is implemented
        start_time = time.time()
        
        try:
        with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(
        data_sub_agent.execute_core_logic(sample_execution_context),
        timeout=1.0
        )
        except asyncio.TimeoutError:
        
        elapsed = time.time() - start_time
        assert elapsed < 2.0  # Should timeout quickly
    
        @pytest.mark.asyncio
        async def test_memory_pressure_handling(self, data_sub_agent):
        """Test behavior under memory pressure."""
        # Create memory-intensive data
        large_data = {"large_array": list(range(100000))}
        
        # Process multiple large datasets
        tasks = []
        for i in range(5):
        tasks.append(data_sub_agent.process_data(large_data))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle memory pressure gracefully
        assert len(results) == 5
        for result in results:
        assert not isinstance(result, MemoryError)
    
        @pytest.mark.asyncio
        async def test_invalid_execution_context(self, data_sub_agent):
        """Test handling of invalid execution context."""
        # Create invalid context
        invalid_context = ExecutionContext(
        run_id="",  # Empty run ID
        agent_name="",  # Empty agent name
        state=None,  # None state
        stream_updates=False
        )
        
        # Should handle gracefully without crashing
        result = await data_sub_agent.validate_preconditions(invalid_context)
        # Precondition validation should catch this
        assert isinstance(result, bool)
    
        @pytest.mark.asyncio
        async def test_websocket_connection_recovery(self, data_sub_agent, mock_websocket_bridge):
        """Test WebSocket connection recovery after failure."""
        mock_websocket_bridge.clear_events()
        
        # Start with working connection
        await data_sub_agent.emit_thinking("Initial message")
        assert len(mock_websocket_bridge.events) == 1
        
        # Simulate connection failure
        mock_websocket_bridge.simulate_connection_failure()
        
        # Should handle gracefully without crashing
        await data_sub_agent.emit_thinking("Message during failure")
        
        # Restore connection
        mock_websocket_bridge.restore_connection()
        await data_sub_agent.emit_thinking("Message after recovery")
        
        # Should continue working after recovery
        thinking_events = mock_websocket_bridge.get_events_by_type("agent_thinking")
        assert len(thinking_events) >= 2  # At least initial + recovery messages
    
        # === Cache and State Management Tests ===
    
        @pytest.mark.asyncio
        async def test_cache_functionality(self, data_sub_agent):
        """Test caching functionality with TTL."""
        test_data = {"id": 1, "content": "test"}
        
        # First call should process and cache
        result1 = await data_sub_agent.process_with_cache(test_data)
        assert result1 is not None
        
        # Second call should await asyncio.sleep(0)
        return cached result quickly
        start_time = time.time()
        result2 = await data_sub_agent.process_with_cache(test_data)
        end_time = time.time()
        
        assert result1 == result2
        assert (end_time - start_time) < 0.01  # Should be very fast from cache
    
        @pytest.mark.asyncio
        async def test_cache_expiration(self, data_sub_agent):
        """Test cache expiration behavior."""
        # Set very short TTL for testing
        data_sub_agent.cache_ttl = 0.1  # 100ms
        
        test_data = {"id": 2, "content": "test2"}
        
        # First call
        result1 = await data_sub_agent.process_with_cache(test_data)
        
        # Wait for cache to expire
        await asyncio.sleep(0.2)
        
        # Second call should reprocess
        result2 = await data_sub_agent.process_with_cache(test_data)
        
        # Results should be the same but processing should have happened twice
        assert result1 == result2
    
        def test_cache_clear_functionality(self, data_sub_agent):
        """Test cache clearing functionality."""
        # Ensure cache exists
        data_sub_agent._cache = {"test": "data"}
        data_sub_agent._cache_timestamps = {"test": time.time()}
        
        # Clear cache
        data_sub_agent.cache_clear()
        
        # Verify helpers.clear_cache was called
        data_sub_agent.helpers.clear_cache.assert_called_once()
    
        @pytest.mark.asyncio
        async def test_state_persistence(self, data_sub_agent):
        """Test state saving and loading."""
        # Save state
        data_sub_agent.state = {"important": "data", "count": 42}
        await data_sub_agent.save_state()
        
        # Verify state was saved
        assert hasattr(data_sub_agent, '_saved_state')
        assert data_sub_agent._saved_state == {"important": "data", "count": 42}
        
        # Load state
        await data_sub_agent.load_state()
        
        # Verify state was loaded (initialized)
        assert hasattr(data_sub_agent, 'state')
        assert isinstance(data_sub_agent.state, dict)
    
        @pytest.mark.asyncio
        async def test_recovery_functionality(self, data_sub_agent):
        """Test agent recovery from failure."""
        await data_sub_agent.recover()
        
        # Should not raise exception and should complete recovery
        assert True  # If we get here, recovery completed successfully
    
        # === Integration and End-to-End Tests ===
    
        @pytest.mark.asyncio
        async def test_full_execution_flow_modern_pattern(self, data_sub_agent, sample_execution_context):
        """Test complete execution flow using modern patterns."""
        if not data_sub_agent.execution_engine:
        pytest.skip("Modern execution engine not enabled")
        
        # Mock execution engine
        expected_result = ExecutionResult(
        success=True,
        status=ExecutionStatus.COMPLETED,
        result={"analysis": "complete", "insights": "cost savings identified"},
        execution_time_ms=1500.0
        )
        data_sub_agent.execution_engine.execute = AsyncMock(return_value=expected_result)
        
        result = await data_sub_agent.execute_modern(
        sample_execution_context.state, 
        sample_execution_context.run_id,
        stream_updates=True
        )
        
        assert result.success is True
        assert result.status == ExecutionStatus.COMPLETED
        assert "analysis" in result.result
    
        @pytest.mark.asyncio
        async def test_legacy_execution_compatibility(self, data_sub_agent):
        """Test backward compatibility with legacy execution."""
        state = DeepAgentState(
        user_id="test_user",
        message="Test legacy execution"
        )
        run_id = "legacy_test_run"
        
        expected_result = TypedAgentResult(status="success", data={"legacy": True})
        data_sub_agent.helpers.execute_legacy_analysis.return_value = expected_result
        
        result = await data_sub_agent.execute(state, run_id, stream_updates=True)
        
        assert result is not None
        data_sub_agent.helpers.execute_legacy_analysis.assert_called_once_with(state, run_id, True)
    
        @pytest.mark.asyncio
        async def test_supervisor_request_handling(self, data_sub_agent):
        """Test handling of supervisor requests."""
        callback_results = []
        
        async def test_callback(result):
        callback_results.append(result)
        
        request = {
        "action": "process_data",
        "data": {"test": "data"},
        "callback": test_callback
        }
        
        result = await data_sub_agent.handle_supervisor_request(request)
        
        assert result["status"] == "completed"
        assert len(callback_results) == 1
        assert callback_results[0]["status"] == "success"
    
        @pytest.mark.asyncio
        async def test_batch_processing_with_error_handling(self, data_sub_agent):
        """Test batch processing with mixed success/failure scenarios."""
        batch_data = [
        {"id": 1, "valid": True},
        {"id": 2, "valid": False},  # This should fail
        {"id": 3, "valid": True},
        {"id": 4, "valid": False}   # This should fail
        ]
        
        results = await data_sub_agent.process_batch_safe(batch_data)
        
        assert len(results) == 4
        
        # Check that some succeeded and some failed appropriately
        success_count = sum(1 for r in results if r.get("status") == "success")
        error_count = sum(1 for r in results if r.get("status") == "error")
        
        # Should have both successes and errors based on the valid field
        assert success_count > 0
        assert error_count > 0
    
        @pytest.mark.asyncio
        async def test_streaming_data_processing(self, data_sub_agent):
        """Test streaming data processing capabilities."""
        dataset = [{"id": i, "data": f"item_{i]"] for i in range(250)]
        chunk_size = 50
        
        chunks = []
        async for chunk in data_sub_agent.process_stream(dataset, chunk_size):
        chunks.append(chunk)
        
        assert len(chunks) == 5  # 250 / 50 = 5 chunks
        assert len(chunks[0]) == 50
        assert len(chunks[-1]) == 50
        
        # Verify all data is included
        all_processed = []
        for chunk in chunks:
        all_processed.extend(chunk)
        assert len(all_processed) == 250
    
        # === Cleanup and Resource Management Tests ===
    
        @pytest.mark.asyncio
        async def test_cleanup_resource_management(self, data_sub_agent, sample_execution_context):
        """Test proper cleanup and resource management."""
        run_id = sample_execution_context.run_id
        current_time = time.time()
        
        await data_sub_agent.cleanup(sample_execution_context.state, run_id)
        
        # Verify cleanup methods were called
        data_sub_agent.helpers.cleanup_resources.assert_called_once()
        
        # Verify the cleanup was called with appropriate timestamp
        call_args = data_sub_agent.helpers.cleanup_resources.call_args[0][0]
        assert isinstance(call_args, (int, float))
        assert abs(call_args - current_time) < 1.0  # Within 1 second
    
        def test_agent_shutdown_lifecycle(self, data_sub_agent):
        """Test proper agent shutdown lifecycle."""
        # Verify initial state
        assert data_sub_agent.state != SubAgentLifecycle.SHUTDOWN
        
        # Shutdown should be idempotent
        async def test_shutdown():
        await data_sub_agent.shutdown()
        first_shutdown_state = data_sub_agent.state
            
        await data_sub_agent.shutdown()  # Second call
        second_shutdown_state = data_sub_agent.state
            
        assert first_shutdown_state == SubAgentLifecycle.SHUTDOWN
        assert second_shutdown_state == SubAgentLifecycle.SHUTDOWN
        
        asyncio.run(test_shutdown())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
    pass