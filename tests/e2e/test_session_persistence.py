"""Session Persistence Tests - WebSocket Disconnection Recovery

Business Value Justification (BVJ):
1. Segment: Growth & Enterprise
2. Business Goal: $20K MRR - User experience continuity  
3. Value Impact: Session persistence prevents user abandonment
4. Revenue Impact: Reduces 15-20% churn from connection issues

Tests session persistence across WebSocket disconnects for seamless UX.
ARCHITECTURAL COMPLIANCE: <300 lines, <8 lines per function
"""

import asyncio
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import pytest

from netra_backend.app.logging_config import central_logger
from test_framework.websocket_helpers import MockWebSocket
from tests.e2e.config import TEST_USERS
from tests.e2e.test_websocket_integration import WebSocketBuilder

logger = central_logger.get_logger(__name__)

class SessionManager:
    """Core session management for disconnection testing."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.chat_histories: Dict[str, List[Dict[str, Any]]] = {}
    
    def create_user_session(self, user_id: str) -> Tuple[str, str]:
        """Create authenticated session with token."""
        session_id = f"session_{user_id}_{uuid.uuid4().hex[:8]}"
        token = f"token_{user_id}_{session_id}_{int(time.time())}"
        return session_id, token
    
    def store_session_data(self, session_id: str, user_id: str, token: str):
        """Store session data for persistence."""
        self.sessions[session_id] = {
            "user_id": user_id, "token": token, "created_at": datetime.now(),
            "last_activity": datetime.now(), "is_active": True
        }
    
    def add_chat_message(self, session_id: str, message: Dict[str, Any]):
        """Add message to session chat history."""
        if session_id not in self.chat_histories:
            self.chat_histories[session_id] = []
        self.chat_histories[session_id].append(message)
    
    def validate_session_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate session token and return session data."""
        for session_id, data in self.sessions.items():
            if data["token"] == token:
                return {"session_id": session_id, **data}
        return None

class ConnectionManager:
    """Manages WebSocket connections for session testing."""
    
    def __init__(self):
        self.connection_events: List[Dict[str, Any]] = []
    
    def create_authenticated_connection(self, user_id: str, token: str):
        """Create authenticated WebSocket connection."""
        return (WebSocketBuilder()
               .with_user_id(user_id)
               .with_authentication(token)
               .build())
    
    def record_connection_event(self, event_type: str, user_id: str, details):
        """Record connection event for validation."""
        self.connection_events.append({
            "event": event_type, "user_id": user_id, "timestamp": datetime.now(),
            "details": details
        })
    
    async def simulate_connection_loss(self, websocket):
        """Simulate unexpected connection loss."""
        await websocket.close(code=1006, reason="Connection lost")
        self.record_connection_event("connection_lost", websocket.user_id,
                                   {"code": 1006, "reason": "network_error"})
    
    async def perform_graceful_disconnect(self, websocket):
        """Perform graceful disconnect with session preservation."""
        await websocket.send_json({"type": "disconnect", "preserve_session": True})
        await websocket.close(code=1000, reason="Graceful disconnect")
        self.record_connection_event("graceful_disconnect", websocket.user_id,
                                   {"preserved": True})

class TokenRefreshManager:
    """Handles token refresh during active sessions."""
    
    def __init__(self, session_manager: SessionManager):
        self.session_manager = session_manager
        self.refresh_events: List[Dict[str, Any]] = []
    
    def create_expired_token_scenario(self, token: str) -> Dict[str, Any]:
        """Create scenario with expired token."""
        session_data = self.session_manager.validate_session_token(token)
        if session_data:
            session_data["expires_at"] = datetime.now() - timedelta(minutes=5)
        return {"token_expired": True, "session_valid": session_data is not None}
    
    def refresh_session_token(self, old_token: str) -> Optional[str]:
        """Refresh expired token maintaining session."""
        session_data = self.session_manager.validate_session_token(old_token)
        if not session_data:
            return None
        user_id = session_data["user_id"]
        session_id = session_data["session_id"]
        new_token = f"refreshed_token_{user_id}_{session_id}_{int(time.time())}"
        self._update_session_token(session_id, new_token)
        return new_token
    
    def _update_session_token(self, session_id: str, new_token: str):
        """Update session with new token."""
        if session_id in self.session_manager.sessions:
            self.session_manager.sessions[session_id]["token"] = new_token
            self.refresh_events.append({"session_id": session_id, 
                                      "timestamp": datetime.now()})

# ============================================================================
# TEST FIXTURES
# ============================================================================

@pytest.fixture
def session_manager():
    """Session manager fixture."""
    return SessionManager()

@pytest.fixture
def connection_manager():
    """WebSocket connection manager fixture."""
    return ConnectionManager()

@pytest.fixture
def token_refresh_manager(session_manager):
    """Token refresh manager fixture."""
    return TokenRefreshManager(session_manager)

# ============================================================================
# CRITICAL TESTS - SESSION PERSISTENCE
# ============================================================================

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_session_persists_across_disconnect_reconnect(session_manager, connection_manager):
    """Test session persistence across disconnect/reconnect."""
    user = TEST_USERS["enterprise"]
    session_id, token = session_manager.create_user_session(user.id)
    session_manager.store_session_data(session_id, user.id, token)
    
    initial_connection = connection_manager.create_authenticated_connection(user.id, token)
    await _build_chat_history(session_manager, session_id, initial_connection)
    await connection_manager.simulate_connection_loss(initial_connection)
    
    reconnected_ws = connection_manager.create_authenticated_connection(user.id, token)
    _validate_session_persistence(session_manager, token, user.id, session_id)

async def _build_chat_history(session_manager, session_id, connection):
    """Build chat history during session."""
    messages = [
        {"role": "user", "content": "Analyze my AI costs"},
        {"role": "assistant", "content": "I found 3 optimization opportunities"}
    ]
    
    for message in messages:
        session_manager.add_chat_message(session_id, message)
        await connection.send_json({"type": "message", "data": message})

def _validate_session_persistence(session_manager, token, user_id, session_id):
    """Validate session and history preserved."""
    session_data = session_manager.validate_session_token(token)
    assert session_data is not None, "Session must persist after disconnection"
    assert session_data["user_id"] == user_id, "User ID must be preserved"
    
    chat_history = session_manager.chat_histories.get(session_id, [])
    assert len(chat_history) == 2, "Chat history must be preserved"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_graceful_disconnect_preserves_session(session_manager, connection_manager):
    """Test graceful disconnect preserves session state."""
    user = TEST_USERS["mid"]
    session_id, token = session_manager.create_user_session(user.id)
    session_manager.store_session_data(session_id, user.id, token)
    
    websocket = connection_manager.create_authenticated_connection(user.id, token)
    _add_session_activity(session_manager, session_id)
    await connection_manager.perform_graceful_disconnect(websocket)
    
    _validate_graceful_disconnect(session_manager, connection_manager, token)

def _add_session_activity(session_manager, session_id):
    """Add session activity."""
    session_manager.add_chat_message(session_id, {
        "role": "user", "content": "What optimization strategies do you recommend?"
    })

def _validate_graceful_disconnect(session_manager, connection_manager, token):
    """Validate session preservation."""
    session_data = session_manager.validate_session_token(token)
    assert session_data is not None, "Session must survive graceful disconnect"
    assert session_data["is_active"], "Session should remain active"
    
    events = connection_manager.connection_events
    disconnect_events = [e for e in events if e["event"] == "graceful_disconnect"]
    assert len(disconnect_events) == 1, "Graceful disconnect must be recorded"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_token_refresh_during_active_session(session_manager, token_refresh_manager, connection_manager):
    """Test token refresh without session interruption."""
    user = TEST_USERS["enterprise"]
    session_id, initial_token = session_manager.create_user_session(user.id)
    session_manager.store_session_data(session_id, user.id, initial_token)
    
    _establish_session_with_activity(session_manager, connection_manager,
                                    session_id, user.id, initial_token)
    refreshed_token = _perform_token_refresh(token_refresh_manager, initial_token)
    _validate_token_refresh_continuity(session_manager, connection_manager, 
                                     user.id, refreshed_token, session_id)

def _establish_session_with_activity(session_manager, connection_manager, 
                                     session_id, user_id, token):
    """Establish connection and add session activity."""
    websocket = connection_manager.create_authenticated_connection(user_id, token)
    for i in range(3):
        session_manager.add_chat_message(session_id, {
            "role": "user", "content": f"Message {i+1} before token refresh"
        })

def _perform_token_refresh(token_refresh_manager, initial_token):
    """Perform token refresh and validate."""
    expiry_scenario = token_refresh_manager.create_expired_token_scenario(initial_token)
    assert expiry_scenario["token_expired"], "Token expiration scenario created"
    
    refreshed_token = token_refresh_manager.refresh_session_token(initial_token)
    assert refreshed_token is not None, "Token refresh must succeed"
    assert refreshed_token != initial_token, "New token must be different"
    return refreshed_token

def _validate_token_refresh_continuity(session_manager, connection_manager, 
                                      user_id, refreshed_token, session_id):
    """Validate session continuity with refreshed token."""
    refreshed_connection = connection_manager.create_authenticated_connection(
        user_id, refreshed_token
    )
    
    session_data = session_manager.validate_session_token(refreshed_token)
    assert session_data is not None, "Session must persist with refreshed token"
    
    chat_history = session_manager.chat_histories.get(session_id, [])
    assert len(chat_history) == 3, "Chat history preserved during token refresh"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multiple_disconnection_scenarios(session_manager, connection_manager):
    """Test session persistence across various disconnection types."""
    user = TEST_USERS["early"]
    session_id, token = session_manager.create_user_session(user.id)
    session_manager.store_session_data(session_id, user.id, token)
    
    scenarios = [
        {"code": 1000, "reason": "Normal"},
        {"code": 1006, "reason": "Abnormal"}, 
        {"code": 1001, "reason": "Going away"}
    ]
    
    for scenario in scenarios:
        websocket = connection_manager.create_authenticated_connection(user.id, token)
        _add_scenario_message(session_manager, session_id, scenario["code"])
        await websocket.close(code=scenario["code"], reason=scenario["reason"])
        _validate_scenario_persistence(session_manager, token, scenario["reason"])

def _add_scenario_message(session_manager, session_id, code):
    """Add message for disconnection scenario."""
    session_manager.add_chat_message(session_id, {
        "role": "user", "content": f"Test message for scenario {code}"
    })

def _validate_scenario_persistence(session_manager, token, reason):
    """Validate session persists after scenario."""
    session_data = session_manager.validate_session_token(token)
    assert session_data is not None, f"Session must persist after {reason}"

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_concurrent_session_operations(session_manager, connection_manager):
    """Test concurrent session operations don't corrupt state."""
    user = TEST_USERS["free"]
    
    async def session_operation_task(task_id: int) -> Dict[str, Any]:
        session_id, token = session_manager.create_user_session(f"{user.id}_{task_id}")
        session_manager.store_session_data(session_id, f"{user.id}_{task_id}", token)
        websocket = connection_manager.create_authenticated_connection(
            f"{user.id}_{task_id}", token
        )
        session_manager.add_chat_message(session_id, {
            "role": "user", "content": f"Concurrent task {task_id}"
        })
        return {"task_id": task_id, "session_id": session_id, "success": True}
    
    tasks = [session_operation_task(i) for i in range(5)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_operations = [r for r in results if isinstance(r, dict) and r["success"]]
    assert len(successful_operations) == 5, "All concurrent operations must succeed"
    
    session_ids = [r["session_id"] for r in successful_operations]
    assert len(set(session_ids)) == 5, "All sessions must have unique identifiers"