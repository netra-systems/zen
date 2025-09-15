#!/usr/bin/env python3
"""Debug production behavior to see why connections aren't being rejected"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch
sys.path.append('/Users/anthony/Desktop/netra-apex')

async def main():
    # Mock production environment exactly like the failing test
    with patch('shared.isolated_environment.get_env') as mock_env:
        mock_env_manager = Mock()
        mock_env_manager.get.side_effect = lambda key, default='': {
            'ENVIRONMENT': 'production',
            'GOOGLE_CLOUD_PROJECT': 'netra-production',
            'K_SERVICE': 'netra-backend'
        }.get(key, default)
        mock_env.return_value = mock_env_manager
        
        # Mock logger
        with patch('netra_backend.app.logging_config.central_logger.get_logger'):
            from netra_backend.app.middleware.gcp_websocket_readiness_middleware import GCPWebSocketReadinessMiddleware
            
            middleware = GCPWebSocketReadinessMiddleware(None)
            
            print(f"Middleware environment: {middleware.environment}")
            print(f"Middleware is_gcp_environment: {middleware.is_gcp_environment}")
            print(f"Middleware is_cloud_run: {middleware.is_cloud_run}")
            
            # Mock request with app exactly like the test
            mock_app_state = Mock()
            mock_app_state.startup_phase = 'unknown'
            mock_app_state.startup_complete = False
            mock_app_state.startup_failed = False
            
            mock_request = Mock()
            mock_request.app = Mock()
            mock_request.app.state = mock_app_state
            
            # Mock the GCP validator to return failure
            with patch('netra_backend.app.websocket_core.gcp_initialization_validator.gcp_websocket_readiness_check') as mock_validator:
                mock_validator.return_value = (False, {
                    'state': 'failed',
                    'failed_services': ['agent_supervisor'],
                    'warnings': ['Service not ready']
                })
                
                # Call the readiness check method
                ready, details = await middleware._check_websocket_readiness(mock_request)
                
                print(f"\nResults:")
                print(f"Ready: {ready}")
                print(f"Details: {details}")
                
                # Check what the middleware does with this result
                if ready:
                    print("🚨 ERROR: Production middleware is allowing connections when it shouldn't!")
                else:
                    print("✅ CORRECT: Production middleware is properly rejecting connections")

if __name__ == "__main__":
    asyncio.run(main())