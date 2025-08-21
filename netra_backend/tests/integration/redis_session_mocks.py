"""
Redis Session Mock Utilities

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) - Core session management functionality
- Business Goal: Platform Stability - Prevent $35K MRR loss from session state failures
- Value Impact: Ensures WebSocket connect → Redis state → multiple connections → state consistency
- Revenue Impact: Prevents customer session loss/desync that would cause immediate churn

Mock utilities for Redis session state synchronization testing.
"""

import asyncio
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from unittest.mock import Mock, AsyncMock


class MockRedisConnection:
    """Mock Redis connection with state synchronization capabilities."""
    
    def __init__(self):
        self.data_store = {}
        self.pub_sub_channels = {}
        self.subscribers = {}
        self.operation_count = 0
        self.sync_events = []
        
    async def set(self, key: str, value: str, ex: Optional[int] = None):
        """Set key-value with optional expiry."""
        self.operation_count += 1
        
        self.data_store[key] = {"value": value, "expires_at": time.time() + ex if ex else None, "set_at": time.time()}
        
        self.sync_events.append({"operation": "set", "key": key, "timestamp": datetime.now(timezone.utc)})
        
        await self._notify_subscribers(key, "set", value)
        return True
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        self.operation_count += 1
        
        if key in self.data_store:
            entry = self.data_store[key]
            
            if entry["expires_at"] and time.time() > entry["expires_at"]:
                del self.data_store[key]
                return None
            
            return entry["value"]
        
        return None
    
    async def delete(self, key: str) -> int:
        """Delete key."""
        self.operation_count += 1
        
        if key in self.data_store:
            del self.data_store[key]
            
            self.sync_events.append({"operation": "delete", "key": key, "timestamp": datetime.now(timezone.utc)})
            
            await self._notify_subscribers(key, "delete", None)
            return 1
        
        return 0
    
    async def hset(self, key: str, field: str, value: str):
        """Set hash field."""
        self.operation_count += 1
        
        if key not in self.data_store:
            self.data_store[key] = {"value": {}, "type": "hash"}
        
        self.data_store[key]["value"][field] = value
        
        self.sync_events.append({"operation": "hset", "key": key, "field": field, "timestamp": datetime.now(timezone.utc)})
        return True
    
    async def hget(self, key: str, field: str) -> Optional[str]:
        """Get hash field."""
        self.operation_count += 1
        
        if key in self.data_store and self.data_store[key].get("type") == "hash":
            return self.data_store[key]["value"].get(field)
        
        return None
    
    async def hgetall(self, key: str) -> Dict[str, str]:
        """Get all hash fields."""
        self.operation_count += 1
        
        if key in self.data_store and self.data_store[key].get("type") == "hash":
            return self.data_store[key]["value"].copy()
        
        return {}
    
    async def publish(self, channel: str, message: str):
        """Publish message to channel."""
        self.operation_count += 1
        
        if channel not in self.pub_sub_channels:
            self.pub_sub_channels[channel] = []
        
        message_data = {"channel": channel, "message": message, "timestamp": datetime.now(timezone.utc)}
        
        self.pub_sub_channels[channel].append(message_data)
        
        if channel in self.subscribers:
            for callback in self.subscribers[channel]:
                await callback(message_data)
        
        return len(self.subscribers.get(channel, []))
    
    async def subscribe(self, channel: str, callback):
        """Subscribe to channel."""
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        
        self.subscribers[channel].append(callback)
    
    async def _notify_subscribers(self, key: str, operation: str, value: Optional[str]):
        """Notify subscribers of key changes."""
        notification = {"key": key, "operation": operation, "value": value, "timestamp": datetime.now(timezone.utc)}
        
        sync_channel = f"state_sync:{key.split(':')[0]}"
        await self.publish(sync_channel, json.dumps(notification))


class MockWebSocketConnection:
    """Mock WebSocket connection with state sync capabilities."""
    
    def __init__(self, user_id: str, connection_id: str):
        self.user_id = user_id
        self.connection_id = connection_id
        self.state = "connected"
        self.messages_sent = []
        self.session_data = {}
        self.sync_notifications = []
        
    async def send_json(self, data: Dict[str, Any]):
        """Send JSON message."""
        if self.state != "connected":
            raise Exception("WebSocket not connected")
        
        self.messages_sent.append({"type": "json", "content": data, "timestamp": datetime.now(timezone.utc)})
    
    async def send_text(self, message: str):
        """Send text message."""
        if self.state != "connected":
            raise Exception("WebSocket not connected")
        
        self.messages_sent.append({"type": "text", "content": message, "timestamp": datetime.now(timezone.utc)})
    
    def disconnect(self):
        """Disconnect WebSocket."""
        self.state = "disconnected"
    
    def receive_sync_notification(self, notification: Dict[str, Any]):
        """Receive state sync notification."""
        self.sync_notifications.append(notification)


class MockRedisSessionManager:
    """Mock Redis session manager with state synchronization."""
    
    def __init__(self, redis_connection: MockRedisConnection):
        self.redis = redis_connection
        self.active_sessions = {}
        self.sync_metrics = {"sessions_created": 0, "sync_operations": 0, "sync_conflicts": 0, "avg_sync_time": 0}
    
    async def create_session(self, user_id: str, connection_id: str, initial_data: Dict[str, Any] = None) -> str:
        """Create new session with Redis state."""
        session_id = str(uuid.uuid4())
        
        session_data = {"session_id": session_id, "user_id": user_id, "connection_id": connection_id, "created_at": datetime.now(timezone.utc).isoformat(), "last_activity": datetime.now(timezone.utc).isoformat(), "state": initial_data or {}}
        
        session_key = f"session:{session_id}"
        user_session_key = f"user_sessions:{user_id}"
        
        await self.redis.set(session_key, json.dumps(session_data), ex=3600)
        await self.redis.hset(user_session_key, connection_id, session_id)
        
        self.active_sessions[session_id] = session_data
        self.sync_metrics["sessions_created"] += 1
        
        return session_id
    
    async def update_session_state(self, session_id: str, state_updates: Dict[str, Any]) -> bool:
        """Update session state with Redis sync."""
        start_time = time.time()
        
        try:
            session_key = f"session:{session_id}"
            
            session_json = await self.redis.get(session_key)
            if not session_json:
                return False
            
            session_data = json.loads(session_json)
            
            session_data["state"].update(state_updates)
            session_data["last_activity"] = datetime.now(timezone.utc).isoformat()
            
            await self.redis.set(session_key, json.dumps(session_data), ex=3600)
            
            if session_id in self.active_sessions:
                self.active_sessions[session_id] = session_data
            
            sync_time = time.time() - start_time
            self.sync_metrics["sync_operations"] += 1
            self._update_avg_sync_time(sync_time)
            
            return True
            
        except Exception:
            return False
    
    async def get_session_state(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session state from Redis."""
        session_key = f"session:{session_id}"
        
        session_json = await self.redis.get(session_key)
        if session_json:
            return json.loads(session_json)
        
        return None
    
    async def get_user_sessions(self, user_id: str) -> Dict[str, str]:
        """Get all sessions for user."""
        user_session_key = f"user_sessions:{user_id}"
        return await self.redis.hgetall(user_session_key)
    
    async def sync_state_across_connections(self, user_id: str, state_updates: Dict[str, Any]) -> List[str]:
        """Sync state across all user connections."""
        user_sessions = await self.get_user_sessions(user_id)
        synced_sessions = []
        
        for connection_id, session_id in user_sessions.items():
            success = await self.update_session_state(session_id, state_updates)
            if success:
                synced_sessions.append(session_id)
        
        return synced_sessions
    
    def _update_avg_sync_time(self, sync_time: float):
        """Update average sync time metric."""
        current_avg = self.sync_metrics["avg_sync_time"]
        sync_count = self.sync_metrics["sync_operations"]
        
        self.sync_metrics["avg_sync_time"] = ((current_avg * (sync_count - 1) + sync_time) / sync_count)


class MockWebSocketManagerWithRedis:
    """Mock WebSocket manager with Redis state synchronization."""
    
    def __init__(self, redis_manager: MockRedisSessionManager):
        self.redis_manager = redis_manager
        self.connections = {}
        self.connection_sessions = {}
        self.sync_subscriptions = {}
    
    async def add_connection(self, user_id: str, websocket: MockWebSocketConnection):
        """Add WebSocket connection with Redis session."""
        connection_id = websocket.connection_id
        
        session_id = await self.redis_manager.create_session(user_id, connection_id)
        
        self.connections[connection_id] = {"websocket": websocket, "user_id": user_id, "session_id": session_id, "connected_at": datetime.now(timezone.utc)}
        
        self.connection_sessions[connection_id] = session_id
        
        await self._subscribe_to_sync_events(user_id, connection_id)
    
    async def remove_connection(self, connection_id: str):
        """Remove WebSocket connection."""
        if connection_id in self.connections:
            connection_info = self.connections[connection_id]
            websocket = connection_info["websocket"]
            websocket.disconnect()
            
            del self.connections[connection_id]
            if connection_id in self.connection_sessions:
                del self.connection_sessions[connection_id]
    
    async def update_user_state(self, user_id: str, state_updates: Dict[str, Any]):
        """Update state for all user connections."""
        synced_sessions = await self.redis_manager.sync_state_across_connections(user_id, state_updates)
        
        user_connections = [conn for conn in self.connections.values() if conn["user_id"] == user_id]
        
        for connection in user_connections:
            websocket = connection["websocket"]
            await websocket.send_json({"type": "state_sync", "state_updates": state_updates, "sync_timestamp": datetime.now(timezone.utc).isoformat()})
        
        return len(synced_sessions)
    
    async def get_connection_state(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """Get state for specific connection."""
        if connection_id in self.connection_sessions:
            session_id = self.connection_sessions[connection_id]
            return await self.redis_manager.get_session_state(session_id)
        
        return None
    
    async def _subscribe_to_sync_events(self, user_id: str, connection_id: str):
        """Subscribe to state sync events."""
        sync_channel = f"state_sync:user_sessions"
        
        async def sync_callback(message_data):
            if connection_id in self.connections:
                websocket = self.connections[connection_id]["websocket"]
                websocket.receive_sync_notification(message_data)
        
        await self.redis_manager.redis.subscribe(sync_channel, sync_callback)
        self.sync_subscriptions[connection_id] = sync_channel
