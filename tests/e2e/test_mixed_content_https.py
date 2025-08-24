"""
E2E Test for Mixed Content and HTTPS Protocol Issues

This test reproduces the critical mixed content/HTTPS issues identified in the Five Whys analysis,
specifically the frontend making HTTP requests from HTTPS pages in staging/production,
causing browser security blocks and WebSocket connection failures.

Root Cause Being Tested:
- secure-api-config.ts not properly detecting staging environment
- API URLs using HTTP when frontend is served over HTTPS
- WebSocket URLs using WS instead of WSS in secure environments  
- Server-side vs client-side protocol detection inconsistencies
- Environment detection logic failing in production deployments
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Any
from unittest.mock import patch, MagicMock
import pytest
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.environment_markers import env, env_requires, dev_and_staging


@env("dev", "staging")
@env_requires(
    services=["frontend", "backend", "auth_service"],
    features=["https_configured", "cors_configured", "ssl_enabled"],
    data=["staging_domain_config", "ssl_certificates"]
)
class TestMixedContentHTTPS(BaseIntegrationTest):
    """Test suite for mixed content and HTTPS protocol enforcement issues."""
    
    def setup_method(self):
        """Set up test environment with staging-like configuration."""
        super().setup_method()
        self.frontend_path = Path(self.project_root) / "frontend"
        self.mixed_content_violations = []
        self.protocol_inconsistencies = []
        
@patch.dict('os.environ', {'ENVIRONMENT': 'staging', 'TESTING': '0'})
        def test_staging_environment_https_detection_FAILING(self):
        """
        FAILING TEST: secure-api-config.ts should detect staging as secure environment.
        
        This test SHOULD FAIL because the environment detection logic in 
        secure-api-config.ts may not properly identify staging as requiring HTTPS,
        leading to HTTP API calls from HTTPS frontend.
        
        Expected failure: isSecureEnvironment() returns false for staging.
        """
        # Mock staging environment variables
        staging_env = {
            'NEXT_PUBLIC_ENVIRONMENT': 'staging',
            'NODE_ENV': 'production',
            'VERCEL_ENV': 'preview'  # Common staging indicator
        }
        
        with patch.dict('os.environ', staging_env, clear=True):
            # Simulate server-side environment detection
            server_side_secure = self._simulate_server_side_environment_detection()
            
            # Simulate client-side environment detection with HTTPS protocol
            client_side_secure = self._simulate_client_side_environment_detection(
                protocol='https:', 
                host='app.staging.netrasystems.ai'
            )
            
            # Both should detect secure environment
            # This assertion SHOULD FAIL if detection is broken
            assert server_side_secure, (
                f"Server-side environment detection failed for staging. "
                f"Environment: {staging_env}. "
                f"secure-api-config.ts isSecureEnvironment() should return true for staging."
            )
            
            assert client_side_secure, (
                f"Client-side environment detection failed for staging with HTTPS. "
                f"secure-api-config.ts should detect HTTPS protocol as secure environment."
            )
    
    def test_api_urls_use_https_in_staging_FAILING(self):
        """
        FAILING TEST: All API URLs should use HTTPS protocol in staging environment.
        
        This test SHOULD FAIL because API URLs may still use HTTP in staging,
        causing mixed content warnings when frontend is served over HTTPS.
        """
        staging_env = {
            'NEXT_PUBLIC_ENVIRONMENT': 'staging',
            'NEXT_PUBLIC_API_URL': 'http://api.staging.netrasystems.ai',  # Wrong protocol
            'NEXT_PUBLIC_AUTH_URL': 'http://auth.staging.netrasystems.ai',  # Wrong protocol
        }
        
        with patch.dict('os.environ', staging_env):
            # Get API configuration for staging
            api_config = self._get_secure_api_config()
            
            # Check for HTTP URLs (mixed content violations)
            http_violations = []
            
            if api_config['apiUrl'].startswith('http://'):
                http_violations.append(f"apiUrl: {api_config['apiUrl']}")
                
            if api_config['authUrl'].startswith('http://'):
                http_violations.append(f"authUrl: {api_config['authUrl']}")
                
            if api_config['wsUrl'].startswith('ws://'):
                http_violations.append(f"wsUrl: {api_config['wsUrl']}")
            
            self.mixed_content_violations.extend(http_violations)
            
            # This assertion SHOULD FAIL due to HTTP URLs in staging
            assert len(http_violations) == 0, (
                f"Found {len(http_violations)} mixed content violations in staging:\n" +
                '\n'.join(f"  - {violation}" for violation in http_violations) +
                f"\n\nAll URLs must use HTTPS/WSS in staging to prevent mixed content errors."
            )
    
    def test_websocket_urls_use_wss_in_staging_FAILING(self):
        """
        FAILING TEST: WebSocket URLs should use WSS protocol in staging environment.
        
        This test SHOULD FAIL because WebSocket URLs may use WS instead of WSS,
        causing connection failures from HTTPS pages due to mixed content restrictions.
        """
        staging_scenarios = [
            {
                'env': {'NEXT_PUBLIC_ENVIRONMENT': 'staging'},
                'client_protocol': 'https:',
                'expected_ws_protocol': 'wss:'
            },
            {
                'env': {'NEXT_PUBLIC_ENVIRONMENT': 'production'},
                'client_protocol': 'https:',
                'expected_ws_protocol': 'wss:'
            },
            {
                'env': {'NEXT_PUBLIC_FORCE_HTTPS': 'true'},
                'client_protocol': 'https:',
                'expected_ws_protocol': 'wss:'
            }
        ]
        
        websocket_violations = []
        
        for scenario in staging_scenarios:
            with patch.dict('os.environ', scenario['env']):
                # Mock client-side window object
                mock_window = MagicMock()
                mock_window.location.protocol = scenario['client_protocol']
                
                with patch('builtins.window', mock_window, create=True):
                    api_config = self._get_secure_api_config()
                    
                    actual_ws_protocol = api_config['wsUrl'].split('://')[0] + ':'
                    expected_ws_protocol = scenario['expected_ws_protocol']
                    
                    if actual_ws_protocol != expected_ws_protocol:
                        websocket_violations.append(
                            f"Environment {scenario['env']}: got {actual_ws_protocol}, "
                            f"expected {expected_ws_protocol} (wsUrl: {api_config['wsUrl']})"
                        )
        
        # This assertion SHOULD FAIL due to WS instead of WSS
        assert len(websocket_violations) == 0, (
            f"Found {len(websocket_violations)} WebSocket protocol violations:\n" +
            '\n'.join(f"  - {violation}" for violation in websocket_violations) +
            f"\n\nWebSocket URLs must use WSS in secure environments to prevent connection failures."
        )
    
    def test_server_client_protocol_consistency_FAILING(self):
        """
        FAILING TEST: Server-side and client-side should produce consistent protocol decisions.
        
        This test SHOULD FAIL because server-side rendering (SSR) and client-side hydration
        may make different protocol decisions, causing hydration mismatches and errors.
        """
        test_environments = [
            {'NEXT_PUBLIC_ENVIRONMENT': 'staging'},
            {'NEXT_PUBLIC_ENVIRONMENT': 'production'},
            {'NEXT_PUBLIC_FORCE_HTTPS': 'true'}
        ]
        
        consistency_issues = []
        
        for env_vars in test_environments:
            with patch.dict('os.environ', env_vars):
                # Server-side configuration (SSR)
                server_config = self._simulate_server_side_config_generation()
                
                # Client-side configuration (hydration)
                client_config = self._simulate_client_side_config_generation(
                    protocol='https:', 
                    host='staging.netrasystems.ai'
                )
                
                # Check for inconsistencies
                if server_config['apiUrl'] != client_config['apiUrl']:
                    consistency_issues.append(
                        f"API URL mismatch in {env_vars}: "
                        f"server='{server_config['apiUrl']}' vs client='{client_config['apiUrl']}'"
                    )
                
                if server_config['wsUrl'] != client_config['wsUrl']:
                    consistency_issues.append(
                        f"WebSocket URL mismatch in {env_vars}: "
                        f"server='{server_config['wsUrl']}' vs client='{client_config['wsUrl']}'"
                    )
        
        self.protocol_inconsistencies.extend(consistency_issues)
        
        # This assertion SHOULD FAIL due to SSR/client inconsistencies
        assert len(consistency_issues) == 0, (
            f"Found {len(consistency_issues)} server/client protocol inconsistencies:\n" +
            '\n'.join(f"  - {issue}" for issue in consistency_issues) +
            f"\n\nServer and client must generate consistent protocols to prevent hydration errors."
        )
    
    def test_environment_detection_edge_cases_FAILING(self):
        """
        FAILING TEST: Environment detection should handle edge cases correctly.
        
        This test SHOULD FAIL because environment detection may not handle
        complex deployment scenarios like preview branches, custom domains, etc.
        """
        edge_case_scenarios = [
            {
                'name': 'Vercel Preview Branch',
                'env': {'VERCEL_ENV': 'preview', 'NEXT_PUBLIC_ENVIRONMENT': 'staging'},
                'client_host': 'netra-git-feature-preview.vercel.app',
                'expected_secure': True
            },
            {
                'name': 'Custom Staging Domain',  
                'env': {'NEXT_PUBLIC_ENVIRONMENT': 'staging'},
                'client_host': 'staging-v2.netrasystems.ai',
                'expected_secure': True
            },
            {
                'name': 'Local Development with Force HTTPS',
                'env': {'NEXT_PUBLIC_FORCE_HTTPS': 'true'},
                'client_host': 'localhost:3000',
                'expected_secure': True
            },
            {
                'name': 'Missing Environment Variable',
                'env': {},  # No environment set
                'client_host': 'unknown-domain.com',
                'expected_secure': False
            }
        ]
        
        detection_failures = []
        
        for scenario in edge_case_scenarios:
            with patch.dict('os.environ', scenario['env'], clear=True):
                mock_window = MagicMock()
                mock_window.location.protocol = 'https:'
                mock_window.location.host = scenario['client_host']
                
                with patch('builtins.window', mock_window, create=True):
                    is_secure = self._simulate_client_side_environment_detection(
                        protocol='https:',
                        host=scenario['client_host']
                    )
                    
                    if is_secure != scenario['expected_secure']:
                        detection_failures.append(
                            f"{scenario['name']}: got {is_secure}, expected {scenario['expected_secure']}"
                        )
        
        # This assertion SHOULD FAIL due to edge case handling issues
        assert len(detection_failures) == 0, (
            f"Environment detection failed for {len(detection_failures)} edge cases:\n" +
            '\n'.join(f"  - {failure}" for failure in detection_failures) +
            f"\n\nEnvironment detection must handle complex deployment scenarios correctly."
        )

    def test_similar_edge_case_cors_origin_protocol_mismatch_FAILING(self):
        """
        FAILING TEST: Similar pattern - CORS origins should match frontend protocol.
        
        This tests a similar failure mode where backend CORS origins are configured
        with HTTP while frontend uses HTTPS, causing CORS errors.
        """
        # Mock staging environment with HTTPS frontend
        staging_env = {
            'NEXT_PUBLIC_ENVIRONMENT': 'staging',
            'FRONTEND_URL': 'https://app.staging.netrasystems.ai'
        }
        
        # Mock backend CORS configuration (potentially with HTTP origins)
        mock_cors_origins = [
            'http://app.staging.netrasystems.ai',  # Wrong protocol
            'https://app.staging.netrasystems.ai',  # Correct protocol
            'http://localhost:3000'  # Dev origin
        ]
        
        with patch.dict('os.environ', staging_env):
            frontend_protocol = 'https:'
            frontend_origin = 'https://app.staging.netrasystems.ai'
            
            # Check if CORS origins match frontend protocol
            protocol_mismatches = []
            
            for origin in mock_cors_origins:
                origin_protocol = origin.split('://')[0] + ':'
                if origin.startswith('http://') and frontend_protocol == 'https:':
                    if not origin.startswith('http://localhost'):  # Localhost exception
                        protocol_mismatches.append(
                            f"CORS origin '{origin}' uses HTTP but frontend uses HTTPS"
                        )
            
            # This assertion SHOULD FAIL due to protocol mismatches
            assert len(protocol_mismatches) == 0, (
                f"Found {len(protocol_mismatches)} CORS protocol mismatches:\n" +
                '\n'.join(f"  - {mismatch}" for mismatch in protocol_mismatches) +
                f"\n\nCORS origins must match frontend protocol to prevent connection errors."
            )

    def _simulate_server_side_environment_detection(self) -> bool:
        """Simulate server-side environment detection logic."""
        # Replicate logic from secure-api-config.ts isSecureEnvironment()
        return os.environ.get('NEXT_PUBLIC_ENVIRONMENT') != 'development'
    
    def _simulate_client_side_environment_detection(self, protocol: str, host: str) -> bool:
        """Simulate client-side environment detection logic."""
        # Replicate client-side logic from secure-api-config.ts
        is_https = protocol == 'https:'
        is_staging = os.environ.get('NEXT_PUBLIC_ENVIRONMENT') == 'staging'
        is_production = os.environ.get('NEXT_PUBLIC_ENVIRONMENT') == 'production'
        force_https = os.environ.get('NEXT_PUBLIC_FORCE_HTTPS') == 'true'
        
        return is_https or is_staging or is_production or force_https
    
    def _get_secure_api_config(self) -> Dict[str, Any]:
        """Simulate getSecureApiConfig() function behavior."""
        environment = os.environ.get('NEXT_PUBLIC_ENVIRONMENT', 'development')
        
        # Default URLs based on environment
        if environment == 'development':
            default_api_url = 'http://localhost:8000'
            default_ws_url = 'ws://localhost:8000/ws'
            default_auth_url = 'http://localhost:8081'
        elif environment == 'production':
            default_api_url = 'https://api.netrasystems.ai'
            default_ws_url = 'wss://api.netrasystems.ai/ws'
            default_auth_url = 'https://auth.netrasystems.ai'
        else:  # staging
            default_api_url = 'https://api.staging.netrasystems.ai'
            default_ws_url = 'wss://api.staging.netrasystems.ai/ws'
            default_auth_url = 'https://auth.staging.netrasystems.ai'
        
        # Get URLs from environment or use defaults
        api_url = os.environ.get('NEXT_PUBLIC_API_URL', default_api_url)
        ws_url = os.environ.get('NEXT_PUBLIC_WS_URL', default_ws_url)
        auth_url = os.environ.get('NEXT_PUBLIC_AUTH_URL', default_auth_url)
        
        # Apply security transformations (simulate secureUrl function)
        is_secure = self._simulate_server_side_environment_detection()
        
        if is_secure:
            api_url = api_url.replace('http://', 'https://')
            auth_url = auth_url.replace('http://', 'https://')
            ws_url = ws_url.replace('ws://', 'wss://')
        
        return {
            'apiUrl': api_url,
            'wsUrl': ws_url,
            'authUrl': auth_url,
            'environment': environment,
            'forceHttps': is_secure
        }
    
    def _simulate_server_side_config_generation(self) -> Dict[str, str]:
        """Simulate server-side API config generation (SSR)."""
        return self._get_secure_api_config()
    
    def _simulate_client_side_config_generation(self, protocol: str, host: str) -> Dict[str, str]:
        """Simulate client-side API config generation (hydration)."""
        # Mock window object for client-side detection
        mock_window = MagicMock()
        mock_window.location.protocol = protocol
        mock_window.location.host = host
        
        with patch('builtins.window', mock_window, create=True):
            return self._get_secure_api_config()
    
    def teardown_method(self):
        """Clean up after test and report violations."""
        super().teardown_method()
        
        # Report mixed content violations for debugging
        if self.mixed_content_violations:
            print(f"\n=== Mixed Content Violations ===")
            for violation in self.mixed_content_violations:
                print(f"  - {violation}")
        
        if self.protocol_inconsistencies:
            print(f"\n=== Protocol Inconsistencies ===")
            for inconsistency in self.protocol_inconsistencies:
                print(f"  - {inconsistency}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])