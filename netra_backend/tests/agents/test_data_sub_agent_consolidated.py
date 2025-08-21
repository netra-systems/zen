"""Tests for Consolidated DataSubAgent

Comprehensive tests for the unified DataSubAgent implementation.
Validates all critical functionality for reliable data insights.

Business Value: Ensures 15-30% cost savings identification works reliably.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.agents.data_sub_agent.data_sub_agent import DataSubAgent
from netra_backend.app.agents.data_sub_agent.clickhouse_client import ClickHouseClient
from netra_backend.app.agents.data_sub_agent.schema_cache import SchemaCache
from netra_backend.app.agents.data_sub_agent.performance_analyzer import PerformanceAnalyzer
from netra_backend.app.services.llm.cost_optimizer import LLMCostOptimizer
from netra_backend.app.agents.data_sub_agent.data_validator import DataValidator

from llm.llm_manager import LLMManager
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.schemas.strict_types import TypedAgentResult
from netra_backend.app.agents.base.interface import ExecutionContext, ExecutionResult, ExecutionStatus

# Add project root to path


class TestDataSubAgentConsolidated:
    """Test suite for consolidated DataSubAgent implementation."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Mock LLM manager for testing."""
        llm_manager = Mock(spec=LLMManager)
        llm_manager.generate_response = AsyncMock(return_value={
            "content": "Test AI insights: Optimize model selection for 20% cost reduction"
        })
        return llm_manager
    
    @pytest.fixture
    def mock_tool_dispatcher(self):
        """Mock tool dispatcher for testing."""
        return Mock(spec=ToolDispatcher)
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager for testing."""
        websocket_manager = Mock()
        websocket_manager.send_agent_update = AsyncMock()
        return websocket_manager
    
    @pytest.fixture
    def sample_workload_data(self) -> List[Dict[str, Any]]:
        """Sample workload data for testing."""
        return [
            {
                "timestamp": datetime.utcnow() - timedelta(hours=1),
                "user_id": "test_user_1",
                "workload_id": "workload_1",
                "workload_type": "chat_completion",
                "latency_ms": 150.5,
                "cost_cents": 2.3,
                "throughput": 100.0
            },
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=30),
                "user_id": "test_user_1",
                "workload_id": "workload_2",
                "workload_type": "embedding",
                "latency_ms": 75.2,
                "cost_cents": 1.1,
                "throughput": 200.0
            },
            {
                "timestamp": datetime.utcnow() - timedelta(minutes=15),
                "user_id": "test_user_2",
                "workload_id": "workload_3", 
                "workload_type": "chat_completion",
                "latency_ms": 3200.0,  # High latency
                "cost_cents": 8.7,     # High cost
                "throughput": 25.0
            }
        ]
    
    @pytest.fixture
    def sample_cost_breakdown(self) -> List[Dict[str, Any]]:
        """Sample cost breakdown data for testing."""
        return [
            {
                "user_id": "test_user_1",
                "workload_type": "chat_completion",
                "request_count": 150,
                "avg_cost_cents": 2.5,
                "total_cost_cents": 375.0
            },
            {
                "user_id": "test_user_1",
                "workload_type": "embedding",
                "request_count": 300,
                "avg_cost_cents": 1.2,
                "total_cost_cents": 360.0
            },
            {
                "user_id": "test_user_2",
                "workload_type": "chat_completion",
                "request_count": 50,
                "avg_cost_cents": 8.5,  # High cost workload
                "total_cost_cents": 425.0
            }
        ]
    
    @pytest.fixture
    async def data_sub_agent(self, mock_llm_manager, mock_tool_dispatcher, mock_websocket_manager):
        """Create DataSubAgent instance for testing."""
        with patch('app.agents.data_sub_agent.data_sub_agent.ClickHouseClient') as mock_ch, \
             patch('app.agents.data_sub_agent.data_sub_agent.SchemaCache') as mock_sc, \
             patch('app.agents.data_sub_agent.data_sub_agent.PerformanceAnalyzer') as mock_pa, \
             patch('app.agents.data_sub_agent.data_sub_agent.LLMCostOptimizer') as mock_co, \
             patch('app.agents.data_sub_agent.data_sub_agent.DataValidator') as mock_dv:
            
            agent = DataSubAgent(
                llm_manager=mock_llm_manager,
                tool_dispatcher=mock_tool_dispatcher,
                websocket_manager=mock_websocket_manager
            )
            
            # Setup mock responses
            agent.clickhouse_client.is_healthy.return_value = True
            agent.schema_cache.is_available.return_value = True
            
            return agent
    
    @pytest.mark.asyncio
    async def test_data_sub_agent_initialization(self, data_sub_agent):
        """Test DataSubAgent initializes correctly."""
        assert data_sub_agent is not None
        assert data_sub_agent.name == "DataSubAgent"
        assert "Advanced data analysis for AI cost optimization" in data_sub_agent.description
        assert hasattr(data_sub_agent, 'clickhouse_client')
        assert hasattr(data_sub_agent, 'schema_cache')
        assert hasattr(data_sub_agent, 'performance_analyzer')
        assert hasattr(data_sub_agent, 'cost_optimizer')
        assert hasattr(data_sub_agent, 'data_validator')
    
    @pytest.mark.asyncio
    async def test_performance_analysis_execution(self, data_sub_agent, sample_workload_data):
        """Test performance analysis execution workflow."""
        # Setup mock data
        data_sub_agent.performance_analyzer.analyze_performance = AsyncMock(return_value={
            "summary": "Performance analysis completed",
            "data_points": 3,
            "findings": ["High latency detected in 33% of requests"],
            "recommendations": ["Consider request optimization"],
            "metrics": {
                "latency": {"avg_latency_ms": 1141.9, "p95_latency_ms": 3200.0}
            },
            "cost_savings": {"percentage": 15.0, "amount_cents": 50.0}
        })
        
        # Create test state
        state = DeepAgentState(
            agent_input={
                "analysis_type": "performance",
                "timeframe": "24h",
                "metrics": ["latency_ms", "cost_cents"]
            },
            user_id="test_user_1"
        )
        
        # Execute analysis
        result = await data_sub_agent.execute(state)
        
        # Validate results
        assert result.success is True
        assert result.agent_name == "DataSubAgent"
        assert "insights" in result.result
        assert result.result["analysis_type"] == "performance"
        assert result.result["data_points_analyzed"] == 3
        assert result.execution_time_ms > 0
        
        # Verify performance analyzer was called
        data_sub_agent.performance_analyzer.analyze_performance.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cost_optimization_execution(self, data_sub_agent, sample_cost_breakdown):
        """Test cost optimization analysis execution."""
        # Setup mock data
        data_sub_agent.cost_optimizer.analyze_costs = AsyncMock(return_value={
            "summary": "Cost optimization analysis completed",
            "data_points": 500,
            "findings": ["High-cost workload identified: chat_completion averages 8.50 cents"],
            "recommendations": ["Switch to more efficient model for high-cost workloads"],
            "savings_potential": {
                "total_savings_cents": 200.0,
                "savings_percentage": 25.0,
                "monthly_projection_cents": 6000.0
            }
        })
        
        # Create test state
        state = DeepAgentState(
            agent_input={
                "analysis_type": "cost_optimization",
                "timeframe": "7d",
                "user_id": "test_user_1"
            }
        )
        
        # Execute analysis
        result = await data_sub_agent.execute(state)
        
        # Validate results
        assert result.success is True
        assert "cost_savings_potential" in result.result["insights"]
        assert result.result["insights"]["cost_savings_potential"]["savings_percentage"] == 25.0
        
        # Verify cost optimizer was called
        data_sub_agent.cost_optimizer.analyze_costs.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_insights_generation(self, data_sub_agent):
        """Test LLM-powered insights generation."""
        # Setup performance analysis with raw data
        data_sub_agent.performance_analyzer.analyze_performance = AsyncMock(return_value={
            "summary": "Analysis with raw data",
            "findings": ["Performance degradation detected"],
            "recommendations": ["Optimize queries"],
            "raw_data": [{"latency_ms": 2000, "cost_cents": 5.0}]
        })
        
        # Create test state
        state = DeepAgentState(
            agent_input={"analysis_type": "performance"},
            user_id="test_user"
        )
        
        # Execute analysis
        result = await data_sub_agent.execute(state)
        
        # Validate LLM insights were included
        assert result.success is True
        assert "ai_insights" in result.result["insights"]
        assert "Optimize model selection" in result.result["insights"]["ai_insights"]
        
        # Verify LLM manager was called
        data_sub_agent.llm_manager.generate_response.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execution_context_interface(self, data_sub_agent):
        """Test BaseExecutionInterface implementation."""
        # Create execution context
        state = DeepAgentState(
            agent_input={"analysis_type": "performance"},
            user_id="test_user"
        )
        
        context = ExecutionContext(
            run_id="test_run_123",
            agent_name="DataSubAgent",
            state=state,
            stream_updates=False
        )
        
        # Mock performance analysis
        data_sub_agent.performance_analyzer.analyze_performance = AsyncMock(return_value={
            "summary": "Test analysis",
            "findings": [],
            "recommendations": [],
            "metrics": {}
        })
        
        # Execute via BaseExecutionInterface
        result = await data_sub_agent.execute_core_logic(context)
        
        # Validate execution result
        assert isinstance(result, ExecutionResult)
        assert result.success is True
        assert result.status == ExecutionStatus.COMPLETED
    
    @pytest.mark.asyncio
    async def test_preconditions_validation(self, data_sub_agent):
        """Test preconditions validation."""
        state = DeepAgentState(agent_input={"analysis_type": "performance"})
        context = ExecutionContext(
            run_id="test_run",
            agent_name="DataSubAgent",
            state=state
        )
        
        # Test with healthy dependencies
        valid = await data_sub_agent.validate_preconditions(context)
        assert valid is True
        
        # Test with unhealthy ClickHouse
        data_sub_agent.clickhouse_client.is_healthy.return_value = False
        valid = await data_sub_agent.validate_preconditions(context)
        assert valid is False
    
    @pytest.mark.asyncio
    async def test_error_handling(self, data_sub_agent):
        """Test error handling in execution workflow."""
        # Setup analyzer to raise exception
        data_sub_agent.performance_analyzer.analyze_performance = AsyncMock(
            side_effect=Exception("ClickHouse connection failed")
        )
        
        state = DeepAgentState(
            agent_input={"analysis_type": "performance"},
            user_id="test_user"
        )
        
        # Execute analysis
        result = await data_sub_agent.execute(state)
        
        # Validate error handling
        assert result.success is False
        assert "ClickHouse connection failed" in result.result["error"]
        assert result.execution_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_invalid_execution_state(self, data_sub_agent):
        """Test handling of invalid execution state."""
        # Test with None state
        result = await data_sub_agent.execute(None)
        assert result.success is False
        assert "Invalid execution state" in result.result["error"]
        
        # Test with state missing agent_input
        empty_state = DeepAgentState()
        result = await data_sub_agent.execute(empty_state)
        assert result.success is False
        assert "Invalid execution state" in result.result["error"]
    
    @pytest.mark.asyncio
    async def test_health_status(self, data_sub_agent):
        """Test health status reporting."""
        # Setup mock health statuses
        data_sub_agent.clickhouse_client.get_health_status.return_value = {
            "healthy": True,
            "last_check": datetime.utcnow().isoformat()
        }
        
        data_sub_agent.schema_cache.get_health_status.return_value = {
            "available": True,
            "cached_tables": ["workload_events"],
            "cache_size": 1
        }
        
        # Get health status
        health = data_sub_agent.get_health_status()
        
        # Validate health status structure
        assert health["agent_name"] == "DataSubAgent"
        assert health["status"] == "healthy"
        assert "clickhouse_health" in health
        assert "schema_cache_health" in health
        assert "components" in health
        assert health["components"]["performance_analyzer"] == "active"
        assert health["components"]["cost_optimizer"] == "active"
        assert health["components"]["data_validator"] == "active"
        assert "timestamp" in health
    
    @pytest.mark.asyncio
    async def test_cleanup_resources(self, data_sub_agent):
        """Test resource cleanup."""
        # Setup cleanup mocks
        data_sub_agent.clickhouse_client.close = AsyncMock()
        data_sub_agent.schema_cache.cleanup = AsyncMock()
        
        # Perform cleanup
        await data_sub_agent.cleanup()
        
        # Verify cleanup was called
        data_sub_agent.clickhouse_client.close.assert_called_once()
        data_sub_agent.schema_cache.cleanup.assert_called_once()
    
    def test_analysis_request_extraction(self, data_sub_agent):
        """Test analysis request parameter extraction."""
        # Test with complete parameters
        state = DeepAgentState(
            agent_input={
                "analysis_type": "cost_optimization",
                "timeframe": "7d",
                "metrics": ["cost_cents", "throughput"],
                "filters": {"workload_type": "chat_completion"}
            },
            user_id="test_user_123"
        )
        
        request = data_sub_agent._extract_analysis_request(state)
        
        assert request["type"] == "cost_optimization"
        assert request["timeframe"] == "7d"
        assert request["metrics"] == ["cost_cents", "throughput"]
        assert request["filters"] == {"workload_type": "chat_completion"}
        assert request["user_id"] == "test_user_123"
    
    def test_analysis_request_defaults(self, data_sub_agent):
        """Test analysis request with default parameters."""
        # Test with minimal parameters
        state = DeepAgentState(
            agent_input={},
            user_id=None
        )
        
        request = data_sub_agent._extract_analysis_request(state)
        
        assert request["type"] == "performance"  # Default
        assert request["timeframe"] == "24h"     # Default
        assert "latency_ms" in request["metrics"]  # Default metrics
        assert "cost_cents" in request["metrics"]
        assert "throughput" in request["metrics"]
        assert request["filters"] == {}         # Default
        assert request["user_id"] is None
    
    @pytest.mark.asyncio
    async def test_trend_analysis_workflow(self, data_sub_agent):
        """Test trend analysis workflow execution."""
        # Setup mock trend analysis
        data_sub_agent.performance_analyzer.analyze_trends = AsyncMock(return_value={
            "summary": "Trend analysis over 7d with 150 data points",
            "trends": {
                "latency_trend": {"trend": "improving", "change_percentage": -10.5},
                "cost_trend": {"trend": "stable", "change_percentage": 2.1}
            },
            "data_points": 150,
            "findings": ["Latency trend improving by 10.5%"]
        })
        
        state = DeepAgentState(
            agent_input={"analysis_type": "trend_analysis", "timeframe": "7d"},
            user_id="test_user"
        )
        
        result = await data_sub_agent.execute(state)
        
        assert result.success is True
        assert result.result["analysis_type"] == "trend_analysis"
        assert "Latency trend improving" in str(result.result["insights"])
        
        # Verify trend analyzer was called
        data_sub_agent.performance_analyzer.analyze_trends.assert_called_once()


class TestClickHouseClient:
    """Test ClickHouse client functionality."""
    
    @pytest.fixture
    def clickhouse_client(self):
        return ClickHouseClient()
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self, clickhouse_client):
        """Test ClickHouse connection establishment."""
        # Test connection with mock
        with patch('app.agents.data_sub_agent.clickhouse_client.get_client', None):
            result = await clickhouse_client.connect()
            assert result is True  # Should succeed in mock mode
    
    @pytest.mark.asyncio
    async def test_workload_metrics_query(self, clickhouse_client, sample_workload_data):
        """Test workload metrics query execution."""
        # Mock query execution
        clickhouse_client.execute_query = AsyncMock(return_value=sample_workload_data)
        
        metrics = await clickhouse_client.get_workload_metrics("24h", "test_user")
        
        assert len(metrics) == 3
        assert metrics[0]["latency_ms"] == 150.5
        assert metrics[0]["cost_cents"] == 2.3
        
        # Verify query was called with correct parameters
        clickhouse_client.execute_query.assert_called_once()
    
    def test_health_status_check(self, clickhouse_client):
        """Test health status checking."""
        # Initially unhealthy (no connection)
        assert clickhouse_client.is_healthy() is False
        
        # Set health status
        clickhouse_client._health_status = {
            "healthy": True,
            "last_check": datetime.utcnow()
        }
        
        assert clickhouse_client.is_healthy() is True
        
        # Test stale connection
        clickhouse_client._health_status["last_check"] = datetime.utcnow() - timedelta(minutes=10)
        assert clickhouse_client.is_healthy() is False


class TestDataValidator:
    """Test data validation functionality."""
    
    @pytest.fixture
    def data_validator(self):
        return DataValidator()
    
    def test_analysis_request_validation(self, data_validator):
        """Test analysis request validation."""
        # Valid request
        valid_request = {
            "type": "performance",
            "timeframe": "24h",
            "metrics": ["latency_ms", "cost_cents"]
        }
        
        is_valid, errors = data_validator.validate_analysis_request(valid_request)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid request
        invalid_request = {
            "type": "invalid_type",
            "timeframe": "invalid_format",
            "metrics": ["invalid_metric"]
        }
        
        is_valid, errors = data_validator.validate_analysis_request(invalid_request)
        assert is_valid is False
        assert len(errors) > 0
    
    def test_raw_data_validation(self, data_validator, sample_workload_data):
        """Test raw data quality validation."""
        is_valid, validation_result = data_validator.validate_raw_data(
            sample_workload_data, 
            ["latency_ms", "cost_cents"]
        )
        
        assert is_valid is True
        assert validation_result["data_points"] == 3
        assert validation_result["quality_score"] > 0.8
        assert "quality_metrics" in validation_result
    
    def test_analysis_result_validation(self, data_validator):
        """Test analysis result validation."""
        # Valid result
        valid_result = {
            "summary": "Analysis completed",
            "findings": ["High latency detected"],
            "recommendations": ["Optimize queries"],
            "cost_savings": {
                "savings_percentage": 20.0,
                "total_potential_savings_cents": 100.0
            }
        }
        
        is_valid, errors = data_validator.validate_analysis_result(valid_result)
        assert is_valid is True
        assert len(errors) == 0
        
        # Invalid result (missing required fields)
        invalid_result = {
            "summary": "Analysis completed"
            # Missing findings and recommendations
        }
        
        is_valid, errors = data_validator.validate_analysis_result(invalid_result)
        assert is_valid is False
        assert len(errors) > 0
