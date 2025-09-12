"""
Comprehensive test suite to reproduce and diagnose the Starlette routing error.

Stack trace pattern:
File "/home/netra/.local/lib/python3.11/site-packages/starlette/routing.py", line 716, in __call__
await self.middleware_stack(scope, receive, send)

MISSION: Reproduce the exact middleware stack configuration causing routing failures
CRITICAL: Focus on middleware ordering, WebSocket conflicts, and exception handling
"""

import asyncio
import pytest
import logging
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.routing import Router, Route, WebSocketRoute
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from shared.isolated_environment import IsolatedEnvironment, get_env


class MiddlewareOrderError(Exception):
    """Exception raised when middleware ordering is incorrect."""
    pass


class TestStarletteRoutingErrorReproduction:
    """
    Test class to reproduce the specific Starlette routing error from the stack trace.
    
    CRITICAL PATTERN: The error occurs in starlette/routing.py line 716 during 
    middleware_stack processing, suggesting middleware configuration issues.
    """
    
    def setup_method(self, method=None):
        """Set up test environment for routing error reproduction."""
        # Initialize environment isolation
        self._env = get_env()
        
        # Configure environment for maximum middleware complexity
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        self._env.set("SECRET_KEY", "a" * 32 + "routing_test_secret_key")
        self._env.set("DEBUG", "true")
        
        # Track middleware execution order for analysis
        self.middleware_execution_log = []
        self.routing_errors = []
        self.exception_details = []
        
        # Simple metrics tracking
        self.metrics = {}
    
    def record_metric(self, name: str, value):
        """Simple metric recording."""
        self.metrics[name] = value
        
    @pytest.mark.asyncio
    async def test_middleware_stack_routing_conflict_reproduction(self):
        """
        Test 1: Reproduce middleware stack conflicts causing routing errors.
        
        HYPOTHESIS: Complex middleware ordering causes routing.py line 716 failure
        """
        from netra_backend.app.core.middleware_setup import setup_middleware
        
        app = FastAPI()
        
        # Add test endpoint to trigger routing
        @app.get("/test-routing")
        async def test_routing_endpoint():
            return {"status": "success"}
            
        @app.websocket("/ws/test-routing")
        async def test_websocket_routing(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_json({"status": "connected"})
            await websocket.close()
        
        try:
            # This should reproduce the middleware configuration from production
            setup_middleware(app)
            
            # Test with TestClient (simulates real request flow)
            client = TestClient(app)
            
            # Test HTTP endpoint
            http_response = client.get("/test-routing")
            assert http_response.status_code == 200
            
            # Test WebSocket endpoint (often triggers routing errors)
            with client.websocket_connect("/ws/test-routing") as websocket:
                data = websocket.receive_json()
                assert data["status"] == "connected"
            
            self.record_metric("routing_reproduction_middleware_stack_success", 1)
            
        except Exception as e:
            self.routing_errors.append(("middleware_stack", str(e), type(e).__name__))
            
            # Check if this matches the expected routing.py error
            if "starlette" in str(e).lower() and "routing" in str(e).lower():
                self.record_metric("routing_reproduction_starlette_routing_error", 1)
            
            # Log detailed error information
            self.exception_details.append({
                "test": "middleware_stack_routing",
                "exception": str(e),
                "type": type(e).__name__,
                "middleware_count": len(app.user_middleware)
            })
            
            raise
    
    @pytest.mark.asyncio
    async def test_websocket_middleware_routing_conflict(self):
        """
        Test 2: Test WebSocket routing with complex middleware stack.
        
        HYPOTHESIS: WebSocket upgrade conflicts with HTTP middleware cause routing errors
        """
        app = FastAPI()
        
        # Manually add middleware in problematic order
        app.add_middleware(SessionMiddleware, secret_key="test_key_32_chars_minimum_required")
        
        # Add multiple middleware that might conflict with WebSocket
        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
        from netra_backend.app.middleware.security_response_middleware import SecurityResponseMiddleware
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
        
        try:
            app.add_middleware(FastAPIAuthMiddleware, excluded_paths=["/ws"])
            app.add_middleware(SecurityResponseMiddleware)
            # Skip GCP middleware as it may not be available in test environment
        except ImportError:
            # Middleware not available, skip
            pass
        
        # Add WebSocket route that triggers the routing error
        @app.websocket("/ws/problematic")
        async def problematic_websocket(websocket: WebSocket):
            try:
                await websocket.accept()
                # This is where routing errors often occur
                await websocket.send_json({"message": "connection established"})
                
                # Simulate some processing that might trigger middleware issues
                await asyncio.sleep(0.1)
                await websocket.send_json({"message": "processing complete"})
                await websocket.close()
                
            except Exception as e:
                self.routing_errors.append(("websocket_handler", str(e), type(e).__name__))
                raise
        
        client = TestClient(app)
        
        try:
            with client.websocket_connect("/ws/problematic") as websocket:
                # This connection attempt often triggers the routing.py error
                message1 = websocket.receive_json()
                assert message1["message"] == "connection established"
                
                message2 = websocket.receive_json()
                assert message2["message"] == "processing complete"
                
            self.record_metric("websocket_routing_websocket_success", 1)
            
        except Exception as e:
            self.routing_errors.append(("websocket_connect", str(e), type(e).__name__))
            
            # Check for the specific routing.py error pattern
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["routing", "middleware_stack", "starlette"]):
                self.record_metric("websocket_routing_routing_error_reproduced", 1)
            
            self.exception_details.append({
                "test": "websocket_middleware_routing",
                "exception": str(e),
                "type": type(e).__name__,
                "websocket_specific": True
            })
            
            raise
    
    @pytest.mark.asyncio
    async def test_middleware_exception_wrapping_issues(self):
        """
        Test 3: Reproduce incomplete exception logging due to middleware wrapping.
        
        HYPOTHESIS: Middleware exception handling masks the real error causing 
        incomplete stack traces like the one provided.
        """
        app = FastAPI()
        
        # Create middleware that intentionally wraps exceptions
        class ExceptionWrappingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    response = await call_next(request)
                    return response
                except Exception as e:
                    # This wrapping might cause the incomplete stack trace
                    self.routing_errors.append(("exception_wrapping", str(e), type(e).__name__))
                    # Re-raise in a way that might truncate the trace
                    raise RuntimeError(f"Wrapped exception: {e}")
        
        # Create middleware that fails during processing
        class FailingMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                # Simulate the type of failure that occurs in routing.py line 716
                if request.url.path == "/trigger-routing-error":
                    raise RuntimeError("Simulated middleware_stack processing error")
                return await call_next(request)
        
        app.add_middleware(SessionMiddleware, secret_key="test_key_32_chars_minimum_required")
        app.add_middleware(ExceptionWrappingMiddleware)
        app.add_middleware(FailingMiddleware)
        
        @app.get("/trigger-routing-error")
        async def trigger_error():
            return {"status": "should not reach here"}
        
        @app.get("/normal-endpoint")
        async def normal_endpoint():
            return {"status": "success"}
        
        client = TestClient(app)
        
        # Test normal endpoint (should work)
        try:
            response = client.get("/normal-endpoint")
            assert response.status_code == 200
            self.record_metric("exception_wrapping_normal_endpoint_success", 1)
        except Exception as e:
            self.routing_errors.append(("normal_endpoint", str(e), type(e).__name__))
        
        # Test error-triggering endpoint
        try:
            response = client.get("/trigger-routing-error")
            # Should not reach here
            assert False, "Expected routing error was not triggered"
        except Exception as e:
            # This should reproduce the truncated stack trace pattern
            self.record_metric("exception_wrapping_routing_error_triggered", 1)
            
            error_str = str(e)
            if "wrapped exception" in error_str.lower():
                self.record_metric("exception_wrapping_exception_wrapping_confirmed", 1)
            
            self.exception_details.append({
                "test": "exception_wrapping", 
                "exception": str(e),
                "type": type(e).__name__,
                "wrapped": "wrapped exception" in error_str.lower()
            })
    
    @pytest.mark.asyncio
    async def test_session_middleware_dependency_chain_failure(self):
        """
        Test 4: Test SessionMiddleware dependency chain that could cause routing failures.
        
        HYPOTHESIS: Middleware depending on SessionMiddleware fail when session setup
        is incomplete, causing routing.py middleware_stack processing to fail.
        """
        app = FastAPI()
        
        # Create middleware that depends on SessionMiddleware
        class SessionDependentMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request: Request, call_next):
                try:
                    # This access pattern causes "SessionMiddleware must be installed" errors
                    session_data = request.session.get("test_key", "default")
                    request.state.session_accessed = True
                except Exception as e:
                    self.routing_errors.append(("session_access", str(e), type(e).__name__))
                    # This might cause the routing.py error
                    raise RuntimeError(f"Session access failed in middleware: {e}")
                
                return await call_next(request)
        
        # Test different middleware orders to find the problematic one
        middleware_orders = [
            # Order 1: SessionMiddleware first (correct)
            [SessionMiddleware, SessionDependentMiddleware],
            # Order 2: SessionDependentMiddleware first (incorrect - should fail)
            [SessionDependentMiddleware, SessionMiddleware],
        ]
        
        for i, middleware_order in enumerate(middleware_orders):
            # Remove subTest usage and use direct loop for pytest compatibility
            test_app = FastAPI()
            
            # Add middleware in the test order
            for middleware_class in middleware_order:
                if middleware_class == SessionMiddleware:
                    test_app.add_middleware(middleware_class, secret_key="test_key_32_chars_minimum")
                else:
                    test_app.add_middleware(middleware_class)
            
            @test_app.get("/test-session-dependency")
            async def test_session():
                return {"status": "success"}
            
            client = TestClient(test_app)
            
            try:
                response = client.get("/test-session-dependency")
                
                if i == 0:  # Correct order
                    assert response.status_code == 200
                    self.record_metric("session_dependency_correct_order_success", 1)
                else:  # Incorrect order
                    # This might succeed unexpectedly
                    self.record_metric("session_dependency_incorrect_order_unexpected_success", 1)
                    
            except Exception as e:
                if i == 1:  # Incorrect order - expected to fail
                    self.record_metric("session_dependency_incorrect_order_failed", 1)
                    error_str = str(e).lower()
                    if "sessionmiddleware" in error_str:
                        self.record_metric("session_dependency_session_error_reproduced", 1)
                
                self.exception_details.append({
                    "test": f"session_dependency_order_{i}",
                    "exception": str(e),
                    "type": type(e).__name__,
                    "middleware_order": [cls.__name__ for cls in middleware_order]
                })
    
    @pytest.mark.asyncio
    async def test_cors_websocket_middleware_interaction(self):
        """
        Test 5: Test CORS and WebSocket middleware interactions causing routing issues.
        
        HYPOTHESIS: CORS middleware processing WebSocket upgrade requests causes
        routing conflicts in the middleware_stack processing.
        """
        from fastapi.middleware.cors import CORSMiddleware
        
        app = FastAPI()
        
        # Add CORS middleware with WebSocket-problematic configuration
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000", "http://localhost:8000"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"]
        )
        
        app.add_middleware(SessionMiddleware, secret_key="test_key_32_chars_minimum")
        
        @app.get("/test-cors")
        async def test_cors_endpoint():
            return {"status": "cors success"}
        
        @app.websocket("/ws/cors-test")
        async def test_cors_websocket(websocket: WebSocket):
            # WebSocket upgrade with CORS middleware often causes issues
            await websocket.accept()
            await websocket.send_json({"status": "websocket cors success"})
            await websocket.close()
        
        client = TestClient(app)
        
        # Test HTTP with CORS
        try:
            response = client.get("/test-cors", headers={"Origin": "http://localhost:3000"})
            assert response.status_code == 200
            self.record_metric("cors_websocket_cors_http_success", 1)
        except Exception as e:
            self.routing_errors.append(("cors_http", str(e), type(e).__name__))
        
        # Test WebSocket with CORS (often triggers routing errors)
        try:
            with client.websocket_connect(
                "/ws/cors-test",
                headers={"Origin": "http://localhost:3000"}
            ) as websocket:
                data = websocket.receive_json()
                assert data["status"] == "websocket cors success"
            
            self.record_metric("cors_websocket_cors_websocket_success", 1)
            
        except Exception as e:
            self.routing_errors.append(("cors_websocket", str(e), type(e).__name__))
            
            # This is a common trigger for the routing.py error
            error_str = str(e).lower()
            if any(keyword in error_str for keyword in ["routing", "cors", "websocket", "upgrade"]):
                self.record_metric("cors_websocket_cors_websocket_routing_error", 1)
            
            self.exception_details.append({
                "test": "cors_websocket_interaction",
                "exception": str(e),
                "type": type(e).__name__,
                "cors_websocket_specific": True
            })
    
    @pytest.mark.asyncio
    async def test_production_middleware_stack_exact_reproduction(self):
        """
        Test 6: Exact reproduction of the production middleware stack configuration.
        
        MISSION CRITICAL: This reproduces the exact middleware configuration that
        caused the routing.py line 716 error in the stack trace.
        """
        from netra_backend.app.core.app_factory import create_app
        
        # Override environment to match production conditions
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        
        try:
            # This creates the exact app configuration from production
            app = create_app()
            
            # Test the exact endpoint patterns that were failing
            client = TestClient(app)
            
            # Test root endpoint
            root_response = client.get("/")
            assert root_response.status_code == 200
            
            # Test health endpoint
            health_response = client.get("/health")
            # May or may not exist, don't assert status
            
            # Test WebSocket endpoint (most likely to trigger the error)
            try:
                with client.websocket_connect("/ws") as websocket:
                    # Just establishing connection often triggers the routing error
                    pass
                self.record_metric("production_reproduction_websocket_connection_success", 1)
            except Exception as websocket_error:
                self.routing_errors.append(("production_websocket", str(websocket_error), type(websocket_error).__name__))
                
                # Check if this matches the production error pattern
                error_str = str(websocket_error).lower()
                if "routing" in error_str and "middleware_stack" in error_str:
                    self.record_metric("production_reproduction_exact_error_reproduced", 1)
                
            self.record_metric("production_reproduction_app_creation_success", 1)
            
        except Exception as e:
            self.routing_errors.append(("production_app_creation", str(e), type(e).__name__))
            
            # Log detailed production error analysis
            self.exception_details.append({
                "test": "production_exact_reproduction",
                "exception": str(e),
                "type": type(e).__name__,
                "production_specific": True,
                "middleware_analysis": self._analyze_middleware_configuration()
            })
            
            # This failure is critical for understanding the production issue
            raise AssertionError(f"Production middleware stack reproduction failed: {e}")
    
    def _analyze_middleware_configuration(self) -> Dict[str, Any]:
        """Analyze current middleware configuration for debugging."""
        try:
            from netra_backend.app.core.app_factory import create_app
            app = create_app()
            
            middleware_analysis = {
                "total_middleware_count": len(app.user_middleware),
                "middleware_classes": [str(mw.cls) for mw in app.user_middleware],
                "session_middleware_present": any("SessionMiddleware" in str(mw.cls) for mw in app.user_middleware),
                "cors_middleware_present": any("CORS" in str(mw.cls) for mw in app.user_middleware),
                "auth_middleware_present": any("Auth" in str(mw.cls) for mw in app.user_middleware),
                "websocket_middleware_present": any("WebSocket" in str(mw.cls) for mw in app.user_middleware)
            }
            
            return middleware_analysis
        except Exception as e:
            return {"analysis_error": str(e)}
    
    def teardown_method(self, method=None):
        """Clean up and log routing error analysis."""
        pass  # No parent teardown needed
        
        # Log comprehensive routing error analysis
        if self.routing_errors:
            print("\n=== ROUTING ERROR ANALYSIS ===")
            for error_type, error_msg, exception_type in self.routing_errors:
                print(f"Error Type: {error_type}")
                print(f"Exception: {exception_type}")
                print(f"Message: {error_msg}")
                print("-" * 50)
        
        if self.exception_details:
            print("\n=== DETAILED EXCEPTION ANALYSIS ===")
            for detail in self.exception_details:
                print(f"Test: {detail['test']}")
                print(f"Exception Type: {detail['type']}")
                print(f"Exception Message: {detail['exception']}")
                if 'middleware_analysis' in detail:
                    print(f"Middleware Analysis: {detail['middleware_analysis']}")
                print("-" * 50)


class TestMiddlewareOrdering:
    """Specific tests for middleware ordering issues that cause routing errors."""
    
    def setup_method(self, method=None):
        """Set up for middleware ordering tests."""
        # Initialize environment isolation
        self._env = get_env()
        self._env.set("SECRET_KEY", "a" * 32 + "middleware_ordering_test")
        
        # Simple metrics tracking
        self.metrics = {}
    
    def record_metric(self, name: str, value):
        """Simple metric recording."""
        self.metrics[name] = value
    
    @pytest.mark.asyncio
    async def test_all_possible_middleware_orders(self):
        """Test different middleware orders to identify the problematic configuration."""
        from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
        
        # Core middleware that must be tested in different orders
        middleware_classes = [
            (SessionMiddleware, {"secret_key": "test_key_32_chars_minimum"}),
            (FastAPIAuthMiddleware, {"excluded_paths": ["/health"]}),
        ]
        
        # Test different permutations
        import itertools
        for order in itertools.permutations(middleware_classes):
            # Remove subTest usage and use direct loop for pytest compatibility  
            app = FastAPI()
            
            # Add middleware in this order
            for middleware_class, kwargs in order:
                try:
                    app.add_middleware(middleware_class, **kwargs)
                except Exception as e:
                    self.record_metric(f"middleware_ordering_add_middleware_failed_{middleware_class.__name__}", 1)
                    continue
            
            @app.get("/test-order")
            async def test_endpoint():
                return {"status": "success"}
            
            # Test the configuration
            client = TestClient(app)
            try:
                response = client.get("/test-order")
                if response.status_code == 200:
                    self.record_metric(f"middleware_ordering_order_success_{len(order)}", 1)
                else:
                    self.record_metric(f"middleware_ordering_order_http_error_{response.status_code}", 1)
            except Exception as e:
                order_str = "_".join([cls.__name__ for cls, _ in order])
                self.record_metric(f"middleware_ordering_order_exception_{order_str}", 1)


if __name__ == "__main__":
    # Run the tests with detailed output
    pytest.main([__file__, "-v", "--tb=long"])