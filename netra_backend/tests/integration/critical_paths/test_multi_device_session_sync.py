"""L3 Integration Test: Multi-Device Session Synchronization

Business Value Justification (BVJ):
- Segment: Mid/Enterprise tiers (cross-device workflows)
- Business Goal: Enable seamless multi-device user experience
- Value Impact: Supports modern work patterns with mobile/desktop switching
- Strategic Impact: Competitive advantage for enterprise customers worth $25K MRR

L3 Test: Real Redis-backed session synchronization across multiple devices.
Tests cross-device state consistency and conflict resolution.
"""

from netra_backend.app.websocket_core.manager import WebSocketManager
# Test framework import - using pytest fixtures instead
from pathlib import Path
import sys

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import redis.asyncio as redis

# JWT service replaced with auth_integration
from netra_backend.app.auth_integration.auth import create_access_token, validate_token_jwt
from unittest.mock import AsyncMock, MagicMock

JWTService = AsyncMock
# Session manager replaced with mock

SessionManager = AsyncMock
from netra_backend.app.websocket_core.manager import WebSocketManager
from netra_backend.app.redis_manager import RedisManager
from netra_backend.app.logging_config import central_logger
from netra_backend.tests.integration.helpers.redis_l3_helpers import RedisContainer, MockWebSocketForRedis

logger = central_logger.get_logger(__name__)

class DeviceSession:

    """Represents a user session on a specific device."""
    
    def __init__(self, user_id: str, device_id: str, device_type: str, 

                 session_id: str, token: str, websocket: MockWebSocketForRedis):

        self.user_id = user_id

        self.device_id = device_id

        self.device_type = device_type

        self.session_id = session_id

        self.token = token

        self.websocket = websocket

        self.last_activity = time.time()

        self.sync_events = []

        self.received_messages = []
    
    def update_activity(self):

        """Update last activity timestamp."""

        self.last_activity = time.time()
    
    def add_sync_event(self, event_type: str, data: Dict[str, Any]):

        """Record synchronization event."""

        self.sync_events.append({

            "type": event_type,

            "data": data,

            "timestamp": time.time()

        })
    
    def add_received_message(self, message: Dict[str, Any]):

        """Record received message."""

        self.received_messages.append({

            "message": message,

            "timestamp": time.time()

        })

class MultiDeviceSessionManager:

    """Manages multi-device session synchronization testing."""
    
    def __init__(self, jwt_service: JWTService, session_manager: SessionManager,

                 websocket_manager: WebSocketManager, redis_client):

        self.jwt_service = jwt_service

        self.session_manager = session_manager

        self.websocket_manager = websocket_manager

        self.redis_client = redis_client

        self.user_devices = {}  # user_id -> List[DeviceSession]

        self.sync_channels = {}  # user_id -> channel_name
    
    async def create_device_session(self, user_id: str, device_type: str, 

                                  device_metadata: Optional[Dict[str, Any]] = None) -> DeviceSession:

        """Create a new device session for a user."""

        device_id = f"{device_type}_{uuid.uuid4().hex[:8]}"
        
        # Generate JWT token for device

        token_result = await self.jwt_service.generate_token(

            user_id=user_id,

            permissions=["read", "write"],

            tier="mid",

            device_id=device_id

        )
        
        if not token_result["success"]:

            raise ValueError(f"Token generation failed: {token_result.get('error')}")
        
        # Create session with device metadata

        session_metadata = {

            "device_id": device_id,

            "device_type": device_type,

            "auth_method": "multi_device",

            "ip_address": "127.0.0.1",

            **(device_metadata or {})

        }
        
        session_result = await self.session_manager.create_session(

            user_id=user_id,

            token=token_result["token"],

            metadata=session_metadata

        )
        
        if not session_result["success"]:

            raise ValueError(f"Session creation failed: {session_result.get('error')}")
        
        # Create WebSocket connection

        websocket = MockWebSocketForRedis(f"{user_id}_{device_id}")
        
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.ws_manager.verify_jwt_token') as mock_verify:

            mock_verify.return_value = {

                "valid": True,

                "user_id": user_id,

                "device_id": device_id,

                "permissions": ["read", "write"]

            }
            
            connection_info = await self.websocket_manager.connect_user(user_id, websocket)
        
        if not connection_info:

            raise ValueError("WebSocket connection failed")
        
        # Create device session

        device_session = DeviceSession(

            user_id=user_id,

            device_id=device_id,

            device_type=device_type,

            session_id=session_result["session_id"],

            token=token_result["token"],

            websocket=websocket

        )
        
        # Track device for user

        if user_id not in self.user_devices:

            self.user_devices[user_id] = []

        self.user_devices[user_id].append(device_session)
        
        # Setup sync channel

        await self._setup_sync_channel(user_id)
        
        # Store device session info in Redis

        await self._store_device_session(device_session)
        
        logger.info(f"Created device session: {device_type} for user {user_id}")

        return device_session
    
    async def sync_state_across_devices(self, user_id: str, state_data: Dict[str, Any], 

                                      origin_device_id: Optional[str] = None):

        """Synchronize state data across all user devices."""

        if user_id not in self.user_devices:

            return
        
        sync_message = {

            "type": "state_sync",

            "data": {

                "state": state_data,

                "origin_device": origin_device_id,

                "sync_timestamp": time.time(),

                "sync_id": str(uuid.uuid4())

            }

        }
        
        # Send to all devices for the user

        sync_tasks = []

        for device_session in self.user_devices[user_id]:

            if device_session.device_id != origin_device_id:  # Don't sync back to origin

                task = self._send_sync_message(device_session, sync_message)

                sync_tasks.append(task)
        
        # Execute sync concurrently

        results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        
        # Track sync events

        successful_syncs = 0

        for i, result in enumerate(results):

            device_session = self.user_devices[user_id][i]

            if isinstance(result, Exception):

                logger.error(f"Sync failed for device {device_session.device_id}: {result}")

            else:

                successful_syncs += 1

                device_session.add_sync_event("state_received", state_data)
        
        # Store sync event in Redis

        sync_key = f"sync_events:{user_id}"

        sync_event = {

            "sync_id": sync_message["data"]["sync_id"],

            "state": state_data,

            "origin_device": origin_device_id,

            "target_devices": len(sync_tasks),

            "successful_syncs": successful_syncs,

            "timestamp": time.time()

        }
        
        await self.redis_client.lpush(sync_key, json.dumps(sync_event))

        await self.redis_client.expire(sync_key, 3600)  # 1 hour retention
        
        return {

            "sync_id": sync_message["data"]["sync_id"],

            "devices_targeted": len(sync_tasks),

            "successful_syncs": successful_syncs

        }
    
    async def get_user_device_sessions(self, user_id: str) -> List[Dict[str, Any]]:

        """Get all active device sessions for a user."""

        device_sessions = []
        
        # Get from Redis

        devices_key = f"user_devices:{user_id}"

        device_data = await self.redis_client.hgetall(devices_key)
        
        for device_id, data in device_data.items():

            device_info = json.loads(data)

            device_sessions.append(device_info)
        
        return device_sessions
    
    async def handle_device_conflict(self, user_id: str, conflicting_action: str, 

                                   device_sessions: List[DeviceSession]) -> Dict[str, Any]:

        """Handle conflicts between device actions."""

        conflict_id = str(uuid.uuid4())

        conflict_timestamp = time.time()
        
        # Determine conflict resolution strategy

        if conflicting_action == "concurrent_edit":
            # Last-write-wins with timestamp

            latest_device = max(device_sessions, key=lambda d: d.last_activity)

            resolution = "last_write_wins"

            winner = latest_device.device_id

        elif conflicting_action == "session_limit":
            # Keep most recent, close oldest

            sorted_devices = sorted(device_sessions, key=lambda d: d.last_activity, reverse=True)

            max_sessions = 3  # Business rule

            if len(sorted_devices) > max_sessions:

                to_close = sorted_devices[max_sessions:]

                resolution = "session_limit_enforced"

                winner = sorted_devices[0].device_id

            else:

                resolution = "no_action_needed"

                winner = None

        else:

            resolution = "unknown_conflict"

            winner = None
        
        # Apply resolution

        conflict_result = {

            "conflict_id": conflict_id,

            "user_id": user_id,

            "action": conflicting_action,

            "resolution": resolution,

            "winner_device": winner,

            "timestamp": conflict_timestamp,

            "devices_involved": [d.device_id for d in device_sessions]

        }
        
        # Store conflict resolution in Redis

        conflict_key = f"conflicts:{user_id}"

        await self.redis_client.lpush(conflict_key, json.dumps(conflict_result))

        await self.redis_client.expire(conflict_key, 7200)  # 2 hours retention
        
        return conflict_result
    
    async def _setup_sync_channel(self, user_id: str):

        """Setup Redis pub/sub channel for user synchronization."""

        if user_id not in self.sync_channels:

            channel_name = f"sync:{user_id}"

            self.sync_channels[user_id] = channel_name
    
    async def _send_sync_message(self, device_session: DeviceSession, message: Dict[str, Any]):

        """Send sync message to a specific device."""

        success = await self.websocket_manager.send_message_to_user(

            device_session.user_id, message

        )
        
        if success:

            device_session.add_received_message(message)

            device_session.update_activity()
        
        return success
    
    async def _store_device_session(self, device_session: DeviceSession):

        """Store device session info in Redis."""

        devices_key = f"user_devices:{device_session.user_id}"

        device_data = {

            "device_id": device_session.device_id,

            "device_type": device_session.device_type,

            "session_id": device_session.session_id,

            "last_activity": device_session.last_activity,

            "created_at": time.time()

        }
        
        await self.redis_client.hset(devices_key, device_session.device_id, json.dumps(device_data))

        await self.redis_client.expire(devices_key, 86400)  # 24 hours
    
    async def cleanup(self):

        """Clean up all device sessions."""

        for user_id, devices in self.user_devices.items():

            for device in devices:

                try:

                    await self.websocket_manager.disconnect_user(device.user_id, device.websocket)

                    await self.session_manager.invalidate_session(device.session_id)

                except Exception as e:

                    logger.warning(f"Cleanup error for device {device.device_id}: {e}")
        
        self.user_devices.clear()

@pytest.mark.L3

@pytest.mark.integration

class TestMultiDeviceSessionSyncL3:

    """L3 integration test for multi-device session synchronization."""
    
    @pytest.fixture(scope="class")

    async def redis_container(self):

        """Set up Redis container."""

        container = RedisContainer()

        redis_url = await container.start()

        yield container, redis_url

        await container.stop()
    
    @pytest.fixture

    async def redis_client(self, redis_container):

        """Create Redis client."""

        _, redis_url = redis_container

        client = redis.Redis.from_url(redis_url, decode_responses=True)

        yield client

        await client.close()
    
    @pytest.fixture

    async def jwt_service(self, redis_client):

        """Initialize JWT service."""

        service = JWTService()
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.redis_manager.RedisManager.get_client') as mock_redis:

            mock_redis.return_value = redis_client

            await service.initialize()

            yield service

            await service.shutdown()
    
    @pytest.fixture

    async def session_manager(self, redis_client):

        """Initialize session manager."""

        manager = SessionManager()
        
        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.redis_manager.RedisManager.get_client') as mock_redis:

            mock_redis.return_value = redis_client

            await manager.initialize()

            yield manager

            await manager.shutdown()
    
    @pytest.fixture

    async def websocket_manager(self, redis_client):

        """Create WebSocket manager."""

        # Mock: Redis external service isolation for fast, reliable tests without network dependency
        with patch('netra_backend.app.ws_manager.redis_manager') as mock_redis_mgr:

            test_redis_mgr = RedisManager()

            test_redis_mgr.enabled = True

            test_redis_mgr.redis_client = redis_client

            mock_redis_mgr.return_value = test_redis_mgr

            mock_redis_mgr.get_client.return_value = redis_client
            
            manager = WebSocketManager()

            yield manager
    
    @pytest.fixture

    async def multi_device_manager(self, jwt_service, session_manager, websocket_manager, redis_client):

        """Create multi-device session manager."""

        manager = MultiDeviceSessionManager(jwt_service, session_manager, websocket_manager, redis_client)

        yield manager

        await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_create_multiple_device_sessions(self, multi_device_manager):

        """Test creating multiple device sessions for the same user."""

        user_id = f"multi_device_user_{uuid.uuid4().hex[:8]}"
        
        # Create sessions for different devices

        devices = [

            ("desktop", {"os": "Windows", "browser": "Chrome"}),

            ("mobile", {"os": "iOS", "app_version": "1.2.3"}),

            ("tablet", {"os": "Android", "app_version": "1.2.3"})

        ]
        
        device_sessions = []

        for device_type, metadata in devices:

            session = await multi_device_manager.create_device_session(

                user_id, device_type, metadata

            )

            device_sessions.append(session)
        
        # Verify all sessions created

        assert len(device_sessions) == 3

        assert user_id in multi_device_manager.user_devices

        assert len(multi_device_manager.user_devices[user_id]) == 3
        
        # Verify unique device IDs

        device_ids = [session.device_id for session in device_sessions]

        assert len(set(device_ids)) == 3
        
        # Verify all WebSocket connections active

        for session in device_sessions:

            assert not session.websocket.closed

            assert session.user_id in multi_device_manager.websocket_manager.active_connections
        
        # Verify device sessions stored in Redis

        stored_sessions = await multi_device_manager.get_user_device_sessions(user_id)

        assert len(stored_sessions) == 3
        
        stored_device_ids = [session["device_id"] for session in stored_sessions]

        assert set(stored_device_ids) == set(device_ids)
    
    @pytest.mark.asyncio
    async def test_cross_device_state_synchronization(self, multi_device_manager):

        """Test state synchronization across multiple devices."""

        user_id = f"sync_user_{uuid.uuid4().hex[:8]}"
        
        # Create two device sessions

        desktop_session = await multi_device_manager.create_device_session(

            user_id, "desktop", {"os": "macOS"}

        )

        mobile_session = await multi_device_manager.create_device_session(

            user_id, "mobile", {"os": "iOS"}

        )
        
        # Simulate state change on desktop

        state_data = {

            "current_thread": "thread_abc123",

            "draft_message": "Hello from desktop",

            "cursor_position": 42,

            "last_modified": time.time()

        }
        
        # Sync state from desktop to other devices

        sync_result = await multi_device_manager.sync_state_across_devices(

            user_id, state_data, origin_device_id=desktop_session.device_id

        )
        
        # Verify sync result

        assert sync_result["devices_targeted"] == 1  # Only mobile should receive

        assert sync_result["successful_syncs"] == 1
        
        # Wait for message delivery

        await asyncio.sleep(0.1)
        
        # Verify mobile received sync message

        mobile_messages = mobile_session.websocket.messages

        assert len(mobile_messages) > 0
        
        sync_message = None

        for msg in mobile_messages:

            if msg.get("type") == "state_sync":

                sync_message = msg

                break
        
        assert sync_message is not None

        assert sync_message["data"]["state"]["current_thread"] == "thread_abc123"

        assert sync_message["data"]["origin_device"] == desktop_session.device_id
        
        # Verify desktop didn't receive its own sync

        desktop_messages = desktop_session.websocket.messages

        sync_to_desktop = any(msg.get("type") == "state_sync" for msg in desktop_messages)

        assert not sync_to_desktop
    
    @pytest.mark.asyncio
    async def test_concurrent_device_state_conflicts(self, multi_device_manager):

        """Test handling of concurrent state changes across devices."""

        user_id = f"conflict_user_{uuid.uuid4().hex[:8]}"
        
        # Create three device sessions

        desktop = await multi_device_manager.create_device_session(user_id, "desktop")

        mobile = await multi_device_manager.create_device_session(user_id, "mobile")

        tablet = await multi_device_manager.create_device_session(user_id, "tablet")
        
        # Simulate concurrent edits

        desktop_state = {

            "document_content": "Desktop edit at " + str(time.time()),

            "edit_timestamp": time.time()

        }
        
        mobile_state = {

            "document_content": "Mobile edit at " + str(time.time()),

            "edit_timestamp": time.time() + 0.1  # Slightly later

        }
        
        # Update activity to simulate concurrent access

        desktop.update_activity()

        await asyncio.sleep(0.05)

        mobile.update_activity()  # Mobile is more recent
        
        # Handle conflict

        conflict_result = await multi_device_manager.handle_device_conflict(

            user_id, "concurrent_edit", [desktop, mobile, tablet]

        )
        
        # Verify conflict resolution

        assert conflict_result["action"] == "concurrent_edit"

        assert conflict_result["resolution"] == "last_write_wins"

        assert conflict_result["winner_device"] == mobile.device_id  # Most recent activity

        assert len(conflict_result["devices_involved"]) == 3
        
        # Verify conflict stored in Redis

        conflict_key = f"conflicts:{user_id}"

        conflicts = await multi_device_manager.redis_client.lrange(conflict_key, 0, -1)

        assert len(conflicts) > 0
        
        latest_conflict = json.loads(conflicts[0])

        assert latest_conflict["conflict_id"] == conflict_result["conflict_id"]
    
    @pytest.mark.asyncio
    async def test_device_session_limit_enforcement(self, multi_device_manager):

        """Test enforcement of maximum device sessions per user."""

        user_id = f"limit_user_{uuid.uuid4().hex[:8]}"
        
        # Create sessions up to the limit

        device_sessions = []

        device_types = ["desktop1", "mobile1", "tablet1", "desktop2", "mobile2"]  # 5 devices
        
        for device_type in device_types:

            session = await multi_device_manager.create_device_session(user_id, device_type)

            device_sessions.append(session)

            await asyncio.sleep(0.1)  # Ensure different timestamps
        
        # Trigger session limit check

        conflict_result = await multi_device_manager.handle_device_conflict(

            user_id, "session_limit", device_sessions

        )
        
        # Verify limit enforcement

        assert conflict_result["action"] == "session_limit"

        assert conflict_result["resolution"] == "session_limit_enforced"

        assert conflict_result["winner_device"] == device_sessions[-1].device_id  # Most recent
        
        # Verify all sessions are tracked

        stored_sessions = await multi_device_manager.get_user_device_sessions(user_id)

        assert len(stored_sessions) == 5
    
    @pytest.mark.asyncio
    async def test_device_disconnection_and_reconnection(self, multi_device_manager):

        """Test device disconnection and reconnection scenarios."""

        user_id = f"reconnect_user_{uuid.uuid4().hex[:8]}"
        
        # Create initial session

        mobile_session = await multi_device_manager.create_device_session(

            user_id, "mobile", {"connection_id": "initial"}

        )
        
        # Verify session active

        assert not mobile_session.websocket.closed

        assert user_id in multi_device_manager.websocket_manager.active_connections
        
        # Simulate disconnection

        await multi_device_manager.websocket_manager.disconnect_user(

            user_id, mobile_session.websocket

        )
        
        # Verify disconnection

        assert mobile_session.websocket.closed
        
        # Create new session (reconnection)

        reconnect_session = await multi_device_manager.create_device_session(

            user_id, "mobile", {"connection_id": "reconnected"}

        )
        
        # Verify new session is different but functional

        assert reconnect_session.device_id != mobile_session.device_id

        assert not reconnect_session.websocket.closed

        assert user_id in multi_device_manager.websocket_manager.active_connections
        
        # Test state sync after reconnection

        sync_state = {"reconnection_test": True, "timestamp": time.time()}

        sync_result = await multi_device_manager.sync_state_across_devices(

            user_id, sync_state, origin_device_id="external"

        )
        
        assert sync_result["successful_syncs"] == 1
        
        # Verify reconnected device received sync

        await asyncio.sleep(0.1)

        messages = reconnect_session.websocket.messages

        sync_received = any(msg.get("type") == "state_sync" for msg in messages)

        assert sync_received
    
    @pytest.mark.asyncio
    async def test_cross_device_message_ordering(self, multi_device_manager):

        """Test message ordering consistency across devices."""

        user_id = f"ordering_user_{uuid.uuid4().hex[:8]}"
        
        # Create two device sessions

        device1 = await multi_device_manager.create_device_session(user_id, "device1")

        device2 = await multi_device_manager.create_device_session(user_id, "device2")
        
        # Send sequence of state syncs

        message_count = 10

        sync_tasks = []
        
        for i in range(message_count):

            state_data = {

                "sequence_number": i,

                "message": f"State update {i}",

                "timestamp": time.time()

            }
            
            task = multi_device_manager.sync_state_across_devices(

                user_id, state_data, origin_device_id=device1.device_id

            )

            sync_tasks.append(task)
            
            # Small delay to ensure ordering

            await asyncio.sleep(0.01)
        
        # Wait for all syncs to complete

        sync_results = await asyncio.gather(*sync_tasks)
        
        # Verify all syncs succeeded

        total_successful = sum(result["successful_syncs"] for result in sync_results)

        assert total_successful == message_count
        
        # Verify message ordering on receiving device

        await asyncio.sleep(0.2)  # Allow all messages to be delivered
        
        device2_sync_messages = [

            msg for msg in device2.websocket.messages 

            if msg.get("type") == "state_sync"

        ]
        
        assert len(device2_sync_messages) == message_count
        
        # Check sequence ordering

        sequence_numbers = [

            msg["data"]["state"]["sequence_number"] 

            for msg in device2_sync_messages

        ]
        
        # Should be in order (0, 1, 2, ..., 9)

        assert sequence_numbers == list(range(message_count))

if __name__ == "__main__":

    pytest.main([__file__, "-v", "-s", "--tb=short"])