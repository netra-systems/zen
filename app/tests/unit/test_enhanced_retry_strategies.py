"""Tests for enhanced retry strategies with exponential backoff and jitter."""

import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

from app.core.enhanced_retry_strategies import (
    RetryConfig,
    BackoffStrategy,
    JitterType,
    EnhancedRetryStrategy,
    DatabaseRetryStrategy,
    ApiRetryStrategy,
    MemoryAwareRetryStrategy,
    AdaptiveRetryStrategy,
    RetryStrategyFactory,
    RetryManager,
    DEFAULT_RETRY_CONFIGS,
    retry_manager
)
from app.core.error_recovery import RecoveryContext, OperationType
from app.core.error_codes import ErrorSeverity


# Helper functions for 8-line compliance
def assert_default_config_values(config):
    """Assert default configuration values."""
    assert config.max_retries == 3
    assert config.base_delay == 1.0
    assert config.max_delay == 300.0
    assert config.backoff_strategy == BackoffStrategy.EXPONENTIAL
    assert config.jitter_type == JitterType.FULL
    assert config.timeout_seconds == 600


def assert_custom_config_values(config):
    """Assert custom configuration values."""
    assert config.max_retries == 5
    assert config.base_delay == 2.0
    assert config.backoff_strategy == BackoffStrategy.LINEAR
    assert config.jitter_type == JitterType.NONE


def assert_exponential_delays(strategy):
    """Assert exponential backoff delay calculations."""
    delay_0 = strategy.get_retry_delay(0)
    delay_1 = strategy.get_retry_delay(1)
    delay_2 = strategy.get_retry_delay(2)
    assert delay_0 == 0.5  # base_delay * 2^0
    assert delay_1 == 1.0  # base_delay * 2^1
    assert delay_2 == 2.0  # base_delay * 2^2


def assert_linear_delays(strategy):
    """Assert linear backoff delay calculations."""
    delay_0 = strategy.get_retry_delay(0)
    delay_1 = strategy.get_retry_delay(1)
    delay_2 = strategy.get_retry_delay(2)
    assert delay_0 == 0.5  # base_delay * (0 + 1)
    assert delay_1 == 1.0  # base_delay * (1 + 1)
    assert delay_2 == 1.5  # base_delay * (2 + 1)


def assert_jitter_delays_properties(delays, max_expected):
    """Assert jitter delay properties."""
    assert len(set(delays)) > 1  # All delays should be different
    assert all(delay <= max_expected for delay in delays)


def get_expected_operation_configs():
    """Get expected operation types for config validation."""
    return [
        OperationType.DATABASE_READ,
        OperationType.DATABASE_WRITE,
        OperationType.EXTERNAL_API,
        OperationType.LLM_REQUEST,
        OperationType.WEBSOCKET_SEND,
        OperationType.AGENT_EXECUTION
    ]


def assert_retry_metrics_structure(metrics):
    """Assert retry metrics have expected structure."""
    assert 'total_metrics' in metrics
    assert 'active_strategies' in metrics
    assert 'strategy_types' in metrics


def assert_retry_metrics_values(metrics):
    """Assert specific retry metrics values."""
    assert metrics['total_metrics']['database_read']['attempts'] == 1
    assert metrics['total_metrics']['external_api']['failures'] == 1


def setup_high_failure_pattern(strategy, recovery_context):
    """Setup high failure rate pattern for adaptive testing."""
    error_pattern = strategy._extract_error_pattern(recovery_context.error)
    strategy.failure_patterns[error_pattern] = 9
    strategy.success_patterns[error_pattern] = 1
    return strategy.config.max_retries


class TestRetryConfig:
    """Test retry configuration."""
    
    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        assert_default_config_values(config)
    
    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            backoff_strategy=BackoffStrategy.LINEAR,
            jitter_type=JitterType.NONE
        )
        
        assert_custom_config_values(config)


class TestDatabaseRetryStrategy:
    """Test database-specific retry strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create database retry strategy."""
        config = RetryConfig(max_retries=3, base_delay=0.5)
        return DatabaseRetryStrategy(config)
    
    @pytest.fixture
    def recovery_context(self):
        """Create recovery context for testing."""
        return RecoveryContext(
            operation_id="test_op",
            operation_type=OperationType.DATABASE_READ,
            error=ConnectionError("Connection lost"),
            severity=ErrorSeverity.HIGH,
            retry_count=0
        )
    
    def test_should_retry_connection_error(self, strategy, recovery_context):
        """Test retry on connection errors."""
        recovery_context.error = ConnectionError("Connection timeout")
        
        assert strategy.should_retry(recovery_context) is True
    
    def test_should_retry_constraint_violation(self, strategy, recovery_context):
        """Test no retry on constraint violations."""
        recovery_context.error = Exception("UNIQUE constraint failed")
        
        assert strategy.should_retry(recovery_context) is False
    
    def test_should_retry_deadlock(self, strategy, recovery_context):
        """Test retry on deadlocks."""
        recovery_context.error = Exception("deadlock detected")
        
        assert strategy.should_retry(recovery_context) is True
    
    def test_should_not_retry_max_attempts(self, strategy, recovery_context):
        """Test no retry when max attempts reached."""
        recovery_context.retry_count = 3
        
        assert strategy.should_retry(recovery_context) is False
    
    def test_should_not_retry_critical_error(self, strategy, recovery_context):
        """Test no retry on critical errors."""
        recovery_context.severity = ErrorSeverity.CRITICAL
        
        assert strategy.should_retry(recovery_context) is False
    
    def test_get_retry_delay_exponential(self, strategy):
        """Test exponential backoff delay calculation."""
        strategy.config.backoff_strategy = BackoffStrategy.EXPONENTIAL
        strategy.config.jitter_type = JitterType.NONE
        
        assert_exponential_delays(strategy)
    
    def test_get_retry_delay_linear(self, strategy):
        """Test linear backoff delay calculation."""
        strategy.config.backoff_strategy = BackoffStrategy.LINEAR
        strategy.config.jitter_type = JitterType.NONE
        
        assert_linear_delays(strategy)
    
    def test_get_retry_delay_with_jitter(self, strategy):
        """Test delay calculation with jitter."""
        strategy.config.jitter_type = JitterType.FULL
        
        delays = [strategy.get_retry_delay(1) for _ in range(10)]
        max_expected = strategy._calculate_base_delay(1)
        assert_jitter_delays_properties(delays, max_expected)
    
    def test_get_retry_delay_max_cap(self, strategy):
        """Test delay is capped at max_delay."""
        strategy.config.max_delay = 5.0
        strategy.config.jitter_type = JitterType.NONE
        
        delay = strategy.get_retry_delay(10)  # Very high retry count
        
        assert delay <= 5.0
    
    def test_record_attempt(self, strategy):
        """Test recording retry attempts."""
        operation_id = "test_op_123"
        
        strategy.record_attempt(operation_id)
        strategy.record_attempt(operation_id)
        
        assert operation_id in strategy.attempt_history
        assert len(strategy.attempt_history[operation_id]) == 2


class TestApiRetryStrategy:
    """Test API-specific retry strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create API retry strategy."""
        config = RetryConfig(max_retries=4, base_delay=1.0)
        return ApiRetryStrategy(config)
    
    @pytest.fixture
    def recovery_context(self):
        """Create recovery context for testing."""
        return RecoveryContext(
            operation_id="api_test",
            operation_type=OperationType.EXTERNAL_API,
            error=Exception("API error"),
            severity=ErrorSeverity.MEDIUM,
            retry_count=0,
            metadata={}
        )
    
    def test_should_retry_server_error(self, strategy, recovery_context):
        """Test retry on server errors."""
        recovery_context.metadata['status_code'] = 500
        
        assert strategy.should_retry(recovery_context) is True
    
    def test_should_retry_rate_limit(self, strategy, recovery_context):
        """Test retry on rate limit."""
        recovery_context.metadata['status_code'] = 429
        
        assert strategy.should_retry(recovery_context) is True
    
    def test_should_not_retry_client_error(self, strategy, recovery_context):
        """Test no retry on client errors."""
        recovery_context.metadata['status_code'] = 404
        
        assert strategy.should_retry(recovery_context) is False
    
    def test_should_retry_timeout(self, strategy, recovery_context):
        """Test retry on timeout errors."""
        recovery_context.error = TimeoutError("Request timeout")
        
        assert strategy.should_retry(recovery_context) is True
    
    def test_should_retry_connection_error(self, strategy, recovery_context):
        """Test retry on connection errors."""
        recovery_context.error = ConnectionError("Network error")
        
        assert strategy.should_retry(recovery_context) is True


class TestMemoryAwareRetryStrategy:
    """Test memory-aware retry strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create memory-aware retry strategy."""
        config = RetryConfig(max_retries=3)
        return MemoryAwareRetryStrategy(config, memory_threshold=0.8)
    
    @pytest.fixture
    def recovery_context(self):
        """Create recovery context for testing."""
        return RecoveryContext(
            operation_id="memory_test",
            operation_type=OperationType.AGENT_EXECUTION,
            error=Exception("Test error"),
            severity=ErrorSeverity.MEDIUM,
            retry_count=0
        )
    
    def test_should_retry_low_memory(self, strategy, recovery_context):
        """Test retry when memory usage is low."""
        with patch.object(strategy, '_get_memory_usage', return_value=0.5):
            assert strategy.should_retry(recovery_context) is True
    
    def test_should_not_retry_high_memory(self, strategy, recovery_context):
        """Test no retry when memory usage is high."""
        with patch.object(strategy, '_get_memory_usage', return_value=0.9):
            assert strategy.should_retry(recovery_context) is False
    
    def test_should_not_retry_memory_error(self, strategy, recovery_context):
        """Test no retry on memory errors."""
        recovery_context.error = MemoryError("Out of memory")
        
        with patch.object(strategy, '_get_memory_usage', return_value=0.5):
            assert strategy.should_retry(recovery_context) is False


class TestAdaptiveRetryStrategy:
    """Test adaptive retry strategy."""
    
    @pytest.fixture
    def strategy(self):
        """Create adaptive retry strategy."""
        config = RetryConfig(max_retries=3)
        return AdaptiveRetryStrategy(config)
    
    @pytest.fixture
    def recovery_context(self):
        """Create recovery context for testing."""
        return RecoveryContext(
            operation_id="adaptive_test",
            operation_type=OperationType.LLM_REQUEST,
            error=ConnectionError("Connection failed"),
            severity=ErrorSeverity.MEDIUM,
            retry_count=0
        )
    
    def test_extract_error_pattern(self, strategy):
        """Test error pattern extraction."""
        error = ConnectionError("timeout occurred")
        pattern = strategy._extract_error_pattern(error)
        
        assert pattern == "ConnectionError:timeout"
    
    def test_get_pattern_failure_rate_no_history(self, strategy):
        """Test failure rate with no history."""
        rate = strategy._get_pattern_failure_rate("new_pattern")
        
        assert rate == 0.5  # Default rate
    
    def test_get_pattern_failure_rate_with_history(self, strategy):
        """Test failure rate calculation with history."""
        pattern = "test_pattern"
        strategy.failure_patterns[pattern] = 8
        strategy.success_patterns[pattern] = 2
        
        rate = strategy._get_pattern_failure_rate(pattern)
        
        assert rate == 0.8  # 8 failures out of 10 total
    
    def test_record_success(self, strategy):
        """Test recording successful retry."""
        pattern = "success_pattern"
        
        strategy.record_success(pattern)
        strategy.record_success(pattern)
        
        assert strategy.success_patterns[pattern] == 2
    
    def test_record_failure(self, strategy):
        """Test recording failed retry."""
        pattern = "failure_pattern"
        
        strategy.record_failure(pattern)
        strategy.record_failure(pattern)
        
        assert strategy.failure_patterns[pattern] == 2
    
    def test_adaptive_max_retries_adjustment(self, strategy, recovery_context):
        """Test adaptive adjustment of max retries."""
        original_max = setup_high_failure_pattern(strategy, recovery_context)
        strategy.should_retry(recovery_context)
        assert strategy.config.max_retries <= original_max


class TestRetryStrategyFactory:
    """Test retry strategy factory."""
    
    def test_create_database_strategy(self):
        """Test creating database retry strategy."""
        strategy = RetryStrategyFactory.create_strategy(OperationType.DATABASE_READ)
        
        assert isinstance(strategy, DatabaseRetryStrategy)
    
    def test_create_api_strategy(self):
        """Test creating API retry strategy."""
        strategy = RetryStrategyFactory.create_strategy(OperationType.EXTERNAL_API)
        
        assert isinstance(strategy, ApiRetryStrategy)
    
    def test_create_memory_aware_strategy(self):
        """Test creating memory-aware retry strategy."""
        strategy = RetryStrategyFactory.create_strategy(OperationType.AGENT_EXECUTION)
        
        assert isinstance(strategy, MemoryAwareRetryStrategy)
    
    def test_create_adaptive_strategy(self):
        """Test creating adaptive retry strategy."""
        strategy = RetryStrategyFactory.create_strategy(OperationType.CACHE_OPERATION)
        
        assert isinstance(strategy, AdaptiveRetryStrategy)
    
    def test_create_with_custom_config(self):
        """Test creating strategy with custom config."""
        custom_config = RetryConfig(max_retries=10, base_delay=0.1)
        strategy = RetryStrategyFactory.create_strategy(
            OperationType.DATABASE_READ, custom_config
        )
        
        assert strategy.config.max_retries == 10
        assert strategy.config.base_delay == 0.1


class TestRetryManager:
    """Test retry manager."""
    
    @pytest.fixture
    def manager(self):
        """Create retry manager."""
        return RetryManager()
    
    def test_get_strategy_caching(self, manager):
        """Test strategy caching."""
        strategy1 = manager.get_strategy(OperationType.DATABASE_READ, "op1")
        strategy2 = manager.get_strategy(OperationType.DATABASE_READ, "op1")
        
        assert strategy1 is strategy2  # Same instance
    
    def test_get_strategy_different_operations(self, manager):
        """Test different strategies for different operations."""
        strategy1 = manager.get_strategy(OperationType.DATABASE_READ)
        strategy2 = manager.get_strategy(OperationType.EXTERNAL_API)
        
        assert type(strategy1) != type(strategy2)
    
    def test_record_retry_attempt_success(self, manager):
        """Test recording successful retry attempt."""
        manager.record_retry_attempt(OperationType.DATABASE_READ, True)
        
        metrics = manager.metrics[OperationType.DATABASE_READ.value]
        assert metrics['attempts'] == 1
        assert metrics['successes'] == 1
        assert metrics['failures'] == 0
    
    def test_record_retry_attempt_failure(self, manager):
        """Test recording failed retry attempt."""
        manager.record_retry_attempt(OperationType.EXTERNAL_API, False)
        
        metrics = manager.metrics[OperationType.EXTERNAL_API.value]
        assert metrics['attempts'] == 1
        assert metrics['successes'] == 0
        assert metrics['failures'] == 1
    
    def test_get_retry_metrics(self, manager):
        """Test getting retry metrics."""
        manager.record_retry_attempt(OperationType.DATABASE_READ, True)
        manager.record_retry_attempt(OperationType.EXTERNAL_API, False)
        metrics = manager.get_retry_metrics()
        assert_retry_metrics_structure(metrics)
        assert_retry_metrics_values(metrics)


class TestDefaultConfigurations:
    """Test default retry configurations."""
    
    def test_default_configs_exist(self):
        """Test that default configs exist for all operation types."""
        expected_operations = get_expected_operation_configs()
        for operation in expected_operations:
            assert operation in DEFAULT_RETRY_CONFIGS
    
    def test_database_read_config(self):
        """Test database read configuration."""
        config = DEFAULT_RETRY_CONFIGS[OperationType.DATABASE_READ]
        
        assert config.max_retries == 3
        assert config.base_delay == 0.1
        assert config.backoff_strategy == BackoffStrategy.EXPONENTIAL
        assert config.jitter_type == JitterType.EQUAL
    
    def test_api_config(self):
        """Test API configuration."""
        config = DEFAULT_RETRY_CONFIGS[OperationType.EXTERNAL_API]
        
        assert config.max_retries == 4
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_strategy == BackoffStrategy.EXPONENTIAL
        assert config.jitter_type == JitterType.DECORRELATED
    
    def test_websocket_config(self):
        """Test WebSocket configuration."""
        config = DEFAULT_RETRY_CONFIGS[OperationType.WEBSOCKET_SEND]
        
        assert config.max_retries == 2
        assert config.base_delay == 0.1
        assert config.backoff_strategy == BackoffStrategy.FIXED
        assert config.jitter_type == JitterType.NONE


class TestGlobalRetryManager:
    """Test global retry manager instance."""
    
    def test_global_instance_exists(self):
        """Test that global retry manager exists."""
        assert retry_manager is not None
        assert isinstance(retry_manager, RetryManager)
    
    def test_global_instance_functionality(self):
        """Test global instance basic functionality."""
        strategy = retry_manager.get_strategy(OperationType.DATABASE_READ)
        
        assert strategy is not None
        assert isinstance(strategy, DatabaseRetryStrategy)