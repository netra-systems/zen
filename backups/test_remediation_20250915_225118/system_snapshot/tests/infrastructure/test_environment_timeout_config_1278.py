"""
Environment Detection and Timeout Configuration Tests for Issue #1278

This test suite validates environment detection and timeout configuration
issues specific to Issue #1278:
- Staging environment detection accuracy
- Database timeout configuration (600s requirement)
- Cloud Run startup timeout handling
- VPC connector timeout interactions

These tests SHOULD FAIL to demonstrate configuration problems.
"""

import asyncio
import time
import os
from typing import Dict, Any, Optional
import pytest
from unittest.mock import patch, Mock

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from dev_launcher.isolated_environment import IsolatedEnvironment
from netra_backend.app.core.configuration.database import DatabaseConfiguration
from netra_backend.app.core.configuration.base import BaseConfiguration
from netra_backend.app.core.configuration.services import ServicesConfiguration


class TestEnvironmentDetection1278(SSotAsyncTestCase):
    """Test environment detection accuracy for Issue #1278"""

    def setUp(self):
        super().setUp()
        self.env = IsolatedEnvironment()

    def test_staging_environment_detection_accuracy(self):
        """
        Test that staging environment is correctly detected.

        Issue #1278 specifically affects staging environment.
        This test ensures environment detection is accurate.
        """
        # Get current environment
        detected_environment = self.env.get_string("ENVIRONMENT", "unknown")

        print(f"Detected environment: {detected_environment}")

        # Check all environment indicators
        environment_indicators = {
            "ENVIRONMENT": self.env.get_string("ENVIRONMENT", None),
            "APP_ENV": self.env.get_string("APP_ENV", None),
            "STAGE": self.env.get_string("STAGE", None),
            "DEPLOYMENT_ENV": self.env.get_string("DEPLOYMENT_ENV", None),
            "GOOGLE_CLOUD_PROJECT": self.env.get_string("GOOGLE_CLOUD_PROJECT", None),
        }

        print(f"Environment indicators:")
        for key, value in environment_indicators.items():
            print(f"  {key}: {value}")

        # Check for staging-specific configuration
        staging_indicators = [
            self.env.get_string("DATABASE_HOST", "").endswith("staging.netrasystems.ai"),
            "staging" in self.env.get_string("GOOGLE_CLOUD_PROJECT", "").lower(),
            "staging" in detected_environment.lower(),
            self.env.get_string("API_BASE_URL", "").endswith("staging.netrasystems.ai")
        ]

        print(f"Staging indicators: {staging_indicators}")

        # If we're testing in staging, ensure it's properly detected
        if any(staging_indicators):
            self.assertIn("staging", detected_environment.lower(),
                         "Staging environment not properly detected")

    def test_staging_specific_configuration_validation(self):
        """
        Test staging-specific configuration requirements.

        Issue #1278 requires specific staging configuration including
        VPC connector, domain names, and timeout values.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Check required staging configuration
        required_staging_config = {
            "DATABASE_HOST": "Must contain staging.netrasystems.ai or valid staging host",
            "VPC_CONNECTOR": "Must be configured for staging-connector",
            "API_BASE_URL": "Must use staging.netrasystems.ai domain",
            "FRONTEND_URL": "Must use staging.netrasystems.ai domain",
            "WEBSOCKET_URL": "Must use api.staging.netrasystems.ai domain"
        }

        configuration_issues = []

        for config_key, requirement in required_staging_config.items():
            config_value = self.env.get_string(config_key, None)

            if config_value is None:
                configuration_issues.append(f"{config_key}: Missing - {requirement}")
            elif config_key in ["API_BASE_URL", "FRONTEND_URL"] and "staging.netrasystems.ai" not in config_value:
                configuration_issues.append(f"{config_key}: {config_value} - {requirement}")
            elif config_key == "WEBSOCKET_URL" and "api.staging.netrasystems.ai" not in config_value:
                configuration_issues.append(f"{config_key}: {config_value} - {requirement}")

        print(f"Staging Configuration Validation:")
        for config_key, requirement in required_staging_config.items():
            value = self.env.get_string(config_key, "NOT SET")
            print(f"  {config_key}: {value}")

        if configuration_issues:
            print(f"Configuration issues found:")
            for issue in configuration_issues:
                print(f"  - {issue}")

        # This assertion SHOULD FAIL if staging configuration is incorrect
        self.assertEqual(len(configuration_issues), 0,
                        f"Staging configuration issues: {configuration_issues}")


class TestTimeoutConfiguration1278(SSotAsyncTestCase):
    """Test timeout configuration for Issue #1278"""

    def setUp(self):
        super().setUp()
        self.env = IsolatedEnvironment()
        self.database_config = DatabaseConfiguration()

    def test_database_timeout_600s_requirement(self):
        """
        Test 600s database timeout requirement for Issue #1278.

        Issue #1278 specifically mentions 600s timeout requirement
        for Cloud Run database connections.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Get database configuration
        db_config = self.database_config.get_connection_config()

        print(f"Database timeout configuration:")
        print(f"  Raw config: {db_config}")

        # Check for 600s timeout configurations
        required_600s_timeouts = [
            "connect_timeout",
            "command_timeout",
            "server_connect_timeout",
            "pool_timeout"
        ]

        timeout_issues = []

        for timeout_key in required_600s_timeouts:
            # Check various possible timeout configuration locations
            timeout_value = None

            # Direct config check
            if timeout_key in db_config:
                timeout_value = db_config[timeout_key]

            # Environment variable check
            env_key = f"DATABASE_{timeout_key.upper()}"
            if timeout_value is None:
                timeout_value = self.env.get_string(env_key, None)

            # Convert to int if string
            if isinstance(timeout_value, str) and timeout_value.isdigit():
                timeout_value = int(timeout_value)

            print(f"  {timeout_key}: {timeout_value}")

            # Validate 600s requirement
            if timeout_value is None:
                timeout_issues.append(f"{timeout_key}: Not configured")
            elif isinstance(timeout_value, (int, float)) and timeout_value < 600:
                timeout_issues.append(f"{timeout_key}: {timeout_value}s < 600s requirement")

        if timeout_issues:
            print(f"Timeout configuration issues:")
            for issue in timeout_issues:
                print(f"  - {issue}")

        # This assertion SHOULD FAIL if 600s timeouts are not configured
        self.assertEqual(len(timeout_issues), 0,
                        f"Database timeout configuration issues: {timeout_issues}")

    def test_cloud_run_startup_timeout_configuration(self):
        """
        Test Cloud Run startup timeout configuration.

        Issue #1278 mentions startup failures due to timeout issues.
        This test validates startup timeout configuration.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Check Cloud Run startup timeout configurations
        startup_timeout_configs = {
            "STARTUP_TIMEOUT": "Overall startup timeout",
            "HEALTH_CHECK_TIMEOUT": "Health check timeout",
            "DATABASE_STARTUP_TIMEOUT": "Database initialization timeout",
            "SERVICE_STARTUP_TIMEOUT": "Service startup timeout",
            "CONTAINER_STARTUP_TIMEOUT": "Container startup timeout"
        }

        startup_timeout_issues = []

        print(f"Cloud Run startup timeout configuration:")

        for config_key, description in startup_timeout_configs.items():
            timeout_value = self.env.get_string(config_key, None)

            if timeout_value and timeout_value.isdigit():
                timeout_value = int(timeout_value)

            print(f"  {config_key}: {timeout_value} ({description})")

            # Validate startup timeouts are sufficient for staging
            if timeout_value is None:
                # Some timeouts are optional, so only flag if critical
                if config_key in ["HEALTH_CHECK_TIMEOUT", "DATABASE_STARTUP_TIMEOUT"]:
                    startup_timeout_issues.append(f"{config_key}: Not configured - {description}")
            elif isinstance(timeout_value, (int, float)) and timeout_value < 120:
                # Startup timeouts should be at least 2 minutes for staging
                startup_timeout_issues.append(f"{config_key}: {timeout_value}s too short for staging - {description}")

        if startup_timeout_issues:
            print(f"Startup timeout issues:")
            for issue in startup_timeout_issues:
                print(f"  - {issue}")

        # This assertion might FAIL if startup timeouts are insufficient
        self.assertLessEqual(len(startup_timeout_issues), 2,
                           f"Too many startup timeout issues: {startup_timeout_issues}")

    async def test_vpc_connector_timeout_interaction(self):
        """
        Test VPC connector timeout interaction.

        Issue #1278 may involve timeout interactions between Cloud Run
        and VPC connector. This test validates these interactions.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Check VPC connector related timeouts
        vpc_timeout_configs = {
            "VPC_CONNECTOR_TIMEOUT": "VPC connector operation timeout",
            "VPC_CONNECTOR_EGRESS": "VPC connector egress setting",
            "CLOUD_SQL_TIMEOUT": "Cloud SQL connection timeout through VPC",
            "PRIVATE_IP_TIMEOUT": "Private IP access timeout"
        }

        vpc_timeout_results = {}

        print(f"VPC connector timeout configuration:")

        for config_key, description in vpc_timeout_configs.items():
            config_value = self.env.get_string(config_key, None)
            vpc_timeout_results[config_key] = config_value

            print(f"  {config_key}: {config_value} ({description})")

        # Test actual VPC connector timeout behavior
        vpc_timeout_test_results = {}

        try:
            # Test database connection timing through VPC
            start_time = time.time()

            # This should go through VPC connector in staging
            from netra_backend.app.db.database_manager import DatabaseManager
            db_manager = DatabaseManager()

            # Use asyncio.wait_for to test timeout behavior
            connection = await asyncio.wait_for(
                db_manager.get_connection_async(),
                timeout=30  # 30 second test timeout
            )

            end_time = time.time()
            vpc_connection_time = end_time - start_time

            vpc_timeout_test_results["vpc_connection"] = {
                "success": True,
                "duration": vpc_connection_time
            }

            print(f"  VPC connection test: SUCCESS ({vpc_connection_time:.2f}s)")

        except asyncio.TimeoutError:
            end_time = time.time()
            vpc_connection_time = end_time - start_time

            vpc_timeout_test_results["vpc_connection"] = {
                "success": False,
                "duration": vpc_connection_time,
                "error": "Timeout"
            }

            print(f"  VPC connection test: TIMEOUT ({vpc_connection_time:.2f}s)")

        except Exception as e:
            end_time = time.time()
            vpc_connection_time = end_time - start_time

            vpc_timeout_test_results["vpc_connection"] = {
                "success": False,
                "duration": vpc_connection_time,
                "error": str(e)
            }

            print(f"  VPC connection test: ERROR ({vpc_connection_time:.2f}s) - {str(e)}")

        # This assertion SHOULD FAIL if VPC connector timeouts are problematic
        vpc_connection_success = vpc_timeout_test_results.get("vpc_connection", {}).get("success", False)
        self.assertTrue(vpc_connection_success,
                       "VPC connector timeout issues detected")


class TestConfigurationDrift1278(SSotAsyncTestCase):
    """Test configuration drift issues for Issue #1278"""

    def setUp(self):
        super().setUp()
        self.env = IsolatedEnvironment()

    def test_staging_configuration_consistency(self):
        """
        Test staging configuration consistency across services.

        Issue #1278 may be caused by configuration drift between
        different services or deployment stages.
        """
        environment = self.env.get_string("ENVIRONMENT", "development")

        if environment != "staging":
            self.skipTest("This test requires staging environment")

        # Check configuration consistency across different sources
        config_sources = {
            "database": DatabaseConfiguration(),
            "services": ServicesConfiguration(),
            "base": BaseConfiguration()
        }

        consistency_issues = []

        # Check database host consistency
        database_hosts = {}
        for source_name, config_source in config_sources.items():
            try:
                if hasattr(config_source, 'get_connection_config'):
                    db_config = config_source.get_connection_config()
                    if 'host' in db_config:
                        database_hosts[source_name] = db_config['host']
                elif hasattr(config_source, 'database_host'):
                    database_hosts[source_name] = config_source.database_host
            except Exception as e:
                print(f"Error getting database host from {source_name}: {e}")

        print(f"Database hosts from different sources:")
        for source, host in database_hosts.items():
            print(f"  {source}: {host}")

        # Check for consistency
        unique_hosts = set(database_hosts.values())
        if len(unique_hosts) > 1:
            consistency_issues.append(f"Inconsistent database hosts: {database_hosts}")

        # Check environment variable consistency
        critical_env_vars = [
            "DATABASE_HOST",
            "DATABASE_PORT",
            "DATABASE_NAME",
            "API_BASE_URL",
            "FRONTEND_URL",
            "WEBSOCKET_URL"
        ]

        env_var_values = {}
        for var in critical_env_vars:
            value = self.env.get_string(var, None)
            env_var_values[var] = value

        print(f"Critical environment variables:")
        for var, value in env_var_values.items():
            print(f"  {var}: {value}")

        # Check for staging-specific values
        staging_domain_vars = ["API_BASE_URL", "FRONTEND_URL"]
        for var in staging_domain_vars:
            value = env_var_values.get(var)
            if value and "staging.netrasystems.ai" not in value:
                consistency_issues.append(f"{var} should contain staging.netrasystems.ai: {value}")

        if consistency_issues:
            print(f"Configuration consistency issues:")
            for issue in consistency_issues:
                print(f"  - {issue}")

        # This assertion SHOULD FAIL if configuration drift exists
        self.assertEqual(len(consistency_issues), 0,
                        f"Configuration consistency issues: {consistency_issues}")


if __name__ == "__main__":
    # Run these tests to validate environment and timeout configuration for Issue #1278
    pytest.main([__file__, "-v", "--tb=short"])