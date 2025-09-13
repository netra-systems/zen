from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

"""

Test Harness Integration Test

Tests the unified test harness service startup functionality.



This test verifies that our fixed service startup sequence works correctly:

1. Environment setup

2. Database initialization 

3. Auth service startup

4. Backend service startup

5. Health check verification

"""



import asyncio

from typing import Any, Dict



import pytest



from tests.e2e.config import setup_test_environment

from tests.e2e.harness_utils import (

    TestHarnessContext,

    UnifiedTestHarnessComplete,

    create_test_harness,

)





@pytest.mark.e2e

class TestUnifiedHarness:

    """Test the unified test harness functionality."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_harness_service_startup_sequence(self):

        """Test complete service startup sequence."""

        # Setup test environment first

        setup_test_environment()

        

        # Create harness instance

        harness = UnifiedTestHarnessComplete("test_startup")

        

        try:

            # Test startup sequence

            await harness.start_services()

            

            # Verify all services are ready

            assert harness.state.ready, "Harness should be ready after startup"

            

            # Check service states

            auth_service = harness.state.services.get("auth_service")

            backend_service = harness.state.services.get("backend")

            

            assert auth_service is not None, "Auth service should be configured"

            assert backend_service is not None, "Backend service should be configured"

            assert auth_service.ready, "Auth service should be ready"

            assert backend_service.ready, "Backend service should be ready"

            

            # Test system health check

            health = await harness.check_system_health()

            assert health["services_ready"], f"All services should be ready: {health}"

            assert health["ready_services"] == health["service_count"], "All services should be healthy"

            

        finally:

            # Always cleanup

            await harness.stop_all_services()

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_harness_context_manager(self):

        """Test harness context manager functionality."""

        # Setup test environment

        setup_test_environment()

        

        async with TestHarnessContext("test_context") as harness:

            # Verify harness is ready

            assert harness.state.ready, "Harness should be ready in context"

            

            # Test basic functionality

            health = await harness.check_system_health()

            assert health["services_ready"], "Services should be ready in context"

            

            # Test auth token generation

            token = await harness.get_auth_token(0)

            assert token is not None, "Should be able to generate auth token"

            assert token.startswith("test-token-"), "Token should have expected format"

        

        # Context manager should have cleaned up

        # Note: We can't easily test cleanup state without accessing internals

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_service_dependency_order(self):

        """Test that services start in correct dependency order."""

        setup_test_environment()

        

        harness = UnifiedTestHarnessComplete("test_dependencies")

        

        try:

            # Start services one by one to test ordering

            await harness._setup_test_environment()

            await harness._setup_databases()

            

            # Start auth service first

            await harness._start_auth_service()

            auth_service = harness.state.services["auth_service"]

            assert auth_service.ready, "Auth service should be ready before backend"

            

            # Start backend service (depends on auth)

            await harness._start_backend_service()

            backend_service = harness.state.services["backend"]

            assert backend_service.ready, "Backend service should be ready after auth"

            

            # Verify both are healthy

            await harness._verify_system_health()

            

        finally:

            await harness.stop_all_services()

    

    @pytest.mark.asyncio 

    @pytest.mark.e2e

    async def test_database_configuration(self):

        """Test that database configuration is correct for testing."""

        setup_test_environment()

        

        harness = UnifiedTestHarnessComplete("test_db_config")

        

        try:

            # Setup databases

            await harness._setup_databases()

            

            # Check database manager initialization

            assert harness.database_manager.initialized, "Database manager should be initialized"

            

            # Verify test database URLs are set correctly

            import os

            assert "localhost" in redis_url, f"Redis should use localhost: {redis_url}"

            

        finally:

            await harness.database_manager.cleanup_databases()





@pytest.mark.real_e2e

@pytest.mark.e2e

class TestRealServiceIntegration:

    """Test with real service processes (marked for real_e2e tests)."""

    

    @pytest.mark.asyncio

    @pytest.mark.e2e

    async def test_real_service_health_checks(self):

        """Test health checks with real service processes."""

        setup_test_environment()

        

        # This test will actually start real services

        async with TestHarnessContext("real_service_test", seed_data=False) as harness:

            # Test auth service health

            auth_health = await harness.service_manager._real_manager._check_service_health(

                harness.state.services["auth_service"]

            )

            assert auth_health, "Auth service should be healthy"

            

            # Test backend service health  

            backend_health = await harness.service_manager._real_manager._check_service_health(

                harness.state.services["backend"]

            )

            assert backend_health, "Backend service should be healthy"

            

            # Test comprehensive health check

            system_health = await harness.check_system_health()

            assert system_health["services_ready"], f"System should be healthy: {system_health}"

            

            # Verify service details

            service_details = system_health["service_details"]

            assert "auth_service" in service_details, "Auth service should be in health details"

            assert "backend" in service_details, "Backend service should be in health details"

            

            for service_name, details in service_details.items():

                assert details["ready"], f"{service_name} should be ready in details"

                assert details["port"] > 0, f"{service_name} should have valid port"





if __name__ == "__main__":

    # Run basic test manually for debugging

    asyncio.run(TestUnifiedHarness().test_harness_service_startup_sequence())

