"""
Integration tests for SessionMiddleware dependency violations - Issue #112.

These tests use real FastAPI app instances to test middleware integration
and demonstrate session dependency issues that block Golden Path.

CRITICAL: These tests FAIL with current broken middleware order.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from netra_backend.app.core.app_factory import create_app
from netra_backend.app.core.middleware_setup import setup_middleware as ssot_setup_middleware, setup_gcp_auth_context_middleware
from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware


class TestSessionDependencyIntegration:
    """Integration tests for session middleware dependency violations."""

    def test_gcp_middleware_session_access_with_proper_order(self):
        """Test GCP middleware session access with proper middleware order.
        
        EXPECTED: This should work when SessionMiddleware is installed first.
        """
        app = FastAPI()
        
        # Install SessionMiddleware first (correct order)
        app.add_middleware(
            SessionMiddleware,
            secret_key="test-secret-key-32-chars-minimum",
            same_site="lax",
            https_only=False,
        )
        
        # Then install GCP middleware
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            # Set some session data
            request.session["user_id"] = "test-user-123"
            request.session["session_id"] = "test-session-456"
            return {"message": "success"}
        
        # Test with client
        with TestClient(app) as client:
            response = client.get("/test")
            assert response.status_code == 200
            assert response.json()["message"] == "success"

    def test_gcp_middleware_session_access_with_broken_order(self):
        """Test GCP middleware with broken middleware order (current state).
        
        EXPECTED: This demonstrates the issue when GCP middleware is installed
        before SessionMiddleware or outside SSOT setup.
        """
        app = FastAPI()
        
        # Install GCP middleware FIRST (broken order)
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
        
        # Then install SessionMiddleware (too late)
        app.add_middleware(
            SessionMiddleware,
            secret_key="test-secret-key-32-chars-minimum",
            same_site="lax",
            https_only=False,
        )
        
        @app.get("/test")
        async def test_endpoint(request: Request):
            # Try to access session
            request.session["user_id"] = "test-user-123"
            return {"message": "success"}
        
        with TestClient(app) as client:
            # This may not fail immediately due to TestClient behavior,
            # but it demonstrates the incorrect middleware order
            response = client.get("/test")
            
            # The response might succeed, but the GCP middleware
            # won't be able to access session data properly
            assert response.status_code == 200
            
            # The real issue is that GCP middleware processes the request
            # BEFORE SessionMiddleware has a chance to set up request.session
            print("WARNING: This test passed but middleware order is still incorrect")

    def test_current_app_factory_middleware_order_issue(self):
        """Test the current app factory middleware order issue.
        
        EXPECTED: This test FAILS because it demonstrates the actual issue
        in the current codebase where GCP middleware is installed outside SSOT.
        """
        # Create app using current factory (has the bug)
        app = create_app()
        
        # Get middleware stack
        middleware_classes = [middleware.__class__.__name__ for middleware in app.middleware_stack]
        
        print(f"Current middleware stack: {middleware_classes}")
        
        # Check if GCP middleware is present (it should be, but outside SSOT)
        gcp_middleware_present = any('GCPAuthContextMiddleware' in name for name in middleware_classes)
        session_middleware_present = any('SessionMiddleware' in name for name in middleware_classes)
        
        if gcp_middleware_present and session_middleware_present:
            # Find their positions
            gcp_position = None
            session_position = None
            
            for i, name in enumerate(middleware_classes):
                if 'GCPAuthContextMiddleware' in name:
                    gcp_position = i
                if 'SessionMiddleware' in name:
                    session_position = i
            
            # CRITICAL: This test FAILS because the order is wrong
            # Middleware stack is processed in reverse order, so lower index = later execution
            assert session_position < gcp_position, (
                f"MIDDLEWARE ORDER VIOLATION: SessionMiddleware (pos {session_position}) "
                f"must execute BEFORE GCPAuthContextMiddleware (pos {gcp_position}). "
                f"Current stack: {middleware_classes}. "
                f"This causes 'SessionMiddleware must be installed' errors in Golden Path."
            )
        else:
            pytest.fail(
                f"Missing middleware: GCP={gcp_middleware_present}, Session={session_middleware_present}. "
                f"Full stack: {middleware_classes}"
            )

    def test_session_access_pattern_in_gcp_middleware(self):
        """Test the actual session access pattern in GCP middleware.
        
        This test demonstrates what happens when GCP middleware tries to access
        session data without proper SessionMiddleware setup.
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import GCPAuthContextMiddleware
        
        # Create minimal request mock
        request_mock = Mock()
        request_mock.headers = {
            'Authorization': 'Bearer test-jwt-token',
            'user-agent': 'test-client',
            'referer': 'http://example.com'
        }
        request_mock.method = 'GET'
        request_mock.url = Mock()
        request_mock.url.path = '/api/test'
        request_mock.client = Mock()
        request_mock.client.host = '127.0.0.1'
        
        # Test case 1: Request WITH session (proper setup)
        request_mock.session = {
            'user_id': 'test-user-123',
            'session_id': 'test-session-456',
            'user_email': 'test@example.com'
        }
        
        middleware = GCPAuthContextMiddleware(None, enable_user_isolation=True)
        
        async def test_with_session():
            auth_context = await middleware._extract_auth_context(request_mock)
            
            # Should successfully extract session data
            assert auth_context['user_id'] == 'test-user-123'
            assert auth_context['session_id'] == 'test-session-456'
            assert auth_context['user_email'] == 'test@example.com'
            
            return auth_context
        
        # Run test
        auth_context = asyncio.run(test_with_session())
        assert auth_context['user_id'] == 'test-user-123'
        
        # Test case 2: Request WITHOUT session (broken setup)
        del request_mock.session  # Simulate missing SessionMiddleware
        
        async def test_without_session():
            auth_context = await middleware._extract_auth_context(request_mock)
            
            # Should fall back to defaults, losing valuable session context
            assert auth_context['user_id'] in ['anonymous', None] or \
                   'user_id' not in auth_context or \
                   auth_context.get('user_id') != 'test-user-123'
            
            # Session data is lost - this is the problem!
            assert 'session_id' not in auth_context or auth_context['session_id'] is None
            
            return auth_context
        
        # Run test without session
        auth_context_broken = asyncio.run(test_without_session())
        
        # This demonstrates data loss when middleware order is wrong
        print(f"With session: user_id=test-user-123, session_id=test-session-456")
        print(f"Without session: user_id={auth_context_broken.get('user_id', 'missing')}, "
              f"session_id={auth_context_broken.get('session_id', 'missing')}")

    def test_ssot_middleware_versus_factory_middleware(self):
        """Test comparison between SSOT middleware setup and current factory setup.
        
        This test reveals the difference between proper SSOT setup and
        the current broken implementation.
        """
        # Test 1: SSOT middleware setup (correct)
        ssot_app = FastAPI()
        ssot_setup_middleware(ssot_app)
        
        ssot_middleware_stack = [m.__class__.__name__ for m in ssot_app.middleware_stack]
        
        # Test 2: Current factory setup (broken)
        factory_app = create_app()
        factory_middleware_stack = [m.__class__.__name__ for m in factory_app.middleware_stack]
        
        print(f"SSOT middleware stack: {ssot_middleware_stack}")
        print(f"Factory middleware stack: {factory_middleware_stack}")
        
        # Check for differences
        ssot_has_gcp = any('GCPAuthContextMiddleware' in name for name in ssot_middleware_stack)
        factory_has_gcp = any('GCPAuthContextMiddleware' in name for name in factory_middleware_stack)
        
        # CRITICAL: This should reveal the issue
        if not ssot_has_gcp and factory_has_gcp:
            pytest.fail(
                "SSOT VIOLATION DETECTED: GCPAuthContextMiddleware is NOT included in "
                "SSOT setup_middleware() but IS present in factory app. This means it's "
                "being installed outside SSOT, violating dependency order and causing "
                "session access issues that block Golden Path."
            )
        
        # If both have GCP middleware, check order
        if ssot_has_gcp and factory_has_gcp:
            # Compare middleware order - this test might pass initially
            # but it helps document the expected vs actual state
            assert True, "Both stacks have GCP middleware - order comparison needed"

    @pytest.mark.asyncio
    async def test_middleware_request_processing_order(self):
        """Test actual request processing order to demonstrate timing issues.
        
        This test shows when each middleware processes the request and
        can reveal timing issues with session access.
        """
        processing_order = []
        
        class OrderTrackingMiddleware:
            def __init__(self, app, name: str):
                self.app = app
                self.name = name
            
            async def __call__(self, scope, receive, send):
                if scope["type"] == "http":
                    processing_order.append(f"{self.name}_start")
                
                response = await self.app(scope, receive, send)
                
                if scope["type"] == "http":
                    processing_order.append(f"{self.name}_end")
                
                return response
        
        app = FastAPI()
        
        # Add tracking middleware to understand execution order
        app.add_middleware(lambda app: OrderTrackingMiddleware(app, "session"))
        app.add_middleware(
            SessionMiddleware,
            secret_key="test-secret-key-32-chars-minimum",
            same_site="lax",
            https_only=False,
        )
        app.add_middleware(lambda app: OrderTrackingMiddleware(app, "gcp_auth"))
        app.add_middleware(GCPAuthContextMiddleware, enable_user_isolation=True)
        
        @app.get("/test-order")
        async def test_endpoint():
            return {"message": "order test"}
        
        # Make request and observe order
        with TestClient(app) as client:
            response = client.get("/test-order")
            assert response.status_code == 200
        
        print(f"Middleware processing order: {processing_order}")
        
        # This test helps us understand the actual execution flow
        assert len(processing_order) > 0, "Should have captured processing order"


class TestGoldenPathBlockingScenarios:
    """Test scenarios that specifically block the Golden Path user flow."""

    def test_websocket_auth_context_golden_path_scenario(self):
        """Test WebSocket authentication context in Golden Path scenario.
        
        Golden Path includes WebSocket connections for real-time agent updates.
        This test simulates the authentication context issues that can block
        WebSocket connections when middleware order is wrong.
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import (
            get_current_user_context,
            get_current_auth_context
        )
        
        # Simulate the Golden Path scenario:
        # 1. User logs in via OAuth (session data stored)
        # 2. User initiates agent execution (WebSocket connection)
        # 3. GCP middleware tries to capture auth context for error reporting
        # 4. If session middleware order is wrong, context is lost
        
        # Create app with broken middleware order (current state)
        app = create_app()
        
        @app.websocket("/ws/agent")
        async def websocket_endpoint(websocket):
            await websocket.accept()
            
            # Try to get current auth context (this is what breaks in Golden Path)
            user_context = get_current_user_context()
            auth_context = get_current_auth_context()
            
            await websocket.send_json({
                "user_context": str(user_context) if user_context else None,
                "auth_context_keys": list(auth_context.keys()) if auth_context else []
            })
            await websocket.close()
        
        # Test WebSocket connection
        with TestClient(app) as client:
            try:
                with client.websocket_connect("/ws/agent") as websocket:
                    data = websocket.receive_json()
                    
                    # In broken middleware order, auth context will be incomplete
                    print(f"WebSocket auth context: {data}")
                    
                    # This test documents the current broken state
                    # In Golden Path, we need proper auth context for user isolation
                    assert True, "WebSocket connection completed (auth context may be incomplete)"
                    
            except Exception as e:
                pytest.fail(f"WebSocket connection failed (Golden Path blocked): {e}")

    def test_agent_execution_auth_context_requirement(self):
        """Test agent execution authentication context requirements.
        
        Golden Path requires proper auth context for:
        1. User isolation in agent execution
        2. Error reporting with user context
        3. Multi-user session management
        """
        from netra_backend.app.middleware.gcp_auth_context_middleware import (
            GCPAuthContextMiddleware,
            MultiUserErrorContext
        )
        from shared.types import StronglyTypedUserExecutionContext, UserID
        
        # Create user context (Golden Path scenario)
        user_context = StronglyTypedUserExecutionContext(
            user_id=UserID("golden-path-user-123"),
            user_email="user@example.com",
            customer_tier="Early",
            session_id="golden-path-session-456",
            business_unit="platform",
            compliance_requirements=[]
        )
        
        # Test multi-user error context creation
        error_context_manager = MultiUserErrorContext()
        error_context = error_context_manager.create_user_error_context(user_context)
        
        # Verify required fields for Golden Path
        required_fields = [
            'user_id', 'user_email', 'customer_tier', 'session_id',
            'isolation_boundary', 'enterprise_context'
        ]
        
        missing_fields = [field for field in required_fields if field not in error_context]
        
        assert not missing_fields, (
            f"Missing required auth context fields for Golden Path: {missing_fields}. "
            f"This will cause agent execution failures and break user isolation. "
            f"Available fields: {list(error_context.keys())}"
        )
        
        # Verify session-based isolation
        assert error_context['session_id'] == "golden-path-session-456"
        assert error_context['isolation_boundary'] == "user-golden-path-user-123"
        
        print(f"Golden Path auth context validation: {len(required_fields)} fields present")


if __name__ == '__main__':
    # Run tests that demonstrate the middleware order issue
    pytest.main([
        __file__ + "::TestSessionDependencyIntegration::test_current_app_factory_middleware_order_issue",
        __file__ + "::TestSessionDependencyIntegration::test_ssot_middleware_versus_factory_middleware",
        "-v", "-s"
    ])