"""
Test Configuration SSOT: Environment Isolation Patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Prevent environment drift and cross-environment contamination  
- Value Impact: Protects $120K+ MRR by ensuring test/dev/staging/prod environment isolation
- Strategic Impact: Eliminates configuration cascade failures from environment leakage

This test validates that environment isolation prevents configuration from one
environment (dev/test) from leaking into another (staging/prod), which can cause
cascade failures and security issues.
"""

import pytest
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env, IsolatedEnvironment


class TestEnvironmentIsolationPatterns(BaseIntegrationTest):
    """Test environment isolation SSOT compliance."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_development_environment_isolation_from_production(self, real_services_fixture):
        """
        Test that development environment configuration is isolated from production.
        
        Development environments often use fallback values and localhost URLs.
        These MUST NOT leak into production environments, which would cause
        cascade failures and security vulnerabilities.
        """
        # Create separate environment instances to simulate service isolation
        dev_env = IsolatedEnvironment()
        staging_env = IsolatedEnvironment()
        prod_env = IsolatedEnvironment()
        
        # Enable isolation for all environments
        dev_env.enable_isolation()
        staging_env.enable_isolation()
        prod_env.enable_isolation()
        
        try:
            # Set up development environment with localhost URLs and test values
            dev_config = {
                'ENVIRONMENT': 'development',
                'DATABASE_URL': 'postgresql://localhost:5432/netra_dev',
                'REDIS_URL': 'redis://localhost:6379',
                'API_URL': 'http://localhost:8000',
                'FRONTEND_URL': 'http://localhost:3000',
                'SERVICE_SECRET': 'dev_secret_not_secure',
                'JWT_SECRET_KEY': 'dev_jwt_key_insecure',
                'DEBUG': 'true',
                'TESTING': 'true'
            }
            
            for key, value in dev_config.items():
                dev_env.set(key, value, 'development_config')
            
            # Set up staging environment with production-like values  
            staging_config = {
                'ENVIRONMENT': 'staging',
                'POSTGRES_HOST': '/cloudsql/netra-staging:us-central1:netra-staging-db',
                'POSTGRES_USER': 'staging_user',
                'POSTGRES_PASSWORD': 'staging_secure_password',
                'POSTGRES_DB': 'netra_staging',
                'REDIS_URL': 'redis://staging-redis.internal:6379',
                'API_URL': 'https://api.staging.netrasystems.ai',
                'FRONTEND_URL': 'https://app.staging.netrasystems.ai',
                'SERVICE_SECRET': 'staging_service_secret_secure',
                'JWT_SECRET_KEY': 'staging_jwt_secret_key_secure',
                'DEBUG': 'false'
            }
            
            for key, value in staging_config.items():
                staging_env.set(key, value, 'staging_config')
            
            # Set up production environment with secure values
            prod_config = {
                'ENVIRONMENT': 'production',
                'POSTGRES_HOST': '/cloudsql/netra-prod:us-central1:netra-production-db',
                'POSTGRES_USER': 'production_user',
                'POSTGRES_PASSWORD': 'production_ultra_secure_password',
                'POSTGRES_DB': 'netra_production',
                'REDIS_URL': 'redis://production-redis.internal:6379',
                'API_URL': 'https://api.netrasystems.ai',
                'FRONTEND_URL': 'https://app.netrasystems.ai', 
                'SERVICE_SECRET': 'production_service_secret_ultra_secure',
                'JWT_SECRET_KEY': 'production_jwt_secret_key_ultra_secure',
                'DEBUG': 'false'
            }
            
            for key, value in prod_config.items():
                prod_env.set(key, value, 'production_config')
            
            # CRITICAL: Verify complete isolation between environments
            
            # Development should have localhost values
            assert dev_env.get('API_URL') == 'http://localhost:8000'
            assert 'localhost' in dev_env.get('DATABASE_URL')
            assert dev_env.get('DEBUG') == 'true'
            
            # Staging should have staging-specific values  
            assert staging_env.get('API_URL') == 'https://api.staging.netrasystems.ai'
            assert 'staging' in staging_env.get('POSTGRES_HOST')
            assert staging_env.get('DEBUG') == 'false'
            
            # Production should have production values
            assert prod_env.get('API_URL') == 'https://api.netrasystems.ai'
            assert 'production' in prod_env.get('POSTGRES_HOST')
            assert prod_env.get('DEBUG') == 'false'
            
            # CRITICAL: No cross-environment contamination
            assert dev_env.get('API_URL') != staging_env.get('API_URL')
            assert dev_env.get('API_URL') != prod_env.get('API_URL')
            assert staging_env.get('API_URL') != prod_env.get('API_URL')
            
            # Service secrets must be unique per environment
            dev_secret = dev_env.get('SERVICE_SECRET')
            staging_secret = staging_env.get('SERVICE_SECRET')
            prod_secret = prod_env.get('SERVICE_SECRET')
            
            assert dev_secret != staging_secret
            assert dev_secret != prod_secret
            assert staging_secret != prod_secret
            
            # JWT secrets must be unique per environment
            dev_jwt = dev_env.get('JWT_SECRET_KEY')
            staging_jwt = staging_env.get('JWT_SECRET_KEY')
            prod_jwt = prod_env.get('JWT_SECRET_KEY')
            
            assert dev_jwt != staging_jwt
            assert dev_jwt != prod_jwt
            assert staging_jwt != prod_jwt
            
            # Verify isolation at os.environ level
            # None of these isolated values should leak to system environment
            assert os.environ.get('API_URL') != 'http://localhost:8000'
            assert os.environ.get('API_URL') != 'https://api.staging.netrasystems.ai'
            assert os.environ.get('SERVICE_SECRET') != dev_secret
            assert os.environ.get('SERVICE_SECRET') != staging_secret
            
        finally:
            # Cleanup all environments
            dev_env.reset_to_original()
            staging_env.reset_to_original()
            prod_env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_test_environment_isolation_from_development(self, real_services_fixture):
        """
        Test that test environment configuration is isolated from development.
        
        Test environments need special configuration that should not affect
        development work. Test values like test databases, mock URLs, and
        test credentials must be completely isolated.
        """
        dev_env = get_env()
        dev_env.enable_isolation()
        
        # Create a separate test environment
        test_env = IsolatedEnvironment()
        test_env.enable_isolation()
        
        try:
            # Set development configuration
            dev_config = {
                'ENVIRONMENT': 'development',
                'POSTGRES_DB': 'netra_dev',
                'POSTGRES_PORT': '5432',
                'REDIS_URL': 'redis://localhost:6379',
                'LLM_API_KEY': 'dev_anthropic_key',
                'OAUTH_CLIENT_ID': 'dev_oauth_client',
                'ENABLE_DEBUG_LOGGING': 'true'
            }
            
            for key, value in dev_config.items():
                dev_env.set(key, value, 'development')
            
            # Set test configuration with different values
            test_config = {
                'ENVIRONMENT': 'testing',
                'POSTGRES_DB': 'netra_test',
                'POSTGRES_PORT': '5434',  # Different port to avoid conflicts
                'REDIS_URL': 'redis://localhost:6381',  # Different port
                'LLM_API_KEY': 'test_mock_anthropic_key',
                'OAUTH_CLIENT_ID': 'test_oauth_client',
                'ENABLE_DEBUG_LOGGING': 'false',
                'TESTING': 'true',
                'PYTEST_CURRENT_TEST': 'test_config_ssot'
            }
            
            for key, value in test_config.items():
                test_env.set(key, value, 'test_framework')
            
            # CRITICAL: Verify test isolation doesn't affect development
            assert dev_env.get('POSTGRES_DB') == 'netra_dev'
            assert test_env.get('POSTGRES_DB') == 'netra_test'
            assert dev_env.get('POSTGRES_DB') != test_env.get('POSTGRES_DB')
            
            # Port isolation prevents conflicts
            assert dev_env.get('POSTGRES_PORT') == '5432'
            assert test_env.get('POSTGRES_PORT') == '5434'
            
            # API keys should be isolated
            assert dev_env.get('LLM_API_KEY') != test_env.get('LLM_API_KEY')
            
            # Test-specific variables shouldn't leak to development
            assert dev_env.get('TESTING') != 'true'
            assert dev_env.get('PYTEST_CURRENT_TEST') is None
            
            # Development-specific logging shouldn't affect tests
            assert dev_env.get('ENABLE_DEBUG_LOGGING') != test_env.get('ENABLE_DEBUG_LOGGING')
            
            # Test subprocess environment isolation
            dev_subprocess_env = dev_env.get_subprocess_env()
            test_subprocess_env = test_env.get_subprocess_env()
            
            assert dev_subprocess_env['POSTGRES_DB'] == 'netra_dev'
            assert test_subprocess_env['POSTGRES_DB'] == 'netra_test'
            
            # CRITICAL: No cross-contamination in subprocess environments
            assert dev_subprocess_env['POSTGRES_PORT'] != test_subprocess_env['POSTGRES_PORT']
            
        finally:
            dev_env.reset_to_original()
            test_env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_service_environment_isolation(self, real_services_fixture):
        """
        Test environment isolation between different services in same environment.
        
        Each service (backend, auth, frontend) may have service-specific
        configuration even within the same environment. These configurations
        must be isolated to prevent cross-service configuration pollution.
        """
        # Create service-specific environments
        backend_env = IsolatedEnvironment()
        auth_env = IsolatedEnvironment() 
        frontend_env = IsolatedEnvironment()
        
        backend_env.enable_isolation()
        auth_env.enable_isolation()
        frontend_env.enable_isolation()
        
        try:
            # Backend service configuration
            backend_config = {
                'SERVICE_NAME': 'netra-backend',
                'SERVICE_PORT': '8000',
                'DATABASE_POOL_SIZE': '20',
                'ENABLE_AGENT_EXECUTION': 'true',
                'MAX_CONCURRENT_AGENTS': '10',
                'LLM_TIMEOUT': '60',
                'SERVICE_SECRET': 'backend_service_secret'
            }
            
            for key, value in backend_config.items():
                backend_env.set(key, value, 'backend_service')
            
            # Auth service configuration  
            auth_config = {
                'SERVICE_NAME': 'netra-auth',
                'SERVICE_PORT': '8081',
                'JWT_EXPIRY_MINUTES': '60',
                'OAUTH_CALLBACK_URL': 'https://auth.staging.netrasystems.ai/callback',
                'SESSION_TIMEOUT_MINUTES': '1440',
                'SERVICE_SECRET': 'auth_service_secret'
            }
            
            for key, value in auth_config.items():
                auth_env.set(key, value, 'auth_service')
            
            # Frontend configuration (different patterns)
            frontend_config = {
                'SERVICE_NAME': 'netra-frontend',
                'SERVICE_PORT': '3000',
                'NEXT_PUBLIC_API_URL': 'https://api.staging.netrasystems.ai',
                'NEXT_PUBLIC_WS_URL': 'wss://api.staging.netrasystems.ai',
                'NEXT_PUBLIC_AUTH_URL': 'https://auth.staging.netrasystems.ai',
                'BUILD_TIMEOUT': '300'
            }
            
            for key, value in frontend_config.items():
                frontend_env.set(key, value, 'frontend_service')
            
            # CRITICAL: Verify service isolation
            
            # Each service should have its own port
            assert backend_env.get('SERVICE_PORT') == '8000'
            assert auth_env.get('SERVICE_PORT') == '8081'
            assert frontend_env.get('SERVICE_PORT') == '3000'
            
            # Service names should be unique
            assert backend_env.get('SERVICE_NAME') == 'netra-backend'
            assert auth_env.get('SERVICE_NAME') == 'netra-auth'
            assert frontend_env.get('SERVICE_NAME') == 'netra-frontend'
            
            # Service-specific configurations shouldn't leak
            assert backend_env.get('JWT_EXPIRY_MINUTES') is None  # Auth-only config
            assert auth_env.get('DATABASE_POOL_SIZE') is None     # Backend-only config
            assert frontend_env.get('MAX_CONCURRENT_AGENTS') is None  # Backend-only config
            
            # Frontend public URLs shouldn't be in backend/auth
            assert backend_env.get('NEXT_PUBLIC_API_URL') is None
            assert auth_env.get('NEXT_PUBLIC_WS_URL') is None
            
            # Service secrets should be the same (shared authentication)
            # but each service manages its own copy
            backend_secret = backend_env.get('SERVICE_SECRET')
            auth_secret = auth_env.get('SERVICE_SECRET')
            
            # In practice, these would be the same value but managed independently
            assert backend_secret is not None
            assert auth_secret is not None
            
            # Test cross-service communication patterns
            # Backend needs to know auth service URL
            backend_env.set('AUTH_SERVICE_URL', 'https://auth.staging.netrasystems.ai', 'service_discovery')
            
            # Auth service needs to validate backend requests  
            auth_env.set('ALLOWED_SERVICE_IDS', 'netra-backend,netra-frontend', 'service_security')
            
            # These cross-service configurations should be isolated
            assert backend_env.get('AUTH_SERVICE_URL') == 'https://auth.staging.netrasystems.ai'
            assert auth_env.get('AUTH_SERVICE_URL') is None  # Not set in auth service
            
            assert auth_env.get('ALLOWED_SERVICE_IDS') == 'netra-backend,netra-frontend'
            assert backend_env.get('ALLOWED_SERVICE_IDS') is None  # Not set in backend
            
        finally:
            backend_env.reset_to_original()
            auth_env.reset_to_original()
            frontend_env.reset_to_original()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_subprocess_environment_inheritance_isolation(self, real_services_fixture):
        """
        Test that subprocess environments properly inherit isolated configuration.
        
        Services often spawn subprocesses (Docker commands, database migrations,
        external tools). These subprocesses must inherit the correct isolated
        environment without breaking isolation boundaries.
        """
        env = get_env()
        env.enable_isolation()
        
        try:
            # Set up isolated environment with subprocess-relevant config
            subprocess_config = {
                'PATH': '/usr/local/bin:/usr/bin:/bin',
                'POSTGRES_HOST': 'localhost', 
                'POSTGRES_PORT': '5434',
                'POSTGRES_USER': 'test_user',
                'POSTGRES_PASSWORD': 'test_password',
                'POSTGRES_DB': 'test_database',
                'PYTHONPATH': '/app:/app/src',
                'SERVICE_SECRET': 'subprocess_test_secret',
                'ISOLATION_TEST_VAR': 'isolated_subprocess_value'
            }
            
            for key, value in subprocess_config.items():
                env.set(key, value, 'subprocess_test')
            
            # Get subprocess environment
            subprocess_env = env.get_subprocess_env()
            
            # CRITICAL: Subprocess should inherit isolated values
            assert subprocess_env['POSTGRES_HOST'] == 'localhost'
            assert subprocess_env['POSTGRES_PORT'] == '5434'
            assert subprocess_env['POSTGRES_USER'] == 'test_user'
            assert subprocess_env['POSTGRES_DB'] == 'test_database'
            assert subprocess_env['ISOLATION_TEST_VAR'] == 'isolated_subprocess_value'
            
            # Test that subprocess environment is a complete copy
            assert 'PATH' in subprocess_env
            assert 'PYTHONPATH' in subprocess_env
            
            # CRITICAL: Modifications to subprocess env shouldn't affect isolated env
            subprocess_env['ISOLATION_TEST_VAR'] = 'modified_in_subprocess'
            
            # Original isolated environment should be unchanged  
            assert env.get('ISOLATION_TEST_VAR') == 'isolated_subprocess_value'
            
            # Test subprocess environment with real subprocess call
            # Use a simple command that echoes an environment variable
            test_script = """
import os
import sys
print(f"POSTGRES_HOST={os.environ.get('POSTGRES_HOST', 'NOT_SET')}")
print(f"ISOLATION_TEST_VAR={os.environ.get('ISOLATION_TEST_VAR', 'NOT_SET')}")
print(f"SERVICE_SECRET={os.environ.get('SERVICE_SECRET', 'NOT_SET')}")
"""
            
            # Create temporary script file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as script_file:
                script_file.write(test_script)
                script_file.flush()
                
                try:
                    # Run subprocess with isolated environment
                    result = subprocess.run(
                        ['python', script_file.name],
                        env=subprocess_env,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    # Verify subprocess got isolated values
                    output = result.stdout
                    assert 'POSTGRES_HOST=localhost' in output
                    assert 'ISOLATION_TEST_VAR=isolated_subprocess_value' in output
                    assert 'SERVICE_SECRET=subprocess_test_secret' in output
                    
                    # CRITICAL: Verify subprocess didn't affect parent environment
                    assert env.get('POSTGRES_HOST') == 'localhost'
                    assert env.get('ISOLATION_TEST_VAR') == 'isolated_subprocess_value'
                    
                    # Verify os.environ wasn't affected by subprocess
                    assert os.environ.get('ISOLATION_TEST_VAR') != 'isolated_subprocess_value'
                    
                finally:
                    os.unlink(script_file.name)
                    
        finally:
            env.reset_to_original()