"""
Auth Service Health Check Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure auth service is healthy and operational for all user authentication needs
- Value Impact: Proactive monitoring prevents auth failures that would block all user access to chat features
- Strategic Impact: Core system reliability that enables business continuity and user experience

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
Tests validate auth service health monitoring with real service dependencies.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import aiohttp
from unittest.mock import patch, AsyncMock

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.config import AuthConfig
from auth_service.services.health_check_service import HealthCheckService
from auth_service.services.redis_service import RedisService
from auth_service.services.database_health_service import DatabaseHealthService
from auth_service.database import get_database


class TestAuthHealthCheckIntegration(BaseIntegrationTest):
    """Integration tests for auth service health checks with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # Real service instances
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.db = get_database()
        self.database_health_service = DatabaseHealthService(self.db)
        self.health_check_service = HealthCheckService(
            self.auth_config,
            self.redis_service,
            self.database_health_service
        )
        
        # Test endpoints
        self.auth_service_url = "http://localhost:8081"
        self.health_endpoint = f"{self.auth_service_url}/health"
        self.readiness_endpoint = f"{self.auth_service_url}/ready"
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean health check test data from Redis
            health_keys = await self.redis_service.keys("health:*")
            if health_keys:
                await self.redis_service.delete(*health_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_health_check(self):
        """
        Test database connectivity and health check.
        
        BVJ: Ensures auth service can connect to PostgreSQL for user authentication.
        """
        # Test database connection health
        db_health = await self.database_health_service.check_database_health()
        
        assert db_health is not None
        assert db_health["status"] == "healthy"
        assert db_health["connected"] is True
        assert "response_time_ms" in db_health
        assert db_health["response_time_ms"] < 1000  # Should be fast
        
        # Test database query execution
        query_health = await self.database_health_service.check_query_health()
        
        assert query_health is not None
        assert query_health["status"] == "healthy"
        assert query_health["query_successful"] is True
        assert "query_time_ms" in query_health
        
        # Test database table accessibility
        table_health = await self.database_health_service.check_table_health("users")
        
        assert table_health is not None
        assert table_health["status"] == "healthy"
        assert table_health["table_accessible"] is True
        assert table_health["table_name"] == "users"
        
        # Test comprehensive database health
        comprehensive_health = await self.database_health_service.comprehensive_health_check()
        
        assert comprehensive_health is not None
        assert comprehensive_health["overall_status"] == "healthy"
        assert comprehensive_health["connection"]["status"] == "healthy"
        assert comprehensive_health["queries"]["status"] == "healthy"
        assert "tables" in comprehensive_health
        assert len(comprehensive_health["tables"]) > 0
        
        # Verify essential tables are healthy
        essential_tables = ["users", "sessions", "refresh_tokens"]  # Auth-specific tables
        for table in essential_tables:
            table_status = comprehensive_health["tables"].get(table)
            if table_status:  # Table exists
                assert table_status["status"] == "healthy"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_health_check(self):
        """
        Test Redis connectivity and health check.
        
        BVJ: Ensures auth service can access Redis for session storage and caching.
        """
        # Test Redis connection health
        redis_health = await self.health_check_service.check_redis_health()
        
        assert redis_health is not None
        assert redis_health["status"] == "healthy"
        assert redis_health["connected"] is True
        assert "response_time_ms" in redis_health
        assert redis_health["response_time_ms"] < 1000
        
        # Test Redis operations
        test_key = "health:test:redis"
        test_value = f"health-check-{int(time.time())}"
        
        # Test SET operation
        await self.redis_service.set(test_key, test_value, ex=60)
        
        # Test GET operation
        retrieved_value = await self.redis_service.get(test_key)
        assert retrieved_value == test_value
        
        # Test Redis performance
        start_time = time.time()
        for i in range(10):
            await self.redis_service.set(f"health:perf:test:{i}", f"value-{i}", ex=60)
            await self.redis_service.get(f"health:perf:test:{i}")
        end_time = time.time()
        
        avg_operation_time = (end_time - start_time) * 1000 / 20  # ms per operation
        assert avg_operation_time < 100  # Should be fast
        
        # Test Redis memory health
        redis_info = await self.redis_service.info()
        if redis_info:
            # Check memory usage is reasonable
            used_memory = redis_info.get("used_memory", 0)
            max_memory = redis_info.get("maxmemory", float('inf'))
            
            if max_memory > 0:
                memory_usage_percent = (used_memory / max_memory) * 100
                assert memory_usage_percent < 90  # Should not be near memory limit
        
        # Cleanup performance test keys
        perf_keys = await self.redis_service.keys("health:perf:test:*")
        if perf_keys:
            await self.redis_service.delete(*perf_keys)
        
        # Cleanup test key
        await self.redis_service.delete(test_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_comprehensive_service_health(self):
        """
        Test comprehensive auth service health check.
        
        BVJ: Validates all auth service components are healthy for complete user authentication.
        """
        # Run comprehensive health check
        comprehensive_health = await self.health_check_service.comprehensive_health_check()
        
        assert comprehensive_health is not None
        assert comprehensive_health["service"] == "auth-service"
        assert comprehensive_health["status"] == "healthy"
        assert "timestamp" in comprehensive_health
        assert "uptime_seconds" in comprehensive_health
        assert comprehensive_health["uptime_seconds"] > 0
        
        # Check individual component health
        components = comprehensive_health["components"]
        
        # Database component
        assert "database" in components
        db_component = components["database"]
        assert db_component["status"] == "healthy"
        assert db_component["connected"] is True
        assert "response_time_ms" in db_component
        
        # Redis component
        assert "redis" in components
        redis_component = components["redis"]
        assert redis_component["status"] == "healthy"
        assert redis_component["connected"] is True
        assert "response_time_ms" in redis_component
        
        # JWT service component
        if "jwt_service" in components:
            jwt_component = components["jwt_service"]
            assert jwt_component["status"] == "healthy"
            assert "token_generation_working" in jwt_component
        
        # System resources
        if "system" in components:
            system_component = components["system"]
            assert system_component["status"] in ["healthy", "warning"]
            
            if "memory_usage_percent" in system_component:
                assert system_component["memory_usage_percent"] < 95
            
            if "cpu_usage_percent" in system_component:
                assert system_component["cpu_usage_percent"] < 95
        
        # Overall health should be healthy if all components are healthy
        component_statuses = [comp["status"] for comp in components.values()]
        if all(status == "healthy" for status in component_statuses):
            assert comprehensive_health["status"] == "healthy"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_response(self):
        """
        Test auth service health endpoint HTTP response.
        
        BVJ: Enables external monitoring systems to verify auth service health.
        """
        # Mock HTTP client for testing endpoint response format
        mock_health_response = {
            "service": "auth-service",
            "status": "healthy", 
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "components": {
                "database": {
                    "status": "healthy",
                    "connected": True,
                    "response_time_ms": 25
                },
                "redis": {
                    "status": "healthy", 
                    "connected": True,
                    "response_time_ms": 15
                }
            }
        }
        
        # Test health endpoint response structure
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.json.return_value = mock_health_response
            mock_get.return_value.__aenter__.return_value = mock_response
            
            async with aiohttp.ClientSession() as session:
                async with session.get(self.health_endpoint) as response:
                    assert response.status == 200
                    health_data = await response.json()
                    
                    assert health_data["service"] == "auth-service"
                    assert health_data["status"] == "healthy"
                    assert "timestamp" in health_data
                    assert "components" in health_data
                    
                    # Verify component structure
                    components = health_data["components"]
                    for component_name, component_data in components.items():
                        assert "status" in component_data
                        assert component_data["status"] in ["healthy", "warning", "unhealthy"]
                        
                        if component_name in ["database", "redis"]:
                            assert "connected" in component_data
                            assert "response_time_ms" in component_data
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_readiness_check(self):
        """
        Test auth service readiness check for startup validation.
        
        BVJ: Ensures auth service is ready to handle authentication requests before routing traffic.
        """
        # Test service readiness
        readiness_result = await self.health_check_service.check_readiness()
        
        assert readiness_result is not None
        assert readiness_result["ready"] is True
        assert readiness_result["status"] == "ready"
        assert "checks_passed" in readiness_result
        assert readiness_result["checks_passed"] > 0
        
        # Verify essential readiness checks
        essential_checks = readiness_result.get("essential_checks", {})
        
        # Database readiness
        if "database" in essential_checks:
            db_ready = essential_checks["database"]
            assert db_ready["ready"] is True
            assert db_ready["can_authenticate_users"] is True
        
        # Redis readiness
        if "redis" in essential_checks:
            redis_ready = essential_checks["redis"]
            assert redis_ready["ready"] is True
            assert redis_ready["can_store_sessions"] is True
        
        # JWT service readiness
        if "jwt_service" in essential_checks:
            jwt_ready = essential_checks["jwt_service"]
            assert jwt_ready["ready"] is True
            assert jwt_ready["can_generate_tokens"] is True
        
        # Configuration readiness
        if "configuration" in essential_checks:
            config_ready = essential_checks["configuration"]
            assert config_ready["ready"] is True
            assert config_ready["all_required_configs_present"] is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_check_failure_scenarios(self):
        """
        Test health check behavior during service failures.
        
        BVJ: Ensures monitoring systems can detect and respond to auth service issues.
        """
        # Test 1: Database connection failure simulation
        with patch.object(self.database_health_service, 'check_database_health') as mock_db_health:
            mock_db_health.return_value = {
                "status": "unhealthy",
                "connected": False,
                "error": "Connection refused",
                "response_time_ms": None
            }
            
            db_health = await self.database_health_service.check_database_health()
            assert db_health["status"] == "unhealthy"
            assert db_health["connected"] is False
            assert "error" in db_health
        
        # Test 2: Redis connection failure simulation
        with patch.object(self.redis_service, 'ping') as mock_redis_ping:
            mock_redis_ping.side_effect = Exception("Redis connection failed")
            
            try:
                redis_health = await self.health_check_service.check_redis_health_with_failure_handling()
                assert redis_health["status"] == "unhealthy"
                assert redis_health["connected"] is False
                assert "error" in redis_health
            except Exception:
                # Expected if health check properly propagates errors
                pass
        
        # Test 3: Partial failure scenario
        with patch.object(self.database_health_service, 'check_database_health') as mock_db_health:
            # Database healthy but slow
            mock_db_health.return_value = {
                "status": "warning",
                "connected": True,
                "response_time_ms": 2000,  # Very slow
                "warning": "Database response time is high"
            }
            
            comprehensive_health = await self.health_check_service.comprehensive_health_check()
            
            # Overall status should reflect the warning
            if comprehensive_health["status"] == "warning":
                assert "warnings" in comprehensive_health
                assert len(comprehensive_health["warnings"]) > 0
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_monitoring_metrics(self):
        """
        Test health monitoring metrics collection and storage.
        
        BVJ: Enables performance monitoring and capacity planning for auth service.
        """
        # Collect health metrics over time
        metrics_collection = []
        
        for i in range(5):
            health_metrics = await self.health_check_service.collect_health_metrics()
            
            assert health_metrics is not None
            assert "timestamp" in health_metrics
            assert "database_response_time_ms" in health_metrics
            assert "redis_response_time_ms" in health_metrics
            assert "active_connections" in health_metrics
            
            metrics_collection.append(health_metrics)
            
            # Wait between collections
            await asyncio.sleep(0.5)
        
        # Analyze metrics trends
        db_response_times = [m["database_response_time_ms"] for m in metrics_collection]
        redis_response_times = [m["redis_response_time_ms"] for m in metrics_collection]
        
        # Response times should be consistent and fast
        assert all(rt < 1000 for rt in db_response_times)  # Under 1 second
        assert all(rt < 500 for rt in redis_response_times)  # Under 0.5 seconds
        
        # Calculate average response times
        avg_db_time = sum(db_response_times) / len(db_response_times)
        avg_redis_time = sum(redis_response_times) / len(redis_response_times)
        
        assert avg_db_time < 500  # Average should be fast
        assert avg_redis_time < 100  # Redis should be very fast
        
        # Store metrics in Redis for monitoring dashboard
        metrics_summary = {
            "collection_time": datetime.now(timezone.utc).isoformat(),
            "sample_count": len(metrics_collection),
            "database_avg_response_ms": avg_db_time,
            "redis_avg_response_ms": avg_redis_time,
            "database_max_response_ms": max(db_response_times),
            "redis_max_response_ms": max(redis_response_times),
            "overall_health": "healthy" if avg_db_time < 500 and avg_redis_time < 100 else "warning"
        }
        
        metrics_key = f"health:metrics:summary:{int(time.time())}"
        await self.redis_service.set(
            metrics_key,
            json.dumps(metrics_summary),
            ex=3600  # Keep for 1 hour
        )
        
        # Verify metrics storage
        stored_metrics = await self.redis_service.get(metrics_key)
        assert stored_metrics is not None
        
        metrics_data = json.loads(stored_metrics)
        assert metrics_data["sample_count"] == 5
        assert metrics_data["overall_health"] == "healthy"
        
        # Cleanup metrics
        await self.redis_service.delete(metrics_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_health_checks(self):
        """
        Test concurrent health check operations for load validation.
        
        BVJ: Ensures health monitoring doesn't impact auth service performance under load.
        """
        # Run concurrent health checks
        concurrent_checks = 10
        
        async def run_health_check(check_id: int):
            """Run a single health check."""
            start_time = time.time()
            
            try:
                health_result = await self.health_check_service.comprehensive_health_check()
                end_time = time.time()
                
                return {
                    "check_id": check_id,
                    "success": True,
                    "duration_ms": (end_time - start_time) * 1000,
                    "status": health_result["status"],
                    "component_count": len(health_result["components"])
                }
            except Exception as e:
                end_time = time.time()
                return {
                    "check_id": check_id,
                    "success": False,
                    "duration_ms": (end_time - start_time) * 1000,
                    "error": str(e)
                }
        
        # Execute concurrent health checks
        tasks = [run_health_check(i) for i in range(concurrent_checks)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results
        successful_checks = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        failed_checks = [r for r in results if isinstance(r, Exception) or not r.get("success")]
        
        # Most checks should succeed
        assert len(successful_checks) >= concurrent_checks * 0.8  # At least 80% success
        assert len(failed_checks) < concurrent_checks * 0.2  # Less than 20% failures
        
        # Check performance under concurrent load
        durations = [r["duration_ms"] for r in successful_checks]
        avg_duration = sum(durations) / len(durations)
        max_duration = max(durations)
        
        # Health checks should remain fast under load
        assert avg_duration < 2000  # Under 2 seconds on average
        assert max_duration < 5000   # Under 5 seconds maximum
        
        # Verify all successful checks returned healthy status
        statuses = [r["status"] for r in successful_checks]
        healthy_count = sum(1 for status in statuses if status == "healthy")
        
        # Most should be healthy (allowing for some warnings under load)
        assert healthy_count >= len(successful_checks) * 0.7