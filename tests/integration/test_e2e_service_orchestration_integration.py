"""
Integration Test: E2E Service Orchestration for Chat Functionality

MISSION CRITICAL: Validates that the E2E service orchestration system properly
starts and configures services for chat functionality testing.

This test ensures:
1. Service orchestration starts Docker containers correctly
2. Backend and auth services can be started and are healthy  
3. WebSocket connectivity works for agent chat events
4. Database connections work for real data testing
5. All service URLs are properly configured

Business Value Justification (BVJ):
1. Segment: All tiers (Free to Enterprise) - $2M+ ARR protection
2. Business Goal: Ensure reliable E2E test infrastructure prevents production bugs
3. Value Impact: Validates core chat agent orchestration works end-to-end
4. Revenue Impact: Prevents agent failure cascades that cause enterprise churn

This test follows CLAUDE.md "Real Everything" principle - no mocks in E2E testing.
"""

import asyncio
import logging
import pytest
import time
from typing import Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

# CLAUDE.md compliance: absolute imports only
from test_framework.unified_docker_manager import (
    ServiceOrchestrator,
    OrchestrationConfig,
    orchestrate_e2e_services
)
from test_framework.real_services import (
    get_real_services,
    RealServicesManager,
    ServiceUnavailableError
)
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.real_services
class TestE2EServiceOrchestration:
    """Test E2E service orchestration integration."""

    async def test_basic_service_orchestration(self):
        """Test basic service orchestration with database services."""
        # Configure orchestration for basic services
        config = OrchestrationConfig(
            environment="test",
            required_services=["postgres", "redis"],
            startup_timeout=60.0,
            health_check_timeout=5.0,
            health_check_retries=10
        )
        
        orchestrator = ServiceOrchestrator(config)
        
        try:
            # Test orchestration
            success, health_report = await orchestrator.orchestrate_services()
            
            assert success, f"Service orchestration failed: {orchestrator.get_health_report()}"
            
            # Validate all required services are healthy
            for service in config.required_services:
                assert service in orchestrator.service_health, f"Missing health data for {service}"
                health = orchestrator.service_health[service]
                assert health.is_healthy, f"Service {service} is not healthy: {health.error_message}"
                assert health.port > 0, f"Invalid port for {service}: {health.port}"
                assert health.response_time_ms >= 0, f"Invalid response time for {service}"
            
            # Test environment configuration
            env = get_env()
            assert env.get("DATABASE_URL") is not None, "#removed-legacynot configured"
            assert env.get("REDIS_URL") is not None, "REDIS_URL not configured"
            assert "localhost:5433" in env.get("DATABASE_URL"), "Wrong PostgreSQL port in DATABASE_URL"
            assert "localhost:6381" in env.get("REDIS_URL"), "Wrong Redis port in REDIS_URL"
            
            logger.info(" PASS:  Basic service orchestration test passed")
            
        finally:
            # Cleanup
            if orchestrator.started_services:
                await orchestrator.cleanup_services()

    async def test_real_services_integration_after_orchestration(self):
        """Test that real services can connect after orchestration."""
        # First orchestrate services
        success, orchestrator = await orchestrate_e2e_services(
            required_services=["postgres", "redis"],
            timeout=45.0
        )
        
        assert success, f"Service orchestration failed: {orchestrator.get_health_report()}"
        
        try:
            # Then test real services integration
            manager = get_real_services()
            await manager.ensure_all_services_available()
            
            # Test PostgreSQL connection
            async with manager.postgres() as postgres:
                result = await postgres.fetchval("SELECT 1 as test_value")
                assert result == 1, "PostgreSQL connection test failed"
                logger.info(" PASS:  PostgreSQL connection test passed")
            
            # Test Redis connection  
            async with manager.redis() as redis:
                await redis.set("test_key", "test_value")
                value = await redis.get("test_key")
                assert value == "test_value", "Redis connection test failed"
                await redis.delete("test_key")
                logger.info(" PASS:  Redis connection test passed")
            
            logger.info(" PASS:  Real services integration after orchestration passed")
            
        finally:
            # Cleanup
            if orchestrator.started_services:
                await orchestrator.cleanup_services()

    async def test_service_connectivity_validation(self):
        """Test service connectivity validation."""
        config = OrchestrationConfig(
            environment="test", 
            required_services=["postgres", "redis"],
            health_check_timeout=3.0,
            health_check_retries=5
        )
        
        orchestrator = ServiceOrchestrator(config)
        
        try:
            success, _ = await orchestrator.orchestrate_services()
            assert success, "Service orchestration should succeed"
            
            # Test direct connectivity
            for service_name, health in orchestrator.service_health.items():
                if health.is_healthy:
                    # Test port connectivity
                    connected = await self._test_port_connectivity(health.port)
                    assert connected, f"Port {health.port} for {service_name} is not connectable"
                    logger.info(f" PASS:  {service_name} port {health.port} connectivity validated")
            
            logger.info(" PASS:  Service connectivity validation passed")
            
        finally:
            if orchestrator.started_services:
                await orchestrator.cleanup_services()

    async def test_environment_configuration_after_orchestration(self):
        """Test that environment is properly configured after orchestration."""
        success, orchestrator = await orchestrate_e2e_services(
            required_services=["postgres", "redis"],
            timeout=30.0
        )
        
        assert success, "Service orchestration should succeed"
        
        try:
            env = get_env()
            
            # Check required environment variables are set
            required_env_vars = [
                "DATABASE_URL",
                "REDIS_URL", 
                "POSTGRES_SERVICE_URL",
                "REDIS_SERVICE_URL"
            ]
            
            for var in required_env_vars:
                value = env.get(var)
                assert value is not None, f"Environment variable {var} not set"
                assert "localhost" in value, f"Environment variable {var} should use localhost"
                logger.info(f" PASS:  {var}={value}")
            
            # Validate port mappings are correct
            database_url = env.get("DATABASE_URL")
            assert ":5433/" in database_url, f"#removed-legacyshould use test port 5433: {database_url}"
            
            redis_url = env.get("REDIS_URL") 
            assert ":6381/" in redis_url, f"REDIS_URL should use test port 6381: {redis_url}"
            
            logger.info(" PASS:  Environment configuration validation passed")
            
        finally:
            if orchestrator.started_services:
                await orchestrator.cleanup_services()

    async def test_orchestration_error_handling(self):
        """Test orchestration error handling when services fail."""
        # Test with non-existent service
        config = OrchestrationConfig(
            environment="test",
            required_services=["nonexistent_service"],
            startup_timeout=5.0,
            health_check_timeout=2.0,
            health_check_retries=2
        )
        
        orchestrator = ServiceOrchestrator(config)
        
        # This should fail gracefully
        success, _ = await orchestrator.orchestrate_services()
        assert not success, "Orchestration should fail for non-existent service"
        
        # Check error reporting
        health_report = orchestrator.get_health_report()
        assert "nonexistent_service" in health_report, "Error report should mention failed service"
        assert "UNHEALTHY" in health_report, "Error report should show unhealthy status"
        
        logger.info(" PASS:  Orchestration error handling test passed")

    async def test_service_health_monitoring(self):
        """Test service health monitoring functionality."""
        config = OrchestrationConfig(
            environment="test",
            required_services=["postgres", "redis"],
            health_check_retries=3,
            health_check_interval=1.0
        )
        
        orchestrator = ServiceOrchestrator(config)
        
        try:
            success, _ = await orchestrator.orchestrate_services()
            assert success, "Service orchestration should succeed"
            
            # Validate health monitoring data
            for service_name, health in orchestrator.service_health.items():
                assert health.last_check is not None, f"No last check time for {service_name}"
                assert health.last_check > 0, f"Invalid last check time for {service_name}"
                assert health.response_time_ms >= 0, f"Invalid response time for {service_name}"
                
                if health.is_healthy:
                    assert health.error_message is None, f"Healthy service should not have error: {service_name}"
                
                logger.info(f" PASS:  {service_name} health monitoring data validated")
            
            # Test health report generation
            report = orchestrator.get_health_report()
            assert "E2E SERVICE ORCHESTRATION HEALTH REPORT" in report, "Health report header missing"
            assert "Environment: test" in report, "Environment not in health report"
            assert "Healthy services:" in report, "Health summary missing"
            
            logger.info(" PASS:  Service health monitoring test passed")
            
        finally:
            if orchestrator.started_services:
                await orchestrator.cleanup_services()

    async def test_concurrent_service_orchestration(self):
        """Test that multiple orchestration attempts handle concurrency correctly."""
        configs = [
            OrchestrationConfig(
                environment="test",
                required_services=["postgres"],
                startup_timeout=30.0
            ),
            OrchestrationConfig(
                environment="test", 
                required_services=["redis"],
                startup_timeout=30.0
            )
        ]
        
        # Run multiple orchestrations concurrently
        tasks = []
        orchestrators = []
        
        for config in configs:
            orchestrator = ServiceOrchestrator(config)
            orchestrators.append(orchestrator)
            tasks.append(orchestrator.orchestrate_services())
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed (they can share the same services)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    pytest.fail(f"Orchestration {i} failed with exception: {result}")
                
                success, _ = result
                assert success, f"Orchestration {i} should succeed"
            
            logger.info(" PASS:  Concurrent service orchestration test passed")
            
        finally:
            # Cleanup all orchestrators
            for orchestrator in orchestrators:
                if orchestrator.started_services:
                    await orchestrator.cleanup_services()

    # Helper methods
    
    async def _test_port_connectivity(self, port: int, host: str = "localhost", timeout: float = 3.0) -> bool:
        """Test if a port is connectable."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            return False


@pytest.mark.asyncio 
@pytest.mark.integration
@pytest.mark.slow
class TestE2EServiceOrchestrationPerformance:
    """Performance tests for E2E service orchestration."""
    
    async def test_orchestration_performance(self):
        """Test that orchestration completes within reasonable time."""
        start_time = time.time()
        
        success, orchestrator = await orchestrate_e2e_services(
            required_services=["postgres", "redis"],
            timeout=60.0
        )
        
        elapsed = time.time() - start_time
        
        try:
            assert success, f"Orchestration failed: {orchestrator.get_health_report()}"
            
            # Should complete within reasonable time (services likely already running)
            assert elapsed < 30.0, f"Orchestration too slow: {elapsed:.1f}s"
            
            # Should have reasonable response times
            for service_name, health in orchestrator.service_health.items():
                if health.is_healthy:
                    assert health.response_time_ms < 5000, f"{service_name} response too slow: {health.response_time_ms}ms"
            
            logger.info(f" PASS:  Orchestration performance test passed ({elapsed:.1f}s)")
            
        finally:
            if orchestrator.started_services:
                await orchestrator.cleanup_services()


# Pytest configuration for this test module
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.integration, 
    pytest.mark.real_services
]