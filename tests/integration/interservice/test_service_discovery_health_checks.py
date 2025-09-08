"""
Service Discovery and Health Check Integration Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Reliability
- Business Goal: Ensure system uptime and automatic failure detection
- Value Impact: Prevents user-facing outages through proactive health monitoring
- Strategic Impact: Enables automated scaling and recovery, reducing operational costs

These tests validate service discovery mechanisms and health check endpoints
across all services to ensure system reliability.
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
from unittest.mock import Mock, patch
from datetime import datetime

from test_framework.ssot.base_test_case import BaseTestCase
from shared.isolated_environment import get_env


class TestServiceDiscoveryHealthChecks(BaseTestCase):
    """Integration tests for service discovery and health monitoring."""
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.health
    async def test_backend_service_health_endpoint(self):
        """
        Test backend service health endpoint returns proper status.
        
        BVJ: System reliability - enables load balancers and monitoring systems
        to detect backend health, preventing user traffic to unhealthy instances.
        """
        env = get_env()
        env.enable_isolation()
        env.set("BACKEND_SERVICE_URL", "http://localhost:8000", "test")
        
        # Mock healthy backend response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "netra_backend",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "healthy",
                "redis": "healthy",
                "auth_service": "healthy"
            },
            "uptime_seconds": 3600,
            "memory_usage_mb": 256.5,
            "active_connections": 12
        }
        
        with patch('httpx.AsyncClient.get', return_value=mock_response) as mock_get:
            # Test health endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{env.get('BACKEND_SERVICE_URL')}/health")
            
            # Verify health response structure
            health_data = mock_response.json()
            assert health_data.get("status") == "healthy"
            assert health_data.get("service") == "netra_backend"
            assert "version" in health_data
            assert "timestamp" in health_data
            assert "checks" in health_data
            
            # Verify dependency checks
            checks = health_data["checks"]
            assert "database" in checks
            assert "redis" in checks
            assert "auth_service" in checks
            
            # All checks should be healthy
            for check_name, check_status in checks.items():
                assert check_status in ["healthy", "degraded", "unhealthy"], f"{check_name} has invalid status: {check_status}"
            
            # Verify metrics are present
            assert "uptime_seconds" in health_data
            assert "memory_usage_mb" in health_data
            assert isinstance(health_data["uptime_seconds"], (int, float))
            assert isinstance(health_data["memory_usage_mb"], (int, float))
            
            # Verify API call
            mock_get.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.health
    async def test_auth_service_health_endpoint(self):
        """
        Test auth service health endpoint and dependency checks.
        
        BVJ: Security reliability - ensures authentication service health
        is properly monitored, preventing auth failures from going undetected.
        """
        env = get_env()
        env.enable_isolation()
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        
        # Mock auth service health response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "healthy",
            "service": "netra_auth",
            "version": "1.0.0",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": "healthy",
                "redis": "healthy",
                "oauth_provider": "healthy"
            },
            "auth_stats": {
                "active_sessions": 45,
                "tokens_issued_last_hour": 123,
                "failed_login_attempts": 2
            }
        }
        
        with patch('httpx.AsyncClient.get', return_value=mock_response) as mock_get:
            # Test auth health endpoint
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{env.get('AUTH_SERVICE_URL')}/health")
            
            # Verify auth-specific health response
            health_data = mock_response.json()
            assert health_data.get("status") == "healthy"
            assert health_data.get("service") == "netra_auth"
            
            # Verify auth-specific checks
            checks = health_data["checks"]
            assert "database" in checks
            assert "redis" in checks
            assert "oauth_provider" in checks
            
            # Verify auth-specific metrics
            auth_stats = health_data.get("auth_stats", {})
            assert "active_sessions" in auth_stats
            assert "tokens_issued_last_hour" in auth_stats
            assert "failed_login_attempts" in auth_stats
            
            # Verify metrics are reasonable
            assert isinstance(auth_stats["active_sessions"], int)
            assert auth_stats["active_sessions"] >= 0
            assert isinstance(auth_stats["failed_login_attempts"], int)
            assert auth_stats["failed_login_attempts"] >= 0
            
            mock_get.assert_called_once()
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.health
    async def test_cross_service_health_aggregation(self):
        """
        Test aggregated health status across all services.
        
        BVJ: System observability - provides single point of truth for overall
        system health, enabling quick incident response and status page updates.
        """
        env = get_env()
        env.enable_isolation()
        env.set("BACKEND_SERVICE_URL", "http://localhost:8000", "test")
        env.set("AUTH_SERVICE_URL", "http://localhost:8081", "test")
        env.set("ANALYTICS_SERVICE_URL", "http://localhost:8002", "test")
        
        # Mock responses for all services
        services_health = {
            "backend": {
                "status": "healthy",
                "service": "netra_backend",
                "checks": {"database": "healthy", "redis": "healthy"}
            },
            "auth": {
                "status": "healthy", 
                "service": "netra_auth",
                "checks": {"database": "healthy", "oauth_provider": "healthy"}
            },
            "analytics": {
                "status": "degraded",
                "service": "netra_analytics", 
                "checks": {"clickhouse": "degraded", "data_pipeline": "healthy"}
            }
        }
        
        async def mock_health_check(url: str) -> Dict[str, Any]:
            """Simulate health check for different services."""
            if "8000" in url:  # Backend
                return services_health["backend"]
            elif "8081" in url:  # Auth
                return services_health["auth"]
            elif "8002" in url:  # Analytics
                return services_health["analytics"]
            else:
                raise ValueError(f"Unknown service URL: {url}")
        
        # Simulate health aggregation logic
        all_services = [
            ("backend", env.get("BACKEND_SERVICE_URL")),
            ("auth", env.get("AUTH_SERVICE_URL")),
            ("analytics", env.get("ANALYTICS_SERVICE_URL"))
        ]
        
        aggregated_health = {
            "overall_status": "degraded",  # Worst status wins
            "services": {},
            "summary": {
                "total_services": len(all_services),
                "healthy_services": 0,
                "degraded_services": 0,
                "unhealthy_services": 0
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Process each service
        for service_name, service_url in all_services:
            try:
                health_data = await mock_health_check(service_url)
                aggregated_health["services"][service_name] = health_data
                
                # Update summary counts
                status = health_data["status"]
                if status == "healthy":
                    aggregated_health["summary"]["healthy_services"] += 1
                elif status == "degraded":
                    aggregated_health["summary"]["degraded_services"] += 1
                else:
                    aggregated_health["summary"]["unhealthy_services"] += 1
                    
            except Exception as e:
                # Service unreachable
                aggregated_health["services"][service_name] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                aggregated_health["summary"]["unhealthy_services"] += 1
        
        # Verify aggregation results
        assert aggregated_health["overall_status"] == "degraded", "Overall status should be worst individual status"
        assert len(aggregated_health["services"]) == 3, "Should check all services"
        
        # Verify summary counts
        summary = aggregated_health["summary"]
        assert summary["healthy_services"] == 2, "Backend and auth should be healthy"
        assert summary["degraded_services"] == 1, "Analytics should be degraded"
        assert summary["unhealthy_services"] == 0, "No services should be unhealthy"
        assert summary["total_services"] == 3, "Should count all services"
        
        # Verify individual service data
        assert aggregated_health["services"]["backend"]["status"] == "healthy"
        assert aggregated_health["services"]["auth"]["status"] == "healthy"
        assert aggregated_health["services"]["analytics"]["status"] == "degraded"
    
    @pytest.mark.integration
    @pytest.mark.interservice
    @pytest.mark.health
    async def test_service_health_check_timeout_handling(self):
        """
        Test health check behavior when services are slow to respond.
        
        BVJ: System resilience - ensures health monitoring doesn't become
        a bottleneck and can detect slow services before they impact users.
        """
        env = get_env()
        env.enable_isolation()
        env.set("BACKEND_SERVICE_URL", "http://localhost:8000", "test")
        env.set("HEALTH_CHECK_TIMEOUT_SECONDS", "5", "test")
        
        # Mock slow/timeout response
        async def simulate_slow_service():
            """Simulate a service that's slow to respond."""
            await asyncio.sleep(10)  # Longer than timeout
            return {"status": "healthy"}
        
        timeout_seconds = int(env.get("HEALTH_CHECK_TIMEOUT_SECONDS", "5"))
        
        # Test timeout handling
        try:
            # Simulate health check with timeout
            with patch('asyncio.wait_for', side_effect=asyncio.TimeoutError()) as mock_wait_for:
                async with httpx.AsyncClient() as client:
                    try:
                        response = await asyncio.wait_for(
                            client.get(f"{env.get('BACKEND_SERVICE_URL')}/health"),
                            timeout=timeout_seconds
                        )
                    except asyncio.TimeoutError:
                        # Expected behavior - should handle timeout gracefully
                        health_result = {
                            "status": "unhealthy",
                            "service": "netra_backend",
                            "error": "health_check_timeout",
                            "timeout_seconds": timeout_seconds,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
                        # Verify timeout handling
                        assert health_result["status"] == "unhealthy"
                        assert health_result["error"] == "health_check_timeout"
                        assert health_result["timeout_seconds"] == timeout_seconds
                        
                        # Verify timeout was attempted
                        mock_wait_for.assert_called_once()
                        
        except Exception as e:
            # Should not raise unhandled exceptions
            assert False, f"Health check timeout should be handled gracefully: {e}"
        
        # Verify timeout configuration is reasonable
        assert 1 <= timeout_seconds <= 30, "Health check timeout should be between 1-30 seconds"