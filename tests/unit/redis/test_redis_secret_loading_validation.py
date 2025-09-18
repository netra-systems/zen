"""
Redis Secret Loading Validation Unit Tests - Issue #1343

Comprehensive unit tests for Redis secret loading functionality to validate
the GCP Secret Manager integration fixes for Cloud Run deployment issues.

Business Value: Early/Mid Tier - System Stability & Platform Infrastructure
Ensures Redis configuration loads properly in staging/production environments,
preventing cache and session failures that could cost $30K+ MRR.

SSOT Compliance: Uses SSotBaseTestCase, IsolatedEnvironment, and unified secrets patterns.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from test_framework.ssot.base_test_case import SSotBaseTestCase

from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler, RedisConnectionError
from netra_backend.app.core.configuration.unified_secrets import UnifiedSecretsManager, SecretConfig


class TestRedisSecretLoadingValidation(SSotBaseTestCase):
    """Unit tests for Redis secret loading with GCP Secret Manager integration."""

    def setup_method(self, method):
        """Setup test environment with isolated configuration."""
        super().setup_method(method)

        # Set up test environment variables
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("GCP_PROJECT_ID", "test-project")

        # Clear any cached secrets manager instance
        if hasattr(UnifiedSecretsManager, '_secrets_manager'):
            delattr(UnifiedSecretsManager, '_secrets_manager')

    def test_redis_secrets_loaded_from_gcp_secret_manager(self):
        """Test that Redis secrets are properly loaded from GCP Secret Manager."""

        # Mock GCP Secret Manager responses
        mock_gcp_responses = {
            "redis-host-staging": "redis-staging.example.com",
            "redis-port-staging": "6379",
            "redis-password-staging": "secret-password-123",
            "redis-db-staging": "1"
        }

        with patch('subprocess.run') as mock_subprocess:
            # Configure subprocess mock to return different secrets
            def subprocess_side_effect(*args, **kwargs):
                mock_result = Mock()
                cmd = args[0]
                secret_name = cmd[5]  # gcloud secrets versions access latest --secret SECRET_NAME

                if secret_name in mock_gcp_responses:
                    mock_result.returncode = 0
                    mock_result.stdout = mock_gcp_responses[secret_name]
                    mock_result.stderr = ""
                else:
                    mock_result.returncode = 1
                    mock_result.stdout = ""
                    mock_result.stderr = f"Secret {secret_name} not found"

                return mock_result

            mock_subprocess.side_effect = subprocess_side_effect

            # Create Redis connection handler
            handler = RedisConnectionHandler()
            connection_info = handler.get_connection_info()

            # Verify secrets were loaded from GCP
            self.assertEqual(connection_info["host"], "redis-staging.example.com")
            self.assertEqual(connection_info["port"], 6379)
            self.assertEqual(connection_info["password"], "secret-password-123")
            self.assertEqual(connection_info["db"], 1)
            self.assertEqual(connection_info["environment"], "staging")

            # Verify GCP Secret Manager was called
            expected_calls = [
                call(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret', 'redis-host-staging', '--project', 'test-project'],
                     capture_output=True, text=True, check=False, timeout=10),
                call(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret', 'redis-port-staging', '--project', 'test-project'],
                     capture_output=True, text=True, check=False, timeout=10),
                call(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret', 'redis-db-staging', '--project', 'test-project'],
                     capture_output=True, text=True, check=False, timeout=10),
                call(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret', 'redis-password-staging', '--project', 'test-project'],
                     capture_output=True, text=True, check=False, timeout=10)
            ]

            # Assert that gcloud commands were called (order may vary)
            actual_calls = mock_subprocess.call_args_list
            self.assertGreater(len(actual_calls), 0, "GCP Secret Manager should have been called")

            # Record metrics for business value tracking
            self.record_metric("gcp_secret_calls", len(actual_calls))
            self.record_metric("redis_secrets_loaded", 4)

    def test_redis_secrets_fallback_to_environment_variables(self):
        """Test Redis configuration falls back to environment variables when GCP secrets fail."""

        # Set environment variable fallbacks
        self.set_env_var("REDIS_HOST", "localhost")
        self.set_env_var("REDIS_PORT", "6379")
        self.set_env_var("REDIS_PASSWORD", "env-password")
        self.set_env_var("REDIS_DB", "0")

        with patch('subprocess.run') as mock_subprocess:
            # Mock GCP Secret Manager to fail
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "Access denied"
            mock_subprocess.return_value = mock_result

            # Create Redis connection handler
            handler = RedisConnectionHandler()
            connection_info = handler.get_connection_info()

            # Verify fallback to environment variables
            self.assertEqual(connection_info["host"], "localhost")
            self.assertEqual(connection_info["port"], 6379)
            self.assertEqual(connection_info["password"], "env-password")
            self.assertEqual(connection_info["db"], 0)

            # Record metrics
            self.record_metric("gcp_secret_failures", len(mock_subprocess.call_args_list))
            self.record_metric("env_fallback_used", True)

    def test_redis_connection_with_loaded_secrets(self):
        """Test Redis connection creation using loaded secrets."""

        # Mock successful secret loading
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "redis-staging.example.com"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Mock Redis client creation
            with patch('redis.Redis') as mock_redis_class:
                mock_redis_instance = Mock()
                mock_redis_instance.ping.return_value = True
                mock_redis_class.return_value = mock_redis_instance

                # Create connection handler and get Redis client
                handler = RedisConnectionHandler()
                client = handler.get_redis_client()

                # Verify Redis client was created with proper configuration
                self.assertIsNotNone(client)
                mock_redis_class.assert_called_once()

                # Verify ping was called to test connection
                mock_redis_instance.ping.assert_called_once()

                # Record metrics
                self.record_metric("redis_connection_successful", True)

    def test_redis_connection_error_handling_with_invalid_secrets(self):
        """Test proper error handling when Redis secrets are invalid."""

        # Mock successful secret loading but invalid Redis host
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "invalid-redis-host"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Mock Redis client to fail connection
            with patch('redis.Redis') as mock_redis_class:
                mock_redis_instance = Mock()
                mock_redis_instance.ping.side_effect = Exception("Connection failed")
                mock_redis_class.return_value = mock_redis_instance

                # Create connection handler
                handler = RedisConnectionHandler()

                # Verify proper error handling
                with self.assertRaises(RedisConnectionError) as context:
                    handler.get_redis_client()

                # Verify error message includes connection failure details
                self.assertIn("Failed to create Redis client", str(context.exception))

                # Record metrics
                self.record_metric("redis_connection_errors", 1)

    def test_redis_validation_status_with_secrets(self):
        """Test Redis connection validation returns proper status with loaded secrets."""

        # Mock successful secret loading
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "redis-staging.example.com"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Mock successful Redis connection
            with patch('redis.Redis') as mock_redis_class:
                mock_redis_instance = Mock()
                mock_redis_instance.ping.return_value = True
                mock_redis_class.return_value = mock_redis_instance

                # Create connection handler and validate
                handler = RedisConnectionHandler()
                status = handler.validate_connection()

                # Verify validation status
                self.assertTrue(status["connected"])
                self.assertEqual(status["environment"], "staging")
                self.assertIsNotNone(status["response_time_ms"])
                self.assertIsNone(status["error"])

                # Record metrics
                self.record_metric("redis_validation_success", True)
                self.record_metric("redis_response_time_ms", status["response_time_ms"])

    def test_environment_specific_secret_mapping(self):
        """Test that environment-specific secret names are mapped correctly."""

        test_environments = ["staging", "production", "development"]

        for env in test_environments:
            with self.subTest(environment=env):
                # Set environment
                self.set_env_var("ENVIRONMENT", env)

                # Clear cached secrets manager
                if hasattr(UnifiedSecretsManager, '_secrets_manager'):
                    delattr(UnifiedSecretsManager, '_secrets_manager')

                # Create secrets manager and test mapping
                secrets_manager = UnifiedSecretsManager()

                # Test Redis host mapping
                expected_host_secret = f"redis-host-{env}"
                actual_mapping = secrets_manager._map_env_to_gcp_secret("REDIS_HOST")
                self.assertEqual(actual_mapping, expected_host_secret)

                # Test Redis password mapping
                expected_password_secret = f"redis-password-{env}"
                actual_mapping = secrets_manager._map_env_to_gcp_secret("REDIS_PASSWORD")
                self.assertEqual(actual_mapping, expected_password_secret)

                # Record metrics
                self.record_metric(f"secret_mapping_{env}_correct", True)

    def test_cloud_run_environment_detection(self):
        """Test Cloud Run environment detection enables GCP secrets automatically."""

        # Mock Cloud Run environment
        self.set_env_var("K_SERVICE", "redis-test-service")
        self.set_env_var("GCP_PROJECT_ID", "netra-staging")

        # Create secrets manager (should auto-detect Cloud Run)
        secrets_manager = UnifiedSecretsManager()

        # Verify GCP secrets are enabled
        self.assertTrue(secrets_manager.config.use_gcp_secrets)
        self.assertEqual(secrets_manager.config.gcp_project_id, "netra-staging")

        # Record metrics
        self.record_metric("cloud_run_detection", True)
        self.record_metric("gcp_secrets_auto_enabled", True)

    def test_redis_ssl_configuration_for_staging_production(self):
        """Test that SSL configuration is properly applied for staging/production environments."""

        staging_production_envs = ["staging", "production"]

        for env in staging_production_envs:
            with self.subTest(environment=env):
                # Set environment
                self.set_env_var("ENVIRONMENT", env)

                # Mock secret loading
                with patch('subprocess.run') as mock_subprocess:
                    mock_result = Mock()
                    mock_result.returncode = 0
                    mock_result.stdout = f"redis-{env}.example.com"
                    mock_result.stderr = ""
                    mock_subprocess.return_value = mock_result

                    # Create Redis connection handler
                    handler = RedisConnectionHandler()
                    connection_info = handler.get_connection_info()

                    # Verify SSL configuration
                    self.assertTrue(connection_info.get("ssl", False))
                    self.assertEqual(connection_info.get("ssl_cert_reqs"), "required")
                    self.assertTrue(connection_info.get("ssl_check_hostname", False))

                    # Record metrics
                    self.record_metric(f"ssl_config_{env}", True)

    def test_redis_connection_pool_creation_with_secrets(self):
        """Test Redis connection pool creation with loaded secrets."""

        # Mock successful secret loading
        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "redis-staging.example.com"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Mock Redis ConnectionPool
            with patch('redis.ConnectionPool') as mock_pool_class:
                mock_pool_instance = Mock()
                mock_pool_class.return_value = mock_pool_instance

                # Create connection handler and pool
                handler = RedisConnectionHandler()
                pool = handler.create_connection_pool()

                # Verify pool was created
                self.assertIsNotNone(pool)
                mock_pool_class.assert_called_once()

                # Verify pool configuration includes loaded secrets
                pool_config = mock_pool_class.call_args[1]
                self.assertEqual(pool_config["host"], "redis-staging.example.com")
                self.assertEqual(pool_config["max_connections"], 50)
                self.assertTrue(pool_config["socket_keepalive"])

                # Record metrics
                self.record_metric("connection_pool_created", True)
                self.record_metric("max_connections", pool_config["max_connections"])

    def test_secret_caching_functionality(self):
        """Test that secrets are properly cached to avoid repeated GCP calls."""

        with patch('subprocess.run') as mock_subprocess:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "cached-redis-host"
            mock_result.stderr = ""
            mock_subprocess.return_value = mock_result

            # Create secrets manager with caching enabled
            config = SecretConfig(cache_secrets=True)
            secrets_manager = UnifiedSecretsManager(config)

            # Get the same secret twice
            secret1 = secrets_manager.get_secret("REDIS_HOST")
            secret2 = secrets_manager.get_secret("REDIS_HOST")

            # Verify same value returned
            self.assertEqual(secret1, secret2)
            self.assertEqual(secret1, "cached-redis-host")

            # Verify GCP was only called once due to caching
            self.assertEqual(mock_subprocess.call_count, 1)

            # Record metrics
            self.record_metric("secret_caching_effective", True)
            self.record_metric("gcp_calls_saved_by_cache", 1)

    def teardown_method(self, method):
        """Clean up test environment."""
        # Clear any cached secrets manager instance
        if hasattr(UnifiedSecretsManager, '_secrets_manager'):
            delattr(UnifiedSecretsManager, '_secrets_manager')

        super().teardown_method(method)