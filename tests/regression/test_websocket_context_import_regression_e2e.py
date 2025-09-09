"""
Regression Test - WebSocket Context Import Failure (E2E)

🚨 CRITICAL REGRESSION TEST 🚨
This test MUST FAIL initially to prove the regression exists.

Purpose: Prove WebSocketRequestContext import regression breaks end-to-end agent-WebSocket flows
Expected State: FAILING - demonstrates business impact on chat value delivery
After Fix: Should pass when WebSocketRequestContext is properly exported

Business Impact:
- Breaks agent execution with WebSocket event delivery
- Prevents users from receiving real-time agent progress updates
- Violates Section 6 mission critical WebSocket agent events
- Destroys substantive chat value delivery

E2E Scope:
- Tests complete agent-WebSocket integration flow
- Validates real WebSocket connections (no mocks per CLAUDE.md)
- Ensures proper authentication and user context handling
- Tests mission critical events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
"""

import pytest
import asyncio
import json
from typing import Dict, List, Any
from datetime import datetime, timedelta

# Test authentication requirement per CLAUDE.md
try:
    from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_test_context
    AUTH_HELPER_AVAILABLE = True
except ImportError as e:
    AUTH_HELPER_AVAILABLE = False
    AUTH_HELPER_ERROR = str(e)

# Test the problematic imports that cause the regression
try:
    from netra_backend.app.websocket_core import WebSocketContext
    WEBSOCKET_CONTEXT_AVAILABLE = True
    WEBSOCKET_CONTEXT_ERROR = None
except ImportError as e:
    WEBSOCKET_CONTEXT_AVAILABLE = False
    WEBSOCKET_CONTEXT_ERROR = str(e)

try:
    # This should FAIL - proving the regression affects E2E flows
    from netra_backend.app.websocket_core import WebSocketRequestContext
    WEBSOCKET_REQUEST_CONTEXT_AVAILABLE = True
    WEBSOCKET_REQUEST_CONTEXT_ERROR = None
except ImportError as e:
    WEBSOCKET_REQUEST_CONTEXT_AVAILABLE = False
    WEBSOCKET_REQUEST_CONTEXT_ERROR = str(e)

# Import WebSocket manager components
try:
    from netra_backend.app.websocket_core import (
        create_websocket_manager,
        IsolatedWebSocketManager,
        UnifiedWebSocketEmitter
    )
    WEBSOCKET_MANAGER_AVAILABLE = True
    WEBSOCKET_MANAGER_ERROR = None
except ImportError as e:
    WEBSOCKET_MANAGER_AVAILABLE = False
    WEBSOCKET_MANAGER_ERROR = str(e)

# Import agent components that depend on WebSocket context
try:
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    AGENT_BRIDGE_AVAILABLE = True
    AGENT_BRIDGE_ERROR = None
except ImportError as e:
    AGENT_BRIDGE_AVAILABLE = False
    AGENT_BRIDGE_ERROR = str(e)

# Import execution context
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    USER_CONTEXT_AVAILABLE = True
    USER_CONTEXT_ERROR = None
except ImportError as e:
    USER_CONTEXT_AVAILABLE = False
    USER_CONTEXT_ERROR = str(e)

# WebSocket test utilities
try:
    import websockets
    from websockets.exceptions import ConnectionClosed
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False


@pytest.mark.e2e
class TestWebSocketContextE2ERegression:
    """E2E tests for WebSocket context import regression.
    
    These tests validate that the regression breaks real end-to-end flows
    that deliver business value through agent-WebSocket integration.
    """
    
    @pytest.fixture(autouse=True)
    async def setup_authenticated_context(self):
        """🚨 CRITICAL: All E2E tests MUST use authentication per CLAUDE.md."""
        if not AUTH_HELPER_AVAILABLE:
            pytest.skip(f"E2E auth helper not available: {AUTH_HELPER_ERROR}")
        
        self.auth_helper = E2EAuthHelper()
        self.auth_context = await create_authenticated_test_context()
        
        # Validate authentication is working
        assert self.auth_context.user_id is not None, "Authentication failed - no user_id"
        assert self.auth_context.jwt_token is not None, "Authentication failed - no JWT token"
    
    @pytest.fixture
    def websocket_url(self):
        """WebSocket URL for testing."""
        # Use test environment WebSocket endpoint
        return "ws://localhost:8000/ws"
    
    @pytest.fixture
    def user_execution_context(self):
        """Create authenticated user execution context for E2E testing."""
        if not USER_CONTEXT_AVAILABLE:
            pytest.skip(f"UserExecutionContext not available: {USER_CONTEXT_ERROR}")
        
        return UserExecutionContext(
            user_id=self.auth_context.user_id,
            thread_id=f"e2e_thread_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            run_id=f"e2e_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            request_id=f"e2e_req_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
    
    @pytest.mark.asyncio
    async def test_websocket_connection_with_context_creation(self, websocket_url, user_execution_context):
        """
        Test that WebSocket connections can be established with proper context creation.
        
        This test validates the baseline E2E functionality works.
        """
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("WebSocket client library not available")
        
        if not WEBSOCKET_CONTEXT_AVAILABLE:
            pytest.fail(f"WebSocketContext not available for E2E testing: {WEBSOCKET_CONTEXT_ERROR}")
        
        try:
            # Attempt to connect with authentication
            headers = {
                "Authorization": f"Bearer {self.auth_context.jwt_token}",
                "X-User-ID": self.auth_context.user_id,
                "X-Thread-ID": user_execution_context.thread_id
            }
            
            async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
                # Send a test message
                test_message = {
                    "type": "test_context_creation",
                    "user_id": user_execution_context.user_id,
                    "thread_id": user_execution_context.thread_id,
                    "run_id": user_execution_context.run_id
                }
                
                await websocket.send(json.dumps(test_message))
                
                # Wait for response with timeout
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    # Validate response includes context information
                    assert response_data.get("status") in ["success", "acknowledged"], f"Unexpected response: {response_data}"
                    
                except asyncio.TimeoutError:
                    pytest.fail("WebSocket connection established but no response received - context creation may have failed")
        
        except Exception as e:
            pytest.fail(f"E2E WebSocket connection with context creation failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_request_context_alias_in_e2e_flow_EXPECTED_TO_FAIL(self, websocket_url, user_execution_context):
        """
        🚨 REGRESSION TEST: Test E2E flow that depends on WebSocketRequestContext alias.
        
        This test MUST FAIL initially, proving that E2E flows break due to the import regression.
        """
        if not WEBSOCKET_REQUEST_CONTEXT_AVAILABLE:
            pytest.fail(
                f"🚨 E2E REGRESSION CONFIRMED: WebSocketRequestContext alias not available for E2E flows. "
                f"Error: {WEBSOCKET_REQUEST_CONTEXT_ERROR}. "
                f"This breaks end-to-end agent-WebSocket integration and substantive chat value delivery."
            )
        
        # If the alias is available (after fix), test E2E flow with it
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("WebSocket client library not available")
        
        try:
            # Simulate E2E flow that would use WebSocketRequestContext
            headers = {
                "Authorization": f"Bearer {self.auth_context.jwt_token}",
                "X-User-ID": self.auth_context.user_id,
                "X-Thread-ID": user_execution_context.thread_id,
                "X-Context-Type": "WebSocketRequestContext"  # Indicate we're using the alias
            }
            
            async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
                test_message = {
                    "type": "test_request_context_alias",
                    "context_type": "WebSocketRequestContext",
                    "user_id": user_execution_context.user_id
                }
                
                await websocket.send(json.dumps(test_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                # Validate the E2E flow worked with the alias
                assert response_data.get("context_type_used") == "WebSocketRequestContext", (
                    "E2E flow should successfully use WebSocketRequestContext alias"
                )
        
        except Exception as e:
            pytest.fail(f"E2E flow with WebSocketRequestContext alias failed: {e}")
    
    @pytest.mark.asyncio
    async def test_agent_websocket_integration_with_context_EXPECTED_TO_FAIL(self, websocket_url, user_execution_context):
        """
        🚨 REGRESSION TEST: Test complete agent-WebSocket integration with context handling.
        
        This test validates the mission critical WebSocket agent events (Section 6 of CLAUDE.md).
        This test MUST FAIL initially, proving business value is broken.
        """
        if not AGENT_BRIDGE_AVAILABLE:
            pytest.skip(f"AgentWebSocketBridge not available: {AGENT_BRIDGE_ERROR}")
        
        if not WEBSOCKETS_AVAILABLE:
            pytest.skip("WebSocket client library not available")
        
        # Track critical events that should be received
        critical_events = [
            "agent_started",
            "agent_thinking", 
            "tool_executing",
            "tool_completed",
            "agent_completed"
        ]
        received_events = []
        
        try:
            # Connect with authenticated context
            headers = {
                "Authorization": f"Bearer {self.auth_context.jwt_token}",
                "X-User-ID": self.auth_context.user_id,
                "X-Thread-ID": user_execution_context.thread_id,
                "X-Run-ID": user_execution_context.run_id
            }
            
            async with websockets.connect(websocket_url, extra_headers=headers) as websocket:
                # Start an agent execution that should trigger WebSocket events
                agent_request = {
                    "type": "execute_agent",
                    "agent_type": "test_agent",
                    "context": {
                        "user_id": user_execution_context.user_id,
                        "thread_id": user_execution_context.thread_id,
                        "run_id": user_execution_context.run_id
                    },
                    "require_websocket_context": True  # This should trigger the regression
                }
                
                await websocket.send(json.dumps(agent_request))
                
                # Collect events with timeout
                timeout_time = datetime.now() + timedelta(seconds=10)
                
                while datetime.now() < timeout_time and len(received_events) < len(critical_events):
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        event_data = json.loads(message)
                        
                        if event_data.get("type") in critical_events:
                            received_events.append(event_data.get("type"))
                            
                        # Check if we got an error related to context import
                        if event_data.get("type") == "error":
                            error_msg = event_data.get("message", "")
                            if "WebSocketRequestContext" in error_msg or "import" in error_msg:
                                pytest.fail(
                                    f"🚨 AGENT-WEBSOCKET INTEGRATION BROKEN: Import error in E2E flow: {error_msg}. "
                                    f"The WebSocketRequestContext regression breaks agent event delivery."
                                )
                    
                    except asyncio.TimeoutError:
                        break  # Continue collecting events until timeout
                
                # Validate that we received critical events
                missing_events = [event for event in critical_events if event not in received_events]
                
                if missing_events:
                    pytest.fail(
                        f"🚨 MISSION CRITICAL EVENTS MISSING: E2E agent-WebSocket integration failed to deliver "
                        f"critical events: {missing_events}. Received: {received_events}. "
                        f"This regression breaks substantive chat value delivery per Section 6 of CLAUDE.md."
                    )
        
        except ConnectionClosed:
            pytest.fail("WebSocket connection closed unexpectedly during agent-WebSocket integration test")
        except Exception as e:
            # Check if the error is related to the WebSocketRequestContext regression
            if "WebSocketRequestContext" in str(e) or "import" in str(e).lower():
                pytest.fail(
                    f"🚨 CONTEXT IMPORT REGRESSION IN E2E: {e}. "
                    f"The missing WebSocketRequestContext export breaks agent-WebSocket integration."
                )
            else:
                pytest.fail(f"Agent-WebSocket integration E2E test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_manager_factory_e2e_with_context_EXPECTED_TO_FAIL(self, user_execution_context):
        """
        🚨 REGRESSION TEST: Test WebSocket manager factory E2E integration with context.
        
        This validates that the factory pattern works end-to-end with proper context handling.
        """
        if not WEBSOCKET_MANAGER_AVAILABLE:
            pytest.skip(f"WebSocket manager components not available: {WEBSOCKET_MANAGER_ERROR}")
        
        try:
            # Create WebSocket manager using factory pattern
            manager = await create_websocket_manager(user_execution_context)
            assert manager is not None, "WebSocket manager creation failed"
            assert isinstance(manager, IsolatedWebSocketManager), "Wrong manager type returned"
            
            # Test that the manager can handle context-based operations
            # This simulates the E2E flow where context types matter
            context_info = {
                "user_id": user_execution_context.user_id,
                "thread_id": user_execution_context.thread_id,
                "run_id": user_execution_context.run_id
            }
            
            # If WebSocketRequestContext is not available, this might affect manager behavior
            if not WEBSOCKET_REQUEST_CONTEXT_AVAILABLE:
                # Check if the manager handles context type validation properly
                # This is where the regression might manifest in E2E scenarios
                try:
                    # Attempt an operation that might internally reference WebSocketRequestContext
                    result = await manager.validate_context_compatibility(context_info)
                    # If this succeeds despite the missing alias, the system has workarounds
                    # But it still represents a regression in API completeness
                    pass
                except AttributeError as ae:
                    if "WebSocketRequestContext" in str(ae):
                        pytest.fail(
                            f"🚨 E2E FACTORY REGRESSION: WebSocket manager factory fails due to missing "
                            f"WebSocketRequestContext alias: {ae}. This breaks E2E integration flows."
                        )
                    raise  # Re-raise if not related to our regression
            
        except Exception as e:
            if "WebSocketRequestContext" in str(e):
                pytest.fail(
                    f"🚨 E2E MANAGER FACTORY REGRESSION: {e}. "
                    f"The missing WebSocketRequestContext export affects factory pattern E2E usage."
                )
            else:
                pytest.fail(f"WebSocket manager factory E2E test failed: {e}")
    
    def test_e2e_regression_impact_summary(self):
        """
        Document the complete E2E impact of the WebSocketRequestContext regression.
        
        This test provides a comprehensive view of what breaks at the E2E level.
        """
        impact_summary = {
            "websocket_context_available": WEBSOCKET_CONTEXT_AVAILABLE,
            "websocket_request_context_available": WEBSOCKET_REQUEST_CONTEXT_AVAILABLE,
            "websocket_manager_available": WEBSOCKET_MANAGER_AVAILABLE,
            "agent_bridge_available": AGENT_BRIDGE_AVAILABLE,
            "auth_helper_available": AUTH_HELPER_AVAILABLE,
            "websockets_client_available": WEBSOCKETS_AVAILABLE,
        }
        
        broken_components = [comp for comp, available in impact_summary.items() if not available]
        working_components = [comp for comp, available in impact_summary.items() if available]
        
        print("\\n🔍 E2E Regression Impact Analysis:")
        print(f"✅ Working components ({len(working_components)}):")
        for comp in working_components:
            print(f"   - {comp}")
        
        print(f"\\n❌ Broken components ({len(broken_components)}):")
        for comp in broken_components:
            print(f"   - {comp}")
        
        if not WEBSOCKET_REQUEST_CONTEXT_AVAILABLE:
            print(f"\\n🚨 PRIMARY REGRESSION: WebSocketRequestContext alias not exported")
            print(f"   Error: {WEBSOCKET_REQUEST_CONTEXT_ERROR}")
            print(f"   Business Impact:")
            print(f"   - Breaks agent-WebSocket integration patterns")
            print(f"   - Prevents delivery of mission critical WebSocket events")
            print(f"   - Violates backward compatibility and SSOT principles")
            print(f"   - Destroys substantive chat value delivery (Section 6 CLAUDE.md)")
        
        # This test documents but doesn't fail - specific regression tests above handle the failures
        assert True, "E2E impact analysis complete - see output for regression details"


if __name__ == "__main__":
    # Allow running this test file directly to see the E2E regression
    pytest.main([__file__, "-v", "-s", "-m", "e2e"])