"""
CORS Configuration Regression Test Suite

Comprehensive test suite to prevent CORS configuration regressions across all environments.
This ensures that all required origins are properly configured and that security
requirements are maintained.

Business Value Justification (BVJ):
- Segment: ALL (Critical for frontend-backend communication)
- Business Goal: Prevent CORS errors that block user interactions
- Value Impact: Ensures platform availability and user experience
- Strategic Impact: Maintains security while enabling cross-origin communication
"""
import pytest
import sys
from pathlib import Path
from typing import List, Dict, Any, Tuple
from shared.isolated_environment import IsolatedEnvironment
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
from shared.cors_config_builder import CORSConfigurationBuilder

class CORSConfigurationTests:
    """Test suite for CORS configuration across all environments."""

    def test_staging_required_origins(self):
        """Test that staging environment has all required origins configured."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
        allowed_origins = cors.origins.allowed
        required_origins = ['https://staging.netrasystems.ai', 'https://app.staging.netrasystems.ai', 'https://auth.staging.netrasystems.ai', 'https://api.staging.netrasystems.ai', 'https://api.staging.netrasystems.ai']
        missing_origins = []
        for origin in required_origins:
            if origin not in allowed_origins:
                missing_origins.append(origin)
        assert len(missing_origins) == 0, f'Missing required staging origins: {missing_origins}. This will cause CORS errors in staging environment.'

    def test_staging_cloud_run_urls(self):
        """Test that staging includes Cloud Run URLs for services."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
        allowed_origins = cors.origins.allowed
        cloud_run_patterns = ['https://netra-frontend-701982941522.us-central1.run.app', 'https://netra-backend-701982941522.us-central1.run.app', 'https://auth.staging.netrasystems.ai']
        missing_urls = []
        for url in cloud_run_patterns:
            if url not in allowed_origins:
                missing_urls.append(url)
        assert len(missing_urls) == 0, f'Missing Cloud Run URLs in staging: {missing_urls}. Direct Cloud Run access will be blocked.'

    def test_staging_localhost_support(self):
        """Test that staging supports localhost for development testing."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
        allowed_origins = cors.origins.allowed
        localhost_origins = ['http://localhost:3000', 'http://localhost:8000', 'http://localhost:8081', 'http://127.0.0.1:3000']
        missing_localhost = []
        for origin in localhost_origins:
            if origin not in allowed_origins:
                missing_localhost.append(origin)
        assert len(missing_localhost) == 0, f'Missing localhost origins in staging: {missing_localhost}. Local development against staging will be blocked.'

    def test_production_required_origins(self):
        """Test that production has all required origins configured."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'production'})
        allowed_origins = cors.origins.allowed
        required_origins = ['https://netrasystems.ai', 'https://www.netrasystems.ai', 'https://app.netrasystems.ai', 'https://api.netrasystems.ai', 'https://auth.netrasystems.ai']
        missing_origins = []
        for origin in required_origins:
            if origin not in allowed_origins:
                missing_origins.append(origin)
        assert len(missing_origins) == 0, f'Missing required production origins: {missing_origins}. This will cause CORS errors in production.'

    def test_production_security_no_wildcards(self):
        """Test that production does not allow wildcard origins."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'production'})
        allowed_origins = cors.origins.allowed
        assert '*' not in allowed_origins, 'SECURITY VIOLATION: Production environment contains wildcard (*) origin. This allows ANY website to access the API.'

    def test_production_no_localhost(self):
        """Test that production does not allow localhost origins."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'production'})
        allowed_origins = cors.origins.allowed
        localhost_patterns = ['localhost', '127.0.0.1', '0.0.0.0', '[::1]']
        localhost_origins = []
        for origin in allowed_origins:
            for pattern in localhost_patterns:
                if pattern in origin:
                    localhost_origins.append(origin)
                    break
        assert len(localhost_origins) == 0, f'SECURITY WARNING: Production contains localhost origins: {localhost_origins}. These should not be allowed in production.'

    def test_development_localhost_comprehensive(self):
        """Test that development environment has comprehensive localhost support."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'development'})
        allowed_origins = cors.origins.allowed
        required_localhost = ['http://localhost:3000', 'http://localhost:8000', 'http://localhost:8081', 'http://127.0.0.1:3000', 'http://0.0.0.0:3000', 'http://frontend:3000', 'http://backend:8000', 'http://auth:8081']
        missing = []
        for origin in required_localhost:
            if origin not in allowed_origins:
                missing.append(origin)
        assert len(missing) == 0, f'Missing localhost origins in development: {missing}. Local development will be restricted.'

    def test_origin_validation_method(self):
        """Test that origin validation method works correctly."""
        test_cases = [('staging', 'https://staging.netrasystems.ai', True), ('staging', 'https://app.staging.netrasystems.ai', True), ('staging', 'https://evil.com', False), ('staging', 'http://localhost:3000', True), ('production', 'https://app.netrasystems.ai', True), ('production', 'http://localhost:3000', False), ('production', 'https://evil.com', False), ('development', 'http://localhost:3000', True), ('development', 'http://192.168.1.100:3000', False)]
        for env, origin, expected in test_cases:
            cors = CORSConfigurationBuilder({'ENVIRONMENT': env})
            result = cors.origins.is_allowed(origin)
            assert result == expected, f'Origin validation failed for {origin} in {env}. Expected: {expected}, Got: {result}'

    def test_cors_headers_configuration(self):
        """Test that CORS headers are properly configured."""
        for env in ['development', 'staging', 'production']:
            cors = CORSConfigurationBuilder({'ENVIRONMENT': env})
            config = cors.fastapi.get_middleware_config()
            assert 'allow_origins' in config, f'Missing allow_origins in {env}'
            assert 'allow_credentials' in config, f'Missing allow_credentials in {env}'
            assert 'allow_methods' in config, f'Missing allow_methods in {env}'
            assert 'allow_headers' in config, f'Missing allow_headers in {env}'
            assert 'expose_headers' in config, f'Missing expose_headers in {env}'
            assert 'max_age' in config, f'Missing max_age in {env}'
            assert config['allow_credentials'] == True, f'allow_credentials should be True in {env} for authenticated requests'
            required_methods = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
            for method in required_methods:
                assert method in config['allow_methods'], f'Missing required HTTP method {method} in {env}'
            required_headers = ['Authorization', 'Content-Type', 'X-Request-ID']
            for header in required_headers:
                assert header in config['allow_headers'], f'Missing required header {header} in {env}'

    def test_websocket_cors_configuration(self):
        """Test that WebSocket CORS configuration is properly set."""
        for env in ['development', 'staging', 'production']:
            cors = CORSConfigurationBuilder({'ENVIRONMENT': env})
            ws_origins = cors.websocket.allowed_origins
            assert ws_origins == cors.origins.allowed, f"WebSocket origins don't match HTTP origins in {env}"

    def test_service_to_service_bypass(self):
        """Test that service-to-service requests can bypass CORS."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
        service_headers = {'x-service-name': 'auth-service', 'user-agent': 'httpx/0.24.1'}
        assert cors.service_detector.is_internal_request(service_headers), 'Service-to-service request not detected'
        assert cors.origins.is_allowed('https://internal.service', service_to_service=True), 'Service-to-service bypass not working'

    def test_content_type_validation(self):
        """Test that suspicious content types are detected."""
        cors = CORSConfigurationBuilder()
        safe_types = ['application/json', 'text/plain', 'application/x-www-form-urlencoded', 'multipart/form-data']
        for content_type in safe_types:
            assert cors.security.validate_content_type(content_type), f'Safe content type {content_type} incorrectly flagged'
        suspicious_types = ['text/x-shellscript', 'application/x-msdownload', 'text/vbscript']
        for content_type in suspicious_types:
            assert not cors.security.validate_content_type(content_type), f'Suspicious content type {content_type} not detected'

    def test_cors_middleware_config_validity(self):
        """Test that CORS middleware configuration is valid for FastAPI."""
        for env in ['development', 'staging', 'production']:
            cors = CORSConfigurationBuilder({'ENVIRONMENT': env})
            config = cors.fastapi.get_middleware_config()
            is_valid = cors.health.validate_config(config)
            assert is_valid, f'Invalid CORS configuration for {env}'
            assert len(config['allow_origins']) > 0, f'No origins configured for {env}'
            assert 0 < config['max_age'] <= 86400, f"Invalid max_age value in {env}: {config['max_age']}"

    def test_cors_fix_middleware_integration(self):
        """Test that CORSFixMiddleware can properly initialize with configuration."""
        from netra_backend.app.middleware.cors_fix_middleware import CORSFixMiddleware

        class MockApp:
            pass
        app = MockApp()
        for env in ['development', 'staging', 'production']:
            try:
                middleware = CORSFixMiddleware(app, environment=env)
                assert middleware.environment == env
                assert len(middleware.allowed_origins) > 0
            except Exception as e:
                pytest.fail(f'CORSFixMiddleware failed to initialize for {env}: {e}')

    @pytest.mark.parametrize('environment', ['development', 'staging', 'production'])
    def test_no_duplicate_origins(self, environment: str):
        """Test that there are no duplicate origins in configuration."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': environment})
        origins = cors.origins.allowed
        unique_origins = list(set(origins))
        assert len(origins) == len(unique_origins), f'Duplicate origins found in {environment}: {[o for o in origins if origins.count(o) > 1]}'

    @pytest.mark.parametrize('environment', ['development', 'staging', 'production'])
    def test_origin_format_validity(self, environment: str):
        """Test that all configured origins have valid format."""
        cors = CORSConfigurationBuilder({'ENVIRONMENT': environment})
        origins = cors.origins.allowed
        for origin in origins:
            if origin == '*':
                continue
            is_valid, error = cors.origins.validate_origin_format(origin)
            assert is_valid, f'Invalid origin format in {environment}: {origin}. Error: {error}'

class CORSRegressionPreventionTests:
    """Tests specifically designed to prevent known CORS issues from recurring."""

    def test_staging_base_domain_included(self):
        """
        Regression test for missing https://staging.netrasystems.ai origin.
        This was causing CORS errors when frontend redirected to base domain.
        """
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
        assert 'https://staging.netrasystems.ai' in cors.origins.allowed, 'REGRESSION: https://staging.netrasystems.ai is missing from staging origins. This exact issue caused CORS errors in staging on 2025-09-03.'

    def test_auth_service_cloud_run_url(self):
        """
        Test that auth service Cloud Run URL is included in staging.
        """
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
        assert 'https://auth.staging.netrasystems.ai' in cors.origins.allowed, 'Auth service Cloud Run URL missing from staging origins'

    def test_auth_service_local_port(self):
        """
        Test that auth service local development port is included.
        """
        cors = CORSConfigurationBuilder({'ENVIRONMENT': 'staging'})
        assert 'http://localhost:8081' in cors.origins.allowed, 'Auth service local port (8081) missing from staging origins'
        assert 'http://127.0.0.1:8081' in cors.origins.allowed, 'Auth service local IP port (127.0.0.1:8081) missing from staging origins'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')