"""Concurrent User Isolation Manager

Manages concurrent user sessions with complete isolation testing.
Split from main test file to maintain 450-line architectural compliance.

Business Value: Multi-tenant security and data isolation validation
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from tests.e2e.real_websocket_client import RealWebSocketClient
from tests.e2e.reconnection_test_helpers import create_test_token


class ConcurrentUserIsolationManager:
    """Manages concurrent user sessions with complete isolation."""
    
    def __init__(self, client_factory):
        """Initialize isolation manager."""
        self.factory = client_factory
        self.user_sessions: Dict[str, Dict[str, Any]] = {}
        self.concurrent_clients: List[RealWebSocketClient] = []
    
    async def setup_concurrent_users(self, user_count: int = 10) -> List[Dict[str, Any]]:
        """Setup concurrent user sessions with isolation."""
        users = []
        for i in range(user_count):
            user_data = await self._create_isolated_user(i)
            users.append(user_data)
        return users
    
    async def _create_isolated_user(self, index: int) -> Dict[str, Any]:
        """Create isolated user with unique session."""
        user_id = f"concurrent_user_{index}_{str(uuid.uuid4())[:8]}"
        session_data = {
            "user_id": user_id,
            "session_id": f"session_{user_id}",
            "budget": 10000 + (index * 1000),  # Unique budget per user
            "preferences": {"focus": f"optimization_type_{index}"},
            "sensitive_data": f"secret_{user_id}_{str(uuid.uuid4())}"
        }
        
        self.user_sessions[user_id] = session_data
        return session_data
    
    async def start_concurrent_sessions(self, users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Start all user sessions concurrently."""
        tasks = []
        for user in users:
            task = self._start_isolated_session(user)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return self._process_concurrent_results(results, users)
    
    async def _start_isolated_session(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Start isolated session for single user."""
        ws_url = f"ws://localhost:8000/ws"
        client = self.factory.create_websocket_client(ws_url)
        self.concurrent_clients.append(client)
        
        auth_token = create_test_token(user["user_id"])
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        connected = await client.connect(headers)
        if not connected:
            return {"error": "Connection failed", "user": user["user_id"]}
        
        return await self._execute_isolated_workflow(client, user)
    
    async def _execute_isolated_workflow(self, client: RealWebSocketClient, user: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete workflow for isolated user."""
        message = self._create_user_message(user)
        
        await client.send(message)
        response = await client.receive()
        
        return self._build_session_result(user, response)
    
    def _create_user_message(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Create user-specific message for workflow."""
        return {
            "type": "chat_message",
            "content": f"Analyze budget of ${user['budget']} for {user['preferences']['focus']}",
            "user_data": user["sensitive_data"],
            "session_id": user["session_id"]
        }
    
    def _build_session_result(self, user: Dict[str, Any], response: Dict[str, Any]) -> Dict[str, Any]:
        """Build session result with isolation validation."""
        return {
            "user_id": user["user_id"],
            "session_id": user["session_id"], 
            "expected_budget": user["budget"],
            "expected_data": user["sensitive_data"],
            "response": response,
            "isolation_key": f"isolation_{user['session_id']}"
        }
    
    def _process_concurrent_results(self, results: List[Any], users: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process concurrent results and filter exceptions."""
        processed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed.append({"error": str(result), "user_index": i})
            elif result is not None:
                processed.append(result)
        return processed
    
    def validate_complete_isolation(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate complete isolation between all user sessions."""
        user_ids = [r.get("user_id") for r in results if r.get("user_id")]
        session_ids = [r.get("session_id") for r in results if r.get("session_id")]
        
        isolation_validation = {
            "unique_users": len(set(user_ids)) == len(user_ids),
            "unique_sessions": len(set(session_ids)) == len(session_ids),
            "no_cross_contamination": self._validate_no_contamination(results),
            "total_users": len(user_ids),
            "successful_sessions": len([r for r in results if not r.get("error")])
        }
        
        return isolation_validation
    
    def _validate_no_contamination(self, results: List[Dict[str, Any]]) -> bool:
        """Validate no data contamination between users."""
        for result in results:
            if result.get("error"):
                continue
                
            expected_data = result.get("expected_data")
            response_data = result.get("response", {}).get("user_data")
            
            if expected_data and response_data and expected_data != response_data:
                return False
        
        return True
    
    async def cleanup_concurrent_sessions(self) -> None:
        """Cleanup all concurrent client sessions."""
        cleanup_tasks = []
        for client in self.concurrent_clients:
            cleanup_tasks.append(client.close())
        
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        self.concurrent_clients.clear()
