"""
Comprehensive tests for WebSocket error validation and loud error patterns.

Tests the enhanced error handling in agent message handling components,
ensuring that silent failures are eliminated and business-critical errors
are logged with maximum visibility.

BVJ: Platform/Internal | Stability | Ensure reliable WebSocket error detection
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone

from netra_backend.app.services.websocket_error_validator import (
    WebSocketEventValidator,
    ValidationResult,
    EventCriticality,
    get_websocket_validator,
    reset_websocket_validator
)
from netra_backend.app.services.user_websocket_emitter import UserWebSocketEmitter
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.websocket_event_router import WebSocketEventRouter
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter


class TestWebSocketErrorValidator:
    """Test comprehensive WebSocket event validation."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_websocket_validator()
        self.validator = WebSocketEventValidator()
    
    def test_validate_mission_critical_events(self):
        """Test validation of mission critical events."""
        # Valid mission critical event
        valid_event = {
            "type": "agent_started",
            "run_id": "run_real_456789",
            "agent_name": "DataAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"message": "Agent started"}
        }
        
        result = self.validator.validate_event(valid_event, "user_real_123456")
        assert result.is_valid
        assert result.criticality == EventCriticality.MISSION_CRITICAL
    
    def test_validate_missing_required_fields(self):
        """Test validation fails for missing required fields."""
        # Missing run_id
        invalid_event = {
            "type": "agent_started",
            "agent_name": "DataAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"message": "Agent started"}
        }
        
        result = self.validator.validate_event(invalid_event, "user_real_123456")
        assert not result.is_valid
        assert "missing required fields" in result.error_message.lower()
        assert result.criticality == EventCriticality.MISSION_CRITICAL
    
    def test_validate_malformed_event_structure(self):
        """Test validation fails for malformed events."""
        # Not a dictionary
        result = self.validator.validate_event("invalid", "user_real_456789")
        assert not result.is_valid
        assert "not a dictionary" in result.error_message.lower()
        assert result.criticality == EventCriticality.MISSION_CRITICAL
        
        # Missing type field
        result = self.validator.validate_event({}, "user_real_456789")
        assert not result.is_valid
        assert "missing required 'type' field" in result.error_message.lower()
        
        # Empty type field
        result = self.validator.validate_event({"type": ""}, "user_real_456789")
        assert not result.is_valid
        assert "empty or not a string" in result.error_message.lower()
    
    def test_validate_cross_user_leakage_detection(self):
        """Test detection of potential cross-user event leakage."""
        event = {
            "type": "agent_started",
            "run_id": "run_real_456789",
            "agent_name": "DataAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"message": "Agent started"},
            "user_id": "user_different_456"  # Different from target user
        }
        
        result = self.validator.validate_event(event, "user_real_123456")
        assert not result.is_valid
        assert "different user_id" in result.error_message.lower() or "cross-user" in result.error_message.lower()
        assert result.criticality == EventCriticality.MISSION_CRITICAL
    
    def test_validate_connection_readiness(self):
        """Test connection readiness validation."""
        # Valid connection
        result = self.validator.validate_connection_ready(
            "user_real_123456", "conn_456", Mock()
        )
        assert result.is_valid
        
        # Empty user_id
        result = self.validator.validate_connection_ready("", "conn_456", Mock())
        assert not result.is_valid
        assert "empty or invalid user_id" in result.error_message.lower()
        
        # Empty connection_id
        result = self.validator.validate_connection_ready("user_real_123456", "", Mock())
        assert not result.is_valid
        assert "empty or invalid connection_id" in result.error_message.lower()
        
        # No WebSocket manager
        result = self.validator.validate_connection_ready("user_real_123456", "conn_456", None)
        assert not result.is_valid
        assert "websocket manager not available" in result.error_message.lower()
    
    def test_validation_statistics(self):
        """Test validation statistics tracking."""
        # Initial state
        stats = self.validator.get_validation_stats()
        assert stats["total_validations"] == 0
        assert stats["failed_validations"] == 0
        assert stats["mission_critical_failures"] == 0
        assert stats["success_rate"] == 100
        
        # Valid validation
        valid_event = {
            "type": "agent_started",
            "run_id": "run_real_456789",
            "agent_name": "DataAgent",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": {"message": "Agent started"}
        }
        self.validator.validate_event(valid_event, "user_real_123456")
        
        # Invalid mission critical validation
        invalid_event = {"type": "agent_started"}
        result = self.validator.validate_event(invalid_event, "user_real_123456")
        # Verify this was counted as mission critical failure
        assert not result.is_valid
        
        stats = self.validator.get_validation_stats()
        assert stats["total_validations"] == 2
        assert stats["failed_validations"] == 1
        assert stats["mission_critical_failures"] == 1
        assert stats["success_rate"] == 50.0


class TestUserWebSocketEmitterErrorHandling:
    """Test enhanced error handling in UserWebSocketEmitter."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_websocket_validator()
        
        self.mock_context = UserExecutionContext(
            user_id="user_real_123456",
            thread_id="thread_real_456789",
            run_id="run_real_789012",
            request_id="req_real_abcdef"
        )
        
        self.mock_router = Mock(spec=WebSocketEventRouter)
        self.mock_router.websocket_manager = Mock()
        
        self.emitter = UserWebSocketEmitter(
            self.mock_context, self.mock_router, "test_conn_123"
        )
    
    @patch('netra_backend.app.services.user_websocket_emitter.logger')
    async def test_send_event_validation_failure_mission_critical(self, mock_logger):
        """Test loud error logging for mission critical event validation failures."""
        # Setup validator to fail validation
        with patch('netra_backend.app.services.user_websocket_emitter.get_websocket_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_validator.validate_event.return_value = ValidationResult(
                is_valid=False,
                error_message="Missing run_id",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="User will not see AI working"
            )
            mock_validator.validate_connection_ready.return_value = ValidationResult(is_valid=True)
            mock_get_validator.return_value = mock_validator
            
            # Attempt to send event
            success = await self.emitter._send_event(
                {"type": "agent_started", "invalid": "data"}, "agent_started"
            )
            
            # Verify failure and loud error logging
            assert not success
            assert self.emitter.events_failed == 1
            
            # Check that CRITICAL level logging was used
            mock_logger.critical.assert_called()
            critical_calls = mock_logger.critical.call_args_list
            
            # Verify specific error messages
            error_messages = [str(call) for call in critical_calls]
            assert any("Event validation failed for agent_started" in msg for msg in error_messages)
            assert any("BUSINESS VALUE FAILURE" in msg for msg in error_messages)
    
    @patch('netra_backend.app.services.user_websocket_emitter.logger')
    async def test_send_event_connection_validation_failure(self, mock_logger):
        """Test loud error logging for connection validation failures."""
        # Setup validator to pass event validation but fail connection validation
        with patch('netra_backend.app.services.user_websocket_emitter.get_websocket_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_validator.validate_event.return_value = ValidationResult(is_valid=True)
            mock_validator.validate_connection_ready.return_value = ValidationResult(
                is_valid=False,
                error_message="Connection not active",
                criticality=EventCriticality.MISSION_CRITICAL,
                business_impact="Connection validation system failure"
            )
            mock_get_validator.return_value = mock_validator
            
            # Attempt to send event
            success = await self.emitter._send_event(
                {"type": "agent_started", "run_id": "test"}, "agent_started"
            )
            
            # Verify failure and loud error logging
            assert not success
            assert self.emitter.events_failed == 1
            
            # Check that CRITICAL level logging was used
            mock_logger.critical.assert_called()
            critical_calls = mock_logger.critical.call_args_list
            
            # Verify specific error messages
            error_messages = [str(call) for call in critical_calls]
            assert any("Connection validation failed" in msg for msg in error_messages)
            assert any("BUSINESS VALUE FAILURE" in msg for msg in error_messages)
    
    @patch('netra_backend.app.services.user_websocket_emitter.logger')
    async def test_send_event_router_failure_mission_critical(self, mock_logger):
        """Test loud error logging for router failures on mission critical events."""
        # Setup successful validation but router failure
        with patch('netra_backend.app.services.user_websocket_emitter.get_websocket_validator') as mock_get_validator:
            mock_validator = Mock()
            mock_validator.validate_event.return_value = ValidationResult(
                is_valid=True,
                criticality=EventCriticality.MISSION_CRITICAL
            )
            mock_validator.validate_connection_ready.return_value = ValidationResult(is_valid=True)
            mock_get_validator.return_value = mock_validator
            
            # Setup router to fail
            self.mock_router.route_event.return_value = False
            
            # Attempt to send mission critical event
            success = await self.emitter._send_event(
                {
                    "type": "agent_started",
                    "run_id": "test_run_123",
                    "agent_name": "TestAgent",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "payload": {}
                },
                "agent_started"
            )
            
            # Verify failure and enhanced error logging for mission critical events
            assert not success
            assert self.emitter.events_failed == 1
            
            # Check that CRITICAL level logging was used
            mock_logger.critical.assert_called()
            critical_calls = mock_logger.critical.call_args_list
            
            # Verify enhanced error messages for mission critical events
            error_messages = [str(call) for call in critical_calls]
            assert any("MISSION CRITICAL EVENT FAILED" in msg for msg in error_messages)
            assert any("Chat functionality degraded" in msg for msg in error_messages)
            assert any("CRITICAL SYSTEM FAILURE" in msg for msg in error_messages)
    
    @patch('netra_backend.app.services.user_websocket_emitter.logger')
    async def test_send_event_exception_handling(self, mock_logger):
        """Test comprehensive exception handling with loud error logging."""
        # Setup validator to raise exception
        with patch('netra_backend.app.services.user_websocket_emitter.get_websocket_validator') as mock_get_validator:
            mock_get_validator.side_effect = Exception("Validator system failure")
            
            # Attempt to send event
            success = await self.emitter._send_event(
                {"type": "agent_started"}, "agent_started"
            )
            
            # Verify failure and critical error logging
            assert not success
            assert self.emitter.events_failed == 1
            
            # Check critical logging with stack trace
            mock_logger.critical.assert_called()
            critical_calls = mock_logger.critical.call_args_list
            
            error_messages = [str(call) for call in critical_calls]
            assert any("EXCEPTION in event transmission" in msg for msg in error_messages)
            assert any("SYSTEM FAILURE" in msg for msg in error_messages)
            assert any("Stack trace" in msg for msg in error_messages)


class TestWebSocketBridgeAdapterErrorHandling:
    """Test enhanced error handling in WebSocketBridgeAdapter."""
    
    def setup_method(self):
        """Setup test environment."""
        self.adapter = WebSocketBridgeAdapter()
        self.mock_bridge = AsyncMock()
        self.adapter.set_websocket_bridge(self.mock_bridge, "test_run_123", "TestAgent")
    
    @patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger')
    async def test_emit_agent_started_exception_loud_error(self, mock_logger):
        """Test loud error logging when agent_started emission fails."""
        # Setup bridge to raise exception
        self.mock_bridge.notify_agent_started.side_effect = Exception("Bridge failure")
        
        # Attempt to emit agent_started
        await self.adapter.emit_agent_started("Test message")
        
        # Verify critical error logging
        mock_logger.critical.assert_called()
        critical_calls = mock_logger.critical.call_args_list
        
        error_messages = [str(call) for call in critical_calls]
        assert any("Failed to emit agent_started for TestAgent" in msg for msg in error_messages)
        assert any("BUSINESS VALUE FAILURE" in msg for msg in error_messages)
        assert any("User will not see agent starting" in msg for msg in error_messages)
        assert any("Stack trace" in msg for msg in error_messages)
    
    @patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger')
    async def test_emit_agent_thinking_exception_loud_error(self, mock_logger):
        """Test loud error logging when agent_thinking emission fails."""
        # Setup bridge to raise exception
        self.mock_bridge.notify_agent_thinking.side_effect = Exception("Bridge failure")
        
        # Attempt to emit agent_thinking
        await self.adapter.emit_thinking("Testing analysis approach")
        
        # Verify critical error logging with business impact
        mock_logger.critical.assert_called()
        critical_calls = mock_logger.critical.call_args_list
        
        error_messages = [str(call) for call in critical_calls]
        assert any("Failed to emit agent_thinking for TestAgent" in msg for msg in error_messages)
        assert any("User will not see real-time reasoning" in msg for msg in error_messages)
        assert any("cannot follow AI's problem-solving approach" in msg for msg in error_messages)
    
    @patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger')
    async def test_emit_tool_executing_exception_loud_error(self, mock_logger):
        """Test loud error logging when tool_executing emission fails."""
        # Setup bridge to raise exception
        self.mock_bridge.notify_tool_executing.side_effect = Exception("Bridge failure")
        
        # Attempt to emit tool_executing
        await self.adapter.emit_tool_executing("data_analysis_tool", {"query": "test"})
        
        # Verify critical error logging with tool context
        mock_logger.critical.assert_called()
        critical_calls = mock_logger.critical.call_args_list
        
        error_messages = [str(call) for call in critical_calls]
        assert any("Failed to emit tool_executing for TestAgent, tool data_analysis_tool" in msg for msg in error_messages)
        assert any("User will not see tool usage transparency" in msg for msg in error_messages)
        assert any("which tools AI is using" in msg for msg in error_messages)
    
    @patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger')
    async def test_emit_tool_completed_exception_loud_error(self, mock_logger):
        """Test loud error logging when tool_completed emission fails."""
        # Setup bridge to raise exception
        self.mock_bridge.notify_tool_completed.side_effect = Exception("Bridge failure")
        
        # Attempt to emit tool_completed
        await self.adapter.emit_tool_completed("data_analysis_tool", {"result": "success"})
        
        # Verify critical error logging with tool results context
        mock_logger.critical.assert_called()
        critical_calls = mock_logger.critical.call_args_list
        
        error_messages = [str(call) for call in critical_calls]
        assert any("Failed to emit tool_completed for TestAgent, tool data_analysis_tool" in msg for msg in error_messages)
        assert any("User will not see tool results" in msg for msg in error_messages)
        assert any("results AI obtained from tools" in msg for msg in error_messages)
    
    @patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger')
    async def test_emit_agent_completed_exception_loud_error(self, mock_logger):
        """Test loud error logging when agent_completed emission fails."""
        # Setup bridge to raise exception
        self.mock_bridge.notify_agent_completed.side_effect = Exception("Bridge failure")
        
        # Attempt to emit agent_completed
        await self.adapter.emit_agent_completed({"response": "Analysis complete"})
        
        # Verify critical error logging with completion context
        mock_logger.critical.assert_called()
        critical_calls = mock_logger.critical.call_args_list
        
        error_messages = [str(call) for call in critical_calls]
        assert any("Failed to emit agent_completed for TestAgent" in msg for msg in error_messages)
        assert any("User will not know when valuable response is ready" in msg for msg in error_messages)
        assert any("may wait indefinitely for response completion" in msg for msg in error_messages)


class TestErrorHandlingIntegration:
    """Test integration of error handling across components."""
    
    def setup_method(self):
        """Setup test environment."""
        reset_websocket_validator()
    
    @patch('netra_backend.app.services.user_websocket_emitter.logger')
    async def test_end_to_end_error_flow_loud_logging(self, mock_logger):
        """Test end-to-end error flow with comprehensive loud logging."""
        # Setup context and emitter
        context = UserExecutionContext(
            user_id="user_real_987654",
            thread_id="thread_real_654321",
            run_id="run_real_321098",
            request_id="req_real_fedcba"
        )
        
        # Setup router with failing WebSocket manager
        mock_router = Mock(spec=WebSocketEventRouter)
        mock_router.websocket_manager = None  # Simulate missing WebSocket manager
        
        emitter = UserWebSocketEmitter(context, mock_router, "test_conn_123")
        
        # Attempt to send mission critical event
        success = await emitter.notify_agent_started("TestAgent", {"test": "data"})
        
        # Verify complete failure with loud error logging
        assert not success
        assert emitter.events_failed == 1
        
        # Verify critical logging was used
        mock_logger.critical.assert_called()
        critical_calls = mock_logger.critical.call_args_list
        
        # Should have multiple critical log entries
        assert len(critical_calls) > 0
        
        error_messages = [str(call) for call in critical_calls]
        # Should log connection validation failure
        assert any("Connection validation failed" in msg for msg in error_messages)
        assert any("BUSINESS VALUE FAILURE" in msg for msg in error_messages)
    
    def test_validator_singleton_behavior(self):
        """Test that validator singleton works correctly."""
        validator1 = get_websocket_validator()
        validator2 = get_websocket_validator()
        
        assert validator1 is validator2
        
        # Reset and verify new instance
        reset_websocket_validator()
        validator3 = get_websocket_validator()
        
        assert validator1 is not validator3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])