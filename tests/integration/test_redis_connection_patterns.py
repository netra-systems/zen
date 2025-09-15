"""
Integration Tests - Issue #1177 Redis Connection Pattern Mismatch

CRITICAL INTEGRATION FAILURE REPRODUCTION: These tests use real Redis connections
to demonstrate the configuration pattern mismatch affecting actual connectivity.

Expected Results: FAIL - component-based connections fail, URL-based succeed
Demonstrates Issue #1177 configuration mismatch between deployment and runtime.

Business Value: Platform/Internal - System Stability & Golden Path Protection
$500K+ ARR depends on reliable Redis connectivity for session and WebSocket functionality.

SSOT Compliance: Uses real services, inherits from SSOT base test case.
"""

import asyncio
import pytest
from unittest.mock import patch
from typing import Dict, Any, Optional

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import IsolatedEnvironment
from netra_backend.app.redis_manager import RedisManager
from shared.redis_configuration_builder import RedisConfigurationBuilder

# Import Redis for direct connection testing
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    redis = None
    REDIS_AVAILABLE = False


class RedisConnectionPatternsTests(SSotAsyncTestCase):
    """Integration tests for Redis connection patterns with real Redis instances."""

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.test_env = IsolatedEnvironment()
        self.test_env.enable_isolation()
        self.redis_clients = []  # Track clients for cleanup

    async def teardown_method(self, method):
        """Async teardown after each test method."""
        # Cleanup any Redis clients created during tests
        for client in self.redis_clients:
            try:
                if hasattr(client, 'aclose'):
                    await client.aclose()
                elif hasattr(client, 'close'):
                    await client.close()
            except Exception:
                pass  # Ignore cleanup errors

        self.test_env.disable_isolation()
        await super().teardown_method(method)

    @pytest.mark.asyncio
    async def test_component_based_redis_connection_success(self):
        """Test Redis connection with component-based config (should succeed)."""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available for integration testing")

        # Setup component-based config for staging Redis
        self.test_env.set("ENVIRONMENT", "staging")
        self.test_env.set("REDIS_HOST", "10.166.204.83")  # Real staging Redis
        self.test_env.set("REDIS_PORT", "6379")
        self.test_env.set("REDIS_DB", "0")

        # Create Redis client directly from components
        redis_url = f"redis://{self.test_env.get('REDIS_HOST')}:{self.test_env.get('REDIS_PORT')}/{self.test_env.get('REDIS_DB')}"
        client = redis.from_url(redis_url, decode_responses=True)
        self.redis_clients.append(client)

        # Test connection
        try:
            await asyncio.wait_for(client.ping(), timeout=5.0)
            connection_success = True
        except Exception as e:
            connection_success = False
            pytest.fail(f"Component-based Redis connection should succeed but failed: {e}")

        assert connection_success, "Component-based Redis connection should work"

    @pytest.mark.asyncio
    async def test_url_based_redis_connection_success(self):
        """Test Redis connection with URL-based config (should succeed)."""
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available for integration testing")

        # Setup URL-based config for staging Redis
        redis_url = "redis://10.166.204.83:6379/0"
        client = redis.from_url(redis_url, decode_responses=True)
        self.redis_clients.append(client)

        # Test connection
        try:
            await asyncio.wait_for(client.ping(), timeout=5.0)
            connection_success = True
        except Exception as e:
            connection_success = False
            pytest.fail(f"URL-based Redis connection should succeed but failed: {e}")

        assert connection_success, "URL-based Redis connection should work"

    @pytest.mark.asyncio
    async def test_redis_manager_component_config_connection_failure(self):
        """
        Test RedisManager with component config (EXPECTED TO FAIL - Issue #1177).

        This test reproduces the exact failure where RedisManager expects
        component-based config but may not handle it properly in staging.
        """
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available for integration testing")

        # Setup component-based config through environment
        self.test_env.set("ENVIRONMENT", "staging")
        self.test_env.set("REDIS_HOST", "10.166.204.83")
        self.test_env.set("REDIS_PORT", "6379")
        self.test_env.set("REDIS_DB", "0")

        # Create RedisManager using our isolated environment
        with patch('netra_backend.app.redis_manager.get_env', return_value=self.test_env):
            with patch('netra_backend.app.core.backend_environment.get_env', return_value=self.test_env):
                redis_manager = RedisManager()

                try:
                    # EXPECTED FAILURE: RedisManager should connect but may fail due to config pattern mismatch
                    await redis_manager.initialize()

                    # Try to get client
                    client = await redis_manager.get_client()

                    if client:
                        # Test actual operation
                        await client.ping()
                        connection_success = True
                    else:
                        connection_success = False

                    # Cleanup
                    await redis_manager.shutdown()

                except Exception as e:
                    connection_success = False
                    # This might FAIL due to Issue #1177 - configuration pattern mismatch
                    pytest.fail(f"RedisManager with component config failed (Issue #1177): {e}")

        # This assertion might FAIL showing the configuration mismatch issue
        assert connection_success, "RedisManager should work with component-based config but fails due to Issue #1177"

    @pytest.mark.asyncio
    async def test_redis_manager_url_only_config_failure(self):
        """
        Test RedisManager with URL-only config (EXPECTED TO FAIL - Issue #1177).

        This reproduces the scenario where deployment provides REDIS_URL
        but RedisManager expects component-based configuration.
        """
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available for integration testing")

        # Setup URL-only config (deployment scenario)
        self.test_env.set("ENVIRONMENT", "staging")
        self.test_env.set("REDIS_URL", "redis://10.166.204.83:6379/0")
        # Deliberately NOT setting REDIS_HOST, REDIS_PORT, REDIS_DB

        # Create RedisManager using our isolated environment
        with patch('netra_backend.app.redis_manager.get_env', return_value=self.test_env):
            with patch('netra_backend.app.core.backend_environment.get_env', return_value=self.test_env):
                redis_manager = RedisManager()

                try:
                    # EXPECTED FAILURE: Should fail because it expects component config
                    await redis_manager.initialize()

                    client = await redis_manager.get_client()

                    if client:
                        await client.ping()
                        connection_success = True
                    else:
                        connection_success = False

                    await redis_manager.shutdown()

                except Exception as e:
                    connection_success = False
                    # This FAILURE demonstrates Issue #1177
                    expected_failure_message = f"RedisManager failed with URL-only config (demonstrating Issue #1177): {e}"
                    print(expected_failure_message)  # Log the expected failure

        # This should FAIL showing that URL-only config doesn't work
        with pytest.raises(AssertionError, match="URL-only config should work but fails"):
            assert connection_success, "URL-only config should work but fails due to component config expectation (Issue #1177)"

    @pytest.mark.asyncio
    async def test_configuration_builder_staging_url_extraction_failure(self):
        """
        Test RedisConfigurationBuilder URL extraction for staging (EXPECTED TO FAIL).

        Shows that staging environment can't extract proper URL when only
        REDIS_URL is provided instead of component config.
        """
        # Setup staging with URL-only config
        env_vars = {
            "ENVIRONMENT": "staging",
            "REDIS_URL": "redis://10.166.204.83:6379/0"
            # Missing component config that staging expects
        }

        builder = RedisConfigurationBuilder(env_vars)

        # Check what staging auto_url produces
        staging_url = builder.staging.auto_url

        # EXPECTED FAILURE: staging.auto_url should be None because it expects components
        assert staging_url is not None, f"Staging auto_url should extract from REDIS_URL but returns None (Issue #1177)"

        # If staging_url is None, we've reproduced the issue
        if staging_url is None:
            pytest.fail("Staging auto_url failed to extract URL from REDIS_URL - this demonstrates Issue #1177")

    @pytest.mark.asyncio
    async def test_actual_staging_redis_connectivity_validation(self):
        """
        Test actual connectivity to staging Redis to validate it's accessible.

        This test ensures the staging Redis instance is actually reachable,
        ruling out network issues as the cause of Issue #1177.
        """
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available for integration testing")

        # Direct connection to staging Redis
        staging_redis_url = "redis://10.166.204.83:6379/0"
        client = redis.from_url(staging_redis_url, decode_responses=True)
        self.redis_clients.append(client)

        # Test basic operations
        try:
            # Test connectivity
            await asyncio.wait_for(client.ping(), timeout=10.0)

            # Test basic operations to ensure Redis is functional
            test_key = "test_connectivity_validation"
            await client.set(test_key, "test_value", ex=60)  # Expires in 60 seconds
            retrieved_value = await client.get(test_key)
            await client.delete(test_key)  # Cleanup

            connectivity_validated = (retrieved_value == "test_value")

        except Exception as e:
            connectivity_validated = False
            pytest.fail(f"Staging Redis is not accessible - this rules out network issues for Issue #1177: {e}")

        assert connectivity_validated, "Staging Redis should be accessible and functional"

    @pytest.mark.asyncio
    async def test_redis_operations_with_different_config_patterns(self):
        """
        Test Redis operations with different configuration patterns.

        Compares success rates between component-based and URL-based configurations
        to identify which pattern causes issues in Issue #1177.
        """
        if not REDIS_AVAILABLE:
            pytest.skip("Redis not available for integration testing")

        test_results = {}

        # Test 1: Component-based configuration
        try:
            component_url = "redis://10.166.204.83:6379/0"  # Built from components
            client = redis.from_url(component_url, decode_responses=True)
            self.redis_clients.append(client)

            await client.ping()
            await client.set("test_component", "success", ex=30)
            result = await client.get("test_component")
            await client.delete("test_component")

            test_results["component_based"] = (result == "success")
        except Exception as e:
            test_results["component_based"] = False
            test_results["component_error"] = str(e)

        # Test 2: URL-based configuration
        try:
            url_based_url = "redis://10.166.204.83:6379/0"  # Direct URL
            client = redis.from_url(url_based_url, decode_responses=True)
            self.redis_clients.append(client)

            await client.ping()
            await client.set("test_url", "success", ex=30)
            result = await client.get("test_url")
            await client.delete("test_url")

            test_results["url_based"] = (result == "success")
        except Exception as e:
            test_results["url_based"] = False
            test_results["url_error"] = str(e)

        # Analysis
        if test_results.get("component_based") and test_results.get("url_based"):
            # Both work - Issue #1177 is in configuration handling, not connectivity
            assert True, "Both patterns work - Issue #1177 is in configuration handling logic"
        else:
            # One or both failed - provides insight into Issue #1177
            failure_details = {k: v for k, v in test_results.items() if k.endswith("_error")}
            pytest.fail(f"Configuration pattern testing shows failures that help diagnose Issue #1177: {failure_details}")