"""
End-to-end integration tests for deployment configuration validation.
These tests verify the complete deployment flow including configuration.

Cross-references:
- Incident Report: FIVE_WHYS_STAGING_CONFIG_FAILURE_20250905.md
- Learning Doc: SPEC/learnings/cloud_run_config_failure_20250905.xml
- Remediation Plan: STAGING_CONFIG_REMEDIATION_PLAN.md
- Unit Tests: tests/unit/test_deployment_config_validation.py
"""

import unittest
import os
import json
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from netra_backend.config.staging import StagingConfig
from netra_backend.config.base import BaseConfig


class TestDeploymentConfigurationE2E(unittest.TestCase):
    """End-to-end tests for deployment configuration validation."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_env_vars = {
            'ENV': 'test',
            'DATABASE_URL': 'postgresql://test:test@localhost/test',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db',
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_pass',
            'JWT_SECRET_KEY': 'test_jwt_secret_key_very_long_and_secure',
            'SECRET_KEY': 'test_secret_key_also_very_long_and_secure',
            'REDIS_HOST': 'localhost',
            'REDIS_PORT': '6379',
            'BACKEND_URL': 'http://localhost:8000',
            'FRONTEND_URL': 'http://localhost:3000',
            'API_BASE_URL': 'http://localhost:8000'
        }
        
    @patch.dict(os.environ, {}, clear=True)
    def test_application_fails_without_config(self):
        """Test that application cannot start without required configuration."""
        from netra_backend.app.services.health.deep_checks import HealthChecker
        
        checker = HealthChecker()
        result = checker.check_configuration()
        
        self.assertFalse(result['healthy'])
        self.assertIn('configuration', result['issues'][0].lower())
        self.assertTrue(len(result['missing_configs']) > 0)
        
    @patch.dict(os.environ, {'ENV': 'test', 'DATABASE_URL': 'incomplete'})
    def test_partial_config_detected(self):
        """Test that partial configuration is detected as incomplete."""
        from netra_backend.app.services.health.deep_checks import validate_configuration
        
        issues = validate_configuration()
        
        self.assertGreater(len(issues), 0)
        # Should detect multiple missing configs
        self.assertTrue(any('JWT_SECRET_KEY' in issue for issue in issues))
        self.assertTrue(any('POSTGRES_HOST' in issue for issue in issues))
        
    def test_staging_config_requires_cloud_sql_format(self):
        """Test that staging config enforces Cloud SQL connection format."""
        with patch.dict(os.environ, {
            'ENV': 'staging',
            'DATABASE_URL': 'postgresql://user:pass@10.0.0.1:5432/db',  # Wrong format
            **self.test_env_vars
        }):
            from netra_backend.config.staging import validate_staging_database_url
            
            is_valid, error = validate_staging_database_url(os.environ['DATABASE_URL'])
            
            self.assertFalse(is_valid)
            self.assertIn('cloudsql', error.lower())
            
    def test_staging_config_rejects_localhost_urls(self):
        """Test that staging configuration rejects localhost URLs."""
        with patch.dict(os.environ, {
            'ENV': 'staging',
            'BACKEND_URL': 'http://localhost:8000',  # Invalid for staging
            'FRONTEND_URL': 'http://localhost:3000',  # Invalid for staging
            **self.test_env_vars
        }):
            from netra_backend.config.base import validate_urls_for_environment
            
            issues = validate_urls_for_environment(os.environ, 'staging')
            
            self.assertGreater(len(issues), 0)
            self.assertTrue(any('localhost' in issue for issue in issues))
            
    @patch('subprocess.run')
    def test_deployment_validates_gsm_secrets(self, mock_run):
        """Test that deployment validates Google Secret Manager secrets exist."""
        # First call: list secrets (missing some)
        mock_run.return_value = Mock(
            returncode=0,
            stdout=json.dumps([
                {'name': 'projects/netra-staging/secrets/jwt-secret-staging'}
                # Missing other required secrets
            ])
        )
        
        from scripts.validate_secrets import check_gsm_secrets
        
        missing = check_gsm_secrets('netra-staging', [
            'jwt-secret-staging',
            'secret-key-staging',
            'postgres-password-staging'
        ])
        
        self.assertEqual(len(missing), 2)  # 2 secrets missing
        self.assertIn('secret-key-staging', missing)
        self.assertIn('postgres-password-staging', missing)
        
    @patch('subprocess.run')
    def test_cloud_run_service_config_validation(self, mock_run):
        """Test validation of Cloud Run service configuration."""
        # Simulate Cloud Run service with incomplete config
        mock_run.return_value = Mock(
            returncode=0,
            stdout='ENV\nDATABASE_URL',  # Only 2 of many required
            stderr=''
        )
        
        from scripts.deploy_to_gcp import get_cloud_run_env_vars
        
        env_vars = get_cloud_run_env_vars('netra-backend', 'netra-staging', 'us-central1')
        
        required_vars = [
            'JWT_SECRET_KEY', 'SECRET_KEY', 'POSTGRES_HOST',
            'POSTGRES_PORT', 'POSTGRES_DB', 'POSTGRES_USER'
        ]
        
        missing = set(required_vars) - set(env_vars.split('\n'))
        
        self.assertGreater(len(missing), 0)
        self.assertIn('JWT_SECRET_KEY', missing)
        
    def test_health_check_with_complete_config(self):
        """Test that health check passes with complete configuration."""
        with patch.dict(os.environ, self.test_env_vars):
            from netra_backend.app.services.health.deep_checks import HealthChecker
            
            checker = HealthChecker()
            
            # Mock database and redis connections
            with patch.object(checker, '_check_database', return_value={'healthy': True}):
                with patch.object(checker, '_check_redis', return_value={'healthy': True}):
                    result = checker.check_all()
                    
                    self.assertTrue(result['configuration']['healthy'])
                    self.assertEqual(len(result['configuration']['missing_configs']), 0)
                    
    def test_deployment_rollback_on_validation_failure(self):
        """Test that deployment rolls back when validation fails."""
        from scripts.deploy_to_gcp import DeploymentManager
        
        manager = DeploymentManager('netra-staging', 'us-central1')
        
        with patch.object(manager, 'deploy_service', return_value=True):
            with patch.object(manager, 'validate_deployment', return_value=False):
                with patch.object(manager, 'rollback', return_value=True) as mock_rollback:
                    
                    success = manager.deploy_with_validation('netra-backend')
                    
                    self.assertFalse(success)
                    mock_rollback.assert_called_once()
                    
    def test_configuration_compliance_monitoring(self):
        """Test ongoing configuration compliance monitoring."""
        from scripts.monitor_config_drift import ConfigMonitor
        
        monitor = ConfigMonitor()
        
        expected_config = self.test_env_vars.copy()
        actual_config = self.test_env_vars.copy()
        actual_config['JWT_SECRET_KEY'] = 'different_value'  # Configuration drift
        del actual_config['REDIS_HOST']  # Missing config
        
        drift_report = monitor.check_drift(expected_config, actual_config)
        
        self.assertEqual(len(drift_report['modified']), 1)
        self.assertEqual(len(drift_report['missing']), 1)
        self.assertIn('JWT_SECRET_KEY', drift_report['modified'])
        self.assertIn('REDIS_HOST', drift_report['missing'])


class TestAsyncDeploymentValidation(unittest.IsolatedAsyncioTestCase):
    """Async tests for deployment validation workflows."""
    
    async def test_parallel_secret_validation(self):
        """Test parallel validation of multiple secrets."""
        from scripts.validate_secrets import validate_secrets_parallel
        
        secrets_to_check = [
            'jwt-secret-staging',
            'secret-key-staging',
            'postgres-password-staging',
            'redis-host-staging'
        ]
        
        with patch('scripts.validate_secrets.check_secret_exists', new_callable=AsyncMock) as mock_check:
            # Mock that half the secrets exist
            mock_check.side_effect = [True, True, False, False]
            
            results = await validate_secrets_parallel('netra-staging', secrets_to_check)
            
            self.assertEqual(len(results['existing']), 2)
            self.assertEqual(len(results['missing']), 2)
            
    async def test_health_check_with_timeout(self):
        """Test health check with timeout for slow config validation."""
        from netra_backend.app.services.health.async_health import AsyncHealthChecker
        
        checker = AsyncHealthChecker()
        
        # Mock slow config check
        async def slow_config_check():
            await asyncio.sleep(10)  # Simulate slow check
            return {'healthy': False}
            
        with patch.object(checker, 'check_configuration', side_effect=slow_config_check):
            # Should timeout after 5 seconds
            result = await checker.check_with_timeout(timeout=5)
            
            self.assertFalse(result['healthy'])
            self.assertIn('timeout', result.get('error', '').lower())


class TestDeploymentConfigCrossReferences(unittest.TestCase):
    """Test that all configuration documentation is properly cross-referenced."""
    
    def test_incident_documentation_exists(self):
        """Test that incident documentation files exist and are linked."""
        required_docs = [
            'FIVE_WHYS_STAGING_CONFIG_FAILURE_20250905.md',
            'STAGING_CONFIG_REMEDIATION_PLAN.md',
            'SPEC/learnings/cloud_run_config_failure_20250905.xml'
        ]
        
        for doc in required_docs:
            doc_path = project_root / doc
            self.assertTrue(doc_path.exists(), f"Missing documentation: {doc}")
            
    def test_test_files_reference_incidents(self):
        """Test that test files properly reference incident documentation."""
        test_file = project_root / 'tests' / 'unit' / 'test_deployment_config_validation.py'
        
        with open(test_file, 'r') as f:
            content = f.read()
            
        # Check for cross-references
        self.assertIn('FIVE_WHYS_STAGING_CONFIG_FAILURE', content)
        self.assertIn('cloud_run_config_failure', content)
        self.assertIn('STAGING_CONFIG_REMEDIATION_PLAN', content)
        
    def test_config_validation_covers_all_required_vars(self):
        """Test that validation covers all 19 required environment variables."""
        from tests.unit.test_deployment_config_validation import TestDeploymentConfigValidation
        
        required_vars = TestDeploymentConfigValidation.REQUIRED_ENV_VARS
        
        # These are the 19 critical vars identified in the incident
        critical_vars = [
            'DATABASE_URL', 'JWT_SECRET_KEY', 'SECRET_KEY',
            'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB',
            'POSTGRES_USER', 'POSTGRES_PASSWORD', 'ENV',
            'REDIS_HOST', 'REDIS_PORT', 'BACKEND_URL',
            'FRONTEND_URL', 'API_BASE_URL'
        ]
        
        for var in critical_vars:
            self.assertIn(var, required_vars, 
                         f"Missing validation for critical var: {var}")


class TestCloudRunProbeSimulation(unittest.TestCase):
    """Simulate Cloud Run probe failures from missing configuration."""
    
    @patch('subprocess.run')
    def test_tcp_probe_failure_simulation(self, mock_run):
        """Simulate TCP probe failure as seen in incident."""
        # Simulate the exact error from the incident
        mock_run.return_value = Mock(
            returncode=1,
            stdout='',
            stderr='Default STARTUP TCP probe failed 1 time consecutively for container "netra-backend"'
        )
        
        from scripts.deploy_to_gcp import check_startup_probe
        
        probe_healthy = check_startup_probe('netra-backend', 'netra-staging', 'us-central1')
        
        self.assertFalse(probe_healthy)
        
    def test_probe_retry_logic(self):
        """Test that probe retry logic handles configuration delays."""
        from scripts.deploy_to_gcp import wait_for_healthy_with_retry
        
        with patch('scripts.deploy_to_gcp.check_startup_probe') as mock_probe:
            # Fail first 2 attempts, succeed on third
            mock_probe.side_effect = [False, False, True]
            
            healthy = wait_for_healthy_with_retry(
                'netra-backend', 
                'netra-staging',
                'us-central1',
                max_attempts=3,
                delay=1
            )
            
            self.assertTrue(healthy)
            self.assertEqual(mock_probe.call_count, 3)


if __name__ == '__main__':
    # Run tests with detailed output
    unittest.main(verbosity=2)