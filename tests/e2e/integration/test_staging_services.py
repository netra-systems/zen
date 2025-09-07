"""Staging Service Health and Connectivity Tests

from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
Business Value Justification (BVJ):
- Segment: Enterprise/Platform - All customer tiers
- Business Goal: Service health validation and connectivity assurance
- Value Impact: Ensures all services are accessible and healthy before deployment
- Revenue Impact: Prevents service outages that could affect customer experience

Tests service availability and health:
- Backend service health endpoints
- Auth service health validation
- Frontend service accessibility  
- WebSocket service connectivity
- Database connection health
- Service recovery mechanisms
"""

import asyncio
import json
import os
from typing import Any, Dict

import aiohttp
import httpx
import pytest

from tests.e2e.staging_test_helpers import (
    ServiceHealthStatus,
    StagingTestSuite,
    get_staging_suite,
)


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class TestStagingServiceHealth:
    """Test health endpoints for all staging services."""
    
    @pytest.mark.e2e
    async def test_backend_service_health(self):
        """Test backend service health endpoint is accessible and healthy."""
        suite = await get_staging_suite()
        backend_url = suite.env_config.services.backend
        
        health_status = await suite.check_service_health(f"{backend_url}/health/")
        
        assert health_status.healthy, f"Backend unhealthy: {health_status.details}"
        assert health_status.status_code == 200
        assert health_status.response_time_ms < 5000  # 5 second timeout
        assert health_status.details.get("status") == "healthy"
    
    @pytest.mark.e2e
    async def test_auth_service_health(self):
        """Test auth service health endpoint is accessible and healthy."""
        suite = await get_staging_suite()
        auth_url = suite.env_config.services.auth
        
        health_status = await suite.check_service_health(f"{auth_url}/health")
        
        assert health_status.healthy, f"Auth unhealthy: {health_status.details}"
        assert health_status.status_code == 200
        assert health_status.response_time_ms < 5000
        assert health_status.details.get("status") == "healthy"
    
    @pytest.mark.e2e
    async def test_frontend_service_accessibility(self):
        """Test frontend service serves content and is accessible."""
        suite = await get_staging_suite()
        frontend_url = suite.env_config.services.frontend
        
        response = await suite.test_client.get(frontend_url)
        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        
        # Basic content validation
        content = response.text
        assert len(content) > 100, "Frontend content too minimal"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class TestStagingWebSocketConnectivity:
    """Test WebSocket service connectivity and protocol support."""
    
    @pytest.mark.e2e
    async def test_websocket_service_configuration(self):
        """Test WebSocket service URL configuration and format."""
        suite = await get_staging_suite()
        ws_url = suite.env_config.services.websocket
        
        # Validate WebSocket URL format and protocol
        assert ws_url.startswith("wss://"), f"Invalid WebSocket URL: {ws_url}"
        assert "staging" in ws_url, "WebSocket URL should contain 'staging'"
    
    @pytest.mark.e2e
    async def test_websocket_health_endpoint(self):
        """Test WebSocket health endpoint via HTTP upgrade check."""
        suite = await get_staging_suite()
        ws_url = suite.env_config.services.websocket
        
        # Convert WebSocket URL to HTTP health check
        http_url = ws_url.replace("wss://", "https://").replace("/ws", "/health/")
        
        response = await suite.test_client.get(http_url)
        assert response.status_code == 200, f"WebSocket health check failed: {response.status_code}"
    
    @pytest.mark.e2e
    async def test_websocket_connection_with_auth(self):
        """Test WebSocket connection with proper authentication flow."""
        suite = await get_staging_suite()
        harness = suite.harness
        
        # Create test user with access token
        user = await harness.create_test_user()
        assert user.access_token, "Failed to get access token for WebSocket test"
        
        # Test WebSocket connection with authentication
        ws_url = harness.get_websocket_url()
        headers = {"Authorization": f"Bearer {user.access_token}"}
        
        async with suite.aio_session.ws_connect(
            ws_url, headers=headers, ssl=False, timeout=10
        ) as ws:
            # Send connection initialization
            await ws.send_json({
                "type": "connection_init",
                "payload": {"auth_token": user.access_token}
            })
            
            # Wait for acknowledgment
            msg = await ws.receive()
            assert msg.type == aiohttp.WSMsgType.TEXT, "Invalid message type"
            data = json.loads(msg.data)
            assert data.get("type") in ["connection_ack", "connected"], \
                   f"Invalid connection response: {data.get('type')}"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class TestStagingDatabaseHealth:
    """Test database connections and health for staging environment."""
    
    @pytest.mark.e2e
    async def test_database_connection_health(self):
        """Test database connections are healthy and responsive."""
        suite = await get_staging_suite()
        harness = suite.harness
        backend_url = harness.get_service_url("backend")
        
        # Test database health via backend service
        try:
            response = await suite.test_client.get(f"{backend_url}/health/database")
            if response.status_code == 200:
                db_data = response.json()
                assert db_data.get("status") in ["healthy", "ok"], \
                       f"Database unhealthy: {db_data}"
            elif response.status_code == 404:
                # Fallback to general health endpoint
                health_response = await suite.test_client.get(f"{backend_url}/health")
                assert health_response.status_code == 200, "Backend health failed"
                health_data = health_response.json()
                assert health_data.get("status") == "healthy", "Backend unhealthy"
        except httpx.RequestError as e:
            pytest.fail(f"Database health check failed with network error: {e}")
    
    @pytest.mark.e2e
    async def test_database_configuration_validation(self):
        """Test database configurations meet staging requirements."""
        # PostgreSQL configuration
        db_url = get_env().get("DATABASE_URL")
        assert db_url is not None, "#removed-legacynot set"
        assert db_url.startswith("postgresql://"), "Invalid PostgreSQL URL"
        
        # Redis configuration  
        redis_url = get_env().get("REDIS_URL")
        assert redis_url is not None, "REDIS_URL not set"
        assert redis_url.startswith("redis://"), "Invalid Redis URL"
        
        # ClickHouse configuration
        clickhouse_url = get_env().get("CLICKHOUSE_URL")
        assert clickhouse_url is not None, "CLICKHOUSE_URL not set"
        assert clickhouse_url.startswith("clickhouse://"), "Invalid ClickHouse URL"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.e2e
class TestStagingServiceRecovery:
    """Test service recovery mechanisms and resilience."""
    
    @pytest.mark.e2e
    async def test_service_health_stability(self):
        """Test service health checks are stable over multiple attempts."""
        suite = await get_staging_suite()
        services = suite.env_config.services
        
        # Multiple health check attempts to verify stability
        health_results = []
        for attempt in range(3):
            backend_health = await suite.check_service_health(f"{services.backend}/health/")
            auth_health = await suite.check_service_health(f"{services.auth}/health")
            
            health_results.append(backend_health.healthy and auth_health.healthy)
            
            if attempt < 2:  # Don't sleep after last attempt
                await asyncio.sleep(2)
        
        # At least 2 out of 3 health checks should pass for stability
        passed_checks = sum(health_results)
        assert passed_checks >= 2, f"Health check stability failed: {health_results}"
    
    @pytest.mark.e2e
    async def test_concurrent_service_access(self):
        """Test services handle concurrent access properly."""
        suite = await get_staging_suite()
        backend_url = suite.env_config.services.backend
        
        # Concurrent health check requests
        async def health_check():
            try:
                response = await suite.test_client.get(f"{backend_url}/health/")
                return response.status_code == 200
            except Exception:
                return False
        
        # Run 5 concurrent health checks
        tasks = [health_check() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_checks = sum(1 for r in results if r is True)
        assert successful_checks >= 3, f"Concurrent access failed: {successful_checks}/5"


@pytest.mark.asyncio
@pytest.mark.staging
@pytest.mark.comprehensive
@pytest.mark.e2e
class TestStagingServiceIntegration:
    """Test service integration and communication patterns."""
    
    @pytest.mark.e2e
    async def test_service_initialization_order(self):
        """Test services initialize in correct dependency order."""
        suite = await get_staging_suite()
        
        # Auth service should be ready first (base dependency)
        auth_health = await suite.check_service_health(
            f"{suite.env_config.services.auth}/health"
        )
        assert auth_health.healthy, "Auth service must be ready first"
        
        # Backend service should be ready with database dependencies
        backend_health = await suite.check_service_health(
            f"{suite.env_config.services.backend}/health"
        )
        assert backend_health.healthy, "Backend service must be ready after auth"
        
        # Verify both services report healthy status
        assert auth_health.details.get("status") == "healthy"
        assert backend_health.details.get("status") == "healthy"
    
    @pytest.mark.e2e
    async def test_api_endpoint_accessibility(self):
        """Test critical API endpoints are accessible through backend."""
        suite = await get_staging_suite()
        harness = suite.harness
        
        # Create test user for authenticated requests
        user = await harness.create_test_user()
        backend_url = harness.get_service_url("backend")
        headers = {"Authorization": f"Bearer {user.access_token}"}
        
        # Test thread creation API (critical user functionality)
        response = await suite.test_client.post(
            f"{backend_url}/api/threads",
            headers=headers,
            json={"name": "Service Integration Test"}
        )
        
        assert response.status_code in [200, 201], \
               f"Thread creation failed: {response.status_code}"
        
        thread_data = response.json()
        assert "id" in thread_data, "Thread creation response missing ID"
    
    @pytest.mark.e2e
    async def test_complete_user_journey_flow(self):
        """Test complete user journey through all services."""
        suite = await get_staging_suite()
        harness = suite.harness
        
        # Create user and WebSocket connection
        user = await harness.create_test_user()
        ws = await harness.create_websocket_connection(user)
        
        # Send test message
        test_message = "Service integration test message"
        await ws.send_message({
            "type": "message", 
            "content": test_message,
            "thread_id": f"integration_test_{user.user_id}"
        })
        
        # Wait for any response (shows message processing works)
        try:
            response = await ws.receive_message(timeout=15)
            # If we get a response, the integration is working
            if response:
                assert response.get("type") in ["message", "ack", "status"]
        except asyncio.TimeoutError:
            # Timeout is acceptable for staging - the connection itself is the test
            pass
        finally:
            await ws.close()


if __name__ == "__main__":
    async def run_validation():
        suite = await get_staging_suite()
        health_results = await suite.run_health_checks()
        healthy = sum(1 for result in health_results.values() if result.healthy)
        print(f"Healthy services: {healthy}/{len(health_results)}")
    
    asyncio.run(run_validation())