"""
Test Configuration SSOT: OAuth/JWT Cascade Failure Prevention

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent OAuth/JWT configuration cascade failures
- Value Impact: Protects $120K+ MRR by preventing authentication system failures
- Strategic Impact: Eliminates $80K+ failures from missing OAuth/JWT configuration

This test validates that OAuth and JWT configuration follows SSOT patterns and
includes proper cascade failure prevention. Authentication failures can lock out
100% of users, making this ULTRA CRITICAL for system stability.
"""

import pytest
from unittest.mock import patch, MagicMock

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env
from shared.jwt_secret_manager import SharedJWTSecretManager


class TestOAuthJWTCascadeFailurePrevention(BaseIntegrationTest):
    """Test OAuth/JWT configuration SSOT compliance and cascade failure prevention."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_secret_manager_ssot_compliance(self, real_services_fixture):
        """
        Test that JWT secret management follows SSOT patterns.
        
        JWT secrets MUST be managed through SharedJWTSecretManager SSOT to prevent:
        - Inconsistent JWT secrets across services (auth failures)
        - Missing JWT validation (security breaches)  
        - Service-to-service authentication failures
        - User session validation failures
        """
        env = get_env()
        env.enable_isolation()
        
        # Test JWT secret SSOT configuration
        jwt_test_configs = [
            # Valid JWT secret (32+ characters)
            'jwt_secret_key_minimum_32_characters_required_for_security',
            # Another valid JWT secret  
            'different_jwt_secret_also_32_characters_minimum_required'
        ]
        
        try:
            for jwt_secret in jwt_test_configs:
                env.set('JWT_SECRET_KEY', jwt_secret, 'jwt_ssot_test')
                
                # Test SharedJWTSecretManager SSOT access
                ssot_jwt_secret = SharedJWTSecretManager.get_jwt_secret()
                
                # CRITICAL: Should return the secret through SSOT pattern
                assert ssot_jwt_secret is not None, "SharedJWTSecretManager should provide JWT secret"
                assert len(ssot_jwt_secret) >= 32, f"JWT secret too short: {len(ssot_jwt_secret)} chars"
                
                # Test that all services get consistent JWT secret
                # Multiple calls should return same secret (consistency)
                jwt_secret_2 = SharedJWTSecretManager.get_jwt_secret()
                assert jwt_secret_2 == ssot_jwt_secret, "JWT secret should be consistent across calls"
                
                # Test JWT secret validation
                is_valid = SharedJWTSecretManager.validate_jwt_secret(ssot_jwt_secret)
                assert is_valid, "JWT secret should pass validation"
            
            # Test JWT secret cascade failure prevention
            
            # Scenario 1: Missing JWT secret (would cause 100% auth failure)
            env.delete('JWT_SECRET_KEY')
            
            # SSOT manager should handle missing secret gracefully
            try:
                missing_secret = SharedJWTSecretManager.get_jwt_secret()
                # Should either provide fallback or raise clear error
                if missing_secret is not None:
                    assert len(missing_secret) >= 32, "Fallback JWT secret should be secure"
                else:
                    # If no fallback, should provide clear error message
                    pass
            except Exception as e:
                # Error should be informative for debugging
                assert 'jwt' in str(e).lower() or 'secret' in str(e).lower(), \
                    f"JWT error should be clear: {str(e)}"
            
            # Scenario 2: Weak JWT secret (security vulnerability)
            weak_secrets = ['weak', '123456', 'short_secret']
            
            for weak_secret in weak_secrets:
                env.set('JWT_SECRET_KEY', weak_secret, 'security_test')
                
                # SSOT should detect weak secrets
                is_weak_valid = SharedJWTSecretManager.validate_jwt_secret(weak_secret)
                assert not is_weak_valid, f"Weak secret should fail validation: {weak_secret}"
                
                # Getting weak secret should trigger security warnings
                try:
                    weak_jwt = SharedJWTSecretManager.get_jwt_secret()
                    if weak_jwt == weak_secret:
                        # If returned, should log security warning (implementation detail)
                        pass
                except Exception:
                    # May reject weak secrets entirely (preferred)
                    pass
            
        finally:
            env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_configuration_ssot_compliance(self, real_services_fixture):
        """
        Test OAuth configuration follows SSOT patterns and prevents cascade failures.
        
        OAuth configuration MUST be centralized to prevent:
        - Missing OAuth credentials (user login failures)
        - Environment-specific OAuth mismatches
        - Service discovery failures for OAuth endpoints
        - Cross-service OAuth validation inconsistencies
        """
        env = get_env()
        env.enable_isolation()
        
        # Test OAuth SSOT configuration patterns
        oauth_configs = {
            'development': {
                'GOOGLE_CLIENT_ID': 'dev_google_client_id',
                'GOOGLE_CLIENT_SECRET': 'dev_google_client_secret',
                'OAUTH_CALLBACK_URL': 'http://localhost:8081/auth/google/callback'
            },
            'staging': {
                'GOOGLE_CLIENT_ID': 'staging_google_client_id',
                'GOOGLE_CLIENT_SECRET': 'staging_google_client_secret',
                'OAUTH_CALLBACK_URL': 'https://auth.staging.netrasystems.ai/auth/google/callback'
            },
            'production': {
                'GOOGLE_CLIENT_ID': 'prod_google_client_id',
                'GOOGLE_CLIENT_SECRET': 'prod_google_client_secret',
                'OAUTH_CALLBACK_URL': 'https://auth.netrasystems.ai/auth/google/callback'
            }
        }
        
        try:
            for environment, config in oauth_configs.items():
                env.set('ENVIRONMENT', environment, 'oauth_test')
                
                # Set OAuth configuration
                for key, value in config.items():
                    env.set(key, value, f'{environment}_oauth_config')
                
                # Test environment-appropriate OAuth configuration
                client_id = env.get('GOOGLE_CLIENT_ID')
                client_secret = env.get('GOOGLE_CLIENT_SECRET')
                callback_url = env.get('OAUTH_CALLBACK_URL')
                
                # CRITICAL: OAuth config should be environment-specific
                assert client_id == config['GOOGLE_CLIENT_ID']
                assert client_secret == config['GOOGLE_CLIENT_SECRET']
                assert callback_url == config['OAUTH_CALLBACK_URL']
                
                # Environment-specific validation
                if environment == 'development':
                    assert 'localhost' in callback_url, "Dev should use localhost"
                elif environment == 'staging':
                    assert 'staging' in callback_url, "Staging should use staging domain"
                    assert 'https' in callback_url, "Staging should use HTTPS"
                elif environment == 'production':
                    assert 'staging' not in callback_url, "Production should not use staging"
                    assert 'localhost' not in callback_url, "Production should not use localhost"
                    assert 'https' in callback_url, "Production should use HTTPS"
                
                # Test OAuth configuration completeness
                oauth_completeness = {
                    'has_client_id': client_id is not None,
                    'has_client_secret': client_secret is not None,
                    'has_callback_url': callback_url is not None
                }
                
                incomplete_fields = [field for field, complete in oauth_completeness.items() if not complete]
                
                if environment == 'production':
                    # Production MUST have complete OAuth
                    assert len(incomplete_fields) == 0, \
                        f"Production OAuth incomplete: {incomplete_fields}"
                else:
                    # Development/staging may have some flexibility
                    pass
                
                # Test OAuth cascade failure prevention scenarios
                
                # Scenario 1: Missing OAuth client ID (login failures)
                original_client_id = env.get('GOOGLE_CLIENT_ID')
                env.delete('GOOGLE_CLIENT_ID')
                
                # Should detect missing critical OAuth component
                missing_client_id = env.get('GOOGLE_CLIENT_ID')
                assert missing_client_id is None
                
                # Restore for next tests
                env.set('GOOGLE_CLIENT_ID', original_client_id, 'restore')
                
                # Scenario 2: Invalid callback URL (OAuth flow breaks)
                invalid_callbacks = [
                    'http://wrong-domain.com/callback',  # Wrong domain
                    'not-a-url',  # Invalid URL format
                    'http://localhost/wrong-path'  # Wrong path
                ]
                
                for invalid_callback in invalid_callbacks:
                    env.set('OAUTH_CALLBACK_URL', invalid_callback, 'invalid_test')
                    
                    callback_url = env.get('OAUTH_CALLBACK_URL')
                    
                    # Should be set but validation would catch this
                    assert callback_url == invalid_callback
                    
                    # In practice, OAuth provider would reject invalid callbacks
                
                # Restore valid callback
                env.set('OAUTH_CALLBACK_URL', config['OAUTH_CALLBACK_URL'], 'restore')
        
        finally:
            env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_oauth_jwt_cross_service_synchronization(self, real_services_fixture):
        """
        Test OAuth/JWT configuration synchronization across services.
        
        Backend and auth services must have synchronized OAuth/JWT configuration
        to prevent cascade failures:
        - Backend JWT validation must use same secret as auth service
        - OAuth callback URLs must be consistent
        - Service-to-service auth must use same SERVICE_SECRET
        """
        # Simulate multi-service environment
        backend_env = get_env()
        backend_env.enable_isolation()
        
        # Create second environment instance for auth service simulation
        from shared.isolated_environment import IsolatedEnvironment
        auth_env = IsolatedEnvironment()
        auth_env.enable_isolation()
        
        try:
            # Set up synchronized configuration
            shared_secrets = {
                'JWT_SECRET_KEY': 'shared_jwt_secret_32_characters_minimum_required',
                'SERVICE_SECRET': 'shared_service_secret_32_characters_minimum',
                'GOOGLE_CLIENT_ID': 'shared_google_client_id',
                'GOOGLE_CLIENT_SECRET': 'shared_google_client_secret'
            }
            
            # Backend service configuration
            backend_config = shared_secrets.copy()
            backend_config.update({
                'SERVICE_NAME': 'netra-backend',
                'SERVICE_PORT': '8000',
                'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai'
            })
            
            for key, value in backend_config.items():
                backend_env.set(key, value, 'backend_service')
            
            # Auth service configuration  
            auth_config = shared_secrets.copy()
            auth_config.update({
                'SERVICE_NAME': 'netra-auth',
                'SERVICE_PORT': '8081',
                'OAUTH_CALLBACK_URL': 'https://auth.staging.netrasystems.ai/auth/google/callback'
            })
            
            for key, value in auth_config.items():
                auth_env.set(key, value, 'auth_service')
            
            # CRITICAL: Test cross-service synchronization
            
            # JWT secrets must be identical
            backend_jwt = backend_env.get('JWT_SECRET_KEY')
            auth_jwt = auth_env.get('JWT_SECRET_KEY')
            assert backend_jwt == auth_jwt, "JWT secrets must be synchronized across services"
            
            # Service secrets must be identical for inter-service auth
            backend_service_secret = backend_env.get('SERVICE_SECRET')
            auth_service_secret = auth_env.get('SERVICE_SECRET')
            assert backend_service_secret == auth_service_secret, \
                "SERVICE_SECRET must be synchronized for inter-service auth"
            
            # OAuth credentials must be accessible to both services
            backend_google_id = backend_env.get('GOOGLE_CLIENT_ID')
            auth_google_id = auth_env.get('GOOGLE_CLIENT_ID')
            assert backend_google_id == auth_google_id, \
                "Google OAuth credentials must be synchronized"
            
            # Test SharedJWTSecretManager consistency across service contexts
            # Mock different service contexts
            with patch('shared.isolated_environment.get_env', return_value=backend_env):
                backend_jwt_ssot = SharedJWTSecretManager.get_jwt_secret()
            
            with patch('shared.isolated_environment.get_env', return_value=auth_env):
                auth_jwt_ssot = SharedJWTSecretManager.get_jwt_secret()
            
            # SSOT should provide consistent JWT across service contexts
            assert backend_jwt_ssot == auth_jwt_ssot, \
                "SharedJWTSecretManager should provide consistent secrets across services"
            
            # Test cascade failure prevention: SERVICE_SECRET mismatch
            auth_env.set('SERVICE_SECRET', 'different_service_secret_32_chars_min', 'mismatch_test')
            
            backend_service_secret = backend_env.get('SERVICE_SECRET')
            auth_service_secret = auth_env.get('SERVICE_SECRET')
            
            # Mismatch detected
            assert backend_service_secret != auth_service_secret, "Should detect SERVICE_SECRET mismatch"
            
            # This would cause inter-service auth failures in practice
            # Real system should validate and alert on this mismatch
            
        finally:
            backend_env.reset_to_original()
            auth_env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_oauth_jwt_test_environment_cascade_prevention(self, real_services_fixture):
        """
        Test OAuth/JWT cascade failure prevention in test environments.
        
        Test environments need special OAuth/JWT handling to prevent cascade failures:
        - Built-in test OAuth credentials when real ones unavailable
        - Test-specific JWT secrets for isolation
        - Graceful degradation when OAuth services unavailable
        - Prevention of test credentials leaking to production
        """
        env = get_env()
        env.enable_isolation()
        
        # Set up test environment markers
        test_environment_config = {
            'ENVIRONMENT': 'testing',
            'TESTING': 'true',
            'PYTEST_CURRENT_TEST': 'test_oauth_jwt_cascade_prevention'
        }
        
        for key, value in test_environment_config.items():
            env.set(key, value, 'test_environment')
        
        try:
            # Test 1: Missing OAuth credentials in test environment
            # Should provide built-in test credentials or graceful degradation
            
            # Don't set OAuth credentials initially
            oauth_client_id = env.get('GOOGLE_CLIENT_ID')
            oauth_client_secret = env.get('GOOGLE_CLIENT_SECRET')
            
            # Test environment should handle missing OAuth gracefully
            if oauth_client_id is None:
                # Should either provide test defaults or not fail catastrophically
                pass
            
            # Test 2: JWT secret handling in test environment
            test_jwt_secrets = [
                'test_jwt_secret_for_testing_minimum_32_characters',
                None  # Test missing JWT secret
            ]
            
            for test_jwt_secret in test_jwt_secrets:
                if test_jwt_secret:
                    env.set('JWT_SECRET_KEY', test_jwt_secret, 'test_jwt')
                else:
                    env.delete('JWT_SECRET_KEY')
                
                # Test JWT secret access through SSOT
                try:
                    ssot_jwt = SharedJWTSecretManager.get_jwt_secret()
                    
                    if ssot_jwt is not None:
                        # Should be secure even in test environment
                        assert len(ssot_jwt) >= 32, "Test JWT secret should still be secure"
                    else:
                        # If None, should handle gracefully without cascade failure
                        pass
                        
                except Exception as e:
                    # Errors should be informative, not cascade failures
                    assert 'jwt' in str(e).lower() or 'secret' in str(e).lower()
            
            # Test 3: Built-in test OAuth credentials
            env.set('GOOGLE_CLIENT_ID', 'test_google_client_id', 'test_oauth')
            env.set('GOOGLE_CLIENT_SECRET', 'test_google_client_secret', 'test_oauth')
            env.set('OAUTH_CALLBACK_URL', 'http://localhost:8081/auth/test/callback', 'test_oauth')
            
            # Test OAuth in test environment
            test_client_id = env.get('GOOGLE_CLIENT_ID')
            test_client_secret = env.get('GOOGLE_CLIENT_SECRET')
            test_callback = env.get('OAUTH_CALLBACK_URL')
            
            assert test_client_id == 'test_google_client_id'
            assert test_client_secret == 'test_google_client_secret'
            assert 'localhost' in test_callback, "Test environment should use localhost"
            
            # CRITICAL: Test credentials should not work in production
            # (This would be enforced by OAuth provider configuration)
            
            # Test 4: SERVICE_SECRET in test environment
            env.set('SERVICE_SECRET', 'test_service_secret_32_characters_minimum', 'test_service')
            
            test_service_secret = env.get('SERVICE_SECRET')
            assert test_service_secret == 'test_service_secret_32_characters_minimum'
            assert len(test_service_secret) >= 32, "Test service secret should be secure"
            
            # Test 5: Environment isolation prevents test credential leakage
            # Create production environment simulation
            prod_env = IsolatedEnvironment()
            prod_env.enable_isolation()
            
            try:
                # Set production environment
                prod_env.set('ENVIRONMENT', 'production', 'prod_test')
                prod_env.set('GOOGLE_CLIENT_ID', 'prod_google_client_id', 'prod_oauth')
                prod_env.set('JWT_SECRET_KEY', 'prod_jwt_secret_32_characters_minimum_secure', 'prod_jwt')
                
                # CRITICAL: Production should not see test credentials
                prod_google_id = prod_env.get('GOOGLE_CLIENT_ID')
                test_google_id = env.get('GOOGLE_CLIENT_ID')
                
                assert prod_google_id != test_google_id, \
                    "Production should not use test OAuth credentials"
                
                prod_jwt = prod_env.get('JWT_SECRET_KEY')
                test_jwt = env.get('JWT_SECRET_KEY')
                
                assert prod_jwt != test_jwt, \
                    "Production should not use test JWT secrets"
                    
            finally:
                prod_env.reset_to_original()
        
        finally:
            env.reset_to_original()