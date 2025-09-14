#!/usr/bin/env python3
"""Debug script to understand middleware initialization."""

import sys
import os
from unittest.mock import Mock, patch
sys.path.append('/Users/anthony/Desktop/netra-apex')

# Mock the environment before importing
with patch('shared.isolated_environment.get_env') as mock_env:
    mock_env_manager = Mock()
    mock_env_manager.get.side_effect = lambda key, default='': {
        'ENVIRONMENT': 'staging',
        'GOOGLE_CLOUD_PROJECT': 'netra-staging',
        'K_SERVICE': 'netra-backend'
    }.get(key, default)
    mock_env.return_value = mock_env_manager
    
    # Mock logger
    with patch('netra_backend.app.logging_config.central_logger.get_logger'):
        from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
        
        middleware = GCPWebSocketReadinessMiddleware(None, timeout_seconds=30.0)
        
        print(f"Environment: {middleware.environment}")
        print(f"Is GCP Environment: {middleware.is_gcp_environment}")
        print(f"Is Cloud Run: {middleware.is_cloud_run}")
        print(f"Timeout: {middleware.timeout_seconds}")
        print(f"Cache duration: {middleware._cache_duration}")