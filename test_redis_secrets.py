#!/usr/bin/env python3
"""
Test Redis Secret Loading for Issue #1343

This script validates that Redis secrets can be loaded properly from GCP Secret Manager
and that the Redis connection configuration is working correctly.

Usage:
    python test_redis_secrets.py [--environment staging|production]
"""

import os
import sys
from pathlib import Path
from typing import Dict, Optional, Any

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import necessary modules
from shared.isolated_environment import get_env
from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.core.configuration.unified_secrets import get_secrets_manager
from netra_backend.app.core.redis_connection_handler import RedisConnectionHandler

logger = get_logger(__name__)


class RedisSecretTester:
    """Test Redis secret loading and connection functionality."""

    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.env = get_env()
        self.secrets_manager = get_secrets_manager()

    def test_gcp_secret_access(self) -> Dict[str, Any]:
        """Test direct access to GCP secrets via gcloud command."""
        print("\n=== Testing GCP Secret Manager Access ===")

        secrets_to_test = [
            f"redis-host-{self.environment}",
            f"redis-port-{self.environment}",
            f"redis-password-{self.environment}",
            f"redis-url-{self.environment}"
        ]

        results = {}

        for secret_name in secrets_to_test:
            try:
                import subprocess
                result = subprocess.run(
                    ["gcloud", "secrets", "versions", "access", "latest",
                     "--secret", secret_name, "--project", f"netra-{self.environment}"],
                    capture_output=True,
                    text=True,
                    check=False
                )

                if result.returncode == 0:
                    # Obscure the actual value for security
                    value = result.stdout.strip()
                    obscured = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
                    results[secret_name] = {
                        "status": "SUCCESS",
                        "value_length": len(value),
                        "obscured_value": obscured
                    }
                    print(f"  PASS {secret_name}: {obscured} (length: {len(value)})")
                else:
                    results[secret_name] = {
                        "status": "FAILED",
                        "error": result.stderr.strip()
                    }
                    print(f"  FAIL {secret_name}: {result.stderr.strip()}")

            except Exception as e:
                results[secret_name] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"  FAIL {secret_name}: {e}")

        return results

    def test_environment_variable_loading(self) -> Dict[str, Any]:
        """Test loading Redis configuration from environment variables."""
        print("\n=== Testing Environment Variable Loading ===")

        env_vars_to_test = [
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB"
        ]

        results = {}

        for env_var in env_vars_to_test:
            try:
                value = self.env.get(env_var)
                if value:
                    # Obscure sensitive values
                    if "PASSWORD" in env_var:
                        obscured = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
                    else:
                        obscured = value

                    results[env_var] = {
                        "status": "FOUND",
                        "value_length": len(value),
                        "obscured_value": obscured
                    }
                    print(f"  PASS {env_var}: {obscured}")
                else:
                    results[env_var] = {
                        "status": "NOT_FOUND",
                        "value": None
                    }
                    print(f"  WARN {env_var}: Not found")

            except Exception as e:
                results[env_var] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"  FAIL {env_var}: {e}")

        return results

    def test_secrets_manager_loading(self) -> Dict[str, Any]:
        """Test the UnifiedSecretsManager for Redis secrets."""
        print("\n=== Testing UnifiedSecretsManager ===")

        secrets_to_test = [
            "REDIS_HOST",
            "REDIS_PORT",
            "REDIS_PASSWORD",
            "REDIS_DB"
        ]

        results = {}

        for secret_key in secrets_to_test:
            try:
                value = self.secrets_manager.get_secret(secret_key)
                if value:
                    # Obscure sensitive values
                    if "PASSWORD" in secret_key:
                        obscured = f"{value[:4]}***{value[-4:]}" if len(value) > 8 else "***"
                    else:
                        obscured = value

                    results[secret_key] = {
                        "status": "FOUND",
                        "value_length": len(value),
                        "obscured_value": obscured
                    }
                    print(f"  PASS {secret_key}: {obscured}")
                else:
                    results[secret_key] = {
                        "status": "NOT_FOUND",
                        "value": None
                    }
                    print(f"  WARN {secret_key}: Not found")

            except Exception as e:
                results[secret_key] = {
                    "status": "ERROR",
                    "error": str(e)
                }
                print(f"  FAIL {secret_key}: {e}")

        return results

    def test_redis_connection_handler(self) -> Dict[str, Any]:
        """Test the RedisConnectionHandler configuration."""
        print("\n=== Testing RedisConnectionHandler ===")

        try:
            # Set environment for the handler
            original_env = self.env.get("ENVIRONMENT")
            self.env.set("ENVIRONMENT", self.environment)

            handler = RedisConnectionHandler()

            # Get connection info
            connection_info = handler.get_connection_info()

            # Obscure password if present
            display_info = connection_info.copy()
            if display_info.get("password"):
                password = display_info["password"]
                display_info["password"] = f"{password[:4]}***{password[-4:]}" if len(password) > 8 else "***"

            print(f"  PASS Connection info loaded:")
            for key, value in display_info.items():
                if key not in ["socket_keepalive_options"]:  # Skip complex nested objects
                    print(f"     {key}: {value}")

            # Test environment config status
            config_status = handler.get_environment_config_status()
            print(f"  PASS Environment config status:")
            print(f"     Environment: {config_status['environment']}")
            print(f"     Host configured: {config_status['host_configured']}")
            print(f"     Localhost warning: {config_status['localhost_warning']}")
            print(f"     SSL enabled: {config_status['ssl_enabled']}")

            # Restore original environment
            if original_env:
                self.env.set("ENVIRONMENT", original_env)

            return {
                "status": "SUCCESS",
                "connection_info": connection_info,
                "config_status": config_status
            }

        except Exception as e:
            print(f"  FAIL RedisConnectionHandler error: {e}")
            return {
                "status": "ERROR",
                "error": str(e)
            }

    def test_redis_connection_validation(self) -> Dict[str, Any]:
        """Test actual Redis connection validation."""
        print("\n=== Testing Redis Connection Validation ===")

        try:
            # Set environment for the handler
            original_env = self.env.get("ENVIRONMENT")
            self.env.set("ENVIRONMENT", self.environment)

            handler = RedisConnectionHandler()

            # Validate connection
            validation_result = handler.validate_connection()

            if validation_result["connected"]:
                print(f"  PASS Redis connection successful:")
                print(f"     Host: {validation_result['host']}")
                print(f"     Port: {validation_result['port']}")
                print(f"     Response time: {validation_result['response_time_ms']}ms")
            else:
                print(f"  FAIL Redis connection failed:")
                print(f"     Host: {validation_result['host']}")
                print(f"     Port: {validation_result['port']}")
                print(f"     Error: {validation_result['error']}")

            # Restore original environment
            if original_env:
                self.env.set("ENVIRONMENT", original_env)

            return validation_result

        except Exception as e:
            print(f"  FAIL Redis connection validation error: {e}")
            return {
                "status": "ERROR",
                "error": str(e)
            }

    def run_complete_test(self) -> Dict[str, Any]:
        """Run all Redis secret loading tests."""
        print(f"Redis Secret Loading Test for Environment: {self.environment}")
        print("=" * 60)

        results = {
            "environment": self.environment,
            "gcp_secrets": self.test_gcp_secret_access(),
            "env_vars": self.test_environment_variable_loading(),
            "secrets_manager": self.test_secrets_manager_loading(),
            "connection_handler": self.test_redis_connection_handler(),
            "connection_validation": self.test_redis_connection_validation()
        }

        # Summary
        print("\n=== Test Summary ===")
        total_tests = 0
        passed_tests = 0

        for test_category, test_results in results.items():
            if test_category == "environment":
                continue

            if isinstance(test_results, dict):
                if "status" in test_results:
                    # Single test result
                    total_tests += 1
                    if test_results["status"] in ["SUCCESS", "FOUND"]:
                        passed_tests += 1
                        print(f"  PASS {test_category}: PASSED")
                    else:
                        print(f"  FAIL {test_category}: FAILED - {test_results.get('error', 'Unknown error')}")
                else:
                    # Multiple test results
                    for item_name, item_result in test_results.items():
                        total_tests += 1
                        if isinstance(item_result, dict) and item_result.get("status") in ["SUCCESS", "FOUND"]:
                            passed_tests += 1

        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")

        if passed_tests == total_tests:
            print("All tests passed! Redis secret loading is working correctly.")
        else:
            print("Some tests failed. Redis secret loading needs fixes.")

        return results


def main():
    """Main test execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Redis secret loading")
    parser.add_argument("--environment",
                       choices=["staging", "production"],
                       default="staging",
                       help="Environment to test (default: staging)")

    args = parser.parse_args()

    tester = RedisSecretTester(args.environment)
    results = tester.run_complete_test()

    # Return appropriate exit code
    if all(test.get("status") in ["SUCCESS", "FOUND"] for test in results.values() if isinstance(test, dict) and "status" in test):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()