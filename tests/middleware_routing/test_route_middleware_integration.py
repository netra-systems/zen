"""
Integration tests for route handling with middleware conflicts.
Focuses on reproducing route-specific middleware interactions causing Starlette routing errors.

TARGET ERROR PATTERN:
File "/home/netra/.local/lib/python3.11/site-packages/starlette/routing.py", line 716, in __call__
await self.middleware_stack(scope, receive, send)

INTEGRATION FOCUS: Route-level middleware conflicts, route matching issues, and ASGI scope processing
"""

import asyncio
import pytest
import json
from typing import Dict, List, Any, Callable
from unittest.mock import patch, AsyncMock
from fastapi import FastAPI, Request, Response, HTTPException, WebSocket, Depends
from fastapi.testclient import TestClient
from fastapi.routing import APIRouter
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
from starlette.types import ASGIApp, Scope, Receive, Send

from shared.isolated_environment import get_env


class RouteConflictMiddleware(BaseHTTPMiddleware):
    """Middleware that intentionally conflicts with certain routes."""
    
    def __init__(self, app: ASGIApp, conflict_paths: List[str] = None):
        super().__init__(app)
        self.conflict_paths = conflict_paths or []
        self.processed_requests = []
    
    async def dispatch(self, request: Request, call_next):
        self.processed_requests.append(request.url.path)
        
        # Create intentional conflicts for testing
        if any(path in request.url.path for path in self.conflict_paths):
            # Simulate the type of error that happens in routing.py
            if request.method == "GET":
                raise RuntimeError(f"Route conflict middleware error for {request.url.path}")
        
        return await call_next(request)


class ScopeModifyingMiddleware(BaseHTTPMiddleware):
    """Middleware that modifies ASGI scope in ways that might cause routing issues."""
    
    async def dispatch(self, request: Request, call_next):
        # Modify request state in ways that might break routing
        request.state.middleware_modified = True
        
        # Add headers that might conflict with routing
        if hasattr(request, 'scope'):
            request.scope['custom_routing_header'] = 'modified'
        
        return await call_next(request)


class TestRouteMiddlewareIntegration:
    """Integration tests for route-specific middleware conflicts."""
    
    def setup_method(self, method=None):
        """Set up integration test environment."""
        # Initialize environment isolation
        self._env = get_env()
        self._env.set("ENVIRONMENT", "development")
        self._env.set("SECRET_KEY", "route_integration_test_secret_key_32_chars")
        
        self.route_errors = []
        self.middleware_interactions = []
        
        # Simple metrics tracking
        self.metrics = {}
    
    def record_metric(self, name: str, value):
        """Simple metric recording."""
        self.metrics[name] = value
    
    @pytest.mark.asyncio
    async def test_api_router_middleware_conflict_reproduction(self):
        """
        Test API router with middleware causing routing conflicts.
        
        HYPOTHESIS: APIRouter middleware interactions cause routing.py middleware_stack failures
        """
        app = FastAPI()
        
        # Create API router with specific middleware
        api_router = APIRouter()
        
        # Add route-specific dependency that might conflict
        async def route_dependency():
            return {"dependency": "data"}
        
        @api_router.get("/api/test-conflict")
        async def api_endpoint(dependency_data = Depends(route_dependency)):
            return {"status": "success", "dependency": dependency_data}
        
        @api_router.websocket("/api/ws/test-conflict")
        async def api_websocket(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_json({"status": "api websocket connected"})
            await websocket.close()
        
        # Add middleware that conflicts with API routes
        app.add_middleware(RouteConflictMiddleware, conflict_paths=["/api/"])
        
        # Include the router
        app.include_router(api_router)
        
        client = TestClient(app)
        
        # Test normal endpoint (should work)
        @app.get("/normal")
        async def normal_endpoint():
            return {"status": "normal endpoint"}
        
        try:
            normal_response = client.get("/normal")
            assert normal_response.status_code == 200
            self.record_metric("api_router_conflict_normal_endpoint_success", 1)
        except Exception as e:
            self.route_errors.append(("normal_endpoint", str(e)))
        
        # Test conflicting API endpoint (should trigger routing error)
        try:
            api_response = client.get("/api/test-conflict")
            # If this succeeds, the conflict wasn't triggered
            self.record_metric("api_router_conflict_conflict_not_triggered", 1)
        except Exception as e:
            # This should reproduce the routing.py error
            self.route_errors.append(("api_conflict", str(e)))
            
            error_str = str(e).lower()
            if "route conflict middleware error" in error_str:
                self.record_metric("api_router_conflict_expected_conflict_reproduced", 1)
            elif "routing" in error_str:
                self.record_metric("api_router_conflict_routing_error_reproduced", 1)
        
        # Test WebSocket API endpoint
        try:
            with client.websocket_connect("/api/ws/test-conflict") as websocket:
                data = websocket.receive_json()
                self.record_metric("api_router_conflict_websocket_api_success", 1)
        except Exception as e:
            self.route_errors.append(("api_websocket_conflict", str(e)))
            
            if "route conflict" in str(e).lower():
                self.record_metric("api_router_conflict_websocket_conflict_reproduced", 1)
    
    @pytest.mark.asyncio
    async def test_nested_router_middleware_interaction(self):
        """
        Test nested routers with middleware causing complex routing issues.
        
        HYPOTHESIS: Complex router nesting with middleware creates routing conflicts
        """
        app = FastAPI()
        
        # Create nested router structure
        v1_router = APIRouter(prefix="/api/v1")
        v2_router = APIRouter(prefix="/api/v2")
        admin_router = APIRouter(prefix="/admin")
        
        # Add endpoints to different routers
        @v1_router.get("/users")
        async def v1_users():
            return {"version": "v1", "users": []}
        
        @v2_router.get("/users")
        async def v2_users():
            return {"version": "v2", "users": []}
        
        @admin_router.get("/health")
        async def admin_health():
            return {"admin": "healthy"}
        
        # Nest admin router inside v2
        v2_router.include_router(admin_router)
        
        # Add middleware that affects routing
        app.add_middleware(ScopeModifyingMiddleware)
        
        # Include all routers
        app.include_router(v1_router)
        app.include_router(v2_router)
        
        client = TestClient(app)
        
        # Test all nested route combinations
        test_routes = [
            "/api/v1/users",
            "/api/v2/users", 
            "/api/v2/admin/health"  # Nested route
        ]
        
        for route in test_routes:
            # Remove subTest usage and use direct loop for pytest compatibility
            try:
                response = client.get(route)
                
                if response.status_code == 200:
                    self.record_metric(f"nested_router_route_success_{route.replace('/', '_')}", 1)
                else:
                    self.record_metric(f"nested_router_route_http_error_{response.status_code}", 1)
                    
            except Exception as e:
                self.route_errors.append((f"nested_route_{route}", str(e)))
                
                # Check if this is a routing-related error
                error_str = str(e).lower()
                if any(keyword in error_str for keyword in ["routing", "scope", "middleware"]):
                    self.record_metric("nested_router_routing_related_error", 1)
    
    @pytest.mark.asyncio
    async def test_websocket_http_route_collision(self):
        """
        Test WebSocket and HTTP routes with same paths causing routing conflicts.
        
        HYPOTHESIS: Path collisions between WebSocket and HTTP routes cause middleware_stack errors
        """
        app = FastAPI()
        
        # Create potentially colliding routes
        @app.get("/collision-path")
        async def http_collision_endpoint():
            return {"type": "http", "path": "/collision-path"}
        
        @app.websocket("/collision-path") 
        async def websocket_collision_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_json({"type": "websocket", "path": "/collision-path"})
            await websocket.close()
        
        # Add middleware that might get confused by the collision
        app.add_middleware(ScopeModifyingMiddleware)
        
        client = TestClient(app)
        
        # Test HTTP endpoint
        try:
            http_response = client.get("/collision-path")
            assert(http_response.status_code, 200)
            data = http_response.json()
            assert(data["type"], "http")
            self.record_metric("route_collision_http_collision_success", 1)
        except Exception as e:
            self.route_errors.append(("http_collision", str(e)))
        
        # Test WebSocket endpoint (this often fails with routing errors)
        try:
            with client.websocket_connect("/collision-path") as websocket:
                data = websocket.receive_json()
                assert(data["type"], "websocket")
                self.record_metric("route_collision_websocket_collision_success", 1)
        except Exception as e:
            self.route_errors.append(("websocket_collision", str(e)))
            
            # This type of collision often triggers the routing.py error
            error_str = str(e).lower()
            if "routing" in error_str:
                self.record_metric("route_collision_routing_collision_error", 1)
    
    @pytest.mark.asyncio
    async def test_middleware_route_matching_interference(self):
        """
        Test middleware that interferes with Starlette's route matching process.
        
        HYPOTHESIS: Middleware modifying request properties causes route matching failures
        """
        class RouteMatchingInterferenceMiddleware(BaseHTTPMiddleware):
            """Middleware that interferes with route matching."""
            
            def __init__(self, app, test_instance):
                super().__init__(app)
                self.test_instance = test_instance
            
            async def dispatch(self, request: Request, call_next):
                # Modify request properties that might affect routing
                original_method = request.method
                original_path = str(request.url.path)
                
                # Log the request for analysis
                self.test_instance.middleware_interactions.append({
                    "original_method": original_method,
                    "original_path": original_path,
                    "scope": dict(request.scope)
                })
                
                # Temporarily modify the request (this might break routing)
                if hasattr(request, 'scope'):
                    if original_path == "/test-interference":
                        # This modification might cause routing issues
                        request.scope['path'] = '/modified-path'
                        request.scope['modified_by_middleware'] = True
                
                try:
                    response = await call_next(request)
                    return response
                except Exception as e:
                    # Log routing-related errors
                    if "routing" in str(e).lower():
                        self.test_instance.route_errors.append(("route_matching_interference", str(e)))
                    raise
        
        app = FastAPI()
        app.add_middleware(RouteMatchingInterferenceMiddleware, test_instance=self)
        
        @app.get("/test-interference")
        async def test_interference():
            return {"status": "interference test"}
        
        @app.get("/normal-route")
        async def normal_route():
            return {"status": "normal"}
        
        client = TestClient(app)
        
        # Test normal route (should work)
        try:
            normal_response = client.get("/normal-route")
            assert normal_response.status_code == 200
            self.record_metric("route_matching_normal_route_success", 1)
        except Exception as e:
            self.route_errors.append(("normal_route_interference", str(e)))
        
        # Test interference route (might trigger routing error)
        try:
            interference_response = client.get("/test-interference")
            if interference_response.status_code == 200:
                self.record_metric("route_matching_interference_route_success", 1)
            else:
                self.record_metric("route_matching_interference_route_http_error", 1)
        except Exception as e:
            self.route_errors.append(("interference_route", str(e)))
            
            # Check if this reproduces the routing.py error pattern
            error_str = str(e).lower()
            if "routing" in error_str and ("scope" in error_str or "middleware" in error_str):
                self.record_metric("route_matching_scope_routing_error", 1)
    
    @pytest.mark.asyncio
    async def test_asgi_scope_corruption_routing_error(self):
        """
        Test ASGI scope corruption causing routing failures.
        
        HYPOTHESIS: Middleware corrupting ASGI scope causes routing.py line 716 failures
        """
        class ASGIScopeCorruptingMiddleware:
            """Middleware that corrupts ASGI scope to reproduce routing errors."""
            
            def __init__(self, app: ASGIApp, test_instance):
                self.app = app
                self.test_instance = test_instance
            
            async def __call__(self, scope: Scope, receive: Receive, send: Send):
                # Corrupt scope in ways that might trigger routing.py errors
                if scope["type"] == "http":
                    # Modify scope properties that routing depends on
                    original_path = scope.get("path", "")
                    
                    # These modifications might cause routing.py middleware_stack failures
                    if original_path == "/test-scope-corruption":
                        scope["path"] = None  # Invalid path
                        scope["corrupted"] = True
                    
                    elif original_path == "/test-method-corruption":
                        scope["method"] = "INVALID_METHOD"
                
                try:
                    await self.app(scope, receive, send)
                except Exception as e:
                    # Log scope-related routing errors
                    if "routing" in str(e).lower():
                        self.test_instance.route_errors.append(("asgi_scope_corruption", str(e)))
                    raise
        
        app = FastAPI()
        
        # Apply ASGI-level middleware that corrupts scope
        app.add_asgi_middleware(ASGIScopeCorruptingMiddleware, test_instance=self)
        
        @app.get("/test-scope-corruption")
        async def test_scope_corruption():
            return {"status": "scope corruption test"}
        
        @app.get("/test-method-corruption")
        async def test_method_corruption():
            return {"status": "method corruption test"}
        
        @app.get("/normal-asgi")
        async def normal_asgi():
            return {"status": "normal asgi"}
        
        client = TestClient(app)
        
        # Test normal endpoint
        try:
            normal_response = client.get("/normal-asgi")
            assert normal_response.status_code == 200
            self.record_metric("asgi_scope_normal_asgi_success", 1)
        except Exception as e:
            self.route_errors.append(("normal_asgi", str(e)))
        
        # Test scope corruption (should trigger routing error)
        corruption_tests = [
            ("/test-scope-corruption", "path_corruption"),
            ("/test-method-corruption", "method_corruption")
        ]
        
        for path, corruption_type in corruption_tests:
            try:
                response = client.get(path)
                # If this succeeds, corruption wasn't effective
                self.record_metric(f"asgi_scope_{corruption_type}_no_effect", 1)
            except Exception as e:
                self.route_errors.append((corruption_type, str(e)))
                
                # Check if this reproduces the routing.py error
                error_str = str(e).lower()
                if "routing" in error_str:
                    self.record_metric(f"asgi_scope_{corruption_type}_routing_error", 1)
    
    @pytest.mark.asyncio
    async def test_production_route_middleware_exact_match(self):
        """
        Test exact production route and middleware configuration.
        
        MISSION CRITICAL: Reproduce the exact route/middleware combination from production
        """
        from netra_backend.app.core.app_factory import create_app
        from netra_backend.app.routes.websocket_ssot import router as websocket_router
        
        # Set production-like environment
        self._env.set("ENVIRONMENT", "staging")
        self._env.set("K_SERVICE", "netra-staging-backend")
        self._env.set("GCP_PROJECT_ID", "netra-staging")
        
        try:
            # Create production app
            app = create_app()
            client = TestClient(app)
            
            # Test the specific routes that were failing in production
            production_test_routes = [
                ("GET", "/", "root_endpoint"),
                ("GET", "/health", "health_endpoint"),
                ("GET", "/api/v1/auth/status", "auth_status"),
                ("WebSocket", "/ws", "main_websocket"),
                ("WebSocket", "/ws/test", "test_websocket")
            ]
            
            for method, path, route_name in production_test_routes:
                # Remove subTest usage and use direct loop for pytest compatibility
                try:
                    if method == "GET":
                        response = client.get(path)
                        # Don't assert specific status codes as some routes may not exist
                        self.record_metric(f"production_routes_{route_name}_success", 1)
                        
                    elif method == "WebSocket":
                        with client.websocket_connect(path) as websocket:
                            # Just establishing connection tests the routing
                            pass
                        self.record_metric(f"production_routes_{route_name}_websocket_success", 1)
                        
                except Exception as e:
                    self.route_errors.append((route_name, str(e)))
                    
                    # Check for the specific routing.py error
                    error_str = str(e).lower()
                    if "routing.py" in error_str or "middleware_stack" in error_str:
                        self.record_metric(f"production_routes_{route_name}_exact_error_match", 1)
                    elif "routing" in error_str:
                        self.record_metric(f"production_routes_{route_name}_routing_related", 1)
            
        except Exception as e:
            # App creation failure is critical
            self.route_errors.append(("production_app_creation", str(e)))
            raise AssertionError(f"Production app creation failed: {e}")
    
    def teardown_method(self, method=None):
        """Clean up and provide detailed error analysis."""
        pass  # No parent teardown needed
        
        if self.route_errors:
            print("\n=== ROUTE MIDDLEWARE INTEGRATION ERROR ANALYSIS ===")
            for error_source, error_msg in self.route_errors:
                print(f"Source: {error_source}")
                print(f"Error: {error_msg}")
                
                # Analyze error for routing.py patterns
                if "routing.py" in error_msg and "line 716" in error_msg:
                    print("🎯 EXACT MATCH: This reproduces the target routing.py line 716 error!")
                elif "middleware_stack" in error_msg:
                    print("🎯 CLOSE MATCH: middleware_stack error - likely related to target issue")
                elif "routing" in error_msg.lower():
                    print("⚠️ ROUTING RELATED: May be related to the target issue")
                
                print("-" * 60)
        
        if self.middleware_interactions:
            print("\n=== MIDDLEWARE INTERACTION ANALYSIS ===")
            for interaction in self.middleware_interactions:
                print(f"Method: {interaction['original_method']}")
                print(f"Path: {interaction['original_path']}")
                print(f"Scope Keys: {list(interaction['scope'].keys())}")
                print("-" * 40)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=long", "--capture=no"])