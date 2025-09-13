"""
Integration tests for Issue #508 - WebSocket ASGI Middleware Processing

Tests WebSocket ASGI middleware processing without Docker dependency.
These tests are designed to FAIL initially to reproduce middleware errors,
then pass after fixes are implemented.

Focus: middleware_setup.py WebSocket exclusion middleware and ASGI scope handling
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi import FastAPI, WebSocket
from starlette.datastructures import URL, QueryParams
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import Scope, Receive, Send

# Import the actual modules under test
from netra_backend.app.core.middleware_setup import WebSocketExclusionMiddleware
from netra_backend.app.routes.websocket_ssot import extract_query_params


class TestWebSocketASGIMiddleware:
    """Integration tests for WebSocket ASGI middleware processing."""
    
    @pytest.fixture
    def app(self):
        """Create a test FastAPI app with WebSocket exclusion middleware."""
        app = FastAPI()
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            await websocket.send_text("Hello WebSocket")
            await websocket.close()
        
        return app
    
    @pytest.fixture
    def middleware(self, app):
        """Create WebSocket exclusion middleware instance."""
        return WebSocketExclusionMiddleware(app)
    
    @pytest.mark.asyncio
    async def test_websocket_exclusion_middleware_with_malformed_scope(self, middleware):
        """Test WebSocket exclusion middleware with malformed ASGI scope - WILL FAIL."""
        # Create a malformed ASGI scope that triggers the error
        malformed_scope = {
            'type': 'websocket',
            'scheme': 'wss',
            'path': '/ws',
            'query_string': b'token=abc123&user_id=user123',
            'headers': [(b'host', b'staging.netra.ai')],
            # Missing required fields or malformed structure that causes URL object issues
        }
        
        # Mock receive and send
        receive = AsyncMock()
        send = AsyncMock()
        
        # This should FAIL initially due to ASGI scope malformation
        with pytest.raises(Exception):  # Expecting middleware to fail
            await middleware(malformed_scope, receive, send)
    
    @pytest.mark.asyncio
    async def test_websocket_ssot_query_param_extraction_with_url_objects(self):
        """Test websocket_ssot.py query parameter extraction with different URL objects - WILL FAIL."""
        
        # Test Case 1: WebSocket with FastAPI URL object (should work)
        websocket_fastapi = Mock()
        websocket_fastapi.url = Mock()
        websocket_fastapi.url.query_params = QueryParams("token=abc123&user_id=user123")
        
        result = extract_query_params(websocket_fastapi)
        assert isinstance(result, dict), "Failed to extract from FastAPI WebSocket"
        assert result.get('token') == 'abc123', "Token extraction failed"
        
        # Test Case 2: WebSocket with raw Starlette URL (should FAIL initially)
        websocket_starlette = Mock()
        websocket_starlette.url = URL("wss://staging.netra.ai/ws?token=abc123&user_id=user123")
        
        # This should FAIL initially because Starlette URL doesn't have query_params
        with pytest.raises(AttributeError, match="'URL' object has no attribute 'query_params'"):
            result = extract_query_params(websocket_starlette)
    
    @pytest.mark.asyncio
    async def test_asgi_scope_passthrough_safety(self, middleware):
        """Test safe ASGI scope passthrough when URL objects are malformed - WILL FAIL."""
        # Create scope that will cause URL object attribute errors
        problematic_scope = {
            'type': 'websocket',
            'scheme': 'wss',
            'path': '/ws',
            'query_string': b'token=special%20chars&param=value',
            'headers': [],
            # Simulate GCP Cloud Run specific scope characteristics
            'server': ('staging.netra.ai', 443),
            'client': ('10.0.0.1', 45678),
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        # Test that middleware handles problematic scopes gracefully
        # This should FAIL initially if middleware doesn't handle URL object issues
        try:
            await middleware(problematic_scope, receive, send)
        except Exception as e:
            # Should catch and handle AttributeError gracefully
            assert "query_params" in str(e), f"Unexpected error type: {e}"
    
    @pytest.mark.asyncio
    async def test_websocket_middleware_ordering_preserves_scope(self):
        """Test that middleware processing order doesn't corrupt ASGI scopes - MAY FAIL."""
        app = FastAPI()
        
        # Add multiple middlewares to test ordering
        app.add_middleware(WebSocketExclusionMiddleware)
        
        @app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            # Test that scope is intact when it reaches the endpoint
            assert hasattr(websocket, 'url'), "WebSocket missing URL after middleware processing"
            await websocket.accept()
            await websocket.close()
        
        # Create proper ASGI scope
        scope = {
            'type': 'websocket',
            'scheme': 'wss',
            'path': '/ws',
            'query_string': b'token=abc123',
            'headers': [(b'host', b'localhost')],
            'server': ('localhost', 8000),
            'client': ('127.0.0.1', 56789),
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        # Test middleware stack doesn't corrupt scope
        try:
            await app(scope, receive, send)
        except Exception as e:
            # If this fails, middleware ordering might be corrupting scopes
            pytest.fail(f"Middleware stack corrupted ASGI scope: {e}")
    
    @pytest.mark.asyncio
    async def test_gcp_cloud_run_asgi_simulation(self):
        """Simulate GCP Cloud Run ASGI environment characteristics - WILL FAIL if GCP-specific."""
        # GCP Cloud Run might create different ASGI scope structures
        gcp_style_scope = {
            'type': 'websocket',
            'scheme': 'wss',
            'path': '/ws',
            'raw_path': b'/ws',
            'query_string': b'token=abc123&user_id=user123',
            'root_path': '',
            'headers': [
                (b'host', b'staging.netra.ai'),
                (b'user-agent', b'websockets/10.4'),
                (b'upgrade', b'websocket'),
                (b'connection', b'Upgrade'),
                (b'sec-websocket-key', b'dGhlIHNhbXBsZSBub25jZQ=='),
                (b'sec-websocket-version', b'13'),
                (b'x-forwarded-for', b'203.0.113.1'),
                (b'x-forwarded-proto', b'https'),
                # GCP-specific headers
                (b'x-cloud-trace-context', b'105445aa7843bc8bf206b120001000/1'),
                (b'x-appengine-request-log-id', b'5f2b6e6c0001f4b6b9d7c8e9'),
            ],
            'server': ('staging.netra.ai', 443),
            'client': ('203.0.113.1', 56789),
            # GCP might add additional scope fields
            'extensions': {},
        }
        
        # Test if WebSocket object creation works with GCP-style scope
        try:
            # Simulate WebSocket object creation from GCP scope
            websocket = Mock()
            
            # Simulate how FastAPI/Starlette might create URL from this scope
            # This might reveal GCP-specific issues
            url_string = f"{gcp_style_scope['scheme']}://{gcp_style_scope['server'][0]}{gcp_style_scope['path']}"
            if gcp_style_scope['query_string']:
                url_string += f"?{gcp_style_scope['query_string'].decode()}"
            
            # This might create a different type of URL object in GCP
            websocket.url = URL(url_string)
            
            # Test query parameter extraction
            result = extract_query_params(websocket)
            
            # This should FAIL initially if GCP creates incompatible URL objects
            assert isinstance(result, dict), "Failed to extract params from GCP-style URL"
            
        except AttributeError as e:
            if "query_params" in str(e):
                pytest.fail(f"GCP-specific ASGI scope creates incompatible URL objects: {e}")
            else:
                raise
    
    @pytest.mark.asyncio
    async def test_websocket_error_recovery_in_middleware(self, middleware):
        """Test WebSocket error recovery when ASGI scope errors occur - WILL FAIL INITIALLY."""
        # Create scope that causes URL object errors
        error_prone_scope = {
            'type': 'websocket',
            'path': '/ws',
            'query_string': b'complex%2Bquery=value%20with%20spaces',
            # Missing required fields
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        # Test that middleware recovers gracefully from URL object errors
        # This should FAIL initially if error recovery is insufficient
        
        # Mock the underlying app to simulate processing after error recovery
        middleware.app = AsyncMock()
        
        try:
            await middleware(error_prone_scope, receive, send)
            # If we get here, error recovery worked
        except Exception as e:
            # Check if it's the specific error we're trying to fix
            if "query_params" in str(e):
                pytest.fail(f"Middleware failed to recover from ASGI scope error: {e}")
            else:
                # Other errors might be expected
                pass
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_asgi_scope_handling(self):
        """Test concurrent WebSocket ASGI scope handling for race conditions - MAY FAIL."""
        async def create_websocket_with_scope(scope_id):
            """Create WebSocket with unique scope for concurrency testing."""
            scope = {
                'type': 'websocket',
                'path': f'/ws/{scope_id}',
                'query_string': f'session_id={scope_id}&token=abc123'.encode(),
                'headers': [(b'host', b'localhost')],
            }
            
            websocket = Mock()
            # This might create URL objects that interfere with each other
            url_string = f"ws://localhost/ws/{scope_id}?session_id={scope_id}&token=abc123"
            websocket.url = URL(url_string)
            
            # Test query parameter extraction under concurrent conditions
            result = extract_query_params(websocket)
            assert result.get('session_id') == str(scope_id), f"Scope {scope_id} extraction failed"
            return result
        
        # Create multiple concurrent WebSocket scope processing
        tasks = [create_websocket_with_scope(i) for i in range(10)]
        
        # This might reveal race conditions in URL object handling
        try:
            results = await asyncio.gather(*tasks)
            assert len(results) == 10, "Concurrent scope processing failed"
        except AttributeError as e:
            if "query_params" in str(e):
                pytest.fail(f"Concurrent ASGI scope processing revealed race condition: {e}")
            else:
                raise


class TestASGIScopeErrorScenarios:
    """Specific error scenario reproduction tests."""
    
    @pytest.mark.asyncio
    async def test_reproduce_exact_middleware_setup_error(self):
        """Reproduce the exact error from middleware_setup.py:576 - WILL FAIL."""
        # Create the exact scenario that causes the logged error
        
        app = FastAPI()
        middleware = WebSocketExclusionMiddleware(app)
        
        # Scope that triggers the AttributeError
        problematic_scope = {
            'type': 'websocket',
            'scheme': 'wss',
            'path': '/ws',
            'query_string': b'token=abc123',
            'headers': [(b'host', b'staging.netra.ai')],
        }
        
        receive = AsyncMock()
        send = AsyncMock()
        
        # This should reproduce the exact error context
        with pytest.raises(Exception, match="ASGI scope error"):
            await middleware(problematic_scope, receive, send)
    
    @pytest.mark.asyncio
    async def test_websocket_url_attribute_access_patterns(self):
        """Test various WebSocket URL attribute access patterns that fail."""
        # Pattern 1: Direct query_params access (fails with raw URL)
        websocket1 = Mock()
        websocket1.url = URL("wss://staging.netra.ai/ws?token=abc123")
        
        with pytest.raises(AttributeError):
            params = websocket1.url.query_params
        
        # Pattern 2: Hasattr check that passes but access fails
        websocket2 = Mock()
        websocket2.url = URL("wss://staging.netra.ai/ws?token=abc123")
        
        # hasattr might return True even if access fails
        if hasattr(websocket2.url, 'query_params'):
            with pytest.raises(AttributeError):
                params = websocket2.url.query_params
        
        # Pattern 3: Safe access pattern (should work)
        websocket3 = Mock()
        websocket3.url = URL("wss://staging.netra.ai/ws?token=abc123")
        
        # Safe pattern with proper fallback
        try:
            params = getattr(websocket3.url, 'query_params', None)
            if params is None:
                # Fallback to query string parsing
                from urllib.parse import parse_qs
                raw_query = getattr(websocket3.url, 'query', '')
                params = parse_qs(raw_query)
                params = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
        except AttributeError:
            params = {}
        
        assert isinstance(params, dict), "Safe access pattern failed"


if __name__ == "__main__":
    # Run tests to validate middleware behavior
    pytest.main([__file__, "-v", "--tb=short"])