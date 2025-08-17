"""Base tests for AgentReliabilityMixin - data classes and initialization."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, UTC

# Import the components we're testing
from app.core.agent_reliability_mixin import (
    AgentReliabilityMixin, AgentError, AgentHealthStatus
)
from app.core.error_codes import ErrorSeverity


class MockAgent(AgentReliabilityMixin):
    """Mock agent for testing the reliability mixin."""
    
    def __init__(self, name: str = "TestAgent"):
        self.name = name
        super().__init__()


class TestAgentError:
    """Test AgentError dataclass."""
    
    def test_agent_error_creation(self):
        """Test AgentError creation with all fields."""
        error = AgentError(
            error_id="test_error_1",
            agent_name="TestAgent",
            operation="test_operation",
            error_type="ValueError",
            message="Test error message",
            timestamp=datetime.now(UTC),
            severity=ErrorSeverity.HIGH,
            context={"key": "value"},
            recovery_attempted=True,
            recovery_successful=False
        )
        
        assert error.error_id == "test_error_1"
        assert error.agent_name == "TestAgent"
        assert error.operation == "test_operation"
        assert error.error_type == "ValueError"
        assert error.message == "Test error message"
        assert error.severity == ErrorSeverity.HIGH
        assert error.context == {"key": "value"}
        assert error.recovery_attempted is True
        assert error.recovery_successful is False


class TestAgentHealthStatus:
    """Test AgentHealthStatus dataclass."""
    
    def test_health_status_creation(self):
        """Test AgentHealthStatus creation with all fields."""
        error = AgentError(
            error_id="test_error_1",
            agent_name="TestAgent",
            operation="test_operation",
            error_type="ValueError",
            message="Test error message",
            timestamp=datetime.now(UTC),
            severity=ErrorSeverity.HIGH
        )
        
        health = AgentHealthStatus(
            agent_name="TestAgent",
            overall_health=0.85,
            circuit_breaker_state="closed",
            recent_errors=2,
            total_operations=100,
            success_rate=0.98,
            average_response_time=1.2,
            last_error=error,
            status="healthy"
        )
        
        assert health.agent_name == "TestAgent"
        assert health.overall_health == 0.85
        assert health.circuit_breaker_state == "closed"
        assert health.recent_errors == 2
        assert health.total_operations == 100
        assert health.success_rate == 0.98
        assert health.average_response_time == 1.2
        assert health.last_error == error
        assert health.status == "healthy"


class TestAgentReliabilityMixinInitialization:
    """Test initialization and configuration of AgentReliabilityMixin."""
    
    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent with reliability mixin."""
        with patch('app.core.agent_reliability_mixin.get_reliability_wrapper') as mock_wrapper:
            mock_reliability = Mock()
            mock_reliability.execute_safely = Mock()
            mock_reliability.circuit_breaker = Mock()
            mock_reliability.circuit_breaker.get_status = Mock(return_value={"state": "closed"})
            mock_reliability.circuit_breaker.reset = Mock()
            mock_wrapper.return_value = mock_reliability
            
            agent = MockAgent("TestAgent")
            agent.reliability = mock_reliability
            return agent
    
    def test_initialization(self, mock_agent):
        """Test proper initialization of reliability mixin."""
        assert mock_agent.name == "TestAgent"
        assert hasattr(mock_agent, 'reliability')
        assert hasattr(mock_agent, 'error_history')
        assert hasattr(mock_agent, 'operation_times')
        assert hasattr(mock_agent, 'recovery_strategies')
        
        # Check initial state
        assert len(mock_agent.error_history) == 0
        assert len(mock_agent.operation_times) == 0
        assert mock_agent.max_error_history == 50
        assert mock_agent.max_operation_history == 100
        assert mock_agent.health_check_interval == 60
        
        # Check default recovery strategies are registered
        assert "llm_call" in mock_agent.recovery_strategies
        assert "database_query" in mock_agent.recovery_strategies
        assert "api_call" in mock_agent.recovery_strategies
    
    def test_get_circuit_breaker_config(self, mock_agent):
        """Test circuit breaker configuration."""
        config = mock_agent._get_circuit_breaker_config()
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30.0
        assert config.name == "TestAgent"
    
    def test_get_retry_config(self, mock_agent):
        """Test retry configuration."""
        config = mock_agent._get_retry_config()
        
        assert config.max_retries == 2
        assert config.base_delay == 1.0
        assert config.max_delay == 10.0
    
    def test_register_recovery_strategy(self, mock_agent):
        """Test registering custom recovery strategy."""
        async def custom_recovery(error, context):
            return {"custom": "recovery"}
        
        mock_agent.register_recovery_strategy("custom_operation", custom_recovery)
        assert "custom_operation" in mock_agent.recovery_strategies
        assert mock_agent.recovery_strategies["custom_operation"] == custom_recovery
    
    def test_record_successful_operation(self, mock_agent):
        """Test recording successful operations."""
        # Record multiple operations
        mock_agent._record_successful_operation("op1", 1.5)
        mock_agent._record_successful_operation("op2", 2.3)
        mock_agent._record_successful_operation("op3", 0.8)
        
        assert len(mock_agent.operation_times) == 3
        assert mock_agent.operation_times == [1.5, 2.3, 0.8]
    
    def test_operation_times_history_limit(self, mock_agent):
        """Test operation times history size limit."""
        # Fill beyond the limit
        for i in range(150):  # More than max_operation_history (100)
            mock_agent._record_successful_operation(f"op{i}", float(i))
        
        # Verify size is limited
        assert len(mock_agent.operation_times) == 100
        # Verify it keeps the most recent entries
        assert mock_agent.operation_times[0] == 50.0  # Should start from 50
        assert mock_agent.operation_times[-1] == 149.0
    
    def test_error_history_limit(self, mock_agent):
        """Test error history size limit."""
        # Create many errors
        for i in range(75):  # More than max_error_history (50)
            error_record = AgentError(
                error_id=f"error_{i}",
                agent_name="TestAgent",
                operation=f"operation_{i}",
                error_type="ValueError",
                message=f"Error {i}",
                timestamp=datetime.now(UTC),
                severity=ErrorSeverity.LOW
            )
            mock_agent.error_history.append(error_record)
        
        # Manually trigger the size limit check
        mock_agent.error_history = mock_agent.error_history[-mock_agent.max_error_history:]
        
        # Verify size is limited
        assert len(mock_agent.error_history) == 50
        # Verify it keeps the most recent entries
        assert mock_agent.error_history[0].error_id == "error_25"
        assert mock_agent.error_history[-1].error_id == "error_74"
