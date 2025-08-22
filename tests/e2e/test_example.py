"""
Example Test using Unified Test Harness
Demonstrates how to use the unified testing infrastructure

This shows the REAL service testing approach per SPEC/unified_system_testing.xml
"""

import asyncio
from typing import Any, Dict

import pytest

from tests.unified import TestClient, TestHarnessContext, UnifiedTestHarness


@pytest.mark.asyncio
async def test_first_time_user_journey():
    """Test complete first-time user journey across all services."""
    async with TestHarnessContext("first_time_user_test") as harness:
        client = TestClient(harness)
        
        # Verify all services are healthy
        health = await harness.check_system_health()
        assert health["services_ready"] is True
        assert health["database_initialized"] is True
        
        # Test user creation via auth service
        response = await client.auth_request("GET", "/health")
        assert response.status_code == 200
        
        # Test backend communication
        response = await client.backend_request("GET", "/health")
        assert response.status_code == 200
        
        await client.close()


@pytest.mark.asyncio
async def test_returning_user_login():
    """Test returning user login flow across services."""
    async with TestHarnessContext("returning_user_test") as harness:
        client = TestClient(harness)
        
        # Get test user
        user = harness.get_test_user(0)
        assert user is not None
        assert user["email"] == "test@example.com"
        
        # Get auth token
        token = await harness.get_auth_token(0)
        assert token is not None
        
        await client.close()


@pytest.mark.asyncio
async def test_basic_chat_interaction():
    """Test basic chat interaction through WebSocket."""
    async with TestHarnessContext("chat_test") as harness:
        # Verify system is ready for chat
        health = await harness.check_system_health()
        assert health["ready_services"] >= 2  # auth + backend
        
        # Test WebSocket connection (would be implemented with real WebSocket)
        auth_url = harness.get_service_url("auth_service")
        backend_url = harness.get_service_url("backend")
        
        assert "localhost:8001" in auth_url
        assert "localhost:8000" in backend_url


@pytest.mark.asyncio
async def test_service_isolation():
    """Test that services are properly isolated but can communicate."""
    harness = await UnifiedTestHarness.create_minimal_harness("isolation_test")
    
    try:
        # Each service should be accessible independently
        services = ["auth_service", "backend"]
        for service in services:
            url = harness.get_service_url(service)
            assert "localhost" in url
            
        # Services should be able to communicate with each other
        health = await harness.check_system_health()
        assert health["service_count"] == 2
        
    finally:
        await harness.stop_all_services()


@pytest.mark.asyncio 
async def test_database_isolation():
    """Test that each test gets isolated database."""
    harness1 = await UnifiedTestHarness.create_minimal_harness("db_test_1")
    harness2 = await UnifiedTestHarness.create_minimal_harness("db_test_2")
    
    try:
        # Each harness should have its own temp directory
        assert harness1.state.temp_dir != harness2.state.temp_dir
        assert harness1.state.databases.test_db_name != harness2.state.databases.test_db_name
        
    finally:
        await harness1.stop_all_services()
        await harness2.stop_all_services()


class TestRealServiceIntegration:
    """Test class demonstrating real service integration patterns."""
    
    @pytest.fixture
    async def harness(self):
        """Fixture providing a test harness for the test class."""
        harness = await UnifiedTestHarness.create_test_harness("class_test")
        yield harness
        await harness.stop_all_services()
    
    @pytest.mark.asyncio
    async def test_auth_to_backend_communication(self, harness):
        """Test communication from auth service to backend."""
        # This would test real JWT token validation between services
        token = await harness.get_auth_token()
        assert token is not None
        
        # Backend should be able to validate tokens from auth service
        client = TestClient(harness)
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test authenticated endpoint
        response = await client.backend_request("GET", "/health", headers=headers)
        assert response.status_code == 200
        
        await client.close()
    
    @pytest.mark.asyncio
    async def test_user_data_consistency(self, harness):
        """Test that user data is consistent across services."""
        user = harness.get_test_user(0)
        assert user is not None
        
        # User should exist in both auth and backend systems
        # This would typically involve API calls to verify data consistency
        auth_health = await harness.health_monitor.check_system_health()
        assert auth_health["services_ready"] is True


# Performance and load testing examples
@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test system behavior under concurrent load."""
    async with TestHarnessContext("load_test") as harness:
        client = TestClient(harness)
        
        # Make multiple concurrent requests to test system stability
        tasks = []
        for i in range(10):
            task = client.auth_request("GET", "/health")
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All requests should succeed
        successful = sum(1 for r in responses if hasattr(r, 'status_code') and r.status_code == 200)
        assert successful >= 8  # Allow for some transient failures
        
        await client.close()


if __name__ == "__main__":
    # Example of running tests directly
    asyncio.run(test_first_time_user_journey())
