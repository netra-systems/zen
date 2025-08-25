"""
Test Enhanced Unified Retry Handler

Tests comprehensive retry functionality including:
- Domain-specific retry policies
- Circuit breaker integration
- Context manager support
- Decorator patterns
- Fibonacci and adaptive backoff strategies
"""

import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Any

from netra_backend.app.core.resilience.unified_retry_handler import (
    UnifiedRetryHandler,
    RetryConfig,
    RetryStrategy,
    RetryDecision,
    RetryResult,
    RetryAttempt,
    RetryContext,
    # Domain-specific policies
    DATABASE_RETRY_POLICY,
    LLM_RETRY_POLICY,
    AGENT_RETRY_POLICY,
    API_RETRY_POLICY,
    WEBSOCKET_RETRY_POLICY,
    FILE_RETRY_POLICY,
    # Convenience functions
    retry_database_operation,
    retry_llm_request,
    retry_agent_operation,
    retry_http_request,
    retry_websocket_operation,
    retry_file_operation,
    # Decorators
    database_retry,
    llm_retry,
    agent_retry,
    api_retry,
    # Global handlers
    database_retry_handler,
    llm_retry_handler,
    agent_retry_handler,
    api_retry_handler,
)


class TestEnhancedRetryStrategies:
    """Test new retry strategies (Fibonacci, Adaptive)."""
    
    def test_fibonacci_delay_calculation(self):
        """Test Fibonacci backoff strategy."""
        config = RetryConfig(
            strategy=RetryStrategy.FIBONACCI,
            base_delay=1.0,
            max_delay=60.0
        )
        handler = UnifiedRetryHandler("test", config)
        
        # Test fibonacci sequence: 1, 1, 2, 3, 5, 8, 13...
        assert handler._fibonacci_delay(1) == 1.0  # base_delay * 1
        assert handler._fibonacci_delay(2) == 1.0  # base_delay * 1
        assert handler._fibonacci_delay(3) == 2.0  # base_delay * 2
        assert handler._fibonacci_delay(4) == 3.0  # base_delay * 3
        assert handler._fibonacci_delay(5) == 5.0  # base_delay * 5
        assert handler._fibonacci_delay(6) == 8.0  # base_delay * 8
    
    def test_adaptive_delay_calculation(self):
        """Test adaptive backoff strategy (currently uses exponential)."""
        config = RetryConfig(
            strategy=RetryStrategy.ADAPTIVE,
            base_delay=1.0,
            backoff_multiplier=2.0
        )
        handler = UnifiedRetryHandler("test", config)
        
        # Currently same as exponential - could be enhanced with historical data
        assert handler._adaptive_delay(1) == 1.0  # base_delay * 2^0
        assert handler._adaptive_delay(2) == 2.0  # base_delay * 2^1
        assert handler._adaptive_delay(3) == 4.0  # base_delay * 2^2
    
    def test_strategy_delay_capping(self):
        """Test that all strategies respect max_delay."""
        config = RetryConfig(
            base_delay=10.0,
            max_delay=15.0,
            backoff_multiplier=3.0
        )
        handler = UnifiedRetryHandler("test", config)
        
        # Test with exponential that would exceed max_delay
        config.strategy = RetryStrategy.EXPONENTIAL
        handler.config = config
        delay = handler._calculate_delay(3)  # 10 * 3^2 = 90, but capped at 15
        assert delay == 15.0
        
        # Test with fibonacci that would exceed max_delay
        config.strategy = RetryStrategy.FIBONACCI
        handler.config = config
        delay = handler._calculate_delay(6)  # 10 * 8 = 80, but capped at 15
        assert delay == 15.0


class TestDomainSpecificPolicies:
    """Test domain-specific retry policies."""
    
    def test_database_retry_policy_configuration(self):
        """Test database retry policy has correct configuration."""
        policy = DATABASE_RETRY_POLICY
        
        assert policy.max_attempts == 5
        assert policy.base_delay == 0.5
        assert policy.max_delay == 30.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL_JITTER
        assert policy.circuit_breaker_enabled == True
        assert policy.circuit_breaker_failure_threshold == 5
        assert policy.circuit_breaker_recovery_timeout == 60.0
        
        # Test retryable exceptions
        import psycopg2
        import sqlalchemy.exc
        assert psycopg2.OperationalError in policy.retryable_exceptions
        assert sqlalchemy.exc.DisconnectionError in policy.retryable_exceptions
        assert ConnectionError in policy.retryable_exceptions
        
        # Test non-retryable exceptions
        assert psycopg2.ProgrammingError in policy.non_retryable_exceptions
        assert sqlalchemy.exc.IntegrityError in policy.non_retryable_exceptions
        assert ValueError in policy.non_retryable_exceptions
    
    def test_llm_retry_policy_configuration(self):
        """Test LLM retry policy has correct configuration."""
        policy = LLM_RETRY_POLICY
        
        assert policy.max_attempts == 4
        assert policy.base_delay == 2.0
        assert policy.max_delay == 120.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL_JITTER
        assert policy.timeout_seconds == 300.0
        assert policy.circuit_breaker_enabled == True
        assert policy.circuit_breaker_failure_threshold == 3
        assert policy.circuit_breaker_recovery_timeout == 180.0
        
        # Test retryable exceptions
        import httpx
        assert TimeoutError in policy.retryable_exceptions
        assert httpx.TimeoutException in policy.retryable_exceptions
        assert httpx.ConnectError in policy.retryable_exceptions
        
        # Test non-retryable exceptions
        assert ValueError in policy.non_retryable_exceptions
        assert httpx.HTTPStatusError in policy.non_retryable_exceptions
    
    def test_agent_retry_policy_configuration(self):
        """Test agent retry policy has correct configuration."""
        policy = AGENT_RETRY_POLICY
        
        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL
        assert policy.circuit_breaker_enabled == False  # Agents handle their own CB
        assert policy.metrics_enabled == True
        
        # Test exceptions
        assert RuntimeError in policy.retryable_exceptions
        assert ValueError in policy.non_retryable_exceptions
        assert AttributeError in policy.non_retryable_exceptions


class TestCircuitBreakerIntegration:
    """Test circuit breaker integration with retry handler."""
    
    @patch('netra_backend.app.core.resilience.unified_retry_handler.get_unified_circuit_breaker_manager')
    def test_circuit_breaker_setup(self, mock_manager):
        """Test circuit breaker setup when enabled."""
        mock_cb = Mock()
        mock_manager.return_value.get_circuit_breaker.return_value = mock_cb
        
        config = RetryConfig(circuit_breaker_enabled=True)
        handler = UnifiedRetryHandler("test", config)
        
        # Verify circuit breaker was configured
        assert handler._circuit_breaker == mock_cb
        mock_manager.return_value.get_circuit_breaker.assert_called_once()
    
    def test_circuit_breaker_disabled_by_default(self):
        """Test circuit breaker is disabled by default."""
        handler = UnifiedRetryHandler("test")
        assert handler._circuit_breaker is None
    
    def test_execute_with_circuit_breaker_open(self):
        """Test execution when circuit breaker is open."""
        config = RetryConfig(circuit_breaker_enabled=True)
        handler = UnifiedRetryHandler("test", config)
        
        # Mock circuit breaker that is open
        mock_cb = Mock()
        mock_cb.can_execute.return_value = False
        handler._circuit_breaker = mock_cb
        
        def failing_func():
            raise Exception("Should not be called")
        
        result = handler.execute_with_retry(failing_func)
        
        assert result.success == False
        assert "Circuit breaker is open" in str(result.final_exception)
        assert len(result.attempts) == 0
    
    @pytest.mark.asyncio
    async def test_execute_async_with_circuit_breaker_open(self):
        """Test async execution when circuit breaker is open."""
        config = RetryConfig(circuit_breaker_enabled=True)
        handler = UnifiedRetryHandler("test", config)
        
        # Mock circuit breaker that is open
        mock_cb = AsyncMock()
        mock_cb.can_execute_async.return_value = False
        handler._circuit_breaker = mock_cb
        
        async def failing_func():
            raise Exception("Should not be called")
        
        result = await handler.execute_with_retry_async(failing_func)
        
        assert result.success == False
        assert "Circuit breaker is open" in str(result.final_exception)
        assert len(result.attempts) == 0
    
    def test_circuit_breaker_success_recording(self):
        """Test circuit breaker records success."""
        config = RetryConfig(circuit_breaker_enabled=True, max_attempts=1)
        handler = UnifiedRetryHandler("test", config)
        
        # Mock circuit breaker
        mock_cb = Mock()
        mock_cb.can_execute.return_value = True
        handler._circuit_breaker = mock_cb
        
        def success_func():
            return "success"
        
        result = handler.execute_with_retry(success_func)
        
        assert result.success == True
        mock_cb.record_success.assert_called_once()
    
    def test_circuit_breaker_failure_recording(self):
        """Test circuit breaker records failures."""
        config = RetryConfig(circuit_breaker_enabled=True, max_attempts=1)
        handler = UnifiedRetryHandler("test", config)
        
        # Mock circuit breaker
        mock_cb = Mock()
        mock_cb.can_execute.return_value = True
        handler._circuit_breaker = mock_cb
        
        def failing_func():
            raise ValueError("Test error")
        
        result = handler.execute_with_retry(failing_func)
        
        assert result.success == False
        mock_cb.record_failure.assert_called_once_with("ValueError")


class TestContextManagerSupport:
    """Test context manager functionality."""
    
    def test_retry_context_sync(self):
        """Test sync context manager."""
        handler = UnifiedRetryHandler("test", RetryConfig(max_attempts=1))
        
        def success_func(x, y):
            return x + y
        
        with handler.retry_context(success_func, 1, 2) as ctx:
            result = ctx.execute()
            assert result == 3
            assert ctx.result.success == True
    
    @pytest.mark.asyncio
    async def test_retry_context_async(self):
        """Test async context manager."""
        handler = UnifiedRetryHandler("test", RetryConfig(max_attempts=1))
        
        async def success_func(x, y):
            return x + y
        
        async with handler.retry_context(success_func, 1, 2) as ctx:
            result = await ctx.execute_async()
            assert result == 3
            assert ctx.result.success == True
    
    def test_retry_context_failure(self):
        """Test context manager with failure."""
        handler = UnifiedRetryHandler("test", RetryConfig(max_attempts=1))
        
        def failing_func():
            raise ValueError("Test error")
        
        with handler.retry_context(failing_func) as ctx:
            with pytest.raises(ValueError):
                ctx.execute()
            assert ctx.result.success == False


class TestDecoratorPatterns:
    """Test enhanced decorator functionality."""
    
    def test_database_retry_decorator(self):
        """Test database retry decorator."""
        call_count = 0
        
        @database_retry(max_attempts=3)
        def flaky_db_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                import psycopg2
                raise psycopg2.OperationalError("Connection failed")
            return "success"
        
        result = flaky_db_operation()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_llm_retry_decorator_async(self):
        """Test LLM retry decorator with async function."""
        call_count = 0
        
        @llm_retry(max_attempts=3)
        async def flaky_llm_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("LLM timeout")
            return "llm_response"
        
        result = await flaky_llm_call()
        assert result == "llm_response"
        assert call_count == 2
    
    def test_agent_retry_decorator_custom_params(self):
        """Test agent retry decorator with custom parameters."""
        call_count = 0
        
        @agent_retry(max_attempts=5, base_delay=0.1)
        def flaky_agent_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("Agent runtime error")
            return "agent_result"
        
        result = flaky_agent_operation()
        assert result == "agent_result"
        assert call_count == 3
    
    def test_api_retry_decorator(self):
        """Test API retry decorator."""
        call_count = 0
        
        @api_retry(max_attempts=2)
        def flaky_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                import urllib.error
                raise urllib.error.URLError("Network error")
            return "api_response"
        
        result = flaky_api_call()
        assert result == "api_response"
        assert call_count == 2


class TestCallableHandlerInterface:
    """Test callable handler interface."""
    
    def test_handler_as_decorator(self):
        """Test using handler as decorator."""
        handler = UnifiedRetryHandler("test", RetryConfig(max_attempts=3))
        call_count = 0
        
        @handler
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "success"
        
        result = flaky_function()
        assert result == "success"
        assert call_count == 2
    
    @pytest.mark.asyncio
    async def test_handler_as_async_decorator(self):
        """Test using handler as async decorator."""
        handler = UnifiedRetryHandler("test", RetryConfig(max_attempts=3))
        call_count = 0
        
        @handler
        async def flaky_async_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Network error")
            return "async_success"
        
        result = await flaky_async_function()
        assert result == "async_success"
        assert call_count == 2


class TestConvenienceFunctions:
    """Test convenience functions with domain policies."""
    
    def test_retry_database_operation_function(self):
        """Test retry_database_operation function."""
        call_count = 0
        
        def flaky_db_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                import psycopg2
                raise psycopg2.OperationalError("DB connection failed")
            return "db_success"
        
        result = retry_database_operation(flaky_db_func)
        assert result == "db_success"
        assert call_count == 2
    
    def test_retry_llm_request_function(self):
        """Test retry_llm_request function."""
        call_count = 0
        
        def flaky_llm_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("LLM timeout")
            return "llm_success"
        
        result = retry_llm_request(flaky_llm_func)
        assert result == "llm_success"
        assert call_count == 2
    
    def test_retry_agent_operation_function(self):
        """Test retry_agent_operation function."""
        call_count = 0
        
        def flaky_agent_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RuntimeError("Agent error")
            return "agent_success"
        
        result = retry_agent_operation(flaky_agent_func)
        assert result == "agent_success"
        assert call_count == 2
    
    def test_retry_websocket_operation_function(self):
        """Test retry_websocket_operation function."""
        call_count = 0
        
        def flaky_ws_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("WebSocket error")
            return "ws_success"
        
        result = retry_websocket_operation(flaky_ws_func)
        assert result == "ws_success"
        assert call_count == 2
    
    def test_retry_file_operation_function(self):
        """Test retry_file_operation function."""
        call_count = 0
        
        def flaky_file_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise OSError("File system error")
            return "file_success"
        
        result = retry_file_operation(flaky_file_func)
        assert result == "file_success"
        assert call_count == 2


class TestGlobalHandlers:
    """Test pre-configured global handlers."""
    
    def test_database_retry_handler(self):
        """Test global database retry handler."""
        assert database_retry_handler.service_name == "database"
        assert database_retry_handler.config.max_attempts == 5
        assert database_retry_handler.config.circuit_breaker_enabled == True
    
    def test_llm_retry_handler(self):
        """Test global LLM retry handler."""
        assert llm_retry_handler.service_name == "llm"
        assert llm_retry_handler.config.max_attempts == 4
        assert llm_retry_handler.config.timeout_seconds == 300.0
    
    def test_agent_retry_handler(self):
        """Test global agent retry handler."""
        assert agent_retry_handler.service_name == "agent"
        assert agent_retry_handler.config.max_attempts == 3
        assert agent_retry_handler.config.circuit_breaker_enabled == False
    
    def test_api_retry_handler(self):
        """Test global API retry handler."""
        assert api_retry_handler.service_name == "api"
        assert api_retry_handler.config.circuit_breaker_enabled == True


class TestEnhancedConfiguration:
    """Test enhanced configuration options."""
    
    def test_with_circuit_breaker_method(self):
        """Test with_circuit_breaker configuration method."""
        handler = UnifiedRetryHandler("test")
        enhanced_handler = handler.with_circuit_breaker(
            enabled=True, 
            failure_threshold=10, 
            recovery_timeout=60.0
        )
        
        assert enhanced_handler.config.circuit_breaker_enabled == True
        assert enhanced_handler.config.circuit_breaker_failure_threshold == 10
        assert enhanced_handler.config.circuit_breaker_recovery_timeout == 60.0
    
    def test_get_circuit_breaker_status(self):
        """Test getting circuit breaker status."""
        handler = UnifiedRetryHandler("test")
        
        # Without circuit breaker
        assert handler.get_circuit_breaker_status() is None
        
        # With circuit breaker (mocked)
        mock_cb = Mock()
        mock_cb.get_status.return_value = {"state": "closed", "failures": 0}
        handler._circuit_breaker = mock_cb
        
        status = handler.get_circuit_breaker_status()
        assert status["state"] == "closed"
        assert status["failures"] == 0


class TestErrorClassification:
    """Test enhanced error classification for different domains."""
    
    def test_database_error_classification(self):
        """Test database-specific error handling."""
        handler = UnifiedRetryHandler("database", DATABASE_RETRY_POLICY)
        
        # Test retryable database errors
        import psycopg2
        retryable_error = psycopg2.OperationalError("Connection failed")
        decision = handler._should_retry(retryable_error, 1)
        assert decision == RetryDecision.RETRY
        
        # Test non-retryable database errors
        non_retryable_error = psycopg2.ProgrammingError("Syntax error")
        decision = handler._should_retry(non_retryable_error, 1)
        assert decision == RetryDecision.STOP
    
    def test_llm_error_classification(self):
        """Test LLM-specific error handling."""
        handler = UnifiedRetryHandler("llm", LLM_RETRY_POLICY)
        
        # Test retryable LLM errors
        retryable_error = TimeoutError("LLM timeout")
        decision = handler._should_retry(retryable_error, 1)
        assert decision == RetryDecision.RETRY
        
        # Test non-retryable LLM errors
        non_retryable_error = ValueError("Invalid prompt")
        decision = handler._should_retry(non_retryable_error, 1)
        assert decision == RetryDecision.STOP


if __name__ == "__main__":
    pytest.main([__file__])