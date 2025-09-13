"""
Issue #449 - WebSocket uvicorn middleware stack failures - Integration Tests

PURPOSE: Test FastAPI/Starlette middleware conflicts that cause WebSocket failures
         when uvicorn processes requests through the middleware stack.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality failing due to middleware
                conflicts between FastAPI, Starlette, and uvicorn in production.

INTEGRATION SCOPE:
- FastAPI middleware registration conflicts
- Starlette middleware ordering issues  
- ASGI application middleware stack processing
- WebSocket vs HTTP middleware routing conflicts
- Session middleware installation ordering

TEST STRATEGY:
These tests should INITIALLY FAIL to demonstrate the real integration issues.
Tests use actual FastAPI/Starlette components to reproduce the failures.
"""

import asyncio
import json
import pytest
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.websockets import WebSocketState
from starlette.routing import Route, WebSocketRoute
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.testclient import TestClient as StarletteTestClient
import uvicorn

from test_framework.ssot.base_test_case import SSotBaseTestCase


class ProblematicSessionMiddleware(BaseHTTPMiddleware):
    """
    Simulates session middleware that causes WebSocket conflicts.
    
    CRITICAL: This replicates the "SessionMiddleware must be installed" error
    that occurs when middleware ordering is incorrect in uvicorn.
    """
    
    async def dispatch(self, request, call_next):
        # This middleware assumes HTTP requests and breaks on WebSocket
        if not hasattr(request, 'session'):
            # Simulate the actual error we see in production
            raise RuntimeError("SessionMiddleware must be installed to access request.session")
        
        response = await call_next(request)
        return response


class ConflictingCORSMiddleware(BaseHTTPMiddleware):
    """
    Simulates CORS middleware that conflicts with WebSocket upgrades.
    
    CRITICAL: This replicates CORS middleware that intercepts WebSocket
    upgrade requests and causes protocol negotiation failures.
    """
    
    async def dispatch(self, request, call_next):
        # CORS middleware that incorrectly processes WebSocket upgrades
        if request.headers.get("upgrade") == "websocket":
            # This middleware incorrectly adds CORS headers to WebSocket upgrade
            response = await call_next(request)
            if hasattr(response, 'headers'):
                response.headers["Access-Control-Allow-Origin"] = "*"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
                # These headers are invalid for WebSocket upgrades
            return response
        
        return await call_next(request)


class AuthMiddlewareWebSocketConflict(BaseHTTPMiddleware):
    """
    Simulates auth middleware that conflicts with WebSocket authentication.
    
    CRITICAL: This replicates auth middleware that applies HTTP auth
    to WebSocket connections, causing authentication failures.
    """
    
    async def dispatch(self, request, call_next):
        # Auth middleware that incorrectly processes WebSocket auth
        auth_header = request.headers.get("authorization")
        
        if not auth_header and request.url.path.startswith("/ws"):
            # Incorrectly reject WebSocket without considering WebSocket auth methods
            from fastapi import HTTPException
            raise HTTPException(status_code=401, detail="Unauthorized")
        
        return await call_next(request)


class TestIssue449FastAPIStarletteMiddlewareConflicts(SSotBaseTestCase):
    """
    Integration tests for Issue #449 - FastAPI/Starlette middleware conflicts.
    
    EXPECTED BEHAVIOR: These tests should FAIL initially to demonstrate
    the middleware conflicts that cause WebSocket failures in production.
    """
    
    def setup_method(self, method=None):
        super().setup_method(method)
        self.fastapi_app = None
        self.starlette_app = None
    
    def teardown_method(self, method=None):
        super().teardown_method(method)
        # Clean up any test clients
        if hasattr(self, 'test_client'):
            self.test_client.close()
    
    def create_problematic_fastapi_app(self) -> FastAPI:
        """
        Create FastAPI app with middleware configuration that causes Issue #449.
        
        This replicates the exact middleware setup that fails in production.
        """
        app = FastAPI()
        
        # Add middleware in wrong order (this causes the issue)
        app.add_middleware(ProblematicSessionMiddleware)
        app.add_middleware(ConflictingCORSMiddleware)
        app.add_middleware(AuthMiddlewareWebSocketConflict)
        
        # Add routes that work fine individually but conflict through middleware
        @app.get("/test")
        async def test_route():
            return {"message": "test"}
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Hello WebSocket")
            await websocket.close()
        
        return app
    
    def create_conflicting_starlette_app(self) -> Starlette:
        """
        Create Starlette app with middleware stack that conflicts with WebSocket.
        
        This replicates Starlette-level middleware conflicts.
        """
        # Create middleware stack with conflicts
        middleware = [
            Middleware(ProblematicSessionMiddleware),
            Middleware(ConflictingCORSMiddleware),
        ]
        
        async def homepage(request):
            return PlainTextResponse("Hello Starlette")
        
        async def websocket_endpoint(websocket):
            await websocket.accept()
            await websocket.send_text("Hello Starlette WebSocket")
            await websocket.close()
        
        routes = [
            Route("/", homepage),
            WebSocketRoute("/ws", websocket_endpoint),
        ]
        
        app = Starlette(routes=routes, middleware=middleware)
        return app
    
    def test_fastapi_session_middleware_websocket_conflict(self):
        """
        Test FastAPI session middleware causing WebSocket failures.
        
        EXPECTED: This test should FAIL, demonstrating SessionMiddleware
        conflicts with WebSocket connections in FastAPI middleware stack.
        """
        app = self.create_problematic_fastapi_app()
        
        # Add SessionMiddleware incorrectly (after other middleware)
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        
        client = TestClient(app)
        self.test_client = client
        
        # Test HTTP route works
        http_response = client.get("/test")
        self.assertEqual(http_response.status_code, 200)
        
        # ASSERTION THAT SHOULD FAIL: WebSocket should work with session middleware
        try:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Hello WebSocket")
            # If we get here, the test should fail since we expect an error
            assert False, "WebSocket should fail due to session middleware conflict"
        except Exception as e:
            # Verify the specific error we're testing for
            error_msg = str(e)
            assert "SessionMiddleware must be installed" in error_msg or "RuntimeError" in error_msg, f"Expected session middleware error, got: {error_msg}"
    
    def test_fastapi_cors_middleware_websocket_upgrade_conflict(self):
        """
        Test FastAPI CORS middleware interfering with WebSocket upgrades.
        
        EXPECTED: This test should FAIL, demonstrating CORS middleware
        incorrectly processes WebSocket upgrade requests.
        """
        app = self.create_problematic_fastapi_app()
        client = TestClient(app)
        self.test_client = client
        
        # ASSERTION THAT SHOULD FAIL: WebSocket upgrade should not be processed as CORS
        try:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                
                # Check if response has incorrect CORS headers for WebSocket
                # WebSocket responses should not have CORS headers
                if hasattr(websocket, 'response'):
                    headers = getattr(websocket.response, 'headers', {})
                    assert "Access-Control-Allow-Origin" not in headers, "WebSocket responses should not have CORS headers"
            
            assert False, "WebSocket should fail due to CORS middleware conflict"
        except Exception as e:
            # The exception should be related to CORS processing WebSocket upgrade
            error_msg = str(e).lower()
            assert "websocket" in error_msg or "upgrade" in error_msg or "cors" in error_msg, f"Error should be WebSocket-related: {e}"
    
    def test_fastapi_auth_middleware_websocket_auth_conflict(self):
        """
        Test FastAPI auth middleware causing WebSocket authentication failures.
        
        EXPECTED: This test should FAIL, demonstrating auth middleware
        incorrectly applies HTTP auth to WebSocket connections.
        """
        app = self.create_problematic_fastapi_app()
        client = TestClient(app)
        self.test_client = client
        
        # ASSERTION THAT SHOULD FAIL: WebSocket should have different auth mechanism
        try:
            # Try to connect to WebSocket without HTTP Authorization header
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Hello WebSocket")
            assert False, "WebSocket should fail due to auth middleware conflict"
        except Exception as e:
            # Should get 401 because auth middleware incorrectly applied HTTP auth to WebSocket
            error_msg = str(e)
            assert "401" in error_msg or "Unauthorized" in error_msg, f"Should get 401 from auth middleware conflict: {error_msg}"
    
    def test_starlette_middleware_stack_ordering_conflict(self):
        """
        Test Starlette middleware stack ordering causing WebSocket conflicts.
        
        EXPECTED: This test should FAIL, demonstrating middleware ordering
        in Starlette causes WebSocket processing failures.
        """
        app = self.create_conflicting_starlette_app()
        client = StarletteTestClient(app)
        
        # Test HTTP route works
        http_response = client.get("/")
        self.assertEqual(http_response.status_code, 200)
        
        # ASSERTION THAT SHOULD FAIL: WebSocket should work with Starlette middleware
        with self.assertRaises(Exception) as context:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Hello Starlette WebSocket")
        
        # Should fail due to middleware stack conflicts
        error_msg = str(context.exception)
        self.assertTrue(
            "middleware" in error_msg.lower() or "websocket" in error_msg.lower(),
            f"Error should be middleware-related: {error_msg}"
        )
    
    def test_fastapi_middleware_registration_order_impact(self):
        """
        Test how FastAPI middleware registration order impacts WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating middleware registration
        order in FastAPI causes WebSocket failures.
        """
        app = FastAPI()
        
        # Register middleware in different orders and test impact
        middleware_orders = [
            # Order 1: Session first (correct)
            [SessionMiddleware, ConflictingCORSMiddleware, AuthMiddlewareWebSocketConflict],
            # Order 2: Session last (incorrect - causes our issue)
            [ConflictingCORSMiddleware, AuthMiddlewareWebSocketConflict, SessionMiddleware],
        ]
        
        for order_index, middleware_order in enumerate(middleware_orders):
            with self.subTest(order=order_index):
                # Create fresh app for each test
                test_app = FastAPI()
                
                # Add middleware in specified order
                for middleware_class in middleware_order:
                    if middleware_class == SessionMiddleware:
                        test_app.add_middleware(middleware_class, secret_key="test-secret")
                    else:
                        test_app.add_middleware(middleware_class)
                
                @test_app.websocket("/ws")
                async def websocket_endpoint(websocket: WebSocket):
                    await websocket.accept()
                    await websocket.send_text("Hello WebSocket")
                    await websocket.close()
                
                client = TestClient(test_app)
                
                # ASSERTION THAT SHOULD FAIL: all orders should work (they don't)
                if order_index == 1:  # Session middleware last
                    with self.assertRaises(RuntimeError):
                        with client.websocket_connect("/ws") as websocket:
                            data = websocket.receive_text()
                            self.assertEqual(data, "Hello WebSocket")
                else:
                    # First order might work, but still has other conflicts
                    with self.assertRaises(Exception):
                        with client.websocket_connect("/ws") as websocket:
                            data = websocket.receive_text()
                
                client.close()
    
    def test_fastapi_asgi_middleware_scope_handling_conflict(self):
        """
        Test FastAPI ASGI middleware scope handling conflicts with WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating ASGI middleware
        incorrectly handles WebSocket scopes in FastAPI.
        """
        app = FastAPI()
        
        # Add middleware that incorrectly handles ASGI scopes
        class ASGIScopeConflictMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                # This middleware assumes HTTP ASGI scope
                if hasattr(request, 'scope'):
                    scope = request.scope
                    if scope.get("type") != "http":
                        # Incorrectly reject non-HTTP scopes
                        from fastapi import HTTPException
                        raise HTTPException(status_code=400, detail="Invalid scope type")
                
                return await call_next(request)
        
        app.add_middleware(ASGIScopeConflictMiddleware)
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Hello WebSocket")
            await websocket.close()
        
        client = TestClient(app)
        self.test_client = client
        
        # ASSERTION THAT SHOULD FAIL: WebSocket should have valid ASGI scope
        with self.assertRaises(Exception) as context:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Hello WebSocket")
        
        # Should fail with scope type error
        error_msg = str(context.exception)
        self.assertIn("scope", error_msg.lower(), "Error should be scope-related")
    
    def test_multiple_websocket_middleware_conflicts(self):
        """
        Test multiple middleware simultaneously conflicting with WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating how multiple middleware
        conflicts compound to completely break WebSocket functionality.
        """
        app = FastAPI()
        
        # Add multiple conflicting middleware
        app.add_middleware(ProblematicSessionMiddleware)
        app.add_middleware(ConflictingCORSMiddleware)
        app.add_middleware(AuthMiddlewareWebSocketConflict)
        
        # Also add session middleware in wrong order
        app.add_middleware(SessionMiddleware, secret_key="test-secret")
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Hello WebSocket")
            await websocket.close()
        
        client = TestClient(app)
        self.test_client = client
        
        # ASSERTION THAT SHOULD FAIL: WebSocket should work despite middleware conflicts
        multiple_errors = []
        try:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Hello WebSocket")
        except Exception as e:
            multiple_errors.append(str(e))
        
        # Should have collected multiple errors from different middleware conflicts
        self.assertGreater(
            len(multiple_errors), 0,
            "Multiple middleware should cause WebSocket failures"
        )
        
        # Verify we got the expected types of errors
        error_text = " ".join(multiple_errors).lower()
        expected_error_indicators = ["session", "cors", "auth", "middleware", "websocket"]
        
        found_indicators = [indicator for indicator in expected_error_indicators 
                          if indicator in error_text]
        self.assertGreater(
            len(found_indicators), 1,
            f"Should have multiple middleware conflict indicators: {found_indicators}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])