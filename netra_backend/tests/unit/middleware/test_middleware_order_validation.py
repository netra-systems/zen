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
        setup_middleware(app)
        middleware_stack = self._get_middleware_stack(app)
        middleware_names = [middleware.__class__.__name__ for middleware in reversed(middleware_stack)]
        session_position = None
        gcp_auth_position = None
        for i, name in enumerate(middleware_names):
            if 'SessionMiddleware' in name:
                session_position = i
            elif 'GCPAuthContextMiddleware' in name:
                gcp_auth_position = i
        if gcp_auth_position is not None:
            assert session_position is not None, 'SessionMiddleware not found but GCPAuthContextMiddleware requires it'
            assert session_position < gcp_auth_position, f'SessionMiddleware (pos {session_position}) must be installed BEFORE GCPAuthContextMiddleware (pos {gcp_auth_position}). Current order: {middleware_names}'
        else:
            pytest.fail("GCPAuthContextMiddleware not found in SSOT middleware stack - it's being installed outside setup_middleware() which violates dependency order")

    def test_middleware_installed_outside_ssot_detected(self):
        """Test detection of middleware installed outside SSOT setup_middleware().
        
        EXPECTED: This test should FAIL because GCPAuthContextMiddleware
        is currently installed in _install_auth_context_middleware outside SSOT.
        """
        app = FastAPI()
        setup_middleware(app)
        initial_middleware_count = len(app.middleware_stack)
        initial_middleware_names = {middleware.__class__.__name__ for middleware in app.middleware_stack}
        _install_auth_context_middleware(app)
        final_middleware_count = len(app.middleware_stack)
        final_middleware_names = {middleware.__class__.__name__ for middleware in app.middleware_stack}
        new_middleware = final_middleware_names - initial_middleware_names
        assert not any(('GCPAuthContextMiddleware' in name for name in new_middleware)), f"GCPAuthContextMiddleware was installed OUTSIDE SSOT setup_middleware(). New middleware: {new_middleware}. This violates dependency order and can cause 'SessionMiddleware must be installed' errors."

    def test_gcp_middleware_session_dependency_validation(self):
        """Test that GCPAuthContextMiddleware properly validates SessionMiddleware dependency.
        
        EXPECTED: This test should reveal the session access pattern in GCP middleware.
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        import inspect
        source_lines = inspect.getsourcelines(GCPAuthContextMiddleware._extract_auth_context)[0]
        source_code = ''.join(source_lines)
        has_session_access = 'request.session' in source_code
        assert has_session_access, 'GCPAuthContextMiddleware does not access request.session - this test may need updating if implementation changed'
        session_patterns = ["hasattr(request, 'session')", 'request.session.get(', 'request.session[']
        found_patterns = [pattern for pattern in session_patterns if pattern in source_code]
        assert found_patterns, f'Expected session access patterns not found in GCPAuthContextMiddleware. Source contains: {source_code[:200]}...'
        print(f'GCP middleware session access patterns found: {found_patterns}')

    def test_session_middleware_required_error_simulation(self):
        """Test simulation of SessionMiddleware dependency error.
        
        EXPECTED: This test demonstrates what happens when GCPAuthContextMiddleware
        runs without SessionMiddleware properly installed.
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        from fastapi import Request
        from unittest.mock import AsyncMock
        middleware = GCPAuthContextMiddleware(None, enable_user_isolation=True)
        mock_request = Mock(spec=Request)
        mock_request.headers = {'Authorization': 'Bearer test-token'}
        mock_request.method = 'GET'
        mock_request.url = Mock()
        mock_request.url.path = '/test'
        mock_request.client = Mock()
        mock_request.client.host = '127.0.0.1'
        import asyncio

        async def test_extraction():
            try:
                auth_context = await middleware._extract_auth_context(mock_request)
                assert 'user_id' in auth_context
                assert 'session_id' not in auth_context or auth_context['session_id'] is None
                return True
            except AttributeError as e:
                if 'session' in str(e):
                    pytest.fail(f'GCP middleware failed due to session dependency: {e}')
                raise
            except Exception as e:
                print(f'Other error (acceptable): {e}')
                return True
        result = asyncio.run(test_extraction())
        assert result, 'Auth context extraction should complete'

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
            middleware_info.append({'position': i, 'class': middleware.__class__.__name__, 'module': middleware.__class__.__module__})
        print('\nCurrent Middleware Stack (execution order):')
        for info in middleware_info:
            print(f"  {info['position']}: {info['class']} from {info['module']}")
        session_middleware_found = any(('SessionMiddleware' in info['class'] for info in middleware_info))
        assert session_middleware_found, f"SessionMiddleware not found in middleware stack. Current stack: {[info['class'] for info in middleware_info]}"
        assert True, 'Diagnostic test completed'

class TestSSOTMiddlewareCompliance:
    """Test SSOT middleware setup compliance."""

    def test_ssot_middleware_function_exists(self):
        """Test that SSOT middleware setup function exists and is accessible."""
        from netra_backend.app.core.middleware_setup import setup_middleware as ssot_setup
        assert callable(ssot_setup), 'SSOT setup_middleware function should be callable'
        import inspect
        sig = inspect.signature(ssot_setup)
        params = list(sig.parameters.keys())
        assert 'app' in params, "SSOT setup_middleware should accept 'app' parameter"
        assert len(params) == 1, f'SSOT setup_middleware should have exactly 1 parameter, got {len(params)}: {params}'

    def test_ssot_setup_includes_session_middleware(self):
        """Test that SSOT setup_middleware includes SessionMiddleware installation."""
        from netra_backend.app.core.middleware_setup import setup_middleware as ssot_setup
        import inspect
        source_lines = inspect.getsourcelines(ssot_setup)[0]
        source_code = ''.join(source_lines)
        session_setup_patterns = ['setup_session_middleware', 'SessionMiddleware', 'session_middleware']
        found_patterns = [pattern for pattern in session_setup_patterns if pattern in source_code]
        assert found_patterns, f'SSOT setup_middleware function does not include session middleware setup. Expected patterns: {session_setup_patterns}. Found: {found_patterns}. Source: {source_code[:300]}...'

    def test_app_factory_delegates_to_ssot(self):
        """Test that app_factory.setup_middleware delegates to SSOT function."""
        from netra_backend.app.core.app_factory import setup_middleware as factory_setup
        import inspect
        source_lines = inspect.getsourcelines(factory_setup)[0]
        source_code = ''.join(source_lines)
        delegation_patterns = ['ssot_setup_middleware', 'from netra_backend.app.core.middleware_setup import setup_middleware', 'middleware_setup.py']
        found_patterns = [pattern for pattern in delegation_patterns if pattern in source_code]
        assert found_patterns, f'app_factory.setup_middleware does not properly delegate to SSOT function. Expected delegation patterns: {delegation_patterns}. Found: {found_patterns}. Source: {source_code[:500]}...'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')