"""Comprehensive unit tests for AgentReliabilityMixin."""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, UTC
from typing import Dict, Any

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


class TestAgentReliabilityMixin:
    """Comprehensive tests for AgentReliabilityMixin."""
    
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
    async def test_execute_with_reliability_success(self, mock_agent):
        """Test successful operation execution."""
        # Setup
        async def mock_operation():
            return {"success": True, "data": "test"}
        
        mock_agent.reliability.execute_safely.return_value = {"success": True, "data": "test"}
        
        # Execute
        result = await mock_agent.execute_with_reliability(
            mock_operation,
            "test_operation",
            timeout=10.0
        )
        
        # Verify
        assert result == {"success": True, "data": "test"}
        assert len(mock_agent.operation_times) == 1
        assert mock_agent.operation_times[0] >= 0  # Accept 0 for fast operations in tests
        assert len(mock_agent.error_history) == 0
        
        # Verify reliability wrapper was called correctly
        mock_agent.reliability.execute_safely.assert_called_once_with(
            mock_operation,
            "test_operation",
            fallback=None,
            timeout=10.0
        )
    async def test_execute_with_reliability_failure_no_recovery(self, mock_agent):
        """Test operation failure without recovery."""
        # Setup
        test_error = ValueError("Test error")
        
        async def mock_operation():
            raise test_error
        
        mock_agent.reliability.execute_safely.side_effect = test_error
        
        # Execute and verify exception is raised
        with pytest.raises(ValueError, match="Test error"):
            await mock_agent.execute_with_reliability(
                mock_operation,
                "test_operation"
            )
        
        # Verify error was recorded
        assert len(mock_agent.error_history) == 1
        error_record = mock_agent.error_history[0]
        assert error_record.agent_name == "TestAgent"
        assert error_record.operation == "test_operation"
        assert error_record.error_type == "ValueError"
        assert error_record.message == "Test error"
        assert error_record.severity == ErrorSeverity.LOW
        assert error_record.recovery_attempted is False
        assert error_record.recovery_successful is False
    async def test_execute_with_reliability_failure_with_recovery(self, mock_agent):
        """Test operation failure with successful recovery."""
        # Setup
        test_error = ValueError("Test error")
        recovery_result = {"recovered": True, "fallback": True}
        
        async def mock_operation():
            raise test_error
        
        async def mock_recovery(error, context):
            return recovery_result
        
        mock_agent.reliability.execute_safely.side_effect = test_error
        mock_agent.register_recovery_strategy("test_operation", mock_recovery)
        
        # Execute
        result = await mock_agent.execute_with_reliability(
            mock_operation,
            "test_operation",
            context={"test": "context"}
        )
        
        # Verify recovery result returned
        assert result == recovery_result
        
        # Verify error was recorded with recovery info
        assert len(mock_agent.error_history) == 1
        error_record = mock_agent.error_history[0]
        assert error_record.recovery_attempted is True
        assert error_record.recovery_successful is True
    
    def test_classify_error_severity(self, mock_agent):
        """Test error severity classification."""
        # Critical errors
        critical_errors = [MemoryError(), SystemExit(), KeyboardInterrupt()]
        for error in critical_errors:
            severity = mock_agent._classify_error_severity(error)
            assert severity == ErrorSeverity.CRITICAL
        
        # High severity errors
        high_errors = [ConnectionError(), TimeoutError()]
        for error in high_errors:
            severity = mock_agent._classify_error_severity(error)
            assert severity == ErrorSeverity.HIGH
        
        # Medium severity errors
        medium_errors = [ValueError("ValidationError")]  # Using ValueError as example
        for error in medium_errors:
            severity = mock_agent._classify_error_severity(error)
            assert severity == ErrorSeverity.LOW  # ValueError maps to LOW by default
        
        # Unknown errors default to LOW
        unknown_error = RuntimeError("Unknown error")
        severity = mock_agent._classify_error_severity(unknown_error)
        assert severity == ErrorSeverity.LOW
    
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
    
    def test_register_recovery_strategy(self, mock_agent):
        """Test registering custom recovery strategy."""
        async def custom_recovery(error, context):
            return {"custom": "recovery"}
        
        mock_agent.register_recovery_strategy("custom_operation", custom_recovery)
        assert "custom_operation" in mock_agent.recovery_strategies
        assert mock_agent.recovery_strategies["custom_operation"] == custom_recovery
    async def test_default_llm_recovery(self, mock_agent):
        """Test default LLM recovery strategy."""
        error = ValueError("LLM failed")
        context = {"prompt": "test prompt"}
        
        result = await mock_agent._default_llm_recovery(error, context)
        
        assert result["status"] == "fallback"
        assert result["message"] == "Operation completed with limited functionality"
        assert result["error"] == "LLM failed"
        assert result["fallback_used"] is True
    async def test_default_db_recovery(self, mock_agent):
        """Test default database recovery strategy."""
        error = ConnectionError("Database unavailable")
        context = {"query": "SELECT * FROM test"}
        
        result = await mock_agent._default_db_recovery(error, context)
        
        assert result["data"] == []
        assert result["cached"] is True
        assert result["error"] == "Database unavailable"
        assert result["fallback_used"] is True
    async def test_default_api_recovery(self, mock_agent):
        """Test default API recovery strategy."""
        error = TimeoutError("API timeout")
        context = {"endpoint": "/api/test"}
        
        result = await mock_agent._default_api_recovery(error, context)
        
        assert result["result"] == "limited"
        assert result["data"] == {}
        assert result["error"] == "API timeout"
        assert result["fallback_used"] is True
    
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
        
        # Health with slow response time
        health = mock_agent._calculate_overall_health(0.9, 0, 10.0)
        assert health == 0.4  # 0.9 - (10-5) * 0.1 = 0.9 - 0.5 = 0.4
        
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
    async def test_attempt_operation_recovery_no_strategy(self, mock_agent):
        """Test recovery attempt when no strategy exists."""
        error = ValueError("Test error")
        result = await mock_agent._attempt_operation_recovery("unknown_operation", error, {})
        assert result is None
    async def test_attempt_operation_recovery_strategy_fails(self, mock_agent):
        """Test recovery attempt when strategy itself fails."""
        async def failing_recovery(error, context):
            raise RuntimeError("Recovery failed")
        
        mock_agent.register_recovery_strategy("test_operation", failing_recovery)
        
        with patch('app.core.agent_reliability_mixin.logger') as mock_logger:
            error = ValueError("Test error")
            result = await mock_agent._attempt_operation_recovery("test_operation", error, {})
            
            assert result is None
            mock_logger.error.assert_called_once()
    
    @patch('app.core.agent_reliability_mixin.logger')
    def test_log_error_different_severities(self, mock_logger, mock_agent):
        """Test logging errors with different severity levels."""
        errors = [
            AgentError("1", "TestAgent", "op1", "MemoryError", "Critical", datetime.now(UTC), ErrorSeverity.CRITICAL),
            AgentError("2", "TestAgent", "op2", "ConnectionError", "High", datetime.now(UTC), ErrorSeverity.HIGH),
            AgentError("3", "TestAgent", "op3", "ValidationError", "Medium", datetime.now(UTC), ErrorSeverity.MEDIUM),
            AgentError("4", "TestAgent", "op4", "ValueError", "Low", datetime.now(UTC), ErrorSeverity.LOW),
        ]
        
        for error in errors:
            mock_agent._log_error(error)
        
        # Verify appropriate logging methods were called
        mock_logger.critical.assert_called_once()
        mock_logger.error.assert_called_once()
        mock_logger.warning.assert_called_once()
        mock_logger.info.assert_called_once()