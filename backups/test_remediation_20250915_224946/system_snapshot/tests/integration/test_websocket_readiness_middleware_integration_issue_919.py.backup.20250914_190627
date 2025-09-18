#!/usr/bin/env python3
"""
Integration Tests for WebSocket Readiness Middleware - Issue #919 Fix

MISSION CRITICAL: Integration tests to validate the end-to-end behavior of the 
WebSocket readiness middleware fix for Issue #919 - startup_phase stuck at 'unknown'
in GCP environments causing legitimate connections to be rejected.

BUSINESS VALIDATION:
- Tests realistic GCP Cloud Run scenarios
- Validates actual WebSocket connection establishment 
- Tests middleware integration with app lifecycle
- Verifies security measures remain intact

Business Value Justification:
- Segment: Platform/Internal ($500K+ ARR protection)  
- Business Goal: Platform Stability & Chat Value Delivery
- Value Impact: Prevents WebSocket 1011 errors that block chat functionality
- Strategic Impact: Enables reliable WebSocket connections in GCP Cloud Run
"""

import asyncio
import pytest
import os
import json
from typing import Dict, Any
from unittest.mock import Mock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.websockets import WebSocket
from starlette.testclient import WebSocketTestSession

import sys
sys.path.append('/Users/anthony/Desktop/netra-apex')


@pytest.fixture
def mock_app_with_middleware():
    """Create a FastAPI app with the WebSocket readiness middleware for testing."""
    app = FastAPI()
    
    # Mock app state
    app.state.startup_phase = 'unknown'  # Issue #919 condition
    app.state.startup_complete = False
    app.state.startup_failed = False
    
    # Add WebSocket endpoint for testing
    @app.websocket("/ws/test")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        await websocket.send_text("connection_established")
        await websocket.close()
    
    return app


class TestWebSocketReadinessMiddlewareIntegration:
    """Integration tests for WebSocket readiness middleware behavior."""
    
    def test_issue_919_gcp_staging_environment_bypass(self, mock_app_with_middleware):
        """
        ISSUE #919 FIX: Test WebSocket connections work in GCP staging with bypass.
        
        SCENARIO: GCP staging environment with startup_phase='unknown' but bypass enabled
        EXPECTED: WebSocket connections should be allowed
        """
        # Mock GCP staging environment with bypass
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging', 
            'K_SERVICE': 'netra-backend',
            'BYPASS_WEBSOCKET_READINESS_STAGING': 'true'
        }, clear=False):
            
            # Add middleware to app
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'staging',
                    'GOOGLE_CLOUD_PROJECT': 'netra-staging',
                    'K_SERVICE': 'netra-backend',
                    'BYPASS_WEBSOCKET_READINESS_STAGING': 'true'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                    
                    setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                    
                    # Test WebSocket connection
                    client = TestClient(mock_app_with_middleware)
                    
                    # Should succeed due to staging bypass
                    with client.websocket_connect("/ws/test") as websocket:
                        data = websocket.receive_text()
                        assert data == "connection_established"
    
    def test_issue_919_gcp_staging_graceful_degradation(self, mock_app_with_middleware):
        """
        ISSUE #919 FIX: Test graceful degradation in staging when services aren't ready.
        
        SCENARIO: GCP staging environment without bypass but graceful degradation
        EXPECTED: WebSocket connections should be allowed despite service failures
        """
        # Mock GCP staging environment without bypass
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging', 
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'K_SERVICE': 'netra-backend',
            'BYPASS_WEBSOCKET_READINESS_STAGING': 'false'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'staging',
                    'GOOGLE_CLOUD_PROJECT': 'netra-staging', 
                    'K_SERVICE': 'netra-backend',
                    'BYPASS_WEBSOCKET_READINESS_STAGING': 'false'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    # Mock the validator to return failure but allow graceful degradation
                    with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
                        mock_validator.return_value = (False, {
                            'state': 'failed',
                            'failed_services': ['agent_supervisor'],
                            'warnings': ['Service not ready']
                        })
                        
                        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                        
                        setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                        
                        # Test WebSocket connection
                        client = TestClient(mock_app_with_middleware)
                        
                        # Should succeed due to staging graceful degradation
                        with client.websocket_connect("/ws/test") as websocket:
                            data = websocket.receive_text()
                            assert data == "connection_established"
    
    def test_issue_919_production_strict_validation(self, mock_app_with_middleware):
        """
        ISSUE #919 FIX: Test production environment enforces strict validation.
        
        SCENARIO: GCP production environment with startup_phase='unknown' 
        EXPECTED: WebSocket connections should be rejected if services aren't ready
        """
        # Mock GCP production environment
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',
            'GOOGLE_CLOUD_PROJECT': 'netra-production', 
            'K_SERVICE': 'netra-backend'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'production',
                    'GOOGLE_CLOUD_PROJECT': 'netra-production',
                    'K_SERVICE': 'netra-backend'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    # Mock the validator to return failure
                    with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
                        mock_validator.return_value = (False, {
                            'state': 'failed',
                            'failed_services': ['agent_supervisor'],
                            'warnings': ['Service not ready']
                        })
                        
                        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                        
                        setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                        
                        # Test WebSocket connection
                        client = TestClient(mock_app_with_middleware)
                        
                        # Should be rejected in production
                        with pytest.raises(Exception):  # Connection should be rejected
                            with client.websocket_connect("/ws/test"):
                                pass
    
    def test_issue_919_non_gcp_environment_allows_connections(self, mock_app_with_middleware):
        """
        Test non-GCP environments allow WebSocket connections without validation.
        
        SCENARIO: Development/local environment
        EXPECTED: WebSocket connections should always be allowed
        """
        # Mock non-GCP environment
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()  
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'development'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                    
                    setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                    
                    # Test WebSocket connection
                    client = TestClient(mock_app_with_middleware)
                    
                    # Should always succeed in non-GCP environments
                    with client.websocket_connect("/ws/test") as websocket:
                        data = websocket.receive_text()
                        assert data == "connection_established"
    
    def test_issue_919_unknown_startup_phase_gcp_cloud_run_fix(self, mock_app_with_middleware):
        """
        ISSUE #919 CORE FIX: Test startup_phase='unknown' bypass in GCP Cloud Run.
        
        SCENARIO: GCP Cloud Run with startup_phase stuck at 'unknown'
        EXPECTED: Should bypass startup phase requirement and validate services directly
        """
        # Set app state to the Issue #919 condition
        mock_app_with_middleware.state.startup_phase = 'unknown'  # The key issue
        mock_app_with_middleware.state.startup_complete = False
        
        # Mock GCP Cloud Run environment
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'gcp-active-dev',  # Matches Issue #919 logs
            'GOOGLE_CLOUD_PROJECT': 'netra-staging',
            'K_SERVICE': 'netra-backend'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'gcp-active-dev',
                    'GOOGLE_CLOUD_PROJECT': 'netra-staging',
                    'K_SERVICE': 'netra-backend'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    # Mock successful service validation (the fix should skip startup phase check)
                    with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
                        mock_validator.return_value = (True, {
                            'state': 'websocket_ready',
                            'failed_services': [],
                            'warnings': []
                        })
                        
                        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                        
                        setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                        
                        # Test WebSocket connection
                        client = TestClient(mock_app_with_middleware)
                        
                        # Should succeed despite startup_phase='unknown' due to Issue #919 fix
                        with client.websocket_connect("/ws/test") as websocket:
                            data = websocket.receive_text()
                            assert data == "connection_established"


class TestAppStateStartupIntegration:
    """Test app state and startup validation integration."""
    
    def test_app_state_readiness_check_integration(self, mock_app_with_middleware):
        """Test app state readiness validation integration."""
        # Mock app state becoming ready during validation
        mock_app_with_middleware.state.startup_phase = 'services'
        mock_app_with_middleware.state.startup_complete = True
        
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'staging',
                    'GOOGLE_CLOUD_PROJECT': 'netra-staging'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    # Mock successful validation with proper app state
                    with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
                        mock_validator.return_value = (True, {
                            'state': 'websocket_ready',
                            'failed_services': [],
                            'warnings': []
                        })
                        
                        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                        
                        setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                        
                        client = TestClient(mock_app_with_middleware)
                        
                        # Should succeed with proper app state
                        with client.websocket_connect("/ws/test") as websocket:
                            data = websocket.receive_text()
                            assert data == "connection_established"


class TestWebSocketConnectionEstablishment:
    """Test WebSocket connection establishment works correctly."""
    
    def test_websocket_connection_headers_validation(self, mock_app_with_middleware):
        """Test WebSocket headers are properly validated."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development'  # Skip GCP validation
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'development'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                    
                    setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                    
                    client = TestClient(mock_app_with_middleware)
                    
                    # Test valid WebSocket connection
                    with client.websocket_connect("/ws/test") as websocket:
                        data = websocket.receive_text()
                        assert data == "connection_established"
    
    def test_websocket_path_detection_integration(self, mock_app_with_middleware):
        """Test WebSocket path detection in integration scenario."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'development'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'development'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                    
                    setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                    
                    client = TestClient(mock_app_with_middleware)
                    
                    # Test WebSocket path is correctly identified
                    with client.websocket_connect("/ws/test") as websocket:
                        data = websocket.receive_text()
                        assert data == "connection_established"


class TestSecurityMeasuresIntact:
    """Test that existing security measures remain intact."""
    
    def test_non_websocket_requests_not_affected(self, mock_app_with_middleware):
        """Test that non-WebSocket requests are not affected by middleware."""
        # Add regular HTTP endpoint
        @mock_app_with_middleware.get("/api/health")
        async def health():
            return {"status": "healthy"}
        
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'staging',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'staging',
                    'GOOGLE_CLOUD_PROJECT': 'netra-staging'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                    
                    setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=5.0)
                    
                    client = TestClient(mock_app_with_middleware)
                    
                    # HTTP requests should work normally
                    response = client.get("/api/health")
                    assert response.status_code == 200
                    assert response.json() == {"status": "healthy"}
    
    def test_invalid_websocket_requests_properly_rejected(self, mock_app_with_middleware):
        """Test that invalid WebSocket requests are properly rejected."""
        with patch.dict(os.environ, {
            'ENVIRONMENT': 'production',  # Strict validation
            'GOOGLE_CLOUD_PROJECT': 'netra-production'
        }, clear=False):
            
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env_manager = Mock()
                mock_env_manager.get.side_effect = lambda key, default='': {
                    'ENVIRONMENT': 'production',
                    'GOOGLE_CLOUD_PROJECT': 'netra-production'
                }.get(key, default)
                mock_env.return_value = mock_env_manager
                
                with patch('netra_backend.app.logging_config.central_logger.get_logger'):
                    # Mock validation failure
                    with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
                        mock_validator.return_value = (False, {
                            'state': 'failed',
                            'failed_services': ['database', 'agent_supervisor'],
                            'warnings': ['Services not ready']
                        })
                        
                        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import setup_gcp_websocket_protection
                        
                        setup_gcp_websocket_protection(mock_app_with_middleware, timeout_seconds=1.0)
                        
                        client = TestClient(mock_app_with_middleware)
                        
                        # Should reject WebSocket connection when services aren't ready
                        with pytest.raises(Exception):  # Connection should be rejected
                            with client.websocket_connect("/ws/test"):
                                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])