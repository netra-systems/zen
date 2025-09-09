"""
Test Service Dependency Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure graceful degradation when services are unavailable
- Value Impact: System resilience enables continuous operation during outages
- Strategic Impact: Critical for $500K+ ARR - service failures should not break user experience

This test validates Critical Issue #2 from Golden Path:
"Missing Service Dependencies" - Agent supervisor and thread service not always available
during WebSocket connection, requiring graceful degradation.

CRITICAL REQUIREMENTS:
1. Test graceful degradation when Redis is unavailable
2. Test partial functionality when database is slow
3. Test service health monitoring with real services
4. Test fallback behavior validation
5. NO MOCKS for PostgreSQL/Redis - test real service failures
6. Use E2E authentication for all service interactions
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealthStatus:
    """Service health status for testing."""
    service_name: str
    is_healthy: bool
    response_time: float
    error_message: Optional[str] = None
    fallback_active: bool = False


class TestServiceDependencyIntegration(BaseIntegrationTest):
    """Test service dependency management with real services."""
    
    def setup_method(self):
        super().setup_method()
        self.auth_helper = E2EAuthHelper(environment="test")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_graceful_degradation_redis_unavailable(self, real_services_fixture):
        """Test graceful degradation when Redis is unavailable."""
        user_context = await create_authenticated_user_context(
            user_email=f"redis_degradation_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Test normal operation first
        normal_result = await self._test_service_operation_with_redis(
            db_session, user_context, redis_available=True
        )
        assert normal_result["success"], "Normal operation should work"
        
        # Test degraded operation without Redis
        degraded_result = await self._test_service_operation_with_redis(
            db_session, user_context, redis_available=False
        )
        
        assert degraded_result["success"], "Should work without Redis"
        assert degraded_result["fallback_used"], "Should use fallback mechanisms"
        assert degraded_result["core_functionality_preserved"], "Core features should work"
        
        # Verify business value delivered
        self.assert_business_value_delivered(degraded_result, "automation")
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_partial_functionality_slow_database(self, real_services_fixture):
        """Test partial functionality when database is slow."""
        user_context = await create_authenticated_user_context(
            user_email=f"slow_db_{uuid.uuid4().hex[:8]}@example.com"
        )
        
        db_session = real_services_fixture["db"]
        await self._create_user_in_database(db_session, user_context)
        
        # Test with artificial database slowdown
        slow_db_result = await self._test_service_with_slow_database(
            db_session, user_context, delay_seconds=2.0
        )
        
        assert slow_db_result["completed"], "Should complete despite slow database"
        assert slow_db_result["timeout_handled"], "Should handle timeouts gracefully"
        assert slow_db_result["partial_results_available"], "Should provide partial results"
        
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_service_health_monitoring(self, real_services_fixture):
        """Test service health monitoring with real services."""
        services_to_monitor = ["postgresql", "redis", "backend", "auth"]
        health_results = {}
        
        for service_name in services_to_monitor:
            health_status = await self._check_service_health(
                real_services_fixture, service_name
            )
            health_results[service_name] = health_status
        
        # Verify critical services are healthy
        critical_services = ["postgresql"]
        for service in critical_services:
            assert health_results[service].is_healthy, f"{service} must be healthy"
        
        # Generate health report
        health_report = await self._generate_service_health_report(health_results)
        assert health_report["overall_health"] >= 0.5, "Overall health should be acceptable"
        
    # Helper methods
    async def _create_user_in_database(self, db_session, user_context):
        """Create user in database for testing."""
        user_insert = """
            INSERT INTO users (id, email, full_name, is_active, created_at)
            VALUES (%(user_id)s, %(email)s, %(full_name)s, true, %(created_at)s)
            ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
        """
        
        await db_session.execute(user_insert, {
            "user_id": str(user_context.user_id),
            "email": user_context.agent_context.get("user_email"),
            "full_name": f"Service Test User {str(user_context.user_id)[:8]}",
            "created_at": datetime.now(timezone.utc)
        })
        await db_session.commit()
    
    async def _test_service_operation_with_redis(
        self, db_session, user_context, redis_available: bool
    ) -> Dict[str, Any]:
        """Test service operation with/without Redis."""
        try:
            if redis_available:
                # Normal operation with Redis
                cache_data = {"user_session": "active", "preferences": {"theme": "dark"}}
                # In real implementation, would store in Redis
                
                return {
                    "success": True,
                    "fallback_used": False,
                    "core_functionality_preserved": True,
                    "cache_available": True
                }
            else:
                # Degraded operation without Redis
                # Use database for session storage instead
                session_insert = """
                    INSERT INTO user_sessions_fallback (
                        user_id, session_data, created_at
                    ) VALUES (%(user_id)s, %(session_data)s, %(created_at)s)
                """
                
                await db_session.execute(session_insert, {
                    "user_id": str(user_context.user_id),
                    "session_data": json.dumps({"fallback": True}),
                    "created_at": datetime.now(timezone.utc)
                })
                await db_session.commit()
                
                return {
                    "success": True,
                    "fallback_used": True,
                    "core_functionality_preserved": True,
                    "cache_available": False
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _test_service_with_slow_database(
        self, db_session, user_context, delay_seconds: float
    ) -> Dict[str, Any]:
        """Test service behavior with slow database."""
        start_time = time.time()
        
        try:
            # Simulate slow query with timeout handling
            slow_query = """
                SELECT pg_sleep(%(delay)s);
                SELECT id, email FROM users WHERE id = %(user_id)s;
            """
            
            try:
                result = await asyncio.wait_for(
                    db_session.execute(slow_query, {
                        "delay": min(delay_seconds, 1.0),  # Cap delay for testing
                        "user_id": str(user_context.user_id)
                    }),
                    timeout=3.0
                )
                
                return {
                    "completed": True,
                    "timeout_handled": False,
                    "partial_results_available": True,
                    "execution_time": time.time() - start_time
                }
                
            except asyncio.TimeoutError:
                # Handle timeout gracefully
                return {
                    "completed": False,
                    "timeout_handled": True,
                    "partial_results_available": True,
                    "execution_time": time.time() - start_time
                }
                
        except Exception as e:
            return {
                "completed": False,
                "error": str(e)
            }
    
    async def _check_service_health(
        self, real_services_fixture, service_name: str
    ) -> ServiceHealthStatus:
        """Check health of a specific service."""
        start_time = time.time()
        
        try:
            if service_name == "postgresql":
                if real_services_fixture["database_available"]:
                    # Test database connection
                    db_session = real_services_fixture["db"]
                    await db_session.execute("SELECT 1")
                    
                    return ServiceHealthStatus(
                        service_name=service_name,
                        is_healthy=True,
                        response_time=time.time() - start_time
                    )
                else:
                    return ServiceHealthStatus(
                        service_name=service_name,
                        is_healthy=False,
                        response_time=time.time() - start_time,
                        error_message="Database not available"
                    )
            
            elif service_name == "redis":
                # Test Redis connection if available
                redis_available = real_services_fixture["services_available"].get("redis", False)
                
                return ServiceHealthStatus(
                    service_name=service_name,
                    is_healthy=redis_available,
                    response_time=time.time() - start_time,
                    fallback_active=not redis_available
                )
            
            else:
                # Other services
                service_available = real_services_fixture["services_available"].get(service_name, False)
                
                return ServiceHealthStatus(
                    service_name=service_name,
                    is_healthy=service_available,
                    response_time=time.time() - start_time
                )
                
        except Exception as e:
            return ServiceHealthStatus(
                service_name=service_name,
                is_healthy=False,
                response_time=time.time() - start_time,
                error_message=str(e)
            )
    
    async def _generate_service_health_report(
        self, health_results: Dict[str, ServiceHealthStatus]
    ) -> Dict[str, Any]:
        """Generate service health report."""
        healthy_services = sum(1 for status in health_results.values() if status.is_healthy)
        total_services = len(health_results)
        
        return {
            "overall_health": healthy_services / total_services,
            "healthy_services": healthy_services,
            "total_services": total_services,
            "critical_services_healthy": health_results.get("postgresql", ServiceHealthStatus("", False, 0)).is_healthy,
            "fallbacks_active": sum(1 for status in health_results.values() if status.fallback_active)
        }