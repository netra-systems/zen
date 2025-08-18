"""Health monitoring tests for AgentReliabilityMixin - metrics and status."""

import pytest
import time
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta, UTC

# Import the components we're testing
from app.core.agent_reliability_mixin import AgentReliabilityMixin
from app.core.agent_reliability_types import AgentError, AgentHealthStatus
from app.core.error_codes import ErrorSeverity


class MockAgent(AgentReliabilityMixin):
    """Mock agent for testing the reliability mixin."""
    
    def __init__(self, name: str = "TestAgent"):
        self.name = name
        super().__init__()


class TestAgentReliabilityMixinMetrics:
    """Test health metrics calculations."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent with reliability mixin."""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability.circuit_breaker.reset = Mock()
            mock_wrapper.return_value = mock_reliability
            
            agent = MockAgent("TestAgent")
            agent.reliability = mock_reliability
            return agent
    
    def test_calculate_success_rate(self, mock_agent):
        """Test success rate calculation."""
        # No operations
        assert mock_agent._calculate_success_rate() == 1.0
        
        # Add successful operations
        mock_agent.operation_times = [1.0, 2.0, 3.0]
        assert mock_agent._calculate_success_rate() == 1.0
        
        # Add failed operations
        mock_agent.error_history = [
            AgentError("1", "TestAgent", "op1", "Error", "msg", datetime.now(UTC), ErrorSeverity.LOW)
        ]
        # 3 successful, 1 failed = 75% success rate
        assert mock_agent._calculate_success_rate() == 0.75
    
    def test_calculate_avg_response_time(self, mock_agent):
        """Test average response time calculation."""
        # No operations
        assert mock_agent._calculate_avg_response_time() == 0.0
        
        # Add operation times
        mock_agent.operation_times = [1.0, 2.0, 3.0, 4.0, 5.0]
        assert mock_agent._calculate_avg_response_time() == 3.0
        
        # Test with more than 20 operations (should use last 20)
        mock_agent.operation_times = list(range(1, 26))  # 1 to 25
        avg = mock_agent._calculate_avg_response_time()
        # Should average last 20: 6 to 25 = (6+25)*20/2/20 = 15.5
        expected = sum(range(6, 26)) / 20
        assert avg == expected
    
    def test_count_recent_errors(self, mock_agent):
        """Test counting recent errors."""
        now = datetime.now(UTC)
        
        # Add errors at different times
        mock_agent.error_history = [
            AgentError("1", "TestAgent", "op1", "Error", "msg", now - timedelta(seconds=600), ErrorSeverity.LOW),  # 10 min ago
            AgentError("2", "TestAgent", "op2", "Error", "msg", now - timedelta(seconds=200), ErrorSeverity.LOW),  # 3.3 min ago
            AgentError("3", "TestAgent", "op3", "Error", "msg", now - timedelta(seconds=100), ErrorSeverity.LOW),  # 1.7 min ago
            AgentError("4", "TestAgent", "op4", "Error", "msg", now - timedelta(seconds=50), ErrorSeverity.LOW),   # 50 sec ago
        ]
        
        # Count errors in last 5 minutes (300 seconds)
        recent_count = mock_agent._count_recent_errors(300)
        assert recent_count == 3  # Should exclude the one from 10 minutes ago
    
    def test_calculate_overall_health(self, mock_agent):
        """Test overall health calculation."""
        # Perfect health
        health = mock_agent._calculate_overall_health(1.0, 0, 1.0)
        assert health == 1.0
        
        # Health with recent errors
        health = mock_agent._calculate_overall_health(0.9, 2, 1.0)
        assert health == 0.7  # 0.9 - (2 * 0.1) = 0.7
        
        # Health with slow response time (capped at 30% penalty)
        health = mock_agent._calculate_overall_health(0.9, 0, 10.0)
        assert abs(health - 0.6) < 1e-10  # 0.9 - min((10-5) * 0.1, 0.3) = 0.9 - 0.3 = 0.6
        
        # Ensure health doesn't go below 0
        health = mock_agent._calculate_overall_health(0.2, 10, 20.0)
        assert health == 0.0
        
        # Ensure health doesn't go above 1
        health = mock_agent._calculate_overall_health(1.5, 0, 1.0)
        assert health == 1.0
    
    def test_determine_health_status(self, mock_agent):
        """Test health status determination."""
        # Healthy
        status = mock_agent._determine_health_status(0.9, 0)
        assert status == "healthy"
        
        # Degraded
        status = mock_agent._determine_health_status(0.7, 1)
        assert status == "degraded"
        
        # Unhealthy
        status = mock_agent._determine_health_status(0.3, 5)
        assert status == "unhealthy"
        
        # Boundary cases
        status = mock_agent._determine_health_status(0.8, 0)
        assert status == "healthy"
        
        status = mock_agent._determine_health_status(0.5, 2)
        assert status == "degraded"


class TestAgentReliabilityMixinHealthStatus:
    """Test health status functionality."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent with reliability mixin."""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            mock_reliability = Mock()
            mock_reliability.execute_safely = AsyncMock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability.circuit_breaker.reset = Mock()
            mock_wrapper.return_value = mock_reliability
            
            agent = MockAgent("TestAgent")
            agent.reliability = mock_reliability
            return agent
    
    def test_get_comprehensive_health_status(self, mock_agent):
        """Test comprehensive health status."""
        # Add some test data
        mock_agent.operation_times = [1.0, 2.0, 3.0]
        mock_agent.error_history = [
            AgentError("1", "TestAgent", "op1", "Error", "msg", datetime.now(UTC), ErrorSeverity.LOW)
        ]
        
        health = mock_agent.get_comprehensive_health_status()
        
        assert health.agent_name == "TestAgent"
        assert 0.0 <= health.overall_health <= 1.0
        assert health.circuit_breaker_state == "closed"
        assert health.total_operations == 4  # 3 successful + 1 failed
        assert health.success_rate == 0.75
        assert health.average_response_time == 2.0
        assert health.status in ["healthy", "degraded", "unhealthy"]
        assert health.last_error.error_id == "1"
    
    def test_get_error_summary_empty(self, mock_agent):
        """Test error summary with no errors."""
        summary = mock_agent.get_error_summary()
        
        assert summary["total_errors"] == 0
        assert summary["error_types"] == {}
        assert summary["recent_errors"] == 0
    
    def test_get_error_summary_with_errors(self, mock_agent):
        """Test error summary with errors."""
        now = datetime.now(UTC)
        
        # Add various errors
        mock_agent.error_history = [
            AgentError("1", "TestAgent", "op1", "ValueError", "msg1", now - timedelta(minutes=10), ErrorSeverity.LOW),
            AgentError("2", "TestAgent", "op2", "ConnectionError", "msg2", now - timedelta(minutes=2), ErrorSeverity.HIGH),
            AgentError("3", "TestAgent", "op3", "ValueError", "msg3", now - timedelta(minutes=1), ErrorSeverity.LOW),
        ]
        
        summary = mock_agent.get_error_summary()
        
        assert summary["total_errors"] == 3
        assert summary["error_types"]["ValueError"] == 2
        assert summary["error_types"]["ConnectionError"] == 1
        assert summary["recent_errors"] == 2  # Last 5 minutes
        assert summary["last_error"]["type"] == "ValueError"
        assert summary["last_error"]["message"] == "msg3"
    
    def test_reset_health_metrics(self, mock_agent):
        """Test resetting health metrics."""
        # Add some data
        mock_agent.operation_times = [1.0, 2.0, 3.0]
        mock_agent.error_history = [
            AgentError("1", "TestAgent", "op1", "Error", "msg", datetime.now(UTC), ErrorSeverity.LOW)
        ]
        
        # Reset
        mock_agent.reset_health_metrics()
        
        # Verify reset
        assert len(mock_agent.operation_times) == 0
        assert len(mock_agent.error_history) == 0
        mock_agent.reliability.circuit_breaker.reset.assert_called_once()
    
    async def test_perform_health_check(self, mock_agent):
        """Test performing health check."""
        # Add some test data
        mock_agent.operation_times = [1.0, 2.0]
        
        with patch('app.core.agent_reliability_mixin.logger') as mock_logger:
            health = await mock_agent.perform_health_check()
            
            assert isinstance(health, AgentHealthStatus)
            assert health.agent_name == "TestAgent"
            
            # Verify timestamp was updated
            assert mock_agent.last_health_check > 0
    
    def test_should_perform_health_check(self, mock_agent):
        """Test health check scheduling."""
        # Initially should check
        assert mock_agent.should_perform_health_check() is True
        
        # After recent check, shouldn't check
        mock_agent.last_health_check = time.time()
        assert mock_agent.should_perform_health_check() is False
        
        # After interval, should check again
        mock_agent.last_health_check = time.time() - 70  # More than 60 seconds ago
        assert mock_agent.should_perform_health_check() is True
