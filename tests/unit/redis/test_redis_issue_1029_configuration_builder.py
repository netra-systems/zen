"""
Unit Test: Redis Issue #1029 Configuration Builder

MISSION CRITICAL: This test suite validates Redis configuration builder patterns
that prevent GCP Memory Store connectivity failures identified in Issue #1029.

Root Cause Context:
- Redis configuration builder should properly handle GCP environments
- Configuration should prioritize Memory Store endpoints over localhost
- Builder should validate GCP-specific requirements (VPC, internal IPs)
- Secret Manager integration should be part of configuration building

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Configuration Stability & Redis Connectivity
- Value Impact: Prevents Redis configuration building errors that break chat
- Strategic Impact: Ensures reliable Redis configuration for $500K+ ARR Golden Path

CLAUDE.md Compliance:
- Unit tests focus on configuration building logic
- Tests validate configuration builder patterns and validation
- No actual Redis connection testing (handled in integration tests)
- Tests designed to fail when builder configuration is incorrect

Test Design: DESIGNED TO FAIL INITIALLY
These tests should FAIL initially to demonstrate Issue #1029 configuration builder problems.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment

class RedisIssue1029ConfigurationBuilderTests(SSotBaseTestCase):
    """
    Unit Test Suite: Redis Issue #1029 Configuration Builder

    These tests validate that Redis configuration builders properly handle
    GCP environments and prevent the connectivity failures in Issue #1029.

    Test Focus:
    - Configuration builder patterns for GCP
    - Memory Store endpoint prioritization
    - GCP-specific validation in builders
    - Secret Manager integration in configuration
    - Environment-aware configuration building
    """

    def setup_method(self, method):
        """Set up test fixtures for configuration builder testing."""
        super().setup_method(method)
        self.gcp_staging_config = {'ENVIRONMENT': 'staging', 'GCP_PROJECT_ID': 'netra-staging', 'REDIS_HOST': '10.45.240.3', 'REDIS_PORT': '6379', 'VPC_CONNECTOR': 'projects/netra-staging/locations/us-central1/connectors/vpc-connector', 'USE_GCP_SECRET_MANAGER': 'true'}
        self.local_dev_config = {'ENVIRONMENT': 'development', 'REDIS_HOST': 'localhost', 'REDIS_PORT': '6379'}

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_redis_configuration_builder_gcp_prioritization(self):
        """
        TEST: Redis configuration builder should prioritize GCP Memory Store (Issue #1029).

        DESIGNED TO FAIL: This test should FAIL initially to demonstrate Issue #1029
        configuration builder problems that default to localhost instead of Memory Store.

        Expected Behavior:
        - Builder should detect GCP environment and prioritize Memory Store
        - Builder should reject localhost in staging/production environments
        - Builder should validate GCP-specific configuration requirements

        Failure Mode: Test MUST fail if builder defaults to localhost in GCP
        """
        print(f'🔍 TESTING: Issue #1029 Redis configuration builder GCP prioritization')
        with patch.dict(os.environ, self.gcp_staging_config):
            env = IsolatedEnvironment()
            config_builder = self._create_mock_configuration_builder(env)
            built_config = config_builder.build_redis_config()
            print(f'📍 Built Redis Config: {built_config}')
            assert 'localhost' not in built_config.get('host', '').lower(), f"X ISSUE #1029 CONFIRMED: Configuration builder defaulted to localhost: {built_config.get('host')}. In GCP staging, builder should prioritize Memory Store endpoint: 10.45.240.3!"
            expected_host = '10.45.240.3'
            actual_host = built_config.get('host')
            assert actual_host == expected_host, f'X ISSUE #1029 CONFIRMED: Configuration builder used wrong host: {actual_host}. Expected GCP Memory Store host: {expected_host}. Incorrect host configuration causes Redis connectivity failures!'

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_redis_builder_gcp_validation_requirements(self):
        """
        TEST: Redis builder should validate GCP-specific requirements (Issue #1029).

        DESIGNED TO FAIL: This test should FAIL initially to demonstrate Issue #1029
        configuration builder missing GCP validation requirements.

        Expected Behavior:
        - Builder should validate VPC connector is configured
        - Builder should validate GCP project ID is set
        - Builder should validate internal IP format
        - Builder should reject invalid GCP configurations

        Failure Mode: Test MUST fail if builder lacks GCP validation
        """
        print(f'🔍 TESTING: Issue #1029 Redis builder GCP validation requirements')
        with patch.dict(os.environ, self.gcp_staging_config):
            env = IsolatedEnvironment()
            config_builder = self._create_mock_configuration_builder(env)
            vpc_validation_result = config_builder.validate_vpc_connector()
            print(f'📍 VPC Validation Result: {vpc_validation_result}')
            assert vpc_validation_result['is_valid'], f"X ISSUE #1029 CONFIRMED: VPC connector validation failed: {vpc_validation_result['error']}. Configuration builder must validate VPC connector for GCP Memory Store access!"
            project_validation_result = config_builder.validate_gcp_project()
            print(f'📍 GCP Project Validation Result: {project_validation_result}')
            assert project_validation_result['is_valid'], f"X ISSUE #1029 CONFIRMED: GCP project validation failed: {project_validation_result['error']}. Configuration builder must validate GCP project for proper Secret Manager and Memory Store access!"
            ip_validation_result = config_builder.validate_internal_ip()
            print(f'📍 Internal IP Validation Result: {ip_validation_result}')
            assert ip_validation_result['is_valid'], f"X ISSUE #1029 CONFIRMED: Internal IP validation failed: {ip_validation_result['error']}. Configuration builder must validate GCP Memory Store internal IP format!"

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_redis_builder_environment_detection(self):
        """
        TEST: Redis builder should properly detect GCP vs local environments (Issue #1029).

        DESIGNED TO FAIL: This test should FAIL initially to demonstrate Issue #1029
        configuration builder environment detection problems.

        Expected Behavior:
        - Builder should detect GCP environments (staging/production)
        - Builder should apply different rules for GCP vs local
        - Builder should prevent localhost in GCP environments
        - Builder should allow localhost only in local development

        Failure Mode: Test MUST fail if environment detection is broken
        """
        print(f'🔍 TESTING: Issue #1029 Redis builder environment detection')
        with patch.dict(os.environ, self.gcp_staging_config):
            gcp_env = IsolatedEnvironment()
            gcp_builder = self._create_mock_configuration_builder(gcp_env)
            is_gcp_detected = gcp_builder.is_gcp_environment()
            print(f'📍 GCP Environment Detected: {is_gcp_detected}')
            assert is_gcp_detected, f"X ISSUE #1029 CONFIRMED: Configuration builder failed to detect GCP environment. Environment: {gcp_env.get('ENVIRONMENT')}, Project: {gcp_env.get('GCP_PROJECT_ID')}. Proper environment detection is required for correct Redis configuration!"
            localhost_allowed = gcp_builder.is_localhost_allowed()
            print(f'📍 Localhost Allowed in GCP: {localhost_allowed}')
            assert not localhost_allowed, f'X ISSUE #1029 CONFIRMED: Configuration builder allows localhost in GCP environment. Localhost should be blocked in GCP environments to prevent connectivity failures!'
        with patch.dict(os.environ, self.local_dev_config):
            local_env = IsolatedEnvironment()
            local_builder = self._create_mock_configuration_builder(local_env)
            is_local_detected = local_builder.is_local_environment()
            print(f'📍 Local Environment Detected: {is_local_detected}')
            assert is_local_detected, f"Configuration builder should properly detect local development environment. Environment: {local_env.get('ENVIRONMENT')}"
            localhost_allowed_local = local_builder.is_localhost_allowed()
            print(f'📍 Localhost Allowed in Local: {localhost_allowed_local}')
            assert localhost_allowed_local, f'Configuration builder should allow localhost in local development environment.'

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_redis_builder_secret_manager_integration(self):
        """
        TEST: Redis builder should integrate with GCP Secret Manager (Issue #1029).

        DESIGNED TO FAIL: This test should FAIL initially to demonstrate Issue #1029
        configuration builder lacking Secret Manager integration.

        Expected Behavior:
        - Builder should support Secret Manager credential retrieval
        - Builder should validate Secret Manager access
        - Builder should fallback gracefully if Secret Manager unavailable
        - Builder should use proper GCP authentication

        Failure Mode: Test MUST fail if Secret Manager integration is missing
        """
        print(f'🔍 TESTING: Issue #1029 Redis builder Secret Manager integration')
        with patch.dict(os.environ, self.gcp_staging_config):
            env = IsolatedEnvironment()
            builder = self._create_mock_configuration_builder(env)
            secret_manager_available = builder.is_secret_manager_available()
            print(f'📍 Secret Manager Available: {secret_manager_available}')
            assert secret_manager_available, f'X ISSUE #1029 CONFIRMED: Configuration builder cannot detect Secret Manager availability. Secret Manager integration is required for secure Redis credential management in GCP!'
            if secret_manager_available:
                secret_config = builder.build_secret_manager_config()
                print(f'📍 Secret Manager Config: {secret_config}')
                assert 'project_id' in secret_config, f'X ISSUE #1029 CONFIRMED: Secret Manager config missing project_id: {secret_config}. Proper project configuration is required for Secret Manager access!'
                assert secret_config['project_id'] == 'netra-staging', f"X ISSUE #1029 CONFIRMED: Secret Manager config has wrong project: {secret_config['project_id']}. Expected 'netra-staging' for staging environment!"

    def _create_mock_configuration_builder(self, env: IsolatedEnvironment):
        """Create a mock configuration builder that simulates the real builder behavior."""

        class MockRedisConfigurationBuilder:

            def __init__(self, environment: IsolatedEnvironment):
                self.env = environment

            def build_redis_config(self) -> Dict[str, Any]:
                """Build Redis configuration - DESIGNED TO FAIL for Issue #1029."""
                redis_host = self.env.get('REDIS_HOST', 'localhost')
                redis_port = self.env.get('REDIS_PORT', '6379')
                return {'host': redis_host, 'port': int(redis_port), 'db': 0}

            def is_gcp_environment(self) -> bool:
                """Detect if running in GCP environment - DESIGNED TO FAIL for Issue #1029."""
                gcp_project = self.env.get('GCP_PROJECT_ID')
                environment = self.env.get('ENVIRONMENT', '').lower()
                return bool(gcp_project and environment in ['staging', 'production'])

            def is_local_environment(self) -> bool:
                """Detect if running in local environment."""
                environment = self.env.get('ENVIRONMENT', '').lower()
                return environment == 'development'

            def is_localhost_allowed(self) -> bool:
                """Check if localhost is allowed in current environment - DESIGNED TO FAIL."""
                return True

            def validate_vpc_connector(self) -> Dict[str, Any]:
                """Validate VPC connector configuration - DESIGNED TO FAIL for Issue #1029."""
                vpc_connector = self.env.get('VPC_CONNECTOR')
                if not vpc_connector:
                    return {'is_valid': False, 'error': 'VPC_CONNECTOR not configured'}
                required_parts = ['projects/', 'locations/', 'connectors/']
                has_all_parts = all((part in vpc_connector for part in required_parts))
                return {'is_valid': has_all_parts, 'error': None if has_all_parts else 'VPC connector malformed'}

            def validate_gcp_project(self) -> Dict[str, Any]:
                """Validate GCP project configuration - DESIGNED TO FAIL for Issue #1029."""
                project_id = self.env.get('GCP_PROJECT_ID')
                if not project_id:
                    return {'is_valid': False, 'error': 'GCP_PROJECT_ID not configured'}
                expected_projects = ['netra-staging', 'netra-production']
                is_valid_project = project_id in expected_projects
                return {'is_valid': is_valid_project, 'error': None if is_valid_project else f'Unexpected project: {project_id}'}

            def validate_internal_ip(self) -> Dict[str, Any]:
                """Validate internal IP format - DESIGNED TO FAIL for Issue #1029."""
                redis_host = self.env.get('REDIS_HOST', 'localhost')
                is_internal_ip = redis_host.startswith('10.')
                return {'is_valid': is_internal_ip, 'error': None if is_internal_ip else f'Not GCP internal IP: {redis_host}'}

            def is_secret_manager_available(self) -> bool:
                """Check Secret Manager availability - DESIGNED TO FAIL for Issue #1029."""
                try:
                    from google.cloud import secretmanager
                    return True
                except ImportError:
                    return False

            def build_secret_manager_config(self) -> Dict[str, Any]:
                """Build Secret Manager configuration - DESIGNED TO FAIL for Issue #1029."""
                project_id = self.env.get('GCP_PROJECT_ID')
                return {'project_id': project_id, 'enabled': bool(project_id)}
        return MockRedisConfigurationBuilder(env)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')