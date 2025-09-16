"""
Integration Tests for Issue #1278: Service Boundary Violations

PURPOSE: Test service startup independence and database timeout configurations.
EXPECTED RESULT: Should FAIL currently due to Issue #1278 infrastructure problems.

These tests validate that services can start independently and don't have
configuration conflicts that lead to middleware failures.
"""

import pytest
import asyncio
import time
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional
import importlib.util


class TestServiceBoundaryViolationsIntegration:
    """Test for service boundary violations causing Issue #1278 infrastructure failures"""

    def setup_method(self):
        """Setup test environment"""
        self.project_root = Path(__file__).parent.parent.parent.parent
        self.timeout_configs = {
            'database_timeout': 600,  # Issue #1278 requires 600s
            'startup_timeout': 120,
            'websocket_timeout': 30
        }

    def test_netra_backend_service_independence(self):
        """
        Test that netra_backend can start without other services

        EXPECTED: FAIL - Issue #1278 indicates service dependency problems
        """
        # Attempt to import core backend modules independently
        backend_modules = [
            'netra_backend.app.config',
            'netra_backend.app.core.configuration.base',
            'netra_backend.app.db.database_manager',
            'netra_backend.app.websocket_core.manager'
        ]

        failures = []
        for module_name in backend_modules:
            try:
                # Clear any cached imports
                if module_name in sys.modules:
                    del sys.modules[module_name]

                # Attempt import
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    failures.append(f"Module not found: {module_name}")
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            except Exception as e:
                failures.append(f"Import failed for {module_name}: {str(e)}")

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(failures) == 0, (
            f"Found {len(failures)} backend service independence violations:\n"
            f"{chr(10).join(failures)}"
        )

    def test_auth_service_independence(self):
        """
        Test that auth_service can start without netra_backend

        EXPECTED: FAIL - Issue #1278 indicates service dependency problems
        """
        auth_modules = [
            'auth_service.auth_core.core.jwt_handler',
            'auth_service.auth_core.core.session_manager',
            'auth_service.auth_core.core.token_validator'
        ]

        failures = []
        for module_name in auth_modules:
            try:
                # Clear any cached imports
                if module_name in sys.modules:
                    del sys.modules[module_name]

                # Attempt import
                spec = importlib.util.find_spec(module_name)
                if spec is None:
                    failures.append(f"Module not found: {module_name}")
                    continue

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            except Exception as e:
                failures.append(f"Import failed for {module_name}: {str(e)}")

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(failures) == 0, (
            f"Found {len(failures)} auth service independence violations:\n"
            f"{chr(10).join(failures)}"
        )

    def test_database_timeout_configuration(self):
        """
        Test that database timeout is properly configured for Issue #1278

        EXPECTED: FAIL - Issue #1278 requires 600s timeout configuration
        """
        config_violations = []

        # Check environment configuration
        try:
            from dev_launcher.isolated_environment import IsolatedEnvironment
            env = IsolatedEnvironment()

            # Check database timeout setting
            db_timeout = env.get_env('DATABASE_TIMEOUT', default='300')
            if int(db_timeout) < 600:
                config_violations.append(
                    f"DATABASE_TIMEOUT is {db_timeout}s, Issue #1278 requires 600s"
                )

        except Exception as e:
            config_violations.append(f"Failed to check database timeout: {str(e)}")

        # Check configuration files for timeout settings
        config_files = [
            self.project_root / '.env.staging.tests',
            self.project_root / '.env.test.local',
            self.project_root / 'netra_backend' / 'app' / 'core' / 'configuration' / 'database.py'
        ]

        for config_file in config_files:
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        content = f.read()

                    # Look for timeout configurations
                    if 'timeout' in content.lower():
                        if '600' not in content and 'DATABASE_TIMEOUT' in content:
                            config_violations.append(
                                f"Potential timeout misconfiguration in {config_file}"
                            )

                except Exception as e:
                    config_violations.append(
                        f"Failed to check config file {config_file}: {str(e)}"
                    )

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(config_violations) == 0, (
            f"Found {len(config_violations)} database timeout configuration violations:\n"
            f"{chr(10).join(config_violations)}"
        )

    def test_websocket_middleware_startup_sequence(self):
        """
        Test WebSocket middleware startup doesn't fail due to service dependencies

        EXPECTED: FAIL - Issue #1278 affects WebSocket middleware initialization
        """
        startup_failures = []

        try:
            # Test WebSocket manager import and basic initialization
            from netra_backend.app.websocket_core.manager import WebSocketManager

            # Attempt to create manager instance (should work without full app context)
            try:
                # This should fail gracefully, not crash with import errors
                manager = WebSocketManager()
                startup_failures.append("WebSocketManager created without app context - unexpected success")
            except ImportError as e:
                startup_failures.append(f"WebSocketManager import failed: {str(e)}")
            except Exception:
                # Expected to fail due to missing app context, but not due to import errors
                pass

        except ImportError as e:
            startup_failures.append(f"WebSocket middleware import failed: {str(e)}")

        # Test CORS configuration import
        try:
            from netra_backend.app.core.websocket_cors import setup_cors
            # Should be importable without errors
        except ImportError as e:
            startup_failures.append(f"WebSocket CORS import failed: {str(e)}")

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(startup_failures) == 0, (
            f"Found {len(startup_failures)} WebSocket middleware startup failures:\n"
            f"{chr(10).join(startup_failures)}"
        )

    def test_configuration_isolation(self):
        """
        Test that service configurations don't interfere with each other

        EXPECTED: FAIL - Issue #1278 indicates configuration conflicts
        """
        isolation_violations = []

        # Test that backend config doesn't depend on auth service
        try:
            from netra_backend.app.config import get_config
            config = get_config()

            # Check for any auth_service references in config
            config_dict = config.__dict__ if hasattr(config, '__dict__') else {}
            for key, value in config_dict.items():
                if isinstance(value, str) and 'auth_service' in value:
                    isolation_violations.append(
                        f"Backend config references auth_service: {key}={value}"
                    )

        except Exception as e:
            isolation_violations.append(f"Backend config test failed: {str(e)}")

        # Test shared configuration independence
        try:
            from shared.cors_config import get_cors_config
            cors_config = get_cors_config()
            # Should work without service-specific dependencies
        except Exception as e:
            isolation_violations.append(f"Shared CORS config failed: {str(e)}")

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(isolation_violations) == 0, (
            f"Found {len(isolation_violations)} configuration isolation violations:\n"
            f"{chr(10).join(isolation_violations)}"
        )

    def test_vpc_connector_requirements(self):
        """
        Test VPC connector requirements for Issue #1278

        EXPECTED: FAIL - Issue #1278 requires specific VPC connector configuration
        """
        vpc_violations = []

        # Check for VPC connector configuration in deployment files
        vpc_files = [
            self.project_root / 'terraform-gcp-staging' / 'vpc-connector.tf',
            self.project_root / 'scripts' / 'deploy_to_gcp.py'
        ]

        for vpc_file in vpc_files:
            if vpc_file.exists():
                try:
                    with open(vpc_file, 'r') as f:
                        content = f.read()

                    # Check for staging-connector and all-traffic configuration
                    if 'staging-connector' not in content:
                        vpc_violations.append(
                            f"Missing staging-connector configuration in {vpc_file}"
                        )

                    if 'all-traffic' not in content and 'ALL_TRAFFIC' not in content:
                        vpc_violations.append(
                            f"Missing all-traffic egress configuration in {vpc_file}"
                        )

                except Exception as e:
                    vpc_violations.append(f"Failed to check VPC file {vpc_file}: {str(e)}")

        # Check environment variables for VPC configuration
        try:
            from dev_launcher.isolated_environment import IsolatedEnvironment
            env = IsolatedEnvironment()

            vpc_connector = env.get_env('VPC_CONNECTOR', default='')
            if 'staging-connector' not in vpc_connector and vpc_connector:
                vpc_violations.append(
                    f"VPC_CONNECTOR environment variable incorrect: {vpc_connector}"
                )

        except Exception as e:
            vpc_violations.append(f"Failed to check VPC environment: {str(e)}")

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(vpc_violations) == 0, (
            f"Found {len(vpc_violations)} VPC connector configuration violations:\n"
            f"{chr(10).join(vpc_violations)}"
        )

    def test_ssl_certificate_domain_configuration(self):
        """
        Test SSL certificate domain configuration for Issue #1278

        EXPECTED: FAIL - Issue #1278 requires *.netrasystems.ai domains
        """
        ssl_violations = []

        # Check environment files for domain configuration
        env_files = [
            self.project_root / '.env.staging.tests',
            self.project_root / '.env.staging.e2e'
        ]

        for env_file in env_files:
            if env_file.exists():
                try:
                    with open(env_file, 'r') as f:
                        content = f.read()

                    # Check for deprecated staging subdomain
                    if 'staging.netrasystems.ai' in content:
                        ssl_violations.append(
                            f"Found deprecated *.staging.netrasystems.ai domain in {env_file}"
                        )

                    # Check for direct Cloud Run URLs (should be avoided)
                    if 'run.app' in content:
                        ssl_violations.append(
                            f"Found direct Cloud Run URL in {env_file} (bypasses load balancer)"
                        )

                except Exception as e:
                    ssl_violations.append(f"Failed to check environment file {env_file}: {str(e)}")

        # This test SHOULD FAIL if Issue #1278 is active
        assert len(ssl_violations) == 0, (
            f"Found {len(ssl_violations)} SSL certificate domain violations:\n"
            f"{chr(10).join(ssl_violations)}"
        )


if __name__ == "__main__":
    # Allow direct execution for debugging
    pytest.main([__file__, "-v", "--tb=short"])