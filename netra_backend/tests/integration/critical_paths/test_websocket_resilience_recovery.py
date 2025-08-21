"""WebSocket Resilience and Recovery Critical Path Tests

Business Value Justification (BVJ):
- Segment: All tiers (core communication infrastructure)
- Business Goal: Maintain real-time communication and user engagement
- Value Impact: Prevents user session loss, ensures continuous connectivity
- Strategic Impact: $30K-50K MRR protection through reliable real-time features

Critical Path: Connection loss detection -> State preservation -> Reconnection -> State recovery -> Message synchronization
Coverage: Connection resilience, state persistence, automatic recovery, message integrity
"""

import pytest
import asyncio
import time
import uuid
import json
import logging
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from netra_backend.app.services.websocket.ws_manager import WebSocketManager
from netra_backend.app.services.websocket.connection_recovery import ConnectionRecovery
from netra_backend.app.services.state_persistence import StatePersistenceService
from netra_backend.app.schemas.registry import WebSocketMessage

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()


logger = logging.getLogger(__name__)


class WebSocketResilienceManager:
    """Manages WebSocket resilience testing with connection simulation."""
    
    def __init__(self):
        self.ws_manager = None
        self.recovery_service = None
        self.state_service = None
        self.active_connections = {}
        self.disconnection_events = []
        self.recovery_metrics = {
            "total_disconnections": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "average_recovery_time": 0,
            "state_preservation_rate": 0
        }
        
    async def initialize_services(self):
        """Initialize WebSocket resilience services."""
        try:
            self.ws_manager = WebSocketManager()
            await self.ws_manager.initialize()
            
            self.recovery_service = ConnectionRecovery()
            await self.recovery_service.initialize()
            
            self.state_service = StatePersistenceService()
            await self.state_service.initialize()
            
            logger.info("WebSocket resilience services initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize resilience services: {e}")
            raise
    
    async def create_websocket_session(self, user_id: str, session_data: Dict = None) -> str:
        """Create a WebSocket session with state tracking."""
        session_id = f"ws_session_{uuid.uuid4().hex[:12]}"
        
        try:
            # Create connection
            connection_data = {
                "session_id": session_id,
                "user_id": user_id,
                "connected_at": time.time(),
                "state": session_data or {},
                "status": "connected",
                "message_queue": [],
                "last_heartbeat": time.time()
            }
            
            self.active_connections[session_id] = connection_data
            
            # Initialize state persistence
            await self.state_service.save_session_state(session_id, connection_data["state"])
            
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create WebSocket session: {e}")
            raise
    
    async def simulate_connection_loss(self, session_id: str, 
                                     disconnection_type: str = "network_timeout") -> Dict[str, Any]:
        """Simulate various types of connection loss."""
        if session_id not in self.active_connections:
            raise ValueError(f"Session {session_id} not found")
        
        connection = self.active_connections[session_id]
        disconnection_time = time.time()
        
        try:
            # Record disconnection event
            disconnection_event = {
                "session_id": session_id,
                "user_id": connection["user_id"],
                "disconnection_type": disconnection_type,
                "disconnection_time": disconnection_time,
                "state_at_disconnection": connection["state"].copy(),
                "pending_messages": len(connection["message_queue"])
            }
            
            self.disconnection_events.append(disconnection_event)
            self.recovery_metrics["total_disconnections"] += 1
            
            # Preserve state before disconnection
            state_preserved = await self.preserve_connection_state(session_id, connection)
            
            # Update connection status
            connection["status"] = "disconnected"
            connection["disconnected_at"] = disconnection_time
            connection["disconnection_type"] = disconnection_type
            
            return {
                "disconnection_successful": True,
                "state_preserved": state_preserved,
                "disconnection_event": disconnection_event
            }
            
        except Exception as e:
            return {
                "disconnection_successful": False,
                "error": str(e)
            }
    
    async def preserve_connection_state(self, session_id: str, connection: Dict) -> bool:
        """Preserve connection state before disconnection."""
        try:
            state_snapshot = {
                "session_id": session_id,
                "user_id": connection["user_id"],
                "application_state": connection["state"],
                "message_queue": connection["message_queue"],
                "last_heartbeat": connection["last_heartbeat"],
                "preservation_time": time.time()
            }
            
            await self.state_service.save_disconnection_state(session_id, state_snapshot)
            return True
            
        except Exception as e:
            logger.error(f"Failed to preserve state for {session_id}: {e}")
            return False
    
    async def attempt_reconnection(self, session_id: str, recovery_token: str = None) -> Dict[str, Any]:
        """Attempt to reconnect and recover session state."""
        if session_id not in self.active_connections:
            return {"success": False, "error": "Session not found"}
        
        connection = self.active_connections[session_id]
        recovery_start_time = time.time()
        
        try:
            # Validate recovery token if provided
            if recovery_token:
                token_valid = await self.validate_recovery_token(session_id, recovery_token)
                if not token_valid:
                    return {"success": False, "error": "Invalid recovery token"}
            
            # Recover preserved state
            state_recovery = await self.recover_session_state(session_id)
            if not state_recovery["success"]:
                return {"success": False, "error": f"State recovery failed: {state_recovery['error']}"}
            
            # Restore connection
            connection["status"] = "connected"
            connection["reconnected_at"] = time.time()
            connection["recovery_time"] = time.time() - recovery_start_time
            
            # Restore application state
            recovered_state = state_recovery["recovered_state"]
            connection["state"] = recovered_state.get("application_state", {})
            connection["message_queue"] = recovered_state.get("message_queue", [])
            
            # Update recovery metrics
            self.recovery_metrics["successful_recoveries"] += 1
            self.update_average_recovery_time(connection["recovery_time"])
            
            return {
                "success": True,
                "recovery_time": connection["recovery_time"],
                "state_recovered": True,
                "messages_restored": len(connection["message_queue"]),
                "recovered_state": recovered_state
            }
            
        except Exception as e:
            self.recovery_metrics["failed_recoveries"] += 1
            return {
                "success": False,
                "error": str(e),
                "recovery_time": time.time() - recovery_start_time
            }
    
    async def validate_recovery_token(self, session_id: str, recovery_token: str) -> bool:
        """Validate recovery token for session restoration."""
        try:
            # Simulate token validation
            expected_token = f"recovery_{session_id}_{int(time.time() // 300)}"  # 5-minute window
            return recovery_token == expected_token
            
        except Exception:
            return False
    
    async def recover_session_state(self, session_id: str) -> Dict[str, Any]:
        """Recover session state from persistence layer."""
        try:
            preserved_state = await self.state_service.load_disconnection_state(session_id)
            
            if not preserved_state:
                return {"success": False, "error": "No preserved state found"}
            
            # Validate state integrity
            required_fields = ["session_id", "user_id", "application_state"]
            for field in required_fields:
                if field not in preserved_state:
                    return {"success": False, "error": f"Missing field: {field}"}
            
            return {
                "success": True,
                "recovered_state": preserved_state
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_message_delivery_during_reconnection(self, session_id: str) -> Dict[str, Any]:
        """Test message delivery and queuing during reconnection process."""
        if session_id not in self.active_connections:
            return {"success": False, "error": "Session not found"}
        
        connection = self.active_connections[session_id]
        
        try:
            # Send messages while disconnected
            test_messages = [
                {"id": str(uuid.uuid4()), "content": f"Test message {i}", "timestamp": time.time()}
                for i in range(3)
            ]
            
            if connection["status"] == "disconnected":
                # Queue messages for delivery after reconnection
                connection["message_queue"].extend(test_messages)
                
                return {
                    "success": True,
                    "messages_queued": len(test_messages),
                    "total_queue_size": len(connection["message_queue"])
                }
            else:
                # Deliver immediately if connected
                for message in test_messages:
                    await self.deliver_message(session_id, message)
                
                return {
                    "success": True,
                    "messages_delivered": len(test_messages),
                    "delivery_method": "immediate"
                }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def deliver_message(self, session_id: str, message: Dict[str, Any]):
        """Deliver message to WebSocket connection."""
        # Simulate message delivery
        await asyncio.sleep(0.01)
        
        # In real implementation, would send via WebSocket
        connection = self.active_connections[session_id]
        if "delivered_messages" not in connection:
            connection["delivered_messages"] = []
        connection["delivered_messages"].append(message)
    
    def update_average_recovery_time(self, new_recovery_time: float):
        """Update running average of recovery times."""
        current_avg = self.recovery_metrics["average_recovery_time"]
        successful_recoveries = self.recovery_metrics["successful_recoveries"]
        
        if successful_recoveries == 1:
            self.recovery_metrics["average_recovery_time"] = new_recovery_time
        else:
            self.recovery_metrics["average_recovery_time"] = (
                (current_avg * (successful_recoveries - 1) + new_recovery_time) / successful_recoveries
            )
    
    async def get_resilience_metrics(self) -> Dict[str, Any]:
        """Get comprehensive resilience metrics."""
        total_attempts = (self.recovery_metrics["successful_recoveries"] + 
                         self.recovery_metrics["failed_recoveries"])
        
        success_rate = 0
        if total_attempts > 0:
            success_rate = (self.recovery_metrics["successful_recoveries"] / total_attempts) * 100
        
        # Calculate state preservation rate
        preserved_states = sum(1 for event in self.disconnection_events if "state_at_disconnection" in event)
        preservation_rate = 0
        if self.disconnection_events:
            preservation_rate = (preserved_states / len(self.disconnection_events)) * 100
        
        return {
            "total_connections": len(self.active_connections),
            "active_connections": len([c for c in self.active_connections.values() if c["status"] == "connected"]),
            "total_disconnections": self.recovery_metrics["total_disconnections"],
            "successful_recoveries": self.recovery_metrics["successful_recoveries"],
            "failed_recoveries": self.recovery_metrics["failed_recoveries"],
            "recovery_success_rate": success_rate,
            "average_recovery_time": self.recovery_metrics["average_recovery_time"],
            "state_preservation_rate": preservation_rate,
            "disconnection_types": self.get_disconnection_type_breakdown()
        }
    
    def get_disconnection_type_breakdown(self) -> Dict[str, int]:
        """Get breakdown of disconnection types."""
        breakdown = {}
        for event in self.disconnection_events:
            disc_type = event["disconnection_type"]
            breakdown[disc_type] = breakdown.get(disc_type, 0) + 1
        return breakdown
    
    async def cleanup(self):
        """Clean up resources."""
        try:
            if self.ws_manager:
                await self.ws_manager.shutdown()
            if self.recovery_service:
                await self.recovery_service.shutdown()
            if self.state_service:
                await self.state_service.shutdown()
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")


@pytest.fixture
async def resilience_manager():
    """Create WebSocket resilience manager for testing."""
    manager = WebSocketResilienceManager()
    await manager.initialize_services()
    yield manager
    await manager.cleanup()


@pytest.mark.asyncio
async def test_network_timeout_recovery(resilience_manager):
    """Test recovery from network timeout disconnection."""
    user_id = "timeout_test_user"
    session_data = {"current_conversation": "test_conversation", "message_count": 5}
    
    # Create session
    session_id = await resilience_manager.create_websocket_session(user_id, session_data)
    
    # Simulate network timeout
    disconnect_result = await resilience_manager.simulate_connection_loss(
        session_id, "network_timeout"
    )
    
    assert disconnect_result["disconnection_successful"] is True
    assert disconnect_result["state_preserved"] is True
    
    # Attempt reconnection
    recovery_result = await resilience_manager.attempt_reconnection(session_id)
    
    assert recovery_result["success"] is True
    assert recovery_result["state_recovered"] is True
    assert recovery_result["recovery_time"] < 3.0  # Should be fast
    
    # Verify state restoration
    recovered_state = recovery_result["recovered_state"]
    assert recovered_state["application_state"]["current_conversation"] == "test_conversation"
    assert recovered_state["application_state"]["message_count"] == 5


@pytest.mark.asyncio
async def test_server_restart_recovery(resilience_manager):
    """Test recovery from server restart scenario."""
    user_id = "restart_test_user"
    session_data = {"workspace_id": "workspace_123", "active_tools": ["search", "calculator"]}
    
    # Create session
    session_id = await resilience_manager.create_websocket_session(user_id, session_data)
    
    # Simulate server restart
    disconnect_result = await resilience_manager.simulate_connection_loss(
        session_id, "server_restart"
    )
    
    assert disconnect_result["disconnection_successful"] is True
    
    # Wait to simulate server restart delay
    await asyncio.sleep(0.1)
    
    # Attempt reconnection with recovery token
    recovery_token = f"recovery_{session_id}_{int(time.time() // 300)}"
    recovery_result = await resilience_manager.attempt_reconnection(session_id, recovery_token)
    
    assert recovery_result["success"] is True
    assert recovery_result["state_recovered"] is True
    
    # Verify workspace and tools restored
    recovered_state = recovery_result["recovered_state"]
    assert recovered_state["application_state"]["workspace_id"] == "workspace_123"
    assert "search" in recovered_state["application_state"]["active_tools"]


@pytest.mark.asyncio
async def test_message_queuing_during_disconnection(resilience_manager):
    """Test message queuing and delivery after reconnection."""
    user_id = "message_queue_user"
    
    # Create session
    session_id = await resilience_manager.create_websocket_session(user_id, {})
    
    # Simulate disconnection
    await resilience_manager.simulate_connection_loss(session_id, "network_interruption")
    
    # Send messages while disconnected
    message_result = await resilience_manager.test_message_delivery_during_reconnection(session_id)
    
    assert message_result["success"] is True
    assert message_result["messages_queued"] == 3
    assert message_result["total_queue_size"] >= 3
    
    # Reconnect
    recovery_result = await resilience_manager.attempt_reconnection(session_id)
    
    assert recovery_result["success"] is True
    assert recovery_result["messages_restored"] >= 3
    
    # Verify messages can be delivered after reconnection
    post_reconnection_result = await resilience_manager.test_message_delivery_during_reconnection(session_id)
    assert post_reconnection_result["delivery_method"] == "immediate"


@pytest.mark.asyncio
async def test_concurrent_reconnection_attempts(resilience_manager):
    """Test handling of multiple concurrent reconnection attempts."""
    user_id = "concurrent_user"
    
    # Create multiple sessions
    session_ids = []
    for i in range(3):
        session_data = {"session_number": i, "user_data": f"data_{i}"}
        session_id = await resilience_manager.create_websocket_session(user_id, session_data)
        session_ids.append(session_id)
    
    # Disconnect all sessions
    for session_id in session_ids:
        await resilience_manager.simulate_connection_loss(session_id, "network_issue")
    
    # Attempt concurrent reconnections
    reconnection_tasks = [
        resilience_manager.attempt_reconnection(session_id)
        for session_id in session_ids
    ]
    
    results = await asyncio.gather(*reconnection_tasks)
    
    # Verify all reconnections succeeded
    successful_reconnections = [r for r in results if r["success"]]
    assert len(successful_reconnections) == 3
    
    # Verify recovery times are reasonable
    for result in successful_reconnections:
        assert result["recovery_time"] < 5.0


@pytest.mark.asyncio
async def test_invalid_recovery_token_handling(resilience_manager):
    """Test handling of invalid recovery tokens."""
    user_id = "invalid_token_user"
    
    # Create session
    session_id = await resilience_manager.create_websocket_session(user_id, {})
    
    # Simulate disconnection
    await resilience_manager.simulate_connection_loss(session_id, "network_timeout")
    
    # Attempt reconnection with invalid token
    invalid_token = "invalid_recovery_token_123"
    recovery_result = await resilience_manager.attempt_reconnection(session_id, invalid_token)
    
    assert recovery_result["success"] is False
    assert "Invalid recovery token" in recovery_result["error"]
    
    # Attempt reconnection without token (should succeed)
    recovery_result_no_token = await resilience_manager.attempt_reconnection(session_id)
    assert recovery_result_no_token["success"] is True


@pytest.mark.asyncio
async def test_resilience_performance_metrics(resilience_manager):
    """Test resilience performance meets requirements."""
    # Create multiple sessions and test various scenarios
    scenarios = [
        ("network_timeout", "fast_recovery"),
        ("server_restart", "medium_recovery"),
        ("connection_drop", "fast_recovery"),
        ("browser_refresh", "instant_recovery")
    ]
    
    for disconnect_type, expected_speed in scenarios:
        user_id = f"perf_user_{disconnect_type}"
        session_id = await resilience_manager.create_websocket_session(user_id, {"test": True})
        
        # Disconnect and reconnect
        await resilience_manager.simulate_connection_loss(session_id, disconnect_type)
        recovery_result = await resilience_manager.attempt_reconnection(session_id)
        
        assert recovery_result["success"] is True
        
        # Verify performance requirements
        recovery_time = recovery_result["recovery_time"]
        if expected_speed == "instant_recovery":
            assert recovery_time < 0.5
        elif expected_speed == "fast_recovery":
            assert recovery_time < 2.0
        elif expected_speed == "medium_recovery":
            assert recovery_time < 5.0
    
    # Get overall metrics
    metrics = await resilience_manager.get_resilience_metrics()
    
    assert metrics["recovery_success_rate"] >= 95.0
    assert metrics["average_recovery_time"] < 3.0
    assert metrics["state_preservation_rate"] >= 95.0


@pytest.mark.asyncio
async def test_state_preservation_integrity(resilience_manager):
    """Test that state preservation maintains data integrity."""
    user_id = "integrity_test_user"
    complex_state = {
        "workspace": {
            "id": "ws_123",
            "name": "Test Workspace",
            "tools": ["search", "calculator", "file_manager"]
        },
        "conversation": {
            "thread_id": "thread_456",
            "messages": [
                {"id": "msg_1", "content": "Hello", "timestamp": time.time()},
                {"id": "msg_2", "content": "How are you?", "timestamp": time.time()}
            ]
        },
        "user_preferences": {
            "theme": "dark",
            "language": "en",
            "notifications": True
        }
    }
    
    # Create session with complex state
    session_id = await resilience_manager.create_websocket_session(user_id, complex_state)
    
    # Simulate disconnection
    disconnect_result = await resilience_manager.simulate_connection_loss(session_id, "data_integrity_test")
    assert disconnect_result["state_preserved"] is True
    
    # Reconnect and verify state integrity
    recovery_result = await resilience_manager.attempt_reconnection(session_id)
    assert recovery_result["success"] is True
    
    recovered_state = recovery_result["recovered_state"]["application_state"]
    
    # Verify complex nested structure preserved
    assert recovered_state["workspace"]["id"] == "ws_123"
    assert len(recovered_state["workspace"]["tools"]) == 3
    assert "search" in recovered_state["workspace"]["tools"]
    
    assert recovered_state["conversation"]["thread_id"] == "thread_456"
    assert len(recovered_state["conversation"]["messages"]) == 2
    
    assert recovered_state["user_preferences"]["theme"] == "dark"
    assert recovered_state["user_preferences"]["notifications"] is True