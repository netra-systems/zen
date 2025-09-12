#!/usr/bin/env python3
"""
Regression test suite for GCP deployment configuration.
Ensures critical environment variables and secrets are properly configured.

CRITICAL: This test prevents deployment failures due to missing environment variables.
"""

from test_framework.ssot.base_test_case import SSotAsyncTestCase, SSotBaseTestCase
import sys
import os
import unittest
from pathlib import Path
from typing import Dict, List, Set
import json
import subprocess
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestGCPDeploymentRegression(SSotBaseTestCase):
    """Regression tests for GCP deployment configuration."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment."""
        cls.project_root = project_root
        cls.deployment_script = cls.project_root / "scripts" / "deploy_to_gcp.py"
        
        # Load deployment script for analysis
        with open(cls.deployment_script, 'r', encoding='utf-8') as f:
            cls.deployment_code = f.read()
    
    def test_gcp_project_id_in_backend_env_vars(self):
        """Test that GCP_PROJECT_ID is present in backend environment variables."""
        # Check that backend service config includes GCP_PROJECT_ID
        self.assertIn('"GCP_PROJECT_ID": self.project_id', self.deployment_code,
                     "Backend service must include GCP_PROJECT_ID environment variable")
        
        # Verify it's in the backend service specifically
        backend_start = self.deployment_code.find('name="backend"')
        backend_end = self.deployment_code.find('ServiceConfig(', backend_start + 1)
        backend_section = self.deployment_code[backend_start:backend_end] if backend_end > 0 else self.deployment_code[backend_start:]
        
        self.assertIn('GCP_PROJECT_ID', backend_section,
                     "Backend service configuration must include GCP_PROJECT_ID")
    
    def test_gcp_project_id_in_auth_env_vars(self):
        """Test that GCP_PROJECT_ID is present in auth service environment variables."""
        # Check that auth service config includes GCP_PROJECT_ID  
        auth_start = self.deployment_code.find('name="auth"')
        auth_end = self.deployment_code.find('ServiceConfig(', auth_start + 1)
        auth_section = self.deployment_code[auth_start:auth_end] if auth_end > 0 else self.deployment_code[auth_start:]
        
        self.assertIn('GCP_PROJECT_ID', auth_section,
                     "Auth service configuration must include GCP_PROJECT_ID")
    
    def test_critical_backend_environment_variables(self):
        """Test that all critical backend environment variables are configured."""
        required_backend_vars = [
            "ENVIRONMENT",
            "PYTHONUNBUFFERED", 
            "AUTH_SERVICE_URL",
            "FRONTEND_URL",
            "FORCE_HTTPS",
            "GCP_PROJECT_ID"  # CRITICAL: Required for secret loading
        ]
        
        backend_start = self.deployment_code.find('name="backend"')
        backend_end = self.deployment_code.find('ServiceConfig(', backend_start + 1)
        backend_section = self.deployment_code[backend_start:backend_end] if backend_end > 0 else self.deployment_code[backend_start:]
        
        for var in required_backend_vars:
            self.assertIn(f'"{var}"', backend_section,
                         f"Backend must include {var} environment variable")
    
    def test_critical_auth_environment_variables(self):
        """Test that all critical auth service environment variables are configured."""
        required_auth_vars = [
            "ENVIRONMENT",
            "PYTHONUNBUFFERED",
            "FRONTEND_URL", 
            "AUTH_SERVICE_URL",
            "JWT_ALGORITHM",
            "JWT_ACCESS_EXPIRY_MINUTES",
            "JWT_REFRESH_EXPIRY_DAYS",
            "JWT_SERVICE_EXPIRY_MINUTES",
            "SESSION_TTL_HOURS",
            "REDIS_DISABLED",
            "SHUTDOWN_TIMEOUT_SECONDS",
            "SECURE_HEADERS_ENABLED",
            "LOG_ASYNC_CHECKOUT",
            "AUTH_FAST_TEST_MODE",
            "USE_MEMORY_DB",
            "FORCE_HTTPS",
            "GCP_PROJECT_ID"  # CRITICAL: Required for secret loading
        ]
        
        auth_start = self.deployment_code.find('name="auth"')
        auth_end = self.deployment_code.find('ServiceConfig(', auth_start + 1)
        auth_section = self.deployment_code[auth_start:auth_end] if auth_end > 0 else self.deployment_code[auth_start:]
        
        for var in required_auth_vars:
            self.assertIn(f'"{var}"', auth_section,
                         f"Auth service must include {var} environment variable")
    
    def test_backend_secret_manager_configuration(self):
        """Test that backend has all required secrets configured in Secret Manager."""
        required_secrets = [
            "POSTGRES_HOST",
            "POSTGRES_PORT", 
            "POSTGRES_DB",
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "JWT_SECRET_KEY",
            "SECRET_KEY",
            "OPENAI_API_KEY",
            "FERNET_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
            "SERVICE_SECRET",
            "REDIS_URL",
            "REDIS_PASSWORD",
            "ANTHROPIC_API_KEY"
        ]
        
        # Find the backend secrets configuration
        backend_secrets_marker = 'if service.name == "backend":'
        backend_secrets_start = self.deployment_code.find(backend_secrets_marker)
        self.assertNotEqual(backend_secrets_start, -1, "Backend secrets configuration not found")
        
        # Find the --set-secrets line for backend
        set_secrets_start = self.deployment_code.find('--set-secrets', backend_secrets_start)
        set_secrets_end = self.deployment_code.find('])', set_secrets_start)
        secrets_section = self.deployment_code[set_secrets_start:set_secrets_end]
        
        for secret in required_secrets:
            self.assertIn(secret, secrets_section,
                         f"Backend must configure {secret} from Secret Manager")
    
    def test_auth_secret_manager_configuration(self):
        """Test that auth service has all required secrets configured in Secret Manager."""
        required_secrets = [
            "POSTGRES_HOST",
            "POSTGRES_PORT",
            "POSTGRES_DB", 
            "POSTGRES_USER",
            "POSTGRES_PASSWORD",
            "JWT_SECRET_KEY",
            "JWT_SECRET",
            "GOOGLE_OAUTH_CLIENT_ID_STAGING",
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
            "SERVICE_SECRET",
            "SERVICE_ID",
            "OAUTH_HMAC_SECRET",
            "REDIS_URL",
            "REDIS_PASSWORD"
        ]
        
        # Find the auth secrets configuration
        auth_secrets_marker = 'elif service.name == "auth":'
        auth_secrets_start = self.deployment_code.find(auth_secrets_marker)
        self.assertNotEqual(auth_secrets_start, -1, "Auth secrets configuration not found")
        
        # Find the --set-secrets line for auth
        set_secrets_start = self.deployment_code.find('--set-secrets', auth_secrets_start)
        set_secrets_end = self.deployment_code.find('])', set_secrets_start)
        secrets_section = self.deployment_code[set_secrets_start:set_secrets_end]
        
        for secret in required_secrets:
            self.assertIn(secret, secrets_section,
                         f"Auth service must configure {secret} from Secret Manager")
    
    def test_cloud_sql_instances_configured(self):
        """Test that Cloud SQL instances are properly configured for services."""
        # Both backend and auth need Cloud SQL
        backend_marker = 'if service.name == "backend":'
        auth_marker = 'elif service.name == "auth":'
        
        for marker, service_name in [(backend_marker, "backend"), (auth_marker, "auth")]:
            service_start = self.deployment_code.find(marker)
            service_end = self.deployment_code.find('elif ', service_start + 1)
            if service_end == -1:
                service_end = self.deployment_code.find('try:', service_start)
            
            service_section = self.deployment_code[service_start:service_end]
            
            self.assertIn('--add-cloudsql-instances', service_section,
                         f"{service_name} must configure Cloud SQL instances")
            self.assertIn('staging-shared-postgres', service_section,
                         f"{service_name} must include staging-shared-postgres instance")
    
    def test_oauth_configuration_validation(self):
        """Test that OAuth configuration validation is performed before deployment."""
        # Check for OAuth validation method
        self.assertIn('def _validate_oauth_configuration', self.deployment_code,
                     "OAuth validation method must exist")
        
        # Check that validation is called before deployment
        self.assertIn('oauth_validation_success = self._validate_oauth_configuration()', 
                     self.deployment_code,
                     "OAuth validation must be called during deployment")
        
        # Check for validation failure handling
        self.assertIn('DEPLOYMENT ABORTED - OAuth validation failed', self.deployment_code,
                     "Deployment must abort if OAuth validation fails")
    
    def test_environment_detection_logic(self):
        """Test that environment detection logic properly sets GCP_PROJECT_ID."""
        # Check that self.project_id is used for GCP_PROJECT_ID
        self.assertIn('"GCP_PROJECT_ID": self.project_id', self.deployment_code,
                     "GCP_PROJECT_ID must be set from self.project_id")
        
        # Verify project_id is properly initialized
        self.assertIn('def __init__(self, project_id:', self.deployment_code,
                     "GCPDeployer must accept project_id parameter")
        self.assertIn('self.project_id = project_id', self.deployment_code,
                     "project_id must be stored as instance variable")
    
    def test_memory_and_cpu_allocation(self):
        """Test that services have appropriate memory and CPU allocations."""
        # Backend should have sufficient resources
        backend_start = self.deployment_code.find('name="backend"')
        backend_end = self.deployment_code.find('ServiceConfig(', backend_start + 1)
        backend_section = self.deployment_code[backend_start:backend_end]
        
        self.assertIn('memory="1Gi"', backend_section,
                     "Backend should have at least 1Gi memory")
        self.assertIn('cpu="2"', backend_section,
                     "Backend should have at least 2 CPU cores")
        
        # Auth service configuration
        auth_start = self.deployment_code.find('name="auth"')
        auth_end = self.deployment_code.find('ServiceConfig(', auth_start + 1)
        auth_section = self.deployment_code[auth_start:auth_end]
        
        self.assertIn('memory="512Mi"', auth_section,
                     "Auth service should have at least 512Mi memory")
    
    def test_staging_urls_configuration(self):
        """Test that staging URLs are properly configured."""
        staging_urls = [
            'https://auth.staging.netrasystems.ai',
            'https://api.staging.netrasystems.ai',
            'https://app.staging.netrasystems.ai'
        ]
        
        for url in staging_urls:
            self.assertIn(url, self.deployment_code,
                         f"Staging URL {url} must be configured")
    
    def test_redis_configuration(self):
        """Test that Redis is properly configured with correct IP address."""
        # Check that Redis URL uses the correct staging IP
        self.assertIn('10.107.0.3', self.deployment_code,
                     "Redis must use correct staging IP address (10.107.0.3)")
        
        # Verify Redis is not disabled in auth service
        auth_start = self.deployment_code.find('name="auth"')
        auth_end = self.deployment_code.find('ServiceConfig(', auth_start + 1)
        auth_section = self.deployment_code[auth_start:auth_end]
        
        self.assertIn('"REDIS_DISABLED": "false"', auth_section,
                     "Redis must not be disabled in auth service")
    
    def test_critical_deployment_flags(self):
        """Test that critical deployment flags are properly set."""
        # Check for ingress configuration
        self.assertIn('"--ingress", "all"', self.deployment_code,
                     "Ingress must be set to 'all' for load balancer compatibility")
        
        # Check for execution environment
        self.assertIn('"--execution-environment", "gen2"', self.deployment_code,
                     "Must use gen2 execution environment")
        
        # Check for CPU throttling
        self.assertIn('"--no-cpu-throttling"', self.deployment_code,
                     "CPU throttling must be disabled for performance")
    
    def test_pre_deployment_validation(self):
        """Test that pre-deployment validation includes all necessary checks."""
        # Check for architecture compliance
        self.assertIn('Architecture Compliance', self.deployment_code,
                     "Must run architecture compliance check")
        
        # Check for integration tests
        self.assertIn('Integration Tests', self.deployment_code,
                     "Must run integration tests before deployment")
        
        # Check for secrets validation
        self.assertIn('validate_secrets_before_deployment', self.deployment_code,
                     "Must validate secrets before deployment")
    
    def test_jwt_secret_consistency(self):
        """Test that JWT secrets are configured consistently between services."""
        # Find setup_secrets method
        setup_secrets_start = self.deployment_code.find('def setup_secrets')
        setup_secrets_end = self.deployment_code.find('def ', setup_secrets_start + 1)
        setup_secrets_section = self.deployment_code[setup_secrets_start:setup_secrets_end]
        
        # Check that JWT secrets use the same value
        self.assertIn('jwt_secret_value =', setup_secrets_section,
                     "JWT secret value must be defined once")
        self.assertIn('"jwt-secret-key-staging": jwt_secret_value', setup_secrets_section,
                     "Backend JWT secret must use shared value")
        self.assertIn('"jwt-secret-staging": jwt_secret_value', setup_secrets_section,
                     "Auth JWT secret must use shared value")
    
    def test_health_check_implementation(self):
        """Test that health checks are properly implemented."""
        self.assertIn('def health_check', self.deployment_code,
                     "Health check method must exist")
        
        # Check for proper health endpoints
        self.assertIn('/health', self.deployment_code,
                     "Must check /health endpoint for services")
        
        # Check for timeout in health checks
        self.assertIn('timeout=10', self.deployment_code,
                     "Health checks must have timeout")
    
    def test_post_deployment_tests(self):
        """Test that post-deployment tests are configured."""
        self.assertIn('run_post_deployment_tests', self.deployment_code,
                     "Post-deployment tests must be available")
        
        self.assertIn('PostDeploymentAuthTest', self.deployment_code,
                     "Must import PostDeploymentAuthTest for validation")
    
    def test_service_account_authentication(self):
        """Test that service account authentication is properly configured."""
        self.assertIn('authenticate_with_service_account', self.deployment_code,
                     "Service account authentication method must exist")
        
        self.assertIn('GCPAuthConfig', self.deployment_code,
                     "Must use centralized GCP auth configuration")
    
    def test_error_handling_and_rollback(self):
        """Test that deployment has proper error handling."""
        # Check for revision readiness waiting
        self.assertIn('wait_for_revision_ready', self.deployment_code,
                     "Must wait for revision to be ready")
        
        # Check for traffic update to latest
        self.assertIn('update_traffic_to_latest', self.deployment_code,
                     "Must update traffic to latest revision")
        
        # Check for deployment failure handling
        self.assertIn('except subprocess.CalledProcessError', self.deployment_code,
                     "Must handle subprocess errors properly")


def run_regression_tests():
    """Run the regression test suite."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestGCPDeploymentRegression)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Return success status
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_regression_tests()
    sys.exit(0 if success else 1)