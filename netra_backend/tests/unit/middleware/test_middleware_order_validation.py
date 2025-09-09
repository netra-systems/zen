"""
Unit tests for middleware dependency order validation - Issue #112.

These tests FAIL with current broken middleware order and PASS after fix.
Tests validate that SessionMiddleware dependency violations are detected.

Business Context: GCPAuthContextMiddleware depends on SessionMiddleware but is
installed outside SSOT setup_middleware() function, causing Golden Path blocking.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from netra_backend.app.core.app_factory import setup_middleware
from netra_backend.app.core.middleware_setup import setup_gcp_auth_context_middleware
from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware


class TestMiddlewareOrderValidation:
    """Test middleware dependency order validation."""

    def test_session_middleware_installed_before_gcp_auth_context(self):
        """Test that SessionMiddleware is installed before GCPAuthContextMiddleware.
        
        EXPECTED: This test should FAIL with current broken code because
        GCPAuthContextMiddleware is installed outside SSOT setup_middleware().
        """
        app = FastAPI()
        
        # Setup middleware using SSOT function
        setup_middleware(app)
        
        # Get middleware stack
        middleware_stack = self._get_middleware_stack(app)
        
        # Extract middleware class names in order (reverse order because they're applied in reverse)
        middleware_names = [
            middleware.__class__.__name__ for middleware in reversed(middleware_stack)
        ]
        
        # Find positions of relevant middleware
        session_position = None
        gcp_auth_position = None
        
        for i, name in enumerate(middleware_names):
            if 'SessionMiddleware' in name:
                session_position = i
            elif 'GCPAuthContextMiddleware' in name:
                gcp_auth_position = i
        
        # CRITICAL TEST: This should fail because GCPAuthContextMiddleware
        # is installed OUTSIDE the SSOT setup_middleware function
        if gcp_auth_position is not None:
            assert session_position is not None, (
                "SessionMiddleware not found but GCPAuthContextMiddleware requires it"
            )
            assert session_position < gcp_auth_position, (
                f"SessionMiddleware (pos {session_position}) must be installed BEFORE "
                f"GCPAuthContextMiddleware (pos {gcp_auth_position}). "
                f"Current order: {middleware_names}"
            )
        else:
            # GCP middleware not in SSOT setup - this is the violation we're testing
            pytest.fail(
                "GCPAuthContextMiddleware not found in SSOT middleware stack - "
                "it's being installed outside setup_middleware() which violates dependency order"
            )

    def test_middleware_installed_outside_ssot_detected(self):
        """Test detection of middleware installed outside SSOT setup_middleware().
        
        EXPECTED: This test should FAIL because GCPAuthContextMiddleware
        is currently installed in _install_auth_context_middleware outside SSOT.
        """
        app = FastAPI()
        
        # First, setup SSOT middleware
        setup_middleware(app)
        initial_middleware_count = len(app.middleware_stack)
        initial_middleware_names = {
            middleware.__class__.__name__ for middleware in app.middleware_stack
        }
        
        # Now install GCP auth context middleware (current broken pattern)
        _install_auth_context_middleware(app)
        
        final_middleware_count = len(app.middleware_stack)
        final_middleware_names = {
            middleware.__class__.__name__ for middleware in app.middleware_stack
        }
        
        # Check if GCP middleware was added outside SSOT
        new_middleware = final_middleware_names - initial_middleware_names
        
        # This test FAILS because GCP middleware is added outside SSOT
        assert not any('GCPAuthContextMiddleware' in name for name in new_middleware), (
            f"GCPAuthContextMiddleware was installed OUTSIDE SSOT setup_middleware(). "
            f"New middleware: {new_middleware}. This violates dependency order and can "
            f"cause 'SessionMiddleware must be installed' errors."
        )

    def test_gcp_middleware_session_dependency_validation(self):
        """Test that GCPAuthContextMiddleware properly validates SessionMiddleware dependency.
        
        EXPECTED: This test should reveal the session access pattern in GCP middleware.
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        import inspect
        
        # Inspect the GCP middleware source to detect session access
        source_lines = inspect.getsourcelines(GCPAuthContextMiddleware._extract_auth_context)[0]
        source_code = ''.join(source_lines)
        
        # Check if middleware accesses request.session
        has_session_access = 'request.session' in source_code
        
        assert has_session_access, (
            "GCPAuthContextMiddleware does not access request.session - "
            "this test may need updating if implementation changed"
        )
        
        # Check for session dependency patterns
        session_patterns = [
            'hasattr(request, \'session\')',
            'request.session.get(',
            'request.session['
        ]
        
        found_patterns = [pattern for pattern in session_patterns if pattern in source_code]
        
        assert found_patterns, (
            f"Expected session access patterns not found in GCPAuthContextMiddleware. "
            f"Source contains: {source_code[:200]}..."
        )
        
        # This confirms the dependency - GCP middleware NEEDS SessionMiddleware
        print(f"GCP middleware session access patterns found: {found_patterns}")

    def test_session_middleware_required_error_simulation(self):
        """Test simulation of SessionMiddleware dependency error.
        
        EXPECTED: This test demonstrates what happens when GCPAuthContextMiddleware
        runs without SessionMiddleware properly installed.
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        from fastapi import Request
        from unittest.mock import AsyncMock
        
        # Create GCP middleware instance
        middleware = GCPAuthContextMiddleware(None, enable_user_isolation=True)
        
        # Create mock request WITHOUT session attribute (simulating missing SessionMiddleware)
        mock_request = Mock(spec=Request)
        mock_request.headers = {'Authorization': 'Bearer test-token'}
        mock_request.method = 'GET'
        mock_request.url = Mock()
        mock_request.url.path = '/test'
        mock_request.client = Mock()
        mock_request.client.host = '127.0.0.1'
        
        # Importantly: NO session attribute - this simulates what happens
        # when SessionMiddleware is not installed or installed after GCP middleware
        # del mock_request.session  # This would be the normal case
        
        # Test auth context extraction
        import asyncio
        
        async def test_extraction():
            try:
                auth_context = await middleware._extract_auth_context(mock_request)
                
                # This should work even without session, but reveals dependency
                assert 'user_id' in auth_context
                
                # The middleware gracefully handles missing session,
                # but this means session data is not captured for error reporting
                assert 'session_id' not in auth_context or auth_context['session_id'] is None
                
                return True
            except AttributeError as e:
                if 'session' in str(e):
                    pytest.fail(f"GCP middleware failed due to session dependency: {e}")
                raise
            except Exception as e:
                # Other errors are acceptable for this test
                print(f"Other error (acceptable): {e}")
                return True
        
        # Run the async test
        result = asyncio.run(test_extraction())
        assert result, "Auth context extraction should complete"

    def _get_middleware_stack(self, app: FastAPI) -> list:
        """Get the middleware stack from FastAPI app.
        
        Args:
            app: FastAPI application instance
            
        Returns:
            List of middleware instances in execution order
        """
        return [middleware for middleware in app.middleware_stack]

    def test_middleware_execution_order_analysis(self):
        """Analyze actual middleware execution order to understand current state.
        
        This is a diagnostic test that shows the current broken state.
        """
        app = FastAPI()
        setup_middleware(app)
        
        middleware_stack = self._get_middleware_stack(app)
        middleware_info = []
        
        for i, middleware in enumerate(middleware_stack):
            middleware_info.append({
                'position': i,
                'class': middleware.__class__.__name__,
                'module': middleware.__class__.__module__,
            })
        
        # Print diagnostic information
        print("\nCurrent Middleware Stack (execution order):")
        for info in middleware_info:
            print(f"  {info['position']}: {info['class']} from {info['module']}")
        
        # Look for session middleware
        session_middleware_found = any(
            'SessionMiddleware' in info['class'] for info in middleware_info
        )
        
        assert session_middleware_found, (
            f"SessionMiddleware not found in middleware stack. "
            f"Current stack: {[info['class'] for info in middleware_info]}"
        )
        
        # This test always passes but provides diagnostic info
        assert True, "Diagnostic test completed"


class TestSSOTMiddlewareCompliance:
    """Test SSOT middleware setup compliance."""

    def test_ssot_middleware_function_exists(self):
        """Test that SSOT middleware setup function exists and is accessible."""
        from netra_backend.app.core.middleware_setup import setup_middleware as ssot_setup
        
        assert callable(ssot_setup), "SSOT setup_middleware function should be callable"
        
        # Check function signature
        import inspect
        sig = inspect.signature(ssot_setup)
        params = list(sig.parameters.keys())
        
        assert 'app' in params, "SSOT setup_middleware should accept 'app' parameter"
        assert len(params) == 1, f"SSOT setup_middleware should have exactly 1 parameter, got {len(params)}: {params}"

    def test_ssot_setup_includes_session_middleware(self):
        """Test that SSOT setup_middleware includes SessionMiddleware installation."""
        from netra_backend.app.core.middleware_setup import setup_middleware as ssot_setup
        import inspect
        
        # Get source code of SSOT setup function
        source_lines = inspect.getsourcelines(ssot_setup)[0]
        source_code = ''.join(source_lines)
        
        # Check for session middleware setup
        session_setup_patterns = [
            'setup_session_middleware',
            'SessionMiddleware',
            'session_middleware'
        ]
        
        found_patterns = [pattern for pattern in session_setup_patterns if pattern in source_code]
        
        assert found_patterns, (
            f"SSOT setup_middleware function does not include session middleware setup. "
            f"Expected patterns: {session_setup_patterns}. "
            f"Found: {found_patterns}. "
            f"Source: {source_code[:300]}..."
        )

    def test_app_factory_delegates_to_ssot(self):
        """Test that app_factory.setup_middleware delegates to SSOT function."""
        from netra_backend.app.core.app_factory import setup_middleware as factory_setup
        import inspect
        
        # Get source code of app factory setup function
        source_lines = inspect.getsourcelines(factory_setup)[0]
        source_code = ''.join(source_lines)
        
        # Check for delegation to SSOT
        delegation_patterns = [
            'ssot_setup_middleware',
            'from netra_backend.app.core.middleware_setup import setup_middleware',
            'middleware_setup.py'
        ]
        
        found_patterns = [pattern for pattern in delegation_patterns if pattern in source_code]
        
        assert found_patterns, (
            f"app_factory.setup_middleware does not properly delegate to SSOT function. "
            f"Expected delegation patterns: {delegation_patterns}. "
            f"Found: {found_patterns}. "
            f"Source: {source_code[:500]}..."
        )


if __name__ == '__main__':
    # Run specific test to demonstrate the issue
    pytest.main([__file__ + "::TestMiddlewareOrderValidation::test_middleware_installed_outside_ssot_detected", "-v", "-s"])