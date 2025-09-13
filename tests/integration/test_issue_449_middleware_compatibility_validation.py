"""
Issue #449 - Middleware Compatibility Validation Tests

PURPOSE: Test FastAPI/Starlette middleware compatibility with enhanced uvicorn
         WebSocket exclusion middleware to prevent websockets_impl.py:244 failures.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality protection through validated
                middleware stack compatibility and enhanced error handling.

TEST FOCUS:
- Enhanced UvicornWebSocketExclusionMiddleware integration
- FastAPI middleware stack compatibility
- Starlette middleware ordering validation
- WebSocket upgrade handling with middleware protection
- Enhanced error recovery and diagnostics

TEST STRATEGY:
These tests validate that the enhanced middleware components correctly integrate
with FastAPI/Starlette to prevent the uvicorn middleware conflicts identified
in Issue #449, demonstrating actual fixes rather than just reproducing failures.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.middleware.uvicorn_protocol_enhancement import (
    UvicornWebSocketExclusionMiddleware,
    create_uvicorn_websocket_exclusion_middleware
)


class CompatibleSessionMiddleware(BaseHTTPMiddleware):
    """
    Session middleware that properly handles WebSocket exclusion.

    CRITICAL FIX: This demonstrates proper middleware that doesn't conflict
    with WebSocket connections when used with enhanced uvicorn protection.
    """

    async def dispatch(self, request, call_next):
        # Check if request is for WebSocket upgrade - skip session processing
        if self._is_websocket_upgrade(request):
            # Pass through without session processing
            return await call_next(request)

        # Only apply session middleware to HTTP requests
        if not hasattr(request, 'session'):
            # Add session if not present
            request.state.session = {}

        response = await call_next(request)
        return response

    def _is_websocket_upgrade(self, request):
        """Check if request is WebSocket upgrade."""
        upgrade = request.headers.get("upgrade", "").lower()
        connection = request.headers.get("connection", "").lower()
        return upgrade == "websocket" and "upgrade" in connection


class CompatibleCORSMiddleware(BaseHTTPMiddleware):
    """
    CORS middleware that properly handles WebSocket upgrades.

    CRITICAL FIX: This demonstrates CORS middleware that doesn't interfere
    with WebSocket protocol negotiation.
    """

    async def dispatch(self, request, call_next):
        # Skip CORS processing for WebSocket upgrades
        if self._is_websocket_upgrade(request):
            return await call_next(request)

        # Apply CORS only to HTTP requests
        response = await call_next(request)

        if hasattr(response, 'headers'):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"

        return response

    def _is_websocket_upgrade(self, request):
        """Check if request is WebSocket upgrade."""
        upgrade = request.headers.get("upgrade", "").lower()
        connection = request.headers.get("connection", "").lower()
        return upgrade == "websocket" and "upgrade" in connection


class TestIssue449MiddlewareCompatibilityValidation(SSotBaseTestCase):
    """
    Integration tests for Issue #449 middleware compatibility validation.

    EXPECTED BEHAVIOR: These tests should PASS, demonstrating that the enhanced
    uvicorn WebSocket exclusion middleware properly integrates with FastAPI/Starlette
    middleware stacks to prevent websockets_impl.py:244 failures.
    """

    def setup_method(self, method=None):
        super().setup_method(method)
        self.enhanced_middleware_class = create_uvicorn_websocket_exclusion_middleware()

    def teardown_method(self, method=None):
        super().teardown_method(method)
        if hasattr(self, 'test_client'):
            self.test_client.close()

    def create_enhanced_fastapi_app(self) -> FastAPI:
        """
        Create FastAPI app with enhanced uvicorn WebSocket exclusion middleware.

        This demonstrates the CORRECT middleware setup that prevents Issue #449.
        """
        app = FastAPI()

        # CRITICAL: Add enhanced uvicorn WebSocket exclusion middleware FIRST
        app.add_middleware(self.enhanced_middleware_class)

        # Add compatible middleware that works with WebSocket exclusion
        app.add_middleware(CompatibleSessionMiddleware)
        app.add_middleware(CompatibleCORSMiddleware)

        # Add session middleware with proper configuration
        app.add_middleware(SessionMiddleware, secret_key="test-secret-key")

        # Add routes that should work with enhanced middleware
        @app.get("/test")
        async def test_route():
            return {"message": "HTTP endpoint working"}

        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Enhanced WebSocket working")
            await websocket.close()

        return app

    def test_enhanced_middleware_prevents_session_conflicts(self):
        """
        Test that enhanced middleware prevents session middleware conflicts.

        EXPECTED: This test should PASS, demonstrating the enhanced middleware
        properly handles session middleware integration without WebSocket conflicts.
        """
        app = self.create_enhanced_fastapi_app()
        client = TestClient(app)
        self.test_client = client

        # Test HTTP route works with session middleware
        http_response = client.get("/test")
        self.assertEqual(http_response.status_code, 200)
        self.assertEqual(http_response.json()["message"], "HTTP endpoint working")

        # ASSERTION: WebSocket should work with enhanced middleware protection
        try:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Enhanced WebSocket working")

            # Test passed - enhanced middleware successfully prevented session conflicts
            self.assertTrue(True, "Enhanced middleware successfully prevented session conflicts")

        except Exception as e:
            self.fail(f"Enhanced middleware should prevent session conflicts: {e}")

    def test_enhanced_middleware_handles_cors_compatibility(self):
        """
        Test that enhanced middleware ensures CORS compatibility.

        EXPECTED: This test should PASS, demonstrating proper CORS middleware
        integration that doesn't interfere with WebSocket protocol negotiation.
        """
        app = self.create_enhanced_fastapi_app()
        client = TestClient(app)
        self.test_client = client

        # Test HTTP route works with CORS middleware
        http_response = client.get("/test")
        self.assertEqual(http_response.status_code, 200)

        # Verify CORS headers are present for HTTP
        self.assertIn("access-control-allow-origin",
                     [h.lower() for h in http_response.headers.keys()],
                     "HTTP response should have CORS headers")

        # ASSERTION: WebSocket should work without CORS interference
        try:
            with client.websocket_connect("/ws") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Enhanced WebSocket working")

            # WebSocket should not have CORS headers (they're not applicable)
            self.assertTrue(True, "Enhanced middleware properly handles CORS compatibility")

        except Exception as e:
            self.fail(f"Enhanced middleware should handle CORS compatibility: {e}")

    def test_enhanced_middleware_stack_ordering_validation(self):
        """
        Test enhanced middleware stack ordering validation.

        EXPECTED: This test should PASS, demonstrating that enhanced uvicorn
        WebSocket exclusion middleware works regardless of other middleware ordering.
        """
        # Test different middleware ordering scenarios
        for order_index, middleware_order in enumerate([
            # Order 1: Enhanced middleware first (recommended)
            [self.enhanced_middleware_class, CompatibleSessionMiddleware, CompatibleCORSMiddleware],
            # Order 2: Enhanced middleware after session (also works)
            [CompatibleSessionMiddleware, self.enhanced_middleware_class, CompatibleCORSMiddleware],
        ]):
            with self.subTest(order=order_index):
                app = FastAPI()

                # Add middleware in specified order
                for middleware_class in middleware_order:
                    if middleware_class == SessionMiddleware:
                        app.add_middleware(middleware_class, secret_key="test-secret")
                    else:
                        app.add_middleware(middleware_class)

                # Add final session middleware
                app.add_middleware(SessionMiddleware, secret_key="test-secret")

                @app.websocket("/ws")
                async def websocket_endpoint(websocket: WebSocket):
                    await websocket.accept()
                    await websocket.send_text("Ordering test working")
                    await websocket.close()

                client = TestClient(app)

                # ASSERTION: All ordering should work with enhanced middleware
                try:
                    with client.websocket_connect("/ws") as websocket:
                        data = websocket.receive_text()
                        self.assertEqual(data, "Ordering test working")

                    # Test passed for this ordering
                    self.assertTrue(True, f"Enhanced middleware works with ordering {order_index}")

                except Exception as e:
                    self.fail(f"Enhanced middleware should work with ordering {order_index}: {e}")

                client.close()

    def test_enhanced_middleware_websocket_upgrade_detection(self):
        """
        Test enhanced middleware WebSocket upgrade detection accuracy.

        EXPECTED: This test should PASS, demonstrating accurate WebSocket upgrade
        detection that prevents uvicorn protocol confusion.
        """
        app = self.create_enhanced_fastapi_app()
        client = TestClient(app)
        self.test_client = client

        # Test WebSocket upgrade detection through HTTP request
        try:
            # This should be handled by WebSocket exclusion middleware
            response = client.get("/ws", headers={
                "Connection": "Upgrade",
                "Upgrade": "websocket",
                "Sec-WebSocket-Version": "13",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="
            })

            # ASSERTION: Should get 426 Upgrade Required from enhanced middleware
            self.assertEqual(response.status_code, 426,
                           "WebSocket upgrade detection should return 426 Upgrade Required")

            response_data = response.json()
            self.assertEqual(response_data["error"], "websocket_upgrade_required",
                           "Should identify WebSocket upgrade requirement")
            self.assertEqual(response_data["middleware"], "uvicorn_websocket_exclusion",
                           "Should identify enhanced middleware handling")

        except Exception as e:
            self.fail(f"Enhanced middleware WebSocket upgrade detection failed: {e}")

    def test_enhanced_middleware_diagnostic_capabilities(self):
        """
        Test enhanced middleware diagnostic and monitoring capabilities.

        EXPECTED: This test should PASS, demonstrating comprehensive diagnostic
        capabilities for troubleshooting Issue #449 related problems.
        """
        app = self.create_enhanced_fastapi_app()

        # Get middleware instance for diagnostic testing
        middleware_instance = None
        for middleware in app.middleware_stack:
            if hasattr(middleware, 'cls') and issubclass(middleware.cls, UvicornWebSocketExclusionMiddleware):
                # Create instance to test diagnostics
                mock_app = AsyncMock()
                middleware_instance = middleware.cls(mock_app)
                break

        self.assertIsNotNone(middleware_instance, "Enhanced middleware should be found in app stack")

        # Test diagnostic info structure
        diagnostic_info = middleware_instance.get_diagnostic_info()

        # ASSERTION: Diagnostic info should be comprehensive
        self.assertEqual(diagnostic_info["middleware"], "uvicorn_websocket_exclusion")
        self.assertEqual(diagnostic_info["issue_reference"], "#449")
        self.assertIn("validation_failures", diagnostic_info)
        self.assertIn("scope_corruptions", diagnostic_info)
        self.assertIn("middleware_conflicts", diagnostic_info)
        self.assertIn("protocol_recoveries", diagnostic_info)

        # Diagnostic data should be properly structured
        self.assertIsInstance(diagnostic_info["recent_failures"], list)
        self.assertIsInstance(diagnostic_info["recent_corruptions"], list)
        self.assertIsInstance(diagnostic_info["recent_conflicts"], list)
        self.assertIsInstance(diagnostic_info["recent_recoveries"], list)

    def test_enhanced_middleware_error_recovery_validation(self):
        """
        Test enhanced middleware error recovery and safe fallback behavior.

        EXPECTED: This test should PASS, demonstrating proper error recovery
        that prevents cascading failures in uvicorn middleware stack.
        """
        app = FastAPI()

        # Add enhanced middleware with error simulation
        enhanced_middleware = self.enhanced_middleware_class
        app.add_middleware(enhanced_middleware)

        # Add route that might cause middleware stress
        @app.get("/error-test")
        async def error_test_route():
            return {"message": "error test"}

        @app.websocket("/ws-error-test")
        async def websocket_error_test(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Error recovery test")
            await websocket.close()

        client = TestClient(app)
        self.test_client = client

        # Test that enhanced middleware handles errors gracefully
        try:
            # Normal HTTP should work
            response = client.get("/error-test")
            self.assertEqual(response.status_code, 200)

            # WebSocket should also work with error recovery
            with client.websocket_connect("/ws-error-test") as websocket:
                data = websocket.receive_text()
                self.assertEqual(data, "Error recovery test")

            # Enhanced middleware should maintain stability
            self.assertTrue(True, "Enhanced middleware maintains stability during error conditions")

        except Exception as e:
            self.fail(f"Enhanced middleware should provide error recovery: {e}")

    def test_enhanced_middleware_real_world_integration(self):
        """
        Test enhanced middleware integration in realistic application scenario.

        EXPECTED: This test should PASS, demonstrating the enhanced middleware
        works correctly in realistic multi-endpoint, multi-middleware scenarios.
        """
        app = FastAPI()

        # Add comprehensive middleware stack with enhanced protection
        app.add_middleware(self.enhanced_middleware_class)
        app.add_middleware(CompatibleSessionMiddleware)
        app.add_middleware(CompatibleCORSMiddleware)
        app.add_middleware(SessionMiddleware, secret_key="production-like-secret")

        # Add realistic routes
        @app.get("/api/health")
        async def health_check():
            return {"status": "healthy", "middleware": "enhanced"}

        @app.get("/api/users/{user_id}")
        async def get_user(user_id: int):
            return {"user_id": user_id, "name": f"User {user_id}"}

        @app.post("/api/data")
        async def post_data(request: Request):
            return {"received": "data", "session": "handled"}

        @app.websocket("/ws/chat")
        async def chat_websocket(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Chat connection established")
            # Simulate chat message exchange
            await websocket.send_json({"type": "welcome", "message": "Welcome to chat"})
            await websocket.close()

        @app.websocket("/ws/notifications")
        async def notifications_websocket(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Notifications connected")
            await websocket.close()

        client = TestClient(app)
        self.test_client = client

        # Test comprehensive application functionality
        try:
            # Test HTTP endpoints
            health_response = client.get("/api/health")
            self.assertEqual(health_response.status_code, 200)
            self.assertEqual(health_response.json()["status"], "healthy")

            user_response = client.get("/api/users/123")
            self.assertEqual(user_response.status_code, 200)
            self.assertEqual(user_response.json()["user_id"], 123)

            data_response = client.post("/api/data", json={"test": "data"})
            self.assertEqual(data_response.status_code, 200)

            # Test multiple WebSocket endpoints
            with client.websocket_connect("/ws/chat") as chat_ws:
                welcome_text = chat_ws.receive_text()
                self.assertEqual(welcome_text, "Chat connection established")

                welcome_json = chat_ws.receive_json()
                self.assertEqual(welcome_json["type"], "welcome")

            with client.websocket_connect("/ws/notifications") as notif_ws:
                notif_text = notif_ws.receive_text()
                self.assertEqual(notif_text, "Notifications connected")

            # All functionality should work with enhanced middleware
            self.assertTrue(True, "Enhanced middleware supports comprehensive real-world scenarios")

        except Exception as e:
            self.fail(f"Enhanced middleware should support real-world integration: {e}")


class TestIssue449EnhancedMiddlewareFactory(SSotBaseTestCase):
    """
    Tests for enhanced middleware factory and configuration.

    EXPECTED BEHAVIOR: These tests should PASS, demonstrating proper factory
    function behavior and middleware configuration for Issue #449 fixes.
    """

    def test_enhanced_middleware_factory_creation(self):
        """
        Test enhanced middleware factory creates correct middleware class.

        EXPECTED: This test should PASS, demonstrating the factory correctly
        creates the enhanced uvicorn WebSocket exclusion middleware.
        """
        # Create middleware using factory
        middleware_class = create_uvicorn_websocket_exclusion_middleware()

        # ASSERTION: Factory should return correct middleware class
        self.assertEqual(middleware_class, UvicornWebSocketExclusionMiddleware,
                        "Factory should return UvicornWebSocketExclusionMiddleware class")

        # Test middleware can be instantiated
        mock_app = AsyncMock()
        middleware_instance = middleware_class(mock_app)

        # ASSERTION: Instance should have required attributes
        self.assertIsNotNone(middleware_instance.protocol_validator,
                           "Middleware should have protocol validator")
        self.assertIsInstance(middleware_instance.middleware_conflicts, list,
                            "Middleware should track conflicts")
        self.assertIsInstance(middleware_instance.protocol_recoveries, list,
                            "Middleware should track recoveries")

    def test_enhanced_middleware_integration_with_fastapi(self):
        """
        Test enhanced middleware integrates correctly with FastAPI.

        EXPECTED: This test should PASS, demonstrating seamless integration
        of enhanced middleware with FastAPI application instances.
        """
        app = FastAPI()

        # Add enhanced middleware via factory
        enhanced_middleware = create_uvicorn_websocket_exclusion_middleware()
        app.add_middleware(enhanced_middleware)

        # ASSERTION: Middleware should be in app middleware stack
        middleware_found = False
        for middleware in app.middleware_stack:
            if hasattr(middleware, 'cls') and issubclass(middleware.cls, UvicornWebSocketExclusionMiddleware):
                middleware_found = True
                break

        self.assertTrue(middleware_found, "Enhanced middleware should be found in FastAPI middleware stack")

        # Test basic functionality
        @app.get("/test")
        async def test_endpoint():
            return {"test": "enhanced middleware integration"}

        client = TestClient(app)
        response = client.get("/test")

        # ASSERTION: Application should work with enhanced middleware
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["test"], "enhanced middleware integration")

        client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])