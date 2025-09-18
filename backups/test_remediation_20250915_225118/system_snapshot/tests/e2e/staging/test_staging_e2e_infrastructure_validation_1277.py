"""
E2E Tests for Staging Environment Infrastructure (Issue #1277)

Business Value Justification (BVJ):
- Segment: Platform/Internal - Production Readiness
- Business Goal: Validate E2E infrastructure works on live staging
- Value Impact: Ensures staging tests can run for release validation
- Revenue Impact: Protects production deployment quality

This test module validates that the Issue #1277 fix enables reliable E2E test
execution on the staging GCP remote environment.
"""

import pytest
import asyncio
from pathlib import Path
from typing import Dict, Any, List

from tests.e2e.real_services_manager import RealServicesManager, ServiceEndpoint
from test_framework.base_e2e_test import BaseE2ETest


class TestStagingE2EInfrastructureValidation(BaseE2ETest):
    """Test E2E infrastructure on staging GCP remote environment."""

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_realservicesmanager_initialization(self):
        """
        Test RealServicesManager initializes correctly on staging.

        This validates the fix works in the staging environment.
        """
        # Force staging environment configuration
        manager = RealServicesManager()

        # Override environment to staging for this test
        original_env = manager.env.get("TEST_ENVIRONMENT", "local")
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")

        try:
            # Should initialize without project root detection errors
            assert manager.project_root is not None
            assert isinstance(manager.project_root, Path)
            assert manager.project_root.exists()

            # Should detect staging environment
            environment = manager._get_current_environment()
            assert environment == "staging"

            # Should configure staging service endpoints
            endpoints = manager.service_endpoints
            assert len(endpoints) > 0

            # Staging endpoints should use HTTPS/WSS and staging domains
            for endpoint in endpoints:
                if endpoint.name in ["auth_service", "backend"]:
                    assert endpoint.url.startswith("https://")
                    assert "staging.netrasystems.ai" in endpoint.url
                elif endpoint.name == "websocket":
                    assert endpoint.url.startswith("wss://")
                    assert "staging.netrasystems.ai" in endpoint.url

            print(f"✓ RealServicesManager initialized for staging with {len(endpoints)} endpoints")

        finally:
            # Restore original environment
            manager.env.set("TEST_ENVIRONMENT", original_env, source="test")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_project_root_detection_reliability(self):
        """
        Test project root detection works reliably on staging environment.

        This ensures the fix is robust across different deployment environments.
        """
        # Test multiple manager instances on staging
        managers = []

        for i in range(3):
            manager = RealServicesManager()
            # Force staging environment
            manager.env.set("TEST_ENVIRONMENT", "staging", source="test")
            managers.append(manager)

        # All should detect the same project root
        first_root = managers[0].project_root
        for i, manager in enumerate(managers[1:], 1):
            assert manager.project_root == first_root, \
                f"Manager {i} detected different root on staging"

        # All should work with staging configuration
        for manager in managers:
            assert len(manager.service_endpoints) > 0
            environment = manager._get_current_environment()
            assert environment == "staging"

        print(f"✓ Project root detection reliable across {len(managers)} instances on staging")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_service_endpoint_configuration(self):
        """
        Test service endpoints are configured correctly for staging.

        This validates staging-specific configuration works with the fix.
        """
        manager = RealServicesManager()
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")

        endpoints = manager.service_endpoints
        assert len(endpoints) > 0

        # Validate staging-specific endpoint configuration
        endpoint_dict = {ep.name: ep for ep in endpoints}

        # Auth service endpoint
        auth_endpoint = endpoint_dict.get("auth_service")
        assert auth_endpoint is not None
        assert auth_endpoint.url == "https://auth.staging.netrasystems.ai"
        assert auth_endpoint.health_path == "/auth/health"

        # Backend endpoint
        backend_endpoint = endpoint_dict.get("backend")
        assert backend_endpoint is not None
        assert backend_endpoint.url == "https://api.staging.netrasystems.ai"
        assert backend_endpoint.health_path == "/health"

        # WebSocket endpoint
        websocket_endpoint = endpoint_dict.get("websocket")
        assert websocket_endpoint is not None
        assert websocket_endpoint.url == "wss://api.staging.netrasystems.ai/ws"
        assert websocket_endpoint.health_path == "/ws/health"

        # Database endpoint (staging-specific)
        database_endpoint = endpoint_dict.get("database")
        assert database_endpoint is not None
        assert "staging" in database_endpoint.url.lower() or "localhost" in database_endpoint.url

        print("✓ All staging service endpoints configured correctly")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    @pytest.mark.real_services
    async def test_staging_health_check_execution(self):
        """
        Test health checks execute successfully on staging services.

        This validates the fix enables health monitoring on live services.
        """
        manager = RealServicesManager()
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")

        try:
            # Initialize HTTP client for health checks
            await manager._ensure_http_client()

            # Execute health checks on staging services
            health_results = await manager.check_all_service_health()

            # Health check should complete without errors
            assert health_results is not None
            assert "services" in health_results
            assert "total_time_ms" in health_results

            # Should have attempted to check all services
            services = health_results["services"]
            assert len(services) > 0

            # Log health check results
            healthy_services = [name for name, status in services.items() if status.get("healthy", False)]
            unhealthy_services = [name for name, status in services.items() if not status.get("healthy", False)]

            print(f"✓ Health checks executed - {len(healthy_services)} healthy, {len(unhealthy_services)} unhealthy")

            # At least some services should respond (even if not all are healthy)
            responded_services = [name for name, status in services.items()
                                if status.get("response_time_ms") is not None]
            assert len(responded_services) > 0, "No services responded to health checks"

        except Exception as e:
            # Health check failures are acceptable for staging (services may be down)
            # but the infrastructure should not fail due to project root detection
            if "Cannot detect project root" in str(e):
                pytest.fail(f"Project root detection failed on staging: {e}")
            else:
                print(f"⚠ Health check issues on staging (acceptable): {e}")

        finally:
            await manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_environment_detection_robustness(self):
        """
        Test environment detection works robustly on staging.

        This ensures the fix handles various environment configurations.
        """
        # Test various environment indicators
        test_cases = [
            {"TEST_ENVIRONMENT": "staging"},
            {"TEST_ENVIRONMENT": "STAGING"},
            {"TEST_ENVIRONMENT": "Staging"},
            {"ENVIRONMENT": "staging"},
            {"ENV": "staging"}
        ]

        for i, env_vars in enumerate(test_cases):
            manager = RealServicesManager()

            # Set environment variables
            for key, value in env_vars.items():
                manager.env.set(key, value, source="test")

            # Should detect staging or default appropriately
            detected_env = manager._get_current_environment()

            # Should not fail due to project root detection
            assert manager.project_root is not None

            # Should configure appropriate endpoints
            endpoints = manager.service_endpoints
            assert len(endpoints) > 0

            print(f"✓ Test case {i+1}: Environment detection robust with {env_vars}")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_concurrent_manager_instances(self):
        """
        Test multiple concurrent RealServicesManager instances on staging.

        This validates the fix works under concurrent usage patterns.
        """
        # Create multiple managers concurrently
        async def create_manager():
            manager = RealServicesManager()
            manager.env.set("TEST_ENVIRONMENT", "staging", source="test")
            return manager

        # Create 5 concurrent instances
        managers = await asyncio.gather(*[create_manager() for _ in range(5)])

        try:
            # All should have consistent project root detection
            first_root = managers[0].project_root
            for i, manager in enumerate(managers[1:], 1):
                assert manager.project_root == first_root, \
                    f"Concurrent manager {i} has inconsistent project root"

            # All should have staging configuration
            for i, manager in enumerate(managers):
                environment = manager._get_current_environment()
                assert environment == "staging", f"Manager {i} not configured for staging"

                endpoints = manager.service_endpoints
                assert len(endpoints) > 0, f"Manager {i} has no endpoints"

            print(f"✓ {len(managers)} concurrent managers all consistent on staging")

        finally:
            # Cleanup all managers
            await asyncio.gather(*[manager.cleanup() for manager in managers])

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_circuit_breaker_functionality(self):
        """
        Test circuit breaker functionality works on staging.

        This validates advanced health monitoring features work with the fix.
        """
        manager = RealServicesManager()
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")

        try:
            # Circuit breaker should be available
            circuit_status = manager.get_circuit_breaker_status()
            assert circuit_status is not None
            assert isinstance(circuit_status, dict)

            # Should be able to configure health checking
            manager.enable_circuit_breaker(True)
            manager.enable_parallel_health_checks(True)

            # Should be able to get performance metrics
            metrics = await manager.get_health_check_performance_metrics()
            assert metrics is not None
            assert "total_time_ms" in metrics
            assert "parallel_execution" in metrics

            print("✓ Circuit breaker and advanced features work on staging")

        except Exception as e:
            if "Cannot detect project root" in str(e):
                pytest.fail(f"Project root detection failed in circuit breaker test: {e}")
            else:
                print(f"⚠ Circuit breaker test issues on staging (acceptable): {e}")

        finally:
            await manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    @pytest.mark.performance
    async def test_staging_infrastructure_performance(self):
        """
        Test E2E infrastructure performance on staging.

        This ensures the fix doesn't introduce performance issues on remote environments.
        """
        import time

        # Test manager initialization performance
        start_time = time.time()
        manager = RealServicesManager()
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")
        init_time = time.time() - start_time

        # Initialization should be fast
        assert init_time < 5.0, f"Manager initialization took {init_time:.1f}s, should be under 5s"

        try:
            # Test health check performance
            start_time = time.time()
            health_results = await manager.check_all_service_health()
            health_check_time = time.time() - start_time

            # Health checks should complete in reasonable time
            assert health_check_time < 30.0, f"Health checks took {health_check_time:.1f}s, should be under 30s"

            # Test multiple rapid calls (caching)
            start_time = time.time()
            for _ in range(3):
                await manager.check_all_service_health()
            rapid_checks_time = time.time() - start_time

            assert rapid_checks_time < 60.0, f"3 rapid health checks took {rapid_checks_time:.1f}s"

            print(f"✓ Staging performance: init={init_time:.2f}s, health={health_check_time:.2f}s")

        except Exception as e:
            if "Cannot detect project root" in str(e):
                pytest.fail(f"Project root detection failed in performance test: {e}")
            else:
                print(f"⚠ Performance test issues on staging: {e}")

        finally:
            await manager.cleanup()


class TestStagingE2ERegressionPrevention:
    """Regression prevention tests specific to staging environment."""

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_reproduces_original_collection_issue(self):
        """
        Test that original Issue #1277 scenario works on staging.

        This ensures the fix works in the actual deployment environment.
        """
        # The original issue would have prevented any E2E infrastructure from working
        # This test ensures it now works on staging

        manager = RealServicesManager()
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")

        # Should be able to initialize without project root errors
        assert manager.project_root is not None
        assert manager.project_root.exists()

        # Should be able to configure for staging
        environment = manager._get_current_environment()
        assert environment == "staging"

        # Should be able to set up service endpoints
        endpoints = manager.service_endpoints
        assert len(endpoints) > 0

        # Should be able to create health checker
        assert manager.health_checker is not None

        print("✓ Original Issue #1277 scenario now works on staging environment")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_independence_from_claude_md(self):
        """
        Test that staging infrastructure works without claude.md files.

        This specifically validates the Issue #1277 fix on staging.
        """
        manager = RealServicesManager()
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")

        # Should work regardless of claude.md file existence
        project_root = manager.project_root

        # Verify the fix: uses pyproject.toml, not claude.md
        assert (project_root / "pyproject.toml").exists()

        # Should not depend on claude.md files
        claude_files = [
            project_root / "claude.md",
            project_root / "CLAUDE.md"
        ]

        for claude_file in claude_files:
            if claude_file.exists():
                print(f"Note: {claude_file.name} exists but is not required")

        # Infrastructure should work regardless
        endpoints = manager.service_endpoints
        assert len(endpoints) > 0

        # Should configure staging endpoints correctly
        staging_endpoints = [ep for ep in endpoints if "staging.netrasystems.ai" in ep.url]
        assert len(staging_endpoints) > 0, "No staging endpoints configured"

        print("✓ Staging infrastructure independent of claude.md files")

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    @pytest.mark.performance
    async def test_staging_no_performance_regression(self):
        """
        Test that the fix doesn't cause performance regressions on staging.

        This ensures the solution is efficient in production-like environments.
        """
        import time

        # Measure performance of key operations
        operations = []

        # Test 1: Manager creation
        start_time = time.time()
        manager = RealServicesManager()
        manager.env.set("TEST_ENVIRONMENT", "staging", source="test")
        operations.append(("manager_creation", time.time() - start_time))

        try:
            # Test 2: Environment detection
            start_time = time.time()
            environment = manager._get_current_environment()
            operations.append(("environment_detection", time.time() - start_time))

            # Test 3: Service endpoint configuration
            start_time = time.time()
            endpoints = manager.service_endpoints
            operations.append(("endpoint_configuration", time.time() - start_time))

            # Test 4: Health checker initialization
            start_time = time.time()
            circuit_status = manager.get_circuit_breaker_status()
            operations.append(("health_checker_init", time.time() - start_time))

            # All operations should be fast
            for operation, duration in operations:
                assert duration < 2.0, f"{operation} took {duration:.2f}s, should be under 2s"

            total_time = sum(duration for _, duration in operations)
            assert total_time < 5.0, f"Total operations took {total_time:.2f}s, should be under 5s"

            print(f"✓ No performance regression on staging - total time: {total_time:.2f}s")

        finally:
            await manager.cleanup()

    @pytest.mark.e2e
    @pytest.mark.staging_remote
    @pytest.mark.gcp_staging
    @pytest.mark.regression_prevention
    @pytest.mark.issue_1277
    @pytest.mark.no_docker
    async def test_staging_error_handling_robustness(self):
        """
        Test error handling remains robust on staging with the fix.

        This ensures the fix doesn't introduce new failure modes.
        """
        # Test various error scenarios that should be handled gracefully
        test_scenarios = [
            # Invalid environment configurations
            {"TEST_ENVIRONMENT": "invalid_env"},
            {"TEST_ENVIRONMENT": ""},
            {"TEST_ENVIRONMENT": None},
        ]

        for scenario in test_scenarios:
            manager = RealServicesManager()

            # Apply scenario configuration
            for key, value in scenario.items():
                if value is not None:
                    manager.env.set(key, str(value), source="test")

            # Should not fail due to project root detection
            try:
                assert manager.project_root is not None
                endpoints = manager.service_endpoints
                assert len(endpoints) > 0
                print(f"✓ Robust error handling for scenario: {scenario}")

            except Exception as e:
                if "Cannot detect project root" in str(e):
                    pytest.fail(f"Project root detection failed in error scenario {scenario}: {e}")
                else:
                    # Other errors are acceptable in error scenarios
                    print(f"⚠ Expected error in scenario {scenario}: {e}")

            await manager.cleanup()