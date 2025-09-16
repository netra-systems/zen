"""
Unit tests for WebSocket Error Recovery - Testing error handling and system resilience.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform reliability and user experience
- Value Impact: Prevents chat session failures from disrupting user workflows
- Strategic Impact: Critical for enterprise users who require reliable AI interactions

These tests focus on error detection, recovery strategies, fault tolerance,
and ensuring the WebSocket system gracefully handles failures to maintain business continuity.
"""

import pytest
import asyncio
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, patch
from netra_backend.app.websocket_core.error_recovery_handler import (
    WebSocketErrorRecoveryHandler,
    ErrorType,
    RecoveryStrategy,
    ErrorContext,
    RecoveryResult,
    CircuitBreaker,
    ErrorMetrics
)
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType


class TestWebSocketErrorRecoveryHandler:
    """Unit tests for WebSocket error recovery handling."""
    
    @pytest.fixture
    def recovery_config(self):
        """Create error recovery configuration."""
        return {
            "circuit_breaker_enabled": True,
            "circuit_breaker_threshold": 5,
            "circuit_breaker_timeout_seconds": 30,
            "max_retry_attempts": 3,
            "retry_backoff_multiplier": 2.0,
            "enable_graceful_degradation": True,
            "error_metrics_enabled": True
        }
    
    @pytest.fixture
    def recovery_handler(self, recovery_config):
        """Create WebSocketErrorRecoveryHandler instance."""
        websocket_manager = Mock()
        message_buffer = Mock() 
        return WebSocketErrorRecoveryHandler(
            config=recovery_config,
            websocket_manager=websocket_manager,
            message_buffer=message_buffer
        )
    
    @pytest.fixture
    def connection_error_context(self):
        """Create sample connection error context."""
        return ErrorContext(
            error_type=ErrorType.CONNECTION_LOST,
            connection_id="conn_123",
            user_id="user_456",
            error_message="WebSocket connection closed unexpectedly",
            timestamp=datetime.now(timezone.utc),
            retry_count=0,
            context_data={
                "last_message_id": "msg_789",
                "connection_duration_seconds": 300,
                "client_ip": "192.168.1.100"
            }
        )
    
    def test_initializes_with_correct_configuration(self, recovery_handler, recovery_config):
        """Test ErrorRecoveryHandler initializes with proper configuration."""
        assert recovery_handler.config == recovery_config
        assert recovery_handler.circuit_breaker is not None
        assert isinstance(recovery_handler.circuit_breaker, CircuitBreaker)
        assert recovery_handler.error_metrics is not None
        assert isinstance(recovery_handler.error_metrics, ErrorMetrics)
        assert len(recovery_handler._active_recoveries) == 0
    
    @pytest.mark.asyncio
    async def test_detects_connection_errors(self, recovery_handler, connection_error_context):
        """Test detection and classification of connection errors."""
        # Report connection error
        await recovery_handler.handle_error(connection_error_context)
        
        # Verify error detected and classified
        assert connection_error_context.connection_id in recovery_handler._active_recoveries
        recovery_state = recovery_handler._active_recoveries[connection_error_context.connection_id]
        
        assert recovery_state.error_context == connection_error_context
        assert recovery_state.recovery_strategy is not None
        assert recovery_state.started_at is not None
        assert recovery_state.is_active is True
    
    @pytest.mark.asyncio
    async def test_applies_connection_recovery_strategy(self, recovery_handler, connection_error_context):
        """Test application of connection recovery strategy."""
        # Configure mock for successful recovery
        recovery_handler.websocket_manager.attempt_reconnection = AsyncMock(return_value=True)
        recovery_handler.message_buffer.get_buffered_messages = AsyncMock(return_value=[])
        
        # Handle error and attempt recovery
        recovery_result = await recovery_handler.handle_error(connection_error_context)
        
        # Verify recovery attempted
        assert isinstance(recovery_result, RecoveryResult)
        assert recovery_result.recovery_attempted is True
        assert recovery_result.strategy_applied == RecoveryStrategy.RECONNECT_WITH_BACKOFF
        
        # Verify reconnection was attempted
        recovery_handler.websocket_manager.attempt_reconnection.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_implements_exponential_backoff_retry(self, recovery_handler, connection_error_context):
        """Test exponential backoff retry mechanism."""
        # Configure mock to fail first few attempts
        attempt_count = 0
        
        async def mock_reconnect_with_failures(*args, **kwargs):
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count <= 2:  # Fail first 2 attempts
                raise Exception("Connection failed")
            return True
        
        recovery_handler.websocket_manager.attempt_reconnection.side_effect = mock_reconnect_with_failures
        recovery_handler.message_buffer.get_buffered_messages = AsyncMock(return_value=[])
        
        # Handle error with retries
        with patch('asyncio.sleep') as mock_sleep:
            recovery_result = await recovery_handler.handle_error(connection_error_context)
        
        # Verify exponential backoff applied
        assert mock_sleep.call_count >= 2  # Should have waited between retries
        
        # Verify backoff progression (approximate check)
        call_args = [call[0][0] for call in mock_sleep.call_args_list]
        if len(call_args) >= 2:
            assert call_args[1] > call_args[0]  # Second delay should be longer
        
        # Should eventually succeed
        assert recovery_result.recovery_successful is True
        assert recovery_result.retry_attempts_made >= 2
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_repeated_failures(self, recovery_handler):
        """Test circuit breaker preventing repeated failure attempts."""
        connection_id = "failing_conn"
        
        # Configure mock to always fail
        recovery_handler.websocket_manager.attempt_reconnection = AsyncMock(
            side_effect=Exception("Persistent failure")
        )
        
        # Trigger multiple failures to trip circuit breaker
        for i in range(6):  # Exceed threshold of 5
            error_context = ErrorContext(
                error_type=ErrorType.CONNECTION_LOST,
                connection_id=connection_id,
                user_id="user_123",
                error_message=f"Failure {i}",
                timestamp=datetime.now(timezone.utc)
            )
            
            try:
                await recovery_handler.handle_error(error_context)
            except:
                pass  # Expected failures
        
        # Circuit breaker should be open (preventing further attempts)
        circuit_breaker = recovery_handler.circuit_breaker
        assert circuit_breaker.is_open() is True
        
        # Further attempts should be rejected quickly
        final_error = ErrorContext(
            error_type=ErrorType.CONNECTION_LOST,
            connection_id=connection_id,
            user_id="user_123",
            error_message="Should be rejected",
            timestamp=datetime.now(timezone.utc)
        )
        
        result = await recovery_handler.handle_error(final_error)
        assert result.recovery_attempted is False
        assert result.rejected_by_circuit_breaker is True
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_mode(self, recovery_handler):
        """Test graceful degradation when recovery fails."""
        connection_id = "degraded_conn"
        user_id = "user_123"
        
        # Configure all recovery attempts to fail
        recovery_handler.websocket_manager.attempt_reconnection = AsyncMock(
            side_effect=Exception("Recovery impossible")
        )
        
        # Create error context
        error_context = ErrorContext(
            error_type=ErrorType.MESSAGE_DELIVERY_FAILED,
            connection_id=connection_id,
            user_id=user_id,
            error_message="Cannot deliver messages",
            timestamp=datetime.now(timezone.utc)
        )
        
        # Enable graceful degradation
        recovery_handler.config["enable_graceful_degradation"] = True
        
        # Handle error
        result = await recovery_handler.handle_error(error_context)
        
        # Should activate graceful degradation
        assert result.degradation_mode_activated is True
        assert result.degradation_strategy is not None
        
        # Should buffer messages for later delivery
        degradation_state = recovery_handler._degradation_states.get(user_id)
        if degradation_state:
            assert degradation_state.is_active is True
            assert degradation_state.fallback_strategy is not None
    
    @pytest.mark.asyncio
    async def test_handles_different_error_types(self, recovery_handler):
        """Test handling of different error types with appropriate strategies."""
        error_scenarios = [
            {
                "error_type": ErrorType.CONNECTION_LOST,
                "expected_strategy": RecoveryStrategy.RECONNECT_WITH_BACKOFF
            },
            {
                "error_type": ErrorType.MESSAGE_SERIALIZATION_FAILED,
                "expected_strategy": RecoveryStrategy.RETRY_WITH_FALLBACK_FORMAT
            },
            {
                "error_type": ErrorType.RATE_LIMIT_EXCEEDED,
                "expected_strategy": RecoveryStrategy.BACKOFF_AND_QUEUE
            },
            {
                "error_type": ErrorType.AUTHENTICATION_FAILED,
                "expected_strategy": RecoveryStrategy.REAUTHENTICATE
            }
        ]
        
        for scenario in error_scenarios:
            error_context = ErrorContext(
                error_type=scenario["error_type"],
                connection_id=f"conn_{scenario['error_type'].value}",
                user_id="test_user",
                error_message=f"Test {scenario['error_type'].value}",
                timestamp=datetime.now(timezone.utc)
            )
            
            # Configure appropriate mocks based on strategy
            if scenario["expected_strategy"] == RecoveryStrategy.RECONNECT_WITH_BACKOFF:
                recovery_handler.websocket_manager.attempt_reconnection = AsyncMock(return_value=True)
            elif scenario["expected_strategy"] == RecoveryStrategy.REAUTHENTICATE:
                recovery_handler.websocket_manager.reauthenticate_user = AsyncMock(return_value=True)
            
            # Handle error
            result = await recovery_handler.handle_error(error_context)
            
            # Verify appropriate strategy applied
            assert result.strategy_applied == scenario["expected_strategy"]
    
    @pytest.mark.asyncio
    async def test_restores_message_buffer_after_recovery(self, recovery_handler, connection_error_context):
        """Test restoration of buffered messages after successful recovery."""
        # Create buffered messages
        buffered_messages = [
            WebSocketMessage(
                type=MessageType.AGENT_THINKING,
                payload={"status": "processing"},
                user_id=connection_error_context.user_id
            ),
            WebSocketMessage(
                type=MessageType.AGENT_PROGRESS,  # Using AGENT_PROGRESS since TOOL_COMPLETED doesn't exist
                payload={"result": "analysis done"},
                user_id=connection_error_context.user_id
            )
        ]
        
        # Configure mocks
        recovery_handler.websocket_manager.attempt_reconnection = AsyncMock(return_value=True)
        recovery_handler.message_buffer.get_buffered_messages = AsyncMock(return_value=buffered_messages)
        recovery_handler.websocket_manager.send_messages = AsyncMock(return_value=True)
        
        # Handle error and recovery
        result = await recovery_handler.handle_error(connection_error_context)
        
        # Verify successful recovery
        assert result.recovery_successful is True
        
        # Verify buffered messages were restored
        recovery_handler.message_buffer.get_buffered_messages.assert_called_once_with(
            connection_error_context.user_id
        )
        recovery_handler.websocket_manager.send_messages.assert_called_once_with(
            connection_error_context.connection_id, buffered_messages
        )
        
        # Verify restoration recorded
        assert result.buffered_messages_restored == len(buffered_messages)
    
    @pytest.mark.asyncio
    async def test_tracks_error_metrics_and_patterns(self, recovery_handler):
        """Test tracking of error metrics and pattern detection."""
        # Generate various error scenarios
        error_types = [ErrorType.CONNECTION_LOST, ErrorType.MESSAGE_DELIVERY_FAILED, ErrorType.RATE_LIMIT_EXCEEDED]
        
        for i, error_type in enumerate(error_types):
            for j in range(3):  # 3 errors of each type
                error_context = ErrorContext(
                    error_type=error_type,
                    connection_id=f"conn_{i}_{j}",
                    user_id=f"user_{i}",
                    error_message=f"Error {i}.{j}",
                    timestamp=datetime.now(timezone.utc) - timedelta(minutes=j)
                )
                
                try:
                    await recovery_handler.handle_error(error_context)
                except:
                    pass  # Expected for some error types
        
        # Get error metrics
        metrics = recovery_handler.error_metrics
        
        # Verify metrics tracking
        assert metrics.total_errors_handled >= len(error_types) * 3
        assert len(metrics.error_type_counts) >= len(error_types)
        
        # Should detect patterns
        for error_type in error_types:
            assert error_type in metrics.error_type_counts
            assert metrics.error_type_counts[error_type] >= 3
        
        # Should track recovery success rates
        assert hasattr(metrics, 'recovery_success_rate')
        assert 0 <= metrics.recovery_success_rate <= 1.0
    
    @pytest.mark.asyncio
    async def test_generates_error_recovery_report(self, recovery_handler):
        """Test generation of comprehensive error recovery reports."""
        # Simulate some error handling activity
        for i in range(5):
            error_context = ErrorContext(
                error_type=ErrorType.CONNECTION_LOST,
                connection_id=f"conn_{i}",
                user_id=f"user_{i}",
                error_message=f"Test error {i}",
                timestamp=datetime.now(timezone.utc)
            )
            
            # Configure mock for some successes, some failures
            success = i % 2 == 0  # Even numbered attempts succeed
            recovery_handler.websocket_manager.attempt_reconnection = AsyncMock(return_value=success)
            
            try:
                await recovery_handler.handle_error(error_context)
            except:
                pass  # Expected for failed recoveries
        
        # Generate report
        report = await recovery_handler.generate_recovery_report(time_period_hours=24)
        
        # Verify report completeness
        assert report is not None
        assert report.total_errors_encountered >= 5
        assert report.total_recovery_attempts >= 5
        assert report.recovery_success_rate >= 0.0
        assert len(report.most_common_error_types) > 0
        
        # Should include system health assessment
        assert hasattr(report, 'system_health_rating')
        assert report.system_health_rating in ['excellent', 'good', 'fair', 'poor', 'critical']
        
        # Should include recommendations for improvement
        if report.system_health_rating in ['fair', 'poor', 'critical']:
            assert len(report.improvement_recommendations) > 0
    
    @pytest.mark.asyncio
    async def test_prevents_cascading_failures(self, recovery_handler):
        """Test prevention of cascading failures across connections."""
        # Simulate error in one connection that could affect others
        primary_error = ErrorContext(
            error_type=ErrorType.RESOURCE_EXHAUSTED,
            connection_id="primary_conn",
            user_id="primary_user",
            error_message="Memory limit exceeded",
            timestamp=datetime.now(timezone.utc),
            context_data={"severity": "high", "affects_others": True}
        )
        
        # Handle primary error
        await recovery_handler.handle_error(primary_error)
        
        # Should activate cascade prevention measures
        prevention_state = recovery_handler._cascade_prevention
        if prevention_state.is_active:
            assert prevention_state.isolation_mode is True
            assert prevention_state.affected_connections is not None
        
        # Subsequent errors should be handled with isolation
        secondary_error = ErrorContext(
            error_type=ErrorType.CONNECTION_LOST,
            connection_id="secondary_conn",
            user_id="secondary_user",
            error_message="Connection lost during resource issue",
            timestamp=datetime.now(timezone.utc)
        )
        
        result = await recovery_handler.handle_error(secondary_error)
        
        # Should apply cascade prevention strategy
        assert result.cascade_prevention_applied is True
        assert result.isolation_measures_activated is True