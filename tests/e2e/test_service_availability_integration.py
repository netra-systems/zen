"""Integration test for the new service availability detection system.



from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

This test demonstrates how to use the service availability detection

in E2E tests to properly handle real vs. mock services.

"""



import pytest

import asyncio

import os



from tests.e2e.service_availability import get_service_availability, ServiceAvailabilityChecker

from tests.e2e.real_service_config import get_real_service_config, ServiceConfigHelper

from tests.e2e.test_environment_config import (

    get_test_environment_config_async,

    should_skip_test_without_real_services,

    should_skip_test_without_real_llm

)





@pytest.mark.e2e

class TestServiceAvailabilityDetection:

    """Test suite for service availability detection."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_service_availability_basic(self):

        """Test basic service availability detection."""

        # Use short timeout for testing

        checker = ServiceAvailabilityChecker(timeout=1.0)

        availability = await checker.check_all_services()

        

        # Should always have these fields

        assert hasattr(availability, 'postgresql')

        assert hasattr(availability, 'redis') 

        assert hasattr(availability, 'clickhouse')

        assert hasattr(availability, 'openai_api')

        assert hasattr(availability, 'anthropic_api')

        

        # Should have boolean availability flags

        assert isinstance(availability.use_real_services, bool)

        assert isinstance(availability.use_real_llm, bool)

        

        # Should have summary

        summary = availability.summary

        assert 'databases' in summary

        assert 'apis' in summary

        assert 'configuration' in summary

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_real_service_config_generation(self):

        """Test real service configuration generation."""

        config = await get_real_service_config()

        

        # Should have database config

        assert config.database is not None

        assert config.database.postgres_url is not None

        assert config.database.redis_url is not None

        

        # Should have LLM config

        assert config.llm is not None

        assert isinstance(config.llm.use_real_llm, bool)

        assert isinstance(config.llm.available_providers, list)

        

        # Should have service availability reference

        assert config.service_availability is not None

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_enhanced_test_environment_config(self):

        """Test enhanced test environment configuration."""

        config = await get_test_environment_config_async()

        

        # Should have enhanced features

        assert hasattr(config, 'service_detection_enabled')

        assert hasattr(config, 'detected_services')

        

        # Should have database configuration

        assert config.database.url is not None

        assert config.database.redis_url is not None

        

        # Service detection should be enabled by default

        assert config.service_detection_enabled is True

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_service_config_helpers(self):

        """Test service configuration helper functions."""

        # These should not raise exceptions

        use_db = await ServiceConfigHelper.should_use_real_databases()

        use_llm = await ServiceConfigHelper.should_use_real_llm()

        

        assert isinstance(use_db, bool)

        assert isinstance(use_llm, bool)

        

        # Test database URL retrieval

        postgres_url = await ServiceConfigHelper.get_database_url("postgres")

        redis_url = await ServiceConfigHelper.get_database_url("redis")

        

        assert postgres_url is not None

        assert redis_url is not None

        

        # Test invalid service

        with pytest.raises(ValueError):

            await ServiceConfigHelper.get_database_url("invalid_service")

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_skip_helpers(self):

        """Test test skip helper functions."""

        # These should return strings (empty if no skip needed)

        skip_services = await should_skip_test_without_real_services()

        skip_llm = await should_skip_test_without_real_llm()

        

        assert isinstance(skip_services, str)

        assert isinstance(skip_llm, str)

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_environment_flag_detection(self):

        """Test environment flag detection."""

        checker = ServiceAvailabilityChecker()

        

        # Test without flags

        assert checker._check_use_real_services_flag() is False

        assert checker._check_use_real_llm_flag() is False

        

        # Test with USE_REAL_SERVICES flag

        with patch.dict(os.environ, {'USE_REAL_SERVICES': 'true'}):

            assert checker._check_use_real_services_flag() is True

        

        # Test with TEST_USE_REAL_LLM flag

        with patch.dict(os.environ, {'TEST_USE_REAL_LLM': 'true'}):

            assert checker._check_use_real_llm_flag() is True

        

        # Test case insensitive

        with patch.dict(os.environ, {'USE_REAL_SERVICES': 'TRUE'}):

            assert checker._check_use_real_services_flag() is True

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_config_caching(self):

        """Test that configuration is cached appropriately."""

        from tests.e2e.real_service_config import RealServiceConfigManager

        

        manager = RealServiceConfigManager()

        

        # First call

        config1 = await manager.get_config()

        

        # Second call should be cached

        config2 = await manager.get_config()

        

        # Should be the same object (cached)

        assert config1 is config2

        

        # Force refresh should create new object

        config3 = await manager.get_config(force_refresh=True)

        assert config3 is not config1





@pytest.mark.e2e

class TestExampleUsagePatterns:

    """Demonstrate usage patterns for the service detection system."""

    

    @pytest.mark.asyncio 

    @pytest.mark.e2e

    async def test_conditional_test_execution(self):

        """Example: Skip test if real services not available."""

        # Pattern 1: Using skip helpers directly

        skip_reason = await should_skip_test_without_real_services("example_test")

        if skip_reason:

            pytest.skip(skip_reason)

        

        # Pattern 2: Using ServiceConfigHelper

        if not await ServiceConfigHelper.should_use_real_databases():

            pytest.skip("Test requires real databases")

        

        # Test would continue here if real services are available

        assert True  # Placeholder test logic

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_dynamic_database_configuration(self):

        """Example: Get appropriate database URLs based on availability."""

        # Get database URLs that work with current environment

        postgres_url = await ServiceConfigHelper.get_database_url("postgres") 

        redis_url = await ServiceConfigHelper.get_database_url("redis")

        

        # URLs should be valid

        assert postgres_url is not None

        assert redis_url is not None

        

        # Would use these URLs to configure test databases

        print(f"Using PostgreSQL: {postgres_url}")

        print(f"Using Redis: {redis_url}")

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_llm_provider_selection(self):

        """Example: Select LLM provider based on availability."""

        provider = await ServiceConfigHelper.get_llm_provider()

        

        if provider:

            print(f"Using LLM provider: {provider}")

            # Would configure LLM client with this provider

        else:

            print("No LLM providers available, using mocks")

            # Would use mock LLM responses

        

        # Test logic continues based on provider availability

        assert True  # Placeholder





# Integration test that can be used to verify the whole system

@pytest.mark.asyncio

@pytest.mark.e2e

async def test_full_integration():

    """Full integration test of the service detection system."""

    print("\

=== Service Detection Integration Test ===")

    

    # Get service availability

    availability = await get_service_availability()

    print(f"Services available: {availability.summary}")

    

    # Get real service config

    config = await get_real_service_config()

    print(f"Configuration: {config.summary}")

    

    # Get enhanced test environment config

    test_config = await get_test_environment_config_async()

    print(f"Test config uses real DB: {test_config.use_real_database}")

    print(f"Test config uses real LLM: {test_config.use_real_llm}")

    

    # Check skip conditions

    skip_services = await should_skip_test_without_real_services()

    skip_llm = await should_skip_test_without_real_llm()

    

    print(f"Would skip without services: {bool(skip_services)}")

    print(f"Would skip without LLM: {bool(skip_llm)}")

    

    print("=== Integration test complete ===\

")





if __name__ == "__main__":

    # Can be run directly for manual testing

    asyncio.run(test_full_integration())

