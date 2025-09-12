"""
System User Authentication Failure Reproduction Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal (System Stability)
- Business Goal: Document and reproduce critical authentication failures
- Value Impact: Provides concrete evidence of authentication configuration gaps
- Strategic Impact: Essential for validating fixes and preventing regression

These tests MUST FAIL initially to prove the issue exists.
Based on GitHub Issue #115: Critical System User Authentication Failure Blocking Golden Path

Root Cause: Missing SERVICE_ID and SERVICE_SECRET in docker-compose.staging.yml backend service
Expected Failure: 403 'Not authenticated' errors for system user operations
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from shared.isolated_environment import get_env


class TestSystemUserAuthFailureReproduction:
    """Reproduce the exact authentication failure scenarios from Issue #115."""
    
    def test_missing_service_id_causes_auth_failure(self):
        """Test that missing SERVICE_ID causes authentication failures.
        
        This test MUST FAIL initially - it proves SERVICE_ID is not configured.
        
        Expected Failure: AssertionError showing SERVICE_ID is None or not 'netra-backend'
        After Fix: This test should PASS when SERVICE_ID=netra-backend is added
        """
        env = get_env()
        
        # This should fail because SERVICE_ID is not set in staging backend
        service_id = env.get("SERVICE_ID")
        
        # CRITICAL: This assertion MUST FAIL to demonstrate the issue
        assert service_id == "netra-backend", (
            f"SERVICE_ID is not configured. Expected 'netra-backend', got '{service_id}'. "
            f"This proves the issue exists - SERVICE_ID must be added to docker-compose.staging.yml backend service. "
            f"See Issue #115 for details."
        )
    
    def test_missing_service_secret_causes_auth_failure(self):
        """Test that missing SERVICE_SECRET causes authentication failures.
        
        This test MUST FAIL initially - it proves SERVICE_SECRET is not configured.
        
        Expected Failure: AssertionError showing SERVICE_SECRET is None
        After Fix: This test should PASS when SERVICE_SECRET is added
        """
        env = get_env()
        
        # This should fail because SERVICE_SECRET is not set in staging backend
        service_secret = env.get("SERVICE_SECRET")
        
        # CRITICAL: This assertion MUST FAIL to demonstrate the issue
        assert service_secret is not None, (
            f"SERVICE_SECRET is not configured. Got None. "
            f"This proves the issue exists - SERVICE_SECRET must be added to docker-compose.staging.yml backend service. "
            f"See Issue #115 for configuration requirements."
        )
        
        assert len(service_secret) >= 32, (
            f"SERVICE_SECRET must be at least 32 characters for security. "
            f"Got length {len(service_secret) if service_secret else 0}. "
            f"Expected minimum 32 characters."
        )
    
    def test_service_auth_header_generation_fails_without_config(self):
        """Test that auth header generation fails without proper SERVICE_ID/SECRET.
        
        This test MUST FAIL initially - it demonstrates the auth client failure.
        
        Expected Failure: Exception during auth header generation
        After Fix: This test should PASS when SERVICE_ID/SECRET are configured
        """
        # Clear environment to simulate missing configuration
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()  # Clear all environment variables
            
            # This should fail because auth client can't generate headers
            with pytest.raises(Exception) as exc_info:
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                auth_client = AuthServiceClient()
                headers = auth_client._get_service_auth_headers()
            
            # Verify the failure is due to missing configuration
            error_msg = str(exc_info.value).lower()
            assert any(keyword in error_msg for keyword in [
                'service_id', 'service_secret', 'not configured', 'missing', 'required'
            ]), (
                f"Expected authentication configuration error mentioning SERVICE_ID or SERVICE_SECRET, "
                f"got: {exc_info.value}. This proves the configuration dependency."
            )
    
    def test_system_user_context_fails_with_invalid_auth(self):
        """Test that system user operations fail with invalid authentication.
        
        This test MUST FAIL initially - it demonstrates the dependencies.py failure.
        
        Expected Failure: 403 'Not authenticated' error from dependencies.py
        After Fix: This test should PASS when authentication is properly configured
        """
        # Mock the exact scenario from dependencies.py where user_id='system'
        user_id = "system"
        
        # Without proper SERVICE_ID/SECRET, system user auth should fail
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()
            
            # Try to create system context - this should fail
            with pytest.raises(Exception) as exc_info:
                from netra_backend.app.dependencies import get_request_scoped_db_session
                # This will fail when it tries to authenticate system user
                session_gen = get_request_scoped_db_session()
                session = next(session_gen)
            
            # Verify it's an authentication failure (the exact issue from Issue #115)
            error_msg = str(exc_info.value).lower()
            assert any(keyword in error_msg for keyword in [
                '403', 'not authenticated', 'unauthorized', 'authentication failed'
            ]), (
                f"Expected 403 authentication error (the exact issue described in Issue #115), "
                f"got: {exc_info.value}. This should reproduce the 'Not authenticated' error."
            )
    
    def test_docker_compose_staging_config_missing_service_auth(self):
        """Test that validates the exact docker-compose.staging.yml configuration issue.
        
        This test MUST FAIL initially - it proves the config gap in docker-compose.staging.yml.
        
        Expected Failure: AssertionError showing SERVICE_ID/SECRET missing from backend environment
        After Fix: This test should PASS when the configuration is added
        """
        import yaml
        
        # Read the actual docker-compose.staging.yml file
        staging_compose_path = "/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml"
        
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Get backend service environment variables
        backend_env = compose_config['services']['backend']['environment']
        
        # These assertions MUST FAIL to prove the configuration issue from Issue #115
        assert 'SERVICE_ID' in backend_env, (
            "SERVICE_ID is missing from docker-compose.staging.yml backend service environment. "
            "This proves the root cause identified in Issue #115 - SERVICE_ID must be added to backend environment."
        )
        
        assert 'SERVICE_SECRET' in backend_env, (
            "SERVICE_SECRET is missing from docker-compose.staging.yml backend service environment. "
            "This proves the root cause identified in Issue #115 - SERVICE_SECRET must be added to backend environment."
        )
        
        # If we reach here, the configuration is correct (test should pass after fix)
        if 'SERVICE_ID' in backend_env:
            assert backend_env['SERVICE_ID'] == 'netra-backend', (
                f"SERVICE_ID should be 'netra-backend', got: {backend_env.get('SERVICE_ID')}"
            )
    
    def test_service_auth_client_initialization_fails_without_config(self):
        """Test that AuthServiceClient initialization fails without proper configuration.
        
        This test validates the specific auth client component that's failing.
        
        Expected Failure: Configuration validation error during client initialization
        After Fix: This test should PASS when SERVICE_ID/SECRET are available
        """
        # Clear service configuration to reproduce the issue
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()
            
            # Try to initialize AuthServiceClient - should fail without config
            with pytest.raises(Exception) as exc_info:
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                auth_client = AuthServiceClient()
                # Force validation by trying to access service_id
                _ = auth_client.service_id
            
            # Verify the failure is configuration-related
            error_msg = str(exc_info.value).lower()
            config_error_keywords = [
                'service_id', 'service_secret', 'not configured', 'missing', 
                'required', 'environment', 'config'
            ]
            
            assert any(keyword in error_msg for keyword in config_error_keywords), (
                f"Expected configuration error mentioning SERVICE_ID or SERVICE_SECRET setup, "
                f"got: {exc_info.value}. This demonstrates the auth client dependency on proper configuration."
            )


class TestServiceAuthConfigurationValidation:
    """Additional validation tests for service authentication configuration."""
    
    def test_auth_service_client_requires_both_id_and_secret(self):
        """Test that auth client requires both SERVICE_ID and SERVICE_SECRET.
        
        This test validates the complete configuration requirements.
        """
        test_cases = [
            {"SERVICE_ID": "netra-backend", "SERVICE_SECRET": None},  # Missing SECRET
            {"SERVICE_ID": None, "SERVICE_SECRET": "test-secret"},     # Missing ID
            {"SERVICE_ID": "", "SERVICE_SECRET": "test-secret"},       # Empty ID
            {"SERVICE_ID": "netra-backend", "SERVICE_SECRET": ""},     # Empty SECRET
        ]
        
        for case in test_cases:
            with patch.dict(os.environ, case, clear=True):
                env = get_env()
                
                # Each incomplete configuration should cause issues
                with pytest.raises(Exception) as exc_info:
                    from netra_backend.app.clients.auth_client_core import AuthServiceClient
                    auth_client = AuthServiceClient()
                    headers = auth_client._get_service_auth_headers()
                
                # Verify it's a configuration issue
                error_msg = str(exc_info.value).lower()
                assert any(keyword in error_msg for keyword in [
                    'service_id', 'service_secret', 'missing', 'required', 'not configured'
                ]), f"Expected configuration error for case {case}, got: {exc_info.value}"
    
    def test_dependencies_system_user_hardcoded_value_issue(self):
        """Test that highlights the hardcoded 'system' user_id in dependencies.py.
        
        This test documents the specific location where the authentication failure occurs.
        """
        # This test documents the exact line in dependencies.py that causes the issue
        from netra_backend.app.dependencies import get_request_scoped_db_session
        
        # Without proper service authentication, the hardcoded user_id="system" fails
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()
            
            # The function hardcodes user_id = "system" at line ~185
            # This causes 403 errors when SERVICE_ID/SECRET are missing
            with pytest.raises(Exception) as exc_info:
                session_gen = get_request_scoped_db_session()
                session = next(session_gen)
            
            # This proves the connection between missing config and the 403 error
            error_msg = str(exc_info.value)
            assert "403" in error_msg or "Not authenticated" in error_msg or "authentication" in error_msg.lower(), (
                f"Expected authentication-related error from dependencies.py system user context, "
                f"got: {exc_info.value}. This is the exact issue described in Issue #115."
            )


if __name__ == "__main__":
    # Run these tests to reproduce Issue #115
    # Expected: All tests should FAIL initially, proving the issue exists
    # After fix: All tests should PASS, proving the issue is resolved
    
    print("[U+1F534] Running Issue #115 Reproduction Tests")
    print("Expected: ALL TESTS SHOULD FAIL to prove the issue exists")
    print("After fix: All tests should PASS to prove resolution")
    print("=" * 60)
    
    pytest.main([__file__, "-v", "--tb=short"])