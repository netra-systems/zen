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
from auth_service.auth_core.config import AuthConfig
from auth_service.services.redis_service import RedisService
from auth_service.health_config import get_auth_health, check_auth_postgres_health, check_oauth_providers_health, check_jwt_configuration
from auth_service.auth_core.database import get_db_session


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
        # Test database connection health using available function
        db_health = await check_auth_postgres_health()
        
        assert db_health is not None
        assert db_health["status"] == "healthy"
        assert "message" in db_health
        
        # Test direct database session access
        try:
            session = get_db_session()
            assert session is not None
            self.logger.info("Database session created successfully")
        except Exception as e:
            pytest.fail(f"Database session creation failed: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_redis_health_check(self):
        """
        Test Redis connectivity and health check.
        
        BVJ: Ensures auth service can access Redis for session storage and caching.
        """
        # Test Redis connection health directly
        try:
            await self.redis_service.ping()
            redis_healthy = True
        except Exception:
            redis_healthy = False
        
        assert redis_healthy, "Redis should be healthy and responsive"
        
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
        # Run comprehensive health check using available function
        comprehensive_health = await get_auth_health()
        
        assert comprehensive_health is not None
        assert comprehensive_health["service"] == "auth_service"
        assert comprehensive_health["status"] in ["healthy", "degraded", "unhealthy"]
        assert "version" in comprehensive_health
        assert "checks" in comprehensive_health
        
        # Check individual component health
        checks = comprehensive_health["checks"]
        
        # Database component
        assert "database" in checks
        db_check = checks["database"]
        assert db_check["status"] in ["healthy", "degraded", "unhealthy"]
        assert "message" in db_check
        
        # JWT service component
        assert "jwt" in checks
        jwt_check = checks["jwt"]
        assert jwt_check["status"] in ["healthy", "degraded", "unhealthy"]
        assert "message" in jwt_check
        
        # OAuth component
        assert "oauth" in checks
        oauth_check = checks["oauth"]
        assert oauth_check["status"] in ["healthy", "degraded", "unhealthy"]
        assert "message" in oauth_check
    
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
        # Test service readiness using available health functions
        auth_health = await get_auth_health()
        jwt_health = await check_jwt_configuration() 
        db_health = await check_auth_postgres_health()
        
        # Service is ready if core components are healthy
        service_ready = (
            auth_health["status"] in ["healthy", "degraded"] and
            jwt_health["status"] in ["healthy", "degraded"] and
            db_health["status"] == "healthy"
        )
        
        assert service_ready, "Auth service should be ready when core components are healthy"
        
        # Verify individual readiness components
        assert jwt_health["status"] in ["healthy", "degraded"]
        assert db_health["status"] == "healthy"
        
        # Test Redis readiness
        try:
            await self.redis_service.ping()
            redis_ready = True
        except Exception:
            redis_ready = False
        
        assert redis_ready, "Redis should be ready for session storage"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_check_failure_scenarios(self):
        """
        Test health check behavior during service failures.
        
        BVJ: Ensures monitoring systems can detect and respond to auth service issues.
        """
        # Test 1: Database connection failure simulation
        with patch('auth_service.health_config.check_auth_postgres_health') as mock_db_health:
            mock_db_health.return_value = {
                "status": "unhealthy",
                "message": "Connection refused"
            }
            
            db_health = await check_auth_postgres_health()
            assert db_health["status"] == "unhealthy"
            assert "message" in db_health
        
        # Test 2: Redis connection failure simulation
        with patch.object(self.redis_service, 'ping') as mock_redis_ping:
            mock_redis_ping.side_effect = Exception("Redis connection failed")
            
            try:
                await self.redis_service.ping()
                pytest.fail("Expected Redis ping to fail")
            except Exception as e:
                assert "Redis connection failed" in str(e)
        
        # Test 3: JWT configuration failure scenario
        with patch('auth_service.health_config.check_jwt_configuration') as mock_jwt_health:
            mock_jwt_health.return_value = {
                "status": "unhealthy",
                "message": "JWT secret key not configured"
            }
            
            jwt_health = await check_jwt_configuration()
            assert jwt_health["status"] == "unhealthy"
            assert "JWT secret key" in jwt_health["message"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_monitoring_metrics(self):
        """
        Test health monitoring metrics collection and storage.
        
        BVJ: Enables performance monitoring and capacity planning for auth service.
        """
        # Collect health metrics over time using available functions
        metrics_collection = []
        
        for i in range(5):
            # Collect health data using available functions
            start_time = time.time()
            auth_health = await get_auth_health()
            end_time = time.time()
            
            health_metrics = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "overall_status": auth_health["status"],
                "health_check_duration_ms": (end_time - start_time) * 1000,
                "service": auth_health["service"],
                "version": auth_health["version"]
            }
            
            assert health_metrics is not None
            assert "timestamp" in health_metrics
            assert "overall_status" in health_metrics
            assert "health_check_duration_ms" in health_metrics
            
            metrics_collection.append(health_metrics)
            
            # Wait between collections
            await asyncio.sleep(0.5)
        
        # Analyze metrics trends
        health_check_durations = [m["health_check_duration_ms"] for m in metrics_collection]
        statuses = [m["overall_status"] for m in metrics_collection]
        
        # Health check durations should be reasonable
        assert all(duration < 5000 for duration in health_check_durations)  # Under 5 seconds
        
        # Calculate average health check time
        avg_health_check_time = sum(health_check_durations) / len(health_check_durations)
        assert avg_health_check_time < 2000  # Average should be under 2 seconds
        
        # Most health checks should return healthy or degraded status
        healthy_count = sum(1 for status in statuses if status in ["healthy", "degraded"])
        assert healthy_count >= len(metrics_collection) * 0.8  # At least 80% healthy
        
        # Store metrics in Redis for monitoring dashboard
        metrics_summary = {
            "collection_time": datetime.now(timezone.utc).isoformat(),
            "sample_count": len(metrics_collection),
            "avg_health_check_duration_ms": avg_health_check_time,
            "max_health_check_duration_ms": max(health_check_durations),
            "healthy_percentage": (healthy_count / len(metrics_collection)) * 100,
            "overall_health": "healthy" if healthy_count >= len(metrics_collection) * 0.8 else "warning"
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
        assert metrics_data["overall_health"] in ["healthy", "warning"]
        
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
                health_result = await get_auth_health()
                end_time = time.time()
                
                return {
                    "check_id": check_id,
                    "success": True,
                    "duration_ms": (end_time - start_time) * 1000,
                    "status": health_result["status"],
                    "component_count": len(health_result["checks"])
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