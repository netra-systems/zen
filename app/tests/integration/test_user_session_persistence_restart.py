"""
User Session Persistence Across Restarts Integration Test

Business Value Justification (BVJ):
- Segment: ALL (critical for user experience)
- Business Goal: User Retention & Experience
- Value Impact: Prevents user session loss during deployments/restarts
- Revenue Impact: Protects $18K MRR from session-related churn

Tests session creation, service restart handling, session validity
after restart, and data consistency across restarts.
"""

import asyncio
import time
import pytest
from typing import Dict, List, Optional, Any
import httpx
import redis.asyncio as redis
from datetime import datetime, timedelta

from test_framework.real_service_helper import RealServiceHelper
from app.services.session.session_manager import SessionManager


class UserSessionPersistenceTest:
    """Test user session persistence across service restarts."""
    
    def __init__(self):
        self.auth_url = "http://localhost:8001"
        self.backend_url = "http://localhost:8000"
        self.ws_url = "ws://localhost:8000/ws"
        self.service_helper = RealServiceHelper()
        self.redis_client: Optional[redis.Redis] = None
        self.session_manager = SessionManager()
        self.active_sessions: List[Dict[str, Any]] = []
    
    async def setup(self):
        """Setup test environment."""
        # Ensure services are running
        await self.service_helper.ensure_services_running([
            "auth_service",
            "backend",
            "redis"
        ])
        
        # Connect to Redis for session monitoring
        self.redis_client = redis.from_url("redis://localhost:6379")
        
        # Clear any existing test sessions
        await self._clear_test_sessions()
    
    async def teardown(self):
        """Cleanup after tests."""
        if self.redis_client:
            await self.redis_client.close()
        
        # Restore services to normal state
        await self.service_helper.ensure_services_running([
            "auth_service",
            "backend"
        ])
    
    async def _clear_test_sessions(self):
        """Clear test sessions from Redis."""
        pattern = "session:test_*"
        cursor = 0
        
        while True:
            cursor, keys = await self.redis_client.scan(
                cursor, 
                match=pattern, 
                count=100
            )
            
            if keys:
                await self.redis_client.delete(*keys)
            
            if cursor == 0:
                break
    
    async def create_authenticated_session(self, user_id: str) -> Dict[str, Any]:
        """Create an authenticated user session."""
        email = f"{user_id}@persistence.test"
        
        async with httpx.AsyncClient() as client:
            # Register user
            await client.post(
                f"{self.auth_url}/auth/register",
                json={
                    "email": email,
                    "password": "test_password",
                    "user_id": user_id
                }
            )
            
            # Authenticate
            auth_response = await client.post(
                f"{self.auth_url}/auth/token",
                json={
                    "username": email,
                    "password": "test_password",
                    "grant_type": "password"
                }
            )
            
            if auth_response.status_code != 200:
                raise ValueError(f"Authentication failed: {auth_response.text}")
            
            token_data = auth_response.json()
            
            # Create session in backend
            session_response = await client.post(
                f"{self.backend_url}/api/v1/session/create",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
                json={"user_id": user_id}
            )
            
            if session_response.status_code == 200:
                session_data = session_response.json()
            else:
                session_data = {"session_id": f"session_{user_id}"}
            
            return {
                "user_id": user_id,
                "email": email,
                "token": token_data["access_token"],
                "refresh_token": token_data.get("refresh_token"),
                "session_id": session_data.get("session_id"),
                "created_at": datetime.now().isoformat()
            }
    
    async def validate_session_active(self, token: str) -> bool:
        """Validate that a session is active."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.backend_url}/api/v1/session/validate",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            return response.status_code == 200
    
    async def perform_authenticated_action(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Perform an authenticated action with session."""
        async with httpx.AsyncClient() as client:
            # Try to access protected endpoint
            response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers={"Authorization": f"Bearer {session['token']}"}
            )
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "data": response.json() if response.status_code == 200 else None
            }
    
    async def restart_auth_service(self, graceful: bool = True):
        """Restart auth service."""
        if graceful:
            # Graceful shutdown
            await self.service_helper.stop_service("auth_service", graceful=True)
            await asyncio.sleep(2)
            await self.service_helper.start_service("auth_service")
        else:
            # Force restart
            await self.service_helper.force_restart_service("auth_service")
    
    async def restart_backend_service(self, graceful: bool = True):
        """Restart backend service."""
        if graceful:
            await self.service_helper.stop_service("backend", graceful=True)
            await asyncio.sleep(2)
            await self.service_helper.start_service("backend")
        else:
            await self.service_helper.force_restart_service("backend")
    
    async def get_session_from_redis(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis."""
        session_key = f"session:{session_id}"
        session_data = await self.redis_client.get(session_key)
        
        if session_data:
            import json
            return json.loads(session_data)
        return None
    
    async def get_user_data(self, user_id: str, token: str) -> Dict[str, Any]:
        """Get user data from backend."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.backend_url}/api/v1/user/{user_id}",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if response.status_code == 200:
                return response.json()
            return {}
    
    async def simulate_user_activity(self, sessions: List[Dict[str, Any]]):
        """Simulate user activity on sessions."""
        activities = []
        
        for session in sessions:
            async with httpx.AsyncClient() as client:
                # Simulate different activities
                activity_response = await client.post(
                    f"{self.backend_url}/api/v1/activity/log",
                    headers={"Authorization": f"Bearer {session['token']}"},
                    json={
                        "user_id": session["user_id"],
                        "activity": "test_activity",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
                activities.append({
                    "user_id": session["user_id"],
                    "success": activity_response.status_code == 200
                })
        
        return activities
    
    async def test_websocket_reconnection(self, session: Dict[str, Any]) -> bool:
        """Test WebSocket reconnection with existing session."""
        import websockets
        import json
        
        try:
            ws = await websockets.connect(
                self.ws_url,
                extra_headers={"Authorization": f"Bearer {session['token']}"}
            )
            
            # Send test message
            await ws.send(json.dumps({
                "type": "ping",
                "session_id": session["session_id"]
            }))
            
            # Wait for response
            response = await asyncio.wait_for(ws.recv(), timeout=5)
            await ws.close()
            
            return True
        except Exception:
            return False


@pytest.mark.integration
@pytest.mark.requires_session_persistence
class TestUserSessionPersistenceRestart:
    """Test suite for user session persistence across restarts."""
    
    @pytest.fixture
    async def test_harness(self):
        """Create test harness for session persistence testing."""
        harness = UserSessionPersistenceTest()
        await harness.setup()
        yield harness
        await harness.teardown()
    
    @pytest.mark.asyncio
    async def test_user_session_persistence_across_restarts(self, test_harness):
        """
        Test session persistence during service restarts.
        
        Validates:
        1. Active sessions creation
        2. Service restart handling
        3. Session validity after restart
        4. Data consistency
        """
        # Phase 1: Establish Active Sessions
        active_sessions = []
        for i in range(10):
            session = await test_harness.create_authenticated_session(f"test_user_{i}")
            active_sessions.append(session)
            test_harness.active_sessions.append(session)
        
        # Phase 2: Pre-Restart Validation
        for session in active_sessions:
            is_active = await test_harness.validate_session_active(session["token"])
            assert is_active == True, f"Session {session['user_id']} not active before restart"
            
            action_result = await test_harness.perform_authenticated_action(session)
            assert action_result["success"] == True, \
                f"Authenticated action failed for {session['user_id']}"
        
        # Store session data in Redis for comparison
        pre_restart_redis_data = {}
        for session in active_sessions:
            if session["session_id"]:
                redis_data = await test_harness.get_session_from_redis(session["session_id"])
                if redis_data:
                    pre_restart_redis_data[session["session_id"]] = redis_data
        
        # Phase 3: Service Restart Sequence
        await test_harness.restart_auth_service(graceful=True)
        await test_harness.restart_backend_service(graceful=True)
        
        # Phase 4: Post-Restart Validation
        await asyncio.sleep(5)  # Allow services to stabilize
        
        sessions_survived = 0
        for session in active_sessions:
            # Session should still be valid
            is_active = await test_harness.validate_session_active(session["token"])
            assert is_active == True, \
                f"Session {session['user_id']} lost after restart"
            
            # User should be able to perform actions
            action_result = await test_harness.perform_authenticated_action(session)
            assert action_result["success"] == True, \
                f"Cannot perform action with session {session['user_id']} after restart"
            
            sessions_survived += 1
        
        # All sessions should survive
        assert sessions_survived == len(active_sessions), \
            f"Only {sessions_survived}/{len(active_sessions)} sessions survived"
        
        # Phase 5: Data Consistency Check
        for session in active_sessions:
            user_data = await test_harness.get_user_data(
                session["user_id"], 
                session["token"]
            )
            assert user_data.get("email") == session["email"], \
                f"User data inconsistent for {session['user_id']}"
            
            # Check Redis session data consistency
            if session["session_id"] and session["session_id"] in pre_restart_redis_data:
                post_restart_data = await test_harness.get_session_from_redis(
                    session["session_id"]
                )
                assert post_restart_data is not None, \
                    f"Session data lost in Redis for {session['session_id']}"
    
    @pytest.mark.asyncio
    async def test_websocket_session_persistence(self, test_harness):
        """Test WebSocket connections can re-establish with existing sessions."""
        # Create sessions with WebSocket connections
        sessions = []
        for i in range(5):
            session = await test_harness.create_authenticated_session(f"ws_user_{i}")
            sessions.append(session)
        
        # Test initial WebSocket connections
        for session in sessions:
            connected = await test_harness.test_websocket_reconnection(session)
            assert connected, f"Initial WebSocket connection failed for {session['user_id']}"
        
        # Restart backend (which handles WebSocket)
        await test_harness.restart_backend_service(graceful=True)
        await asyncio.sleep(5)
        
        # Test WebSocket reconnection with existing sessions
        reconnected_count = 0
        for session in sessions:
            connected = await test_harness.test_websocket_reconnection(session)
            if connected:
                reconnected_count += 1
        
        # Most sessions should reconnect successfully
        assert reconnected_count >= len(sessions) * 0.8, \
            f"Only {reconnected_count}/{len(sessions)} WebSocket sessions reconnected"
    
    @pytest.mark.asyncio
    async def test_concurrent_activity_during_restart(self, test_harness):
        """Test handling of concurrent user activity during restart."""
        # Create active sessions
        sessions = []
        for i in range(10):
            session = await test_harness.create_authenticated_session(f"active_user_{i}")
            sessions.append(session)
        
        # Start background activity
        activity_task = asyncio.create_task(
            test_harness.simulate_user_activity(sessions)
        )
        
        # Restart services during activity
        await asyncio.sleep(2)  # Let some activity happen
        await test_harness.restart_backend_service(graceful=True)
        
        # Complete activity task
        activities = await activity_task
        
        # Some activities should succeed (before/after restart)
        successful = [a for a in activities if a["success"]]
        assert len(successful) > 0, "No activities succeeded during restart"
        
        # After restart, all sessions should still work
        await asyncio.sleep(5)
        for session in sessions:
            is_active = await test_harness.validate_session_active(session["token"])
            assert is_active, f"Session {session['user_id']} lost during concurrent activity"
    
    @pytest.mark.asyncio
    async def test_session_expiry_handling_across_restart(self, test_harness):
        """Test session expiry handling across service restarts."""
        # Create sessions with different expiry times
        sessions = []
        
        # Short-lived session (should expire)
        short_session = await test_harness.create_authenticated_session("short_lived_user")
        
        # Set short expiry in Redis (simulate)
        if short_session["session_id"]:
            await test_harness.redis_client.expire(
                f"session:{short_session['session_id']}", 
                5  # 5 seconds
            )
        sessions.append(("short", short_session))
        
        # Long-lived session (should persist)
        long_session = await test_harness.create_authenticated_session("long_lived_user")
        sessions.append(("long", long_session))
        
        # Wait for short session to expire
        await asyncio.sleep(6)
        
        # Restart services
        await test_harness.restart_auth_service(graceful=True)
        await test_harness.restart_backend_service(graceful=True)
        await asyncio.sleep(5)
        
        # Check session states
        for session_type, session in sessions:
            is_active = await test_harness.validate_session_active(session["token"])
            
            if session_type == "short":
                # Should be expired
                assert not is_active, "Short-lived session should have expired"
            else:
                # Should still be valid
                assert is_active, "Long-lived session should persist"
    
    @pytest.mark.asyncio
    async def test_forced_restart_session_recovery(self, test_harness):
        """Test session recovery after forced (non-graceful) restart."""
        # Create sessions
        sessions = []
        for i in range(5):
            session = await test_harness.create_authenticated_session(f"force_restart_user_{i}")
            sessions.append(session)
        
        # Perform actions to ensure sessions are active
        for session in sessions:
            await test_harness.perform_authenticated_action(session)
        
        # Force restart (non-graceful)
        await test_harness.restart_auth_service(graceful=False)
        await test_harness.restart_backend_service(graceful=False)
        
        # Wait for services to recover
        await asyncio.sleep(10)
        
        # Sessions should still be valid (from Redis persistence)
        recovered_count = 0
        for session in sessions:
            is_active = await test_harness.validate_session_active(session["token"])
            if is_active:
                recovered_count += 1
        
        # Most sessions should recover even after forced restart
        assert recovered_count >= len(sessions) * 0.8, \
            f"Only {recovered_count}/{len(sessions)} sessions recovered after forced restart"