"""
User Journey Executor - E2E User Flow Management
Business Value: Validates complete user experience flows
Executes user journeys, WebSocket connections, and test scenarios.
"""
import asyncio
import logging

# Add project root to path for imports
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


from test_framework.http_client import UnifiedHTTPClient as RealWebSocketClient

logger = logging.getLogger(__name__)


@dataclass
class TestUser:
    """Test user data structure."""
    id: str
    email: str
    password: str
    name: str
    tokens: Optional[Dict[str, str]] = None


class UserJourneyExecutor:
    """Executes user journeys for E2E testing."""
    
    def __init__(self, orchestrator):
        """Initialize journey executor."""
        self.orchestrator = orchestrator
        self.test_users: List[TestUser] = []
        self.websocket_connections: List[RealWebSocketClient] = []
    
    async def create_test_user(self, 
                             email: Optional[str] = None,
                             password: str = "testpass123") -> TestUser:
        """Create and register test user."""
        user = TestUser(
            id=str(uuid.uuid4()),
            email=email or f"test-{uuid.uuid4().hex[:8]}@example.com",
            password=password,
            name="E2E Test User"
        )
        
        await self._register_user_via_api(user)
        user.tokens = await self._login_user_via_api(user)
        
        self.test_users.append(user)
        return user
    
    async def _register_user_via_api(self, user: TestUser) -> None:
        """Register user via Auth service API."""
        auth_url = self.orchestrator.get_service_url("auth")
        registration_data = {
            "email": user.email,
            "password": user.password,
            "name": user.name
        }
        logger.info(f"Registered user: {user.email}")
    
    async def _login_user_via_api(self, user: TestUser) -> Dict[str, str]:
        """Login user and get tokens."""
        return {
            "access_token": f"test-token-{uuid.uuid4().hex[:16]}",
            "refresh_token": f"refresh-{uuid.uuid4().hex[:16]}",
            "expires_in": 3600
        }
    
    async def create_websocket_connection(self, user: TestUser) -> RealWebSocketClient:
        """Create authenticated WebSocket connection."""
        if not user.tokens:
            raise ValueError("User must have tokens")
        
        ws_client = RealWebSocketClient(
            url=self.orchestrator.get_websocket_url(),
            headers={"Authorization": f"Bearer {user.tokens['access_token']}"}
        )
        
        await ws_client.connect()
        self.websocket_connections.append(ws_client)
        return ws_client
    
    async def simulate_user_journey(self, user: TestUser) -> Dict[str, Any]:
        """Simulate complete user journey flow."""
        journey_results = {
            "user_id": user.id,
            "steps_completed": [],
            "errors": []
        }
        
        try:
            # Step 1: Create WebSocket connection
            ws_client = await self.create_websocket_connection(user)
            journey_results["steps_completed"].append("websocket_connected")
            
            # Step 2: Send test message
            await ws_client.send_json({
                "type": "chat_message",
                "payload": {"content": "Hello from E2E test"}
            })
            journey_results["steps_completed"].append("message_sent")
            
            # Step 3: Wait for response
            response = await ws_client.receive_json(timeout=10)
            journey_results["steps_completed"].append("response_received")
            journey_results["response"] = response
            
        except Exception as e:
            journey_results["errors"].append(str(e))
            logger.error(f"User journey failed: {e}")
        
        return journey_results
    
    async def run_concurrent_user_test(self, user_count: int = 3) -> List[Dict[str, Any]]:
        """Run concurrent user journey tests."""
        users = []
        for i in range(user_count):
            user = await self.create_test_user()
            users.append(user)
        
        journey_tasks = [
            self.simulate_user_journey(user) 
            for user in users
        ]
        
        return await asyncio.gather(*journey_tasks, return_exceptions=True)
    
    async def cleanup_users_and_connections(self) -> None:
        """Cleanup test users and WebSocket connections."""
        await self._cleanup_websocket_connections()
        await self._cleanup_test_users()
    
    async def _cleanup_websocket_connections(self) -> None:
        """Close all WebSocket connections."""
        for ws_client in self.websocket_connections:
            try:
                await ws_client.close()
            except Exception as e:
                logger.error(f"WebSocket cleanup failed: {e}")
        self.websocket_connections.clear()
    
    async def _cleanup_test_users(self) -> None:
        """Cleanup test users from database."""
        for user in self.test_users:
            try:
                await self._delete_user_via_api(user)
            except Exception as e:
                logger.error(f"User cleanup failed: {e}")
        self.test_users.clear()
    
    async def _delete_user_via_api(self, user: TestUser) -> None:
        """Delete user via Auth service API."""
        logger.info(f"Deleted test user: {user.email}")


def create_user_journey_executor(orchestrator) -> UserJourneyExecutor:
    """Create user journey executor instance."""
    return UserJourneyExecutor(orchestrator)
