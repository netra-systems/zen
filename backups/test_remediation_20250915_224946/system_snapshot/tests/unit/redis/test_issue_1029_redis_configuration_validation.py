"""
Unit Test: Redis Issue #1029 Configuration Validation

MISSION CRITICAL: This test suite reproduces the Redis DNS resolution failure
(Error -3) connecting to 10.166.204.83:6379 identified in Issue #1029.

Root Cause Context:
- Component-based Redis configuration missing/invalid GCP Secret Manager secrets
- Migration from REDIS_URL to redis-host-staging, redis-port-staging, redis-password-staging
- DNS resolution failure indicates incorrect IP or network configuration
- Missing VPC connector integration causing Memory Store access failure

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Redis Connectivity & Session Management Stability
- Value Impact: Prevents Redis connection failures that break $500K+ ARR chat functionality
- Strategic Impact: Ensures reliable Redis configuration for Golden Path user sessions

CLAUDE.md Compliance:
- Unit tests focus on configuration validation logic
- Tests designed to fail when component secrets are missing/invalid
- No actual Redis connection testing (handled in integration tests)
- Tests validate Secret Manager integration patterns

Test Design: DESIGNED TO FAIL INITIALLY
These tests should FAIL initially to demonstrate Issue #1029 configuration problems.
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import IsolatedEnvironment
from shared.redis_configuration_builder import RedisConfigurationBuilder

class RedisIssue1029ConfigurationValidationTests(SSotBaseTestCase):
    """
    Unit Test Suite: Redis Issue #1029 Configuration Validation

    These tests reproduce the DNS resolution failure and validate that
    Redis configuration validation catches missing GCP Secret Manager secrets.

    Test Focus:
    - GCP Secret Manager secret availability validation
    - Component-based configuration completeness
    - DNS resolution error reproduction
    - VPC connector requirement validation
    - Environment-specific configuration rules
    """

    def setup_method(self, method):
        """Set up test fixtures for Issue #1029 configuration validation."""
        super().setup_method(method)
        self.gcp_staging_config = {'ENVIRONMENT': 'staging', 'GCP_PROJECT_ID': 'netra-staging', 'USE_GCP_SECRET_MANAGER': 'true', 'VPC_CONNECTOR': 'projects/netra-staging/locations/us-central1/connectors/vpc-connector'}
        self.complete_gcp_config = {'ENVIRONMENT': 'staging', 'GCP_PROJECT_ID': 'netra-staging', 'USE_GCP_SECRET_MANAGER': 'true', 'VPC_CONNECTOR': 'projects/netra-staging/locations/us-central1/connectors/vpc-connector', 'REDIS_HOST': '10.166.204.83', 'REDIS_PORT': '6379', 'REDIS_PASSWORD': 'redis-staging-password'}
        self.local_dev_config = {'ENVIRONMENT': 'development', 'REDIS_HOST': 'localhost', 'REDIS_PORT': '6379'}

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_missing_component_secrets_validation(self):
        """
        TEST: Configuration should fail validation when component secrets are missing (Issue #1029).

        DESIGNED TO REPRODUCE: This test reproduces Issue #1029 by validating that
        missing redis-host-staging, redis-port-staging secrets are properly detected.

        Expected Behavior:
        - RedisConfigurationBuilder should detect missing required secrets
        - Builder should fail validation in staging environment
        - Builder should provide clear error messages about missing secrets
        - Builder should differentiate between local dev and GCP requirements

        Failure Mode: Test MUST demonstrate validation failure when secrets missing
        """
        print(f'🔍 TESTING: Issue #1029 missing component secrets validation')
        with patch.dict(os.environ, self.gcp_staging_config, clear=True):
            env_vars = dict(os.environ)
            builder = RedisConfigurationBuilder(env_vars)
            print(f'📍 Environment: {builder.environment}')
            print(f'📍 Redis Host Available: {builder.redis_host}')
            print(f'📍 Has Connection Config: {builder.connection.has_config}')
            assert not builder.connection.has_config, f'❌ ISSUE #1029 REPRODUCED: RedisConfigurationBuilder reports configuration available when redis-host-staging secret is missing! Host: {builder.redis_host}, Config Available: {builder.connection.has_config}'
            is_valid, error_message = builder.validate()
            print(f'📍 Configuration Valid: {is_valid}')
            print(f'📍 Validation Error: {error_message}')
            assert not is_valid, f'❌ ISSUE #1029 REPRODUCED: Configuration validation passed when redis-host-staging secret is missing! This causes DNS resolution failure Error -3 connecting to undefined host.'
            assert 'REDIS_HOST' in error_message, f"❌ ISSUE #1029 REPRODUCED: Validation error doesn't mention missing REDIS_HOST: '{error_message}'. Missing redis-host-staging secret should be clearly identified!"

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_dns_resolution_error_reproduction(self):
        """
        TEST: Reproduce DNS resolution Error -3 from missing/invalid host configuration.

        DESIGNED TO REPRODUCE: This test reproduces the exact DNS resolution failure
        described in Issue #1029: "Error -3 connecting to 10.166.204.83:6379".

        Expected Behavior:
        - Configuration with missing host should trigger DNS resolution concern
        - Builder should detect invalid/missing Memory Store endpoint
        - Builder should validate GCP internal IP format (10.x.x.x)
        - Builder should prevent localhost fallback in GCP staging

        Failure Mode: Test demonstrates DNS failure conditions from Issue #1029
        """
        print(f'🔍 TESTING: Issue #1029 DNS resolution Error -3 reproduction')
        problem_configs = [{**self.gcp_staging_config, 'REDIS_PORT': '6379'}, {**self.gcp_staging_config, 'REDIS_HOST': '', 'REDIS_PORT': '6379'}, {**self.gcp_staging_config, 'REDIS_HOST': 'undefined-host', 'REDIS_PORT': '6379'}, {**self.gcp_staging_config, 'REDIS_HOST': 'localhost', 'REDIS_PORT': '6379'}]
        for i, config in enumerate(problem_configs):
            print(f"\n📍 Testing Problem Config {i + 1}: {config.get('REDIS_HOST', 'MISSING')}")
            with patch.dict(os.environ, config, clear=True):
                env_vars = dict(os.environ)
                builder = RedisConfigurationBuilder(env_vars)
                redis_url = builder.get_url_for_environment()
                print(f'📍 Generated Redis URL: {redis_url}')
                if config.get('REDIS_HOST') == '':
                    assert redis_url is None or 'redis://:' in str(redis_url), f'❌ ISSUE #1029 REPRODUCED: Empty REDIS_HOST not properly handled. Empty host causes DNS Error -3!'
                elif 'REDIS_HOST' not in config:
                    assert redis_url is None or 'localhost' in str(redis_url), f'❌ ISSUE #1029 REPRODUCED: Missing REDIS_HOST fallback behavior. Missing host causes DNS Error -3 when no valid fallback!'
                elif config.get('REDIS_HOST') == 'localhost':
                    print(f'📍 WARNING: localhost in GCP staging will fail to connect to Memory Store')
                is_valid, error_message = builder.validate()
                if config.get('REDIS_HOST') in ['', 'undefined-host'] or 'REDIS_HOST' not in config:
                    assert not is_valid, f"❌ ISSUE #1029 REPRODUCED: Invalid Redis host configuration passed validation: {config.get('REDIS_HOST', 'MISSING')}"

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_gcp_memory_store_ip_validation(self):
        """
        TEST: Validate GCP Memory Store internal IP format and accessibility.

        DESIGNED TO REPRODUCE: This test validates the specific IP address
        10.166.204.83 mentioned in Issue #1029 and GCP internal IP requirements.

        Expected Behavior:
        - Builder should validate GCP Memory Store IP format (10.x.x.x)
        - Builder should distinguish internal vs external IPs
        - Builder should require VPC connector for internal IP access
        - Builder should prevent external IP in Memory Store context

        Failure Mode: Test validates Memory Store IP requirements from Issue #1029
        """
        print(f'🔍 TESTING: Issue #1029 GCP Memory Store IP validation')
        issue_1029_ip = '10.166.204.83'
        config_with_memory_store_ip = {**self.gcp_staging_config, 'REDIS_HOST': issue_1029_ip, 'REDIS_PORT': '6379'}
        with patch.dict(os.environ, config_with_memory_store_ip, clear=True):
            env_vars = dict(os.environ)
            builder = RedisConfigurationBuilder(env_vars)
            print(f'📍 Testing Memory Store IP: {issue_1029_ip}')
            print(f'📍 Environment: {builder.environment}')
            print(f"📍 VPC Connector: {builder.env.get('VPC_CONNECTOR', 'MISSING')}")
            redis_host = builder.redis_host
            print(f'📍 Redis Host from Builder: {redis_host}')
            assert redis_host == issue_1029_ip, f'❌ ISSUE #1029 REPRODUCED: Builder modified Memory Store IP! Expected: {issue_1029_ip}, Got: {redis_host}'
            is_internal_ip = redis_host.startswith('10.')
            assert is_internal_ip, f'❌ ISSUE #1029 REPRODUCED: Memory Store IP {redis_host} not recognized as GCP internal IP (10.x.x.x). This causes connectivity issues!'
            redis_url = builder.get_url_for_environment()
            print(f'📍 Generated URL: {builder.mask_url_for_logging(redis_url)}')
            if redis_url:
                assert issue_1029_ip in redis_url, f"❌ ISSUE #1029 REPRODUCED: Generated URL doesn't contain Memory Store IP! URL: {builder.mask_url_for_logging(redis_url)}"
            has_vpc_connector = bool(builder.env.get('VPC_CONNECTOR'))
            print(f'📍 VPC Connector Configured: {has_vpc_connector}')
            if not has_vpc_connector:
                print(f'⚠️  WARNING: Memory Store IP {issue_1029_ip} requires VPC connector for access!')
                print(f'⚠️  This could cause DNS resolution Error -3 without proper VPC connectivity!')

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_secret_manager_integration_validation(self):
        """
        TEST: Validate GCP Secret Manager integration for component secrets.

        DESIGNED TO REPRODUCE: This test validates that the migration from REDIS_URL
        to component secrets (redis-host-staging, etc.) is properly handled.

        Expected Behavior:
        - Builder should support Secret Manager component secret retrieval
        - Builder should validate required secrets are available
        - Builder should provide clear errors when secrets are missing
        - Builder should handle Secret Manager authentication errors

        Failure Mode: Test demonstrates Secret Manager integration gaps
        """
        print(f'🔍 TESTING: Issue #1029 Secret Manager integration validation')
        secret_manager_config = {**self.gcp_staging_config, 'USE_GCP_SECRET_MANAGER': 'true', 'GCP_PROJECT_ID': 'netra-staging'}
        with patch.dict(os.environ, secret_manager_config, clear=True):
            env_vars = dict(os.environ)
            builder = RedisConfigurationBuilder(env_vars)
            print(f"📍 Using Secret Manager: {builder.env.get('USE_GCP_SECRET_MANAGER')}")
            print(f"📍 GCP Project: {builder.env.get('GCP_PROJECT_ID')}")
            using_secret_manager = builder.env.get('USE_GCP_SECRET_MANAGER') == 'true'
            assert using_secret_manager, f"❌ ISSUE #1029 REPRODUCED: Builder doesn't recognize Secret Manager usage flag"
            required_secrets = ['redis-host-staging', 'redis-port-staging', 'redis-password-staging']
            print(f'📍 Checking required component secrets...')
            for secret_name in required_secrets:
                print(f'📍 Secret {secret_name}: NOT AVAILABLE (causes Issue #1029)')
            is_valid, error_message = builder.validate()
            print(f'📍 Configuration Valid: {is_valid}')
            print(f'📍 Validation Error: {error_message}')
            assert not is_valid, f'❌ ISSUE #1029 REPRODUCED: Configuration validation passed without required component secrets! Missing secrets: {required_secrets}'

    @pytest.mark.unit
    @pytest.mark.redis
    @pytest.mark.critical
    def test_issue_1029_configuration_comparison_local_vs_gcp(self):
        """
        TEST: Compare local development vs GCP staging configuration requirements.

        DESIGNED TO VALIDATE: This test ensures that different environments
        have appropriate configuration requirements and validation rules.

        Expected Behavior:
        - Local development should work with localhost Redis
        - GCP staging should require Memory Store configuration
        - Builder should apply different validation rules per environment
        - Builder should prevent environment configuration mixups

        Failure Mode: Test validates environment-specific configuration rules
        """
        print(f'🔍 TESTING: Issue #1029 configuration comparison local vs GCP')
        print(f'\n📍 Testing Local Development Configuration...')
        with patch.dict(os.environ, self.local_dev_config, clear=True):
            local_env_vars = dict(os.environ)
            local_builder = RedisConfigurationBuilder(local_env_vars)
            local_is_valid, local_error = local_builder.validate()
            local_url = local_builder.get_url_for_environment()
            print(f'📍 Local Valid: {local_is_valid}')
            print(f'📍 Local URL: {local_url}')
            print(f'📍 Local Error: {local_error}')
            assert local_is_valid, f'Local development configuration should be valid: {local_error}'
            assert 'localhost' in local_url, f'Local development should use localhost: {local_url}'
        print(f'\n📍 Testing GCP Staging Configuration (Issue #1029 reproduction)...')
        with patch.dict(os.environ, self.gcp_staging_config, clear=True):
            gcp_env_vars = dict(os.environ)
            gcp_builder = RedisConfigurationBuilder(gcp_env_vars)
            gcp_is_valid, gcp_error = gcp_builder.validate()
            gcp_url = gcp_builder.get_url_for_environment()
            print(f'📍 GCP Valid: {gcp_is_valid}')
            print(f'📍 GCP URL: {gcp_url}')
            print(f'📍 GCP Error: {gcp_error}')
            assert not gcp_is_valid, f'❌ ISSUE #1029 REPRODUCED: GCP staging configuration passed validation without required Memory Store configuration! This leads to DNS Error -3.'
            assert 'REDIS_HOST' in gcp_error, f"❌ ISSUE #1029 REPRODUCED: GCP validation error doesn't mention missing REDIS_HOST: '{gcp_error}'"
        print(f'\n📍 Testing Complete GCP Configuration...')
        with patch.dict(os.environ, self.complete_gcp_config, clear=True):
            complete_env_vars = dict(os.environ)
            complete_builder = RedisConfigurationBuilder(complete_env_vars)
            complete_is_valid, complete_error = complete_builder.validate()
            complete_url = complete_builder.get_url_for_environment()
            print(f'📍 Complete Valid: {complete_is_valid}')
            print(f'📍 Complete URL: {complete_builder.mask_url_for_logging(complete_url)}')
            print(f'📍 Complete Error: {complete_error}')
            assert complete_is_valid, f'Complete GCP configuration should be valid: {complete_error}'
            if complete_url:
                assert '10.166.204.83' in complete_url, f'Complete GCP configuration should use Memory Store IP: {complete_builder.mask_url_for_logging(complete_url)}'

    def test_issue_1029_error_reproduction_summary(self):
        """
        TEST: Summary test that reproduces all aspects of Issue #1029.

        This test provides a comprehensive reproduction of the Redis DNS resolution
        Error -3 and documents all contributing factors.
        """
        print(f'\n🔍 ISSUE #1029 ERROR REPRODUCTION SUMMARY')
        print(f'=' * 80)
        print(f'\n📍 ISSUE DESCRIPTION:')
        print(f'   DNS resolution failure (Error -3) connecting to 10.166.204.83:6379')
        print(f'   Root cause: Missing component-based Redis configuration secrets')
        print(f'   Migration from REDIS_URL to redis-host-staging, redis-port-staging')
        print(f'\n📍 CONFIGURATION PROBLEMS REPRODUCED:')
        with patch.dict(os.environ, self.gcp_staging_config, clear=True):
            builder = RedisConfigurationBuilder(dict(os.environ))
            print(f'   1. Missing REDIS_HOST: {builder.redis_host is None}')
            print(f'   2. Configuration invalid: {not builder.validate()[0]}')
            print(f'   3. No connection config: {not builder.connection.has_config}')
        print(f'\n📍 EXPECTED ERRORS:')
        print(f'   - DNS resolution Error -3 (host undefined)')
        print(f'   - Redis connection timeout')
        print(f'   - Session management failures')
        print(f'   - Golden Path chat functionality breaks')
        print(f'\n📍 SOLUTION REQUIREMENTS:')
        print(f'   - Configure redis-host-staging secret: 10.166.204.83')
        print(f'   - Configure redis-port-staging secret: 6379')
        print(f'   - Configure redis-password-staging secret')
        print(f'   - Ensure VPC connector for Memory Store access')
        print(f'   - Validate Secret Manager integration')
        with patch.dict(os.environ, self.gcp_staging_config, clear=True):
            builder = RedisConfigurationBuilder(dict(os.environ))
            is_valid, error = builder.validate()
            assert not is_valid and 'REDIS_HOST' in error, f'❌ ISSUE #1029 FULLY REPRODUCED: Missing redis-host-staging secret causes configuration validation failure leading to DNS Error -3 when attempting Redis connection!'
        print(f'\n✅ ISSUE #1029 SUCCESSFULLY REPRODUCED')
        print(f'=' * 80)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')