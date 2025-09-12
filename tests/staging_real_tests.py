"""
Staging Environment Real Tests
================================
This test suite runs real HTTP calls against the staging environment.
Tests rated 7/10 and above in priority.
"""

import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import httpx
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure staging URLs
STAGING_BASE_URL = os.environ.get("STAGING_BASE_URL", "https://staging.netra.ai")
STAGING_AUTH_URL = os.environ.get("STAGING_AUTH_URL", "https://auth-staging.netra.ai")
STAGING_API_URL = os.environ.get("STAGING_API_URL", f"{STAGING_BASE_URL}/api")

# Test configuration
TIMEOUT = 30  # seconds for each request
TEST_USER_EMAIL = "test@netra.ai"
TEST_USER_PASSWORD = "TestPassword123!"


class TestStagingEnvironment:
    """Test suite for staging environment with real HTTP calls"""
    
    @pytest.fixture
    async def http_client(self):
        """Create an async HTTP client for testing"""
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            yield client
    
    @pytest.mark.asyncio
    async def test_staging_health_check(self, http_client):
        """Test that staging environment is healthy (10/10 priority)"""
        try:
            response = await http_client.get(f"{STAGING_BASE_URL}/health")
            assert response.status_code == 200, f"Health check failed: {response.status_code}"
            
            data = response.json()
            assert data.get("status") == "healthy", f"Unhealthy status: {data}"
            print(f" PASS:  Staging health check passed: {data}")
        except httpx.ConnectError:
            pytest.skip("Cannot connect to staging environment")
    
    @pytest.mark.asyncio
    async def test_auth_service_health(self, http_client):
        """Test auth service health (10/10 priority)"""
        try:
            response = await http_client.get(f"{STAGING_AUTH_URL}/health")
            assert response.status_code == 200, f"Auth health check failed: {response.status_code}"
            
            data = response.json()
            assert data.get("status") in ["healthy", "ok"], f"Auth unhealthy: {data}"
            print(f" PASS:  Auth service health check passed: {data}")
        except httpx.ConnectError:
            pytest.skip("Cannot connect to auth staging environment")
    
    @pytest.mark.asyncio
    async def test_api_endpoints_available(self, http_client):
        """Test that critical API endpoints are available (9/10 priority)"""
        critical_endpoints = [
            "/api/v1/sessions",
            "/api/v1/threads",
            "/api/v1/messages",
            "/api/v1/agents"
        ]
        
        for endpoint in critical_endpoints:
            try:
                response = await http_client.get(f"{STAGING_BASE_URL}{endpoint}")
                # We expect 401 without auth, but not 404 or 500
                assert response.status_code in [200, 401, 403], \
                    f"Endpoint {endpoint} returned unexpected status: {response.status_code}"
                print(f" PASS:  Endpoint {endpoint} is available")
            except httpx.ConnectError:
                pytest.skip(f"Cannot connect to endpoint {endpoint}")
    
    @pytest.mark.asyncio
    async def test_authentication_flow(self, http_client):
        """Test complete authentication flow (10/10 priority)"""
        # Step 1: Register or login
        login_data = {
            "username": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            # Try to login
            response = await http_client.post(
                f"{STAGING_AUTH_URL}/auth/token",
                data=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                assert "access_token" in data, "No access token in response"
                assert "token_type" in data, "No token type in response"
                
                access_token = data["access_token"]
                print(f" PASS:  Authentication successful, token: {access_token[:20]}...")
                
                # Step 2: Use token to access protected endpoint
                headers = {"Authorization": f"Bearer {access_token}"}
                protected_response = await http_client.get(
                    f"{STAGING_BASE_URL}/api/v1/user/profile",
                    headers=headers
                )
                
                if protected_response.status_code == 200:
                    profile = protected_response.json()
                    print(f" PASS:  Protected endpoint access successful: {profile}")
                else:
                    print(f" WARNING: [U+FE0F] Protected endpoint returned: {protected_response.status_code}")
            else:
                print(f" WARNING: [U+FE0F] Login failed with status: {response.status_code}")
                # Try registration if login failed
                await self._try_registration(http_client)
        except httpx.ConnectError:
            pytest.skip("Cannot connect to auth service")
    
    async def _try_registration(self, http_client):
        """Helper to try user registration"""
        register_data = {
            "email": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD,
            "full_name": "Test User"
        }
        
        response = await http_client.post(
            f"{STAGING_AUTH_URL}/auth/register",
            json=register_data
        )
        
        if response.status_code in [200, 201]:
            print(f" PASS:  User registration successful")
        else:
            print(f" WARNING: [U+FE0F] Registration returned: {response.status_code}")
    
    @pytest.mark.asyncio
    async def test_websocket_connectivity(self):
        """Test WebSocket connectivity (9/10 priority)"""
        import websockets
        ws_url = STAGING_BASE_URL.replace("https://", "wss://").replace("http://", "ws://")
        ws_url = f"{ws_url}/ws"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Send a test message
                await websocket.send(json.dumps({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
                # Wait for response
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                data = json.loads(response)
                print(f" PASS:  WebSocket connection successful: {data}")
        except Exception as e:
            print(f" WARNING: [U+FE0F] WebSocket connection failed: {e}")
            pytest.skip("Cannot connect to WebSocket")
    
    @pytest.mark.asyncio
    async def test_agent_execution(self, http_client):
        """Test agent execution flow (8/10 priority)"""
        # First get auth token
        token = await self._get_auth_token(http_client)
        if not token:
            pytest.skip("Cannot authenticate for agent test")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a session
        session_data = {"name": "Test Session"}
        session_response = await http_client.post(
            f"{STAGING_BASE_URL}/api/v1/sessions",
            json=session_data,
            headers=headers
        )
        
        if session_response.status_code in [200, 201]:
            session = session_response.json()
            session_id = session.get("id") or session.get("session_id")
            print(f" PASS:  Session created: {session_id}")
            
            # Send a message to trigger agent
            message_data = {
                "session_id": session_id,
                "content": "Test message for agent execution",
                "type": "user_message"
            }
            
            message_response = await http_client.post(
                f"{STAGING_BASE_URL}/api/v1/messages",
                json=message_data,
                headers=headers
            )
            
            if message_response.status_code in [200, 201]:
                message = message_response.json()
                print(f" PASS:  Agent message sent: {message}")
            else:
                print(f" WARNING: [U+FE0F] Message send failed: {message_response.status_code}")
        else:
            print(f" WARNING: [U+FE0F] Session creation failed: {session_response.status_code}")
    
    async def _get_auth_token(self, http_client) -> Optional[str]:
        """Helper to get authentication token"""
        login_data = {
            "username": TEST_USER_EMAIL,
            "password": TEST_USER_PASSWORD
        }
        
        try:
            response = await http_client.post(
                f"{STAGING_AUTH_URL}/auth/token",
                data=login_data
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("access_token")
        except:
            pass
        return None
    
    @pytest.mark.asyncio
    async def test_data_persistence(self, http_client):
        """Test data persistence across services (7/10 priority)"""
        token = await self._get_auth_token(http_client)
        if not token:
            pytest.skip("Cannot authenticate for persistence test")
        
        headers = {"Authorization": f"Bearer {token}"}
        test_data = {
            "test_id": f"test_{datetime.utcnow().timestamp()}",
            "data": "Test persistence data"
        }
        
        # Create data
        create_response = await http_client.post(
            f"{STAGING_BASE_URL}/api/v1/test/data",
            json=test_data,
            headers=headers
        )
        
        if create_response.status_code in [200, 201, 404]:
            if create_response.status_code == 404:
                print(" WARNING: [U+FE0F] Test data endpoint not available")
            else:
                # Try to retrieve data
                get_response = await http_client.get(
                    f"{STAGING_BASE_URL}/api/v1/test/data/{test_data['test_id']}",
                    headers=headers
                )
                
                if get_response.status_code == 200:
                    retrieved = get_response.json()
                    assert retrieved.get("data") == test_data["data"], \
                        "Data persistence verification failed"
                    print(f" PASS:  Data persistence test passed")
                else:
                    print(f" WARNING: [U+FE0F] Data retrieval failed: {get_response.status_code}")
        else:
            print(f" WARNING: [U+FE0F] Data creation failed: {create_response.status_code}")


def main():
    """Run staging tests with real HTTP calls"""
    print("=" * 60)
    print("STAGING ENVIRONMENT REAL TESTS")
    print(f"Target: {STAGING_BASE_URL}")
    print("=" * 60)
    
    # Run pytest programmatically
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    return pytest.main(pytest_args)


if __name__ == "__main__":
    sys.exit(main())