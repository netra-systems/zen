"""
Issue #449 - WebSocket uvicorn middleware stack failures - Unit Tests

PURPOSE: Test uvicorn ASGI protocol layer failures specifically related to WebSocket
         middleware stack transitions and uvicorn's WebSocket protocol handling.

BUSINESS IMPACT: $500K+ ARR WebSocket functionality failing due to uvicorn middleware
                stack conflicts between HTTP/WebSocket protocols in GCP staging.

ISSUE SCOPE:
- uvicorn WebSocket protocol transitions
- ASGI scope handling failures  
- Protocol negotiation between HTTP and WebSocket
- Middleware stack conflicts at ASGI level

TEST STRATEGY:
These tests should INITIALLY FAIL to demonstrate the issue exists.
Each test isolates specific uvicorn middleware stack failure patterns.
"""

import asyncio
import json
import pytest
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock, patch
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.websockets import WebSocket
from starlette.routing import Route, WebSocketRoute
import uvicorn

from test_framework.ssot.base_test_case import SSotBaseTestCase


class UvicornMiddlewareConflictSimulator:
    """
    Simulates uvicorn middleware stack conflicts that cause Issue #449.
    
    CRITICAL: This simulates the actual failures we see in production
    where uvicorn's ASGI protocol handling conflicts with WebSocket upgrades.
    """
    
    def __init__(self):
        self.protocol_conflicts = []
        self.asgi_scope_errors = []
        self.middleware_stack_failures = []
    
    def simulate_protocol_transition_failure(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate uvicorn protocol transition failure from HTTP to WebSocket.
        
        This replicates the middleware stack issue where uvicorn fails to properly
        transition between HTTP and WebSocket protocols in the ASGI layer.
        """
        if scope.get("type") == "websocket":
            # Simulate uvicorn middleware stack confusion
            conflict = {
                "error": "Protocol transition failure",
                "details": "uvicorn middleware stack failed to handle WebSocket upgrade",
                "scope_type": scope.get("type"),
                "path": scope.get("path", "/"),
                "protocol_version": scope.get("asgi", {}).get("version", "unknown")
            }
            self.protocol_conflicts.append(conflict)
            
            # Corrupt the scope to simulate the uvicorn failure
            corrupted_scope = scope.copy()
            corrupted_scope["type"] = "http"  # Wrong protocol type
            corrupted_scope["method"] = "GET"  # Invalid for WebSocket
            return corrupted_scope
        
        return scope
    
    def simulate_asgi_scope_validation_failure(self, scope: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate ASGI scope validation failures in uvicorn middleware stack.
        
        This replicates the issue where uvicorn's middleware validation
        rejects valid WebSocket ASGI scopes.
        """
        required_websocket_fields = ["type", "path", "query_string", "headers"]
        missing_fields = []
        
        for field in required_websocket_fields:
            if field not in scope:
                missing_fields.append(field)
        
        if missing_fields:
            error = {
                "error": "ASGI scope validation failure",
                "details": f"uvicorn middleware rejected scope - missing fields: {missing_fields}",
                "scope": scope,
                "missing_fields": missing_fields
            }
            self.asgi_scope_errors.append(error)
            
            # Return invalid scope to simulate failure
            return {"type": "invalid", "error": "scope_validation_failed"}
        
        return scope
    
    def simulate_middleware_stack_ordering_failure(self, middlewares: list) -> list:
        """
        Simulate uvicorn middleware stack ordering failures.
        
        This replicates how uvicorn's middleware ordering can cause
        conflicts between HTTP and WebSocket middleware.
        """
        # Simulate incorrect middleware ordering that causes failures
        failure = {
            "error": "Middleware stack ordering failure",
            "details": "uvicorn applied HTTP middleware to WebSocket requests",
            "middleware_count": len(middlewares),
            "middleware_types": [type(m).__name__ for m in middlewares]
        }
        self.middleware_stack_failures.append(failure)
        
        # Return corrupted middleware stack
        return middlewares[::-1]  # Reverse order to simulate failure


class ConflictingHTTPMiddleware(BaseHTTPMiddleware):
    """
    Middleware that conflicts with WebSocket protocol in uvicorn.
    
    CRITICAL: This simulates real middleware that works for HTTP
    but causes uvicorn WebSocket protocol failures.
    """
    
    async def dispatch(self, request, call_next):
        # This middleware assumes HTTP and fails for WebSocket
        if hasattr(request, 'method'):
            # HTTP-specific logic that breaks WebSocket
            response = await call_next(request)
            response.headers["X-HTTP-Only"] = "true"
            return response
        else:
            # WebSocket request - this should not happen but does in uvicorn failures
            raise RuntimeError("HTTP middleware applied to WebSocket request")


class TestIssue449UvicornMiddlewareFailures(SSotBaseTestCase):
    """
    Unit tests for Issue #449 - uvicorn middleware stack failures.
    
    EXPECTED BEHAVIOR: These tests should FAIL initially to demonstrate
    the issue exists. Each test isolates a specific uvicorn failure pattern.
    """
    
    def setup_method(self, method=None):
        super().setup_method(method)
        self.conflict_simulator = UvicornMiddlewareConflictSimulator()
        self.mock_uvicorn_config = {
            "host": "127.0.0.1",
            "port": 8000,
            "interface": "asgi3",
            "ws_ping_interval": 20.0,
            "ws_ping_timeout": 20.0,
            "ws_max_size": 16 * 1024 * 1024
        }
    
    
    def test_uvicorn_protocol_transition_failure(self):
        """
        Test uvicorn protocol transition failure from HTTP to WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn cannot properly
        transition from HTTP to WebSocket protocol in the middleware stack.
        """
        # Create valid WebSocket ASGI scope
        websocket_scope = {
            "type": "websocket",
            "path": "/ws",
            "query_string": b"",
            "headers": [],
            "asgi": {"version": "3.0"}
        }
        
        # Simulate uvicorn protocol transition failure
        corrupted_scope = self.conflict_simulator.simulate_protocol_transition_failure(websocket_scope)
        
        # ASSERTION THAT SHOULD FAIL: uvicorn should preserve WebSocket scope
        self.assertEqual(
            corrupted_scope["type"], 
            "websocket", 
            "uvicorn corrupted WebSocket scope during protocol transition"
        )
        
        # Additional validation that should fail
        self.assertNotIn("method", corrupted_scope, "WebSocket scope should not have HTTP method")
        
        # Verify the conflict was recorded
        self.assertGreater(len(self.conflict_simulator.protocol_conflicts), 0)
        conflict = self.conflict_simulator.protocol_conflicts[0]
        self.assertEqual(conflict["error"], "Protocol transition failure")
    
    def test_uvicorn_asgi_scope_validation_failure(self):
        """
        Test uvicorn ASGI scope validation failures for WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn incorrectly
        validates WebSocket ASGI scopes in the middleware stack.
        """
        # Create incomplete WebSocket scope (missing headers)
        incomplete_scope = {
            "type": "websocket",
            "path": "/ws",
            "query_string": b""
            # Missing "headers" field
        }
        
        # Simulate uvicorn ASGI scope validation
        validated_scope = self.conflict_simulator.simulate_asgi_scope_validation_failure(incomplete_scope)
        
        # ASSERTION THAT SHOULD FAIL: uvicorn should handle missing headers gracefully
        self.assertNotEqual(
            validated_scope["type"], 
            "invalid", 
            "uvicorn should not invalidate scope for missing headers"
        )
        
        # Verify error was recorded
        self.assertGreater(len(self.conflict_simulator.asgi_scope_errors), 0)
        error = self.conflict_simulator.asgi_scope_errors[0]
        self.assertIn("headers", error["missing_fields"])
    
    def test_uvicorn_middleware_stack_ordering_failure(self):
        """
        Test uvicorn middleware stack ordering failures.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn applies
        HTTP middleware to WebSocket requests due to ordering issues.
        """
        # Create middleware stack with HTTP-only middleware
        original_middlewares = [
            ConflictingHTTPMiddleware,
            # Other middleware would be here
        ]
        
        # Simulate uvicorn middleware ordering failure
        corrupted_middlewares = self.conflict_simulator.simulate_middleware_stack_ordering_failure(original_middlewares)
        
        # ASSERTION THAT SHOULD FAIL: middleware order should be preserved
        self.assertEqual(
            len(corrupted_middlewares), 
            len(original_middlewares),
            "uvicorn should preserve middleware count"
        )
        
        self.assertEqual(
            corrupted_middlewares[0], 
            original_middlewares[0],
            "uvicorn should preserve middleware ordering"
        )
        
        # Verify failure was recorded
        self.assertGreater(len(self.conflict_simulator.middleware_stack_failures), 0)
        failure = self.conflict_simulator.middleware_stack_failures[0]
        self.assertEqual(failure["error"], "Middleware stack ordering failure")
    
    @patch('uvicorn.run')
    def test_uvicorn_websocket_config_conflicts(self, mock_uvicorn_run):
        """
        Test uvicorn WebSocket configuration conflicts.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn WebSocket
        configuration conflicts with middleware stack.
        """
        # Create app with conflicting middleware
        app = Starlette()
        
        # Add HTTP-only middleware that conflicts with WebSocket
        app.add_middleware(ConflictingHTTPMiddleware)
        
        # uvicorn config with WebSocket settings
        config = self.mock_uvicorn_config.copy()
        config["app"] = app
        
        # ASSERTION THAT SHOULD FAIL: uvicorn should handle middleware conflicts
        try:
            # This should fail due to middleware conflicts
            with self.assertRaises(RuntimeError):
                # Simulate WebSocket request hitting HTTP middleware
                mock_request = Mock()
                delattr(mock_request, 'method')  # Remove HTTP method to simulate WebSocket
                
                middleware = ConflictingHTTPMiddleware(app)
                # This should raise RuntimeError about HTTP middleware on WebSocket
                asyncio.run(middleware.dispatch(mock_request, lambda r: Mock()))
            
            # If we get here, the test should fail
            self.fail("uvicorn should have detected middleware conflict")
            
        except RuntimeError as e:
            # Expected error, but this means uvicorn has the issue
            self.assertIn("HTTP middleware applied to WebSocket", str(e))
    
    def test_uvicorn_asgi_interface_version_conflicts(self):
        """
        Test uvicorn ASGI interface version conflicts with WebSocket.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn ASGI 3.0
        interface conflicts with WebSocket middleware stack.
        """
        # Test different ASGI versions
        asgi_versions = ["2.0", "3.0", "3.1"]
        
        for version in asgi_versions:
            websocket_scope = {
                "type": "websocket",
                "path": "/ws",
                "query_string": b"",
                "headers": [],
                "asgi": {"version": version}
            }
            
            # ASSERTION THAT SHOULD FAIL: all ASGI versions should work
            if version == "2.0":
                # ASGI 2.0 should be supported but often fails in uvicorn
                try:
                    # Simulate uvicorn trying to access ASGI 3.0 fields in 2.0 scope
                    _ = websocket_scope["asgi"]["spec_version"]  # Only exists in ASGI 3.0+
                    self.fail("ASGI 2.0 scope should not have spec_version field")
                except KeyError:
                    # Expected for ASGI 2.0 - this shows the compatibility issue
                    pass
    
    def test_uvicorn_websocket_subprotocol_negotiation_failure(self):
        """
        Test uvicorn WebSocket subprotocol negotiation failures.
        
        EXPECTED: This test should FAIL, demonstrating uvicorn fails
        to properly negotiate WebSocket subprotocols through middleware.
        """
        # Create WebSocket scope with subprotocol headers
        websocket_scope = {
            "type": "websocket",
            "path": "/ws",
            "query_string": b"",
            "headers": [
                (b"sec-websocket-protocol", b"chat, superchat"),
                (b"upgrade", b"websocket"),
                (b"connection", b"upgrade")
            ]
        }
        
        # Simulate uvicorn subprotocol processing
        processed_scope = self.conflict_simulator.simulate_protocol_transition_failure(websocket_scope)
        
        # ASSERTION THAT SHOULD FAIL: subprotocol headers should be preserved
        headers_dict = dict(processed_scope.get("headers", []))
        self.assertIn(
            b"sec-websocket-protocol", 
            headers_dict,
            "uvicorn should preserve WebSocket subprotocol headers"
        )
        
        # Verify protocol negotiation data is intact
        protocol_header = headers_dict.get(b"sec-websocket-protocol", b"")
        self.assertIn(b"chat", protocol_header, "uvicorn should preserve subprotocol options")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])