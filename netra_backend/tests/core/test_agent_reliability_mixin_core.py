"""Core reliability tests for AgentReliabilityMixin - execution and error handling."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, UTC

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


# Import the components we're testing
from netra_backend.app.core.agent_reliability_mixin import AgentReliabilityMixin
from netra_backend.app.core.agent_reliability_types import AgentError
from netra_backend.app.core.error_codes import ErrorSeverity


class MockAgent(AgentReliabilityMixin):
    """Mock agent for testing the reliability mixin."""
    
    def __init__(self, name: str = "TestAgent"):
        self.name = name
        super().__init__()


class TestAgentReliabilityMixinExecution:
    """Test core execution and reliability functionality."""
    
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


class TestAgentReliabilityMixinErrorHandling:
    """Test error handling and classification."""
    
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


class TestDefaultRecoveryStrategies:
    """Test default recovery strategies."""
    
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
