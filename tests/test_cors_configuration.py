#!/usr/bin/env python3
"""
Comprehensive CORS Configuration Unit Tests
Tests CORS middleware configuration, origin validation, and environment-specific settings.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import Dict, List, Any
from starlette.responses import Response
from starlette.requests import Request


class TestCORSOriginParsing:
    """Test CORS origin parsing from environment variables."""
    
    def test_cors_origins_wildcard_parsing(self):
        """Test CORS_ORIGINS=* environment variable parsing."""
        with patch.dict(os.environ, {"CORS_ORIGINS": "*"}):
            from app.core.middleware_setup import _handle_dev_env_origins
            origins = _handle_dev_env_origins("*")
            assert origins == ["*"]
    
    def test_cors_origins_comma_separated_parsing(self):
        """Test CORS_ORIGINS comma-separated parsing."""
        test_origins = "http://localhost:3000,https://app.staging.netrasystems.ai,https://production.netrasystems.ai"
        with patch.dict(os.environ, {"CORS_ORIGINS": test_origins}):
            from app.core.middleware_setup import _handle_dev_env_origins
            origins = _handle_dev_env_origins(test_origins)
            expected = [
                "http://localhost:3000",
                "https://app.staging.netrasystems.ai", 
                "https://production.netrasystems.ai"
            ]
            assert origins == expected
    
    def test_cors_origins_empty_string_handling(self):
        """Test CORS_ORIGINS empty string handling."""
        with patch.dict(os.environ, {"CORS_ORIGINS": ""}):
            from app.core.middleware_setup import _get_development_cors_origins
            origins = _get_development_cors_origins()
            assert "*" in origins
            assert "http://localhost:3000" in origins
    
    def test_cors_origins_whitespace_handling(self):
        """Test CORS_ORIGINS with extra whitespace."""
        test_origins = " http://localhost:3000 , https://app.staging.netrasystems.ai , "
        from app.core.middleware_setup import _handle_dev_env_origins
        origins = _handle_dev_env_origins(test_origins)
        expected = ["http://localhost:3000", "https://app.staging.netrasystems.ai"]
        assert origins == expected


class TestCORSEnvironmentConfigurations:
    """Test CORS configuration for different environments."""
    
    def test_development_cors_origins(self):
        """Test development environment CORS origins."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            from app.core.middleware_setup import get_cors_origins
            origins = get_cors_origins()
            assert "*" in origins
            assert "http://localhost:3000" in origins
            assert "http://localhost:8000" in origins
    
    def test_staging_cors_origins(self):
        """Test staging environment CORS origins."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "staging"
            with patch.dict(os.environ, {"CORS_ORIGINS": ""}):
                from app.core.middleware_setup import get_cors_origins
                origins = get_cors_origins()
                assert "https://staging.netrasystems.ai" in origins
                assert "https://app.staging.netrasystems.ai" in origins
                assert "http://localhost:3000" in origins
    
    def test_production_cors_origins(self):
        """Test production environment CORS origins."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "production"
            with patch.dict(os.environ, {"CORS_ORIGINS": ""}):
                from app.core.middleware_setup import get_cors_origins
                origins = get_cors_origins()
                assert "https://netrasystems.ai" in origins
                assert "*" not in origins
                assert "localhost" not in "".join(origins)
    
    def test_production_cors_env_override(self):
        """Test production CORS origins can be overridden by environment variable."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "production"
            test_origins = "https://custom.netrasystems.ai,https://api.netrasystems.ai"
            with patch.dict(os.environ, {"CORS_ORIGINS": test_origins}):
                from app.core.middleware_setup import get_cors_origins
                origins = get_cors_origins()
                assert "https://custom.netrasystems.ai" in origins
                assert "https://api.netrasystems.ai" in origins


class TestCORSOriginValidation:
    """Test CORS origin validation logic."""
    
    def test_direct_origin_match(self):
        """Test direct origin matching."""
        from app.core.middleware_setup import is_origin_allowed
        allowed_origins = ["http://localhost:3000", "https://app.netrasystems.ai"]
        
        assert is_origin_allowed("http://localhost:3000", allowed_origins) is True
        assert is_origin_allowed("https://app.netrasystems.ai", allowed_origins) is True
        assert is_origin_allowed("https://evil.com", allowed_origins) is False
    
    def test_wildcard_origin_development(self):
        """Test wildcard origin validation in development."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            from app.core.middleware_setup import is_origin_allowed
            allowed_origins = ["*"]
            
            assert is_origin_allowed("http://localhost:3000", allowed_origins) is True
            assert is_origin_allowed("https://random.domain.com", allowed_origins) is True
            assert is_origin_allowed("http://127.0.0.1:8080", allowed_origins) is True
    
    def test_wildcard_origin_staging_disabled(self):
        """Test wildcard origin validation disabled in staging."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "staging"
            from app.core.middleware_setup import is_origin_allowed
            allowed_origins = ["*"]
            
            # Wildcard should be disabled in staging, but specific patterns allowed
            assert is_origin_allowed("https://malicious.com", allowed_origins) is False
    
    def test_localhost_pattern_matching(self):
        """Test localhost pattern matching."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            from app.core.middleware_setup import is_origin_allowed
            allowed_origins = ["*"]
            
            # Various localhost formats
            assert is_origin_allowed("http://localhost:3000", allowed_origins) is True
            assert is_origin_allowed("https://localhost:8080", allowed_origins) is True
            assert is_origin_allowed("http://127.0.0.1:5000", allowed_origins) is True
            assert is_origin_allowed("https://127.0.0.1", allowed_origins) is True
    
    def test_staging_domain_pattern_matching(self):
        """Test staging domain pattern matching."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "staging"
            from app.core.middleware_setup import is_origin_allowed
            allowed_origins = ["*"]
            
            # Should match staging subdomain patterns
            assert is_origin_allowed("https://app.staging.netrasystems.ai", allowed_origins) is True
            assert is_origin_allowed("https://auth.staging.netrasystems.ai", allowed_origins) is True
            assert is_origin_allowed("https://backend.staging.netrasystems.ai", allowed_origins) is True
            assert is_origin_allowed("https://pr-123.staging.netrasystems.ai", allowed_origins) is True
            
            # Should not match production patterns
            assert is_origin_allowed("https://app.netrasystems.ai", allowed_origins) is False
    
    def test_cloud_run_pattern_matching(self):
        """Test Cloud Run URL pattern matching."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "staging"
            from app.core.middleware_setup import is_origin_allowed
            allowed_origins = ["*"]
            
            # Cloud Run patterns
            assert is_origin_allowed("https://netra-frontend-123456.us-central1.run.app", allowed_origins) is True
            assert is_origin_allowed("https://netra-backend-654321.us-central1.run.app", allowed_origins) is True
            assert is_origin_allowed("https://service-abc123-uc.a.run.app", allowed_origins) is True
            
            # Invalid patterns
            assert is_origin_allowed("https://malicious.run.app", allowed_origins) is False
    
    def test_empty_origin_rejection(self):
        """Test empty origin is rejected."""
        from app.core.middleware_setup import is_origin_allowed
        allowed_origins = ["*", "http://localhost:3000"]
        
        assert is_origin_allowed("", allowed_origins) is False
        assert is_origin_allowed(None, allowed_origins) is False


class TestDynamicCORSMiddleware:
    """Test DynamicCORSMiddleware functionality."""
    
    @pytest.fixture
    def mock_request_options(self):
        """Create mock OPTIONS request."""
        request = MagicMock(spec=Request)
        request.method = "OPTIONS"
        request.headers = {"origin": "http://localhost:3000"}
        return request
    
    @pytest.fixture  
    def mock_request_get(self):
        """Create mock GET request."""
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.headers = {"origin": "http://localhost:3000"}
        return request
    
    @pytest.fixture
    def call_next_mock(self):
        """Create mock call_next function."""
        async def mock_call_next(request):
            response = Response(content="test response")
            return response
        return mock_call_next
    
    @pytest.mark.asyncio
    async def test_dynamic_cors_options_preflight(self, mock_request_options, call_next_mock):
        """Test DynamicCORSMiddleware handles OPTIONS preflight correctly."""
        # Import the auth service's DynamicCORSMiddleware
        import sys
        sys.path.append("C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\auth_service")
        from main import DynamicCORSMiddleware
        
        middleware = DynamicCORSMiddleware(app=None)
        response = await middleware.dispatch(mock_request_options, call_next_mock)
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
        assert "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD" in response.headers["Access-Control-Allow-Methods"]
        assert response.headers["Access-Control-Max-Age"] == "3600"
    
    @pytest.mark.asyncio
    async def test_dynamic_cors_regular_request(self, mock_request_get, call_next_mock):
        """Test DynamicCORSMiddleware handles regular requests correctly."""
        import sys
        sys.path.append("C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1\\auth_service")
        from main import DynamicCORSMiddleware
        
        middleware = DynamicCORSMiddleware(app=None)
        response = await middleware.dispatch(mock_request_get, call_next_mock)
        
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
        assert response.headers["Access-Control-Expose-Headers"] == "X-Trace-ID, X-Request-ID, Content-Length, Content-Type"


class TestCustomCORSMiddleware:
    """Test CustomCORSMiddleware functionality."""
    
    @pytest.fixture
    def mock_request_options(self):
        """Create mock OPTIONS request."""
        request = MagicMock(spec=Request)
        request.method = "OPTIONS"
        request.headers = {"origin": "http://localhost:3000"}
        return request
    
    @pytest.fixture
    def call_next_mock(self):
        """Create mock call_next function."""
        async def mock_call_next(request):
            response = Response(content="test response")
            return response
        return mock_call_next
    
    @pytest.mark.asyncio
    async def test_custom_cors_options_handling(self, mock_request_options, call_next_mock):
        """Test CustomCORSMiddleware handles OPTIONS correctly."""
        from app.core.middleware_setup import CustomCORSMiddleware
        
        middleware = CustomCORSMiddleware(app=None)
        response = await middleware.dispatch(mock_request_options, call_next_mock)
        
        assert response.status_code == 200
        assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
        assert response.headers["Access-Control-Allow-Credentials"] == "true"
        assert response.headers["Access-Control-Max-Age"] == "3600"
    
    @pytest.mark.asyncio 
    async def test_custom_cors_origin_validation(self):
        """Test CustomCORSMiddleware validates origins correctly."""
        from app.core.middleware_setup import CustomCORSMiddleware
        
        # Mock request with disallowed origin
        request = MagicMock(spec=Request)
        request.method = "GET"
        request.headers = {"origin": "https://malicious.com"}
        
        async def mock_call_next(request):
            return Response(content="test")
        
        # Mock get_cors_origins to return specific allowed origins
        with patch('app.core.middleware_setup.get_cors_origins') as mock_get_origins:
            mock_get_origins.return_value = ["http://localhost:3000"]
            
            middleware = CustomCORSMiddleware(app=None)
            response = await middleware.dispatch(request, mock_call_next)
            
            # Should not have CORS headers for disallowed origin
            assert "Access-Control-Allow-Origin" not in response.headers


class TestCORSHeaderValidation:
    """Test CORS header validation."""
    
    def test_preflight_headers_complete(self):
        """Test preflight response has all required headers."""
        required_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods", 
            "Access-Control-Allow-Headers",
            "Access-Control-Allow-Credentials",
            "Access-Control-Max-Age"
        ]
        
        # Test headers are defined in middleware
        from app.core.middleware_setup import CustomCORSMiddleware
        middleware = CustomCORSMiddleware(app=None)
        
        # Check that the required headers are set in the middleware code
        # (This is a structural test to ensure all headers are included)
        import inspect
        source = inspect.getsource(middleware._handle_request)
        
        for header in required_headers:
            assert header in source, f"Required header {header} not found in middleware"
    
    def test_exposed_headers_configuration(self):
        """Test expose headers are properly configured."""
        from app.core.middleware_setup import CustomCORSMiddleware
        
        middleware = CustomCORSMiddleware(app=None)
        import inspect
        source = inspect.getsource(middleware._add_cors_headers)
        
        # Check that expose headers are configured
        assert "Access-Control-Expose-Headers" in source
        assert "X-Trace-ID" in source
        assert "X-Request-ID" in source
    
    def test_allowed_methods_comprehensive(self):
        """Test all required HTTP methods are allowed."""
        required_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"]
        
        from app.core.middleware_setup import _get_production_cors_config
        config = _get_production_cors_config(["https://netrasystems.ai"])
        
        allowed_methods = config["allow_methods"]
        for method in required_methods:
            assert method in allowed_methods, f"Method {method} not in allowed methods"
    
    def test_allowed_headers_comprehensive(self):
        """Test all required headers are allowed."""
        required_headers = [
            "Authorization", "Content-Type", "X-Request-ID", 
            "X-Trace-ID", "Accept", "Origin", "Referer", "X-Requested-With"
        ]
        
        from app.core.middleware_setup import _get_production_cors_config
        config = _get_production_cors_config(["https://netrasystems.ai"])
        
        allowed_headers = config["allow_headers"]
        for header in required_headers:
            assert header in allowed_headers, f"Header {header} not in allowed headers"


class TestCORSMiddlewareSetup:
    """Test CORS middleware setup logic."""
    
    def test_middleware_setup_development(self):
        """Test middleware setup for development environment."""
        from fastapi import FastAPI
        from app.core.middleware_setup import setup_cors_middleware
        
        app = FastAPI()
        
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            
            # Mock the add_middleware method to capture what's added
            middleware_calls = []
            original_add_middleware = app.add_middleware
            def mock_add_middleware(*args, **kwargs):
                middleware_calls.append((args, kwargs))
                return original_add_middleware(*args, **kwargs)
            app.add_middleware = mock_add_middleware
            
            setup_cors_middleware(app)
            
            # Should use CustomCORSMiddleware for development
            assert len(middleware_calls) > 0
            middleware_class = middleware_calls[0][0][0]
            assert "CustomCORSMiddleware" in str(middleware_class)
    
    def test_middleware_setup_production(self):
        """Test middleware setup for production environment."""
        from fastapi import FastAPI
        from app.core.middleware_setup import setup_cors_middleware
        
        app = FastAPI()
        
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "production"
            
            middleware_calls = []
            original_add_middleware = app.add_middleware
            def mock_add_middleware(*args, **kwargs):
                middleware_calls.append((args, kwargs))
                return original_add_middleware(*args, **kwargs)
            app.add_middleware = mock_add_middleware
            
            with patch.dict(os.environ, {"CORS_ORIGINS": ""}):
                setup_cors_middleware(app)
            
            # Should use CORSMiddleware for production
            assert len(middleware_calls) > 0
            middleware_class = middleware_calls[0][0][0]
            assert "CORSMiddleware" in str(middleware_class)


class TestCORSRegressionPrevention:
    """Test specific regression scenarios from the CORS specification."""
    
    def test_auth_config_endpoint_cors_regression(self):
        """Test that /auth/config endpoint will have CORS headers."""
        # This tests the specific regression mentioned in the spec:
        # "Access to fetch at 'http://localhost:8081/auth/config' from origin 'http://localhost:3001' has been blocked by CORS policy"
        
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            from app.core.middleware_setup import is_origin_allowed, get_cors_origins
            
            origins = get_cors_origins()
            
            # Verify that localhost:3001 can access localhost:8081 resources
            assert is_origin_allowed("http://localhost:3001", origins) is True
    
    def test_frontend_backend_cors_regression(self):
        """Test frontend (3001) to backend (8000) CORS."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            from app.core.middleware_setup import is_origin_allowed, get_cors_origins
            
            origins = get_cors_origins()
            
            # Frontend to backend communication
            assert is_origin_allowed("http://localhost:3001", origins) is True
            
            # Various dev ports should work
            assert is_origin_allowed("http://localhost:3000", origins) is True
            assert is_origin_allowed("http://localhost:8000", origins) is True
    
    def test_dynamic_port_regression(self):
        """Test dynamic localhost ports are handled correctly."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            from app.core.middleware_setup import is_origin_allowed
            
            # With wildcard, any localhost port should work
            origins = ["*"]
            assert is_origin_allowed("http://localhost:49672", origins) is True
            assert is_origin_allowed("http://127.0.0.1:35281", origins) is True
    
    def test_staging_pr_environment_regression(self):
        """Test staging PR environment dynamic origins."""
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "staging"
            from app.core.middleware_setup import is_origin_allowed
            
            origins = ["*"]  # Staging uses pattern matching
            
            # PR environment URLs should be allowed
            assert is_origin_allowed("https://pr-123.staging.netrasystems.ai", origins) is True
            assert is_origin_allowed("https://frontend-pr-456.staging.netrasystems.ai", origins) is True
    
    def test_credentials_with_wildcard_regression(self):
        """Test that credentials work with wildcard origins."""
        # This tests the specific issue where credentials: true cannot be used with origin: "*"
        # Our solution uses DynamicCORSMiddleware to echo back the requesting origin
        
        with patch('app.core.middleware_setup.settings') as mock_settings:
            mock_settings.environment = "development"
            
            # This should be handled by DynamicCORSMiddleware, not throw an error
            from app.core.middleware_setup import get_cors_origins
            origins = get_cors_origins()
            assert "*" in origins  # Development should include wildcard


if __name__ == "__main__":
    pytest.main([__file__, "-v"])