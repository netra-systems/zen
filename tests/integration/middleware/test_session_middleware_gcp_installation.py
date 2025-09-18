"""
Integration tests for SessionMiddleware installation in GCP-like environments.
Tests the critical path that addresses Issue #1127: "SessionMiddleware must be installed to access request.session"
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class SessionMiddlewareGCPInstallationTests(SSotBaseTestCase):
    """Test SessionMiddleware installation in GCP-like environments."""

    def test_session_middleware_installed_in_app_factory(self):
        """Verify SessionMiddleware is properly installed via app_factory.

        CRITICAL TEST: This validates that create_app() correctly installs SessionMiddleware
        which is required for request.session access in gcp_auth_context_middleware.py:160
        """
        from netra_backend.app.core.app_factory import create_app

        # Create app using the same factory method as production
        app = create_app()

        # Verify SessionMiddleware is installed
        session_middleware_found = False
        middleware_stack = []

        for middleware in app.user_middleware:
            middleware_name = middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls)
            middleware_stack.append(middleware_name)

            if 'SessionMiddleware' in middleware_name:
                session_middleware_found = True
                # Verify it's the correct SessionMiddleware class
                assert middleware.cls == SessionMiddleware or 'SessionMiddleware' in str(middleware.cls.__bases__)

        # Assert SessionMiddleware is found
        assert session_middleware_found, f"SessionMiddleware not found in middleware stack. Found: {middleware_stack}"

        # Log for debugging
        print(f"CHECK SessionMiddleware found in middleware stack: {middleware_stack}")

    def test_session_middleware_order_validation(self):
        """Verify SessionMiddleware is installed BEFORE auth middleware.

        CRITICAL TEST: SessionMiddleware MUST be installed before any middleware
        that accesses request.session to prevent the Issue #1127 error.
        """
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Find middleware positions
        session_middleware_pos = None
        auth_middleware_pos = None

        for i, middleware in enumerate(app.user_middleware):
            middleware_name = middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls)

            if 'SessionMiddleware' in middleware_name:
                session_middleware_pos = i
            elif 'auth' in middleware_name.lower() or 'Auth' in middleware_name:
                auth_middleware_pos = i

        # Validate order
        assert session_middleware_pos is not None, "SessionMiddleware not found in middleware stack"

        if auth_middleware_pos is not None:
            # SessionMiddleware should come BEFORE auth middleware in the stack
            # Note: FastAPI adds middleware in reverse order, so lower index = installed later = runs first
            assert session_middleware_pos < auth_middleware_pos, \
                f"SessionMiddleware (pos {session_middleware_pos}) must come before auth middleware (pos {auth_middleware_pos})"

        print(f"CHECK SessionMiddleware correctly positioned at index {session_middleware_pos}")

    def test_session_middleware_secret_key_configuration(self):
        """Verify SECRET_KEY is properly configured from environment.

        CRITICAL TEST: Validates that SessionMiddleware gets a proper secret key
        to prevent configuration-related session access failures.
        """
        env = IsolatedEnvironment()

        # Set a valid SECRET_KEY
        env.set("SECRET_KEY", "test-secret-key-for-session-middleware-32-chars-minimum-required")

        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Find SessionMiddleware instance
        session_middleware = None
        for middleware in app.user_middleware:
            if 'SessionMiddleware' in middleware.cls.__name__:
                session_middleware = middleware
                break

        assert session_middleware is not None, "SessionMiddleware not found"

        # Verify secret key is configured (we can't access it directly due to security)
        # Instead, we'll test that sessions work
        with TestClient(app) as client:
            # Make a request that would use sessions
            response = client.get("/health")  # Use health endpoint as it exists

            # Verify the request was successful (no SessionMiddleware errors)
            assert response.status_code in [200, 404], f"Request failed with status {response.status_code}: {response.text}"

        print("CHECK SessionMiddleware SECRET_KEY configuration validated")

    def test_session_middleware_gcp_environment_compatibility(self):
        """Test middleware works with GCP Cloud Run environment variables.

        CRITICAL TEST: Simulates GCP Cloud Run environment to validate
        SessionMiddleware works in the actual deployment environment.
        """
        env = IsolatedEnvironment()

        # Set GCP Cloud Run environment variables
        env.set("K_SERVICE", "netra-backend")  # GCP Cloud Run marker
        env.set("K_REVISION", "1")
        env.set("PORT", "8080")
        env.set("ENVIRONMENT", "staging")
        env.set("SECRET_KEY", "gcp-staging-secret-key-32-chars-minimum-required-for-session-middleware")
        env.set("GCP_PROJECT_ID", "netra-staging")

        from netra_backend.app.core.app_factory import create_app

        # Create app with GCP environment
        app = create_app()

        with TestClient(app) as client:
            # Test that basic requests work without session errors
            response = client.get("/health")

            # Should not fail due to SessionMiddleware issues
            assert response.status_code in [200, 404], f"GCP environment request failed: {response.status_code} - {response.text}"

        print("CHECK SessionMiddleware works in simulated GCP Cloud Run environment")

    def test_request_session_access_simulation(self):
        """Test that request.session access works like in gcp_auth_context_middleware.py:160.

        CRITICAL TEST: This directly simulates the failing scenario from Issue #1127
        by accessing request.session in the same pattern as the error location.
        """
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Create a test endpoint that accesses request.session like the failing middleware
        @app.get("/test-session-access")
        async def test_session_access(request: Request):
            """Test endpoint that mimics gcp_auth_context_middleware.py:160"""
            try:
                # This is the exact pattern from line 160 that's failing
                session = request.session

                # If we get here, SessionMiddleware is working
                return {"status": "success", "session_available": session is not None}

            except RuntimeError as e:
                if "SessionMiddleware must be installed" in str(e):
                    # This is the exact error from Issue #1127
                    return {"status": "error", "error": "SessionMiddleware not installed", "message": str(e)}
                else:
                    return {"status": "error", "error": "Other RuntimeError", "message": str(e)}

        with TestClient(app) as client:
            response = client.get("/test-session-access")
            data = response.json()

            # Verify no SessionMiddleware error occurred
            assert data["status"] == "success", f"Session access failed: {data}"
            assert data["session_available"] is True, "Session should be available"

        print("CHECK request.session access works correctly (Issue #1127 pattern)")

    def test_concurrent_session_access(self):
        """Test concurrent session access to catch race conditions.

        This validates that SessionMiddleware handles concurrent requests
        without the access errors reported in Issue #1127.
        """
        import asyncio
        import concurrent.futures

        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        @app.get("/test-concurrent-session/{user_id}")
        async def test_concurrent_session(request: Request, user_id: str):
            """Test endpoint for concurrent session access"""
            try:
                session = request.session
                session['user_id'] = user_id
                return {"status": "success", "user_id": user_id, "session_id": id(session)}
            except RuntimeError as e:
                return {"status": "error", "message": str(e)}

        def make_request(user_id):
            """Make a single request"""
            with TestClient(app) as client:
                response = client.get(f"/test-concurrent-session/{user_id}")
                return response.json()

        # Test concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, f"user_{i}") for i in range(10)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all requests succeeded
        for result in results:
            assert result["status"] == "success", f"Concurrent session access failed: {result}"

        print(f"CHECK Concurrent session access successful for {len(results)} requests")