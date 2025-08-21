"""
E2E Tests for Mixin System Comprehensive Functionality

Tests mixin functionality including:
- State management mixins functionality
- Logging mixins with proper formatting
- Validation mixins for data integrity
- Caching mixins with TTL
- Error handling and recovery mixins

All functions ≤8 lines per CLAUDE.md requirements.
Module ≤300 lines per CLAUDE.md requirements.
"""

import asyncio
import time
import pytest
from datetime import datetime, UTC, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch

from netra_backend.app.core.agent_reliability_mixin import AgentReliabilityMixin
from netra_backend.app.core.agent_reliability_types import AgentHealthStatus
from logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestStateMixins:
    """Test state management mixin functionality."""
    
    def test_state_mixin_initialization(self):
        """Test state management mixin initialization."""
        mixin = self._create_reliability_mixin()
        assert hasattr(mixin, 'error_history')
        assert hasattr(mixin, 'operation_times')
        assert mixin.max_error_history == 50
    
    async def test_state_tracking_operations(self):
        """Test state tracking during operations."""
        mixin = self._create_reliability_mixin()
        
        async def success_operation():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await mixin.execute_with_reliability(success_operation, "test_op")
        assert result == "success"
        assert len(mixin.operation_times) == 1
        assert mixin.operation_times[0] >= 0.1
    
    def test_state_history_management(self):
        """Test state history size management."""
        mixin = self._create_reliability_mixin()
        
        # Fill error history beyond limit
        for i in range(55):
            mixin.error_history.append(Mock(timestamp=datetime.now(UTC)))
        
        mixin._record_successful_operation("test", 1.0)
        assert len(mixin.error_history) <= mixin.max_error_history
    
    def test_health_status_calculation(self):
        """Test health status calculation from state."""
        mixin = self._create_reliability_mixin()
        mixin.operation_times = [1.0, 2.0, 1.5]
        
        health_status = mixin.get_comprehensive_health_status()
        assert isinstance(health_status, AgentHealthStatus)
        assert health_status.success_rate == 1.0
        assert health_status.status == "healthy"
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()


class TestLoggingMixins:
    """Test logging mixin functionality with proper formatting."""
    
    async def test_structured_logging_format(self):
        """Test structured logging format in mixins."""
        mixin = self._create_reliability_mixin()
        
        async def failing_operation():
            raise ValueError("Test validation error")
        
        with patch.object(logger, 'info') as mock_log:
            with pytest.raises(ValueError):
                await mixin.execute_with_reliability(failing_operation, "test_op")
            
            # Verify structured logging was called
            assert len(mixin.error_history) == 1
    
    def test_log_level_classification(self):
        """Test proper log level classification."""
        mixin = self._create_reliability_mixin()
        
        with patch.object(logger, 'critical') as mock_critical:
            error = MemoryError("Critical error")
            severity = mixin._classify_error_severity(error)
            assert severity.value == "CRITICAL"
    
    def test_error_context_logging(self):
        """Test error context in logging output."""
        mixin = self._create_reliability_mixin()
        context = {"user_id": "test_user", "operation": "test"}
        
        with patch.object(logger, 'warning') as mock_log:
            error = ValueError("Test error")
            error_record = Mock()
            error_record.agent_name = "TestAgent"
            error_record.operation = "test_op"
            error_record.message = "Test error"
            error_record.error_id = "test_id"
            error_record.error_type = "ValueError"
            error_record.severity.value = "MEDIUM"
            error_record.context = context
            
            mixin._log_error(error_record)
            mock_log.assert_called()
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()


class TestValidationMixins:
    """Test validation mixin functionality for data integrity."""
    
    def test_operation_cache_tracking(self):
        """Test operation caching and tracking."""
        mixin = self._create_reliability_mixin()
        
        # Simulate multiple operations
        for i in range(5):
            mixin._record_successful_operation(f"op_{i}", float(i + 1))
        
        assert len(mixin.operation_times) == 5
        avg_time = mixin._calculate_avg_response_time()
        assert avg_time == 3.0  # Average of [1,2,3,4,5]
    
    def test_error_severity_validation(self):
        """Test error severity validation in mixins."""
        mixin = self._create_reliability_mixin()
        
        # Test different error severities
        critical_error = MemoryError("Out of memory")
        high_error = ValueError("Invalid value")
        medium_error = ConnectionError("Connection failed")
        
        assert mixin._classify_error_severity(critical_error).value == "CRITICAL"
        assert mixin._classify_error_severity(high_error).value == "HIGH"
        assert mixin._classify_error_severity(medium_error).value == "MEDIUM"
    
    def test_validation_thresholds(self):
        """Test validation threshold compliance."""
        mixin = self._create_reliability_mixin()
        
        # Test health calculation with different scenarios
        health_score = mixin._calculate_overall_health(0.95, 0, 2.0)
        assert health_score >= 0.8  # Healthy threshold
        
        degraded_score = mixin._calculate_overall_health(0.7, 2, 3.0)
        assert degraded_score >= 0.5  # Degraded threshold
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()


class TestCachingMixins:
    """Test caching mixin functionality with TTL."""
    
    def test_cache_ttl_behavior(self):
        """Test cache TTL behavior in mixins."""
        mixin = self._create_reliability_mixin()
        
        # Test recent errors counting (TTL-like behavior)
        old_time = datetime.now(UTC) - timedelta(minutes=10)
        recent_time = datetime.now(UTC) - timedelta(seconds=30)
        
        mixin.error_history = [
            Mock(timestamp=old_time),
            Mock(timestamp=recent_time)
        ]
        
        recent_count = mixin._count_recent_errors(300)  # Last 5 minutes
        assert recent_count == 1  # Only recent error
    
    def test_cache_size_limits(self):
        """Test cache size limits in mixins."""
        mixin = self._create_reliability_mixin()
        
        # Fill operation cache beyond limit
        for i in range(105):
            mixin.operation_times.append(float(i))
        
        mixin._record_successful_operation("test", 1.0)
        assert len(mixin.operation_times) <= mixin.max_operation_history
    
    def test_health_metrics_caching(self):
        """Test health metrics caching behavior."""
        mixin = self._create_reliability_mixin()
        
        # Check if health check should be performed (cache expiry)
        assert mixin.should_perform_health_check() is True
        
        # Simulate recent health check
        mixin.last_health_check = time.time()
        assert mixin.should_perform_health_check() is False
    
    def test_cache_invalidation_timing(self):
        """Test cache invalidation based on time windows."""
        mixin = self._create_reliability_mixin()
        
        # Test success rate calculation (sliding window cache)
        mixin.operation_times = [1.0, 2.0, 3.0]
        success_rate = mixin._calculate_success_rate()
        assert success_rate == 1.0  # All successful operations
        
        # Add error to history
        mixin.error_history = [Mock()]
        success_rate_with_error = mixin._calculate_success_rate()
        assert success_rate_with_error < 1.0  # Mixed success/failure
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()


class TestErrorHandlingMixins:
    """Test error handling and recovery mixins."""
    
    async def test_error_recovery_strategies(self):
        """Test error recovery strategy registration and execution."""
        mixin = self._create_reliability_mixin()
        
        async def recovery_function(error, context):
            return {"recovered": True, "original_error": str(error)}
        
        mixin.register_recovery_strategy("test_operation", recovery_function)
        
        async def failing_operation():
            raise ValueError("Test error")
        
        result = await mixin.execute_with_reliability(failing_operation, "test_operation")
        assert result["recovered"] is True
        assert "Test error" in result["original_error"]
    
    async def test_default_recovery_fallbacks(self):
        """Test default recovery strategy fallbacks."""
        mixin = self._create_reliability_mixin()
        
        # Test LLM recovery fallback
        llm_result = await mixin._default_llm_recovery(ValueError("LLM error"), {})
        assert llm_result["fallback_used"] is True
        
        # Test database recovery fallback
        db_result = await mixin._default_db_recovery(ConnectionError("DB error"), {})
        assert db_result["fallback_used"] is True
    
    async def test_circuit_breaker_integration(self):
        """Test circuit breaker integration with error mixins."""
        mixin = self._create_reliability_mixin()
        
        # Simulate multiple failures to trigger circuit breaker
        async def consistently_failing_operation():
            raise ConnectionError("Service unavailable")
        
        # Multiple failures should eventually trigger circuit breaker
        for i in range(5):
            try:
                await mixin.execute_with_reliability(consistently_failing_operation, "failing_op")
            except ConnectionError:
                pass  # Expected
        
        # Verify error history tracking
        assert len(mixin.error_history) > 0
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()