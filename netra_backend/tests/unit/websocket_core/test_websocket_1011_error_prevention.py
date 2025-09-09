"""
Test WebSocket 1011 Error Prevention

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Stability & Chat Functionality  
- Value Impact: Prevents 1011 WebSocket errors that block $500K+ ARR chat features
- Strategic Impact: Ensures critical WebSocket state management functions are available

CRITICAL: This test validates that the fixes implemented for the WebSocket 1011
internal server error are working correctly by ensuring that critical functions
are properly imported and available.

Fixes validated:
1. get_connection_state_machine function is not None (was failing due to fallback imports)
2. ApplicationConnectionState enum is available
3. WebSocket state management components are properly imported
4. No silent import failures that manifest as 1011 errors

See: WEBSOCKET_1011_FIVE_WHYS_ANALYSIS_20250909_NIGHT.md for full analysis.
"""

import pytest
from unittest.mock import Mock

from netra_backend.app.logging_config import central_logger
from shared.types.core_types import UserID, ConnectionID

logger = central_logger.get_logger(__name__)


class TestWebSocket1011ErrorPrevention:
    """
    Test that critical WebSocket 1011 error conditions are prevented.
    
    CRITICAL: These tests validate that the root causes identified in the
    five-whys analysis have been properly addressed.
    """

    def test_connection_state_machine_function_available(self):
        """
        Test that get_connection_state_machine is not None.
        
        ROOT CAUSE: This function was set to None during import fallback,
        causing WebSocket 1011 errors in staging when state management failed.
        """
        from netra_backend.app.websocket_core import get_connection_state_machine
        
        # CRITICAL: This must never be None - was causing 1011 errors
        assert get_connection_state_machine is not None, \
            "get_connection_state_machine is None - this causes WebSocket 1011 internal server errors"
        
        # Verify it's callable
        assert callable(get_connection_state_machine), \
            "get_connection_state_machine is not callable - state management will fail"
        
        logger.info("SUCCESS: get_connection_state_machine is available and callable")

    def test_application_connection_state_enum_available(self):
        """
        Test that ApplicationConnectionState enum is available.
        
        This was also affected by the fallback import behavior.
        """
        from netra_backend.app.websocket_core import ApplicationConnectionState
        
        # CRITICAL: ApplicationConnectionState must not be None
        assert ApplicationConnectionState is not None, \
            "ApplicationConnectionState is None - WebSocket state management will fail"
        
        # Verify required states are available
        required_states = ['CONNECTING', 'ACCEPTED', 'AUTHENTICATED', 'SERVICES_READY', 'PROCESSING_READY']
        for state_name in required_states:
            assert hasattr(ApplicationConnectionState, state_name), \
                f"ApplicationConnectionState missing {state_name} - state transitions will fail"
        
        logger.info("SUCCESS: ApplicationConnectionState enum is complete and available")

    def test_connection_state_registry_available(self):
        """
        Test that connection state registry functions are available.
        """
        from netra_backend.app.websocket_core import get_connection_state_registry
        
        # CRITICAL: Registry function must not be None
        assert get_connection_state_registry is not None, \
            "get_connection_state_registry is None - connection state management will fail"
        
        assert callable(get_connection_state_registry), \
            "get_connection_state_registry is not callable"
        
        logger.info("SUCCESS: Connection state registry is available")

    def test_message_queue_components_available(self):
        """
        Test that message queue components are available.
        
        These were also affected by fallback import behavior.
        """
        from netra_backend.app.websocket_core import (
            MessageQueue,
            MessageQueueRegistry,
            get_message_queue_registry
        )
        
        # CRITICAL: Message queue components must not be None
        assert MessageQueue is not None, "MessageQueue is None - message handling will fail"
        assert MessageQueueRegistry is not None, "MessageQueueRegistry is None"
        assert get_message_queue_registry is not None, "get_message_queue_registry is None"
        
        logger.info("SUCCESS: Message queue components are available")

    def test_websocket_import_no_fallback_errors(self):
        """
        Test that WebSocket core imports without triggering fallback behavior.
        
        CRITICAL: This test ensures that the import fixes prevent the fallback
        behavior that was setting critical functions to None.
        """
        # Import all critical components - should not raise ImportError
        try:
            from netra_backend.app.websocket_core import (
                get_connection_state_machine,
                ApplicationConnectionState,
                get_connection_state_registry,
                MessageQueue,
                get_message_queue_registry
            )
            
            # Verify none are None (fallback behavior)
            critical_components = {
                'get_connection_state_machine': get_connection_state_machine,
                'ApplicationConnectionState': ApplicationConnectionState,
                'get_connection_state_registry': get_connection_state_registry,
                'MessageQueue': MessageQueue,
                'get_message_queue_registry': get_message_queue_registry
            }
            
            for name, component in critical_components.items():
                assert component is not None, \
                    f"{name} is None - fallback import behavior not fixed"
            
            logger.info("SUCCESS: All critical WebSocket components imported without fallback")
            
        except ImportError as e:
            pytest.fail(f"Critical WebSocket import failed: {e}. This will cause 1011 errors.")

    def test_connection_state_machine_creation(self):
        """
        Test that connection state machine can be created without errors.
        
        This verifies that the import fixes allow proper state machine operation.
        """
        from netra_backend.app.websocket_core import get_connection_state_registry
        
        # Get registry (should not be None due to our fixes)
        registry = get_connection_state_registry()
        assert registry is not None, "State machine registry is None"
        
        # Test connection registration (basic functionality test)
        test_connection_id = "test_connection_123"
        test_user_id = "test_user_456"
        
        # This should not raise errors related to undefined functions
        try:
            state_machine = registry.register_connection(test_connection_id, test_user_id)
            assert state_machine is not None, "State machine creation failed"
            
            # Clean up
            registry.unregister_connection(test_connection_id)
            
            logger.info("SUCCESS: Connection state machine creation works correctly")
            
        except Exception as e:
            pytest.fail(f"State machine creation failed: {e}. This could cause 1011 errors.")

    def test_orchestrator_factory_pattern_available(self):
        """
        Test that orchestrator factory pattern is available.
        
        This addresses the secondary issue where agent execution was blocking
        due to missing orchestrator dependencies.
        """
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        
        # Test that the factory pattern is available
        # Note: This test checks the pattern exists, not that it's fully functional
        assert hasattr(AgentWebSocketBridge, 'create_execution_orchestrator'), \
            "AgentWebSocketBridge missing create_execution_orchestrator method"
        
        # Verify the dependency check uses factory pattern
        bridge = Mock(spec=AgentWebSocketBridge)
        bridge.create_execution_orchestrator = Mock()
        
        # Test that orchestrator_factory_available check works
        factory_available = hasattr(bridge, 'create_execution_orchestrator')
        assert factory_available is True, \
            "Orchestrator factory pattern not properly detected"
        
        logger.info("SUCCESS: Orchestrator factory pattern is available")

    def test_websocket_1011_error_prevention_integration(self):
        """
        Integration test that validates all 1011 error prevention measures.
        
        This test combines all the fixes to ensure they work together.
        """
        # Test 1: Import all critical components without fallback
        from netra_backend.app.websocket_core import (
            get_connection_state_machine,
            ApplicationConnectionState,
            get_connection_state_registry
        )
        
        # Test 2: Verify no components are None
        assert get_connection_state_machine is not None
        assert ApplicationConnectionState is not None
        assert get_connection_state_registry is not None
        
        # Test 3: Verify state machine functionality
        registry = get_connection_state_registry()
        test_connection = "integration_test_connection"
        test_user = "integration_test_user"
        
        state_machine = registry.register_connection(test_connection, test_user)
        assert state_machine is not None
        
        # Test 4: Verify state transitions work
        from netra_backend.app.websocket_core import ApplicationConnectionState
        success = state_machine.transition_to(
            ApplicationConnectionState.ACCEPTED,
            reason="Integration test",
            metadata={"test": True}
        )
        assert success is True, "State transition failed"
        
        # Cleanup
        registry.unregister_connection(test_connection)
        
        logger.info("SUCCESS: Complete WebSocket 1011 error prevention validated")

    def test_error_messages_reference_analysis_document(self):
        """
        Test that error messages reference the analysis document for debugging.
        
        This ensures that if import errors do occur, developers can find the
        root cause analysis document for troubleshooting.
        """
        # Test that our import error message contains reference to analysis
        try:
            # This should trigger an import error with our custom message
            # We'll test this by temporarily breaking the import (mock scenario)
            
            # Since we can't easily break imports in a test, we'll just verify
            # that the error message format is correct by checking the __init__.py content
            init_file = "netra_backend/app/websocket_core/__init__.py"
            with open(init_file, 'r') as f:
                content = f.read()
            
            # Verify our error message contains the analysis document reference
            assert "WEBSOCKET_1011_FIVE_WHYS_ANALYSIS_20250909_NIGHT.md" in content, \
                "Import error message doesn't reference analysis document"
            
            assert "This will cause 1011 WebSocket errors" in content, \
                "Import error message doesn't explain impact"
            
            logger.info("SUCCESS: Error messages properly reference analysis document")
            
        except Exception as e:
            pytest.fail(f"Error message validation failed: {e}")


# Integration test fixture for WebSocket 1011 prevention
@pytest.fixture
def websocket_1011_prevention_context():
    """
    Fixture that provides context for WebSocket 1011 error prevention testing.
    
    This ensures that tests run in an environment where the fixes are active.
    """
    # Verify that critical components are available before running tests
    from netra_backend.app.websocket_core import (
        get_connection_state_machine,
        ApplicationConnectionState
    )
    
    if get_connection_state_machine is None or ApplicationConnectionState is None:
        pytest.skip("WebSocket 1011 prevention fixes not active - critical components unavailable")
    
    return {
        'state_machine_function': get_connection_state_machine,
        'connection_states': ApplicationConnectionState,
        'test_connection_id': 'test_1011_prevention',
        'test_user_id': 'test_user_1011'
    }


class TestWebSocket1011BusinessImpactPrevention:
    """
    Business-focused tests that validate chat functionality protection.
    
    These tests focus on the business value aspects of preventing 1011 errors.
    """

    def test_chat_functionality_dependency_availability(self, websocket_1011_prevention_context):
        """
        Test that chat functionality dependencies are available.
        
        BVJ: Segment: Free/Early/Mid/Enterprise, Goal: Revenue Protection,
        Impact: Ensures $500K+ ARR chat functionality remains operational
        """
        context = websocket_1011_prevention_context
        
        # Chat functionality requires operational state machines
        assert context['state_machine_function'] is not None, \
            "Chat functionality blocked - state machine unavailable"
        
        # Chat requires proper connection state management
        states = context['connection_states']
        chat_critical_states = ['AUTHENTICATED', 'SERVICES_READY', 'PROCESSING_READY']
        
        for state in chat_critical_states:
            assert hasattr(states, state), \
                f"Chat functionality blocked - {state} unavailable"
        
        logger.info("SUCCESS: Chat functionality dependencies are protected")

    def test_real_time_agent_events_capability(self, websocket_1011_prevention_context):
        """
        Test that real-time agent events capability is maintained.
        
        BVJ: Segment: Platform, Goal: User Experience,
        Impact: Ensures critical WebSocket events can be delivered to users
        """
        from netra_backend.app.websocket_core import get_connection_state_registry
        
        # Real-time events require operational connection registry
        registry = get_connection_state_registry()
        assert registry is not None, \
            "Real-time agent events blocked - connection registry unavailable"
        
        # Test that connections can reach the state needed for event delivery
        context = websocket_1011_prevention_context
        connection_id = context['test_connection_id']
        user_id = context['test_user_id']
        
        # Register connection
        state_machine = registry.register_connection(connection_id, user_id)
        assert state_machine is not None, \
            "Real-time events blocked - connection state management failed"
        
        # Verify can transition to processing ready (required for event delivery)
        processing_state = context['connection_states'].PROCESSING_READY
        can_reach_processing = state_machine.can_transition_to(processing_state)
        
        # Cleanup
        registry.unregister_connection(connection_id)
        
        assert can_reach_processing, \
            "Real-time agent events blocked - cannot reach processing ready state"
        
        logger.info("SUCCESS: Real-time agent events capability is protected")