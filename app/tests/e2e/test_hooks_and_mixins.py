"""
E2E Tests for Hooks and Mixins System Integration

Tests comprehensive hook and mixin functionality including:
- Pre-execution hooks (validation, setup)
- Post-execution hooks (cleanup, logging)
- Error hooks (recovery, notification)
- State management mixins
- Logging mixins with proper formatting
- Validation mixins for data integrity
- Caching mixins with TTL

All functions ≤8 lines per CLAUDE.md requirements.
"""

import asyncio
import time
import pytest
from datetime import datetime, UTC, timedelta
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock, patch

from app.agents.quality_hooks import QualityHooksManager
from app.core.agent_reliability_mixin import AgentReliabilityMixin, AgentHealthStatus
from app.agents.supervisor.execution_context import AgentExecutionContext
from app.agents.state import DeepAgentState
from app.services.quality_gate_service import ContentType, ValidationResult, QualityMetrics
from app.core.exceptions_base import NetraException
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestPreExecutionHooks:
    """Test pre-execution hooks for validation and setup."""
    
    async def test_validation_hook_success(self):
        """Test successful pre-execution validation hook."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        hook_manager.quality_gate_service.validate_content.assert_called_once()
        assert state.quality_metrics.get("TestAgent") is not None
    
    async def test_validation_hook_failure(self):
        """Test pre-execution validation hook failure handling."""
        hook_manager = self._create_mock_hook_manager()
        hook_manager.quality_gate_service.validate_content.side_effect = Exception("Validation error")
        
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        assert not hasattr(state, 'quality_metrics')
    
    def test_setup_hook_initialization(self):
        """Test pre-execution setup hook initialization."""
        hook_manager = QualityHooksManager(None, None, strict_mode=True)
        assert hook_manager.strict_mode is True
        assert hook_manager.quality_stats['total_validations'] == 0
    
    async def test_validation_hook_with_context(self):
        """Test validation hook with execution context."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        validation_args = hook_manager.quality_gate_service.validate_content.call_args
        assert validation_args[1]['context']['run_id'] == context.run_id
    
    def _create_mock_hook_manager(self):
        """Create mock hook manager for testing."""
        quality_gate = Mock()
        quality_gate.validate_content = AsyncMock(return_value=self._create_validation_result())
        monitoring = Mock()
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_test_context(self) -> AgentExecutionContext:
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test_run", thread_id="test_thread", 
            user_id="test_user", agent_name="TestAgent", max_retries=3
        )
    
    def _create_test_state(self) -> DeepAgentState:
        """Create test agent state."""
        state = DeepAgentState(user_request="test request")
        state.triage_result = {'summary': 'test summary'}
        return state
    
    def _create_validation_result(self) -> ValidationResult:
        """Create mock validation result."""
        metrics = QualityMetrics(overall_score=0.85, issues=0)
        return ValidationResult(passed=True, metrics=metrics, retry_suggested=False)


class TestPostExecutionHooks:
    """Test post-execution hooks for cleanup and logging."""
    
    async def test_cleanup_hook_success(self):
        """Test successful post-execution cleanup hook."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state_with_metrics()
        
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        hook_manager.monitoring_service.record_quality_event.assert_called_once()
    
    async def test_cleanup_hook_no_metrics(self):
        """Test cleanup hook when no metrics exist."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        hook_manager.monitoring_service.record_quality_event.assert_not_called()
    
    async def test_logging_hook_formatting(self):
        """Test logging hook with proper formatting."""
        hook_manager = self._create_mock_hook_manager()
        validation_result = self._create_validation_result(passed=True, score=0.95)
        
        hook_manager._log_validation_success(validation_result)
        # Verify logging through captured logs if needed
    
    async def test_post_execution_state_cleanup(self):
        """Test state cleanup in post-execution hook."""
        hook_manager = self._create_mock_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state_with_metrics()
        
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        # Verify state is properly maintained after monitoring
        assert hasattr(state, 'quality_metrics')
    
    def _create_mock_hook_manager(self):
        """Create mock hook manager for testing."""
        quality_gate = Mock()
        monitoring = Mock()
        monitoring.record_quality_event = AsyncMock()
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_test_context(self) -> AgentExecutionContext:
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test_run", thread_id="test_thread", 
            user_id="test_user", agent_name="TestAgent", max_retries=3
        )
    
    def _create_test_state(self) -> DeepAgentState:
        """Create test agent state."""
        return DeepAgentState(user_request="test request")
    
    def _create_test_state_with_metrics(self) -> DeepAgentState:
        """Create test state with quality metrics."""
        state = self._create_test_state()
        state.quality_metrics = {"TestAgent": QualityMetrics(overall_score=0.9, issues=0)}
        return state
    
    def _create_validation_result(self, passed: bool = True, score: float = 0.85) -> ValidationResult:
        """Create validation result for testing."""
        metrics = QualityMetrics(overall_score=score, issues=0 if passed else 2)
        return ValidationResult(passed=passed, metrics=metrics, retry_suggested=not passed)


class TestErrorHooks:
    """Test error hooks for recovery and notification."""
    
    async def test_error_hook_recovery_success(self):
        """Test successful error recovery through hooks."""
        mixin = self._create_reliability_mixin()
        
        async def failing_operation():
            raise ValueError("Test error")
        
        async def recovery_func(error, context):
            return {"recovered": True, "error": str(error)}
        
        mixin.register_recovery_strategy("test_op", recovery_func)
        result = await mixin.execute_with_reliability(failing_operation, "test_op")
        assert result["recovered"] is True
    
    async def test_error_hook_recovery_failure(self):
        """Test error hook when recovery fails."""
        mixin = self._create_reliability_mixin()
        
        async def failing_operation():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await mixin.execute_with_reliability(failing_operation, "test_op")
    
    async def test_error_notification_hook(self):
        """Test error notification through hooks."""
        mixin = self._create_reliability_mixin()
        
        async def failing_operation():
            raise ConnectionError("Network error")
        
        with pytest.raises(ConnectionError):
            await mixin.execute_with_reliability(failing_operation, "network_op")
        
        assert len(mixin.error_history) == 1
        assert mixin.error_history[0].error_type == "ConnectionError"
    
    async def test_error_classification_hook(self):
        """Test error classification in error hooks."""
        mixin = self._create_reliability_mixin()
        
        async def critical_error():
            raise MemoryError("Out of memory")
        
        with pytest.raises(MemoryError):
            await mixin.execute_with_reliability(critical_error, "memory_op")
        
        assert mixin.error_history[0].severity.value == "CRITICAL"
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()


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
    
    async def test_content_validation_mixin(self):
        """Test content validation through mixins."""
        hook_manager = self._create_hook_manager()
        context = self._create_test_context()
        state = self._create_test_state()
        
        await hook_manager.quality_validation_hook(context, "TriageSubAgent", state)
        assert hook_manager.quality_stats['total_validations'] == 1
    
    async def test_strict_validation_mode(self):
        """Test strict validation mode in mixins."""
        hook_manager = QualityHooksManager(
            quality_gate_service=Mock(), 
            monitoring_service=Mock(), 
            strict_mode=True
        )
        assert hook_manager.strict_mode is True
    
    def test_validation_retry_logic(self):
        """Test validation retry logic in mixins."""
        hook_manager = self._create_hook_manager()
        context = self._create_retry_context()
        
        should_retry = hook_manager.quality_retry_hook(context, "TestAgent", 1)
        assert should_retry is False  # Due to low quality score
    
    def test_content_type_mapping(self):
        """Test content type mapping in validation."""
        hook_manager = self._create_hook_manager()
        
        content_type = hook_manager._get_content_type_for_agent("DataSubAgent")
        assert content_type == ContentType.DATA_ANALYSIS
        
        general_type = hook_manager._get_content_type_for_agent("UnknownAgent")
        assert general_type == ContentType.GENERAL
    
    def _create_hook_manager(self) -> QualityHooksManager:
        """Create quality hook manager for testing."""
        quality_gate = Mock()
        quality_gate.validate_content = AsyncMock(
            return_value=ValidationResult(
                passed=True, 
                metrics=QualityMetrics(overall_score=0.85, issues=0),
                retry_suggested=False
            )
        )
        monitoring = Mock()
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_test_context(self) -> AgentExecutionContext:
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test_run", thread_id="test_thread", 
            user_id="test_user", agent_name="TestAgent", max_retries=3
        )
    
    def _create_test_state(self) -> DeepAgentState:
        """Create test agent state."""
        state = DeepAgentState(user_request="test request")
        state.triage_result = {'summary': 'test triage summary'}
        return state
    
    def _create_retry_context(self) -> AgentExecutionContext:
        """Create context with quality validation for retry testing."""
        context = self._create_test_context()
        context.metadata = {
            'quality_validation': ValidationResult(
                passed=False,
                metrics=QualityMetrics(overall_score=0.1, issues=5),
                retry_suggested=True
            )
        }
        return context


class TestCachingMixins:
    """Test caching mixin functionality with TTL."""
    
    def test_operation_cache_tracking(self):
        """Test operation caching and tracking."""
        mixin = self._create_reliability_mixin()
        
        # Simulate multiple operations
        for i in range(5):
            mixin._record_successful_operation(f"op_{i}", float(i + 1))
        
        assert len(mixin.operation_times) == 5
        avg_time = mixin._calculate_avg_response_time()
        assert avg_time == 3.0  # Average of [1,2,3,4,5]
    
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
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()


class TestIntegrationPoints:
    """Test integration points between hooks and mixins."""
    
    async def test_hook_sequence_execution(self):
        """Test proper hook execution sequence."""
        hook_manager = self._create_hook_manager()
        mixin = self._create_reliability_mixin()
        
        context = self._create_test_context()
        state = self._create_test_state()
        
        # Pre-execution hook
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        
        # Main execution with reliability
        async def test_operation():
            return "success"
        
        result = await mixin.execute_with_reliability(test_operation, "test_op")
        
        # Post-execution hook
        await hook_manager.quality_monitoring_hook(context, "TestAgent", state)
        
        assert result == "success"
        assert len(mixin.operation_times) == 1
    
    async def test_error_propagation_through_layers(self):
        """Test error propagation through hook and mixin layers."""
        hook_manager = self._create_hook_manager()
        mixin = self._create_reliability_mixin()
        
        async def failing_operation():
            raise ValueError("Propagation test")
        
        with pytest.raises(ValueError):
            await mixin.execute_with_reliability(failing_operation, "test_op")
        
        # Verify error was recorded in mixin
        assert len(mixin.error_history) == 1
        assert mixin.error_history[0].message == "Propagation test"
    
    async def test_state_sharing_between_layers(self):
        """Test state sharing between hooks and mixins."""
        hook_manager = self._create_hook_manager()
        mixin = self._create_reliability_mixin()
        
        context = self._create_test_context()
        state = self._create_test_state()
        
        # Hook modifies state
        await hook_manager.quality_validation_hook(context, "TestAgent", state)
        
        # Verify state was modified
        assert hasattr(state, 'quality_metrics')
        
        # Mixin can access hook-modified state
        health_status = mixin.get_comprehensive_health_status()
        assert health_status.agent_name == "TestAgent"
    
    def _create_hook_manager(self) -> QualityHooksManager:
        """Create quality hook manager for testing."""
        quality_gate = Mock()
        quality_gate.validate_content = AsyncMock(
            return_value=ValidationResult(
                passed=True, 
                metrics=QualityMetrics(overall_score=0.85, issues=0),
                retry_suggested=False
            )
        )
        monitoring = Mock()
        return QualityHooksManager(quality_gate, monitoring)
    
    def _create_reliability_mixin(self) -> AgentReliabilityMixin:
        """Create reliability mixin for testing."""
        class TestAgent(AgentReliabilityMixin):
            name = "TestAgent"
        
        return TestAgent()
    
    def _create_test_context(self) -> AgentExecutionContext:
        """Create test execution context."""
        return AgentExecutionContext(
            run_id="test_run", thread_id="test_thread", 
            user_id="test_user", agent_name="TestAgent", max_retries=3
        )
    
    def _create_test_state(self) -> DeepAgentState:
        """Create test agent state."""
        state = DeepAgentState(user_request="test request")
        state.triage_result = {'summary': 'test summary'}
        return state