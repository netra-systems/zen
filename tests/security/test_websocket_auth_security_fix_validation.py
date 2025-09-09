"""
WebSocket Authentication Security Fix Validation Tests

CRITICAL SECURITY VALIDATION: This test suite validates that our WebSocket
authentication security fix properly prevents automatic auth bypass for 
staging deployments while preserving E2E testing functionality.

Tests the specific security fix: 
- BEFORE: Staging deployments automatically bypassed auth
- AFTER: Only explicit environment variables enable E2E bypass
"""

import pytest
import unittest.mock
from unittest.mock import Mock, patch
import os
from typing import Dict, Any

# Import the function we need to test
from netra_backend.app.websocket_core.unified_websocket_auth import extract_e2e_context_from_websocket

class TestWebSocketAuthSecurityFix:
    """
    CRITICAL SECURITY VALIDATION: Test our WebSocket authentication security fix.
    
    This validates the specific change in extract_e2e_context_from_websocket()
    that prevents automatic auth bypass for staging deployments.
    """
    
    def test_staging_deployment_no_automatic_bypass(self):
        """
        CRITICAL SECURITY TEST: Verify staging deployments don't automatically bypass auth.
        
        BEFORE FIX: staging environment = automatic auth bypass
        AFTER FIX: staging environment alone = NO bypass (requires explicit E2E env vars)
        """
        # Mock a staging environment WITHOUT E2E environment variables
        staging_env = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging", 
            "K_SERVICE": "netra-backend-staging",
            # CRITICAL: No E2E environment variables set
        }
        
        # Mock WebSocket with staging headers but NO E2E markers
        mock_websocket = Mock()
        mock_websocket.headers = {
            "host": "staging.example.com",
            "user-agent": "production-client"
            # CRITICAL: No E2E test headers
        }
        
        with patch.dict('os.environ', staging_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # CRITICAL ASSERTION: Should NOT enable E2E bypass for staging without explicit E2E vars
            assert context is None or not context.get("is_e2e_testing", False), \
                "SECURITY VIOLATION: Staging deployment automatically enabled E2E bypass without explicit E2E env vars!"
            
            # Additional security check
            if context:
                assert not context.get("bypass_enabled", False), \
                    "SECURITY VIOLATION: Auth bypass enabled for staging without E2E environment variables!"

    def test_staging_with_explicit_e2e_env_allows_bypass(self):
        """
        Verify that staging WITH explicit E2E environment variables still allows bypass.
        This ensures our fix doesn't break legitimate E2E testing.
        """
        # Mock a staging environment WITH explicit E2E environment variables
        staging_e2e_env = {
            "ENVIRONMENT": "staging",
            "GOOGLE_CLOUD_PROJECT": "netra-staging", 
            "K_SERVICE": "netra-backend-staging",
            # CRITICAL: Explicit E2E environment variables
            "E2E_TESTING": "1",
            "E2E_OAUTH_SIMULATION_KEY": "test-key-123"
        }
        
        # Mock WebSocket with E2E test headers
        mock_websocket = Mock()
        mock_websocket.headers = {
            "host": "staging.example.com",
            "x-test-type": "E2E",
            "x-e2e-test": "true"
        }
        
        with patch.dict('os.environ', staging_e2e_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Should enable E2E bypass when explicit E2E env vars are present
            assert context is not None, "E2E context should be created with explicit E2E environment variables"
            assert context.get("is_e2e_testing", False), "E2E testing should be enabled with explicit env vars"

    def test_production_deployment_never_bypasses(self):
        """
        Verify production deployments NEVER enable auth bypass, regardless of environment variables.
        """
        # Mock a production environment with E2E env vars (should still deny)
        production_env = {
            "ENVIRONMENT": "production",
            "GOOGLE_CLOUD_PROJECT": "netra-prod", 
            "K_SERVICE": "netra-backend-prod",
            # Even with E2E env vars, production should deny
            "E2E_TESTING": "1",
            "E2E_OAUTH_SIMULATION_KEY": "test-key-123"
        }
        
        mock_websocket = Mock()
        mock_websocket.headers = {
            "host": "prod.example.com",
            "x-test-type": "E2E"
        }
        
        with patch.dict('os.environ', production_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # CRITICAL: Production should NEVER allow E2E bypass
            assert context is None or not context.get("is_e2e_testing", False), \
                "SECURITY VIOLATION: Production deployment enabled E2E bypass!"

    def test_concurrent_e2e_detection_works(self):
        """
        Verify concurrent E2E detection still works (race condition fix).
        """
        # Mock environment with concurrent test markers
        concurrent_env = {
            "ENVIRONMENT": "test",
            "PYTEST_XDIST_WORKER": "gw0",
            "PYTEST_CURRENT_TEST": "test_concurrent_websockets.py::test_multiple_connections"
        }
        
        mock_websocket = Mock()
        mock_websocket.headers = {}
        
        with patch.dict('os.environ', concurrent_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Should enable E2E for concurrent testing scenarios
            assert context is not None, "Concurrent E2E context should be created"
            assert context.get("is_e2e_testing", False), "Concurrent E2E testing should be enabled"

    def test_local_development_bypass_still_works(self):
        """
        Verify local development E2E bypass still works.
        """
        # Mock local development environment
        local_env = {
            "ENVIRONMENT": "development",
            "E2E_TESTING": "1"
        }
        
        mock_websocket = Mock()
        mock_websocket.headers = {
            "x-test-mode": "true"
        }
        
        with patch.dict('os.environ', local_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Local development should allow E2E bypass
            assert context is not None, "Local E2E context should be created"
            assert context.get("is_e2e_testing", False), "Local E2E testing should be enabled"

    def test_no_environment_variables_no_bypass(self):
        """
        Verify that without any E2E environment variables, no bypass is enabled.
        """
        # Mock environment with NO E2E variables
        clean_env = {
            "ENVIRONMENT": "staging",  # Even in staging
            "GOOGLE_CLOUD_PROJECT": "netra-staging"
            # NO E2E environment variables
        }
        
        mock_websocket = Mock()
        mock_websocket.headers = {}
        
        with patch.dict('os.environ', clean_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Should NOT enable bypass without explicit E2E env vars
            assert context is None or not context.get("is_e2e_testing", False), \
                "Auth bypass should not be enabled without explicit E2E environment variables"


class TestWebSocketAuthSecurityRegression:
    """
    Regression tests to ensure the security fix doesn't break existing functionality.
    """
    
    def test_websocket_headers_e2e_detection_preserved(self):
        """
        Ensure WebSocket header-based E2E detection still works.
        """
        mock_websocket = Mock()
        mock_websocket.headers = {
            "x-test-type": "E2E",
            "x-e2e-test": "true",
            "x-test-environment": "staging"
        }
        
        # Even with minimal environment
        minimal_env = {"ENVIRONMENT": "test"}
        
        with patch.dict('os.environ', minimal_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Header-based E2E detection should still work
            assert context is not None, "Header-based E2E detection should work"
            
    def test_multiple_e2e_detection_methods_work_together(self):
        """
        Ensure multiple E2E detection methods work together correctly.
        """
        # Environment with both env vars and headers
        combined_env = {
            "ENVIRONMENT": "test",
            "E2E_TESTING": "1",
            "PYTEST_RUNNING": "1"
        }
        
        mock_websocket = Mock()
        mock_websocket.headers = {
            "x-test-mode": "true",
            "x-e2e-test": "true"
        }
        
        with patch.dict('os.environ', combined_env, clear=True):
            context = extract_e2e_context_from_websocket(mock_websocket)
            
            # Combined detection should work
            assert context is not None, "Combined E2E detection should work"
            assert context.get("is_e2e_testing", False), "Combined E2E should enable testing mode"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])