"""
Unit Tests for GCP WebSocket Readiness Middleware - Issue #919 Fix

MISSION CRITICAL: Tests the fix for WebSocket connection rejection in GCP environments
where startup_phase gets stuck at 'unknown', causing legitimate connections to be rejected.

ISSUE #919 SUMMARY:
- WebSocket connections rejected with "State: unknown, Failed services: [], Error: service_not_ready"
- Root cause: GCP Cloud Run startup_phase stuck at 'unknown'
- Fix: Graceful degradation for GCP environments with unknown startup phase

Business Value Justification:
- Segment: Platform/Internal ($500K+ ARR protection)
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Prevents WebSocket 1011 errors that block chat functionality
- Strategic Impact: Enables reliable WebSocket connections in GCP Cloud Run
"""
import asyncio
import pytest
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
import sys
import os
sys.path.append('/Users/anthony/Desktop/netra-apex')
from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware, create_gcp_websocket_readiness_middleware, setup_gcp_websocket_protection, websocket_readiness_health_check
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.testclient import TestClient

@pytest.mark.unit
class TestGCPWebSocketReadinessMiddleware:
    """Unit tests for GCP WebSocket readiness middleware."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app_state = Mock()
        self.mock_app_state.startup_phase = 'unknown'
        self.mock_app_state.startup_complete = False
        self.mock_app_state.startup_failed = False
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        self.logger_patcher = patch('netra_backend.app.logging_config.central_logger.get_logger')
        self.mock_logger = self.logger_patcher.start()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        self.logger_patcher.stop()

    def test_middleware_initialization_gcp_environment(self):
        """Test middleware initialization in GCP environment."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging', 'K_SERVICE': 'netra-backend'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
        middleware = GCPWebSocketReadinessMiddleware(None, timeout_seconds=30.0)
        assert middleware.environment == 'staging'
        assert middleware.is_gcp_environment == True
        assert middleware.is_cloud_run == True
        assert middleware.timeout_seconds == 30.0
        assert middleware._cache_duration == 15.0

    def test_middleware_initialization_non_gcp_environment(self):
        """Test middleware initialization in non-GCP environment."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'development'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
        middleware = GCPWebSocketReadinessMiddleware(None)
        assert middleware.environment == 'development'
        assert middleware.is_gcp_environment == False
        assert middleware.is_cloud_run == False

    def test_should_protect_request_gcp_websocket(self):
        """Test that WebSocket requests in GCP environments are protected."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'staging', 'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.headers = {'connection': 'upgrade', 'upgrade': 'websocket', 'sec-websocket-key': 'test-key', 'sec-websocket-version': '13'}
        mock_request.url = Mock()
        mock_request.url.path = '/ws/chat'
        mock_request.method = 'GET'
        with patch.object(middleware, '_is_websocket_request', return_value=True):
            should_protect = middleware._should_protect_request(mock_request)
        assert should_protect == True

    def test_should_protect_request_non_gcp_environment(self):
        """Test that non-GCP environments skip protection."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'development'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        with patch.object(middleware, '_is_websocket_request', return_value=True):
            should_protect = middleware._should_protect_request(mock_request)
        assert should_protect == False

    def test_is_websocket_request_standard_headers(self):
        """Test WebSocket request detection with standard headers."""
        mock_env_manager = Mock()
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.headers = {'connection': 'upgrade', 'upgrade': 'websocket', 'sec-websocket-key': 'dGhlIHNhbXBsZSBub25jZQ==', 'sec-websocket-version': '13'}
        mock_request.url = Mock()
        mock_request.url.path = '/ws/chat'
        mock_request.method = 'GET'
        is_websocket = middleware._is_websocket_request(mock_request)
        assert is_websocket == True

    def test_is_websocket_request_path_based_detection(self):
        """Test WebSocket request detection based on path."""
        mock_env_manager = Mock()
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.headers = {'sec-websocket-key': 'dGhlIHNhbXBsZSBub25jZQ==', 'sec-websocket-version': '13'}
        mock_request.url = Mock()
        mock_request.url.path = '/ws/chat'
        mock_request.method = 'GET'
        is_websocket = middleware._is_websocket_request(mock_request)
        assert is_websocket == True

    def test_is_websocket_request_non_websocket(self):
        """Test that non-WebSocket requests are not detected."""
        mock_env_manager = Mock()
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.headers = {}
        mock_request.url = Mock()
        mock_request.url.path = '/api/health'
        mock_request.method = 'GET'
        is_websocket = middleware._is_websocket_request(mock_request)
        assert is_websocket == False

    @pytest.mark.asyncio
    async def test_check_websocket_readiness_staging_bypass(self):
        """Test ISSUE #919 FIX: staging bypass for readiness check."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'staging', 'BYPASS_WEBSOCKET_READINESS_STAGING': 'true', 'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = self.mock_app_state
        ready, details = await middleware._check_websocket_readiness(mock_request)
        assert ready == True
        assert details['bypass_active'] == True
        assert details['bypass_reason'] == 'staging_middleware_remediation'
        assert 'middleware_bypass' in details

    @pytest.mark.asyncio
    async def test_check_websocket_readiness_staging_graceful_degradation(self):
        """Test ISSUE #919 FIX: staging graceful degradation when readiness fails."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'staging', 'BYPASS_WEBSOCKET_READINESS_STAGING': 'false', 'GOOGLE_CLOUD_PROJECT': 'netra-staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = self.mock_app_state
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
            mock_validator.return_value = (False, {'failed_services': ['agent_supervisor'], 'state': 'failed'})
            ready, details = await middleware._check_websocket_readiness(mock_request)
            assert ready == True
            assert details['graceful_degradation'] == True
            assert details['original_ready'] == False
            assert details['degradation_reason'] == 'staging_environment_graceful_override'

    @pytest.mark.asyncio
    async def test_check_websocket_readiness_production_strict_validation(self):
        """Test that production environment enforces strict validation."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'production', 'GOOGLE_CLOUD_PROJECT': 'netra-production'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = self.mock_app_state
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
            mock_validator.return_value = (False, {'failed_services': ['agent_supervisor'], 'state': 'failed'})
            ready, details = await middleware._check_websocket_readiness(mock_request)
            assert ready == False
            assert 'graceful_degradation' not in details or not details.get('graceful_degradation')

    @pytest.mark.asyncio
    async def test_check_websocket_readiness_validator_import_error(self):
        """Test handling of validator import errors."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'development'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.app = Mock()
        mock_request.app.state = self.mock_app_state
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check', side_effect=ImportError('Module not found')):
            ready, details = await middleware._check_websocket_readiness(mock_request)
            assert ready == True
            assert details['validator_available'] == False
            assert details['allowed'] == True

    @pytest.mark.asyncio
    async def test_validate_cloud_run_websocket_compatibility(self):
        """Test Cloud Run WebSocket compatibility validation."""
        mock_env_manager = Mock()
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.headers = {'sec-websocket-key': 'dGhlIHNhbXBsZSBub25jZQ==', 'sec-websocket-version': '13', 'upgrade': 'websocket', 'connection': 'upgrade'}
        mock_request.content_length = 100
        result = await middleware._validate_cloud_run_websocket_compatibility(mock_request)
        assert result['valid'] == True
        assert result['cloud_run_compatible'] == True
        assert len(result['errors']) == 0

    @pytest.mark.asyncio
    async def test_validate_cloud_run_websocket_missing_headers(self):
        """Test Cloud Run compatibility with missing required headers."""
        mock_env_manager = Mock()
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.headers = {'upgrade': 'websocket', 'connection': 'upgrade'}
        mock_request.content_length = None
        result = await middleware._validate_cloud_run_websocket_compatibility(mock_request)
        assert result['valid'] == False
        assert 'Missing required header: sec-websocket-key' in result['errors']
        assert 'Missing required header: sec-websocket-version' in result['errors']

    @pytest.mark.asyncio
    async def test_reject_websocket_connection_cloud_run_compatible(self):
        """Test WebSocket connection rejection with Cloud Run compatibility."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = '/ws/chat'
        details = {'failed_services': ['agent_supervisor'], 'state': 'failed', 'error': 'service_not_ready'}
        response = await middleware._reject_websocket_connection_cloud_run_compatible(mock_request, details)
        assert isinstance(response, JSONResponse)
        assert response.status_code == 503
        assert 'Retry-After' in response.headers
        assert response.headers['X-Cloud-Run-Compatible'] == 'true'
        assert response.headers['X-Issue-449-Fix'] == 'enhanced-rejection'

    @pytest.mark.asyncio
    async def test_reject_websocket_connection_timeout_error(self):
        """Test WebSocket connection rejection for timeout errors."""
        mock_env_manager = Mock()
        self.mock_env.return_value = mock_env_manager
        middleware = GCPWebSocketReadinessMiddleware(None)
        mock_request = Mock()
        mock_request.url = Mock()
        mock_request.url.path = '/ws/chat'
        details = {'error': 'cloud_run_timeout', 'state': 'timeout'}
        response = await middleware._reject_websocket_connection_cloud_run_compatible(mock_request, details)
        assert response.status_code == 408
        assert int(response.headers['Retry-After']) == 5
        import json
        content = json.loads(response.body.decode())
        assert content['error'] == 'cloud_run_timeout'
        assert content['details']['cloud_run_timeout'] == middleware.load_balancer_timeout

@pytest.mark.unit
class TestGCPWebSocketMiddlewareFactory:
    """Test middleware factory functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'test'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        self.logger_patcher = patch('netra_backend.app.logging_config.central_logger.get_logger')
        self.mock_logger = self.logger_patcher.start()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        self.logger_patcher.stop()

    def test_create_gcp_websocket_readiness_middleware_class(self):
        """Test creating middleware class for FastAPI."""
        middleware_class = create_gcp_websocket_readiness_middleware(timeout_seconds=45.0)
        assert middleware_class is not None
        assert issubclass(middleware_class, GCPWebSocketReadinessMiddleware)
        instance = middleware_class(None)
        assert instance.timeout_seconds == 45.0

    def test_create_gcp_websocket_readiness_middleware_instance(self):
        """Test creating middleware instance directly."""
        mock_app = Mock()
        middleware = create_gcp_websocket_readiness_middleware(mock_app, timeout_seconds=60.0)
        assert isinstance(middleware, GCPWebSocketReadinessMiddleware)
        assert middleware.timeout_seconds == 60.0

    def test_setup_gcp_websocket_protection(self):
        """Test setting up WebSocket protection on FastAPI app."""
        mock_app = Mock()
        with patch.object(mock_app, 'add_middleware') as mock_add_middleware:
            setup_gcp_websocket_protection(mock_app, timeout_seconds=30.0)
            mock_add_middleware.assert_called_once()
            args, kwargs = mock_add_middleware.call_args
            assert args[0] == GCPWebSocketReadinessMiddleware
            assert kwargs['timeout_seconds'] == 30.0

@pytest.mark.unit
class TestWebSocketReadinessHealthCheck:
    """Test health check integration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.env_patcher.start()
        self.logger_patcher = patch('netra_backend.app.logging_config.central_logger.get_logger')
        self.mock_logger = self.logger_patcher.start()

    def teardown_method(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        self.logger_patcher.stop()

    @pytest.mark.asyncio
    async def test_websocket_readiness_health_check_success(self):
        """Test health check when WebSocket is ready."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'staging'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        mock_app_state = Mock()
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
            mock_validator.return_value = (True, {'state': 'websocket_ready', 'failed_services': [], 'warnings': []})
            result = await websocket_readiness_health_check(mock_app_state)
            assert result['websocket_ready'] == True
            assert result['service'] == 'websocket_readiness'
            assert result['status'] == 'healthy'
            assert 'timestamp' in result

    @pytest.mark.asyncio
    async def test_websocket_readiness_health_check_failure(self):
        """Test health check when WebSocket is not ready."""
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {'ENVIRONMENT': 'production'}.get(key, default)
        self.mock_env.return_value = mock_env_manager
        mock_app_state = Mock()
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
            mock_validator.return_value = (False, {'state': 'failed', 'failed_services': ['agent_supervisor'], 'warnings': ['Service timeout']})
            result = await websocket_readiness_health_check(mock_app_state)
            assert result['websocket_ready'] == False
            assert result['status'] == 'degraded'
            assert 'agent_supervisor' in result['details']['failed_services']

    @pytest.mark.asyncio
    async def test_websocket_readiness_health_check_import_error(self):
        """Test health check when validator is not available."""
        mock_env_manager = Mock()
        self.mock_env.return_value = mock_env_manager
        mock_app_state = Mock()
        with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check', side_effect=ImportError('Module not found')):
            result = await websocket_readiness_health_check(mock_app_state)
            assert result['websocket_ready'] == True
            assert result['status'] == 'healthy'
            assert result['details']['validator_available'] == False
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')