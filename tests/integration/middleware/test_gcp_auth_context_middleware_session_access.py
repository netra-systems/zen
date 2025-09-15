"""
Integration tests for GCP Auth Context middleware session access.
Tests the specific failure scenario from Issue #1127: gcp_auth_context_middleware.py:160
"""
import pytest
from unittest.mock import patch, Mock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment


class GCPAuthContextMiddlewareSessionAccessTests(SSotBaseTestCase):
    """Test GCP Auth Context middleware session access patterns from Issue #1127."""

    def test_gcp_auth_context_middleware_session_access_exact_scenario(self):
        """Test exact line 160 scenario from gcp_auth_context_middleware.py.

        CRITICAL TEST: This reproduces the exact error condition from Issue #1127
        where gcp_auth_context_middleware.py:160 fails with "SessionMiddleware must be installed"
        """
        from netra_backend.app.core.app_factory import create_app

        # Create app with full middleware stack
        app = create_app()

        # Create a test endpoint that simulates the GCP auth context middleware behavior
        @app.get("/test-gcp-auth-context")
        async def test_gcp_auth_context(request: Request):
            """Simulate the exact session access pattern from gcp_auth_context_middleware.py:160"""
            try:
                # This is the exact pattern that's failing in production
                session_data = {}

                # Line 160: session = request.session
                session = request.session

                if session:
                    session_data.update({
                        'session_id': session.get('session_id'),
                        'user_id': session.get('user_id'),
                        'test_timestamp': '2025-01-15T12:00:00Z'
                    })

                return {
                    "status": "success",
                    "session_data": session_data,
                    "session_available": session is not None
                }

            except RuntimeError as e:
                # Catch the specific error from Issue #1127
                if "SessionMiddleware must be installed" in str(e):
                    return {
                        "status": "error",
                        "error_type": "SessionMiddleware_not_installed",
                        "message": str(e),
                        "issue_reference": "#1127"
                    }
                else:
                    return {
                        "status": "error",
                        "error_type": "other_runtime_error",
                        "message": str(e)
                    }

        # Test with GCP-like headers that would trigger the middleware
        with TestClient(app) as client:
            response = client.get("/test-gcp-auth-context", headers={
                "X-Forwarded-For": "10.0.0.1",  # GCP internal IP
                "User-Agent": "GCP-Health-Check/1.0",
                "X-Cloud-Trace-Context": "test-trace-id",
            })

            data = response.json()

            # Verify no session access errors occurred
            assert response.status_code == 200, f"Request failed with status {response.status_code}: {response.text}"
            assert data["status"] == "success", f"Session access failed in GCP auth context pattern: {data}"
            assert data["session_available"] is True, "Session should be available for GCP auth context middleware"

        print("✅ GCP Auth Context middleware session access pattern works (Issue #1127 fixed)")

    def test_middleware_chain_with_gcp_auth_context_enabled(self):
        """Test middleware chain when GCP auth context middleware is actually enabled.

        CRITICAL TEST: This validates the middleware chain when GCP auth context middleware
        is actually installed and trying to access request.session.
        """
        env = IsolatedEnvironment()

        # Set environment to enable GCP auth context middleware
        env.set("ENVIRONMENT", "staging")
        env.set("GCP_PROJECT_ID", "netra-staging")
        env.set("GOOGLE_CLOUD_PROJECT", "netra-staging")
        env.set("SECRET_KEY", "gcp-test-secret-key-32-chars-minimum-required-for-middleware-testing")

        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        # Check that GCP Auth Context middleware is in the stack
        gcp_auth_middleware_found = False
        session_middleware_found = False
        middleware_stack = []

        for middleware in app.user_middleware:
            middleware_name = middleware.cls.__name__ if hasattr(middleware.cls, '__name__') else str(middleware.cls)
            middleware_stack.append(middleware_name)

            if 'SessionMiddleware' in middleware_name:
                session_middleware_found = True
            elif 'GCPAuth' in middleware_name or 'gcp_auth' in middleware_name.lower():
                gcp_auth_middleware_found = True

        print(f"Middleware stack: {middleware_stack}")

        # Verify SessionMiddleware is installed (required for GCP auth context)
        assert session_middleware_found, f"SessionMiddleware not found, but required for GCP auth context. Stack: {middleware_stack}"

        # Test that requests work without session errors when both middleware are present
        with TestClient(app) as client:
            response = client.get("/health", headers={
                "X-Forwarded-For": "35.235.240.1",  # GCP Cloud Run IP range
                "User-Agent": "GoogleHC/1.0",
                "X-Cloud-Trace-Context": "105445aa7843bc8bf206b12000100000/1;o=1"
            })

            # Should not fail due to session middleware issues
            assert response.status_code in [200, 404], f"Request with GCP headers failed: {response.status_code} - {response.text}"

        print("✅ GCP Auth Context middleware chain works with SessionMiddleware")

    def test_session_persistence_across_requests(self):
        """Test session data persists across requests in GCP auth context.

        This validates that session data set by GCP auth context middleware
        persists correctly across multiple requests.
        """
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        @app.get("/set-session")
        async def set_session(request: Request):
            """Set session data like GCP auth context middleware would"""
            session = request.session
            session.update({
                'user_id': 'gcp-test-user-123',
                'session_id': 'gcp-session-456',
                'auth_provider': 'gcp',
                'timestamp': '2025-01-15T12:00:00Z'
            })
            return {"status": "session_set", "session_id": session.get('session_id')}

        @app.get("/get-session")
        async def get_session(request: Request):
            """Get session data like other parts of the system would"""
            session = request.session
            return {
                "status": "session_retrieved",
                "session_data": dict(session),
                "session_available": session is not None
            }

        with TestClient(app) as client:
            # First request: set session data
            set_response = client.get("/set-session")
            set_data = set_response.json()

            assert set_response.status_code == 200
            assert set_data["status"] == "session_set"
            assert set_data["session_id"] == "gcp-session-456"

            # Second request: retrieve session data (should persist)
            get_response = client.get("/get-session")
            get_data = get_response.json()

            assert get_response.status_code == 200
            assert get_data["status"] == "session_retrieved"
            assert get_data["session_available"] is True
            assert get_data["session_data"]["user_id"] == "gcp-test-user-123"
            assert get_data["session_data"]["session_id"] == "gcp-session-456"

        print("✅ Session data persists across requests in GCP auth context pattern")

    def test_session_access_with_real_fastapi_request(self):
        """Test session access with real FastAPI Request object.

        CRITICAL TEST: This uses the exact same Request object type and pattern
        that would be used in the actual gcp_auth_context_middleware.py:160 scenario.
        """
        from netra_backend.app.core.app_factory import create_app
        from fastapi import Request

        app = create_app()

        @app.middleware("http")
        async def test_gcp_auth_middleware(request: Request, call_next):
            """Simulate the exact middleware pattern from gcp_auth_context_middleware.py"""

            # This simulates the exact code path that's failing
            session_data = {}

            try:
                # Line 160 from gcp_auth_context_middleware.py: session = request.session
                session = request.session

                if session:
                    session_data.update({
                        'session_id': session.get('session_id'),
                        'user_id': session.get('user_id'),
                        'middleware_test': 'gcp_auth_context_simulation'
                    })

                # Add to request state for verification
                request.state.session_test_data = session_data
                request.state.session_accessible = True

            except RuntimeError as e:
                # Catch the exact error condition
                request.state.session_accessible = False
                request.state.session_error = str(e)

            response = await call_next(request)
            return response

        @app.get("/test-middleware-session")
        async def test_endpoint(request: Request):
            """Test endpoint to verify middleware session access"""
            return {
                "session_accessible": getattr(request.state, 'session_accessible', False),
                "session_error": getattr(request.state, 'session_error', None),
                "session_test_data": getattr(request.state, 'session_test_data', {}),
                "request_id": id(request)
            }

        with TestClient(app) as client:
            response = client.get("/test-middleware-session")
            data = response.json()

            # Verify session was accessible in middleware
            assert response.status_code == 200
            assert data["session_accessible"] is True, f"Session not accessible in middleware: {data.get('session_error')}"
            assert data["session_error"] is None, f"Session access error in middleware: {data['session_error']}"

        print("✅ Real FastAPI Request session access works in middleware pattern")

    def test_session_access_error_handling(self):
        """Test graceful handling when SessionMiddleware is missing.

        This validates that our error handling works when SessionMiddleware
        is not properly installed, which is the root cause of Issue #1127.
        """
        # Create an app WITHOUT SessionMiddleware to simulate the error condition
        app = FastAPI()

        # Intentionally skip SessionMiddleware installation to reproduce the error

        @app.get("/test-missing-session-middleware")
        async def test_missing_session_middleware(request: Request):
            """Test what happens when SessionMiddleware is missing"""
            try:
                # This should fail with "SessionMiddleware must be installed"
                session = request.session
                return {"status": "unexpected_success", "session_available": True}

            except RuntimeError as e:
                if "SessionMiddleware must be installed" in str(e):
                    return {
                        "status": "expected_error_reproduced",
                        "error": str(e),
                        "issue_reference": "#1127"
                    }
                else:
                    return {"status": "unexpected_error", "error": str(e)}

        with TestClient(app) as client:
            response = client.get("/test-missing-session-middleware")
            data = response.json()

            # Verify we can reproduce the Issue #1127 error condition
            assert response.status_code == 200
            assert data["status"] == "expected_error_reproduced", f"Did not reproduce Issue #1127 error: {data}"
            assert "SessionMiddleware must be installed" in data["error"]

        print("✅ Successfully reproduced Issue #1127 error condition when SessionMiddleware is missing")

    def test_concurrent_gcp_auth_context_session_access(self):
        """Test concurrent session access in GCP auth context pattern.

        This validates that multiple concurrent requests don't cause
        session access failures due to middleware ordering or race conditions.
        """
        import concurrent.futures
        from netra_backend.app.core.app_factory import create_app

        app = create_app()

        @app.get("/concurrent-gcp-session/{request_id}")
        async def concurrent_gcp_session(request: Request, request_id: str):
            """Simulate concurrent GCP auth context session access"""
            try:
                # Pattern from gcp_auth_context_middleware.py
                session_data = {}
                session = request.session

                if session:
                    session_data.update({
                        'request_id': request_id,
                        'user_id': f'gcp-user-{request_id}',
                        'session_id': f'session-{request_id}',
                        'timestamp': '2025-01-15T12:00:00Z'
                    })

                    # Update session with request-specific data
                    session.update(session_data)

                return {
                    "status": "success",
                    "request_id": request_id,
                    "session_data": session_data,
                    "session_available": session is not None
                }

            except RuntimeError as e:
                return {
                    "status": "error",
                    "request_id": request_id,
                    "error": str(e),
                    "error_type": "session_access_failure"
                }

        def make_concurrent_request(request_id):
            """Make a single request with unique ID"""
            with TestClient(app) as client:
                response = client.get(f"/concurrent-gcp-session/{request_id}")
                return response.json()

        # Test 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(make_concurrent_request, f"req_{i}")
                for i in range(20)
            ]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Verify all requests succeeded
        success_count = 0
        error_count = 0

        for result in results:
            if result["status"] == "success":
                success_count += 1
                assert result["session_available"] is True
            else:
                error_count += 1
                print(f"❌ Request {result['request_id']} failed: {result['error']}")

        assert error_count == 0, f"Some concurrent requests failed: {error_count} errors out of {len(results)} requests"
        assert success_count == 20, f"Expected 20 successful requests, got {success_count}"

        print(f"✅ All {success_count} concurrent GCP auth context session access requests succeeded")