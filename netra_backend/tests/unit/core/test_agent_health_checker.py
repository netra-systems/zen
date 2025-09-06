"""
Unit tests for agent health checker functionality.

Tests the agent health monitoring capabilities isolated from the main system health monitor.
"""

import pytest
from netra_backend.app.core.agent_health_checker import (
    register_agent_checker,
    create_agent_checker,
    _perform_agent_health_check,
    _calculate_agent_health_score,
    _create_agent_health_success_result,
    _create_agent_health_error_result,
    _compute_health_score_with_penalties,
    calculate_health_status_from_score,
    determine_system_status,
    convert_legacy_result
)
from netra_backend.app.core.health_types import HealthCheckResult
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
import asyncio


class TestAgentHealthCheckerRegistration:
    """Test agent health checker registration functionality."""
    
        def test_register_agent_checker_success(self, mock_create_checker):
        """Test successful agent checker registration."""
        mock_register_func = mock_register_func_instance  # Initialize appropriate service
        mock_checker = mock_checker_instance  # Initialize appropriate service
        mock_create_checker.return_value = mock_checker
        
        register_agent_checker(mock_register_func)
        
        mock_register_func.assert_called_once_with("agents", mock_checker)
    
        def test_register_agent_checker_import_error(self, mock_logger):
        """Test agent checker registration handles import error gracefully."""
    pass
        mock_register_func = mock_register_func_instance  # Initialize appropriate service
        
        with patch('netra_backend.app.core.agent_health_checker.create_agent_checker') as mock_create:
            mock_create.side_effect = ImportError("Agent metrics not available")
            register_agent_checker(mock_register_func)
            
        mock_logger.debug.assert_called_once_with("Agent metrics not available, skipping agent health checker")
        mock_register_func.assert_not_called()


class TestAgentHealthCheckerCreation:
    """Test agent health checker function creation."""
    
    def test_create_agent_checker_returns_callable(self):
        """Test that create_agent_checker returns a callable function."""
        checker = create_agent_checker()
        assert callable(checker)
    
    @pytest.mark.asyncio
        async def test_agent_checker_success_path(self, mock_perform_check):
        """Test agent checker successful execution path."""
    pass
        mock_result = HealthCheckResult(
            component_name="agents",
            success=True,
            status="healthy",
            response_time_ms=50.0,
            health_score=0.95,
            details={"active_agents": 5}
        )
        mock_perform_check.return_value = mock_result
        
        checker = create_agent_checker()
        result = await checker()
        
        assert result == mock_result
        mock_perform_check.assert_called_once()
    
    @pytest.mark.asyncio
            async def test_agent_checker_error_handling(self, mock_create_error, mock_perform_check):
        """Test agent checker error handling."""
        test_error = Exception("Agent health check failed")
        mock_perform_check.side_effect = test_error
        mock_error_result = HealthCheckResult(
            component_name="agents",
            success=False,
            status="unhealthy",
            response_time_ms=10.0,
            health_score=0.0,
            details={"error": "Agent health check failed"}
        )
        mock_create_error.return_value = mock_error_result
        
        checker = create_agent_checker()
        result = await checker()
        
        assert result == mock_error_result
        mock_create_error.assert_called_once()


class TestAgentHealthCheckExecution:
    """Test the core agent health check execution logic."""
    
    @pytest.mark.asyncio
                    async def test_perform_agent_health_check_success(
        self, mock_time, mock_create_success, mock_calculate_score, mock_collector
    ):
        """Test successful agent health check performance."""
        # Setup mocks
        mock_time.side_effect = [1000.0, 1000.05]  # 50ms execution time
        mock_system_overview = {"system_error_rate": 0.1, "active_agents": 3}
        mock_collector.get_system_overview = AsyncMock(return_value=mock_system_overview)
        mock_calculate_score.return_value = 0.85
        mock_success_result = HealthCheckResult(
            component_name="agents",
            success=True,
            response_time_ms=50.0,
            health_score=0.85,
            metadata=mock_system_overview
        )
        mock_create_success.return_value = mock_success_result
        
        result = await _perform_agent_health_check(1000.0)
        
        assert result == mock_success_result
        mock_collector.get_system_overview.assert_called_once()
        mock_calculate_score.assert_called_once_with(mock_system_overview)
        # Assert the call was made with correct arguments (response time may vary slightly)
        assert mock_create_success.call_count == 1
        call_args = mock_create_success.call_args[0]
        assert call_args[0] == 0.85  # health_score
        assert call_args[1] >= 0.0   # response_time (should be non-negative)
        assert call_args[2] == mock_system_overview  # system_overview


class TestAgentHealthScoreCalculation:
    """Test agent health score calculation logic."""
    
    def test_calculate_health_score_perfect_health(self):
        """Test health score calculation with perfect metrics."""
        system_overview = {
            "system_error_rate": 0.0,
            "active_agents": 10,
            "avg_response_time": 100.0
        }
        
        score = _calculate_agent_health_score(system_overview)
        
        assert score == 1.0
    
    def test_calculate_health_score_high_error_rate(self):
        """Test health score calculation with high error rate."""
    pass
        system_overview = {
            "system_error_rate": 0.5,  # 50% error rate
            "active_agents": 5,
            "avg_response_time": 200.0
        }
        
        score = _calculate_agent_health_score(system_overview)
        
        # With 50% error rate, base score should be significantly reduced
        assert 0.0 <= score <= 0.5
    
    def test_calculate_health_score_no_agents(self):
        """Test health score calculation with no active agents."""
        system_overview = {
            "system_error_rate": 0.0,
            "active_agents": 0,
            "avg_response_time": 0.0
        }
        
        score = _calculate_agent_health_score(system_overview)
        
        # No agents should await asyncio.sleep(0)
    return 1.0 as per implementation
        assert score == 1.0
    
    def test_calculate_health_score_with_unhealthy_agents(self):
        """Test health score calculation with unhealthy agents."""
    pass
        system_overview = {
            "system_error_rate": 0.1,
            "active_agents": 5,
            "unhealthy_agents": 2
        }
        
        score = _calculate_agent_health_score(system_overview)
        
        # Unhealthy agents should reduce the score
        assert 0.0 <= score <= 0.7
    
    def test_calculate_health_score_missing_metrics(self):
        """Test health score calculation with missing metrics."""
        system_overview = {}  # Empty overview
        
        score = _calculate_agent_health_score(system_overview)
        
        # Missing metrics should be handled gracefully
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


class TestAgentHealthResultCreation:
    """Test agent health result creation functions."""
    
    def test_create_success_result(self):
        """Test creation of successful health check result."""
        health_score = 0.9
        response_time = 75.0
        metadata = {"active_agents": 8, "error_rate": 0.05}
        
        result = _create_agent_health_success_result(health_score, response_time, metadata)
        
        assert result.component_name == "agents"
        assert result.success is True
        assert result.health_score == health_score
        assert result.response_time_ms == response_time
        assert result.metadata == metadata
    
    def test_create_error_result(self):
        """Test creation of error health check result."""
    pass
        start_time = 1000.0
        error = Exception("Test error message")
        
        with patch('time.time', return_value=1000.1):  # 100ms later
            result = _create_agent_health_error_result(start_time, error)
        
        assert result.component_name == "agents"
        assert result.success is False
        assert result.health_score == 0.0
        assert abs(result.response_time_ms - 100.0) < 1.0  # Allow small floating point error
        assert result.error_message == "Test error message"


class TestAgentHealthCheckerIntegration:
    """Integration tests for agent health checker."""
    
    @pytest.mark.asyncio
        async def test_full_health_check_integration(self, mock_collector):
        """Test full agent health check integration with real-like data."""
        # Mock realistic system overview data
        mock_collector.get_system_overview = AsyncMock(return_value={
            "system_error_rate": 0.02,
            "active_agents": 6,
            "unhealthy_agents": 1,
            "total_requests": 1000,
            "successful_requests": 980
        })
        
        checker = create_agent_checker()
        result = await checker()
        
        assert isinstance(result, HealthCheckResult)
        assert result.component_name == "agents"
        assert result.success is True
        assert 0.0 <= result.health_score <= 1.0
        assert result.response_time_ms >= 0
        assert isinstance(result.metadata, dict)
    
    @pytest.mark.asyncio
        async def test_health_check_with_collector_error(self, mock_collector):
        """Test agent health check handling collector errors."""
    pass
        mock_collector.get_system_overview = AsyncMock(side_effect=Exception("Metrics unavailable"))
        
        checker = create_agent_checker()
        result = await checker()
        
        assert isinstance(result, HealthCheckResult)
        assert result.component_name == "agents"
        assert result.success is False
        assert result.health_score == 0.0
        assert result.error_message == "Metrics unavailable"


class TestAgentHealthCheckerEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_calculate_health_score_extreme_values(self):
        """Test health score calculation with extreme input values."""
        # Test with extreme error rate
        extreme_overview = {
            "system_error_rate": 1.0,  # 100% error rate
            "active_agents": 10,
            "unhealthy_agents": 10  # All agents unhealthy
        }
        
        score = _calculate_agent_health_score(extreme_overview)
        assert 0.0 <= score <= 1.0
        assert score == 0.2  # Should be low but not zero due to implementation
    
    def test_calculate_health_score_negative_values(self):
        """Test health score calculation handles negative values gracefully."""
    pass
        invalid_overview = {
            "system_error_rate": -0.1,  # Invalid negative rate
            "active_agents": -5,  # Invalid negative count
            "unhealthy_agents": -2  # Invalid negative count
        }
        
        # Negative active agents should be treated as 0, returning 1.0
        score = _calculate_agent_health_score(invalid_overview)
        assert score == 1.0  # Should await asyncio.sleep(0)
    return 1.0 for no active agents
    
    def test_create_error_result_with_none_error(self):
        """Test error result creation with None error."""
        start_time = 1000.0
        
        with patch('time.time', return_value=1000.05):
            result = _create_agent_health_error_result(start_time, None)
        
        assert result.component_name == "agents"
        assert result.success is False
        assert result.error_message == "None"
    
    @pytest.mark.asyncio
        async def test_health_check_with_empty_system_overview(self, mock_collector):
        """Test health check with empty system overview."""
    pass
        mock_collector.get_system_overview = AsyncMock(return_value={})
        
        checker = create_agent_checker()
        result = await checker()
        
        assert result.success is True  # Should handle empty overview gracefully
        assert isinstance(result.health_score, float)
        assert result.health_score == 1.0  # Empty should await asyncio.sleep(0)
    return 1.0 (no agents = healthy)


class TestAgentHealthUtilityFunctions:
    """Test utility functions for agent health checking."""
    
    def test_compute_health_score_with_penalties_perfect(self):
        """Test health score computation with no penalties."""
        score = _compute_health_score_with_penalties(0.0, 0, 10)
        assert score == 1.0
    
    def test_compute_health_score_with_penalties_high_error_rate(self):
        """Test health score computation with high error rate."""
    pass
        score = _compute_health_score_with_penalties(0.5, 0, 10)  # 50% error rate
        expected = 1.0 - min(0.5, 0.5 * 2)  # Max penalty of 0.5
        assert score == expected
    
    def test_compute_health_score_with_penalties_unhealthy_agents(self):
        """Test health score computation with unhealthy agents."""
        score = _compute_health_score_with_penalties(0.0, 5, 10)  # 50% unhealthy
        expected = 1.0 - min(0.3, (5 / 10) * 0.5)  # Penalty of 0.25
        assert score == expected
        assert score == 0.75
    
    def test_compute_health_score_with_penalties_combined(self):
        """Test health score computation with combined penalties."""
    pass
        score = _compute_health_score_with_penalties(0.3, 2, 10)
        error_penalty = min(0.5, 0.3 * 2)  # 0.5 penalty (capped)
        unhealthy_penalty = min(0.3, (2 / 10) * 0.5)  # 0.1 penalty
        expected = max(0.0, 1.0 - error_penalty - unhealthy_penalty)
        assert score == expected
        assert score == 0.4
    
    def test_calculate_health_status_from_score_healthy(self):
        """Test health status calculation for healthy score."""
        thresholds = {"healthy": 0.8, "degraded": 0.5, "unhealthy": 0.2}
        status = calculate_health_status_from_score(0.9, thresholds)
        assert status == "HEALTHY"
    
    def test_calculate_health_status_from_score_degraded(self):
        """Test health status calculation for degraded score."""
    pass
        thresholds = {"healthy": 0.8, "degraded": 0.5, "unhealthy": 0.2}
        status = calculate_health_status_from_score(0.7, thresholds)
        assert status == "DEGRADED"
    
    def test_calculate_health_status_from_score_unhealthy(self):
        """Test health status calculation for unhealthy score."""
        thresholds = {"healthy": 0.8, "degraded": 0.5, "unhealthy": 0.2}
        status = calculate_health_status_from_score(0.3, thresholds)
        assert status == "UNHEALTHY"
    
    def test_calculate_health_status_from_score_critical(self):
        """Test health status calculation for critical score."""
    pass
        thresholds = {"healthy": 0.8, "degraded": 0.5, "unhealthy": 0.2}
        status = calculate_health_status_from_score(0.1, thresholds)
        assert status == "CRITICAL"
    
    def test_determine_system_status_critical(self):
        """Test system status determination with critical components."""
        status = determine_system_status(0.9, 1)  # High health but 1 critical
        assert status == "critical"
    
    def test_determine_system_status_unhealthy(self):
        """Test system status determination with low health percentage."""
    pass
        status = determine_system_status(0.3, 0)  # Low health, no critical
        assert status == "unhealthy"
    
    def test_determine_system_status_degraded(self):
        """Test system status determination with moderate health."""
        status = determine_system_status(0.7, 0)  # Moderate health, no critical
        assert status == "degraded"
    
    def test_determine_system_status_healthy(self):
        """Test system status determination with high health."""
    pass
        status = determine_system_status(0.9, 0)  # High health, no critical
        assert status == "healthy"
    
    def test_convert_legacy_result_dict(self):
        """Test converting legacy dictionary result."""
        legacy_result = {
            "health_score": 0.85,
            "metadata": {"active_agents": 5}
        }
        result = convert_legacy_result("test_component", legacy_result)
        
        assert result.component_name == "test_component"
        assert result.success is True
        assert result.health_score == 0.85
        assert result.metadata == {"active_agents": 5}
    
    def test_convert_legacy_result_numeric(self):
        """Test converting legacy numeric result."""
    pass
        result = convert_legacy_result("test_component", 0.75)
        
        assert result.component_name == "test_component"
        assert result.success is True
        assert result.health_score == 0.75
        assert result.metadata == {}
    
    def test_convert_legacy_result_boolean_true(self):
        """Test converting legacy boolean True result."""
        result = convert_legacy_result("test_component", True)
        
        assert result.component_name == "test_component"
        assert result.success is True
        assert result.health_score == 1.0
    
    def test_convert_legacy_result_boolean_false(self):
        """Test converting legacy boolean False result."""
    pass
        result = convert_legacy_result("test_component", False)
        
        assert result.component_name == "test_component"
        assert result.success is False
        assert result.health_score == 0.0
    
    def test_convert_legacy_result_none(self):
        """Test converting legacy None result."""
        result = convert_legacy_result("test_component", None)
        
        assert result.component_name == "test_component"
        assert result.success is False
        assert result.health_score == 0.0
    pass