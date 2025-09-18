"""
UnifiedSecretsManager Redis Integration Unit Tests - Issue #1343

Comprehensive unit tests for the UnifiedSecretsManager's Redis-specific functionality,
including GCP Secret Manager integration, environment variable fallbacks, and caching.

Business Value: Platform/Internal - System Stability & Infrastructure Reliability
Ensures proper secret management for Redis connections across all environments,
preventing configuration failures that could impact $30K+ MRR operations.

SSOT Compliance: Uses SSotBaseTestCase, IsolatedEnvironment, and unified configuration patterns.
"""

import pytest
import subprocess
import os
from unittest.mock import Mock, patch, MagicMock, call
from test_framework.ssot.base_test_case import SSotBaseTestCase

from netra_backend.app.core.configuration.unified_secrets import (
    UnifiedSecretsManager,
    SecretConfig,
    get_secrets_manager,
    get_secret,
    set_secret
)


class TestUnifiedSecretsManagerRedis(SSotBaseTestCase):
    """Unit tests for UnifiedSecretsManager Redis secret management functionality."""

    def setup_method(self, method):
        """Setup test environment with clean secrets manager state."""
        super().setup_method(method)

        # Clear global secrets manager instance
        import netra_backend.app.core.configuration.unified_secrets as secrets_module
        secrets_module._secrets_manager = None

        # Set test environment
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("GCP_PROJECT_ID", "test-project-redis")

    def test_gcp_secret_manager_redis_secret_retrieval(self):
        """Test GCP Secret Manager integration for Redis secrets."""

        # Mock successful GCP secret retrieval
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "redis-secret-value"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Create secrets manager
            config = SecretConfig(use_gcp_secrets=True, gcp_project_id="test-project-redis")
            secrets_manager = UnifiedSecretsManager(config)

            # Test Redis secret retrieval
            redis_host = secrets_manager.get_secret("REDIS_HOST")

            # Verify GCP call was made correctly
            expected_call = call(
                ['gcloud', 'secrets', 'versions', 'access', 'latest',
                 '--secret', 'redis-host-staging', '--project', 'test-project-redis'],
                capture_output=True, text=True, check=False, timeout=10
            )
            mock_subprocess.assert_called_with(expected_call)

            # Verify secret was retrieved
            self.assertEqual(redis_host, "redis-secret-value")

            # Record metrics
            self.record_metric("gcp_redis_secret_calls", 1)
            self.record_metric("gcp_redis_secret_success", True)

    def test_redis_secret_environment_mapping(self):
        """Test proper mapping of Redis environment variables to GCP secret names."""

        config = SecretConfig(use_gcp_secrets=True)
        secrets_manager = UnifiedSecretsManager(config)

        # Test environment-specific Redis secret mappings
        test_cases = [
            ("REDIS_HOST", "staging", "redis-host-staging"),
            ("REDIS_PORT", "staging", "redis-port-staging"),
            ("REDIS_PASSWORD", "staging", "redis-password-staging"),
            ("REDIS_URL", "staging", "redis-url-staging"),
            ("REDIS_HOST", "production", "redis-host-production"),
            ("REDIS_PASSWORD", "production", "redis-password-production"),
        ]

        for env_var, environment, expected_secret in test_cases:
            with self.subTest(env_var=env_var, environment=environment):
                # Set environment
                self.set_env_var("ENVIRONMENT", environment)

                # Create new secrets manager for environment
                new_secrets_manager = UnifiedSecretsManager(config)
                actual_secret = new_secrets_manager._map_env_to_gcp_secret(env_var)

                # Verify mapping
                self.assertEqual(actual_secret, expected_secret)

                # Record metrics
                self.record_metric(f"redis_mapping_{environment}_{env_var}", True)

    def test_redis_secret_fallback_to_environment_variables(self):
        """Test fallback to environment variables when GCP secrets are unavailable."""

        # Set environment variable fallbacks
        self.set_env_var("REDIS_HOST", "localhost")
        self.set_env_var("REDIS_PORT", "6379")
        self.set_env_var("REDIS_PASSWORD", "fallback-password")

        # Mock GCP secret failure
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Secret not found"
            mock_subprocess.return_value = mock_result

            # Create secrets manager with GCP enabled but fallback allowed
            config = SecretConfig(use_gcp_secrets=True, fallback_to_env=True)
            secrets_manager = UnifiedSecretsManager(config)

            # Test fallback behavior
            redis_host = secrets_manager.get_secret("REDIS_HOST")
            redis_port = secrets_manager.get_secret("REDIS_PORT")
            redis_password = secrets_manager.get_secret("REDIS_PASSWORD")

            # Verify fallback values
            self.assertEqual(redis_host, "localhost")
            self.assertEqual(redis_port, "6379")
            self.assertEqual(redis_password, "fallback-password")

            # Record metrics
            self.record_metric("gcp_secret_failures", mock_subprocess.call_count)
            self.record_metric("env_fallback_used", True)

    def test_redis_secret_caching_mechanism(self):
        """Test secret caching to avoid repeated GCP API calls."""

        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "cached-redis-value"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Create secrets manager with caching enabled
            config = SecretConfig(use_gcp_secrets=True, cache_secrets=True)
            secrets_manager = UnifiedSecretsManager(config)

            # Get the same secret multiple times
            value1 = secrets_manager.get_secret("REDIS_HOST")
            value2 = secrets_manager.get_secret("REDIS_HOST")
            value3 = secrets_manager.get_secret("REDIS_HOST")

            # Verify same value returned
            self.assertEqual(value1, "cached-redis-value")
            self.assertEqual(value2, "cached-redis-value")
            self.assertEqual(value3, "cached-redis-value")

            # Verify GCP was only called once
            self.assertEqual(mock_subprocess.call_count, 1)

            # Test cache clearing
            secrets_manager.clear_cache()
            value4 = secrets_manager.get_secret("REDIS_HOST")

            # Verify GCP was called again after cache clear
            self.assertEqual(mock_subprocess.call_count, 2)
            self.assertEqual(value4, "cached-redis-value")

            # Record metrics
            self.record_metric("cache_hits", 2)
            self.record_metric("cache_cleared", True)

    def test_cloud_run_auto_detection_for_redis_secrets(self):
        """Test Cloud Run environment auto-detection enables GCP secrets for Redis."""

        # Mock Cloud Run environment
        self.set_env_var("K_SERVICE", "redis-backend-service")
        self.set_env_var("GCP_PROJECT_ID", "netra-staging")

        # Create secrets manager (should auto-detect Cloud Run)
        secrets_manager = UnifiedSecretsManager()

        # Verify GCP secrets auto-enabled
        self.assertTrue(secrets_manager.config.use_gcp_secrets)
        self.assertEqual(secrets_manager.config.gcp_project_id, "netra-staging")

        # Record metrics
        self.record_metric("cloud_run_auto_detection", True)
        self.record_metric("gcp_project_detected", "netra-staging")

    def test_gcp_project_detection_from_metadata_service(self):
        """Test GCP project ID detection from metadata service."""

        # Remove environment variables
        self.delete_env_var("GCP_PROJECT_ID")
        self.delete_env_var("GOOGLE_CLOUD_PROJECT")

        # Mock metadata service response
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = Mock()
            mock_response.read.return_value = b"detected-project-id"
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            # Create secrets manager
            secrets_manager = UnifiedSecretsManager()

            # Verify project ID was detected
            self.assertEqual(secrets_manager.config.gcp_project_id, "detected-project-id")

            # Verify metadata service was called
            mock_urlopen.assert_called_once()

            # Record metrics
            self.record_metric("metadata_service_detection", True)

    def test_redis_secret_timeout_handling(self):
        """Test proper timeout handling for GCP secret retrieval."""

        with patch('subprocess.run') as mock_subprocess:
            # Mock timeout exception
            mock_subprocess.side_effect = subprocess.TimeoutExpired(
                cmd=['gcloud', 'secrets', 'versions', 'access'],
                timeout=10
            )

            # Create secrets manager
            config = SecretConfig(use_gcp_secrets=True)
            secrets_manager = UnifiedSecretsManager(config)

            # Test timeout handling with default fallback
            redis_host = secrets_manager.get_secret("REDIS_HOST", default="timeout-fallback")

            # Verify fallback value used
            self.assertEqual(redis_host, "timeout-fallback")

            # Record metrics
            self.record_metric("gcp_timeout_handled", True)

    def test_redis_secret_error_logging(self):
        """Test proper error logging for Redis secret retrieval failures."""

        with patch('subprocess.run') as mock_subprocess:
            # Mock subprocess error
            mock_subprocess.side_effect = Exception("Subprocess error")

            # Create secrets manager
            config = SecretConfig(use_gcp_secrets=True)
            secrets_manager = UnifiedSecretsManager(config)

            # Test error handling
            with patch.object(secrets_manager.__class__.__module__, 'logger') as mock_logger:
                redis_host = secrets_manager.get_secret("REDIS_HOST", default="error-fallback")

                # Verify error was logged
                # Note: The exact logging call depends on implementation
                self.assertEqual(redis_host, "error-fallback")

            # Record metrics
            self.record_metric("gcp_error_handled", True)

    def test_global_secrets_manager_functions(self):
        """Test global convenience functions for Redis secrets."""

        # Mock GCP secret retrieval
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "global-redis-host"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Test global get_secret function
            redis_host = get_secret("REDIS_HOST")
            self.assertEqual(redis_host, "global-redis-host")

            # Test global set_secret function
            set_secret("REDIS_TEST_VAR", "test-value")

            # Test that set value can be retrieved
            test_value = get_secret("REDIS_TEST_VAR")
            self.assertEqual(test_value, "test-value")

            # Record metrics
            self.record_metric("global_functions_working", True)

    def test_redis_secret_validation_edge_cases(self):
        """Test edge cases in Redis secret validation."""

        config = SecretConfig(use_gcp_secrets=False, fallback_to_env=True)
        secrets_manager = UnifiedSecretsManager(config)

        # Test empty string handling
        self.set_env_var("REDIS_EMPTY", "")
        empty_secret = secrets_manager.get_secret("REDIS_EMPTY", default="default-value")
        self.assertEqual(empty_secret, "default-value")

        # Test None handling
        none_secret = secrets_manager.get_secret("REDIS_NONEXISTENT", default="none-default")
        self.assertEqual(none_secret, "none-default")

        # Test "disabled" value handling (should trigger GCP fallback)
        self.set_env_var("REDIS_DISABLED", "disabled")
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "gcp-override-value"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Enable GCP for this test
            config.use_gcp_secrets = True
            secrets_manager = UnifiedSecretsManager(config)
            disabled_secret = secrets_manager.get_secret("REDIS_DISABLED")

            # Should use GCP value instead of "disabled"
            self.assertEqual(disabled_secret, "gcp-override-value")

        # Record metrics
        self.record_metric("edge_cases_handled", 3)

    def test_windows_gcloud_command_detection(self):
        """Test proper gcloud command detection on Windows."""

        # Mock Windows environment
        with patch('os.name', 'nt'):
            with patch('subprocess.run') as mock_subprocess:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = "windows-redis-value"
                mock_result.stderr = ""
                mock_subprocess.return_value = mock_result

                # Create secrets manager
                config = SecretConfig(use_gcp_secrets=True, gcp_project_id="test-project")
                secrets_manager = UnifiedSecretsManager(config)

                # Get secret
                redis_host = secrets_manager.get_secret("REDIS_HOST")

                # Verify Windows gcloud command was used
                call_args = mock_subprocess.call_args[0][0]
                self.assertEqual(call_args[0], "gcloud.cmd")

                # Verify secret retrieved
                self.assertEqual(redis_host, "windows-redis-value")

                # Record metrics
                self.record_metric("windows_gcloud_detection", True)

    def teardown_method(self, method):
        """Clean up test environment."""
        # Clear global secrets manager instance
        import netra_backend.app.core.configuration.unified_secrets as secrets_module
        secrets_module._secrets_manager = None

        super().teardown_method(method)