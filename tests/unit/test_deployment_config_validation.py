"""
Unit tests for deployment configuration validation.
Tests to prevent staging deployment failures due to missing configurations.

Related incidents:
- FIVE_WHYS_STAGING_CONFIG_FAILURE_20250905.md
- SPEC/learnings/cloud_run_config_failure_20250905.xml
- STAGING_CONFIG_REMEDIATION_PLAN.md
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class TestDeploymentConfigValidation(unittest.TestCase):
    """Test suite for deployment configuration validation."""
    
    # Critical environment variables that MUST be present
    REQUIRED_ENV_VARS = [
        'DATABASE_URL',
        'JWT_SECRET_KEY', 
        'SECRET_KEY',
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_DB',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'ENV',
        'REDIS_HOST',
        'REDIS_PORT',
        'BACKEND_URL',
        'FRONTEND_URL',
        'API_BASE_URL'
    ]
    
    # Google Secret Manager secrets that must exist
    REQUIRED_GSM_SECRETS = [
        'jwt-secret-staging',
        'secret-key-staging',
        'postgres-password-staging',
        'postgres-user-staging',
        'postgres-db-staging',
        'redis-host-staging'
    ]
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_subprocess = patch('subprocess.run').start()
        self.mock_subprocess.return_value = Mock(
            returncode=0,
            stdout='',
            stderr=''
        )
        
    def tearDown(self):
        """Clean up patches."""
        patch.stopall()
        
    def test_all_required_env_vars_defined(self):
        """Test that all required environment variables are defined in config."""
        # This tests that our list of required vars is complete
        self.assertEqual(len(self.REQUIRED_ENV_VARS), 14, 
                        "Should have exactly 14 required environment variables")
        
        # Verify critical vars are in the list
        critical_vars = ['DATABASE_URL', 'JWT_SECRET_KEY', 'POSTGRES_HOST']
        for var in critical_vars:
            self.assertIn(var, self.REQUIRED_ENV_VARS,
                         f"{var} must be in required environment variables")
    
    @patch('subprocess.run')
    def test_validate_cloud_run_has_env_vars(self, mock_run):
        """Test validation that Cloud Run service has all required env vars."""
        # Simulate Cloud Run service with missing env vars
        mock_run.return_value = Mock(
            returncode=0,
            stdout='ENV\nDATABASE_URL\n',  # Only 2 of 14 required
            stderr=''
        )
        
        from scripts.deploy_to_gcp import validate_cloud_run_env_vars
        
        with self.assertRaises(ValueError) as context:
            validate_cloud_run_env_vars('netra-backend', 'netra-staging', 'us-central1')
        
        error_message = str(context.exception)
        self.assertIn('Missing required env vars', error_message)
        self.assertIn('JWT_SECRET_KEY', error_message)
        self.assertIn('POSTGRES_HOST', error_message)
        
    @patch('subprocess.run')
    def test_validate_gsm_secrets_exist(self, mock_run):
        """Test validation that Google Secret Manager has all required secrets."""
        # Simulate GSM with missing secrets
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {'name': 'projects/netra-staging/secrets/jwt-secret-staging'},
                {'name': 'projects/netra-staging/secrets/secret-key-staging'}
                # Missing postgres-password-staging and others
            ]),
            stderr=''
        )
        
        from scripts.validate_secrets import validate_gsm_secrets_exist
        
        missing_secrets = validate_gsm_secrets_exist('netra-staging', self.REQUIRED_GSM_SECRETS)
        
        self.assertGreater(len(missing_secrets), 0, "Should detect missing secrets")
        self.assertIn('postgres-password-staging', missing_secrets)
        self.assertIn('redis-host-staging', missing_secrets)
        
    def test_deployment_config_completeness(self):
        """Test that deployment config includes all required settings."""
        from deployment.secrets_config import BACKEND_SECRETS, AUTH_SECRETS
        
        # Check backend secrets configuration
        backend_secret_keys = list(BACKEND_SECRETS.keys())
        critical_backend_secrets = [
            'DATABASE_URL',
            'POSTGRES_PASSWORD',
            'JWT_SECRET_KEY',
            'SECRET_KEY'
        ]
        
        for secret in critical_backend_secrets:
            self.assertIn(secret, backend_secret_keys,
                         f"Backend must have {secret} in secrets config")
            
    @patch.dict(os.environ, {}, clear=True)
    def test_staging_config_validation(self):
        """Test that staging configuration validates required fields."""
        from netra_backend.config.staging import StagingConfig
        
        # Test that config raises error when critical vars missing
        with self.assertRaises((ValueError, KeyError)) as context:
            config = StagingConfig()
            # Attempt to access critical config
            _ = config.database_url
            
    def test_deployment_script_validates_before_deploy(self):
        """Test that deployment script validates configuration before deploying."""
        with patch('scripts.deploy_to_gcp.validate_secrets_before_deployment') as mock_validate:
            with patch('scripts.deploy_to_gcp.deploy_service') as mock_deploy:
                mock_validate.return_value = False  # Validation fails
                
                from scripts.deploy_to_gcp import main
                
                # Should not reach deploy when validation fails
                with self.assertRaises(SystemExit):
                    main(['--project', 'netra-staging'])
                    
                mock_deploy.assert_not_called()
                
    def test_health_check_reports_missing_config(self):
        """Test that health check endpoint reports configuration issues."""
        from netra_backend.app.services.health.deep_checks import validate_configuration
        
        with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
            issues = validate_configuration()
            
            self.assertGreater(len(issues), 0, "Should detect configuration issues")
            
            # Should report specific missing configs
            issue_text = ' '.join(issues)
            self.assertIn('DATABASE_URL', issue_text)
            self.assertIn('JWT_SECRET_KEY', issue_text)
            
    @patch('subprocess.run')
    def test_cloud_run_probe_with_missing_config(self, mock_run):
        """Test that Cloud Run probe fails when configuration is missing."""
        # Simulate probe failure due to missing config
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='Default STARTUP TCP probe failed 1 time consecutively'
        )
        
        from scripts.deploy_to_gcp import check_service_health
        
        is_healthy = check_service_health('netra-backend', 'netra-staging', 'us-central1')
        
        self.assertFalse(is_healthy, "Service should not be healthy with missing config")
        
    def test_config_validation_error_messages(self):
        """Test that configuration validation provides clear error messages."""
        from netra_backend.config.base import validate_required_configs
        
        missing_configs = ['DATABASE_URL', 'JWT_SECRET_KEY', 'REDIS_HOST']
        error_message = validate_required_configs({}, self.REQUIRED_ENV_VARS)
        
        self.assertIn('CRITICAL', error_message)
        self.assertIn('Missing required config', error_message)
        
        for config in missing_configs:
            self.assertIn(config, error_message,
                         f"Error message should mention missing {config}")
                         
    def test_deployment_rollback_on_config_failure(self):
        """Test that deployment rolls back when configuration validation fails."""
        with patch('scripts.deploy_to_gcp.deploy_to_cloud_run') as mock_deploy:
            with patch('scripts.deploy_to_gcp.validate_deployment') as mock_validate:
                with patch('scripts.deploy_to_gcp.rollback_deployment') as mock_rollback:
                    
                    mock_deploy.return_value = True
                    mock_validate.return_value = False  # Post-deploy validation fails
                    
                    from scripts.deploy_to_gcp import deploy_with_validation
                    
                    result = deploy_with_validation('netra-backend', 'netra-staging')
                    
                    self.assertFalse(result)
                    mock_rollback.assert_called_once()
                    
    def test_secrets_config_matches_required_vars(self):
        """Test that secrets config covers all required environment variables."""
        from deployment.secrets_config import get_all_configured_secrets
        
        configured_secrets = get_all_configured_secrets('backend')
        
        # Map of env var to secret name patterns
        env_to_secret_mapping = {
            'DATABASE_URL': 'database-url',
            'JWT_SECRET_KEY': 'jwt-secret',
            'SECRET_KEY': 'secret-key',
            'POSTGRES_PASSWORD': 'postgres-password',
        }
        
        for env_var, secret_pattern in env_to_secret_mapping.items():
            found = any(secret_pattern in secret.lower() 
                       for secret in configured_secrets)
            self.assertTrue(found,
                          f"No secret configured for {env_var}")
                          
    def test_prevent_deployment_with_localhost_urls(self):
        """Test that deployment prevents localhost URLs in staging/production."""
        test_configs = {
            'ENV': 'staging',
            'BACKEND_URL': 'http://localhost:8000',  # Invalid for staging
            'FRONTEND_URL': 'http://localhost:3000',  # Invalid for staging
            'API_BASE_URL': 'http://localhost:8000'   # Invalid for staging
        }
        
        from netra_backend.config.base import validate_urls_for_environment
        
        issues = validate_urls_for_environment(test_configs, 'staging')
        
        self.assertGreater(len(issues), 0, "Should detect localhost URLs in staging")
        self.assertIn('localhost', ' '.join(issues))
        
    def test_cloud_sql_connection_format(self):
        """Test that Cloud SQL connections use Unix socket format."""
        valid_formats = [
            'postgresql://user:pass@/db?host=/cloudsql/project:region:instance',
            '/cloudsql/project:region:instance'
        ]
        
        invalid_formats = [
            'postgresql://user:pass@10.0.0.1:5432/db',  # TCP instead of socket
            'localhost:5432',  # Localhost 
            '127.0.0.1'  # Loopback
        ]
        
        from netra_backend.config.base import validate_cloud_sql_format
        
        for valid in valid_formats:
            self.assertTrue(validate_cloud_sql_format(valid),
                          f"{valid} should be valid Cloud SQL format")
                          
        for invalid in invalid_formats:
            self.assertFalse(validate_cloud_sql_format(invalid),
                           f"{invalid} should be invalid for Cloud SQL")


class TestDeploymentScriptIntegration(unittest.TestCase):
    """Integration tests for deployment script configuration handling."""
    
    @patch('subprocess.run')
    def test_full_deployment_flow_with_validation(self, mock_run):
        """Test complete deployment flow with configuration validation."""
        # Mock successful responses for all checks
        mock_run.side_effect = [
            # GSM secrets exist check
            Mock(returncode=0, stdout=json.dumps([
                {'name': f'projects/netra-staging/secrets/{secret}'}
                for secret in TestDeploymentConfigValidation.REQUIRED_GSM_SECRETS
            ])),
            # Cloud Run deployment
            Mock(returncode=0, stdout='Service deployed'),
            # Post-deployment validation
            Mock(returncode=0, stdout='\n'.join(
                TestDeploymentConfigValidation.REQUIRED_ENV_VARS
            ))
        ]
        
        from scripts.deploy_to_gcp import full_deployment_with_validation
        
        result = full_deployment_with_validation(
            project='netra-staging',
            service='netra-backend',
            region='us-central1'
        )
        
        self.assertTrue(result, "Deployment should succeed with all configs present")
        
        # Verify all validation steps were called
        self.assertEqual(mock_run.call_count, 3)
        
    @patch('subprocess.run')
    def test_deployment_fails_fast_on_missing_secrets(self, mock_run):
        """Test that deployment fails immediately when secrets are missing."""
        # Mock missing secrets
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([])  # No secrets exist
        )
        
        from scripts.deploy_to_gcp import full_deployment_with_validation
        
        with self.assertRaises(ValueError) as context:
            full_deployment_with_validation(
                project='netra-staging',
                service='netra-backend',
                region='us-central1'
            )
            
        self.assertIn('Missing required secrets', str(context.exception))
        
        # Should only call once for secret check, not proceed to deployment
        self.assertEqual(mock_run.call_count, 1)


class TestConfigurationMonitoring(unittest.TestCase):
    """Tests for ongoing configuration monitoring and drift detection."""
    
    def test_config_drift_detection(self):
        """Test detection of configuration drift from expected state."""
        expected_config = {
            'DATABASE_URL': 'postgresql://user:pass@/db?host=/cloudsql/instance',
            'JWT_SECRET_KEY': 'expected_secret',
            'ENV': 'staging'
        }
        
        actual_config = {
            'DATABASE_URL': 'postgresql://user:pass@/db?host=/cloudsql/instance',
            'JWT_SECRET_KEY': 'different_secret',  # Drifted
            # ENV is missing - also drift
        }
        
        from scripts.monitor_config_drift import detect_drift
        
        drift = detect_drift(expected_config, actual_config)
        
        self.assertEqual(len(drift), 2, "Should detect 2 drifted configs")
        self.assertIn('JWT_SECRET_KEY', drift)
        self.assertIn('ENV', drift)
        
    def test_config_compliance_report(self):
        """Test generation of configuration compliance report."""
        from scripts.generate_config_compliance import generate_report
        
        report = generate_report(
            service='netra-backend',
            environment='staging',
            required_vars=TestDeploymentConfigValidation.REQUIRED_ENV_VARS
        )
        
        self.assertIn('Configuration Compliance Report', report)
        self.assertIn('Required Variables', report)
        self.assertIn('Missing Variables', report)
        self.assertIn('Recommendations', report)


if __name__ == '__main__':
    # Run with verbose output to see all test results
    unittest.main(verbosity=2)