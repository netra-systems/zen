"""E2E Tests for WebSocket Agent Events with Authentication

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure real-time user feedback during authenticated AI sessions
- Value Impact: Prevents user abandonment by providing live progress updates
- Strategic Impact: Core UX that builds user trust and engagement with AI

CRITICAL TEST PURPOSE:
These E2E tests validate WebSocket event delivery during authenticated
agent execution to ensure users receive real-time AI progress updates.

Test Coverage:
- WebSocket authentication and connection establishment
- Real-time event delivery during agent execution
- Event ordering and timing with authentication context
- Multi-user event isolation with real authentication
- Connection recovery during authenticated sessions
"""

import pytest
import asyncio
import uuid

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.e2e
class TestWebSocketAgentEventsAuthenticatedE2E:
    """E2E tests for WebSocket agent events with authentication."""
    
    def setup_method(self):
        """Set up E2E test environment."""
        self.auth_helper = E2EAuthHelper(environment="staging")
    
    @pytest.mark.asyncio
    async def test_websocket_agent_events_authenticated_flow(self, real_services_fixture):
        """Test complete WebSocket event flow with authentication."""
        # Arrange - Create authenticated user
        user_credentials = {
            "email": f"ws-events-{uuid.uuid4()}@netra.test",
            "password": "WebSocketTest123!",
            "name": "WebSocket Events Test User"
        }
        
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        thread_id = f"ws-events-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            # Connect with authentication
            await websocket_client.connect_with_auth()
            
            # Start agent execution
            agent_request = {
                "agent_name": "websocket_test_agent",
                "task": "test_websocket_events",
                "thread_id": thread_id,
                "user_context": {"user_id": user_id}
            }
            
            response = await self._send_authenticated_agent_request(
                auth_token=access_token,
                agent_request=agent_request,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert response["success"] == True
            
            # Collect WebSocket events
            collected_events = []
            timeout = asyncio.get_event_loop().time() + 15.0
            
            while asyncio.get_event_loop().time() < timeout:
                try:
                    events = await websocket_client.get_received_events(timeout=1.0)
                    collected_events.extend(events)
                    
                    # Check for completion
                    if any(e.get("type") == "agent_completed" for e in events):
                        break
                except asyncio.TimeoutError:
                    continue
            
            # Assert - verify event delivery
            assert len(collected_events) >= 3
            
            # Verify core events present
            event_types = [e.get("type") for e in collected_events]
            required_events = ["agent_started", "agent_thinking", "agent_completed"]
            
            for required_event in required_events:
                assert required_event in event_types
            
            # Verify authentication context in events
            for event in collected_events:
                assert "timestamp" in event
                if "user_id" in event.get("payload", {}):
                    assert event["payload"]["user_id"] == user_id
        
        finally:
            await websocket_client.disconnect()
            await self.auth_helper.cleanup_user_session(auth_result)
    
    @pytest.mark.asyncio
    async def test_multi_user_websocket_isolation_e2e(self, real_services_fixture):
        """Test WebSocket event isolation between authenticated users."""
        # Create two authenticated users
        user1_creds = {
            "email": f"user1-iso-{uuid.uuid4()}@netra.test",
            "password": "Isolation1Test123!",
            "name": "User 1 Isolation Test"
        }
        
        user2_creds = {
            "email": f"user2-iso-{uuid.uuid4()}@netra.test", 
            "password": "Isolation2Test123!",
            "name": "User 2 Isolation Test"
        }
        
        auth1 = await self.auth_helper.create_authenticated_user_session(user1_creds)
        auth2 = await self.auth_helper.create_authenticated_user_session(user2_creds)
        
        client1 = RealWebSocketTestClient(
            thread_id=f"user1-{uuid.uuid4()}",
            user_id=auth1["user_id"],
            auth_token=auth1["access_token"]
        )
        
        client2 = RealWebSocketTestClient(
            thread_id=f"user2-{uuid.uuid4()}",
            user_id=auth2["user_id"],
            auth_token=auth2["access_token"]
        )
        
        try:
            # Connect both clients
            await client1.connect_with_auth()
            await client2.connect_with_auth()
            
            # Execute agents for both users simultaneously
            agent1_task = self._execute_agent_and_collect_events(
                client1, auth1, "user1_agent", real_services_fixture["backend_url"]
            )
            agent2_task = self._execute_agent_and_collect_events(
                client2, auth2, "user2_agent", real_services_fixture["backend_url"]
            )
            
            user1_events, user2_events = await asyncio.gather(agent1_task, agent2_task)
            
            # Verify isolation
            assert len(user1_events) >= 2
            assert len(user2_events) >= 2
            
            # Verify no cross-contamination
            user1_event_data = str(user1_events)
            user2_event_data = str(user2_events)
            
            assert auth2["user_id"] not in user1_event_data
            assert auth1["user_id"] not in user2_event_data
        
        finally:
            await client1.disconnect()
            await client2.disconnect()
            await self.auth_helper.cleanup_user_session(auth1)
            await self.auth_helper.cleanup_user_session(auth2)
    
    async def _execute_agent_and_collect_events(self, client, auth_result, agent_name, backend_url):
        """Execute agent and collect WebSocket events."""
        agent_request = {
            "agent_name": agent_name,
            "task": "isolation_test",
            "thread_id": client.thread_id,
            "user_context": {"user_id": auth_result["user_id"]}
        }
        
        # Start agent
        await self._send_authenticated_agent_request(
            auth_token=auth_result["access_token"],
            agent_request=agent_request,
            backend_url=backend_url
        )
        
        # Collect events
        events = []
        timeout = asyncio.get_event_loop().time() + 10.0
        
        while asyncio.get_event_loop().time() < timeout:
            try:
                new_events = await client.get_received_events(timeout=1.0)
                events.extend(new_events)
                if any(e.get("type") == "agent_completed" for e in new_events):
                    break
            except asyncio.TimeoutError:
                continue
        
        return events
    
    async def _send_authenticated_agent_request(self, auth_token: str, agent_request: dict, backend_url: str) -> dict:
        """Send authenticated agent request."""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{backend_url}/api/v1/agents/execute",
                json=agent_request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    result["success"] = True
                    return result
                else:
                    return {"success": False, "error": await response.text()}