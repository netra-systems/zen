"""
Regression Test - WebSocket Context Import Failure (Unit)

 ALERT:  CRITICAL REGRESSION TEST  ALERT: 
This test MUST FAIL initially to prove the regression exists.

Purpose: Prove that WebSocketRequestContext cannot be imported from websocket_core
Expected State: FAILING - demonstrates the import regression
After Fix: Should pass when WebSocketRequestContext is properly exported

Business Impact:
- Breaks agent-WebSocket integration
- Prevents proper context handling in WebSocket events
- Violates SSOT principles for WebSocket context management

Test Strategy:
- Use REAL imports (no mocks per CLAUDE.md)
- Test direct imports from websocket_core package
- Verify both WebSocketContext and WebSocketRequestContext are available
- Ensure backward compatibility is maintained
"""

import pytest
import sys
from typing import Type

# CRITICAL: These imports MUST FAIL to prove the regression
try:
    # This should work - WebSocketContext exists
    from netra_backend.app.websocket_core import WebSocketContext
    WEBSOCKET_CONTEXT_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_CONTEXT_AVAILABLE = False
    WEBSOCKET_CONTEXT_ERROR = str(e)

try:
    # This should FAIL - WebSocketRequestContext alias not exported
    from netra_backend.app.websocket_core import WebSocketRequestContext  
    WEBSOCKET_REQUEST_CONTEXT_AVAILABLE = True
except ImportError as e:
    WEBSOCKET_REQUEST_CONTEXT_AVAILABLE = False
    WEBSOCKET_REQUEST_CONTEXT_ERROR = str(e)

# Import for validation after direct import
if WEBSOCKET_CONTEXT_AVAILABLE:
    try:
        from netra_backend.app.websocket_core.context import WebSocketRequestContext as DirectWebSocketRequestContext
        DIRECT_IMPORT_AVAILABLE = True
    except ImportError as e:
        DIRECT_IMPORT_AVAILABLE = False
        DIRECT_IMPORT_ERROR = str(e)
else:
    DIRECT_IMPORT_AVAILABLE = False
    DIRECT_IMPORT_ERROR = "WebSocketContext not available"

class TestWebSocketContextImportRegression:
    """Test WebSocketContext import regression.
    
    These tests MUST FAIL initially to prove the regression exists.
    After the fix, they should pass.
    """
    
    def test_websocket_context_is_available(self):
        """
        Test that WebSocketContext can be imported from websocket_core.
        
        This test should PASS - WebSocketContext should be available.
        """
        assert WEBSOCKET_CONTEXT_AVAILABLE, (
            f"WebSocketContext should be importable from websocket_core. "
            f"Error: {WEBSOCKET_CONTEXT_ERROR if not WEBSOCKET_CONTEXT_AVAILABLE else 'None'}"
        )
        
        # Validate the imported class
        assert hasattr(WebSocketContext, '__name__')
        assert WebSocketContext.__name__ == 'WebSocketContext'
        
        # Check it has expected methods
        expected_methods = ['create_for_user', 'is_active', 'update_activity', 'get_connection_info']
        for method in expected_methods:
            assert hasattr(WebSocketContext, method), f"WebSocketContext missing method: {method}"
    
    def test_websocket_request_context_alias_available_EXPECTED_TO_FAIL(self):
        """
         ALERT:  REGRESSION TEST: This test MUST FAIL to prove the issue exists.
        
        Test that WebSocketRequestContext alias can be imported from websocket_core.
        
        CRITICAL: This test should FAIL initially, proving the regression.
        After fixing the export in __init__.py, this test should pass.
        """
        # This assertion should FAIL, proving the regression
        assert WEBSOCKET_REQUEST_CONTEXT_AVAILABLE, (
            f" ALERT:  REGRESSION DETECTED: WebSocketRequestContext alias cannot be imported "
            f"from websocket_core package. Error: {WEBSOCKET_REQUEST_CONTEXT_ERROR}. "
            f"This breaks backward compatibility and agent-WebSocket integration."
        )
        
        if WEBSOCKET_REQUEST_CONTEXT_AVAILABLE:
            # If available, validate it's the same as WebSocketContext
            assert WebSocketRequestContext is WebSocketContext, (
                "WebSocketRequestContext should be an alias for WebSocketContext"
            )
    
    def test_alias_exists_in_context_module(self):
        """
        Test that the WebSocketRequestContext alias exists in the context module.
        
        This proves the alias was created but not exported.
        """
        assert DIRECT_IMPORT_AVAILABLE, (
            f"WebSocketRequestContext alias should exist in context module. "
            f"Error: {DIRECT_IMPORT_ERROR}"
        )
        
        # Validate it's the same as WebSocketContext when imported directly
        if WEBSOCKET_CONTEXT_AVAILABLE and DIRECT_IMPORT_AVAILABLE:
            assert DirectWebSocketRequestContext is WebSocketContext, (
                "WebSocketRequestContext should be an alias for WebSocketContext"
            )
    
    def test_backward_compatibility_broken_EXPECTED_TO_FAIL(self):
        """
         ALERT:  REGRESSION TEST: This test MUST FAIL to prove backward compatibility is broken.
        
        Test that code expecting WebSocketRequestContext import will fail.
        
        This simulates the real-world impact of the regression.
        """
        # Simulate code that expects to import WebSocketRequestContext
        import_statement = "from netra_backend.app.websocket_core import WebSocketRequestContext"
        
        try:
            exec(import_statement)
            import_successful = True
        except ImportError:
            import_successful = False
        
        # This assertion should FAIL, proving backward compatibility is broken
        assert import_successful, (
            f" ALERT:  BACKWARD COMPATIBILITY BROKEN: The import statement '{import_statement}' "
            f"fails, breaking existing code that depends on WebSocketRequestContext alias. "
            f"This violates SSOT principles and breaks agent-WebSocket integration."
        )
    
    def test_websocket_core_exports_completeness(self):
        """
        Test that websocket_core exports are complete and consistent.
        
        This validates the overall health of the websocket_core module exports.
        """
        from netra_backend.app.websocket_core import __all__
        
        # Check that __all__ is defined
        assert isinstance(__all__, list), "websocket_core should define __all__ list"
        assert len(__all__) > 0, "websocket_core __all__ should not be empty"
        
        # WebSocketContext should be in __all__
        assert 'WebSocketContext' in __all__, "WebSocketContext should be in __all__"
        
        # WebSocketRequestContext should be in __all__ (this will fail, proving the issue)
        # Note: This assertion is expected to fail during regression testing
        try:
            assert 'WebSocketRequestContext' in __all__, (
                "WebSocketRequestContext alias should be in __all__ for backward compatibility"
            )
            request_context_in_all = True
        except AssertionError:
            request_context_in_all = False
        
        # Report the findings
        missing_exports = []
        if not request_context_in_all:
            missing_exports.append('WebSocketRequestContext')
        
        if missing_exports:
            pytest.fail(
                f" ALERT:  EXPORT REGRESSION: websocket_core __all__ is missing: {missing_exports}. "
                f"This breaks backward compatibility and SSOT principles."
            )
    
    def test_module_structure_integrity(self):
        """
        Test that the websocket_core module structure is intact.
        
        This ensures the regression is specifically about exports, not module corruption.
        """
        import netra_backend.app.websocket_core as websocket_core
        import netra_backend.app.websocket_core.context as context_module
        
        # Module should be loadable
        assert websocket_core is not None, "websocket_core module should be loadable"
        assert context_module is not None, "websocket_core.context module should be loadable"
        
        # Context module should have both classes
        assert hasattr(context_module, 'WebSocketContext'), "context module missing WebSocketContext"
        assert hasattr(context_module, 'WebSocketRequestContext'), "context module missing WebSocketRequestContext alias"
        
        # They should be the same object
        assert context_module.WebSocketRequestContext is context_module.WebSocketContext, (
            "WebSocketRequestContext should be an alias for WebSocketContext in context module"
        )
    
    def test_import_paths_documentation(self):
        """
        Document the current import paths and their status.
        
        This test provides visibility into what works and what doesn't.
        """
        import_results = {
            "from netra_backend.app.websocket_core import WebSocketContext": WEBSOCKET_CONTEXT_AVAILABLE,
            "from netra_backend.app.websocket_core import WebSocketRequestContext": WEBSOCKET_REQUEST_CONTEXT_AVAILABLE,
            "from netra_backend.app.websocket_core.context import WebSocketContext": WEBSOCKET_CONTEXT_AVAILABLE,
            "from netra_backend.app.websocket_core.context import WebSocketRequestContext": DIRECT_IMPORT_AVAILABLE,
        }
        
        failed_imports = [path for path, success in import_results.items() if not success]
        successful_imports = [path for path, success in import_results.items() if success]
        
        print("\n SEARCH:  Import Path Analysis:")
        print(f" PASS:  Successful imports ({len(successful_imports)}):")
        for path in successful_imports:
            print(f"   - {path}")
        
        print(f"\n FAIL:  Failed imports ({len(failed_imports)}):")
        for path in failed_imports:
            print(f"   - {path}")
        
        if failed_imports:
            print(f"\n ALERT:  REGRESSION IMPACT: {len(failed_imports)} import path(s) are broken")
        
        # This test always passes but documents the current state
        assert True, "Documentation test - see output for import path status"


if __name__ == "__main__":
    # Allow running this test file directly to see the regression
    pytest.main([__file__, "-v", "-s"])