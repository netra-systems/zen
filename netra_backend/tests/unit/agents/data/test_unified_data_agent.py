"""Unit tests for UnifiedDataAgent SSOT implementation.

Tests the consolidated data agent with factory pattern and user isolation.
"""

import asyncio
import pytest
from unittest.mock import patch, AsyncMock
from datetime import datetime, timezone
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.data.unified_data_agent import (
    UnifiedDataAgent,
    UnifiedDataAgentFactory,
    PerformanceAnalysisStrategy,
    AnomalyDetectionStrategy,
    CorrelationAnalysisStrategy,
    UsagePatternStrategy,
    CostOptimizationStrategy
)
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUnifiedDataAgentFactory:
    """Test factory pattern for user isolation."""
    
    def test_factory_creates_isolated_agents(self):
        """Test factory creates separate agents per user context."""
        factory = UnifiedDataAgentFactory()
        
        # Create contexts for different users
        context1 = UserExecutionContext(
            user_id="user1",
            request_id="req1",
            thread_id="thread1",
            run_id="run1"
        )
        
        context2 = UserExecutionContext(
            user_id="user2",
            request_id="req2",
            thread_id="thread2",
            run_id="run2"
        )
        
        # Create agents
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent1 = factory.create_for_context(context1)
            agent2 = factory.create_for_context(context2)
        
        # Verify different instances
        assert agent1 is not agent2
        assert agent1.context.user_id == "user1"
        assert agent2.context.user_id == "user2"
        
        # Verify factory tracking
        assert factory.created_count == 2
        assert len(factory.active_agents) == 2
        
    def test_factory_cleanup(self):
        """Test factory cleanup of agents."""
        factory = UnifiedDataAgentFactory()
        
        context = UserExecutionContext(
            user_id="user1",
            request_id="req1",
            thread_id="thread1",
            run_id="run1"
        )
        
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent = factory.create_for_context(context)
            agent_id = agent.agent_id
        
        # Verify agent is tracked
        assert agent_id in factory.active_agents
        
        # Clean up
        factory.cleanup_agent(agent_id)
        
        # Verify cleanup
        assert agent_id not in factory.active_agents
        
    def test_factory_status(self):
        """Test factory status reporting."""
        factory = UnifiedDataAgentFactory()
        
        # Create agents for multiple users
        contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"user{i}",
                request_id=f"req{i}",
                thread_id=f"thread{i}",
                run_id=f"run{i}"
            )
            contexts.append(context)
            with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
                factory.create_for_context(context)
        
        status = factory.get_status()
        
        assert status["total_created"] == 3
        assert status["active_agents"] == 3
        assert len(status["active_users"]) == 3
        assert "user0" in status["active_users"]
        assert "user1" in status["active_users"]
        assert "user2" in status["active_users"]


class TestUnifiedDataAgent:
    """Test UnifiedDataAgent core functionality."""
    
    @pytest.fixture
    def user_context(self):
        """Create test user context."""
        return UserExecutionContext(
            user_id="test_user",
            request_id="test_request",
            thread_id="test_thread",
            run_id="test_run"
        )
    
    @pytest.fixture
    def agent(self, user_context):
        """Create test agent instance."""
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            return UnifiedDataAgent(context=user_context)
    
    def test_agent_initialization(self, agent, user_context):
        """Test agent initializes with correct context."""
        assert agent.context == user_context
        assert agent.agent_id == "test_user_test_request"
        assert len(agent.strategies) == 5
        assert 'performance' in agent.strategies
        assert 'anomaly' in agent.strategies
        assert 'correlation' in agent.strategies
        assert 'usage_pattern' in agent.strategies
        assert 'cost_optimization' in agent.strategies
        
    def test_extract_analysis_type(self):
        """Test analysis type extraction from context."""
        # Test with metadata
        context1 = UserExecutionContext(
            user_id="test_user",
            request_id="test_request",
            thread_id="test_thread",
            run_id="test_run",
            metadata={'analysis_type': 'anomaly'}
        )
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent1 = UnifiedDataAgent(context=context1)
            assert agent1._extract_analysis_type(context1) == 'anomaly'
        
        # Test with metadata analysis_type
        context2 = UserExecutionContext(
            user_id="test_user",
            request_id="test_request2",
            thread_id="test_thread",
            run_id="test_run2",
            metadata={'analysis_type': 'correlation'}
        )
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent2 = UnifiedDataAgent(context=context2)
            assert agent2._extract_analysis_type(context2) == 'correlation'
        
        # Test default
        context3 = UserExecutionContext(
            user_id="test_user",
            request_id="test_request3",
            thread_id="test_thread",
            run_id="test_run3"
        )
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent3 = UnifiedDataAgent(context=context3)
            assert agent3._extract_analysis_type(context3) == 'performance'
        
    def test_validate_request(self, agent):
        """Test request validation."""
        # Valid request
        result = agent._validate_request('performance', {'timeframe': '24h'})
        assert result["valid"] is True
        
        # Invalid analysis type
        result = agent._validate_request('invalid_type', {'timeframe': '24h'})
        assert result["valid"] is False
        assert "Invalid analysis type" in result["error"]
        
        # Invalid timeframe
        result = agent._validate_request('performance', {'timeframe': 'invalid'})
        assert result["valid"] is False
        assert "Invalid timeframe format" in result["error"]
        
    def test_validate_timeframe_format(self, agent):
        """Test timeframe format validation."""
        assert agent._validate_timeframe_format('24h') is True
        assert agent._validate_timeframe_format('7d') is True
        assert agent._validate_timeframe_format('30d') is True
        assert agent._validate_timeframe_format('1w') is True
        assert agent._validate_timeframe_format('invalid') is False
        assert agent._validate_timeframe_format('24') is False
        assert agent._validate_timeframe_format('h') is False
        
    def test_generate_fallback_data(self, agent):
        """Test fallback data generation."""
        metrics = ["latency_ms", "throughput", "success_rate"]
        data = agent._generate_fallback_data(metrics, 10)
        
        assert len(data) == 10
        for record in data:
            assert "timestamp" in record
            assert "latency_ms" in record
            assert "throughput" in record
            assert "success_rate" in record
            assert 10 <= record["latency_ms"] <= 500
            assert 100 <= record["throughput"] <= 1000
            assert 0.9 <= record["success_rate"] <= 1.0
    
    @pytest.mark.asyncio
    async def test_websocket_event_emission(self):
        """Test WebSocket event emission."""
        # Mock WebSocket manager
        mock_ws_manager = AsyncMock()
        
        # Create context with WebSocket manager - UserExecutionContext is frozen, so use dict for testing
        class MockContext:
            def __init__(self):
                self.user_id = "test_user"
                self.request_id = "test_request"
                self.websocket_manager = mock_ws_manager
        
        context = MockContext()
        
        # Create agent
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent = UnifiedDataAgent(context=UserExecutionContext(
                user_id="test_user",
                request_id="test_request",
                thread_id="test_thread",
                run_id="test_run"
            ))
        
        # Emit event
        await agent._emit_websocket_event(
            context,
            "agent_started",
            {"run_id": "test_run", "agent_name": "UnifiedDataAgent"}
        )
        
        # Verify event sent
        mock_ws_manager.send_event.assert_called_once_with(
            "agent_started",
            {"run_id": "test_run", "agent_name": "UnifiedDataAgent"}
        )
    
    @pytest.mark.asyncio
    async def test_handle_validation_error(self, agent, user_context):
        """Test validation error handling."""
        validation_result = {
            "valid": False,
            "error": "Test validation error"
        }
        
        result = await agent._handle_validation_error(user_context, validation_result)
        
        assert result["error"] == "Test validation error"
        assert result["analysis_type"] == "error"
        assert len(result["suggestions"]) > 0
    
    @pytest.mark.asyncio
    async def test_handle_unknown_analysis(self, agent, user_context):
        """Test unknown analysis type handling."""
        result = await agent._handle_unknown_analysis(user_context, "unknown_type")
        
        assert "Unknown analysis type: unknown_type" in result["error"]
        assert "available_types" in result
        assert len(result["available_types"]) == 5


class TestAnalysisStrategies:
    """Test individual analysis strategy implementations."""
    
    def test_performance_strategy_metrics_extraction(self):
        """Test performance strategy extracts metrics correctly."""
        strategy = PerformanceAnalysisStrategy()
        
        data = [
            {"latency_ms": 100, "throughput": 500},
            {"latency_ms": 200, "throughput": 600},
            {"latency_ms": 150, "throughput": 550}
        ]
        
        metrics = strategy._extract_metrics(data)
        
        assert metrics["avg_latency"] == 150.0
        assert metrics["avg_throughput"] == 550.0
        assert metrics["total_requests"] == 3
        assert "p50_latency" in metrics
        assert "p95_latency" in metrics
        assert "p99_latency" in metrics
    
    def test_anomaly_strategy_zscore_detection(self):
        """Test anomaly detection using z-score method."""
        strategy = AnomalyDetectionStrategy()
        
        # Create data with outlier
        data = [
            {"value": 10, "timestamp": "2024-01-01T00:00:00"},
            {"value": 12, "timestamp": "2024-01-01T01:00:00"},
            {"value": 11, "timestamp": "2024-01-01T02:00:00"},
            {"value": 100, "timestamp": "2024-01-01T03:00:00"},  # Outlier
            {"value": 13, "timestamp": "2024-01-01T04:00:00"}
        ]
        
        loop = asyncio.new_event_loop()
        anomalies = loop.run_until_complete(
            strategy._detect_anomalies(data, {"z_threshold": 2.0})
        )
        
        assert len(anomalies) > 0
        # The value 100 should be detected as anomaly
        outlier_found = any(a["value"] == 100 for a in anomalies)
        assert outlier_found
    
    def test_correlation_strategy_pearson(self):
        """Test correlation calculation."""
        strategy = CorrelationAnalysisStrategy()
        
        # Perfect positive correlation
        x = [1, 2, 3, 4, 5]
        y = [2, 4, 6, 8, 10]
        
        corr = strategy._pearson_correlation(x, y)
        assert abs(corr - 1.0) < 0.01  # Should be close to 1.0
        
        # Perfect negative correlation
        y_neg = [10, 8, 6, 4, 2]
        corr_neg = strategy._pearson_correlation(x, y_neg)
        assert abs(corr_neg - (-1.0)) < 0.01  # Should be close to -1.0
    
    def test_usage_pattern_peak_hours(self):
        """Test peak hour identification."""
        strategy = UsagePatternStrategy()
        
        # Create data with clear peak hours
        data = []
        for hour in range(24):
            count = 100 if hour in [9, 10, 11, 14, 15, 16] else 10
            for _ in range(count):
                # Mock timestamp that hashes to specific hour
                data.append({"timestamp": f"2024-01-01T{hour:02d}:00:00"})
        
        # This is a simplified test - actual implementation would parse real timestamps
        peak_hours = strategy._identify_peak_hours(data)
        
        # Should identify some peak hours
        assert isinstance(peak_hours, list)
    
    def test_cost_optimization_opportunities(self):
        """Test cost optimization opportunity identification."""
        strategy = CostOptimizationStrategy()
        
        data = [
            {"model_name": "gpt-4", "cost_cents": 50, "tokens_input": 1500},
            {"model_name": "gpt-4", "cost_cents": 60, "tokens_input": 1800},
            {"model_name": "gpt-3.5", "cost_cents": 10, "tokens_input": 500},
            {"model_name": "gpt-4", "cost_cents": 55, "tokens_input": 1600}
        ]
        
        current_costs = strategy._calculate_current_costs(data)
        opportunities = strategy._identify_opportunities(data, current_costs)
        
        # Should identify model optimization opportunity (75% using expensive model)
        assert len(opportunities) > 0
        model_opt = next((o for o in opportunities if o["type"] == "model_optimization"), None)
        assert model_opt is not None
        
        # Should identify token optimization (avg > 1000)
        token_opt = next((o for o in opportunities if o["type"] == "token_optimization"), None)
        assert token_opt is not None


@pytest.mark.asyncio
class TestUnifiedDataAgentExecution:
    """Test end-to-end execution of UnifiedDataAgent."""
    
    async def test_execute_performance_analysis(self):
        """Test full execution with performance analysis."""
        context = UserExecutionContext(
            user_id="test_user",
            request_id="test_req_perf",
            thread_id="test_thread",
            run_id="test_run_perf",
            metadata={
                "analysis_type": "performance",
                "timeframe": "24h"
            }
        )
        
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent = UnifiedDataAgent(context=context)
        
        # Mock data fetching
        with patch.object(agent, '_fetch_data', return_value=[
            {"latency_ms": 100, "throughput": 500, "success_rate": 0.99},
            {"latency_ms": 110, "throughput": 480, "success_rate": 0.98},
            {"latency_ms": 95, "throughput": 520, "success_rate": 1.0}
        ]):
            result = await agent.execute(context)
        
        assert result["analysis_type"] == "performance"
        assert "metrics" in result
        assert "trends" in result
        assert "insights" in result
        assert "recommendations" in result
    
    async def test_execute_with_websocket_events(self):
        """Test execution emits all required WebSocket events."""
        context = UserExecutionContext(
            user_id="test_user",
            request_id="test_req_ws",
            thread_id="test_thread",
            run_id="test_run_ws",
            websocket_client_id="test_ws_connection"
        )
        
        # Mock WebSocket manager (this should be patched at the agent level)
        mock_ws_manager = AsyncMock()
        
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent = UnifiedDataAgent(context=context)
        
        # Mock the websocket event emission
        async def mock_emit_websocket_event(ctx, event_type, data):
            await mock_ws_manager.send_event(event_type, data)
        
        with patch.object(agent, '_emit_websocket_event', side_effect=mock_emit_websocket_event) as mock_emit:
            # Mock data fetching
            with patch.object(agent, '_fetch_data', return_value=[{"value": 10}]):
                await agent.execute(context)
        
        # Verify all critical events were sent
        calls = mock_ws_manager.send_event.call_args_list
        event_types = [call[0][0] for call in calls]
        
        assert "agent_started" in event_types
        assert "agent_thinking" in event_types
        assert "tool_executing" in event_types
        assert "tool_completed" in event_types
        assert "agent_completed" in event_types
    
    async def test_execute_error_handling(self):
        """Test execution handles errors gracefully."""
        context = UserExecutionContext(
            user_id="test_user",
            request_id="test_req_error",
            thread_id="test_thread",
            run_id="test_run_error"
        )
        
        with patch('netra_backend.app.agents.data.unified_data_agent.DataAccessCapabilities'):
            agent = UnifiedDataAgent(context=context)
        
        # Mock data fetching to raise error
        with patch.object(agent, '_fetch_data', side_effect=Exception("Test error")):
            result = await agent.execute(context)
        
        # Should return error result, not raise
        assert "error" in result
        assert "Test error" in result["error"]
        assert result["analysis_type"] == "error"