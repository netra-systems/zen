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

@pytest.mark.unit
class SystemUserAuthFailureReproductionTests:
    """Reproduce the exact authentication failure scenarios from Issue #115."""

    def test_missing_service_id_causes_auth_failure(self):
        """Test that missing SERVICE_ID causes authentication failures.
        
        This test MUST FAIL initially - it proves SERVICE_ID is not configured.
        
        Expected Failure: AssertionError showing SERVICE_ID is None or not 'netra-backend'
        After Fix: This test should PASS when SERVICE_ID=netra-backend is added
        """
        env = get_env()
        service_id = env.get('SERVICE_ID')
        assert service_id == 'netra-backend', f"SERVICE_ID is not configured. Expected 'netra-backend', got '{service_id}'. This proves the issue exists - SERVICE_ID must be added to docker-compose.staging.yml backend service. See Issue #115 for details."

    def test_missing_service_secret_causes_auth_failure(self):
        """Test that missing SERVICE_SECRET causes authentication failures.
        
        This test MUST FAIL initially - it proves SERVICE_SECRET is not configured.
        
        Expected Failure: AssertionError showing SERVICE_SECRET is None
        After Fix: This test should PASS when SERVICE_SECRET is added
        """
        env = get_env()
        service_secret = env.get('SERVICE_SECRET')
        assert service_secret is not None, f'SERVICE_SECRET is not configured. Got None. This proves the issue exists - SERVICE_SECRET must be added to docker-compose.staging.yml backend service. See Issue #115 for configuration requirements.'
        assert len(service_secret) >= 32, f'SERVICE_SECRET must be at least 32 characters for security. Got length {(len(service_secret) if service_secret else 0)}. Expected minimum 32 characters.'

    def test_service_auth_header_generation_fails_without_config(self):
        """Test that auth header generation fails without proper SERVICE_ID/SECRET.
        
        This test MUST FAIL initially - it demonstrates the auth client failure.
        
        Expected Failure: Exception during auth header generation
        After Fix: This test should PASS when SERVICE_ID/SECRET are configured
        """
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()
            with pytest.raises(Exception) as exc_info:
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                auth_client = AuthServiceClient()
                headers = auth_client._get_service_auth_headers()
            error_msg = str(exc_info.value).lower()
            assert any((keyword in error_msg for keyword in ['service_id', 'service_secret', 'not configured', 'missing', 'required'])), f'Expected authentication configuration error mentioning SERVICE_ID or SERVICE_SECRET, got: {exc_info.value}. This proves the configuration dependency.'

    def test_system_user_context_fails_with_invalid_auth(self):
        """Test that system user operations fail with invalid authentication.
        
        This test MUST FAIL initially - it demonstrates the dependencies.py failure.
        
        Expected Failure: 403 'Not authenticated' error from dependencies.py
        After Fix: This test should PASS when authentication is properly configured
        """
        user_id = 'system'
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()
            with pytest.raises(Exception) as exc_info:
                from netra_backend.app.dependencies import get_request_scoped_db_session
                session_gen = get_request_scoped_db_session()
                session = next(session_gen)
            error_msg = str(exc_info.value).lower()
            assert any((keyword in error_msg for keyword in ['403', 'not authenticated', 'unauthorized', 'authentication failed'])), f"Expected 403 authentication error (the exact issue described in Issue #115), got: {exc_info.value}. This should reproduce the 'Not authenticated' error."

    def test_docker_compose_staging_config_missing_service_auth(self):
        """Test that validates the exact docker-compose.staging.yml configuration issue.
        
        This test MUST FAIL initially - it proves the config gap in docker-compose.staging.yml.
        
        Expected Failure: AssertionError showing SERVICE_ID/SECRET missing from backend environment
        After Fix: This test should PASS when the configuration is added
        """
        import yaml
        staging_compose_path = '/Users/anthony/Documents/GitHub/netra-apex/docker-compose.staging.yml'
        with open(staging_compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        backend_env = compose_config['services']['backend']['environment']
        assert 'SERVICE_ID' in backend_env, 'SERVICE_ID is missing from docker-compose.staging.yml backend service environment. This proves the root cause identified in Issue #115 - SERVICE_ID must be added to backend environment.'
        assert 'SERVICE_SECRET' in backend_env, 'SERVICE_SECRET is missing from docker-compose.staging.yml backend service environment. This proves the root cause identified in Issue #115 - SERVICE_SECRET must be added to backend environment.'
        if 'SERVICE_ID' in backend_env:
            assert backend_env['SERVICE_ID'] == 'netra-backend', f"SERVICE_ID should be 'netra-backend', got: {backend_env.get('SERVICE_ID')}"

    def test_service_auth_client_initialization_fails_without_config(self):
        """Test that AuthServiceClient initialization fails without proper configuration.
        
        This test validates the specific auth client component that's failing.
        
        Expected Failure: Configuration validation error during client initialization
        After Fix: This test should PASS when SERVICE_ID/SECRET are available
        """
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()
            with pytest.raises(Exception) as exc_info:
                from netra_backend.app.clients.auth_client_core import AuthServiceClient
                auth_client = AuthServiceClient()
                _ = auth_client.service_id
            error_msg = str(exc_info.value).lower()
            config_error_keywords = ['service_id', 'service_secret', 'not configured', 'missing', 'required', 'environment', 'config']
            assert any((keyword in error_msg for keyword in config_error_keywords)), f'Expected configuration error mentioning SERVICE_ID or SERVICE_SECRET setup, got: {exc_info.value}. This demonstrates the auth client dependency on proper configuration.'

@pytest.mark.unit
class ServiceAuthConfigurationValidationTests:
    """Additional validation tests for service authentication configuration."""

    def test_auth_service_client_requires_both_id_and_secret(self):
        """Test that auth client requires both SERVICE_ID and SERVICE_SECRET.
        
        This test validates the complete configuration requirements.
        """
        test_cases = [{'SERVICE_ID': 'netra-backend', 'SERVICE_SECRET': None}, {'SERVICE_ID': None, 'SERVICE_SECRET': 'test-secret'}, {'SERVICE_ID': '', 'SERVICE_SECRET': 'test-secret'}, {'SERVICE_ID': 'netra-backend', 'SERVICE_SECRET': ''}]
        for case in test_cases:
            with patch.dict(os.environ, case, clear=True):
                env = get_env()
                with pytest.raises(Exception) as exc_info:
                    from netra_backend.app.clients.auth_client_core import AuthServiceClient
                    auth_client = AuthServiceClient()
                    headers = auth_client._get_service_auth_headers()
                error_msg = str(exc_info.value).lower()
                assert any((keyword in error_msg for keyword in ['service_id', 'service_secret', 'missing', 'required', 'not configured'])), f'Expected configuration error for case {case}, got: {exc_info.value}'

    def test_dependencies_system_user_hardcoded_value_issue(self):
        """Test that highlights the hardcoded 'system' user_id in dependencies.py.
        
        This test documents the specific location where the authentication failure occurs.
        """
        from netra_backend.app.dependencies import get_request_scoped_db_session
        with patch.dict(os.environ, {}, clear=True):
            env = get_env()
            env.clear_for_test()
            with pytest.raises(Exception) as exc_info:
                session_gen = get_request_scoped_db_session()
                session = next(session_gen)
            error_msg = str(exc_info.value)
            assert '403' in error_msg or 'Not authenticated' in error_msg or 'authentication' in error_msg.lower(), f'Expected authentication-related error from dependencies.py system user context, got: {exc_info.value}. This is the exact issue described in Issue #115.'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')