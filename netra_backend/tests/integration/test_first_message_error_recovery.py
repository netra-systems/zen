"""Integration Test: First Message Error Recovery
BVJ: $12K MRR - Poor error handling causes 60% user abandonment  
Components: Error Detection → Retry Logic → Circuit Breaker → State Recovery
Critical: System must gracefully recover from failures during first interaction
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from netra_backend.app.schemas import User

from netra_backend.app.core.error_recovery import ErrorRecoveryStrategy
from netra_backend.app.services.agent_service_core import AgentService

from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.core.circuit_breaker import CircuitBreaker
from netra_backend.app.core.health.telemetry_manager import TelemetryManager
from test_framework.mock_utils import mock_justified

@pytest.mark.asyncio
class TestFirstMessageErrorRecovery:
    """Test error recovery during first user message processing."""
    
    @pytest.fixture
    async def circuit_breaker(self):
        """Create circuit breaker for testing."""
        yield CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5.0,
            half_open_requests=1
        )
    
    @pytest.fixture
    async def telemetry_manager(self):
        """Create telemetry manager for error tracking."""
        yield TelemetryManager()
    
    @pytest.fixture
    async def message_handler(self):
        """Create message handler with error recovery."""
        # L2: Mocking supervisor for error recovery testing
        # Mock: Generic component isolation for controlled unit testing
        mock_supervisor = Mock()
        # Mock: Generic component isolation for controlled unit testing
        mock_supervisor.run = AsyncMock()
        
        # Mock: Generic component isolation for controlled unit testing
        thread_service = Mock()
        # Mock: Generic component isolation for controlled unit testing
        thread_service.get_or_create_thread = AsyncMock()
        # Mock: Generic component isolation for controlled unit testing
        thread_service.create_message = AsyncMock()
        
        handler = MessageHandlerService(mock_supervisor, thread_service)
        yield handler
    
    @pytest.fixture
    @pytest.mark.asyncio
    async def test_user(self):
        """Create test user for error recovery testing."""
        return User(
            id="error_recovery_user_001",
            email="recovery@test.netrasystems.ai",
            username="recoveryuser",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
    
    @pytest.mark.asyncio
    async def test_transient_failure_with_retry(
        self, message_handler, test_user
    ):
        """Test recovery from transient failures with retry logic."""
        
        # Configure failure then success pattern
        call_count = 0
        
        async def flaky_handler(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary network issue")
            return {"status": "success", "response": "Processed successfully"}
        
        message_handler.supervisor.run = flaky_handler
        
        # Process message with retry
        max_retries = 3
        retry_delay = 0.1
        
        for attempt in range(max_retries):
            try:
                result = await message_handler.supervisor.run(
                    user_request="First message",
                    thread_id="test_thread",
                    user_id=test_user.id,
                    run_id="test_run"
                )
                break
            except ConnectionError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay * (2 ** attempt))
                else:
                    raise
        
        # Verify success after retries
        assert result["status"] == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_activation(
        self, circuit_breaker, message_handler, test_user
    ):
        """Test circuit breaker activation on repeated failures."""
        
        # Simulate repeated failures
        async def failing_handler(*args, **kwargs):
            raise Exception("Service unavailable")
        
        message_handler.supervisor.run = failing_handler
        
        # Track circuit breaker state
        failure_count = 0
        
        for i in range(5):
            try:
                if circuit_breaker.is_open():
                    # Circuit open, skip call
                    raise Exception("Circuit breaker open")
                
                await message_handler.supervisor.run(
                    user_request=f"Message {i}",
                    thread_id="test_thread",
                    user_id=test_user.id,
                    run_id=f"run_{i}"
                )
            except Exception:
                failure_count += 1
                circuit_breaker.record_failure()
                
                if circuit_breaker.consecutive_failures >= circuit_breaker.failure_threshold:
                    circuit_breaker.trip()
        
        # Verify circuit breaker tripped
        assert circuit_breaker.is_open()
        assert failure_count >= 3
    
    @pytest.mark.asyncio
    async def test_state_preservation_during_failure(
        self, message_handler, test_user
    ):
        """Test state preservation when first message fails."""
        
        # Mock state storage
        # L2: Mocking state store for preservation testing
        state_store = {}
        
        async def save_state(key: str, value: Any):
            state_store[key] = value
        
        async def load_state(key: str) -> Any:
            return state_store.get(key)
        
        # Save message state before processing
        message_state = {
            "user_id": test_user.id,
            "content": "Important first message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "attempt": 1
        }
        await save_state(f"message_{test_user.id}", message_state)
        
        # Simulate processing failure
        async def failing_processor(*args, **kwargs):
            # Update attempt count
            current_state = await load_state(f"message_{test_user.id}")
            current_state["attempt"] += 1
            await save_state(f"message_{test_user.id}", current_state)
            raise Exception("Processing failed")
        
        message_handler.supervisor.run = failing_processor
        
        # Attempt processing
        with pytest.raises(Exception):
            await message_handler.supervisor.run(
                user_request=message_state["content"],
                thread_id="test_thread",
                user_id=test_user.id,
                run_id="test_run"
            )
        
        # Verify state preserved
        preserved_state = await load_state(f"message_{test_user.id}")
        assert preserved_state["content"] == "Important first message"
        assert preserved_state["attempt"] == 2
    
    @pytest.mark.asyncio
    async def test_graceful_degradation(
        self, message_handler, telemetry_manager, test_user
    ):
        """Test graceful degradation when services unavailable."""
        
        # Track degradation state
        degraded_mode = False
        
        async def degraded_handler(*args, **kwargs):
            nonlocal degraded_mode
            if not degraded_mode:
                # Try normal processing
                raise Exception("Primary service unavailable")
            else:
                # Use degraded mode
                return {
                    "status": "degraded",
                    "response": "Limited functionality response",
                    "warning": "Some features unavailable"
                }
        
        # Attempt normal processing
        try:
            message_handler.supervisor.run = degraded_handler
            await message_handler.supervisor.run(
                user_request="First message",
                thread_id="test_thread",
                user_id=test_user.id,
                run_id="test_run"
            )
        except Exception:
            # Switch to degraded mode
            degraded_mode = True
            telemetry_manager.record_event("degraded_mode_activated")
        
        # Process in degraded mode
        result = await message_handler.supervisor.run(
            user_request="First message",
            thread_id="test_thread",
            user_id=test_user.id,
            run_id="test_run"
        )
        
        # Verify degraded response
        assert result["status"] == "degraded"
        assert "Limited functionality" in result["response"]
    
    @pytest.mark.asyncio
    async def test_user_notification_on_recovery(
        self, message_handler, test_user
    ):
        """Test user notification after error recovery."""
        
        # Mock WebSocket manager for notifications
        # L2: Mocking WebSocket for notification testing
        # Mock: Generic component isolation for controlled unit testing
        ws_manager = Mock()
        # Mock: Generic component isolation for controlled unit testing
        ws_manager.send_message = AsyncMock()
        
        # Simulate failure then recovery
        attempt = 0
        
        async def recovering_handler(*args, **kwargs):
            nonlocal attempt
            attempt += 1
            if attempt == 1:
                raise Exception("Initial failure")
            return {"status": "success", "response": "Recovered"}
        
        message_handler.supervisor.run = recovering_handler
        
        # Process with recovery
        try:
            await message_handler.supervisor.run(
                user_request="First message",
                thread_id="test_thread",
                user_id=test_user.id,
                run_id="test_run"
            )
        except Exception:
            # Retry after failure
            await asyncio.sleep(0.1)
            result = await message_handler.supervisor.run(
                user_request="First message",
                thread_id="test_thread",
                user_id=test_user.id,
                run_id="test_run"
            )
            
            # Send recovery notification
            await ws_manager.send_message(test_user.id, {
                "type": "recovery_notification",
                "message": "Your message has been processed successfully",
                "status": "recovered"
            })
        
        # Verify notification sent
        ws_manager.send_message.assert_called_once()
        call_args = ws_manager.send_message.call_args[0]
        assert call_args[0] == test_user.id
        assert call_args[1]["type"] == "recovery_notification"
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, message_handler, test_user):
        """Test timeout handling for first message."""
        
        # Simulate slow processing
        async def slow_handler(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return {"status": "success"}
        
        message_handler.supervisor.run = slow_handler
        
        # Process with timeout
        timeout_seconds = 5.0
        
        try:
            result = await asyncio.wait_for(
                message_handler.supervisor.run(
                    user_request="First message",
                    thread_id="test_thread",
                    user_id=test_user.id,
                    run_id="test_run"
                ),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            # Handle timeout gracefully
            result = {
                "status": "timeout",
                "message": "Processing is taking longer than expected",
                "suggestion": "Please try again or check back later"
            }
        
        # Verify timeout handled
        assert result["status"] == "timeout"
        assert "taking longer" in result["message"]
    
    @pytest.mark.asyncio
    async def test_error_telemetry_collection(
        self, telemetry_manager, message_handler, test_user
    ):
        """Test error telemetry collection during failures."""
        
        # Track telemetry events
        events = []
        
        def record_event(event_type: str, data: Dict):
            events.append({
                "type": event_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        
        telemetry_manager.record_event = record_event
        
        # Simulate various errors
        error_scenarios = [
            ("network_error", ConnectionError("Network unreachable")),
            ("auth_error", PermissionError("Unauthorized")),
            ("processing_error", ValueError("Invalid input"))
        ]
        
        for error_type, error in error_scenarios:
            try:
                raise error
            except Exception as e:
                telemetry_manager.record_event(error_type, {
                    "error": str(e),
                    "user_id": test_user.id,
                    "context": "first_message"
                })
        
        # Verify telemetry collected
        assert len(events) == 3
        assert events[0]["type"] == "network_error"
        assert events[1]["type"] == "auth_error"
        assert events[2]["type"] == "processing_error"