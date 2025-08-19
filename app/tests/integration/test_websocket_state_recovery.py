"""
WebSocket State Recovery Integration Test

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise, Mid, Early - All customers depend on connection reliability
2. **Business Goal**: Protect $35K MRR from connection drops and state loss 
3. **Value Impact**: Prevents critical workflow interruption during expensive AI operations
4. **Revenue Impact**: Connection drops = 20% customer frustration = potential $7K ARR churn
5. **Platform Stability**: Ensures state consistency for Enterprise tier SLA compliance

Tests WebSocket reconnection with complete state preservation, message queue recovery,
and active thread restoration. Critical for maintaining customer trust during network disruptions.
"""

import pytest
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch

from app.core.websocket_recovery_manager import websocket_recovery_manager
from app.core.websocket_connection_manager import WebSocketConnectionManager
from app.core.websocket_recovery_types import ConnectionState, ReconnectionConfig
from app.schemas.websocket_message_types import WebSocketMessage
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestWebSocketStateRecovery:
    """Integration tests for WebSocket state recovery and preservation."""

    @pytest.fixture
    async def recovery_test_setup(self):
        """Setup test environment for state recovery testing."""
        return await self._create_recovery_test_env()

    @pytest.fixture
    def websocket_config(self):
        """Create WebSocket configuration for testing."""
        return self._create_websocket_config()

    @pytest.fixture
    def workflow_state_data(self):
        """Create workflow state data for testing."""
        return self._create_workflow_state_data()

    async def _create_recovery_test_env(self):
        """Create isolated test environment for state recovery."""
        # Use real WebSocket recovery manager
        recovery_manager = websocket_recovery_manager
        
        # Clean any existing connections
        await recovery_manager.cleanup_all()
        
        # Test WebSocket server URL (mock server will be created)
        test_server_url = "ws://localhost:8765/test"
        
        return {
            "recovery_manager": recovery_manager,
            "server_url": test_server_url,
            "test_session_id": str(uuid.uuid4())
        }

    def _create_websocket_config(self):
        """Create WebSocket configuration for testing."""
        return ReconnectionConfig(
            max_attempts=3,
            initial_delay=0.1,  # Fast retry for testing
            max_delay=1.0,
            timeout_seconds=5.0,
            max_pending_messages=100
        )

    def _create_workflow_state_data(self):
        """Create comprehensive workflow state data."""
        workflow_id = str(uuid.uuid4())
        thread_id = str(uuid.uuid4())
        
        return {
            "workflow_id": workflow_id,
            "thread_id": thread_id,
            "user_id": str(uuid.uuid4()),
            "session_state": {
                "active_agents": ["TriageAgent", "DataAgent"],
                "current_stage": "data_analysis",
                "progress_percentage": 65,
                "last_update": datetime.now(timezone.utc).isoformat()
            },
            "message_history": [
                {"type": "agent_started", "agent": "TriageAgent", "timestamp": datetime.now(timezone.utc).isoformat()},
                {"type": "progress_update", "progress": 30, "timestamp": datetime.now(timezone.utc).isoformat()},
                {"type": "progress_update", "progress": 65, "timestamp": datetime.now(timezone.utc).isoformat()}
            ],
            "pending_operations": [
                {"operation": "data_validation", "priority": "high"},
                {"operation": "result_compilation", "priority": "medium"}
            ]
        }

    async def test_websocket_reconnection_with_state_preservation(
        self, recovery_test_setup, websocket_config, workflow_state_data
    ):
        """
        Test WebSocket reconnection after service restart with complete state preservation.
        
        BVJ: Protects $35K MRR by ensuring no workflow state is lost during reconnections.
        Enterprise customers require guaranteed state consistency for SLA compliance.
        """
        test_env = recovery_test_setup
        config = websocket_config
        state_data = workflow_state_data
        
        # Phase 1: Establish connection and build state
        connection_manager = await self._establish_connection_with_state(
            test_env, config, state_data
        )
        
        # Phase 2: Simulate connection drop
        disconnection_state = await self._simulate_connection_drop(
            connection_manager, state_data
        )
        
        # Phase 3: Reconnect and verify state recovery
        restored_manager = await self._reconnect_and_restore_state(
            test_env, config, disconnection_state
        )
        
        # Phase 4: Verify complete state preservation
        await self._verify_state_preservation(
            restored_manager, state_data, disconnection_state
        )

    async def _establish_connection_with_state(self, test_env, config, state_data):
        """Establish WebSocket connection and build workflow state."""
        connection_id = f"test_conn_{state_data['workflow_id']}"
        
        # Create connection manager with mock WebSocket server
        with patch('websockets.connect') as mock_connect:
            mock_websocket = await self._create_mock_websocket()
            
            # Make the mock_connect coroutine awaitable
            async def mock_connect_coroutine(*args, **kwargs):
                return mock_websocket
            
            mock_connect.side_effect = mock_connect_coroutine
            
            # Create connection through recovery manager
            manager = await test_env["recovery_manager"].create_connection(
                connection_id, test_env["server_url"], config
            )
            
            # Establish connection
            success = await manager.connect()
            assert success, "Initial connection should succeed"
            assert manager.state == ConnectionState.CONNECTED
            
            # Build workflow state through message sending
            await self._build_workflow_state(manager, state_data)
            
            return manager

    async def _create_mock_websocket(self):
        """Create mock WebSocket for testing."""
        import websockets
        
        # Create a proper mock that can be awaited
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock()
        mock_ws.send = AsyncMock()
        mock_ws.close = AsyncMock()
        mock_ws.ping = AsyncMock()
        
        # Configure message receiving behavior  
        mock_ws.recv.side_effect = [
            json.dumps({"type": "connection_ack", "status": "connected"}),
            json.dumps({"type": "pong"}),
        ]
        
        # Make the mock awaitable by returning itself
        mock_ws.__aenter__ = AsyncMock(return_value=mock_ws)
        mock_ws.__aexit__ = AsyncMock(return_value=None)
        
        return mock_ws

    async def _build_workflow_state(self, manager, state_data):
        """Build workflow state by sending messages."""
        # Send workflow initialization messages
        init_messages = [
            {
                "type": "workflow_start",
                "workflow_id": state_data["workflow_id"],
                "thread_id": state_data["thread_id"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            {
                "type": "agent_activation",
                "agents": state_data["session_state"]["active_agents"],
                "workflow_id": state_data["workflow_id"]
            },
            {
                "type": "state_update",
                "progress": state_data["session_state"]["progress_percentage"],
                "stage": state_data["session_state"]["current_stage"]
            }
        ]
        
        # Send messages and verify they are processed
        for message in init_messages:
            success = await manager.send_message(message, require_ack=True)
            assert success, f"Message should be sent successfully: {message['type']}"
        
        # Allow message processing
        await asyncio.sleep(0.1)

    async def _simulate_connection_drop(self, manager, state_data):
        """Simulate sudden connection drop."""
        # Capture state before disconnection
        pre_disconnect_status = manager.get_status()
        
        # Force connection state to simulate network failure
        manager.state = ConnectionState.DISCONNECTED
        manager.websocket = None
        
        # Attempt to send message during disconnection (should queue)
        disconnect_message = {
            "type": "emergency_update",
            "workflow_id": state_data["workflow_id"],
            "message": "Connection lost during critical operation",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # This should queue the message instead of failing
        queued = await manager.send_message(disconnect_message, require_ack=True)
        assert not queued or manager.message_handler.get_pending_count() > 0
        
        return {
            "pre_disconnect_status": pre_disconnect_status,
            "pending_messages": manager.message_handler.pending_messages.copy(),
            "connection_metrics": manager.metrics,
            "disconnect_message": disconnect_message
        }

    async def _reconnect_and_restore_state(self, test_env, config, disconnect_state):
        """Reconnect WebSocket and restore state."""
        # Create new connection manager for reconnection
        reconnect_id = f"reconnect_{test_env['test_session_id']}"
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = await self._create_mock_websocket()
            mock_connect.return_value = mock_websocket
            
            # Create new connection
            restored_manager = await test_env["recovery_manager"].create_connection(
                reconnect_id, test_env["server_url"], config
            )
            
            # Simulate state restoration by copying pending messages
            restored_manager.message_handler.pending_messages = disconnect_state["pending_messages"]
            
            # Reconnect
            success = await restored_manager.connect()
            assert success, "Reconnection should succeed"
            assert restored_manager.state == ConnectionState.CONNECTED
            
            return restored_manager

    async def _verify_state_preservation(self, manager, original_state, disconnect_state):
        """Verify complete state preservation after reconnection."""
        # Verify connection is healthy
        status = manager.get_status()
        assert status["state"] == ConnectionState.CONNECTED.value
        
        # Verify pending messages are preserved
        pending_count = status["pending_messages"]
        assert pending_count >= 1, "Disconnect message should be queued"
        
        # Verify message queue ordering
        if manager.message_handler.pending_messages:
            last_message = manager.message_handler.pending_messages[-1]
            assert last_message.message.get("type") == "emergency_update"
            assert last_message.message.get("workflow_id") == original_state["workflow_id"]
        
        # Send recovery verification message
        verify_message = {
            "type": "state_verification",
            "workflow_id": original_state["workflow_id"],
            "verification_token": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        success = await manager.send_message(verify_message)
        assert success, "State verification message should be sent"

    async def test_message_queue_preservation_during_disconnect(
        self, recovery_test_setup, websocket_config, workflow_state_data
    ):
        """
        Test message queue preservation and ordering during disconnection.
        
        BVJ: Ensures no critical workflow updates are lost. Message loss = workflow 
        inconsistency = customer frustration = potential churn.
        """
        test_env = recovery_test_setup
        config = websocket_config
        state_data = workflow_state_data
        
        # Setup connection with queued messages
        manager = await self._setup_connection_with_queued_messages(
            test_env, config, state_data
        )
        
        # Verify message ordering preservation
        await self._verify_message_ordering_preservation(manager, state_data)

    async def _setup_connection_with_queued_messages(self, test_env, config, state_data):
        """Setup connection and queue multiple messages."""
        connection_id = f"queue_test_{state_data['workflow_id']}"
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = await self._create_mock_websocket()
            mock_connect.return_value = mock_websocket
            
            manager = await test_env["recovery_manager"].create_connection(
                connection_id, test_env["server_url"], config
            )
            
            # Connect and then force disconnect to test queuing
            await manager.connect()
            manager.state = ConnectionState.DISCONNECTED
            manager.websocket = None
            
            # Queue multiple messages with different priorities
            queue_messages = [
                {"type": "urgent_alert", "priority": "high", "sequence": 1},
                {"type": "progress_update", "priority": "medium", "sequence": 2},
                {"type": "status_info", "priority": "low", "sequence": 3},
                {"type": "critical_error", "priority": "critical", "sequence": 4}
            ]
            
            for message in queue_messages:
                await manager.send_message(message, require_ack=True)
            
            return manager

    async def _verify_message_ordering_preservation(self, manager, state_data):
        """Verify message ordering is preserved in queue."""
        pending_messages = manager.message_handler.pending_messages
        assert len(pending_messages) >= 4, "All messages should be queued"
        
        # Verify messages maintain sequence order
        sequences = [msg.content.get("sequence") for msg in pending_messages if "sequence" in msg.content]
        assert sequences == sorted(sequences), "Message sequence should be preserved"

    async def test_active_thread_recovery_after_reconnection(
        self, recovery_test_setup, websocket_config, workflow_state_data
    ):
        """
        Test active thread recovery and continuation after reconnection.
        
        BVJ: Enterprise customers run long-duration AI operations (10-30 min).
        Thread interruption = workflow restart = time/cost loss = customer dissatisfaction.
        """
        test_env = recovery_test_setup
        config = websocket_config
        state_data = workflow_state_data
        
        # Simulate active thread with ongoing operations
        thread_state = await self._simulate_active_thread_state(
            test_env, config, state_data
        )
        
        # Disconnect and verify thread preservation
        await self._verify_thread_state_preservation(thread_state, state_data)

    async def _simulate_active_thread_state(self, test_env, config, state_data):
        """Simulate active thread with ongoing operations."""
        connection_id = f"thread_test_{state_data['thread_id']}"
        
        with patch('websockets.connect') as mock_connect:
            mock_websocket = await self._create_mock_websocket()
            mock_connect.return_value = mock_websocket
            
            manager = await test_env["recovery_manager"].create_connection(
                connection_id, test_env["server_url"], config
            )
            
            await manager.connect()
            
            # Simulate active thread operations
            thread_messages = [
                {
                    "type": "thread_start",
                    "thread_id": state_data["thread_id"],
                    "operation": "ai_optimization",
                    "estimated_duration": 1800  # 30 minutes
                },
                {
                    "type": "thread_progress",
                    "thread_id": state_data["thread_id"],
                    "progress": 45,
                    "current_operation": "data_analysis"
                }
            ]
            
            for message in thread_messages:
                await manager.send_message(message)
            
            return {
                "manager": manager,
                "thread_id": state_data["thread_id"],
                "active_operations": state_data["pending_operations"]
            }

    async def _verify_thread_state_preservation(self, thread_state, state_data):
        """Verify thread state is preserved during disconnection."""
        manager = thread_state["manager"]
        
        # Force disconnection
        manager.state = ConnectionState.DISCONNECTED
        
        # Send thread continuation message (should queue)
        continuation_message = {
            "type": "thread_continue",
            "thread_id": thread_state["thread_id"],
            "resume_from": "data_analysis",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        await manager.send_message(continuation_message)
        
        # Verify message is queued for thread continuation
        assert manager.message_handler.get_pending_count() > 0
        
        # Find the continuation message in queue
        continuation_found = False
        for pending_msg in manager.message_handler.pending_messages:
            if pending_msg.message.get("type") == "thread_continue":
                assert pending_msg.message.get("thread_id") == thread_state["thread_id"]
                continuation_found = True
                break
        
        assert continuation_found, "Thread continuation message should be queued"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])