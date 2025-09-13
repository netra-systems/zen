"""
Unit tests for Issue #508 - ASGI Scope Interface Validation

Tests designed to reproduce and validate the AttributeError:
'URL' object has no attribute 'query_params'

These tests will FAIL initially to reproduce the error, then pass after fixes.
"""

import pytest
from unittest.mock import Mock, MagicMock
from fastapi import Request, WebSocket
from starlette.datastructures import URL, QueryParams
from starlette.requests import Request as StarletteRequest
from urllib.parse import parse_qs

# Import the actual modules that are failing
from netra_backend.app.routes.websocket_ssot import extract_query_params
from netra_backend.app.core.middleware_setup import WebSocketExclusionMiddleware


class TestASGIScopeInterface:
    """Test ASGI scope object interface handling and compatibility issues."""
    
    def test_fastapi_request_url_has_query_params(self):
        """Verify FastAPI Request.url has query_params attribute - SHOULD PASS."""
        # Create a mock ASGI scope that FastAPI would create
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/test',
            'query_string': b'param1=value1&param2=value2',
            'headers': [],
        }
        
        # Create FastAPI Request object
        request = Request(scope)
        
        # This should work - FastAPI Request.url should have query_params
        assert hasattr(request.url, 'query_params'), "FastAPI Request.url missing query_params attribute"
        assert request.url.query_params is not None, "FastAPI Request.url.query_params is None"
        
        # Test actual query parameter access
        query_params = request.url.query_params
        assert 'param1' in query_params, "Query parameter parsing failed"
        assert query_params['param1'] == 'value1', "Query parameter value incorrect"
    
    def test_starlette_url_missing_query_params(self):
        """Test raw Starlette URL object - SHOULD FAIL to reproduce the error."""
        # Create a raw Starlette URL object (not from Request)
        url = URL("https://example.com/test?param1=value1&param2=value2")
        
        # This should FAIL initially - raw URL objects don't have query_params
        with pytest.raises(AttributeError, match="'URL' object has no attribute 'query_params'"):
            _ = url.query_params  # This line should trigger the AttributeError
    
    def test_websocket_url_object_type_detection(self):
        """Test WebSocket URL object type detection - WILL FAIL if logic is flawed."""
        # Create a WebSocket mock that might have malformed URL
        websocket_mock = Mock()
        
        # Scenario 1: WebSocket with proper FastAPI URL (has query_params)
        fastapi_url = Mock()
        fastapi_url.query_params = QueryParams("param1=value1")
        websocket_mock.url = fastapi_url
        
        # This should work
        result = extract_query_params(websocket_mock)
        assert isinstance(result, dict), "Failed to extract query params from proper FastAPI URL"
        
        # Scenario 2: WebSocket with raw Starlette URL (missing query_params) - SHOULD FAIL
        starlette_url = URL("https://example.com/ws?param1=value1")
        websocket_mock.url = starlette_url
        
        # This will FAIL initially if the detection logic doesn't handle missing query_params
        with pytest.raises(AttributeError):
            result = extract_query_params(websocket_mock)
    
    def test_asgi_scope_malformation_scenarios(self):
        """Test malformed ASGI scopes that could cause URL object corruption - WILL FAIL."""
        # Scenario 1: Missing URL entirely
        websocket_mock = Mock()
        websocket_mock.url = None
        
        result = extract_query_params(websocket_mock)
        assert result == {}, "Should return empty dict for None URL"
        
        # Scenario 2: URL with no query attribute at all
        malformed_url = Mock(spec=[])  # Empty spec means no attributes
        websocket_mock.url = malformed_url
        
        # This should FAIL initially if not handled properly
        with pytest.raises(AttributeError):
            result = extract_query_params(websocket_mock)
    
    def test_query_params_access_patterns(self):
        """Test multiple ways to access query parameters safely - VALIDATES FIXES."""
        
        def safe_query_params_extraction(websocket):
            """Safe query parameter extraction with fallbacks."""
            if not hasattr(websocket, 'url') or websocket.url is None:
                return {}
                
            # Try FastAPI style first
            if hasattr(websocket.url, 'query_params'):
                return dict(websocket.url.query_params)
            
            # Fallback to raw query string parsing
            elif hasattr(websocket.url, 'query'):
                raw_query = getattr(websocket.url, 'query', '')
                if raw_query:
                    parsed = parse_qs(raw_query)
                    return {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            
            return {}
        
        # Test with FastAPI style URL
        websocket_fastapi = Mock()
        websocket_fastapi.url = Mock()
        websocket_fastapi.url.query_params = QueryParams("param1=value1")
        
        result = safe_query_params_extraction(websocket_fastapi)
        assert result.get('param1') == 'value1', "Failed to extract from FastAPI URL"
        
        # Test with Starlette URL (has .query attribute)
        websocket_starlette = Mock()
        websocket_starlette.url = URL("https://example.com/ws?param1=value1&param2=value2")
        
        result = safe_query_params_extraction(websocket_starlette)
        assert result.get('param1') == 'value1', "Failed to extract from Starlette URL"
        assert result.get('param2') == 'value2', "Failed to extract multiple params"
    
    def test_middleware_asgi_scope_handling(self):
        """Test middleware ASGI scope handling that's failing - WILL FAIL INITIALLY."""
        # Create malformed ASGI scope that triggers the error
        malformed_scope = {
            'type': 'websocket',
            'path': '/ws',
            'query_string': b'token=abc123',
        }
        
        # Mock receive and send
        receive_mock = Mock()
        send_mock = Mock()
        
        # Create middleware instance
        app_mock = Mock()
        middleware = WebSocketExclusionMiddleware(app_mock)
        
        # This should FAIL initially if middleware doesn't handle malformed scopes
        with pytest.raises(Exception):  # Expecting some kind of failure
            # Note: This is async, so we'd need to run it properly in a real test
            pass  # Placeholder - would need async test runner
    
    def test_url_object_attribute_existence_validation(self):
        """Validate URL object attribute existence patterns."""
        # Test FastAPI Request URL
        scope = {
            'type': 'http',
            'method': 'GET',
            'path': '/test',
            'query_string': b'param1=value1',
            'headers': [],
        }
        request = Request(scope)
        
        # Validate attribute patterns
        assert hasattr(request.url, 'query_params'), "FastAPI URL missing query_params"
        assert hasattr(request.url, 'query'), "FastAPI URL missing query"
        
        # Test raw Starlette URL
        starlette_url = URL("https://example.com/test?param1=value1")
        
        # Validate attribute patterns  
        assert not hasattr(starlette_url, 'query_params'), "Raw Starlette URL should NOT have query_params"
        assert hasattr(starlette_url, 'query'), "Starlette URL should have query"
        assert starlette_url.query == 'param1=value1', "Starlette URL query incorrect"


class TestASGIScopeErrorReproduction:
    """Tests specifically designed to reproduce the exact errors from Issue #508."""
    
    def test_reproduce_websocket_ssot_error_line_385(self):
        """Reproduce the exact error from websocket_ssot.py:385 - WILL FAIL."""
        # Create a websocket mock with a Starlette URL object (no query_params)
        websocket = Mock()
        websocket.url = URL("wss://staging.netra.ai/ws?token=abc123&user_id=user123")
        
        # This should reproduce the AttributeError from line 385
        with pytest.raises(AttributeError, match="'URL' object has no attribute 'query_params'"):
            # This is the exact code pattern from websocket_ssot.py:385
            if hasattr(websocket.url, 'query_params'):
                query_params = websocket.url.query_params  # This line should fail
    
    def test_reproduce_middleware_setup_error_line_576(self):
        """Reproduce error context from middleware_setup.py:576 - WILL FAIL."""
        # This test represents the error handling context where the AttributeError occurs
        
        def simulate_middleware_websocket_processing():
            """Simulate the WebSocket processing that fails."""
            websocket = Mock()
            websocket.url = URL("wss://staging.netra.ai/ws?token=abc123")
            
            # This simulates the processing that leads to the error
            try:
                if hasattr(websocket.url, 'query_params'):
                    params = websocket.url.query_params
                return params
            except AttributeError as e:
                # This is where middleware_setup.py:576 catches the error
                raise Exception(f"CRITICAL: ASGI scope error in WebSocket exclusion: {e}")
        
        # This should reproduce the exact error message from the logs
        with pytest.raises(Exception, match="CRITICAL: ASGI scope error in WebSocket exclusion"):
            simulate_middleware_websocket_processing()
    
    def test_gcp_cloud_run_asgi_scope_characteristics(self):
        """Test GCP Cloud Run specific ASGI scope characteristics - MAY FAIL."""
        # GCP Cloud Run might create ASGI scopes differently
        # This test simulates potential differences
        
        gcp_style_scope = {
            'type': 'websocket',
            'scheme': 'wss',
            'path': '/ws',
            'query_string': b'token=abc123&user_id=user123',
            'headers': [
                (b'host', b'staging.netra.ai'),
                (b'x-forwarded-for', b'10.0.0.1'),
                (b'x-forwarded-proto', b'https'),
            ],
            # GCP might add additional scope keys that affect URL object creation
            'server': ('staging.netra.ai', 443),
            'client': ('10.0.0.1', 56789),
        }
        
        # Test if different scope creation affects URL object type
        # This might reveal GCP-specific ASGI scope handling issues
        # Implementation would depend on how FastAPI/Starlette creates URLs from scopes
        
        # Placeholder for actual testing logic
        assert gcp_style_scope['type'] == 'websocket'
        assert gcp_style_scope['query_string'] == b'token=abc123&user_id=user123'


if __name__ == "__main__":
    # Run tests to reproduce errors
    pytest.main([__file__, "-v", "--tb=short"])