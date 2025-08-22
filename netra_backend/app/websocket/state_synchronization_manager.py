"""WebSocket State Synchronization Manager

Manages application state synchronization across WebSocket connections:
- Initial state snapshots on connection
- Incremental state updates during sessions
- Full resync after reconnection
- Version conflict resolution
- Multi-connection state consistency

Business Value Justification (BVJ):
- Segment: All customer tiers (Free, Early, Mid, Enterprise)
- Business Goal: Eliminate stale UI data that frustrates users
- Value Impact: Consistent state across tabs/devices improves user trust
- Revenue Impact: Prevents user confusion that leads to churn
"""

import asyncio
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.registry import WebSocketMessage, WebSocketMessageType

logger = central_logger.get_logger(__name__)


@dataclass
class ApplicationState:
    """Application state structure for synchronization."""
    user_id: str
    session_id: str
    agent_state: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]
    ui_preferences: Dict[str, Any]
    thread_data: Dict[str, Any]
    version: int = 1
    last_updated: Optional[datetime] = None
    
    def __post_init__(self):
        if self.last_updated is None:
            self.last_updated = datetime.now(timezone.utc)


@dataclass
class StateUpdate:
    """Incremental state update structure."""
    update_type: str  # 'agent_progress', 'conversation_message', 'ui_preference', etc.
    data: Dict[str, Any]
    version: int
    user_id: str
    session_id: str
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


class StateSynchronizationManager:
    """Manages WebSocket state synchronization across connections."""
    
    def __init__(self):
        """Initialize state synchronization manager."""
        self.user_states: Dict[str, ApplicationState] = {}
        self.connection_states: Dict[str, Dict[str, Any]] = {}  # connection_id -> state info
        self.version_tracking: Dict[str, int] = {}  # user_id -> current version
        self.active_sessions: Dict[str, Set[str]] = {}  # user_id -> set of connection_ids
    
    async def handle_new_connection(self, user_id: str, connection_id: str, websocket) -> Dict[str, Any]:
        """Handle new WebSocket connection and send initial state snapshot."""
        logger.info(f"Handling new connection for user {user_id}, connection {connection_id}")
        
        # Track connection
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = set()
        self.active_sessions[user_id].add(connection_id)
        
        # Get or create user state
        state = self._get_or_create_user_state(user_id)
        
        # Send initial state snapshot
        snapshot = await self._create_state_snapshot(state)
        await self._send_message(websocket, snapshot)
        
        logger.info(f"Sent state snapshot to user {user_id}, version {state.version}")
        return snapshot
    
    def _get_or_create_user_state(self, user_id: str) -> ApplicationState:
        """Get existing user state or create new one."""
        if user_id not in self.user_states:
            session_id = str(uuid.uuid4())
            self.user_states[user_id] = ApplicationState(
                user_id=user_id,
                session_id=session_id,
                agent_state={
                    "current_agent": None,
                    "execution_step": 0,
                    "total_steps": 0,
                    "tools_in_use": [],
                    "intermediate_results": {}
                },
                conversation_history=[],
                ui_preferences={
                    "theme": "dark",
                    "notification_settings": {"real_time_updates": True},
                    "auto_save_interval": 30
                },
                thread_data={
                    "current_thread_id": None,
                    "threads": {}
                },
                version=1
            )
            self.version_tracking[user_id] = 1
        return self.user_states[user_id]
    
    async def _create_state_snapshot(self, state: ApplicationState) -> Dict[str, Any]:
        """Create complete state snapshot message."""
        return {
            "type": "state_snapshot",
            "payload": {
                "version": state.version,
                "user_id": state.user_id,
                "session_id": state.session_id,
                "agent_state": state.agent_state,
                "conversation_history": state.conversation_history,
                "ui_preferences": state.ui_preferences,
                "thread_data": state.thread_data,
                "timestamp": state.last_updated.isoformat() if state.last_updated else None
            }
        }
    
    async def handle_state_update(self, user_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incremental state update."""
        update_type = update_data.get("update_type")
        data = update_data.get("data", {})
        client_version = update_data.get("version", 0)
        
        logger.debug(f"Processing state update for user {user_id}: {update_type}")
        
        # Check for version conflicts
        current_version = self.version_tracking.get(user_id, 1)
        if client_version != current_version:
            return await self._handle_version_conflict(user_id, client_version, current_version)
        
        # Apply update to state
        state = self._get_or_create_user_state(user_id)
        updated_state = await self._apply_state_update(state, update_type, data)
        
        # Increment version
        updated_state.version += 1
        updated_state.last_updated = datetime.now(timezone.utc)
        self.version_tracking[user_id] = updated_state.version
        
        # Create update response
        response = {
            "type": "state_updated",
            "payload": {
                "version": updated_state.version,
                "update_type": update_type,
                "data": data,
                "user_id": user_id,
                "timestamp": updated_state.last_updated.isoformat()
            }
        }
        
        # Broadcast to all user connections
        await self._broadcast_to_user_connections(user_id, response)
        
        logger.debug(f"State update processed for user {user_id}, new version {updated_state.version}")
        return response
    
    async def _apply_state_update(self, state: ApplicationState, update_type: str, data: Dict[str, Any]) -> ApplicationState:
        """Apply incremental update to application state."""
        if update_type == "agent_progress":
            state.agent_state.update(data)
        elif update_type == "conversation_message":
            state.conversation_history.append(data)
        elif update_type == "ui_preference":
            state.ui_preferences.update(data)
        elif update_type == "thread_update":
            state.thread_data.update(data)
        else:
            logger.warning(f"Unknown update type: {update_type}")
        
        return state
    
    async def _handle_version_conflict(self, user_id: str, client_version: int, server_version: int) -> Dict[str, Any]:
        """Handle version conflict between client and server."""
        logger.warning(f"Version conflict for user {user_id}: client={client_version}, server={server_version}")
        
        return {
            "type": "version_conflict",
            "payload": {
                "client_version": client_version,
                "server_version": server_version,
                "user_id": user_id,
                "resolution": "resync_required",
                "message": "Client state is out of sync, full resync required"
            }
        }
    
    async def handle_reconnection(self, user_id: str, connection_id: str, websocket) -> Dict[str, Any]:
        """Handle WebSocket reconnection with full state resync."""
        logger.info(f"Handling reconnection for user {user_id}, connection {connection_id}")
        
        # Track reconnection
        if user_id not in self.active_sessions:
            self.active_sessions[user_id] = set()
        self.active_sessions[user_id].add(connection_id)
        
        # Get current state
        state = self._get_or_create_user_state(user_id)
        
        # Send full state resync
        resync_message = await self._create_state_resync(state)
        await self._send_message(websocket, resync_message)
        
        logger.info(f"Sent state resync to user {user_id}, version {state.version}")
        return resync_message
    
    async def _create_state_resync(self, state: ApplicationState) -> Dict[str, Any]:
        """Create full state resync message."""
        return {
            "type": "state_resync",
            "payload": {
                "version": state.version,
                "user_id": state.user_id,
                "session_id": state.session_id,
                "agent_state": state.agent_state,
                "conversation_history": state.conversation_history,
                "ui_preferences": state.ui_preferences,
                "thread_data": state.thread_data,
                "timestamp": state.last_updated.isoformat() if state.last_updated else None,
                "resync_reason": "reconnection"
            }
        }
    
    async def handle_partial_state_update(self, user_id: str, partial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle partial state update (dot notation paths)."""
        updates = partial_data.get("updates", {})
        version = partial_data.get("version", 0)
        
        logger.debug(f"Processing partial state update for user {user_id}: {len(updates)} fields")
        
        # Check version conflict
        current_version = self.version_tracking.get(user_id, 1)
        if version != current_version:
            return await self._handle_version_conflict(user_id, version, current_version)
        
        # Apply partial updates
        state = self._get_or_create_user_state(user_id)
        await self._apply_partial_updates(state, updates)
        
        # Increment version
        state.version += 1
        state.last_updated = datetime.now(timezone.utc)
        self.version_tracking[user_id] = state.version
        
        return {
            "type": "partial_update_applied",
            "payload": {
                "version": state.version,
                "user_id": user_id,
                "applied_updates": list(updates.keys()),
                "timestamp": state.last_updated.isoformat()
            }
        }
    
    async def _apply_partial_updates(self, state: ApplicationState, updates: Dict[str, Any]) -> None:
        """Apply partial updates using dot notation paths."""
        for path, value in updates.items():
            parts = path.split('.')
            obj = state
            
            # Navigate to parent object
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                elif isinstance(obj, dict) and part in obj:
                    obj = obj[part]
                else:
                    logger.warning(f"Invalid path in partial update: {path}")
                    continue
            
            # Set the final value
            final_key = parts[-1]
            if hasattr(obj, final_key):
                setattr(obj, final_key, value)
            elif isinstance(obj, dict):
                obj[final_key] = value
            else:
                logger.warning(f"Cannot set value for path: {path}")
    
    async def handle_get_current_state(self, user_id: str, session_id: str, websocket) -> Dict[str, Any]:
        """Handle request for current state."""
        state = self._get_or_create_user_state(user_id)
        
        response = {
            "type": "current_state",
            "payload": {
                "version": state.version,
                "user_id": state.user_id,
                "session_id": state.session_id,
                "agent_state": state.agent_state,
                "conversation_history": state.conversation_history,
                "ui_preferences": state.ui_preferences,
                "thread_data": state.thread_data,
                "timestamp": state.last_updated.isoformat() if state.last_updated else None
            }
        }
        
        await self._send_message(websocket, response)
        return response
    
    async def handle_disconnection(self, user_id: str, connection_id: str) -> None:
        """Handle WebSocket disconnection cleanup."""
        logger.debug(f"Handling disconnection for user {user_id}, connection {connection_id}")
        
        if user_id in self.active_sessions:
            self.active_sessions[user_id].discard(connection_id)
            
            # Clean up if no active connections
            if not self.active_sessions[user_id]:
                del self.active_sessions[user_id]
                logger.debug(f"No active connections for user {user_id}, cleaned up session")
    
    async def _broadcast_to_user_connections(self, user_id: str, message: Dict[str, Any]) -> None:
        """Broadcast message to all active connections for a user."""
        if user_id not in self.active_sessions:
            return
        
        connections = self.active_sessions[user_id].copy()
        logger.debug(f"Broadcasting to {len(connections)} connections for user {user_id}")
        
        # In a real implementation, this would send to all WebSocket connections
        # For now, we'll log the broadcast intent
        for connection_id in connections:
            logger.debug(f"Would broadcast to connection {connection_id}: {message['type']}")
    
    async def _send_message(self, websocket, message: Dict[str, Any]) -> None:
        """Send message through WebSocket."""
        try:
            if hasattr(websocket, 'send'):
                await websocket.send(json.dumps(message))
            else:
                logger.debug(f"Mock websocket - would send: {message['type']}")
        except Exception as e:
            logger.error(f"Failed to send WebSocket message: {e}")
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get state synchronization statistics."""
        total_users = len(self.user_states)
        total_connections = sum(len(sessions) for sessions in self.active_sessions.values())
        
        return {
            "total_users_with_state": total_users,
            "total_active_connections": total_connections,
            "users_with_active_connections": len(self.active_sessions),
            "average_connections_per_user": total_connections / max(len(self.active_sessions), 1)
        }