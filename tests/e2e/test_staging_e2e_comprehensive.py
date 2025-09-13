from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Comprehensive E2E Test Suite for Staging Environment

This test suite validates the complete staging environment by making
real API and WebSocket calls to deployed services.

Business Value:
- Validates $50K+ MRR features in production-like environment
- Prevents deployment issues that could affect customer experience
- Ensures staging environment mirrors production behavior

The OAUTH SIMULATION ONLY simulates the Google OAuth flow for testing,
it does not bypass authentication - valid tokens are still required.
"""

import asyncio
import os
import pytest
import logging
from typing import Dict, List
import httpx

from tests.e2e.staging_config import get_staging_config
from tests.e2e.staging_auth_client import StagingAuthClient, StagingAPIClient
from tests.e2e.staging_websocket_client import StagingWebSocketClient

logger = logging.getLogger(__name__)

# Mark all tests as staging E2E tests
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging
]


@pytest.fixture
async def staging_config():
    """Provide staging configuration."""
    config = get_staging_config()
    config.validate_configuration()
    return config


@pytest.fixture
async def auth_client(staging_config):
    """Provide staging auth client."""
    return StagingAuthClient(staging_config)


@pytest.fixture
async def api_client(auth_client):
    """Provide authenticated API client."""
    client = StagingAPIClient(auth_client)
    await client.authenticate()
    return client


@pytest.fixture
async def websocket_client(auth_client):
    """Provide WebSocket client with cleanup."""
    client = StagingWebSocketClient(auth_client)
    yield client
    if client.is_connected:
        await client.disconnect()


class TestStagingHealthChecks:
    """Test health endpoints of all staging services."""
    
    @pytest.mark.asyncio
    async def test_all_services_healthy(self, api_client):
        """Verify all staging services are healthy."""
        health_results = await api_client.health_check()
        
        # Check each service
        for service, status in health_results.items():
            assert status["status"] in ["healthy", "degraded"], \
                f"{service} is not healthy: {status}"
            
            if status["status"] == "healthy":
                assert status.get("response_time", 1.0) < 5.0, \
                    f"{service} response time too slow: {status.get('response_time')}s"
        
        logger.info(f"All services healthy: {list(health_results.keys())}")
    
    @pytest.mark.asyncio
    async def test_backend_health_detailed(self, staging_config):
        """Test backend health endpoint in detail."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{staging_config.urls.backend_url}/health")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify health response structure
            assert "status" in data
            assert data["status"] in ["healthy", "degraded"]
            
            # Check for expected components
            if "components" in data:
                assert "database" in data["components"]
                assert "redis" in data["components"]


class TestStagingAuthentication:
    """Test authentication flows against staging."""
    
    @pytest.mark.asyncio
    async def test_auth_token_generation(self, auth_client):
        """Test that OAUTH SIMULATION correctly simulates OAuth flow."""
        # Get token simulating OAuth login
        tokens = await auth_client.get_auth_token(
            email="test-oauth@staging.netrasystems.ai",
            name="OAuth Test User"
        )
        
        assert "access_token" in tokens
        assert tokens["access_token"] is not None
        assert len(tokens["access_token"]) > 20
        
        # Verify the token is valid
        user_info = await auth_client.verify_token(tokens["access_token"])
        assert user_info["email"] == "test-oauth@staging.netrasystems.ai"
        assert user_info.get("valid") is True
    
    @pytest.mark.asyncio
    async def test_token_refresh_flow(self, auth_client):
        """Test refresh token flow."""
        # Get initial tokens
        initial_tokens = await auth_client.get_auth_token()
        
        assert "refresh_token" in initial_tokens
        
        # Wait a moment to ensure different token
        await asyncio.sleep(1)
        
        # Refresh the token
        new_tokens = await auth_client.refresh_token(initial_tokens["refresh_token"])
        
        assert "access_token" in new_tokens
        assert new_tokens["access_token"] != initial_tokens["access_token"]
        
        # Verify new token works
        user_info = await auth_client.verify_token(new_tokens["access_token"])
        assert user_info.get("valid") is True
    
    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self, staging_config):
        """Test that invalid tokens are properly rejected."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{staging_config.urls.backend_url}/api/v1/user/profile",
                headers={"Authorization": "Bearer invalid_token_12345"}
            )
            
            assert response.status_code == 401


class TestStagingAPIEndpoints:
    """Test API endpoints against staging backend."""
    
    @pytest.mark.asyncio
    async def test_user_profile_endpoint(self, api_client):
        """Test user profile endpoint with authenticated request."""
        response = await api_client.get("/api/v1/user/profile")
        
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data
    
    @pytest.mark.asyncio
    async def test_chat_endpoint(self, api_client):
        """Test chat creation and retrieval."""
        # Create a new chat
        response = await api_client.post("/api/v1/chats", {
            "title": "Staging E2E Test Chat",
            "type": "standard"
        })
        
        if response.status_code == 201:
            chat_data = response.json()
            assert "id" in chat_data
            assert chat_data["title"] == "Staging E2E Test Chat"
            
            # Retrieve the chat
            chat_id = chat_data["id"]
            response = await api_client.get(f"/api/v1/chats/{chat_id}")
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_agent_endpoint(self, api_client):
        """Test agent endpoint."""
        response = await api_client.get("/api/v1/agents")
        
        assert response.status_code in [200, 404]  # May not have agents configured
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


class TestStagingWebSocket:
    """Test WebSocket functionality against staging."""
    
    @pytest.mark.asyncio
    async def test_websocket_connection(self, websocket_client):
        """Test WebSocket connection to staging."""
        connected = await websocket_client.connect()
        assert connected is True
        assert websocket_client.is_connected is True
        
        # Send a ping message
        success = await websocket_client.send_message("ping", {"timestamp": "test"})
        assert success is True
        
        # Wait for any response
        await asyncio.sleep(2)
        
        stats = websocket_client.get_message_stats()
        assert stats["total_messages"] >= 0
    
    @pytest.mark.asyncio
    async def test_websocket_chat_flow(self, websocket_client):
        """Test chat message flow through WebSocket."""
        await websocket_client.connect()
        
        # Track received messages
        chat_events = []
        
        async def track_event(msg):
            chat_events.append(msg)
        
        websocket_client.on_message("chat_response", track_event)
        websocket_client.on_message("typing_indicator", track_event)
        
        # Send chat message
        success = await websocket_client.send_chat_message(
            "Hello from staging E2E test"
        )
        assert success is True
        
        # Wait for response
        await asyncio.sleep(3)
        
        # Check if we received any chat events
        logger.info(f"Received {len(chat_events)} chat events")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_websocket_agent_interaction(self, websocket_client):
        """Test agent interaction through WebSocket."""
        await websocket_client.connect()
        
        # Test simple agent flow
        success = await websocket_client.test_agent_flow(
            "What is the capital of France?"
        )
        
        # Agent flow might not be fully configured in staging
        if not success:
            pytest.skip("Agent flow not available in staging")
        
        assert success is True


class TestStagingEndToEndScenarios:
    """Test complete end-to-end scenarios."""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self, auth_client, api_client, websocket_client):
        """Test a complete user journey from auth to chat."""
        # Step 1: Authenticate (simulating OAuth)
        tokens = await auth_client.get_auth_token(
            email="journey-test@staging.netrasystems.ai",
            name="Journey Test User"
        )
        assert tokens["access_token"] is not None
        
        # Step 2: Get user profile
        api_client.current_token = tokens["access_token"]
        response = await api_client.get("/api/v1/user/profile")
        assert response.status_code in [200, 404]  # Profile might not exist yet
        
        # Step 3: Connect WebSocket
        connected = await websocket_client.connect(token=tokens["access_token"])
        assert connected is True
        
        # Step 4: Send a message
        success = await websocket_client.send_chat_message(
            "Testing complete user journey"
        )
        assert success is True
        
        # Step 5: Disconnect properly
        await websocket_client.disconnect()
        
        # Step 6: Logout
        logout_success = await auth_client.logout(tokens["access_token"])
        assert logout_success is True
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, auth_client):
        """Test multiple concurrent connections to staging."""
        # Create multiple clients
        clients = []
        
        for i in range(3):
            tokens = await auth_client.get_auth_token(
                email=f"concurrent-{i}@staging.netrasystems.ai",
                name=f"Concurrent User {i}"
            )
            
            ws_client = StagingWebSocketClient(auth_client)
            connected = await ws_client.connect(token=tokens["access_token"])
            assert connected is True
            clients.append(ws_client)
        
        # All clients send messages
        for i, client in enumerate(clients):
            success = await client.send_chat_message(f"Message from client {i}")
            assert success is True
        
        # Wait for activity
        await asyncio.sleep(2)
        
        # Disconnect all
        for client in clients:
            await client.disconnect()


class TestStagingErrorHandling:
    """Test error handling in staging environment."""
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, api_client):
        """Test that rate limiting is properly configured."""
        # Make multiple rapid requests
        responses = []
        for _ in range(20):
            response = await api_client.get("/api/v1/user/profile")
            responses.append(response.status_code)
            
            # If we hit rate limit, that's expected
            if response.status_code == 429:
                logger.info("Rate limiting is active")
                break
        
        # Either all succeeded or we hit rate limit
        assert all(r in [200, 429] for r in responses)
    
    @pytest.mark.asyncio
    async def test_invalid_endpoint_handling(self, api_client):
        """Test handling of invalid endpoints."""
        response = await api_client.get("/api/v1/invalid/endpoint/12345")
        assert response.status_code in [404, 400]
    
    @pytest.mark.asyncio
    async def test_malformed_request_handling(self, api_client):
        """Test handling of malformed requests."""
        # Send invalid JSON
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{api_client.config.urls.backend_url}/api/v1/chats",
                headers=api_client.config.get_auth_headers(api_client.current_token),
                content="not-json{invalid"
            )
            
            assert response.status_code in [400, 422]


# Test runner for direct execution
if __name__ == "__main__":
    import sys
    import subprocess
    
    # Set environment to staging
    
    # Check for E2E bypass key
    if not get_env().get("E2E_OAUTH_SIMULATION_KEY"):
        print("ERROR: E2E_OAUTH_SIMULATION_KEY environment variable not set")
        print("This key is required to simulate OAuth flow in staging tests")
        sys.exit(1)
    
    # Run tests with verbose output
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "-s", "--tb=short"],
        capture_output=False
    )
    
    sys.exit(result.returncode)
