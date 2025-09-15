"""
Integration tests for Redis configuration validation in health endpoints.

These tests reproduce the issue where missing Redis configuration (REDIS_HOST)
causes health endpoint validation failures in staging environment.

Issue #598: Health endpoint should return 503 initially, 200 after configuration fix.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from netra_backend.app.main import app
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env
from netra_backend.app.core.backend_environment import BackendEnvironment
from netra_backend.app.core.health_checkers import check_redis_health
from netra_backend.app.redis_manager import redis_manager


class TestRedisConfigurationValidationIntegration(SSotAsyncTestCase):
    """Integration tests for Redis configuration validation failures."""

    def setUp(self):
        """Set up test environment with isolated configuration."""
        super().setUp()

        # Enable environment isolation for test-specific configuration
        self.env = get_env()
        self.env.enable_isolation()

        # Set up staging environment for proper validation
        self.env.set("ENVIRONMENT", "staging", source="test_redis_config_validation")

    def tearDown(self):
        """Clean up test environment."""
        # Reset Redis manager state
        if hasattr(redis_manager, '_connected'):
            redis_manager._connected = False
        if hasattr(redis_manager, '_client'):
            redis_manager._client = None
        super().tearDown()

    def test_redis_configuration_missing_host_validation_failure(self):
        """Test that missing REDIS_HOST causes configuration validation failure."""
        # Configure staging environment with missing Redis configuration
        self.env.set("ENVIRONMENT", "staging", source="test_redis_missing_host")
        self.env.set("REDIS_HOST", "", source="test_redis_missing_host")  # Empty Redis host
        self.env.set("SECRET_KEY", "test-staging-secret-key-32-chars-min", source="test_redis_missing_host")

        # Initialize BackendEnvironment with missing Redis config
        backend_env = BackendEnvironment()

        # Test that Redis configuration validation detects missing host
        with self.assertRaises(ValueError) as context:
            backend_env.get_redis_url()

        self.assertIn("Redis configuration required", str(context.exception))
        self.assertIn("staging environment", str(context.exception))

    def test_redis_configuration_builder_validation_failure(self):
        """Test that RedisConfigurationBuilder detects missing configuration."""
        from shared.redis_configuration_builder import RedisConfigurationBuilder

        # Create environment with missing Redis host
        env_vars = {
            "ENVIRONMENT": "staging",
            "REDIS_HOST": "",  # Missing Redis host
            "REDIS_PORT": "6379",
            "REDIS_DB": "0"
        }

        builder = RedisConfigurationBuilder(env_vars)

        # Test validation failure
        is_valid, error_message = builder.validate()

        self.assertFalse(is_valid)
        self.assertIn("Missing required variables for staging", error_message)
        self.assertIn("REDIS_HOST", error_message)

    def test_redis_configuration_builder_staging_no_config(self):
        """Test that RedisConfigurationBuilder returns None for missing staging config."""
        from shared.redis_configuration_builder import RedisConfigurationBuilder

        # Create environment with no Redis configuration
        env_vars = {
            "ENVIRONMENT": "staging",
            # No Redis configuration variables
        }

        builder = RedisConfigurationBuilder(env_vars)

        # Test that connection.has_config is False
        self.assertFalse(builder.connection.has_config)

        # Test that auto_url returns None
        auto_url = builder.staging.auto_url
        self.assertIsNone(auto_url)

    async def test_redis_health_check_missing_configuration(self):
        """Test that Redis health check handles missing configuration appropriately."""
        # Set up staging environment with missing Redis configuration
        self.env.set("ENVIRONMENT", "staging", source="test_redis_health_missing")
        self.env.set("REDIS_HOST", "", source="test_redis_health_missing")

        # Mock redis_manager to simulate configuration issues
        with patch('netra_backend.app.core.health_checkers.redis_manager') as mock_redis_manager:
            # Configure redis_manager to be enabled but fail on client access
            mock_redis_manager.enabled = True
            mock_redis_manager.get_client.side_effect = RuntimeError("Redis configuration not found")

            # Test Redis health check
            result = await check_redis_health()

            # Should return unhealthy result due to configuration issue
            self.assertEqual(result.status, "unhealthy")
            self.assertFalse(result.success)
            self.assertIn("Redis configuration not found", result.details.get("error_message", ""))

    async def test_redis_health_check_with_valid_configuration(self):
        """Test that Redis health check works with valid configuration."""
        # Set up staging environment with valid Redis configuration
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("REDIS_HOST", "localhost")
        self.set_env_var("REDIS_PORT", "6379")
        self.set_env_var("REDIS_DB", "0")

        # Mock successful Redis connection
        with patch('netra_backend.app.redis_manager.redis_manager') as mock_redis_manager:
            # Configure successful Redis manager
            mock_redis_manager.enabled = True
            mock_client = AsyncMock()
            mock_client.ping = AsyncMock(return_value=True)
            mock_redis_manager.get_client.return_value = mock_client

            # Test Redis health check
            result = await check_redis_health()

            # Should return healthy result
            self.assertEqual(result.status, "healthy")
            self.assertTrue(result.success)

    def test_backend_environment_redis_host_staging_validation(self):
        """Test BackendEnvironment Redis host validation in staging environment."""
        # Set up staging environment with missing Redis host
        self.env.set("ENVIRONMENT", "staging", source="test_backend_redis_host")
        self.env.set("REDIS_HOST", "", source="test_backend_redis_host")

        backend_env = BackendEnvironment()

        # Test that get_redis_host raises ValueError for staging with missing host
        with self.assertRaises(ValueError) as context:
            backend_env.get_redis_host()

        self.assertIn("REDIS_HOST required", str(context.exception))
        self.assertIn("staging environment", str(context.exception))

    def test_backend_environment_validation_redis_missing(self):
        """Test BackendEnvironment.validate() detects missing Redis configuration."""
        # Set up staging environment with missing Redis configuration
        self.env.set("ENVIRONMENT", "staging", source="test_validation_redis")
        self.env.set("REDIS_HOST", "", source="test_validation_redis")
        self.env.set("SECRET_KEY", "test-staging-secret-key-32-chars-min", source="test_validation_redis")

        backend_env = BackendEnvironment()

        # Test validation
        validation_result = backend_env.validate()

        self.assertFalse(validation_result["valid"])
        self.assertTrue(any("Redis configuration" in issue for issue in validation_result["issues"]))
        self.assertEqual(validation_result["environment"], "staging")

    def test_backend_environment_validation_redis_present(self):
        """Test BackendEnvironment.validate() passes with valid Redis configuration."""
        # Set up staging environment with valid Redis configuration
        self.env.set("ENVIRONMENT", "staging", source="test_validation_redis_ok")
        self.env.set("REDIS_HOST", "localhost", source="test_validation_redis_ok")
        self.env.set("REDIS_PORT", "6379", source="test_validation_redis_ok")
        self.env.set("REDIS_DB", "0", source="test_validation_redis_ok")
        self.env.set("SECRET_KEY", "test-staging-secret-key-32-chars-min", source="test_validation_redis_ok")

        backend_env = BackendEnvironment()

        # Test validation
        validation_result = backend_env.validate()

        # Should pass validation (or at least not fail on Redis)
        redis_issues = [issue for issue in validation_result["issues"] if "Redis" in issue]
        self.assertEqual(len(redis_issues), 0, f"Unexpected Redis validation issues: {redis_issues}")

    def test_development_environment_redis_fallback(self):
        """Test that development environment has Redis fallback behavior."""
        # Set up development environment with missing Redis configuration
        self.env.set("ENVIRONMENT", "development", source="test_dev_redis_fallback")
        self.env.set("REDIS_HOST", "", source="test_dev_redis_fallback")

        backend_env = BackendEnvironment()

        # Development should have fallback behavior
        redis_url = backend_env.get_redis_url()

        # Should get fallback URL
        self.assertIsNotNone(redis_url)
        self.assertIn("redis://localhost:6379", redis_url)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])