"""
Comprehensive tests for ErrorRecoveryManager - production-critical error recovery system.

Tests cover retry strategies, compensation actions, circuit breakers, rollback mechanisms,
and comprehensive recovery workflows for different operation types.
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from netra_backend.app.core.error_recovery import (
    ErrorRecoveryManager, RecoveryExecutor, RecoveryContext, RecoveryResult,
    RetryStrategy, CompensationAction, DatabaseRollbackAction, CacheInvalidationAction,
    ErrorRecoveryCircuitBreaker, RecoveryAction, OperationType,
    recovery_manager, recovery_executor
)
from netra_backend.app.core.error_codes import ErrorSeverity


class TestRecoveryContext:
    """Test RecoveryContext data class and functionality."""
    
    def test_recovery_context_creation(self):
        """Test RecoveryContext initialization with required fields."""
        error = ValueError("Test error")
        context = RecoveryContext(
            operation_id="test-op-123",
            operation_type=OperationType.DATABASE_WRITE,
            error=error,
            severity=ErrorSeverity.MEDIUM
        )
        
        assert context.operation_id == "test-op-123"
        assert context.operation_type == OperationType.DATABASE_WRITE
        assert context.error is error
        assert context.severity == ErrorSeverity.MEDIUM
        assert context.retry_count == 0
        assert context.max_retries == 3
        assert isinstance(context.started_at, datetime)
        assert isinstance(context.metadata, dict)
        
    def test_recovery_context_elapsed_time(self):
        """Test elapsed time calculation in RecoveryContext."""
        # Create context with specific start time
        start_time = datetime.now() - timedelta(seconds=10)
        context = RecoveryContext(
            operation_id="test-op",
            operation_type=OperationType.LLM_REQUEST,
            error=Exception("Test"),
            severity=ErrorSeverity.LOW
        )
        context.started_at = start_time
        
        elapsed = context.elapsed_time
        assert isinstance(elapsed, timedelta)
        assert elapsed.total_seconds() >= 10
        
    def test_recovery_context_with_custom_values(self):
        """Test RecoveryContext with custom retry and metadata values."""
        metadata = {"request_id": "req-456", "user_id": "user-789"}
        context = RecoveryContext(
            operation_id="custom-op",
            operation_type=OperationType.EXTERNAL_API,
            error=ConnectionError("Network issue"),
            severity=ErrorSeverity.HIGH,
            retry_count=2,
            max_retries=5,
            metadata=metadata
        )
        
        assert context.retry_count == 2
        assert context.max_retries == 5
        assert context.metadata == metadata


class TestRetryStrategy:
    """Test retry strategy logic and configuration."""
    
    def test_retry_strategy_initialization(self):
        """Test RetryStrategy initialization with defaults and custom values."""
        # Default strategy
        default_strategy = RetryStrategy()
        assert default_strategy.max_retries == 3
        assert default_strategy.base_delay == 1.0
        
        # Custom strategy
        custom_strategy = RetryStrategy(max_retries=5, base_delay=2.0)
        assert custom_strategy.max_retries == 5
        assert custom_strategy.base_delay == 2.0
        
    def test_should_retry_within_limit(self):
        """Test retry decision when within retry limit."""
        strategy = RetryStrategy(max_retries=3)
        
        context = RecoveryContext(
            operation_id="test-op",
            operation_type=OperationType.DATABASE_READ,
            error=ConnectionError("Temporary failure"),
            severity=ErrorSeverity.LOW,
            retry_count=1
        )
        
        assert strategy.should_retry(context) is True
        
    def test_should_not_retry_over_limit(self):
        """Test retry decision when retry limit exceeded."""
        strategy = RetryStrategy(max_retries=2)
        
        context = RecoveryContext(
            operation_id="test-op",
            operation_type=OperationType.DATABASE_READ,
            error=ConnectionError("Persistent failure"),
            severity=ErrorSeverity.LOW,
            retry_count=3  # Over limit
        )
        
        assert strategy.should_retry(context) is False
        
    def test_should_not_retry_value_error(self):
        """Test that ValueError is not retryable."""
        strategy = RetryStrategy()
        
        context = RecoveryContext(
            operation_id="test-op",
            operation_type=OperationType.LLM_REQUEST,
            error=ValueError("Invalid input"),
            severity=ErrorSeverity.LOW,
            retry_count=0
        )
        
        assert strategy.should_retry(context) is False
        
    def test_should_not_retry_critical_error(self):
        """Test that critical errors are not retryable."""
        strategy = RetryStrategy()
        
        context = RecoveryContext(
            operation_id="test-op",
            operation_type=OperationType.DATABASE_WRITE,
            error=Exception("Critical system failure"),
            severity=ErrorSeverity.CRITICAL,
            retry_count=0
        )
        
        assert strategy.should_retry(context) is False
        
    def test_exponential_backoff_delay(self):
        """Test exponential backoff delay calculation."""
        strategy = RetryStrategy(base_delay=1.0)
        
        assert strategy.get_delay(0) == 1.0  # 1.0 * 2^0
        assert strategy.get_delay(1) == 2.0  # 1.0 * 2^1
        assert strategy.get_delay(2) == 4.0  # 1.0 * 2^2
        assert strategy.get_delay(3) == 8.0  # 1.0 * 2^3
        
    def test_maximum_delay_cap(self):
        """Test that delay is capped at 30 seconds."""
        strategy = RetryStrategy(base_delay=1.0)
        
        # High retry count should be capped at 30 seconds
        assert strategy.get_delay(10) == 30.0


class TestDatabaseRollbackAction:
    """Test database rollback compensation action."""
    
    @pytest.mark.asyncio
    async def test_database_rollback_success(self):
        """Test successful database rollback execution."""
        mock_transaction_manager = Mock()
        mock_transaction_manager.rollback_operation = AsyncMock(return_value=True)
        
        action = DatabaseRollbackAction(mock_transaction_manager)
        
        context = RecoveryContext(
            operation_id="db-op-123",
            operation_type=OperationType.DATABASE_WRITE,
            error=Exception("DB error"),
            severity=ErrorSeverity.MEDIUM
        )
        
        result = await action.execute(context)
        
        assert result is True
        mock_transaction_manager.rollback_operation.assert_called_once_with("db-op-123")
        
    @pytest.mark.asyncio
    async def test_database_rollback_failure(self):
        """Test database rollback failure handling."""
        mock_transaction_manager = Mock()
        mock_transaction_manager.rollback_operation = AsyncMock(
            side_effect=Exception("Rollback failed")
        )
        
        action = DatabaseRollbackAction(mock_transaction_manager)
        
        context = RecoveryContext(
            operation_id="db-op-456",
            operation_type=OperationType.DATABASE_WRITE,
            error=Exception("DB error"),
            severity=ErrorSeverity.MEDIUM
        )
        
        result = await action.execute(context)
        
        assert result is False
        
    def test_database_rollback_can_compensate(self):
        """Test database rollback applicability check."""
        action = DatabaseRollbackAction(Mock())
        
        # Should apply to database operations
        db_write_context = RecoveryContext(
            operation_id="test",
            operation_type=OperationType.DATABASE_WRITE,
            error=Exception(),
            severity=ErrorSeverity.MEDIUM
        )
        assert action.can_compensate(db_write_context) is True
        
        db_read_context = RecoveryContext(
            operation_id="test",
            operation_type=OperationType.DATABASE_READ,
            error=Exception(),
            severity=ErrorSeverity.MEDIUM
        )
        assert action.can_compensate(db_read_context) is True
        
        # Should not apply to non-database operations
        llm_context = RecoveryContext(
            operation_id="test",
            operation_type=OperationType.LLM_REQUEST,
            error=Exception(),
            severity=ErrorSeverity.MEDIUM
        )
        assert action.can_compensate(llm_context) is False


class TestCacheInvalidationAction:
    """Test cache invalidation compensation action."""
    
    @pytest.mark.asyncio
    async def test_cache_invalidation_success(self):
        """Test successful cache invalidation execution."""
        mock_cache_manager = Mock()
        mock_cache_manager.invalidate_keys = AsyncMock()
        
        action = CacheInvalidationAction(mock_cache_manager)
        
        context = RecoveryContext(
            operation_id="cache-op-123",
            operation_type=OperationType.CACHE_OPERATION,
            error=Exception("Cache error"),
            severity=ErrorSeverity.LOW,
            metadata={"cache_keys": ["key1", "key2", "key3"]}
        )
        
        result = await action.execute(context)
        
        assert result is True
        mock_cache_manager.invalidate_keys.assert_called_once_with(["key1", "key2", "key3"])
        
    @pytest.mark.asyncio
    async def test_cache_invalidation_no_keys(self):
        """Test cache invalidation with no cache keys."""
        mock_cache_manager = Mock()
        
        action = CacheInvalidationAction(mock_cache_manager)
        
        context = RecoveryContext(
            operation_id="cache-op-456",
            operation_type=OperationType.CACHE_OPERATION,
            error=Exception("Cache error"),
            severity=ErrorSeverity.LOW,
            metadata={}  # No cache_keys
        )
        
        result = await action.execute(context)
        
        assert result is True  # Should succeed with no keys
        
    @pytest.mark.asyncio
    async def test_cache_invalidation_failure(self):
        """Test cache invalidation failure handling."""
        mock_cache_manager = Mock()
        mock_cache_manager.invalidate_keys = AsyncMock(
            side_effect=Exception("Cache service unavailable")
        )
        
        action = CacheInvalidationAction(mock_cache_manager)
        
        context = RecoveryContext(
            operation_id="cache-op-789",
            operation_type=OperationType.CACHE_OPERATION,
            error=Exception("Cache error"),
            severity=ErrorSeverity.LOW,
            metadata={"cache_keys": ["key1"]}
        )
        
        result = await action.execute(context)
        
        assert result is False
        
    def test_cache_invalidation_can_compensate(self):
        """Test cache invalidation applicability check."""
        action = CacheInvalidationAction(Mock())
        
        # Should apply when cache_keys present
        context_with_keys = RecoveryContext(
            operation_id="test",
            operation_type=OperationType.CACHE_OPERATION,
            error=Exception(),
            severity=ErrorSeverity.LOW,
            metadata={"cache_keys": ["key1"]}
        )
        assert action.can_compensate(context_with_keys) is True
        
        # Should not apply when no cache_keys
        context_without_keys = RecoveryContext(
            operation_id="test",
            operation_type=OperationType.CACHE_OPERATION,
            error=Exception(),
            severity=ErrorSeverity.LOW,
            metadata={}
        )
        assert action.can_compensate(context_without_keys) is False


class TestErrorRecoveryCircuitBreaker:
    """Test specialized error recovery circuit breaker."""
    
    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initialization with defaults."""
        circuit = ErrorRecoveryCircuitBreaker()
        
        assert circuit.config.name == "error_recovery_circuit"
        assert circuit.config.failure_threshold == 5
        assert circuit.config.recovery_timeout == 60.0
        
    def test_circuit_breaker_custom_config(self):
        """Test circuit breaker with custom configuration."""
        circuit = ErrorRecoveryCircuitBreaker(
            failure_threshold=3,
            timeout=30,
            name="custom_recovery"
        )
        
        assert circuit.config.name == "custom_recovery"
        assert circuit.config.failure_threshold == 3
        assert circuit.config.recovery_timeout == 30.0
        
    def test_should_allow_request(self):
        """Test synchronous request allowance check."""
        circuit = ErrorRecoveryCircuitBreaker()
        
        # Initially should allow requests
        assert circuit.should_allow_request() is True
        
    def test_record_success_and_failure(self):
        """Test recording success and failure operations."""
        circuit = ErrorRecoveryCircuitBreaker()
        
        # Should not raise exceptions
        circuit.record_success()
        circuit.record_failure("TestError")
        circuit.record_failure()  # Default error type


class TestErrorRecoveryManager:
    """Test central error recovery manager."""
    
    def test_error_recovery_manager_initialization(self):
        """Test ErrorRecoveryManager initialization."""
        manager = ErrorRecoveryManager()
        
        assert isinstance(manager.compensation_actions, list)
        assert isinstance(manager.retry_strategies, dict)
        assert isinstance(manager.circuit_breakers, dict)
        assert isinstance(manager.active_operations, dict)
        
        # Check default retry strategies are set up
        assert OperationType.DATABASE_WRITE in manager.retry_strategies
        assert OperationType.LLM_REQUEST in manager.retry_strategies
        assert OperationType.EXTERNAL_API in manager.retry_strategies
        
    def test_default_retry_strategies(self):
        """Test default retry strategies configuration."""
        manager = ErrorRecoveryManager()
        
        # Database operations
        db_write_strategy = manager.retry_strategies[OperationType.DATABASE_WRITE]
        assert db_write_strategy.max_retries == 2
        assert db_write_strategy.base_delay == 0.5
        
        db_read_strategy = manager.retry_strategies[OperationType.DATABASE_READ]
        assert db_read_strategy.max_retries == 3
        assert db_read_strategy.base_delay == 0.1
        
        # Service operations
        llm_strategy = manager.retry_strategies[OperationType.LLM_REQUEST]
        assert llm_strategy.max_retries == 3
        assert llm_strategy.base_delay == 2.0
        
        external_api_strategy = manager.retry_strategies[OperationType.EXTERNAL_API]
        assert external_api_strategy.max_retries == 3
        assert external_api_strategy.base_delay == 1.0
        
    def test_register_compensation_action(self):
        """Test registering compensation actions."""
        manager = ErrorRecoveryManager()
        
        mock_action = Mock(spec=CompensationAction)
        manager.register_compensation_action(mock_action)
        
        assert mock_action in manager.compensation_actions
        assert len(manager.compensation_actions) == 1
        
    def test_get_circuit_breaker_creates_new(self):
        """Test circuit breaker creation for new service."""
        manager = ErrorRecoveryManager()
        
        circuit = manager.get_circuit_breaker("test-service")
        
        assert circuit is not None
        assert isinstance(circuit, ErrorRecoveryCircuitBreaker)
        assert "test-service" in manager.circuit_breakers
        assert manager.circuit_breakers["test-service"] is circuit
        
    def test_get_circuit_breaker_reuses_existing(self):
        """Test circuit breaker reuse for existing service."""
        manager = ErrorRecoveryManager()
        
        circuit1 = manager.get_circuit_breaker("existing-service")
        circuit2 = manager.get_circuit_breaker("existing-service")
        
        assert circuit1 is circuit2


class TestRecoveryExecutor:
    """Test recovery execution logic and workflows."""
    
    def test_recovery_executor_initialization(self):
        """Test RecoveryExecutor initialization."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        assert executor.recovery_manager is manager
        
    @pytest.mark.asyncio
    async def test_attempt_recovery_circuit_break(self):
        """Test recovery attempt blocked by circuit breaker."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Mock circuit breaker to deny requests
        mock_circuit = Mock()
        mock_circuit.should_allow_request.return_value = False
        
        with patch.object(executor, '_get_circuit_breaker', return_value=mock_circuit):
            context = RecoveryContext(
                operation_id="test-op",
                operation_type=OperationType.EXTERNAL_API,
                error=Exception("Test error"),
                severity=ErrorSeverity.MEDIUM
            )
            
            result = await executor.attempt_recovery(context)
            
            assert result.success is False
            assert result.action_taken == RecoveryAction.CIRCUIT_BREAK
            assert result.circuit_broken is True
            
    @pytest.mark.asyncio
    async def test_attempt_recovery_retry(self):
        """Test recovery attempt with retry action."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Mock circuit breaker to allow requests
        mock_circuit = Mock()
        mock_circuit.should_allow_request.return_value = True
        
        with patch.object(executor, '_get_circuit_breaker', return_value=mock_circuit):
            with patch('asyncio.sleep') as mock_sleep:  # Speed up test
                context = RecoveryContext(
                    operation_id="retry-test",
                    operation_type=OperationType.LLM_REQUEST,
                    error=ConnectionError("Temporary failure"),
                    severity=ErrorSeverity.MEDIUM,
                    retry_count=1
                )
                
                result = await executor.attempt_recovery(context)
                
                assert result.success is True
                assert result.action_taken == RecoveryAction.RETRY
                mock_sleep.assert_called_once()
                
    @pytest.mark.asyncio
    async def test_attempt_recovery_compensation(self):
        """Test recovery attempt with compensation action."""
        manager = ErrorRecoveryManager()
        
        # Register mock compensation action
        mock_action = Mock(spec=CompensationAction)
        mock_action.can_compensate.return_value = True
        mock_action.execute = AsyncMock(return_value=True)
        manager.register_compensation_action(mock_action)
        
        executor = RecoveryExecutor(manager)
        
        # Mock circuit breaker to allow requests
        mock_circuit = Mock()
        mock_circuit.should_allow_request.return_value = True
        
        with patch.object(executor, '_get_circuit_breaker', return_value=mock_circuit):
            context = RecoveryContext(
                operation_id="compensate-test",
                operation_type=OperationType.DATABASE_WRITE,
                error=Exception("DB constraint violation"),
                severity=ErrorSeverity.CRITICAL,  # Critical errors not retried
                retry_count=0
            )
            
            result = await executor.attempt_recovery(context)
            
            assert result.success is True
            assert result.action_taken == RecoveryAction.COMPENSATE
            assert result.compensation_required is True
            mock_action.execute.assert_called_once_with(context)
            
    @pytest.mark.asyncio
    async def test_attempt_recovery_abort(self):
        """Test recovery attempt that results in abort."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Mock circuit breaker to allow requests
        mock_circuit = Mock()
        mock_circuit.should_allow_request.return_value = True
        
        with patch.object(executor, '_get_circuit_breaker', return_value=mock_circuit):
            context = RecoveryContext(
                operation_id="abort-test",
                operation_type=OperationType.FILE_OPERATION,
                error=ValueError("Invalid file format"),  # Not retryable
                severity=ErrorSeverity.HIGH,
                retry_count=0
            )
            
            result = await executor.attempt_recovery(context)
            
            assert result.success is False
            assert result.action_taken == RecoveryAction.ABORT
            assert result.error_message is not None
            
    @pytest.mark.asyncio
    async def test_execute_compensation_multiple_actions(self):
        """Test executing multiple compensation actions."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Register multiple compensation actions
        action1 = Mock(spec=CompensationAction)
        action1.can_compensate.return_value = True
        action1.execute = AsyncMock(return_value=True)
        
        action2 = Mock(spec=CompensationAction)
        action2.can_compensate.return_value = True
        action2.execute = AsyncMock(return_value=True)
        
        action3 = Mock(spec=CompensationAction)
        action3.can_compensate.return_value = False  # Should not be executed
        
        manager.register_compensation_action(action1)
        manager.register_compensation_action(action2)
        manager.register_compensation_action(action3)
        
        context = RecoveryContext(
            operation_id="multi-comp-test",
            operation_type=OperationType.DATABASE_WRITE,
            error=Exception("Test error"),
            severity=ErrorSeverity.MEDIUM
        )
        
        result = await executor._execute_compensation(context)
        
        assert result is True
        action1.execute.assert_called_once_with(context)
        action2.execute.assert_called_once_with(context)
        action3.execute.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_execute_compensation_partial_failure(self):
        """Test compensation execution with partial failures."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Register actions with mixed success
        successful_action = Mock(spec=CompensationAction)
        successful_action.can_compensate.return_value = True
        successful_action.execute = AsyncMock(return_value=True)
        
        failing_action = Mock(spec=CompensationAction)
        failing_action.can_compensate.return_value = True
        failing_action.execute = AsyncMock(return_value=False)
        
        manager.register_compensation_action(successful_action)
        manager.register_compensation_action(failing_action)
        
        context = RecoveryContext(
            operation_id="partial-comp-test",
            operation_type=OperationType.CACHE_OPERATION,
            error=Exception("Test error"),
            severity=ErrorSeverity.MEDIUM
        )
        
        result = await executor._execute_compensation(context)
        
        assert result is False  # Overall failure due to one failing action
        successful_action.execute.assert_called_once_with(context)
        failing_action.execute.assert_called_once_with(context)


class TestRecoveryResult:
    """Test RecoveryResult data class."""
    
    def test_recovery_result_creation(self):
        """Test RecoveryResult creation with various configurations."""
        # Successful retry result
        retry_result = RecoveryResult(
            success=True,
            action_taken=RecoveryAction.RETRY
        )
        
        assert retry_result.success is True
        assert retry_result.action_taken == RecoveryAction.RETRY
        assert retry_result.result_data is None
        assert retry_result.error_message is None
        assert retry_result.compensation_required is False
        assert retry_result.circuit_broken is False
        
        # Failed result with error
        failed_result = RecoveryResult(
            success=False,
            action_taken=RecoveryAction.ABORT,
            error_message="Recovery impossible"
        )
        
        assert failed_result.success is False
        assert failed_result.action_taken == RecoveryAction.ABORT
        assert failed_result.error_message == "Recovery impossible"
        
        # Compensation result
        compensation_result = RecoveryResult(
            success=True,
            action_taken=RecoveryAction.COMPENSATE,
            result_data={"rollback_id": "rb-123"},
            compensation_required=True
        )
        
        assert compensation_result.success is True
        assert compensation_result.action_taken == RecoveryAction.COMPENSATE
        assert compensation_result.result_data == {"rollback_id": "rb-123"}
        assert compensation_result.compensation_required is True


@pytest.mark.integration
class TestErrorRecoveryIntegration:
    """Integration tests for complete error recovery workflows."""
    
    @pytest.mark.asyncio
    async def test_database_error_recovery_workflow(self):
        """Test complete database error recovery workflow."""
        # Set up recovery manager with database rollback action
        manager = ErrorRecoveryManager()
        
        mock_transaction_manager = Mock()
        mock_transaction_manager.rollback_operation = AsyncMock(return_value=True)
        
        rollback_action = DatabaseRollbackAction(mock_transaction_manager)
        manager.register_compensation_action(rollback_action)
        
        executor = RecoveryExecutor(manager)
        
        # Create database error context
        context = RecoveryContext(
            operation_id="db-integration-test",
            operation_type=OperationType.DATABASE_WRITE,
            error=Exception("Constraint violation"),
            severity=ErrorSeverity.HIGH,  # High severity to skip retry
            retry_count=0,
            metadata={"transaction_id": "tx-456"}
        )
        
        result = await executor.attempt_recovery(context)
        
        # Should succeed with compensation
        assert result.success is True
        assert result.action_taken == RecoveryAction.COMPENSATE
        assert result.compensation_required is True
        
        # Verify rollback was called
        mock_transaction_manager.rollback_operation.assert_called_once_with(
            "db-integration-test"
        )
        
    @pytest.mark.asyncio
    async def test_llm_request_retry_workflow(self):
        """Test LLM request retry recovery workflow."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Mock successful circuit breaker
        mock_circuit = Mock()
        mock_circuit.should_allow_request.return_value = True
        
        with patch.object(executor, '_get_circuit_breaker', return_value=mock_circuit):
            with patch('asyncio.sleep') as mock_sleep:
                context = RecoveryContext(
                    operation_id="llm-integration-test",
                    operation_type=OperationType.LLM_REQUEST,
                    error=ConnectionError("API timeout"),
                    severity=ErrorSeverity.MEDIUM,
                    retry_count=1,
                    metadata={"model": "gpt-4", "prompt_tokens": 500}
                )
                
                result = await executor.attempt_recovery(context)
                
                # Should retry
                assert result.success is True
                assert result.action_taken == RecoveryAction.RETRY
                
                # Verify exponential backoff delay
                expected_delay = manager.retry_strategies[OperationType.LLM_REQUEST].get_delay(1)
                mock_sleep.assert_called_once_with(expected_delay)
                
    @pytest.mark.asyncio
    async def test_cache_error_recovery_workflow(self):
        """Test cache error recovery with invalidation workflow."""
        manager = ErrorRecoveryManager()
        
        # Set up cache invalidation action
        mock_cache_manager = Mock()
        mock_cache_manager.invalidate_keys = AsyncMock()
        
        cache_action = CacheInvalidationAction(mock_cache_manager)
        manager.register_compensation_action(cache_action)
        
        executor = RecoveryExecutor(manager)
        
        context = RecoveryContext(
            operation_id="cache-integration-test",
            operation_type=OperationType.CACHE_OPERATION,
            error=Exception("Cache corruption"),
            severity=ErrorSeverity.CRITICAL,  # Skip retry
            retry_count=0,
            metadata={
                "cache_keys": ["user:123:profile", "user:123:preferences"],
                "cache_region": "us-east-1"
            }
        )
        
        result = await executor.attempt_recovery(context)
        
        # Should succeed with compensation
        assert result.success is True
        assert result.action_taken == RecoveryAction.COMPENSATE
        
        # Verify cache invalidation
        mock_cache_manager.invalidate_keys.assert_called_once_with([
            "user:123:profile", "user:123:preferences"
        ])


class TestGlobalInstances:
    """Test global error recovery instances."""
    
    def test_global_recovery_manager_exists(self):
        """Test global recovery manager instance."""
        assert recovery_manager is not None
        assert isinstance(recovery_manager, ErrorRecoveryManager)
        
    def test_global_recovery_executor_exists(self):
        """Test global recovery executor instance."""
        assert recovery_executor is not None
        assert isinstance(recovery_executor, RecoveryExecutor)
        assert recovery_executor.recovery_manager is recovery_manager
        
    def test_global_instances_consistency(self):
        """Test global instances are consistently related."""
        # Executor should use the global recovery manager
        assert recovery_executor.recovery_manager is recovery_manager
        
        # Importing again should give same instances
        from netra_backend.app.core.error_recovery import (
            recovery_manager as rm2,
            recovery_executor as re2
        )
        
        assert recovery_manager is rm2
        assert recovery_executor is re2


class TestRecoveryActionEnums:
    """Test recovery action and operation type enums."""
    
    def test_recovery_action_values(self):
        """Test RecoveryAction enum values."""
        assert RecoveryAction.RETRY.value == "retry"
        assert RecoveryAction.ROLLBACK.value == "rollback"
        assert RecoveryAction.COMPENSATE.value == "compensate"
        assert RecoveryAction.FALLBACK.value == "fallback"
        assert RecoveryAction.ABORT.value == "abort"
        assert RecoveryAction.CIRCUIT_BREAK.value == "circuit_break"
        
    def test_operation_type_values(self):
        """Test OperationType enum values."""
        assert OperationType.DATABASE_WRITE.value == "database_write"
        assert OperationType.DATABASE_READ.value == "database_read"
        assert OperationType.LLM_REQUEST.value == "llm_request"
        assert OperationType.WEBSOCKET_SEND.value == "websocket_send"
        assert OperationType.FILE_OPERATION.value == "file_operation"
        assert OperationType.EXTERNAL_API.value == "external_api"
        assert OperationType.AGENT_EXECUTION.value == "agent_execution"
        assert OperationType.CACHE_OPERATION.value == "cache_operation"


class TestErrorHandling:
    """Test error handling in recovery operations."""
    
    @pytest.mark.asyncio
    async def test_recovery_executor_exception_handling(self):
        """Test exception handling in recovery executor."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Mock circuit breaker to raise exception
        with patch.object(executor, '_get_circuit_breaker', side_effect=Exception("Circuit error")):
            context = RecoveryContext(
                operation_id="error-test",
                operation_type=OperationType.EXTERNAL_API,
                error=Exception("Original error"),
                severity=ErrorSeverity.MEDIUM
            )
            
            result = await executor.attempt_recovery(context)
            
            # Should handle exception and return abort result
            assert result.success is False
            assert result.action_taken == RecoveryAction.ABORT
            assert "Circuit error" in result.error_message
            
    @pytest.mark.asyncio
    async def test_compensation_action_exception_handling(self):
        """Test exception handling in compensation actions."""
        manager = ErrorRecoveryManager()
        executor = RecoveryExecutor(manager)
        
        # Register compensation action that raises exception
        failing_action = Mock(spec=CompensationAction)
        failing_action.can_compensate.return_value = True
        failing_action.execute = AsyncMock(side_effect=Exception("Compensation error"))
        
        manager.register_compensation_action(failing_action)
        
        context = RecoveryContext(
            operation_id="comp-error-test",
            operation_type=OperationType.DATABASE_WRITE,
            error=Exception("Test error"),
            severity=ErrorSeverity.MEDIUM
        )
        
        result = await executor._execute_single_compensation(failing_action, context)
        
        # Should handle exception gracefully
        assert result is False