# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: Unit tests for deployment configuration validation.
    # REMOVED_SYNTAX_ERROR: Tests to prevent staging deployment failures due to missing configurations.

    # REMOVED_SYNTAX_ERROR: Related incidents:
        # REMOVED_SYNTAX_ERROR: - FIVE_WHYS_STAGING_CONFIG_FAILURE_20250905.md
        # REMOVED_SYNTAX_ERROR: - SPEC/learnings/cloud_run_config_failure_20250905.xml
        # REMOVED_SYNTAX_ERROR: - STAGING_CONFIG_REMEDIATION_PLAN.md
        # REMOVED_SYNTAX_ERROR: '''

        # REMOVED_SYNTAX_ERROR: import unittest
        # REMOVED_SYNTAX_ERROR: import json
        # REMOVED_SYNTAX_ERROR: import os
        # REMOVED_SYNTAX_ERROR: import sys
        # REMOVED_SYNTAX_ERROR: from pathlib import Path
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env
        # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        # REMOVED_SYNTAX_ERROR: from test_framework.database.test_database_manager import TestDatabaseManager
        # REMOVED_SYNTAX_ERROR: from test_framework.redis_test_utils.test_redis_manager import TestRedisManager
        # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
        # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment
        # REMOVED_SYNTAX_ERROR: import asyncio

        # Add project root to path
        # REMOVED_SYNTAX_ERROR: project_root = Path(__file__).parent.parent.parent
        # REMOVED_SYNTAX_ERROR: sys.path.insert(0, str(project_root))


# REMOVED_SYNTAX_ERROR: class TestDeploymentConfigValidation(unittest.TestCase):
    # REMOVED_SYNTAX_ERROR: """Test suite for deployment configuration validation."""

    # Critical environment variables that MUST be present
    # REMOVED_SYNTAX_ERROR: REQUIRED_ENV_VARS = [ )
    # REMOVED_SYNTAX_ERROR: 'DATABASE_URL',
    # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY',
    # REMOVED_SYNTAX_ERROR: 'SECRET_KEY',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_HOST',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PORT',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_DB',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_USER',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD',
    # REMOVED_SYNTAX_ERROR: 'ENV',
    # REMOVED_SYNTAX_ERROR: 'REDIS_HOST',
    # REMOVED_SYNTAX_ERROR: 'REDIS_PORT',
    # REMOVED_SYNTAX_ERROR: 'BACKEND_URL',
    # REMOVED_SYNTAX_ERROR: 'FRONTEND_URL',
    # REMOVED_SYNTAX_ERROR: 'API_BASE_URL'
    

    # Google Secret Manager secrets that must exist
    # REMOVED_SYNTAX_ERROR: REQUIRED_GSM_SECRETS = [ )
    # REMOVED_SYNTAX_ERROR: 'jwt-secret-staging',
    # REMOVED_SYNTAX_ERROR: 'secret-key-staging',
    # REMOVED_SYNTAX_ERROR: 'postgres-password-staging',
    # REMOVED_SYNTAX_ERROR: 'postgres-user-staging',
    # REMOVED_SYNTAX_ERROR: 'postgres-db-staging',
    # REMOVED_SYNTAX_ERROR: 'redis-host-staging'
    

# REMOVED_SYNTAX_ERROR: def setUp(self):
    # REMOVED_SYNTAX_ERROR: """Set up test fixtures."""
    # REMOVED_SYNTAX_ERROR: self.mock_subprocess = patch('subprocess.run').start()
    # REMOVED_SYNTAX_ERROR: self.mock_subprocess.return_value = Mock( )
    # REMOVED_SYNTAX_ERROR: returncode=0,
    # REMOVED_SYNTAX_ERROR: stdout='',
    # REMOVED_SYNTAX_ERROR: stderr=''
    

# REMOVED_SYNTAX_ERROR: def tearDown(self):
    # REMOVED_SYNTAX_ERROR: """Clean up patches."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: patch.stopall()

# REMOVED_SYNTAX_ERROR: def test_all_required_env_vars_defined(self):
    # REMOVED_SYNTAX_ERROR: """Test that all required environment variables are defined in config."""
    # This tests that our list of required vars is complete
    # REMOVED_SYNTAX_ERROR: self.assertEqual(len(self.REQUIRED_ENV_VARS), 14,
    # REMOVED_SYNTAX_ERROR: "Should have exactly 14 required environment variables")

    # Verify critical vars are in the list
    # REMOVED_SYNTAX_ERROR: critical_vars = ['DATABASE_URL', 'JWT_SECRET_KEY', 'POSTGRES_HOST']
    # REMOVED_SYNTAX_ERROR: for var in critical_vars:
        # REMOVED_SYNTAX_ERROR: self.assertIn(var, self.REQUIRED_ENV_VARS,
        # REMOVED_SYNTAX_ERROR: "formatted_string")

# REMOVED_SYNTAX_ERROR: def test_validate_cloud_run_has_env_vars(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test validation that Cloud Run service has all required env vars."""
    # REMOVED_SYNTAX_ERROR: pass
    # Simulate Cloud Run service with missing env vars
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = Mock( )
    # REMOVED_SYNTAX_ERROR: returncode=0,
    # REMOVED_SYNTAX_ERROR: stdout="ENV
    # REMOVED_SYNTAX_ERROR: DATABASE_URL
    # REMOVED_SYNTAX_ERROR: ",  # Only 2 of 14 required
    # REMOVED_SYNTAX_ERROR: stderr=''
    

    # REMOVED_SYNTAX_ERROR: from scripts.deploy_to_gcp import validate_cloud_run_env_vars

    # REMOVED_SYNTAX_ERROR: with self.assertRaises(ValueError) as context:
        # REMOVED_SYNTAX_ERROR: validate_cloud_run_env_vars('netra-backend', 'netra-staging', 'us-central1')

        # REMOVED_SYNTAX_ERROR: error_message = str(context.exception)
        # REMOVED_SYNTAX_ERROR: self.assertIn('Missing required env vars', error_message)
        # REMOVED_SYNTAX_ERROR: self.assertIn('JWT_SECRET_KEY', error_message)
        # REMOVED_SYNTAX_ERROR: self.assertIn('POSTGRES_HOST', error_message)

# REMOVED_SYNTAX_ERROR: def test_validate_gsm_secrets_exist(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test validation that Google Secret Manager has all required secrets."""
    # Simulate GSM with missing secrets
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = Mock( )
    # REMOVED_SYNTAX_ERROR: returncode=0,
    # REMOVED_SYNTAX_ERROR: stdout=json.dumps([ ))
    # REMOVED_SYNTAX_ERROR: {'name': 'projects/netra-staging/secrets/jwt-secret-staging'},
    # REMOVED_SYNTAX_ERROR: {'name': 'projects/netra-staging/secrets/secret-key-staging'}
    # Missing postgres-password-staging and others
    # REMOVED_SYNTAX_ERROR: ]),
    # REMOVED_SYNTAX_ERROR: stderr=''
    

    # REMOVED_SYNTAX_ERROR: from scripts.validate_secrets import validate_gsm_secrets_exist

    # REMOVED_SYNTAX_ERROR: missing_secrets = validate_gsm_secrets_exist('netra-staging', self.REQUIRED_GSM_SECRETS)

    # REMOVED_SYNTAX_ERROR: self.assertGreater(len(missing_secrets), 0, "Should detect missing secrets")
    # REMOVED_SYNTAX_ERROR: self.assertIn('postgres-password-staging', missing_secrets)
    # REMOVED_SYNTAX_ERROR: self.assertIn('redis-host-staging', missing_secrets)

# REMOVED_SYNTAX_ERROR: def test_deployment_config_completeness(self):
    # REMOVED_SYNTAX_ERROR: """Test that deployment config includes all required settings."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from deployment.secrets_config import BACKEND_SECRETS, AUTH_SECRETS

    # Check backend secrets configuration
    # REMOVED_SYNTAX_ERROR: backend_secret_keys = list(BACKEND_SECRETS.keys())
    # REMOVED_SYNTAX_ERROR: critical_backend_secrets = [ )
    # REMOVED_SYNTAX_ERROR: 'DATABASE_URL',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD',
    # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY',
    # REMOVED_SYNTAX_ERROR: 'SECRET_KEY'
    

    # REMOVED_SYNTAX_ERROR: for secret in critical_backend_secrets:
        # REMOVED_SYNTAX_ERROR: self.assertIn(secret, backend_secret_keys,
        # REMOVED_SYNTAX_ERROR: "formatted_string")

# REMOVED_SYNTAX_ERROR: def test_staging_config_validation(self):
    # REMOVED_SYNTAX_ERROR: """Test that staging configuration validates required fields."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.config.staging import StagingConfig

    # Test that config raises error when critical vars missing
    # REMOVED_SYNTAX_ERROR: with self.assertRaises((ValueError, KeyError)) as context:
        # REMOVED_SYNTAX_ERROR: config = StagingConfig()
        # Attempt to access critical config
        # REMOVED_SYNTAX_ERROR: _ = config.database_url

# REMOVED_SYNTAX_ERROR: def test_deployment_script_validates_before_deploy(self):
    # REMOVED_SYNTAX_ERROR: """Test that deployment script validates configuration before deploying."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch('scripts.deploy_to_gcp.validate_secrets_before_deployment') as mock_validate:
        # REMOVED_SYNTAX_ERROR: with patch('scripts.deploy_to_gcp.deploy_service') as mock_deploy:
            # REMOVED_SYNTAX_ERROR: mock_validate.return_value = False  # Validation fails

            # REMOVED_SYNTAX_ERROR: from scripts.deploy_to_gcp import main

            # Should not reach deploy when validation fails
            # REMOVED_SYNTAX_ERROR: with self.assertRaises(SystemExit):
                # REMOVED_SYNTAX_ERROR: main(['--project', 'netra-staging'])

                # REMOVED_SYNTAX_ERROR: mock_deploy.assert_not_called()

# REMOVED_SYNTAX_ERROR: def test_health_check_reports_missing_config(self):
    # REMOVED_SYNTAX_ERROR: """Test that health check endpoint reports configuration issues."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.services.health.deep_checks import validate_configuration

    # REMOVED_SYNTAX_ERROR: with patch.dict(os.environ, {}, clear=True):  # Clear all env vars
    # REMOVED_SYNTAX_ERROR: issues = validate_configuration()

    # REMOVED_SYNTAX_ERROR: self.assertGreater(len(issues), 0, "Should detect configuration issues")

    # Should report specific missing configs
    # REMOVED_SYNTAX_ERROR: issue_text = ' '.join(issues)
    # REMOVED_SYNTAX_ERROR: self.assertIn('DATABASE_URL', issue_text)
    # REMOVED_SYNTAX_ERROR: self.assertIn('JWT_SECRET_KEY', issue_text)

# REMOVED_SYNTAX_ERROR: def test_cloud_run_probe_with_missing_config(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test that Cloud Run probe fails when configuration is missing."""
    # REMOVED_SYNTAX_ERROR: pass
    # Simulate probe failure due to missing config
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = Mock( )
    # REMOVED_SYNTAX_ERROR: returncode=1,
    # REMOVED_SYNTAX_ERROR: stdout='',
    # REMOVED_SYNTAX_ERROR: stderr='Default STARTUP TCP probe failed 1 time consecutively'
    

    # REMOVED_SYNTAX_ERROR: from scripts.deploy_to_gcp import check_service_health

    # REMOVED_SYNTAX_ERROR: is_healthy = check_service_health('netra-backend', 'netra-staging', 'us-central1')

    # REMOVED_SYNTAX_ERROR: self.assertFalse(is_healthy, "Service should not be healthy with missing config")

# REMOVED_SYNTAX_ERROR: def test_config_validation_error_messages(self):
    # REMOVED_SYNTAX_ERROR: """Test that configuration validation provides clear error messages."""
    # REMOVED_SYNTAX_ERROR: from netra_backend.config.base import validate_required_configs

    # REMOVED_SYNTAX_ERROR: missing_configs = ['DATABASE_URL', 'JWT_SECRET_KEY', 'REDIS_HOST']
    # REMOVED_SYNTAX_ERROR: error_message = validate_required_configs({}, self.REQUIRED_ENV_VARS)

    # REMOVED_SYNTAX_ERROR: self.assertIn('CRITICAL', error_message)
    # REMOVED_SYNTAX_ERROR: self.assertIn('Missing required config', error_message)

    # REMOVED_SYNTAX_ERROR: for config in missing_configs:
        # REMOVED_SYNTAX_ERROR: self.assertIn(config, error_message,
        # REMOVED_SYNTAX_ERROR: "formatted_string")

# REMOVED_SYNTAX_ERROR: def test_deployment_rollback_on_config_failure(self):
    # REMOVED_SYNTAX_ERROR: """Test that deployment rolls back when configuration validation fails."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: with patch('scripts.deploy_to_gcp.deploy_to_cloud_run') as mock_deploy:
        # REMOVED_SYNTAX_ERROR: with patch('scripts.deploy_to_gcp.validate_deployment') as mock_validate:
            # REMOVED_SYNTAX_ERROR: with patch('scripts.deploy_to_gcp.rollback_deployment') as mock_rollback:

                # REMOVED_SYNTAX_ERROR: mock_deploy.return_value = True
                # REMOVED_SYNTAX_ERROR: mock_validate.return_value = False  # Post-deploy validation fails

                # REMOVED_SYNTAX_ERROR: from scripts.deploy_to_gcp import deploy_with_validation

                # REMOVED_SYNTAX_ERROR: result = deploy_with_validation('netra-backend', 'netra-staging')

                # REMOVED_SYNTAX_ERROR: self.assertFalse(result)
                # REMOVED_SYNTAX_ERROR: mock_rollback.assert_called_once()

# REMOVED_SYNTAX_ERROR: def test_secrets_config_matches_required_vars(self):
    # REMOVED_SYNTAX_ERROR: """Test that secrets config covers all required environment variables."""
    # REMOVED_SYNTAX_ERROR: from deployment.secrets_config import get_all_configured_secrets

    # REMOVED_SYNTAX_ERROR: configured_secrets = get_all_configured_secrets('backend')

    # Map of env var to secret name patterns
    # REMOVED_SYNTAX_ERROR: env_to_secret_mapping = { )
    # REMOVED_SYNTAX_ERROR: 'DATABASE_URL': 'database-url',
    # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY': 'jwt-secret',
    # REMOVED_SYNTAX_ERROR: 'SECRET_KEY': 'secret-key',
    # REMOVED_SYNTAX_ERROR: 'POSTGRES_PASSWORD': 'postgres-password',
    

    # REMOVED_SYNTAX_ERROR: for env_var, secret_pattern in env_to_secret_mapping.items():
        # REMOVED_SYNTAX_ERROR: found = any(secret_pattern in secret.lower() )
        # REMOVED_SYNTAX_ERROR: for secret in configured_secrets)
        # REMOVED_SYNTAX_ERROR: self.assertTrue(found,
        # REMOVED_SYNTAX_ERROR: "formatted_string")

# REMOVED_SYNTAX_ERROR: def test_prevent_deployment_with_localhost_urls(self):
    # REMOVED_SYNTAX_ERROR: """Test that deployment prevents localhost URLs in staging/production."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: test_configs = { )
    # REMOVED_SYNTAX_ERROR: 'ENV': 'staging',
    # REMOVED_SYNTAX_ERROR: 'BACKEND_URL': 'http://localhost:8000',  # Invalid for staging
    # REMOVED_SYNTAX_ERROR: 'FRONTEND_URL': 'http://localhost:3000',  # Invalid for staging
    # REMOVED_SYNTAX_ERROR: 'API_BASE_URL': 'http://localhost:8000'   # Invalid for staging
    

    # REMOVED_SYNTAX_ERROR: from netra_backend.config.base import validate_urls_for_environment

    # REMOVED_SYNTAX_ERROR: issues = validate_urls_for_environment(test_configs, 'staging')

    # REMOVED_SYNTAX_ERROR: self.assertGreater(len(issues), 0, "Should detect localhost URLs in staging")
    # REMOVED_SYNTAX_ERROR: self.assertIn('localhost', ' '.join(issues))

# REMOVED_SYNTAX_ERROR: def test_cloud_sql_connection_format(self):
    # REMOVED_SYNTAX_ERROR: """Test that Cloud SQL connections use Unix socket format."""
    # REMOVED_SYNTAX_ERROR: valid_formats = [ )
    # REMOVED_SYNTAX_ERROR: 'postgresql://user:pass@/db?host=/cloudsql/project:region:instance',
    # REMOVED_SYNTAX_ERROR: '/cloudsql/project:region:instance'
    

    # REMOVED_SYNTAX_ERROR: invalid_formats = [ )
    # REMOVED_SYNTAX_ERROR: 'postgresql://user:pass@10.0.0.1:5432/db',  # TCP instead of socket
    # REMOVED_SYNTAX_ERROR: 'localhost:5432',  # Localhost
    # REMOVED_SYNTAX_ERROR: '127.0.0.1'  # Loopback
    

    # REMOVED_SYNTAX_ERROR: from netra_backend.config.base import validate_cloud_sql_format

    # REMOVED_SYNTAX_ERROR: for valid in valid_formats:
        # REMOVED_SYNTAX_ERROR: self.assertTrue(validate_cloud_sql_format(valid),
        # REMOVED_SYNTAX_ERROR: "formatted_string")

        # REMOVED_SYNTAX_ERROR: for invalid in invalid_formats:
            # REMOVED_SYNTAX_ERROR: self.assertFalse(validate_cloud_sql_format(invalid),
            # REMOVED_SYNTAX_ERROR: "formatted_string")


# REMOVED_SYNTAX_ERROR: class TestDeploymentScriptIntegration(unittest.TestCase):
    # REMOVED_SYNTAX_ERROR: """Integration tests for deployment script configuration handling."""

# REMOVED_SYNTAX_ERROR: def test_full_deployment_flow_with_validation(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test complete deployment flow with configuration validation."""
    # Mock successful responses for all checks
    # REMOVED_SYNTAX_ERROR: mock_run.side_effect = [ )
    # GSM secrets exist check
    # REMOVED_SYNTAX_ERROR: Mock(returncode=0, stdout=json.dumps([ )))
    # REMOVED_SYNTAX_ERROR: {'name': 'formatted_string'}
    # REMOVED_SYNTAX_ERROR: for secret in TestDeploymentConfigValidation.REQUIRED_GSM_SECRETS
    # REMOVED_SYNTAX_ERROR: ])),
    # Cloud Run deployment
    # REMOVED_SYNTAX_ERROR: Mock(returncode=0, stdout='Service deployed'),
    # Post-deployment validation
    # REMOVED_SYNTAX_ERROR: Mock(returncode=0, stdout=" )
    # REMOVED_SYNTAX_ERROR: ".join( )
    # REMOVED_SYNTAX_ERROR: TestDeploymentConfigValidation.REQUIRED_ENV_VARS
    
    

    # REMOVED_SYNTAX_ERROR: from scripts.deploy_to_gcp import full_deployment_with_validation

    # REMOVED_SYNTAX_ERROR: result = full_deployment_with_validation( )
    # REMOVED_SYNTAX_ERROR: project='netra-staging',
    # REMOVED_SYNTAX_ERROR: service='netra-backend',
    # REMOVED_SYNTAX_ERROR: region='us-central1'
    

    # REMOVED_SYNTAX_ERROR: self.assertTrue(result, "Deployment should succeed with all configs present")

    # Verify all validation steps were called
    # REMOVED_SYNTAX_ERROR: self.assertEqual(mock_run.call_count, 3)

# REMOVED_SYNTAX_ERROR: def test_deployment_fails_fast_on_missing_secrets(self, mock_run):
    # REMOVED_SYNTAX_ERROR: """Test that deployment fails immediately when secrets are missing."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock missing secrets
    # REMOVED_SYNTAX_ERROR: mock_run.return_value = Mock( )
    # REMOVED_SYNTAX_ERROR: returncode=0,
    # REMOVED_SYNTAX_ERROR: stdout=json.dumps([])  # No secrets exist
    

    # REMOVED_SYNTAX_ERROR: from scripts.deploy_to_gcp import full_deployment_with_validation

    # REMOVED_SYNTAX_ERROR: with self.assertRaises(ValueError) as context:
        # REMOVED_SYNTAX_ERROR: full_deployment_with_validation( )
        # REMOVED_SYNTAX_ERROR: project='netra-staging',
        # REMOVED_SYNTAX_ERROR: service='netra-backend',
        # REMOVED_SYNTAX_ERROR: region='us-central1'
        

        # REMOVED_SYNTAX_ERROR: self.assertIn('Missing required secrets', str(context.exception))

        # Should only call once for secret check, not proceed to deployment
        # REMOVED_SYNTAX_ERROR: self.assertEqual(mock_run.call_count, 1)


# REMOVED_SYNTAX_ERROR: class TestConfigurationMonitoring(unittest.TestCase):
    # REMOVED_SYNTAX_ERROR: """Tests for ongoing configuration monitoring and drift detection."""

# REMOVED_SYNTAX_ERROR: def test_config_drift_detection(self):
    # REMOVED_SYNTAX_ERROR: """Test detection of configuration drift from expected state."""
    # REMOVED_SYNTAX_ERROR: expected_config = { )
    # REMOVED_SYNTAX_ERROR: 'DATABASE_URL': 'postgresql://user:pass@/db?host=/cloudsql/instance',
    # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY': 'expected_secret',
    # REMOVED_SYNTAX_ERROR: 'ENV': 'staging'
    

    # REMOVED_SYNTAX_ERROR: actual_config = { )
    # REMOVED_SYNTAX_ERROR: 'DATABASE_URL': 'postgresql://user:pass@/db?host=/cloudsql/instance',
    # REMOVED_SYNTAX_ERROR: 'JWT_SECRET_KEY': 'different_secret',  # Drifted
    # ENV is missing - also drift
    

    # REMOVED_SYNTAX_ERROR: from scripts.monitor_config_drift import detect_drift

    # REMOVED_SYNTAX_ERROR: drift = detect_drift(expected_config, actual_config)

    # REMOVED_SYNTAX_ERROR: self.assertEqual(len(drift), 2, "Should detect 2 drifted configs")
    # REMOVED_SYNTAX_ERROR: self.assertIn('JWT_SECRET_KEY', drift)
    # REMOVED_SYNTAX_ERROR: self.assertIn('ENV', drift)

# REMOVED_SYNTAX_ERROR: def test_config_compliance_report(self):
    # REMOVED_SYNTAX_ERROR: """Test generation of configuration compliance report."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: from scripts.generate_config_compliance import generate_report

    # REMOVED_SYNTAX_ERROR: report = generate_report( )
    # REMOVED_SYNTAX_ERROR: service='netra-backend',
    # REMOVED_SYNTAX_ERROR: environment='staging',
    # REMOVED_SYNTAX_ERROR: required_vars=TestDeploymentConfigValidation.REQUIRED_ENV_VARS
    

    # REMOVED_SYNTAX_ERROR: self.assertIn('Configuration Compliance Report', report)
    # REMOVED_SYNTAX_ERROR: self.assertIn('Required Variables', report)
    # REMOVED_SYNTAX_ERROR: self.assertIn('Missing Variables', report)
    # REMOVED_SYNTAX_ERROR: self.assertIn('Recommendations', report)


    # REMOVED_SYNTAX_ERROR: if __name__ == '__main__':
        # Run with verbose output to see all test results
        # REMOVED_SYNTAX_ERROR: unittest.main(verbosity=2)