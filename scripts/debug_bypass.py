#!/usr/bin/env python3
"""Debug the staging bypass behavior"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch
sys.path.append('/Users/anthony/Desktop/netra-apex')

async def main():
    # Mock environment
    with patch('shared.isolated_environment.get_env') as mock_env:
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {
            'ENVIRONMENT': 'staging',
            'BYPASS_WEBSOCKET_READINESS_STAGING': 'true',
            'GOOGLE_CLOUD_PROJECT': 'netra-staging'
        }.get(key, default)
        mock_env.return_value = mock_env_manager
        
        # Mock logger
        with patch('netra_backend.app.logging_config.central_logger.get_logger'):
            from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
            
            middleware = GCPWebSocketReadinessMiddleware(None)
            
            # Mock request with app
            mock_request = Mock()
            mock_app_state = Mock()
            mock_app_state.startup_phase = 'unknown'
            mock_app_state.startup_complete = False
            mock_app_state.startup_failed = False
            mock_request.app = Mock()
            mock_request.app.state = mock_app_state
            
            # Call the readiness check method
            ready, details = await middleware._check_websocket_readiness(mock_request)
            
            print(f"Ready: {ready}")
            print(f"Details: {details}")
            if 'bypass_reason' in details:
                print(f"Bypass reason: {details['bypass_reason']}")

if __name__ == "__main__":
    asyncio.run(main())