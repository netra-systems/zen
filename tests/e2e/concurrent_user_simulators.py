"""Concurrent User Simulators and WebSocket Management

Business Value Justification (BVJ):
- Segment: Enterprise (concurrent user simulation required)
- Business Goal: Simulate realistic concurrent user behavior
- Value Impact: Validates enterprise-grade concurrency handling
- Revenue Impact: Protects $100K+ ARR from concurrency issues

ARCHITECTURAL COMPLIANCE:
- File size: <300 lines (MANDATORY)
- Function size: <8 lines each (MANDATORY)
- Modular design with focused responsibilities
"""

import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional

from tests.e2e.concurrent_user_models import (
    ConcurrentUserMetrics, UserSession, MockServiceManager, MockWebSocketClient, IsolationValidator,
    ConcurrentUserMetrics,
    UserSession,
    MockServiceManager,
    MockWebSocketClient,
    IsolationValidator
)


class ConcurrentUserSimulator:
    """Simulates concurrent users with isolated sessions"""
    
    def __init__(self):
        self.service_manager = MockServiceManager()
        self.metrics = ConcurrentUserMetrics()
        self.auth_base_url = "http://localhost:8001"
        self.backend_base_url = "http://localhost:8000" 
        self.websocket_url = "ws://localhost:8000/ws"
    
    async def create_concurrent_users(self, user_count: int) -> List[UserSession]:
        """Create multiple user sessions concurrently"""
        user_tasks = []
        for i in range(user_count):
            user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:6]}"
            task = asyncio.create_task(self._create_single_user(user_id))
            user_tasks.append(task)
        
        users = await asyncio.gather(*user_tasks, return_exceptions=True)
        return [u for u in users if isinstance(u, UserSession)]
    
    async def _create_single_user(self, user_id: str) -> UserSession:
        """Create and authenticate single user"""
        email = f"{user_id}@concurrent.test"
        user = UserSession(user_id=user_id, email=email)
        
        # Authenticate user via mock endpoint
        token_result = await self._authenticate_user(user)
        if token_result:
            user.access_token = token_result
            self.metrics.successful_logins += 1
        
        return user
    
    async def _authenticate_user(self, user: UserSession) -> Optional[str]:
        """Mock authenticate user and return access token"""
        await asyncio.sleep(0.05)  # Simulate auth time
        # Generate unique token per user
        return f"mock_token_{user.user_id}_{uuid.uuid4().hex[:8]}"


class ConcurrentWebSocketManager:
    """Manages concurrent WebSocket connections and messaging"""
    
    def __init__(self, simulator: ConcurrentUserSimulator):
        self.simulator = simulator
        self.active_connections: Dict[str, MockWebSocketClient] = {}
        self.message_responses: Dict[str, List[Dict]] = {}
    
    async def establish_all_connections(self, users: List[UserSession]) -> int:
        """Establish WebSocket connections for all users concurrently"""
        connection_tasks = []
        for user in users:
            if user.access_token:
                task = asyncio.create_task(self._connect_user_websocket(user))
                connection_tasks.append(task)
        
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        successful_connections = sum(1 for r in results if r is True)
        self.simulator.metrics.successful_connections = successful_connections
        return successful_connections
    
    async def _connect_user_websocket(self, user: UserSession) -> bool:
        """Mock establish WebSocket connection for single user"""
        try:
            ws_client = MockWebSocketClient(self.simulator.websocket_url, user.user_id)
            headers = {"Authorization": f"Bearer {user.access_token}"}
            
            connected = await ws_client.connect(headers)
            if connected:
                user.websocket_client = ws_client
                self.active_connections[user.user_id] = ws_client
                return True
        except Exception:
            pass
        return False
    
    async def send_concurrent_messages(self, users: List[UserSession]) -> Dict[str, Any]:
        """Send messages from all users concurrently"""
        message_tasks = []
        for user in users:
            if user.websocket_client:
                task = asyncio.create_task(self._send_user_message(user))
                message_tasks.append(task)
        
        results = await asyncio.gather(*message_tasks, return_exceptions=True)
        return self._analyze_message_results(results, users)
    
    async def _send_user_message(self, user: UserSession) -> Dict[str, Any]:
        """Send unique message for single user and wait for response"""
        start_time = time.time()
        unique_content = f"Help me optimize AI costs for user {user.user_id}"
        
        message = {
            "type": "chat_message",
            "content": unique_content,
            "thread_id": user.thread_id,
            "user_id": user.user_id,
            "timestamp": time.time()
        }
        
        try:
            # Send message
            sent = await user.websocket_client.send(message)
            user.sent_messages.append(message)
            
            if sent:
                # Wait for response
                response = await user.websocket_client.receive(timeout=3.0)
                response_time = time.time() - start_time
                
                if response:
                    user.received_responses.append(response)
                    self.simulator.metrics.successful_messages += 1
                    self.simulator.metrics.response_times.append(response_time)
                    return {"success": True, "response": response, "time": response_time}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "No response received"}
    
    def _analyze_message_results(self, results: List[Any], users: List[UserSession]) -> Dict[str, Any]:
        """Analyze concurrent messaging results"""
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        return {
            "total_messages": len(results),
            "successful_messages": successful,
            "success_rate": (successful / len(results)) * 100 if results else 0,
            "users_with_responses": len([u for u in users if u.received_responses])
        }
