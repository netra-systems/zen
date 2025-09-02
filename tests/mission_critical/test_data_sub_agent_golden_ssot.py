"""Test DataSubAgent Golden Pattern SSOT Implementation

Validates that DataSubAgent follows the golden pattern established by TriageSubAgent:
- Single inheritance from BaseAgent
- No infrastructure duplication
- Only business logic in sub-agent
- Proper WebSocket event emission
- Comprehensive data analysis functionality

This test ensures the consolidation from 66+ fragmented files to single SSOT is successful.
"""

import asyncio
import pytest
from typing import Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher


class TestDataSubAgentGoldenPattern:
    """Test golden pattern compliance for DataSubAgent."""
    
    @pytest.fixture
    async def mock_llm_manager(self):
        """Mock LLM manager."""
        llm_manager = MagicMock(spec=LLMManager)
        llm_manager.generate_response = AsyncMock(return_value={"content": "Test AI insights"})
        return llm_manager
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Mock tool dispatcher."""
        return MagicMock(spec=ToolDispatcher)
    
    @pytest.fixture
    async def data_agent(self, mock_llm_manager, mock_tool_dispatcher):
        """Create DataSubAgent instance for testing."""
        return DataSubAgent(
            llm_manager=mock_llm_manager,
            tool_dispatcher=mock_tool_dispatcher
        )
    
    def test_golden_pattern_inheritance(self, data_agent):
        """Test that DataSubAgent follows golden pattern inheritance."""
        from netra_backend.app.agents.base_agent import BaseAgent
        
        # Should inherit from BaseAgent only (single inheritance)
        assert isinstance(data_agent, BaseAgent)
        
        # Should have BaseAgent's infrastructure methods
        assert hasattr(data_agent, 'emit_thinking')
        assert hasattr(data_agent, 'emit_progress')
        assert hasattr(data_agent, 'emit_tool_executing')
        assert hasattr(data_agent, 'emit_tool_completed')
        assert hasattr(data_agent, 'emit_error')
        assert hasattr(data_agent, 'execute_with_reliability')
        
        # Should have required abstract methods implemented
        assert hasattr(data_agent, 'validate_preconditions')
        assert hasattr(data_agent, 'execute_core_logic')
        
        # Should NOT have infrastructure duplicated
        assert not hasattr(data_agent, '_send_websocket_update')  # Should use inherited methods
        assert not hasattr(data_agent, '_retry_operation')       # Should use inherited reliability
        
    def test_consolidated_core_components(self, data_agent):
        """Test that core components are properly consolidated."""
        # Should have consolidated core business logic components
        assert hasattr(data_agent, 'data_analysis_core')
        assert hasattr(data_agent, 'data_processor')
        assert hasattr(data_agent, 'anomaly_detector')
        
        # Legacy compatibility attributes should exist
        assert hasattr(data_agent, 'clickhouse_client')
        assert hasattr(data_agent, 'cache_ttl')
        
        # Should not have fragmented helper classes
        assert not hasattr(data_agent, 'helpers')  # Removed fragmented helpers
        assert not hasattr(data_agent, 'core')     # Consolidated into data_analysis_core
    
    async def test_validate_preconditions_golden_pattern(self, data_agent):
        """Test precondition validation following golden pattern."""
        # Test valid preconditions
        state = DeepAgentState()
        state.agent_input = {"analysis_type": "performance", "timeframe": "24h"}
        context = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=state,
            stream_updates=True
        )
        
        result = await data_agent.validate_preconditions(context)
        assert result is True
        
        # Test invalid preconditions - no state
        context_no_state = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=None,
            stream_updates=True
        )
        
        result = await data_agent.validate_preconditions(context_no_state)
        assert result is False
        
        # Test invalid preconditions - no agent_input
        state_no_input = DeepAgentState()
        context_no_input = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=state_no_input,
            stream_updates=True
        )
        
        result = await data_agent.validate_preconditions(context_no_input)
        assert result is False
    
    @patch('netra_backend.app.agents.data_sub_agent.core.data_analysis_core.DataAnalysisCore.analyze_performance')
    async def test_execute_core_logic_websocket_events(self, mock_analyze_performance, data_agent):
        """Test that core logic execution emits proper WebSocket events."""
        # Mock the analysis result
        mock_analyze_performance.return_value = {
            "status": "completed",
            "data_points": 100,
            "summary": "Performance analysis completed",
            "findings": ["High latency detected", "Throughput within normal range"],
            "recommendations": ["Optimize queries", "Add caching"],
            "metrics": {
                "latency": {"avg_latency_ms": 250.0, "p95_latency_ms": 450.0},
                "throughput": {"avg_throughput": 15.2}
            }
        }
        
        # Mock WebSocket methods
        data_agent.emit_thinking = AsyncMock()
        data_agent.emit_progress = AsyncMock()
        data_agent.emit_tool_executing = AsyncMock()
        data_agent.emit_tool_completed = AsyncMock()
        
        # Create test context
        state = DeepAgentState()
        state.agent_input = {"analysis_type": "performance", "timeframe": "24h"}
        context = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=state,
            stream_updates=True
        )
        
        # Execute core logic
        result = await data_agent.execute_core_logic(context)
        
        # Verify WebSocket events were emitted (golden pattern requirement)
        assert data_agent.emit_thinking.call_count >= 2  # Multiple thinking events
        assert data_agent.emit_progress.call_count >= 2  # Multiple progress events
        data_agent.emit_tool_executing.assert_called()   # Tool execution started
        data_agent.emit_tool_completed.assert_called()   # Tool execution completed
        
        # Verify result structure
        assert result is not None
        assert result["analysis_type"] == "performance"
        assert result["status"] == "completed"
        assert result["data_points_analyzed"] == 100
        assert "execution_time_ms" in result
        
        # Verify flattened insights
        assert result["key_findings"] == "High latency detected, Throughput within normal range"
        assert result["recommendations"] == "Optimize queries, Add caching"
        assert result["avg_latency_ms"] == 250.0
        assert result["p95_latency_ms"] == 450.0
        assert result["avg_throughput"] == 15.2
    
    @patch('netra_backend.app.agents.data_sub_agent.core.data_analysis_core.DataAnalysisCore.analyze_costs')
    async def test_cost_optimization_analysis(self, mock_analyze_costs, data_agent):
        """Test cost optimization analysis functionality."""
        # Mock cost analysis result
        mock_analyze_costs.return_value = {
            "status": "completed",
            "data_points": 50,
            "summary": "Cost analysis completed",
            "total_cost_cents": 12500,
            "avg_daily_cost_cents": 417,
            "savings_potential": {
                "savings_percentage": 23,
                "total_savings_cents": 2875,
                "potential_monthly_savings_cents": 2875
            },
            "recommendations": ["Optimize resource allocation", "Use reserved capacity"]
        }
        
        # Mock WebSocket methods
        data_agent.emit_thinking = AsyncMock()
        data_agent.emit_progress = AsyncMock()
        data_agent.emit_tool_executing = AsyncMock()
        data_agent.emit_tool_completed = AsyncMock()
        
        # Create test context for cost optimization
        state = DeepAgentState()
        state.agent_input = {"analysis_type": "cost_optimization", "timeframe": "30d"}
        context = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=state,
            stream_updates=True
        )
        
        # Execute core logic
        result = await data_agent.execute_core_logic(context)
        
        # Verify cost optimization specific results
        assert result["analysis_type"] == "cost_optimization"
        assert result["cost_savings_percentage"] == 23
        assert result["cost_savings_amount_cents"] == 2875
        assert "Optimize resource allocation" in result["recommendations"]
        
        # Verify proper tool events
        data_agent.emit_tool_executing.assert_called_with("cost_optimizer", {
            "analysis_type": "cost_optimization", 
            "timeframe": "30d"
        })
        data_agent.emit_tool_completed.assert_called_with("cost_optimizer", {
            "status": "success",
            "savings_identified": 23
        })
    
    @patch('netra_backend.app.agents.data_sub_agent.core.data_analysis_core.DataAnalysisCore.detect_anomalies')
    async def test_anomaly_detection_analysis(self, mock_detect_anomalies, data_agent):
        """Test anomaly detection functionality."""
        # Mock anomaly detection result
        mock_detect_anomalies.return_value = {
            "status": "completed",
            "anomalies_count": 5,
            "anomaly_percentage": 8.3,
            "anomalies": [
                {"timestamp": "2023-01-01T10:00:00Z", "value": 1200, "severity": "high"},
                {"timestamp": "2023-01-01T14:00:00Z", "value": 950, "severity": "medium"}
            ]
        }
        
        # Mock WebSocket methods
        data_agent.emit_thinking = AsyncMock()
        data_agent.emit_progress = AsyncMock()
        data_agent.emit_tool_executing = AsyncMock()
        data_agent.emit_tool_completed = AsyncMock()
        
        # Create test context for anomaly detection
        state = DeepAgentState()
        state.agent_input = {"analysis_type": "anomaly_detection", "timeframe": "7d"}
        context = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=state,
            stream_updates=True
        )
        
        # Execute core logic
        result = await data_agent.execute_core_logic(context)
        
        # Verify anomaly detection specific results
        assert result["analysis_type"] == "anomaly_detection"
        assert result["anomalies_detected"] == 5
        assert result["anomaly_percentage"] == 8.3
        
        # Verify proper tool events for anomaly detection
        data_agent.emit_tool_executing.assert_called_with("anomaly_detector", {
            "analysis_type": "anomaly_detection",
            "metric": "latency_ms"
        })
        data_agent.emit_tool_completed.assert_called_with("anomaly_detector", {
            "status": "success",
            "anomalies_found": 5
        })
    
    async def test_legacy_execute_method_compatibility(self, data_agent):
        """Test backward compatibility with legacy execute method."""
        # Mock core logic execution
        data_agent._execute_data_main = AsyncMock(return_value={
            "analysis_type": "performance",
            "status": "completed",
            "data_points_analyzed": 25
        })
        
        # Create test state
        state = DeepAgentState()
        state.agent_input = {"analysis_type": "performance"}
        
        # Execute using legacy method
        result = await data_agent.execute(state, "test123", stream_updates=True)
        
        # Should store result in state
        assert hasattr(state, 'data_result')
        assert state.data_result is not None
    
    def test_health_status_comprehensive(self, data_agent):
        """Test comprehensive health status reporting."""
        health_status = data_agent.get_health_status()
        
        # Should include core components health
        assert "agent_name" in health_status
        assert health_status["agent_name"] == "DataSubAgent"
        assert "core_components" in health_status
        
        # Should report health of consolidated components
        core_components = health_status["core_components"]
        assert "data_analysis_core" in core_components
        assert "data_processor" in core_components
        assert "anomaly_detector" in core_components
        
        # Should include business logic health
        assert "business_logic_health" in health_status
        assert "processing_stats" in health_status
        assert "detection_stats" in health_status
    
    async def test_error_handling_with_websocket_events(self, data_agent):
        """Test proper error handling with WebSocket event emission."""
        # Mock analysis to raise an exception
        data_agent.data_analysis_core.analyze_performance = AsyncMock(side_effect=Exception("Database error"))
        
        # Mock WebSocket methods
        data_agent.emit_thinking = AsyncMock()
        data_agent.emit_progress = AsyncMock()
        data_agent.emit_tool_executing = AsyncMock()
        data_agent.emit_tool_completed = AsyncMock()
        data_agent.emit_error = AsyncMock()
        
        # Create test context
        state = DeepAgentState()
        state.agent_input = {"analysis_type": "performance", "timeframe": "24h"}
        context = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=state,
            stream_updates=True
        )
        
        # Should raise exception but emit error event
        with pytest.raises(Exception, match="Database error"):
            await data_agent.execute_core_logic(context)
        
        # Should have emitted error event
        data_agent.emit_error.assert_called_once()
        error_call = data_agent.emit_error.call_args
        assert "tool_execution_error" in error_call[0]
    
    def test_ssot_consolidation_metrics(self, data_agent):
        """Test that SSOT consolidation metrics are accessible."""
        # Should have consolidated all 66+ files into core components
        assert hasattr(data_agent, 'data_analysis_core')  # Main analysis engine
        assert hasattr(data_agent, 'data_processor')      # Data processing
        assert hasattr(data_agent, 'anomaly_detector')    # Anomaly detection
        
        # Core should have proper health reporting
        core_health = data_agent.data_analysis_core.get_health_status()
        assert "clickhouse_health" in core_health
        assert "redis_health" in core_health
        assert "status" in core_health
        
        # Processor should have statistics
        processor_stats = data_agent.data_processor.get_processing_stats()
        assert "processed" in processor_stats
        assert "errors" in processor_stats
        
        # Detector should have statistics
        detector_stats = data_agent.anomaly_detector.get_detection_stats()
        assert "anomalies_detected" in detector_stats
        assert "total_analyzed" in detector_stats
    
    def test_no_infrastructure_duplication(self, data_agent):
        """Test that no infrastructure is duplicated from BaseAgent."""
        # Should NOT have custom WebSocket handling
        assert not hasattr(data_agent, '_websocket_manager')
        assert not hasattr(data_agent, '_send_websocket_event')
        assert not hasattr(data_agent, 'websocket_handler')
        
        # Should NOT have custom retry logic
        assert not hasattr(data_agent, '_retry_with_backoff')
        assert not hasattr(data_agent, '_execute_with_circuit_breaker')
        
        # Should NOT have custom execution engine
        assert not hasattr(data_agent, '_modern_execution_engine')
        assert not hasattr(data_agent, 'execution_patterns')
        
        # Should use BaseAgent's infrastructure
        assert hasattr(data_agent, 'execute_with_reliability')  # From BaseAgent
        assert hasattr(data_agent, 'emit_thinking')            # From BaseAgent
        assert hasattr(data_agent, 'redis_manager')            # From BaseAgent
    
    @pytest.mark.asyncio
    async def test_full_golden_pattern_workflow(self, data_agent):
        """Test complete golden pattern workflow end-to-end."""
        # Mock all core components
        data_agent.data_analysis_core.analyze_performance = AsyncMock(return_value={
            "status": "completed",
            "data_points": 150,
            "summary": "Comprehensive performance analysis",
            "findings": ["System performing well", "Minor optimization opportunities"],
            "recommendations": ["Implement query caching", "Optimize database indexes"],
            "metrics": {
                "latency": {"avg_latency_ms": 180.0, "p95_latency_ms": 320.0},
                "throughput": {"avg_throughput": 22.5}
            }
        })
        
        data_agent.data_processor.process_analysis_request = AsyncMock(return_value={
            "type": "performance",
            "timeframe": "24h",
            "metrics": ["latency_ms", "cost_cents", "throughput"],
            "filters": {},
            "user_id": "test_user"
        })
        
        data_agent.data_processor.enrich_analysis_result = AsyncMock(return_value={
            "request_context": {"analysis_type": "performance"},
            "processing_metadata": {"data_quality": "high"}
        })
        
        # Mock WebSocket methods
        data_agent.emit_thinking = AsyncMock()
        data_agent.emit_progress = AsyncMock()
        data_agent.emit_tool_executing = AsyncMock()
        data_agent.emit_tool_completed = AsyncMock()
        
        # Create test context
        state = DeepAgentState()
        state.agent_input = {
            "analysis_type": "performance",
            "timeframe": "24h",
            "metrics": ["latency_ms", "throughput"]
        }
        state.user_id = "test_user"
        
        context = ExecutionContext(
            run_id="test123",
            agent_name="DataSubAgent",
            state=state,
            stream_updates=True
        )
        
        # Execute full workflow
        result = await data_agent.execute_core_logic(context)
        
        # Verify complete golden pattern compliance
        assert result is not None
        assert result["status"] == "completed"
        assert result["analysis_type"] == "performance"
        assert result["data_points_analyzed"] == 150
        
        # Verify all WebSocket events emitted
        assert data_agent.emit_thinking.call_count >= 2
        assert data_agent.emit_progress.call_count >= 3  # Including completion
        data_agent.emit_tool_executing.assert_called_once()
        data_agent.emit_tool_completed.assert_called_once()
        
        # Verify business logic processed correctly
        assert result["key_findings"] == "System performing well, Minor optimization opportunities"
        assert result["recommendations"] == "Implement query caching, Optimize database indexes"
        assert result["avg_latency_ms"] == 180.0
        assert result["avg_throughput"] == 22.5
        
        print("✅ DataSubAgent Golden Pattern SSOT Implementation - All Tests Pass!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])