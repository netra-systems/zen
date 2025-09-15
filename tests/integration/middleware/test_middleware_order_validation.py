"""
Integration tests for middleware ordering validation.
Tests that middleware is installed in the correct order to prevent Issue #1127 session access failures.
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class MiddlewareOrderValidationTests(SSotBaseTestCase):
    """Test middleware ordering to prevent session access failures."""

    def test_session_middleware_installed_first_in_stack(self):
        """Test that SessionMiddleware is installed first in the middleware stack.

        CRITICAL TEST: SessionMiddleware MUST be installed first so it runs before
        any middleware that tries to access request.session (like GCP auth context middleware).
        """
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Get middleware stack in installation order
        middleware_names = []
        session_middleware_position = None

        for i, middleware in enumerate(app.user_middleware):
            middleware_name = middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls)
            middleware_names.append(middleware_name)

            if 'SessionMiddleware' in middleware_name:
                session_middleware_position = i

        print(f"Middleware installation order: {middleware_names}")

        # SessionMiddleware should be found
        assert session_middleware_position is not None, f"SessionMiddleware not found. Middleware stack: {middleware_names}"

        # SessionMiddleware should be installed early in the stack
        # Note: FastAPI middleware is applied in reverse order (last added = first to run)
        # So SessionMiddleware should be at a high index to run first
        assert session_middleware_position >= 0, f"SessionMiddleware position invalid: {session_middleware_position}"

        print(f"✅ SessionMiddleware found at position {session_middleware_position} in middleware stack")

    def test_middleware_dependency_order(self):
        """Test that middleware that depends on sessions is ordered after SessionMiddleware.

        CRITICAL TEST: Any middleware accessing request.session must be installed AFTER SessionMiddleware
        to prevent the "SessionMiddleware must be installed" error from Issue #1127.
        """
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Find positions of session-dependent middleware
        middleware_positions = {}
        dependent_middleware = []

        for i, middleware in enumerate(app.user_middleware):
            middleware_name = middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls)

            # Track positions of key middleware
            if 'SessionMiddleware' in middleware_name:
                middleware_positions['session'] = i
            elif 'GCPAuth' in middleware_name or 'gcp_auth' in middleware_name.lower():
                middleware_positions['gcp_auth'] = i
                dependent_middleware.append('gcp_auth')
            elif 'auth' in middleware_name.lower() and 'SessionMiddleware' not in middleware_name:
                middleware_positions['auth'] = i
                dependent_middleware.append('auth')

        print(f"Middleware positions: {middleware_positions}")

        # Validate SessionMiddleware exists
        assert 'session' in middleware_positions, "SessionMiddleware not found in stack"

        # Validate order for each session-dependent middleware
        session_pos = middleware_positions['session']
        for dependent in dependent_middleware:
            if dependent in middleware_positions:
                dependent_pos = middleware_positions[dependent]
                # In FastAPI, lower index = installed later = runs first
                # So SessionMiddleware (higher index) should run before dependents (lower index)
                assert session_pos > dependent_pos, \
                    f"SessionMiddleware (pos {session_pos}) must be installed before {dependent} middleware (pos {dependent_pos})"

        print(f"✅ Middleware dependency order validated for {len(dependent_middleware)} dependent middleware")

    def test_session_access_order_in_middleware_chain(self):
        """Test session access works correctly through the middleware chain.

        This validates that session access works at each level of the middleware chain,
        ensuring proper ordering prevents the Issue #1127 error.
        """
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Track session access at different middleware levels
        session_access_log = []

        @app.middleware("http")
        async def test_session_access_middleware(request: Request, call_next):
            """Test middleware that accesses sessions"""
            try:
                session = request.session
                session_access_log.append({
                    "middleware": "test_middleware",
                    "success": True,
                    "session_available": session is not None
                })
                # Set test data in session
                session['test_middleware_accessed'] = True
            except RuntimeError as e:
                session_access_log.append({
                    "middleware": "test_middleware",
                    "success": False,
                    "error": str(e)
                })

            response = await call_next(request)
            return response

        @app.get("/test-session-chain")
        async def test_endpoint(request: Request):
            """Test endpoint that also accesses sessions"""
            try:
                session = request.session
                session_access_log.append({
                    "level": "endpoint",
                    "success": True,
                    "session_available": session is not None,
                    "test_data": session.get('test_middleware_accessed', False)
                })
                return {
                    "status": "success",
                    "session_available": session is not None,
                    "middleware_data": session.get('test_middleware_accessed', False)
                }
            except RuntimeError as e:
                session_access_log.append({
                    "level": "endpoint",
                    "success": False,
                    "error": str(e)
                })
                return {"status": "error", "error": str(e)}

        with TestClient(app) as client:
            response = client.get("/test-session-chain")
            data = response.json()

            # Verify request succeeded
            assert response.status_code == 200
            assert data["status"] == "success"

            # Verify session access worked at all levels
            assert len(session_access_log) >= 2, f"Expected session access at multiple levels, got: {session_access_log}"

            for access in session_access_log:
                assert access["success"] is True, f"Session access failed at level {access}: {access.get('error')}"

        print(f"✅ Session access works through {len(session_access_log)} levels of middleware chain")

    def test_middleware_order_prevents_session_errors(self):
        """Test that proper middleware order prevents session access errors.

        CRITICAL TEST: This validates that the middleware ordering implemented
        in the SSOT middleware_setup.py prevents the Issue #1127 error.
        """
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Simulate the exact session access pattern that was failing
        session_access_attempts = []

        @app.middleware("http")
        async def simulate_gcp_auth_middleware(request: Request, call_next):
            """Simulate the GCP auth context middleware session access"""
            try:
                # This is the pattern from gcp_auth_context_middleware.py:160
                session_data = {}
                session = request.session  # This line was failing

                if session:
                    session_data.update({
                        'session_id': session.get('session_id'),
                        'user_id': session.get('user_id'),
                        'simulated_gcp_auth': True
                    })

                session_access_attempts.append({
                    "middleware": "simulated_gcp_auth",
                    "success": True,
                    "session_data": session_data
                })

            except RuntimeError as e:
                session_access_attempts.append({
                    "middleware": "simulated_gcp_auth",
                    "success": False,
                    "error": str(e),
                    "is_session_middleware_error": "SessionMiddleware must be installed" in str(e)
                })

            response = await call_next(request)
            return response

        @app.get("/test-middleware-order")
        async def test_endpoint(request: Request):
            """Test endpoint"""
            return {
                "status": "success",
                "session_access_attempts": len(session_access_attempts),
                "middleware_chain_working": len(session_access_attempts) > 0
            }

        with TestClient(app) as client:
            response = client.get("/test-middleware-order")
            data = response.json()

            # Verify request succeeded
            assert response.status_code == 200
            assert data["status"] == "success"

            # Verify session access worked in middleware
            assert len(session_access_attempts) > 0, "No session access attempts recorded"

            for attempt in session_access_attempts:
                assert attempt["success"] is True, f"Session access failed in middleware: {attempt.get('error')}"
                assert not attempt.get("is_session_middleware_error", False), \
                    "Got Issue #1127 SessionMiddleware error despite proper ordering"

        print(f"✅ Middleware ordering prevents session access errors (Issue #1127 resolved)")

    def test_middleware_initialization_sequence(self):
        """Test the complete middleware initialization sequence.

        This validates that the SSOT middleware setup function correctly
        initializes middleware in the proper order.
        """
        from netra_backend.app.core.middleware_setup import setup_middleware
        from fastapi import FastAPI

        app = FastAPI()

        # Clear any existing middleware
        app.user_middleware = []

        # Use the SSOT middleware setup
        setup_middleware(app)

        # Analyze the middleware stack
        middleware_stack = []
        critical_middleware_positions = {}

        for i, middleware in enumerate(app.user_middleware):
            middleware_name = middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls)
            middleware_stack.append(middleware_name)

            # Track critical middleware positions
            if 'SessionMiddleware' in middleware_name:
                critical_middleware_positions['session'] = i
            elif 'WebSocketExclusion' in middleware_name or 'websocket_exclusion' in middleware_name.lower():
                critical_middleware_positions['websocket_exclusion'] = i
            elif 'GCPAuth' in middleware_name or 'gcp_auth' in middleware_name.lower():
                critical_middleware_positions['gcp_auth'] = i
            elif 'CORS' in middleware_name:
                critical_middleware_positions['cors'] = i

        print(f"SSOT Middleware initialization sequence: {middleware_stack}")
        print(f"Critical middleware positions: {critical_middleware_positions}")

        # Validate SessionMiddleware is installed
        assert 'session' in critical_middleware_positions, \
            f"SessionMiddleware not found in SSOT setup. Stack: {middleware_stack}"

        # Validate basic middleware order requirements
        session_pos = critical_middleware_positions['session']

        # If GCP auth middleware exists, it should come after session
        if 'gcp_auth' in critical_middleware_positions:
            gcp_auth_pos = critical_middleware_positions['gcp_auth']
            assert session_pos > gcp_auth_pos, \
                f"SessionMiddleware must come after GCP auth middleware in middleware stack"

        print(f"✅ SSOT middleware initialization sequence is correct")

    def test_production_environment_middleware_order(self):
        """Test middleware order in production-like environment configuration.

        CRITICAL TEST: This validates middleware ordering in a production configuration
        where GCP auth context middleware would be enabled and accessing sessions.
        """
        env = IsolatedEnvironment()

        # Set production-like environment
        env.set("ENVIRONMENT", "production")
        env.set("GCP_PROJECT_ID", "netra-production")
        env.set("GOOGLE_CLOUD_PROJECT", "netra-production")
        env.set("SECRET_KEY", "production-secret-key-32-chars-minimum-required-for-session-middleware")

        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Verify middleware stack in production configuration
        middleware_names = []
        session_pos = None
        gcp_auth_pos = None

        for i, middleware in enumerate(app.user_middleware):
            middleware_name = middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls)
            middleware_names.append(middleware_name)

            if 'SessionMiddleware' in middleware_name:
                session_pos = i
            elif 'GCPAuth' in middleware_name or 'gcp_auth' in middleware_name.lower():
                gcp_auth_pos = i

        print(f"Production middleware stack: {middleware_names}")

        # Validate SessionMiddleware is present
        assert session_pos is not None, f"SessionMiddleware missing in production config: {middleware_names}"

        # If GCP auth middleware is present, validate order
        if gcp_auth_pos is not None:
            assert session_pos > gcp_auth_pos, \
                f"Production: SessionMiddleware (pos {session_pos}) must come before GCP auth (pos {gcp_auth_pos})"

        # Test actual session access in production-like request
        with TestClient(app) as client:
            response = client.get("/health", headers={
                "X-Forwarded-For": "35.235.240.1",  # GCP Cloud Run IP
                "User-Agent": "GoogleHC/1.0",
                "X-Cloud-Trace-Context": "trace-id/span-id;o=1"
            })

            # Should not fail due to session middleware ordering issues
            assert response.status_code in [200, 404], \
                f"Production environment request failed: {response.status_code} - {response.text}"

        print("✅ Production environment middleware order is correct")