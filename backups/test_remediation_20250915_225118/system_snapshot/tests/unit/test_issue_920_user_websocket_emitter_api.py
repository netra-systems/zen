"""
Test Issue #920: UserWebSocketEmitter API Accessibility and Functionality

Business Value Justification (BVJ):
- Segment: Platform/Internal - WebSocket Infrastructure Validation
- Business Goal: Validate UserWebSocketEmitter API is accessible and functional for Issue #920
- Value Impact: Ensures WebSocket event emission infrastructure works correctly
- Strategic Impact: Critical for real-time agent communication and user experience

This test suite validates Issue #920 specific UserWebSocketEmitter behaviors:
- UserWebSocketEmitter API should be importable and accessible
- Emitter should function correctly with various manager configurations
- Event emission should work with proper error handling
- API should maintain backward compatibility during Issue #920 fixes

TEST DESIGN NOTE: These tests validate that UserWebSocketEmitter API works correctly
and is not broken by Issue #920 ExecutionEngineFactory changes.
"""

import asyncio
import pytest
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, Any, Dict

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    UserWebSocketEmitter,
    AgentInstanceFactory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


class Issue920UserWebSocketEmitterApiTests(SSotBaseTestCase):
    """Test UserWebSocketEmitter API accessibility and functionality for Issue #920."""
    
    def setup_method(self, method):
        """Setup test environment for Issue #920 UserWebSocketEmitter API tests."""
        super().setup_method(method)
        
        # Test identifiers
        self.test_user_id = f"issue920_ws_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"issue920_ws_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"issue920_ws_run_{uuid.uuid4().hex[:8]}"
        
        # Mock WebSocket manager/bridge with complete interface
        self.mock_websocket_manager = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_manager.notify_agent_started = AsyncMock(return_value=True)
        self.mock_websocket_manager.notify_agent_completed = AsyncMock(return_value=True)
        self.mock_websocket_manager.notify_tool_executing = AsyncMock(return_value=True)
        self.mock_websocket_manager.emit_critical_event = AsyncMock(return_value=True)
        self.mock_websocket_manager.emit_user_event = AsyncMock(return_value=True)
        self.mock_websocket_manager.emit_event = AsyncMock(return_value=True)
        self.mock_websocket_manager.is_connection_active = Mock(return_value=True)
        
        # User execution context
        self.user_context = Mock(spec=UserExecutionContext)
        self.user_context.user_id = self.test_user_id
        self.user_context.thread_id = self.test_thread_id
        self.user_context.run_id = self.test_run_id
        self.user_context.session_id = f"session_{uuid.uuid4().hex[:8]}"
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_user_websocket_emitter_import_accessibility(self):
        """
        ISSUE #920 VALIDATION: UserWebSocketEmitter should be importable and accessible.
        
        This test validates that Issue #920 fixes don't break UserWebSocketEmitter imports
        and that the API remains accessible for agent factory usage.
        """
        # When: Importing UserWebSocketEmitter
        # Then: Import should succeed without errors
        assert UserWebSocketEmitter is not None
        
        # And: UserWebSocketEmitter should be the correct class/alias
        # Note: UserWebSocketEmitter should be an alias to UnifiedWebSocketEmitter
        assert UserWebSocketEmitter == UnifiedWebSocketEmitter
        
        # And: Class should be callable
        assert callable(UserWebSocketEmitter)
        
        self.record_metric("user_websocket_emitter_import_success", True)
    
    @pytest.mark.unit
    def test_user_websocket_emitter_initialization_with_manager(self):
        """
        ISSUE #920 VALIDATION: UserWebSocketEmitter should initialize with manager parameter.
        
        This validates the correct API usage pattern that should work after Issue #920 fixes.
        """
        # When: Creating UserWebSocketEmitter with manager parameter
        emitter = UserWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id,
            context=self.user_context
        )
        
        # Then: Emitter should initialize successfully
        assert emitter is not None
        assert emitter.user_id == self.test_user_id
        assert emitter.context is self.user_context
        
        # And: Emitter should have required attributes
        assert hasattr(emitter, 'metrics')
        assert hasattr(emitter, 'user_id')
        assert hasattr(emitter, 'context')
        
        # And: Metrics should be initialized
        assert emitter.metrics.total_events == 0
        assert emitter.metrics.last_event_time is None
        assert hasattr(emitter.metrics, 'created_at')
        
        self.record_metric("user_websocket_emitter_initialization_success", True)
    
    @pytest.mark.unit
    def test_user_websocket_emitter_initialization_with_none_manager(self):
        """
        ISSUE #920 EDGE CASE: UserWebSocketEmitter behavior with None manager.
        
        This tests how UserWebSocketEmitter handles None manager, which might occur
        during Issue #920 scenarios where ExecutionEngineFactory has websocket_bridge=None.
        """
        # When: Attempting to create UserWebSocketEmitter with None manager
        try:
            emitter = UserWebSocketEmitter(
                manager=None,  # This might fail or might be handled gracefully
                user_id=self.test_user_id,
                context=self.user_context
            )
            
            # If successful: Validate emitter handles None manager gracefully
            assert emitter is not None
            assert emitter.user_id == self.test_user_id
            
            self.record_metric("none_manager_handled_gracefully", True)
            
        except (TypeError, ValueError, AttributeError) as e:
            # Expected behavior: UserWebSocketEmitter requires valid manager
            assert "manager" in str(e).lower() or "required" in str(e).lower()
            
            self.record_metric("none_manager_validation_enforced", True)
    
    @pytest.mark.unit
    async def test_user_websocket_emitter_agent_started_notification(self):
        """
        ISSUE #920 VALIDATION: UserWebSocketEmitter should emit agent started notifications.
        
        This validates that the core WebSocket functionality continues to work
        correctly after Issue #920 fixes.
        """
        # Given: Properly initialized UserWebSocketEmitter
        emitter = UserWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id,
            context=self.user_context
        )
        
        # When: Sending agent started notification
        await emitter.notify_agent_started(
            agent_name="test_agent_issue_920",
            context={"test": "issue_920_validation"}
        )
        
        # Then: WebSocket manager should receive the notification
        # Note: UnifiedWebSocketEmitter uses emit_critical_event internally
        assert self.mock_websocket_manager.emit_critical_event.call_count >= 1
        
        # And: Emitter metrics should be updated
        assert emitter.metrics.total_events >= 1
        assert emitter.metrics.last_event_time is not None
        
        self.record_metric("agent_started_notification_success", True)
    
    @pytest.mark.unit
    async def test_user_websocket_emitter_multiple_events_isolation(self):
        """
        ISSUE #920 VALIDATION: Multiple UserWebSocketEmitter instances should maintain isolation.
        
        This validates that Issue #920 fixes don't break user isolation in WebSocket events.
        """
        # Given: Two separate UserWebSocketEmitter instances for different users
        user2_id = f"issue920_ws_user2_{uuid.uuid4().hex[:8]}"
        user2_context = Mock(spec=UserExecutionContext)
        user2_context.user_id = user2_id
        user2_context.thread_id = f"thread2_{uuid.uuid4().hex[:8]}"
        user2_context.run_id = f"run2_{uuid.uuid4().hex[:8]}"
        
        emitter1 = UserWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id,
            context=self.user_context
        )
        
        emitter2 = UserWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=user2_id,
            context=user2_context
        )
        
        # When: Sending notifications from both emitters
        await emitter1.notify_agent_started(
            agent_name="agent_user1",
            context={"user": self.test_user_id}
        )
        
        await emitter2.notify_agent_started(
            agent_name="agent_user2", 
            context={"user": user2_id}
        )
        
        # Then: Both emitters should maintain separate state
        assert emitter1.user_id != emitter2.user_id
        assert emitter1.context != emitter2.context
        
        # And: Metrics should be maintained separately
        assert emitter1.metrics.total_events >= 1
        assert emitter2.metrics.total_events >= 1
        
        # And: WebSocket manager should receive both notifications
        assert self.mock_websocket_manager.emit_critical_event.call_count >= 2
        
        self.record_metric("multiple_emitter_isolation_validated", True)
    
    @pytest.mark.unit
    async def test_user_websocket_emitter_error_handling(self):
        """
        ISSUE #920 VALIDATION: UserWebSocketEmitter should handle WebSocket errors gracefully.
        
        This validates that error handling continues to work correctly after Issue #920 fixes.
        """
        # Given: UserWebSocketEmitter with manager that fails
        failing_manager = Mock(spec=AgentWebSocketBridge)
        failing_manager.emit_critical_event = AsyncMock(return_value=False)  # Simulate failure
        failing_manager.is_connection_active = Mock(return_value=False)
        
        emitter = UserWebSocketEmitter(
            manager=failing_manager,
            user_id=self.test_user_id,
            context=self.user_context
        )
        
        # When: Attempting to send notification that fails
        # Note: UnifiedWebSocketEmitter should handle failures gracefully
        await emitter.notify_agent_started(
            agent_name="failing_agent",
            context={"test": "error_handling"}
        )
        
        # Then: Emitter should handle failure gracefully (no exception raised)
        # And: Metrics should still be updated (attempt was made)
        assert emitter.metrics.total_events >= 1
        assert emitter.metrics.last_event_time is not None
        
        self.record_metric("error_handling_validated", True)
    
    @pytest.mark.unit
    def test_user_websocket_emitter_api_compatibility(self):
        """
        ISSUE #920 VALIDATION: UserWebSocketEmitter API should maintain backward compatibility.
        
        This validates that the API surface remains consistent after Issue #920 fixes.
        """
        # When: Creating UserWebSocketEmitter
        emitter = UserWebSocketEmitter(
            manager=self.mock_websocket_manager,
            user_id=self.test_user_id,
            context=self.user_context
        )
        
        # Then: Required API methods should be present
        required_methods = [
            'notify_agent_started',
            'notify_agent_completed', 
            'notify_tool_executing'
        ]
        
        for method_name in required_methods:
            assert hasattr(emitter, method_name), f"Missing required method: {method_name}"
            assert callable(getattr(emitter, method_name)), f"Method not callable: {method_name}"
        
        # And: Required attributes should be present
        required_attributes = [
            'user_id',
            'context',
            'metrics'
        ]
        
        for attr_name in required_attributes:
            assert hasattr(emitter, attr_name), f"Missing required attribute: {attr_name}"
        
        self.record_metric("api_compatibility_validated", True)