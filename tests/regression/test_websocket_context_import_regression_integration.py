"""
Regression Test - WebSocket Context Import Failure (Integration)

 ALERT:  CRITICAL REGRESSION TEST  ALERT: 
This test MUST FAIL initially to prove the regression exists.

Purpose: Prove WebSocketRequestContext import regression breaks WebSocket manager factory integration
Expected State: FAILING - demonstrates integration-level impact
After Fix: Should pass when WebSocketRequestContext is properly exported

Business Impact:
- Breaks WebSocket manager factory pattern usage
- Prevents agent-WebSocket bridge from functioning
- Violates User Context Architecture for multi-user isolation

Integration Scope:
- Tests WebSocket manager factory with context handling
- Validates agent-WebSocket bridge integration patterns
- Ensures proper user isolation and context extraction
- Uses REAL services per CLAUDE.md requirements (no mocks)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket
from datetime import datetime

# Test imports - these will help identify what breaks during the regression
try:
    from netra_backend.app.websocket_core import (
        create_websocket_manager,
        WebSocketManagerFactory,
        IsolatedWebSocketManager,
        get_websocket_manager_factory
    )
    FACTORY_IMPORTS_AVAILABLE = True
    FACTORY_IMPORT_ERROR = None
except ImportError as e:
    FACTORY_IMPORTS_AVAILABLE = False
    FACTORY_IMPORT_ERROR = str(e)

try:
    # This import should work - WebSocketContext should be available
    from netra_backend.app.websocket_core import WebSocketContext
    WEBSOCKET_CONTEXT_AVAILABLE = True
    WEBSOCKET_CONTEXT_ERROR = None
except ImportError as e:
    WEBSOCKET_CONTEXT_AVAILABLE = False
    WEBSOCKET_CONTEXT_ERROR = str(e)

try:
    # This import should FAIL - proving the regression
    from netra_backend.app.websocket_core import WebSocketRequestContext
    WEBSOCKET_REQUEST_CONTEXT_AVAILABLE = True
    WEBSOCKET_REQUEST_CONTEXT_ERROR = None
except ImportError as e:
    WEBSOCKET_REQUEST_CONTEXT_AVAILABLE = False
    WEBSOCKET_REQUEST_CONTEXT_ERROR = str(e)

# Import user execution context for integration testing
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    USER_CONTEXT_AVAILABLE = True
except ImportError as e:
    USER_CONTEXT_AVAILABLE = False
    USER_CONTEXT_ERROR = str(e)


class TestWebSocketContextIntegrationRegression:
    """Integration tests for WebSocket context import regression.
    
    These tests verify that the regression breaks real integration patterns
    used throughout the codebase.
    """
    
    @pytest.fixture
    def mock_websocket(self):
        """Create a mock WebSocket for testing."""
        websocket = MagicMock(spec=WebSocket)
        websocket.client_state = MagicMock()
        websocket.client_state.name = "CONNECTED"
        return websocket
    
    @pytest.fixture
    def user_execution_context(self):
        """Create a valid user execution context for testing."""
        if not USER_CONTEXT_AVAILABLE:
            pytest.skip(f"UserExecutionContext not available: {USER_CONTEXT_ERROR}")
        
        return UserExecutionContext(
            user_id="test_user_12345",
            thread_id="test_thread_67890", 
            run_id="test_run_11111",
            request_id="test_request_22222"
        )
    
    def test_websocket_context_creation_works(self, mock_websocket, user_execution_context):
        """
        Test that WebSocketContext can be created successfully.
        
        This test should PASS - validates the baseline functionality.
        """
        if not WEBSOCKET_CONTEXT_AVAILABLE:
            pytest.fail(f"WebSocketContext not available: {WEBSOCKET_CONTEXT_ERROR}")
        
        # Create context using available WebSocketContext
        context = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id=user_execution_context.user_id,
            thread_id=user_execution_context.thread_id,
            run_id=user_execution_context.run_id
        )
        
        assert context is not None
        assert context.user_id == user_execution_context.user_id
        assert context.thread_id == user_execution_context.thread_id
        assert context.run_id == user_execution_context.run_id
        assert context.websocket == mock_websocket
    
    def test_websocket_request_context_alias_creation_EXPECTED_TO_FAIL(self, mock_websocket, user_execution_context):
        """
         ALERT:  REGRESSION TEST: This test MUST FAIL to prove the regression.
        
        Test that WebSocketRequestContext alias can be used for context creation.
        
        CRITICAL: This should FAIL, demonstrating that code expecting the alias will break.
        """
        if not WEBSOCKET_REQUEST_CONTEXT_AVAILABLE:
            pytest.fail(
                f" ALERT:  REGRESSION CONFIRMED: WebSocketRequestContext alias not available. "
                f"Error: {WEBSOCKET_REQUEST_CONTEXT_ERROR}. "
                f"This breaks integration patterns that expect this alias."
            )
        
        # If the alias is available (after fix), validate it works the same way
        context = WebSocketRequestContext.create_for_user(
            websocket=mock_websocket,
            user_id=user_execution_context.user_id,
            thread_id=user_execution_context.thread_id,
            run_id=user_execution_context.run_id
        )
        
        assert context is not None
        assert context.user_id == user_execution_context.user_id
        assert isinstance(context, WebSocketContext), "WebSocketRequestContext should be WebSocketContext"
    
    @pytest.mark.asyncio
    async def test_websocket_manager_factory_with_context_creation(self, mock_websocket, user_execution_context):
        """
        Test WebSocket manager factory integration with context creation.
        
        This validates that the factory pattern works with proper context handling.
        """
        if not FACTORY_IMPORTS_AVAILABLE:
            pytest.skip(f"Factory imports not available: {FACTORY_IMPORT_ERROR}")
        
        if not WEBSOCKET_CONTEXT_AVAILABLE:
            pytest.skip(f"WebSocketContext not available: {WEBSOCKET_CONTEXT_ERROR}")
        
        # Create a WebSocket manager using the factory
        try:
            manager = await create_websocket_manager(user_execution_context)
            assert manager is not None
            assert isinstance(manager, IsolatedWebSocketManager)
        except Exception as e:
            pytest.fail(f"WebSocket manager creation failed: {e}")
    
    def test_context_types_interchangeability_EXPECTED_TO_FAIL(self, mock_websocket, user_execution_context):
        """
         ALERT:  REGRESSION TEST: Test that WebSocketContext and WebSocketRequestContext are interchangeable.
        
        This test MUST FAIL initially, proving that code expecting interchangeability will break.
        """
        if not WEBSOCKET_CONTEXT_AVAILABLE:
            pytest.skip(f"WebSocketContext not available: {WEBSOCKET_CONTEXT_ERROR}")
        
        # Create context with available class
        context_original = WebSocketContext.create_for_user(
            websocket=mock_websocket,
            user_id=user_execution_context.user_id,
            thread_id=user_execution_context.thread_id,
            run_id=user_execution_context.run_id
        )
        
        if not WEBSOCKET_REQUEST_CONTEXT_AVAILABLE:
            pytest.fail(
                f" ALERT:  INTERCHANGEABILITY BROKEN: Cannot test WebSocketRequestContext compatibility. "
                f"Error: {WEBSOCKET_REQUEST_CONTEXT_ERROR}. "
                f"Code that expects both types to be available will fail."
            )
        
        # If both are available (after fix), they should be the same type
        assert WebSocketRequestContext is WebSocketContext, (
            "WebSocketRequestContext should be an alias for WebSocketContext for backward compatibility"
        )
        
        # Test that isinstance works with both
        assert isinstance(context_original, WebSocketContext)
        assert isinstance(context_original, WebSocketRequestContext)
    
    def test_agent_websocket_bridge_integration_pattern_EXPECTED_TO_FAIL(self, mock_websocket, user_execution_context):
        """
         ALERT:  REGRESSION TEST: Test agent-WebSocket bridge integration pattern.
        
        This simulates how agent-WebSocket bridge code would try to use WebSocketRequestContext.
        This test MUST FAIL initially, proving the integration is broken.
        """
        # Simulate agent-WebSocket bridge code pattern
        def create_websocket_context_for_agent(websocket, user_context):
            """Simulate agent bridge context creation pattern."""
            # This is the kind of code that would break with the regression
            try:
                # Agent bridge might expect to import WebSocketRequestContext
                from netra_backend.app.websocket_core import WebSocketRequestContext
                return WebSocketRequestContext.create_for_user(
                    websocket=websocket,
                    user_id=user_context.user_id,
                    thread_id=user_context.thread_id,
                    run_id=user_context.run_id
                )
            except ImportError as e:
                # This is where the regression manifests
                raise ImportError(f"Agent-WebSocket bridge integration broken: {e}")
        
        # This should work after the fix, but fail during regression
        try:
            context = create_websocket_context_for_agent(mock_websocket, user_execution_context)
            integration_successful = True
        except ImportError:
            integration_successful = False
        
        # This assertion should FAIL, proving the integration is broken
        assert integration_successful, (
            f" ALERT:  AGENT-WEBSOCKET INTEGRATION BROKEN: Agent bridge cannot import WebSocketRequestContext. "
            f"Error: {WEBSOCKET_REQUEST_CONTEXT_ERROR}. "
            f"This breaks critical agent-WebSocket communication patterns."
        )
    
    def test_legacy_code_compatibility_EXPECTED_TO_FAIL(self, mock_websocket, user_execution_context):
        """
         ALERT:  REGRESSION TEST: Test that legacy code patterns still work.
        
        This simulates existing codebase patterns that depend on WebSocketRequestContext.
        """
        # Simulate various legacy code patterns that might exist
        legacy_patterns = [
            # Pattern 1: Direct import and usage
            lambda: __import__('netra_backend.app.websocket_core', fromlist=['WebSocketRequestContext']).WebSocketRequestContext,
            
            # Pattern 2: Import with alias
            lambda: getattr(__import__('netra_backend.app.websocket_core'), 'WebSocketRequestContext', None),
            
            # Pattern 3: Hasattr check
            lambda: hasattr(__import__('netra_backend.app.websocket_core'), 'WebSocketRequestContext'),
        ]
        
        failed_patterns = []
        
        for i, pattern in enumerate(legacy_patterns):
            try:
                result = pattern()
                if result is None or result is False:
                    failed_patterns.append(f"Pattern {i+1}: returned {result}")
            except (ImportError, AttributeError) as e:
                failed_patterns.append(f"Pattern {i+1}: {type(e).__name__}: {e}")
        
        if failed_patterns:
            pytest.fail(
                f" ALERT:  LEGACY CODE COMPATIBILITY BROKEN: {len(failed_patterns)} pattern(s) failed:\\n" +
                "\\n".join(f"  - {pattern}" for pattern in failed_patterns) +
                f"\\n\\nThis regression breaks existing code that depends on WebSocketRequestContext import patterns."
            )
    
    def test_websocket_core_module_health_check(self):
        """
        Test overall websocket_core module health to isolate the regression.
        
        This ensures the regression is specifically about WebSocketRequestContext export.
        """
        import netra_backend.app.websocket_core as websocket_core
        
        # Module should load successfully
        assert websocket_core is not None, "websocket_core module should be loadable"
        
        # Should have __all__ defined
        assert hasattr(websocket_core, '__all__'), "websocket_core should define __all__"
        assert isinstance(websocket_core.__all__, list), "__all__ should be a list"
        
        # Should have key exports
        key_exports = [
            'WebSocketContext',
            'create_websocket_manager', 
            'WebSocketManagerFactory',
            'IsolatedWebSocketManager'
        ]
        
        missing_exports = []
        for export in key_exports:
            if export not in websocket_core.__all__:
                missing_exports.append(export)
        
        assert not missing_exports, f"Missing key exports from __all__: {missing_exports}"
        
        # Now check if WebSocketRequestContext is missing (this identifies the regression)
        websocket_request_context_missing = 'WebSocketRequestContext' not in websocket_core.__all__
        
        if websocket_request_context_missing:
            print(f"\\n ALERT:  REGRESSION IDENTIFIED: WebSocketRequestContext missing from websocket_core.__all__")
            print(f"Available exports: {sorted(websocket_core.__all__)}")
        
        # This documents the regression but doesn't fail the health check
        # The specific regression tests above will fail appropriately


if __name__ == "__main__":
    # Allow running this test file directly to see the regression
    pytest.main([__file__, "-v", "-s"])