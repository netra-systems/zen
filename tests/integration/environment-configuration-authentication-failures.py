from shared.isolated_environment import get_env
"""
env = get_env()
Environment Configuration Authentication Failures - Iteration 2 Audit Findings

This test file validates the complete breakdown of authentication due to 
environment configuration issues identified in Iteration 2:

**CRITICAL ENVIRONMENT CONFIGURATION FAILURES:**
1. Authentication environment variables missing, empty, or corrupted
2. Service account credentials not accessible from environment
3. JWT signing keys not configured or synchronized across environments  
4. OAuth configuration incomplete or invalid
5. Database authentication credentials corrupted by environment sanitization
6. SSL certificates missing or invalid in staging environment
7. Environment-specific authentication URLs incorrect or unreachable

**EXPECTED TO FAIL**: These tests demonstrate environment configuration issues 
causing authentication system breakdown

Environment Types Tested:
- Development (local)
- Staging (GCP)
- Production-like configurations
- Container/Docker environments
- CI/CD pipeline environments

Root Causes (Environment Configuration):
- Critical authentication environment variables undefined or empty
- Environment variable sanitization corrupting authentication credentials
- Service account key files missing or inaccessible  
- Environment-specific configuration overrides failing
- Secrets management integration broken
- Container environment variable injection failures
"""

import os
import pytest
import tempfile
import json
from pathlib import Path

from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.config import get_unified_config
from shared.isolated_environment import IsolatedEnvironment as AuthIsolatedEnvironment
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient


class TestEnvironmentConfigurationAuthenticationFailures:
    """Test environment configuration authentication failures from Iteration 2 audit"""

    def setup_method(self):
        """Set up test environment with clean state"""
        self.original_environ = env.get_all()
        self.temp_files = []
        
    def teardown_method(self):
        """Clean up test environment"""
        env.clear()
        env.update(self.original_environ, "test")
        
        # Clean up temporary files
        for temp_file in self.temp_files:
            try:
                os.unlink(temp_file)
            except FileNotFoundError:
                pass

    @pytest.mark.integration
    @pytest.mark.critical
    def test_critical_authentication_environment_variables_missing(self):
        """
        EXPECTED TO FAIL - CRITICAL ENV VAR ISSUE
        Critical authentication environment variables should be present and valid
        Root cause: Missing or undefined authentication environment variables
        """
        critical_auth_env_vars = [
            'JWT_SECRET_KEY',
            'JWT_ALGORITHM', 
            'JWT_ACCESS_TOKEN_EXPIRE_MINUTES',
            'AUTH_SERVICE_URL',
            'OAUTH_CLIENT_ID',
            'OAUTH_CLIENT_SECRET',
            'OAUTH_REDIRECT_URI',
            'SERVICE_ACCOUNT_KEY_PATH',
            'NETRA_API_KEY',
            'GOOGLE_APPLICATION_CREDENTIALS',
            'AUTH_DATABASE_URL',
            'REDIS_URL'
        ]
        
        # Test each critical environment variable
        missing_vars = []
        empty_vars = []
        
        for var_name in critical_auth_env_vars:
            # Clear the variable to simulate missing environment
            if var_name in os.environ:
                del os.environ[var_name]
            
            env = IsolatedEnvironment()
            var_value = env.get(var_name)
            
            if var_value is None:
                missing_vars.append(var_name)
            elif var_value == "":
                empty_vars.append(var_name)
            elif len(str(var_value).strip()) < 8:  # Too short to be valid
                empty_vars.append(f"{var_name} (too short: '{var_value}')")
        
        # These should NOT be missing or empty in a properly configured environment
        assert len(missing_vars) == 0, f"Critical auth environment variables missing: {missing_vars}"
        assert len(empty_vars) == 0, f"Critical auth environment variables empty: {empty_vars}"

    @pytest.mark.integration
    @pytest.mark.critical
    def test_service_account_credentials_not_accessible_from_environment(self):
        """
        EXPECTED TO FAIL - CRITICAL SERVICE ACCOUNT ISSUE
        Service account credentials should be accessible via environment configuration
        Root cause: Service account key file not accessible or environment variable incorrect
        """
        # Test various service account configuration patterns
        service_account_configs = [
            ('GOOGLE_APPLICATION_CREDENTIALS', '/path/to/service-account.json'),
            ('SERVICE_ACCOUNT_KEY_PATH', '/path/to/netra-staging-key.json'),
            ('NETRA_SERVICE_ACCOUNT_JSON', '{"type": "service_account", "project_id": "netra-staging"}'),
            ('GCP_SERVICE_ACCOUNT_EMAIL', 'netra-backend@staging.iam.gserviceaccount.com')
        ]
        
        for env_var, test_value in service_account_configs:
            os.environ[env_var] = test_value
            
            env = IsolatedEnvironment()
            retrieved_value = env.get(env_var)
            
            # Should be accessible and not corrupted
            assert retrieved_value is not None, f"Service account env var {env_var} should not be None"
            assert retrieved_value != "", f"Service account env var {env_var} should not be empty"
            assert retrieved_value == test_value, f"Service account env var {env_var} corrupted: expected '{test_value}', got '{retrieved_value}'"
            
            # For file paths, should be valid paths
            if env_var.endswith('_PATH') or env_var == 'GOOGLE_APPLICATION_CREDENTIALS':
                assert retrieved_value.endswith('.json'), f"Service account file {env_var} should be JSON file"

    @pytest.mark.integration
    @pytest.mark.critical
    def test_jwt_signing_keys_not_configured_across_environments(self):
        """
        EXPECTED TO FAIL - CRITICAL JWT KEY ISSUE
        JWT signing keys should be properly configured across all environments
        Root cause: JWT signing key configuration missing or inconsistent
        """
        # Test JWT key configuration for different environments
        environments = ['development', 'staging', 'production']
        
        for env_name in environments:
            env.set('ENVIRONMENT', env_name, "test")
            env.set('NODE_ENV', env_name, "test") if env_name != 'development' else 'development'
            
            # Set environment-specific JWT keys
            jwt_key_vars = [
                f'JWT_SECRET_KEY_{env_name.upper()}',
                'JWT_SECRET_KEY',
                f'JWT_PRIVATE_KEY_{env_name.upper()}',
                f'JWT_PUBLIC_KEY_{env_name.upper()}'
            ]
            
            # Clear all JWT keys to simulate missing configuration
            for key_var in jwt_key_vars:
                if key_var in os.environ:
                    del os.environ[key_var]
            
            env = IsolatedEnvironment()
            config = get_unified_config()
            
            # Should have JWT configuration for this environment
            jwt_secret = env.get('JWT_SECRET_KEY')
            jwt_algorithm = env.get('JWT_ALGORITHM', 'HS256')
            
            # JWT configuration should be present and valid
            assert jwt_secret is not None, f"JWT secret key missing for {env_name} environment"
            assert jwt_secret != "", f"JWT secret key empty for {env_name} environment"
            assert len(jwt_secret) >= 32, f"JWT secret key too short for {env_name} environment (got {len(jwt_secret)} chars)"
            assert jwt_algorithm in ['HS256', 'RS256', 'ES256'], f"Invalid JWT algorithm for {env_name}: {jwt_algorithm}"

    @pytest.mark.integration
    @pytest.mark.critical
    def test_oauth_configuration_incomplete_or_invalid(self):
        """
        EXPECTED TO FAIL - CRITICAL OAUTH CONFIG ISSUE
        OAuth configuration should be complete and valid for authentication
        Root cause: OAuth configuration incomplete, invalid, or missing
        """
        # Test OAuth configuration completeness
        oauth_config_vars = [
            'OAUTH_CLIENT_ID',
            'OAUTH_CLIENT_SECRET', 
            'OAUTH_REDIRECT_URI',
            'OAUTH_SCOPE',
            'OAUTH_PROVIDER_URL',
            'OAUTH_TOKEN_URL',
            'OAUTH_USERINFO_URL'
        ]
        
        # Clear OAuth configuration to simulate missing/invalid config
        for oauth_var in oauth_config_vars:
            if oauth_var in os.environ:
                del os.environ[oauth_var]
        
        env = IsolatedEnvironment()
        
        # Test OAuth configuration validity
        oauth_issues = []
        
        client_id = env.get('OAUTH_CLIENT_ID')
        if not client_id or len(client_id) < 20:
            oauth_issues.append(f"OAUTH_CLIENT_ID invalid: '{client_id}'")
        
        client_secret = env.get('OAUTH_CLIENT_SECRET')  
        if not client_secret or len(client_secret) < 20:
            oauth_issues.append(f"OAUTH_CLIENT_SECRET invalid: '{client_secret}'")
            
        redirect_uri = env.get('OAUTH_REDIRECT_URI')
        if not redirect_uri or not redirect_uri.startswith('http'):
            oauth_issues.append(f"OAUTH_REDIRECT_URI invalid: '{redirect_uri}'")
            
        scope = env.get('OAUTH_SCOPE', 'openid profile email')
        if not scope or 'openid' not in scope:
            oauth_issues.append(f"OAUTH_SCOPE invalid: '{scope}'")
        
        # Should NOT have OAuth configuration issues
        assert len(oauth_issues) == 0, f"OAuth configuration issues: {oauth_issues}"

    @pytest.mark.integration  
    @pytest.mark.critical
    def test_database_authentication_credentials_corrupted_by_sanitization(self):
        """
        EXPECTED TO FAIL - CRITICAL SANITIZATION ISSUE
        Database authentication credentials should not be corrupted by environment sanitization
        Root cause: Environment sanitization corrupting database passwords and connection strings
        """
        # Test database credentials with special characters (common in real environments)
        test_credentials = [
            ('POSTGRES_PASSWORD', 'P@ssw0rd!2024#$%'),
            ('CLICKHOUSE_PASSWORD', 'Ch!ckH0use&Pass*123'),
            ('REDIS_PASSWORD', 'Red!s@Pass#2024$'),
            ('DATABASE_URL', 'postgresql://user:P@ssw0rd!123@host:5432/db'),
            ('CLICKHOUSE_URL', 'http://user:Ch!ck@host:8123/db'),
            ('REDIS_URL', 'redis://:Red!s@Pass@host:6379/0')
        ]
        
        corruption_issues = []
        
        for var_name, original_value in test_credentials:
            os.environ[var_name] = original_value
            
            env = IsolatedEnvironment()
            sanitized_value = env.get(var_name)
            
            # Check for sanitization corruption
            if sanitized_value != original_value:
                corruption_issues.append(f"{var_name}: '{original_value}'  ->  '{sanitized_value}'")
            
            # Check for specific character corruption patterns
            if original_value and sanitized_value:
                special_chars = ['@', '!', '#', '$', '%', '&', '*']
                for char in special_chars:
                    if char in original_value and char not in sanitized_value:
                        corruption_issues.append(f"{var_name}: Missing '{char}' after sanitization")
        
        # Should NOT have credential corruption
        assert len(corruption_issues) == 0, f"Database credential corruption: {corruption_issues}"

    @pytest.mark.integration
    @pytest.mark.critical
    def test_ssl_certificates_missing_or_invalid_in_staging(self):
        """
        EXPECTED TO FAIL - CRITICAL SSL CERT ISSUE
        SSL certificates should be properly configured for staging environment
        Root cause: SSL certificate files missing or environment configuration invalid
        """
        # Test SSL certificate configuration for staging
        env.set('ENVIRONMENT', 'staging', "test")
        env.set('NODE_ENV', 'production', "test")
        
        ssl_cert_vars = [
            'SSL_CERT_PATH',
            'SSL_KEY_PATH', 
            'SSL_CA_CERT_PATH',
            'TLS_CERT_FILE',
            'TLS_KEY_FILE',
            'HTTPS_CERT',
            'HTTPS_KEY'
        ]
        
        # Clear SSL certificate configuration
        for cert_var in ssl_cert_vars:
            if cert_var in os.environ:
                del os.environ[cert_var]
        
        env = IsolatedEnvironment()
        
        ssl_issues = []
        
        # Check SSL certificate configuration
        for cert_var in ssl_cert_vars:
            cert_path = env.get(cert_var)
            
            if cert_var.endswith('_PATH') or cert_var.endswith('_FILE'):
                # Should be valid file path  
                if cert_path and not cert_path.endswith(('.pem', '.crt', '.key')):
                    ssl_issues.append(f"{cert_var}: Invalid certificate file extension: '{cert_path}'")
            
            if cert_var.startswith('SSL_CERT') or cert_var.startswith('TLS_CERT'):
                # Certificate files should exist in staging
                if not cert_path:
                    ssl_issues.append(f"{cert_var}: Missing in staging environment")
        
        # Should NOT have SSL certificate issues in staging
        assert len(ssl_issues) == 0, f"SSL certificate configuration issues: {ssl_issues}"

    @pytest.mark.integration
    @pytest.mark.critical
    def test_environment_specific_authentication_urls_incorrect(self):
        """
        EXPECTED TO FAIL - CRITICAL URL CONFIG ISSUE
        Environment-specific authentication URLs should be correct and reachable
        Root cause: Authentication service URLs incorrect for environment
        """
        # Test environment-specific URL configuration
        environments_urls = [
            ('development', {
                'AUTH_SERVICE_URL': 'http://localhost:8080',
                'BACKEND_URL': 'http://localhost:8000',
                'FRONTEND_URL': 'http://localhost:3000'
            }),
            ('staging', {
                'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
                'BACKEND_URL': 'https://api.staging.netrasystems.ai', 
                'FRONTEND_URL': 'https://app.staging.netrasystems.ai'
            }),
            ('production', {
                'AUTH_SERVICE_URL': 'https://auth.netrasystems.ai',
                'BACKEND_URL': 'https://api.netrasystems.ai',
                'FRONTEND_URL': 'https://app.netrasystems.ai'  
            })
        ]
        
        for env_name, expected_urls in environments_urls:
            env.set('ENVIRONMENT', env_name, "test")
            
            # Clear URL configuration
            for url_var in expected_urls.keys():
                if url_var in os.environ:
                    del os.environ[url_var]
            
            env = IsolatedEnvironment()
            url_issues = []
            
            for url_var, expected_url in expected_urls.items():
                actual_url = env.get(url_var)
                
                # Should have URL configured
                if not actual_url:
                    url_issues.append(f"{url_var}: Missing for {env_name} environment")
                    continue
                
                # Should be valid URL format
                if not actual_url.startswith(('http://', 'https://')):
                    url_issues.append(f"{url_var}: Invalid URL format for {env_name}: '{actual_url}'")
                    continue
                
                # Should match expected pattern for environment
                if env_name == 'development' and not actual_url.startswith('http://localhost'):
                    url_issues.append(f"{url_var}: Should use localhost for development: '{actual_url}'")
                elif env_name in ['staging', 'production'] and not actual_url.startswith('https://'):
                    url_issues.append(f"{url_var}: Should use HTTPS for {env_name}: '{actual_url}'")
            
            # Should NOT have URL configuration issues
            assert len(url_issues) == 0, f"Authentication URL issues for {env_name}: {url_issues}"

    @pytest.mark.integration
    @pytest.mark.medium
    def test_secrets_management_integration_broken(self):
        """
        EXPECTED TO FAIL - MEDIUM SECRETS ISSUE
        Secrets management integration should provide authentication secrets
        Root cause: Integration with secrets management (Google Secret Manager, etc.) broken
        """
        # Test secrets management integration
        with patch('google.cloud.secretmanager.SecretManagerServiceClient') as mock_secrets:
            # Mock secrets management failure
            mock_secrets.return_value.access_secret_version.side_effect = Exception(
                "Unable to access secret: permission denied or service unavailable"
            )
            
            secret_names = [
                'jwt-secret-key',
                'oauth-client-secret', 
                'database-password',
                'service-account-key'
            ]
            
            env = IsolatedEnvironment()
            
            # Should be able to retrieve secrets from secrets manager
            for secret_name in secret_names:
                try:
                    # This should work but will fail due to broken integration
                    secret_value = env.get_secret(secret_name)
                    
                    assert secret_value is not None, f"Secret {secret_name} should be retrievable"
                    assert secret_value != "", f"Secret {secret_name} should not be empty"
                    
                except Exception as e:
                    # Should NOT fail to retrieve secrets
                    assert "permission denied" not in str(e), f"Secrets management permission issue: {str(e)}"
                    assert "service unavailable" not in str(e), f"Secrets management service issue: {str(e)}"

    @pytest.mark.integration
    @pytest.mark.medium
    def test_container_environment_variable_injection_failures(self):
        """
        EXPECTED TO FAIL - MEDIUM CONTAINER ISSUE
        Container environment should properly inject authentication variables
        Root cause: Docker/container environment variable injection not working
        """
        # Test container environment variable injection patterns
        container_auth_vars = {
            'NETRA_JWT_SECRET': 'container-jwt-secret-12345',
            'NETRA_OAUTH_CLIENT_ID': 'container-oauth-client-id',
            'NETRA_SERVICE_ACCOUNT': '{"type": "service_account"}',
            'NETRA_DATABASE_URL': 'postgresql://container:pass@db:5432/netra'
        }
        
        # Simulate container environment injection
        for var_name, var_value in container_auth_vars.items():
            os.environ[var_name] = var_value
        
        env = IsolatedEnvironment()
        injection_issues = []
        
        for var_name, expected_value in container_auth_vars.items():
            actual_value = env.get(var_name)
            
            if actual_value != expected_value:
                injection_issues.append(f"{var_name}: Expected '{expected_value}', got '{actual_value}'")
            
            # Check for container-specific prefixes
            if var_name.startswith('NETRA_') and not actual_value:
                injection_issues.append(f"{var_name}: Container variable injection failed")
        
        # Should NOT have container injection issues
        assert len(injection_issues) == 0, f"Container environment injection issues: {injection_issues}"

    @pytest.mark.integration
    @pytest.mark.medium
    def test_ci_cd_pipeline_environment_authentication_failures(self):
        """
        EXPECTED TO FAIL - MEDIUM CI/CD ISSUE
        CI/CD pipeline environment should have authentication configuration
        Root cause: CI/CD environment missing authentication configuration
        """
        # Simulate CI/CD environment
        ci_cd_env_vars = [
            'CI',
            'GITHUB_ACTIONS',
            'PIPELINE_ENV'
        ]
        
        for ci_var in ci_cd_env_vars:
            os.environ[ci_var] = 'true'
        
        env.set('ENVIRONMENT', 'ci', "test")
        
        env = IsolatedEnvironment()
        
        # CI/CD should have authentication configuration
        ci_auth_requirements = [
            ('NETRA_TEST_API_KEY', 'test-api-key-for-ci'),
            ('NETRA_TEST_JWT_SECRET', 'test-jwt-secret-for-ci'),
            ('NETRA_TEST_SERVICE_ACCOUNT', '{"type": "service_account", "project_id": "test"}')
        ]
        
        ci_issues = []
        
        for var_name, test_value in ci_auth_requirements:
            # Clear to simulate missing CI configuration
            if var_name in os.environ:
                del os.environ[var_name]
            
            actual_value = env.get(var_name)
            
            if not actual_value:
                ci_issues.append(f"{var_name}: Missing in CI/CD environment")
            elif len(actual_value) < 10:
                ci_issues.append(f"{var_name}: Too short in CI/CD environment: '{actual_value}'")
        
        # Should NOT have CI/CD authentication issues
        assert len(ci_issues) == 0, f"CI/CD authentication configuration issues: {ci_issues}"

    @pytest.mark.integration
    @pytest.mark.critical
    def test_environment_override_configuration_failing(self):
        """
        EXPECTED TO FAIL - CRITICAL OVERRIDE ISSUE
        Environment-specific configuration overrides should work properly
        Root cause: Environment override mechanism not working for authentication config
        """
        # Test environment configuration override mechanism
        base_config = {
            'JWT_SECRET_KEY': 'base-jwt-secret',
            'AUTH_SERVICE_URL': 'http://localhost:8080',
            'OAUTH_CLIENT_ID': 'base-oauth-client-id'
        }
        
        staging_overrides = {
            'JWT_SECRET_KEY': 'staging-jwt-secret-override',
            'AUTH_SERVICE_URL': 'https://auth.staging.netrasystems.ai',
            'OAUTH_CLIENT_ID': 'staging-oauth-client-id-override'
        }
        
        # Set base configuration
        for var_name, var_value in base_config.items():
            os.environ[var_name] = var_value
        
        # Set staging environment
        env.set('ENVIRONMENT', 'staging', "test")
        
        # Set staging overrides (should override base config)
        for var_name, var_value in staging_overrides.items():
            os.environ[f"{var_name}_STAGING"] = var_value
        
        env = IsolatedEnvironment()
        override_issues = []
        
        for var_name, expected_override in staging_overrides.items():
            # Should get override value, not base value
            actual_value = env.get(var_name)
            base_value = base_config[var_name]
            
            if actual_value == base_value:
                override_issues.append(f"{var_name}: Override not applied (still using base: '{base_value}')")
            elif actual_value != expected_override:
                override_issues.append(f"{var_name}: Override incorrect (expected '{expected_override}', got '{actual_value}')")
        
        # Should NOT have override configuration issues
        assert len(override_issues) == 0, f"Environment override issues: {override_issues}"