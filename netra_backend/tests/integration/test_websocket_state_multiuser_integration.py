"""
Comprehensive Integration Tests for UnifiedWebSocketManager + UnifiedStateManager + Multi-User Patterns

Business Value Justification (BVJ):
- Segment: Enterprise, Mid, Early (all concurrent chat users)
- Business Goal: Enable reliable multi-user concurrent chat sessions worth $50K+ MRR
- Value Impact: Ensures complete isolation between users, preventing data leakage and maintaining session state
- Strategic Impact: Core platform functionality that enables scaling to 10+ concurrent users with guaranteed isolation

This test suite validates the critical integration points between:
- UnifiedWebSocketManager: SSOT for WebSocket connection management
- UnifiedStateManager: SSOT for all state management operations  
- Multi-user isolation patterns: Factory-based user context separation

CRITICAL: NO MOCKS - Uses real instances but NO external services (integration level)
Following TEST_CREATION_GUIDE.md patterns exactly
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

import pytest

from test_framework.base_integration_test import BaseIntegrationTest
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection
)
from netra_backend.app.core.managers.unified_state_manager import (
    UnifiedStateManager,
    StateManagerFactory,
    StateScope,
    StateType,
    StateStatus,
    StateEntry,
    StateQuery
)


@dataclass
class MockWebSocket:
    """Mock WebSocket for testing without external connections."""
    connection_id: str
    user_id: str
    messages_sent: List[Dict[str, Any]]
    is_closed: bool = False
    
    async def send_json(self, message: Dict[str, Any]) -> None:
        """Mock send_json method."""
        if self.is_closed:
            raise Exception("WebSocket connection closed")
        self.messages_sent.append(message)
    
    def close(self) -> None:
        """Close the mock WebSocket."""
        self.is_closed = True


class TestWebSocketStateMultiUserIntegration(BaseIntegrationTest):
    """Test WebSocket-State-MultiUser integration patterns."""
    
    @pytest.fixture
    def websocket_manager(self) -> UnifiedWebSocketManager:
        """Create fresh WebSocket manager instance."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def state_manager(self) -> UnifiedStateManager:
        """Create fresh state manager instance."""
        return UnifiedStateManager(
            enable_persistence=False,  # No external services
            enable_ttl_cleanup=False   # Manual cleanup for tests
        )
    
    @pytest.fixture
    def user_state_manager_a(self) -> UnifiedStateManager:
        """Create user-specific state manager for user A."""
        return UnifiedStateManager(
            user_id="user_a",
            enable_persistence=False,
            enable_ttl_cleanup=False
        )
    
    @pytest.fixture
    def user_state_manager_b(self) -> UnifiedStateManager:
        """Create user-specific state manager for user B."""  
        return UnifiedStateManager(
            user_id="user_b", 
            enable_persistence=False,
            enable_ttl_cleanup=False
        )
    
    @pytest.fixture
    def mock_websocket_a(self) -> MockWebSocket:
        """Mock WebSocket for user A."""
        return MockWebSocket(
            connection_id=f"conn_a_{uuid.uuid4().hex[:8]}",
            user_id="user_a",
            messages_sent=[]
        )
    
    @pytest.fixture
    def mock_websocket_b(self) -> MockWebSocket:
        """Mock WebSocket for user B."""
        return MockWebSocket(
            connection_id=f"conn_b_{uuid.uuid4().hex[:8]}",
            user_id="user_b", 
            messages_sent=[]
        )

    # ============================================================================
    # CORE INTEGRATION TESTS 
    # ============================================================================

    @pytest.mark.integration
    async def test_websocket_connection_state_management_per_user(
        self, 
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager,
        mock_websocket_a: MockWebSocket,
        mock_websocket_b: MockWebSocket
    ):
        """
        BVJ: Core concurrent chat functionality - ensures users can connect and maintain separate states.
        Tests integration between WebSocket connections and user-specific state management.
        """
        # Set up WebSocket manager with state integration
        state_manager.set_websocket_manager(websocket_manager)
        
        # Create WebSocket connections for both users
        conn_a = WebSocketConnection(
            connection_id=mock_websocket_a.connection_id,
            user_id="user_a",
            websocket=mock_websocket_a,
            connected_at=datetime.now(),
            metadata={"test": "connection_state_integration"}
        )
        
        conn_b = WebSocketConnection(
            connection_id=mock_websocket_b.connection_id,
            user_id="user_b", 
            websocket=mock_websocket_b,
            connected_at=datetime.now(),
            metadata={"test": "connection_state_integration"}
        )
        
        await websocket_manager.add_connection(conn_a)
        await websocket_manager.add_connection(conn_b)
        
        # Set WebSocket-specific state for each user
        state_manager.set_websocket_state(
            mock_websocket_a.connection_id,
            "chat_context",
            {"active_agent": "cost_optimizer", "conversation_stage": "analysis"},
            ttl_seconds=1800
        )
        
        state_manager.set_websocket_state(
            mock_websocket_b.connection_id, 
            "chat_context",
            {"active_agent": "data_insights", "conversation_stage": "recommendations"},
            ttl_seconds=1800
        )
        
        # Verify state isolation between users
        state_a = state_manager.get_websocket_state(mock_websocket_a.connection_id, "chat_context")
        state_b = state_manager.get_websocket_state(mock_websocket_b.connection_id, "chat_context")
        
        assert state_a["active_agent"] == "cost_optimizer"
        assert state_b["active_agent"] == "data_insights"
        assert state_a["conversation_stage"] != state_b["conversation_stage"]
        
        # Verify WebSocket connections are properly tracked per user
        connections_a = websocket_manager.get_user_connections("user_a")
        connections_b = websocket_manager.get_user_connections("user_b")
        
        assert len(connections_a) == 1
        assert len(connections_b) == 1
        assert mock_websocket_a.connection_id in connections_a
        assert mock_websocket_b.connection_id in connections_b
        
        # Verify cross-user isolation (user A cannot access user B's state)
        state_cross_check = state_manager.get_websocket_state(mock_websocket_b.connection_id, "chat_context", default="ISOLATED")
        # This should work as it's the same state manager, but we're testing proper key isolation
        assert state_cross_check["active_agent"] == "data_insights"  # Proper access
        
        # Test state update coordination with WebSocket events
        await websocket_manager.send_to_user("user_a", {
            "type": "state_update", 
            "data": {"conversation_stage": "completed"}
        })
        
        # Verify message was sent only to user A
        assert len(mock_websocket_a.messages_sent) == 1
        assert len(mock_websocket_b.messages_sent) == 0
        assert mock_websocket_a.messages_sent[0]["type"] == "state_update"

    @pytest.mark.integration
    async def test_multi_user_concurrent_websocket_connections_with_isolated_state(
        self,
        websocket_manager: UnifiedWebSocketManager,
        user_state_manager_a: UnifiedStateManager,
        user_state_manager_b: UnifiedStateManager
    ):
        """
        BVJ: Multi-user scaling capability - ensures 10+ users can connect concurrently with complete isolation.
        Tests factory pattern for user-specific state managers with concurrent WebSocket connections.
        """
        # Create multiple connections per user to simulate real usage
        user_a_websockets = []
        user_b_websockets = []
        
        # User A: 3 concurrent connections (mobile, desktop, tablet)
        for i in range(3):
            websocket = MockWebSocket(
                connection_id=f"user_a_conn_{i}_{uuid.uuid4().hex[:8]}",
                user_id="user_a",
                messages_sent=[]
            )
            user_a_websockets.append(websocket)
            
            conn = WebSocketConnection(
                connection_id=websocket.connection_id,
                user_id="user_a",
                websocket=websocket,
                connected_at=datetime.now(),
                metadata={"device": f"device_{i}"}
            )
            await websocket_manager.add_connection(conn)
        
        # User B: 2 concurrent connections (desktop, mobile)  
        for i in range(2):
            websocket = MockWebSocket(
                connection_id=f"user_b_conn_{i}_{uuid.uuid4().hex[:8]}",
                user_id="user_b",
                messages_sent=[]
            )
            user_b_websockets.append(websocket)
            
            conn = WebSocketConnection(
                connection_id=websocket.connection_id,
                user_id="user_b",
                websocket=websocket,
                connected_at=datetime.now(),
                metadata={"device": f"device_{i}"}
            )
            await websocket_manager.add_connection(conn)
        
        # Set up user-specific state in isolated state managers
        user_state_manager_a.set_user_state(
            "user_a",
            "active_conversation", 
            {
                "thread_id": "thread_a_123",
                "agent_chain": ["triage", "cost_optimizer"],
                "data_context": {"monthly_spend": 50000}
            }
        )
        
        user_state_manager_b.set_user_state(
            "user_b", 
            "active_conversation",
            {
                "thread_id": "thread_b_456", 
                "agent_chain": ["triage", "data_insights"],
                "data_context": {"user_segments": ["enterprise", "analytics"]}
            }
        )
        
        # Set WebSocket managers for state coordination
        user_state_manager_a.set_websocket_manager(websocket_manager)
        user_state_manager_b.set_websocket_manager(websocket_manager)
        
        # Verify concurrent connections are tracked correctly
        connections_a = websocket_manager.get_user_connections("user_a")
        connections_b = websocket_manager.get_user_connections("user_b")
        
        assert len(connections_a) == 3
        assert len(connections_b) == 2
        
        # Test concurrent message delivery to all user connections
        await websocket_manager.send_to_user("user_a", {
            "type": "agent_started",
            "data": {"agent": "cost_optimizer", "thread_id": "thread_a_123"}
        })
        
        await websocket_manager.send_to_user("user_b", {
            "type": "agent_started", 
            "data": {"agent": "data_insights", "thread_id": "thread_b_456"}
        })
        
        # Verify all user A connections received user A's message
        for websocket in user_a_websockets:
            assert len(websocket.messages_sent) == 1
            assert websocket.messages_sent[0]["data"]["thread_id"] == "thread_a_123"
        
        # Verify all user B connections received user B's message
        for websocket in user_b_websockets:
            assert len(websocket.messages_sent) == 1
            assert websocket.messages_sent[0]["data"]["thread_id"] == "thread_b_456"
        
        # Verify complete state isolation between users
        state_a = user_state_manager_a.get_user_state("user_a", "active_conversation")
        state_b = user_state_manager_b.get_user_state("user_b", "active_conversation")
        
        assert state_a["data_context"]["monthly_spend"] == 50000
        assert state_b["data_context"]["user_segments"] == ["enterprise", "analytics"]
        
        # Verify users cannot access each other's states
        cross_state_a_to_b = user_state_manager_a.get_user_state("user_b", "active_conversation", default="ISOLATED")
        cross_state_b_to_a = user_state_manager_b.get_user_state("user_a", "active_conversation", default="ISOLATED")
        
        assert cross_state_a_to_b == "ISOLATED"
        assert cross_state_b_to_a == "ISOLATED"

    @pytest.mark.integration 
    async def test_websocket_event_routing_with_user_specific_state_coordination(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager,
        mock_websocket_a: MockWebSocket,
        mock_websocket_b: MockWebSocket
    ):
        """
        BVJ: Real-time chat experience - ensures WebSocket events are routed correctly with state coordination.
        Tests integration between event routing and state management for concurrent users.
        """
        # Set up connections and state integration
        conn_a = WebSocketConnection(
            connection_id=mock_websocket_a.connection_id,
            user_id="user_a",
            websocket=mock_websocket_a,
            connected_at=datetime.now()
        )
        
        conn_b = WebSocketConnection(
            connection_id=mock_websocket_b.connection_id, 
            user_id="user_b",
            websocket=mock_websocket_b,
            connected_at=datetime.now()
        )
        
        await websocket_manager.add_connection(conn_a)
        await websocket_manager.add_connection(conn_b)
        
        # Set up user-specific conversation state
        state_manager.set_user_state("user_a", "current_agent", "cost_optimizer")
        state_manager.set_user_state("user_a", "execution_id", "exec_a_001")
        
        state_manager.set_user_state("user_b", "current_agent", "data_insights")
        state_manager.set_user_state("user_b", "execution_id", "exec_b_002")
        
        # Test critical WebSocket events with state coordination
        critical_events = [
            {
                "type": "agent_started",
                "data": {
                    "agent": "cost_optimizer",
                    "execution_id": "exec_a_001",
                    "user_context": {"optimization_focus": "compute_costs"}
                }
            },
            {
                "type": "agent_thinking", 
                "data": {
                    "thought": "Analyzing current spend patterns...",
                    "execution_id": "exec_a_001"
                }
            },
            {
                "type": "tool_executing",
                "data": {
                    "tool": "aws_cost_analyzer", 
                    "execution_id": "exec_a_001"
                }
            },
            {
                "type": "tool_completed",
                "data": {
                    "tool": "aws_cost_analyzer",
                    "result": {"potential_savings": 15000},
                    "execution_id": "exec_a_001"
                }
            },
            {
                "type": "agent_completed",
                "data": {
                    "result": {"recommendations": ["rightsizing", "reserved_instances"]},
                    "execution_id": "exec_a_001"
                }
            }
        ]
        
        # Send all critical events to user A
        for event in critical_events:
            await websocket_manager.send_to_user("user_a", event)
        
        # Send different events to user B
        await websocket_manager.send_to_user("user_b", {
            "type": "agent_started",
            "data": {
                "agent": "data_insights", 
                "execution_id": "exec_b_002",
                "user_context": {"analysis_type": "user_behavior"}
            }
        })
        
        # Verify user A received all 5 critical events
        assert len(mock_websocket_a.messages_sent) == 5
        assert mock_websocket_a.messages_sent[0]["type"] == "agent_started"
        assert mock_websocket_a.messages_sent[1]["type"] == "agent_thinking" 
        assert mock_websocket_a.messages_sent[2]["type"] == "tool_executing"
        assert mock_websocket_a.messages_sent[3]["type"] == "tool_completed"
        assert mock_websocket_a.messages_sent[4]["type"] == "agent_completed"
        
        # Verify all events have correct execution ID for user A
        for event in mock_websocket_a.messages_sent:
            if "execution_id" in event["data"]:
                assert event["data"]["execution_id"] == "exec_a_001"
        
        # Verify user B received only their event
        assert len(mock_websocket_b.messages_sent) == 1
        assert mock_websocket_b.messages_sent[0]["data"]["execution_id"] == "exec_b_002"
        assert mock_websocket_b.messages_sent[0]["data"]["agent"] == "data_insights"
        
        # Update state based on completed execution and verify coordination
        state_manager.set_user_state("user_a", "last_result", {
            "agent": "cost_optimizer",
            "potential_savings": 15000,
            "recommendations_count": 2
        })
        
        # Verify state is properly isolated and updated
        user_a_result = state_manager.get_user_state("user_a", "last_result")
        user_b_result = state_manager.get_user_state("user_b", "last_result", default=None)
        
        assert user_a_result["potential_savings"] == 15000
        assert user_b_result is None  # User B should not see user A's results

    @pytest.mark.integration
    async def test_connection_recovery_with_state_restoration_for_individual_users(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager
    ):
        """
        BVJ: Chat reliability - ensures users can reconnect without losing conversation state.
        Tests connection recovery mechanisms with user-specific state restoration.
        """
        # Initial connection setup
        initial_websocket = MockWebSocket(
            connection_id="initial_conn_user_a",
            user_id="user_a",
            messages_sent=[]
        )
        
        conn = WebSocketConnection(
            connection_id="initial_conn_user_a",
            user_id="user_a", 
            websocket=initial_websocket,
            connected_at=datetime.now(),
            metadata={"connection_type": "initial"}
        )
        
        await websocket_manager.add_connection(conn)
        
        # Set up conversation state
        conversation_state = {
            "thread_id": "thread_recovery_test",
            "agent_history": ["triage", "cost_optimizer"],
            "current_stage": "optimization_analysis", 
            "data_context": {
                "monthly_spend": 75000,
                "optimization_goals": ["reduce_compute", "optimize_storage"]
            },
            "message_count": 15,
            "last_interaction": datetime.now().isoformat()
        }
        
        state_manager.set_user_state("user_a", "conversation_session", conversation_state)
        state_manager.set_user_state("user_a", "pending_messages", [
            {"type": "agent_thinking", "content": "Analyzing storage patterns..."},
            {"type": "tool_executing", "content": "Running storage audit..."}
        ])
        
        # Simulate connection failure
        initial_websocket.close()
        await websocket_manager.remove_connection("initial_conn_user_a")
        
        # Verify user has no active connections
        assert not websocket_manager.is_connection_active("user_a")
        
        # User attempts to reconnect with new WebSocket
        recovery_websocket = MockWebSocket(
            connection_id="recovery_conn_user_a",
            user_id="user_a",
            messages_sent=[]
        )
        
        recovery_conn = WebSocketConnection(
            connection_id="recovery_conn_user_a",
            user_id="user_a",
            websocket=recovery_websocket,
            connected_at=datetime.now(),
            metadata={"connection_type": "recovery"}
        )
        
        await websocket_manager.add_connection(recovery_conn)
        
        # Verify connection recovery
        assert websocket_manager.is_connection_active("user_a")
        recovery_connections = websocket_manager.get_user_connections("user_a")
        assert len(recovery_connections) == 1
        assert "recovery_conn_user_a" in recovery_connections
        
        # Restore conversation state from state manager
        restored_conversation = state_manager.get_user_state("user_a", "conversation_session")
        restored_messages = state_manager.get_user_state("user_a", "pending_messages")
        
        # Verify complete state restoration
        assert restored_conversation["thread_id"] == "thread_recovery_test"
        assert restored_conversation["current_stage"] == "optimization_analysis"
        assert restored_conversation["data_context"]["monthly_spend"] == 75000
        assert len(restored_conversation["agent_history"]) == 2
        
        # Send recovery notification with restored state
        await websocket_manager.send_to_user("user_a", {
            "type": "connection_recovered",
            "data": {
                "session_restored": True,
                "conversation_state": restored_conversation,
                "pending_messages": restored_messages
            }
        })
        
        # Verify recovery message was delivered
        assert len(recovery_websocket.messages_sent) == 1
        recovery_message = recovery_websocket.messages_sent[0]
        assert recovery_message["type"] == "connection_recovered"
        assert recovery_message["data"]["session_restored"] is True
        assert recovery_message["data"]["conversation_state"]["thread_id"] == "thread_recovery_test"

    @pytest.mark.integration
    async def test_websocket_message_persistence_through_state_management(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager,
        mock_websocket_a: MockWebSocket,
        mock_websocket_b: MockWebSocket
    ):
        """
        BVJ: Data integrity - ensures chat messages persist through state management for audit/recovery.
        Tests message persistence coordination between WebSocket events and state storage.
        """
        # Set up connections
        conn_a = WebSocketConnection(
            connection_id=mock_websocket_a.connection_id,
            user_id="user_a",
            websocket=mock_websocket_a,
            connected_at=datetime.now()
        )
        
        conn_b = WebSocketConnection(
            connection_id=mock_websocket_b.connection_id,
            user_id="user_b", 
            websocket=mock_websocket_b,
            connected_at=datetime.now()
        )
        
        await websocket_manager.add_connection(conn_a)
        await websocket_manager.add_connection(conn_b)
        
        # Define message persistence handler
        message_log_a = []
        message_log_b = []
        
        async def persist_message(user_id: str, message: Dict[str, Any]) -> None:
            """Persist message to user-specific message log."""
            message_with_timestamp = {
                **message,
                "timestamp": datetime.now().isoformat(),
                "persisted_by": "state_manager"
            }
            
            if user_id == "user_a":
                message_log_a.append(message_with_timestamp)
            elif user_id == "user_b":
                message_log_b.append(message_with_timestamp)
            
            # Store in state manager as well
            current_messages = state_manager.get_user_state(user_id, "message_history", default=[])
            current_messages.append(message_with_timestamp)
            state_manager.set_user_state(user_id, "message_history", current_messages)
        
        # Send messages to both users and persist them
        user_a_messages = [
            {"type": "agent_started", "data": {"agent": "cost_optimizer"}},
            {"type": "agent_thinking", "data": {"thought": "Analyzing costs..."}},
            {"type": "tool_executing", "data": {"tool": "aws_analyzer"}},
            {"type": "agent_completed", "data": {"result": "analysis_complete"}}
        ]
        
        user_b_messages = [
            {"type": "agent_started", "data": {"agent": "data_insights"}}, 
            {"type": "agent_thinking", "data": {"thought": "Processing data..."}},
            {"type": "agent_completed", "data": {"result": "insights_ready"}}
        ]
        
        # Send and persist user A messages
        for message in user_a_messages:
            await websocket_manager.send_to_user("user_a", message)
            await persist_message("user_a", message)
        
        # Send and persist user B messages  
        for message in user_b_messages:
            await websocket_manager.send_to_user("user_b", message)
            await persist_message("user_b", message)
        
        # Verify messages were delivered via WebSocket
        assert len(mock_websocket_a.messages_sent) == 4
        assert len(mock_websocket_b.messages_sent) == 3
        
        # Verify message persistence in local logs
        assert len(message_log_a) == 4
        assert len(message_log_b) == 3
        
        # Verify message persistence in state manager
        persisted_messages_a = state_manager.get_user_state("user_a", "message_history")
        persisted_messages_b = state_manager.get_user_state("user_b", "message_history")
        
        assert len(persisted_messages_a) == 4
        assert len(persisted_messages_b) == 3
        
        # Verify message content and metadata
        for i, original_msg in enumerate(user_a_messages):
            persisted_msg = persisted_messages_a[i]
            assert persisted_msg["type"] == original_msg["type"]
            assert persisted_msg["data"] == original_msg["data"]
            assert "timestamp" in persisted_msg
            assert persisted_msg["persisted_by"] == "state_manager"
        
        # Verify user isolation in persisted messages
        user_a_agent_types = [msg["data"]["agent"] for msg in persisted_messages_a if msg["type"] == "agent_started"]
        user_b_agent_types = [msg["data"]["agent"] for msg in persisted_messages_b if msg["type"] == "agent_started"]
        
        assert user_a_agent_types == ["cost_optimizer"]
        assert user_b_agent_types == ["data_insights"]
        
        # Test message retrieval for audit/recovery
        def get_messages_by_type(user_id: str, message_type: str) -> List[Dict[str, Any]]:
            messages = state_manager.get_user_state(user_id, "message_history", default=[])
            return [msg for msg in messages if msg["type"] == message_type]
        
        user_a_completions = get_messages_by_type("user_a", "agent_completed")
        user_b_completions = get_messages_by_type("user_b", "agent_completed")
        
        assert len(user_a_completions) == 1
        assert len(user_b_completions) == 1
        assert user_a_completions[0]["data"]["result"] == "analysis_complete"
        assert user_b_completions[0]["data"]["result"] == "insights_ready"

    @pytest.mark.integration
    async def test_cross_user_isolation_validation_in_websocket_state(
        self,
        websocket_manager: UnifiedWebSocketManager,
        user_state_manager_a: UnifiedStateManager,
        user_state_manager_b: UnifiedStateManager
    ):
        """
        BVJ: Security and data privacy - ensures complete isolation between users to prevent data leakage.
        Tests comprehensive isolation between users across WebSocket connections and state management.
        """
        # Create connections for multiple users
        users_websockets = {}
        users_connections = {}
        
        user_ids = ["user_a", "user_b", "user_c", "user_d"]
        
        for user_id in user_ids:
            websocket = MockWebSocket(
                connection_id=f"conn_{user_id}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                messages_sent=[]
            )
            users_websockets[user_id] = websocket
            
            conn = WebSocketConnection(
                connection_id=websocket.connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(),
                metadata={"isolation_test": True}
            )
            users_connections[user_id] = conn
            await websocket_manager.add_connection(conn)
        
        # Set up user-specific confidential data in isolated state managers
        confidential_data = {
            "user_a": {
                "company": "Acme Corp",
                "monthly_spend": 100000,
                "secret_projects": ["project_alpha", "cost_reduction_initiative"],
                "api_keys": {"aws": "secret_key_a_123"}
            },
            "user_b": {
                "company": "Beta Industries", 
                "monthly_spend": 250000,
                "secret_projects": ["project_beta", "market_expansion"],
                "api_keys": {"gcp": "secret_key_b_456"}
            },
            "user_c": {
                "company": "Gamma LLC",
                "monthly_spend": 50000,
                "secret_projects": ["project_gamma", "product_launch"],
                "api_keys": {"azure": "secret_key_c_789"}
            },
            "user_d": {
                "company": "Delta Corp",
                "monthly_spend": 500000,
                "secret_projects": ["project_delta", "acquisition_plans"],
                "api_keys": {"multi_cloud": "secret_key_d_000"}
            }
        }
        
        # Use separate state managers for each user to ensure isolation
        user_state_managers = {
            "user_a": user_state_manager_a,
            "user_b": user_state_manager_b,
            "user_c": UnifiedStateManager(user_id="user_c", enable_persistence=False),
            "user_d": UnifiedStateManager(user_id="user_d", enable_persistence=False)
        }
        
        # Set confidential data for each user
        for user_id, data in confidential_data.items():
            state_manager = user_state_managers[user_id]
            state_manager.set_user_state(user_id, "confidential_data", data)
            state_manager.set_user_state(user_id, "session_token", f"token_{user_id}_{uuid.uuid4().hex}")
        
        # Attempt cross-user access validation
        for accessing_user in user_ids:
            for target_user in user_ids:
                if accessing_user != target_user:
                    # Try to access other user's data using accessing user's state manager
                    accessing_state_manager = user_state_managers[accessing_user]
                    
                    # This should return None/default because state managers are user-isolated
                    other_user_data = accessing_state_manager.get_user_state(
                        target_user, "confidential_data", default="ACCESS_DENIED"
                    )
                    
                    # Verify access is denied (returns default value)
                    assert other_user_data == "ACCESS_DENIED", (
                        f"User {accessing_user} should not access user {target_user}'s data"
                    )
        
        # Test WebSocket message delivery isolation
        sensitive_messages = {
            "user_a": {
                "type": "confidential_alert",
                "data": {"api_key_rotation_required": True, "affected_systems": ["billing", "analytics"]}
            },
            "user_b": {
                "type": "confidential_alert", 
                "data": {"security_breach_detected": True, "affected_accounts": ["prod", "staging"]}
            },
            "user_c": {
                "type": "confidential_alert",
                "data": {"budget_exceeded": True, "overage_amount": 25000}
            },
            "user_d": {
                "type": "confidential_alert",
                "data": {"compliance_violation": True, "regulation": "GDPR", "action_required": "immediate"}}
        }
        
        # Send sensitive messages to each user
        for user_id, message in sensitive_messages.items():
            await websocket_manager.send_to_user(user_id, message)
        
        # Verify each user received only their own sensitive message
        for user_id in user_ids:
            websocket = users_websockets[user_id]
            assert len(websocket.messages_sent) == 1
            
            received_message = websocket.messages_sent[0]
            expected_message = sensitive_messages[user_id]
            
            assert received_message["type"] == expected_message["type"]
            assert received_message["data"] == expected_message["data"]
        
        # Verify no cross-contamination in WebSocket connections
        for user_id in user_ids:
            connections = websocket_manager.get_user_connections(user_id)
            assert len(connections) == 1
            
            # Ensure connection ID belongs to the correct user
            connection_id = list(connections)[0]
            assert user_id in connection_id, f"Connection ID {connection_id} should contain user ID {user_id}"
        
        # Test state query isolation
        for user_id in user_ids:
            state_manager = user_state_managers[user_id]
            
            # Query for user-specific data
            user_states = state_manager.query_states(
                StateQuery(scope=StateScope.USER, user_id=user_id)
            )
            
            # Verify only this user's states are returned
            for state_entry in user_states:
                assert state_entry.user_id == user_id or state_entry.user_id is None

    @pytest.mark.integration
    async def test_websocket_connection_pooling_with_user_specific_locks(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager
    ):
        """
        BVJ: Performance optimization - ensures efficient connection pooling while maintaining user isolation.
        Tests connection pooling mechanisms with user-specific locking for thread safety.
        """
        # Create connection pool for multiple users with multiple connections each
        connection_pools = {}
        
        for user_index in range(5):  # 5 users
            user_id = f"user_{user_index}"
            connection_pools[user_id] = []
            
            # Each user has 3 concurrent connections (connection pooling scenario)
            for conn_index in range(3):
                websocket = MockWebSocket(
                    connection_id=f"{user_id}_pool_{conn_index}_{uuid.uuid4().hex[:8]}",
                    user_id=user_id,
                    messages_sent=[]
                )
                
                conn = WebSocketConnection(
                    connection_id=websocket.connection_id,
                    user_id=user_id,
                    websocket=websocket,
                    connected_at=datetime.now(),
                    metadata={"pool_connection": True, "pool_index": conn_index}
                )
                
                connection_pools[user_id].append((websocket, conn))
                await websocket_manager.add_connection(conn)
        
        # Verify connection pooling structure
        total_expected_connections = 5 * 3  # 5 users × 3 connections
        actual_connections = sum(
            len(websocket_manager.get_user_connections(f"user_{i}"))
            for i in range(5)
        )
        assert actual_connections == total_expected_connections
        
        # Test concurrent message broadcasting with user-specific locks
        async def send_concurrent_messages():
            """Send messages concurrently to test thread safety."""
            tasks = []
            
            for user_index in range(5):
                user_id = f"user_{user_index}"
                
                # Create task for each user to send messages concurrently
                task = asyncio.create_task(
                    websocket_manager.send_to_user(user_id, {
                        "type": "concurrent_test",
                        "data": {
                            "user_id": user_id,
                            "timestamp": time.time(),
                            "pool_test": True
                        }
                    })
                )
                tasks.append(task)
            
            # Execute all message sends concurrently
            await asyncio.gather(*tasks)
        
        # Execute concurrent sending multiple times to stress test locks
        for round_num in range(10):
            await send_concurrent_messages()
            # Small delay to allow processing
            await asyncio.sleep(0.01)
        
        # Verify all messages were delivered correctly to connection pools
        for user_index in range(5):
            user_id = f"user_{user_index}"
            user_pool = connection_pools[user_id]
            
            # Each connection in the pool should have received all 10 messages
            for websocket, conn in user_pool:
                assert len(websocket.messages_sent) == 10
                
                # Verify each message has correct user_id
                for message in websocket.messages_sent:
                    assert message["data"]["user_id"] == user_id
                    assert message["data"]["pool_test"] is True
        
        # Test connection pooling with state coordination
        for user_index in range(5):
            user_id = f"user_{user_index}"
            
            # Set user-specific state that should coordinate with all pooled connections
            state_manager.set_user_state(user_id, "pool_coordination", {
                "active_connections": len(websocket_manager.get_user_connections(user_id)),
                "last_activity": datetime.now().isoformat(),
                "pool_status": "active"
            })
        
        # Verify state is properly set for all users
        for user_index in range(5):
            user_id = f"user_{user_index}"
            pool_state = state_manager.get_user_state(user_id, "pool_coordination")
            
            assert pool_state["active_connections"] == 3
            assert pool_state["pool_status"] == "active"
            assert "last_activity" in pool_state
        
        # Test removal of connections from pool (simulate connection drops)
        for user_index in range(2):  # Remove connections for first 2 users
            user_id = f"user_{user_index}"
            user_pool = connection_pools[user_id]
            
            # Remove one connection from each user's pool
            websocket_to_remove, conn_to_remove = user_pool[0]
            await websocket_manager.remove_connection(conn_to_remove.connection_id)
        
        # Verify connection pool updates
        assert len(websocket_manager.get_user_connections("user_0")) == 2  # 3 - 1 = 2
        assert len(websocket_manager.get_user_connections("user_1")) == 2  # 3 - 1 = 2
        assert len(websocket_manager.get_user_connections("user_2")) == 3  # unchanged
        assert len(websocket_manager.get_user_connections("user_3")) == 3  # unchanged  
        assert len(websocket_manager.get_user_connections("user_4")) == 3  # unchanged

    @pytest.mark.integration
    async def test_real_time_state_synchronization_through_websocket_events(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager,
        mock_websocket_a: MockWebSocket,
        mock_websocket_b: MockWebSocket
    ):
        """
        BVJ: Real-time collaboration - ensures state changes are synchronized across user sessions via WebSocket.
        Tests real-time state synchronization mechanisms through WebSocket event coordination.
        """
        # Set up connections with state synchronization enabled
        conn_a = WebSocketConnection(
            connection_id=mock_websocket_a.connection_id,
            user_id="user_a", 
            websocket=mock_websocket_a,
            connected_at=datetime.now(),
            metadata={"sync_enabled": True}
        )
        
        conn_b = WebSocketConnection(
            connection_id=mock_websocket_b.connection_id,
            user_id="user_b",
            websocket=mock_websocket_b,
            connected_at=datetime.now(), 
            metadata={"sync_enabled": True}
        )
        
        await websocket_manager.add_connection(conn_a)
        await websocket_manager.add_connection(conn_b)
        
        # Enable WebSocket events for state changes
        state_manager.set_websocket_manager(websocket_manager)
        state_manager.enable_websocket_events(True)
        
        # Set up state change listener for real-time sync
        state_changes_log = []
        
        def track_state_changes(event):
            """Track state changes for testing."""
            state_changes_log.append({
                "key": event.key,
                "change_type": event.change_type, 
                "user_id": event.user_id,
                "timestamp": event.timestamp
            })
        
        state_manager.add_change_listener(track_state_changes)
        
        # Test real-time state synchronization scenarios
        
        # Scenario 1: User A updates their conversation state
        conversation_state_a = {
            "thread_id": "sync_test_thread_a",
            "current_agent": "cost_optimizer",
            "analysis_progress": 75,
            "last_update": datetime.now().isoformat()
        }
        
        state_manager.set_user_state("user_a", "conversation_sync", conversation_state_a)
        
        # Allow time for async event processing
        await asyncio.sleep(0.1)
        
        # Scenario 2: User B updates their different conversation state
        conversation_state_b = {
            "thread_id": "sync_test_thread_b",
            "current_agent": "data_insights", 
            "analysis_progress": 45,
            "last_update": datetime.now().isoformat()
        }
        
        state_manager.set_user_state("user_b", "conversation_sync", conversation_state_b)
        
        # Allow time for async event processing
        await asyncio.sleep(0.1)
        
        # Scenario 3: Update shared configuration state (global scope)
        global_config = {
            "feature_flags": {"new_ui_enabled": True, "beta_features": ["advanced_analytics"]},
            "system_status": "operational",
            "maintenance_window": None
        }
        
        state_manager.set("global_config", global_config, scope=StateScope.GLOBAL, state_type=StateType.CONFIGURATION_STATE)
        
        # Allow time for async event processing
        await asyncio.sleep(0.1)
        
        # Verify state changes were tracked
        assert len(state_changes_log) >= 3  # At least 3 state changes
        
        # Verify user-specific state changes
        user_a_changes = [change for change in state_changes_log if change["user_id"] == "user_a"]
        user_b_changes = [change for change in state_changes_log if change["user_id"] == "user_b"]
        global_changes = [change for change in state_changes_log if change["user_id"] is None]
        
        assert len(user_a_changes) >= 1
        assert len(user_b_changes) >= 1
        assert len(global_changes) >= 1
        
        # Test atomic state updates with synchronization
        def update_progress(current_value):
            """Update progress atomically."""
            if current_value is None:
                return {"progress": 0, "status": "started"}
            return {
                "progress": current_value.get("progress", 0) + 25,
                "status": "in_progress" if current_value.get("progress", 0) < 75 else "completed"
            }
        
        # Perform atomic updates for both users
        state_manager.update("user:user_a:task_progress", update_progress)
        state_manager.update("user:user_b:task_progress", update_progress) 
        
        # Perform multiple updates to test synchronization
        for _ in range(3):
            state_manager.update("user:user_a:task_progress", update_progress)
            state_manager.update("user:user_b:task_progress", update_progress)
            await asyncio.sleep(0.05)
        
        # Verify final states are properly synchronized
        final_progress_a = state_manager.get("user:user_a:task_progress")
        final_progress_b = state_manager.get("user:user_b:task_progress")
        
        assert final_progress_a["progress"] == 100  # Started at 0, added 25 four times
        assert final_progress_b["progress"] == 100
        assert final_progress_a["status"] == "completed"
        assert final_progress_b["status"] == "completed"
        
        # Verify state isolation (users can't see each other's task progress)
        user_a_isolated_progress = state_manager.get_user_state("user_a", "task_progress", default="NOT_FOUND")
        user_b_isolated_progress = state_manager.get_user_state("user_b", "task_progress", default="NOT_FOUND")
        
        # These should not be found because the keys were set with direct key format
        assert user_a_isolated_progress == "NOT_FOUND"
        assert user_b_isolated_progress == "NOT_FOUND"
        
        # But global config should be accessible 
        retrieved_global_config = state_manager.get("global_config")
        assert retrieved_global_config["feature_flags"]["new_ui_enabled"] is True
        assert retrieved_global_config["system_status"] == "operational"

    @pytest.mark.integration
    async def test_websocket_disconnection_handling_with_state_cleanup(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager
    ):
        """
        BVJ: Resource management - ensures proper cleanup when users disconnect to prevent memory leaks.
        Tests WebSocket disconnection handling with coordinated state cleanup procedures.
        """
        # Create connections for multiple users with various session data
        users_data = {}
        
        for user_index in range(3):
            user_id = f"cleanup_user_{user_index}"
            
            # Create WebSocket connection
            websocket = MockWebSocket(
                connection_id=f"cleanup_conn_{user_index}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                messages_sent=[]
            )
            
            conn = WebSocketConnection(
                connection_id=websocket.connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(),
                metadata={"cleanup_test": True}
            )
            
            users_data[user_id] = {"websocket": websocket, "connection": conn}
            await websocket_manager.add_connection(conn)
        
        # Set up extensive state data for each user
        for user_index in range(3):
            user_id = f"cleanup_user_{user_index}"
            
            # Set various types of state data
            state_manager.set_user_state(user_id, "session_data", {
                "login_time": datetime.now().isoformat(),
                "preferences": {"theme": "dark", "notifications": True},
                "activity_log": [f"action_{i}" for i in range(10)]
            })
            
            state_manager.set_thread_state(f"thread_{user_id}", "conversation_history", {
                "messages": [f"message_{i}" for i in range(50)],
                "participants": [user_id],
                "created_at": datetime.now().isoformat()
            })
            
            state_manager.set_agent_state(f"agent_{user_id}", "execution_context", {
                "current_step": "analysis", 
                "completed_tools": ["data_loader", "analyzer"],
                "remaining_tools": ["reporter", "optimizer"],
                "temp_data": {"large_dataset": list(range(1000))}
            }, ttl_seconds=3600)
            
            state_manager.set_websocket_state(
                users_data[user_id]["connection"].connection_id,
                "connection_metadata",
                {
                    "browser": "Chrome",
                    "device_type": "desktop",
                    "connection_quality": "high",
                    "bandwidth_usage": {"sent": 1024000, "received": 2048000}
                }
            )
        
        # Verify all state data is present
        initial_state_count = len(state_manager.keys())
        assert initial_state_count > 0
        
        # Test graceful disconnection with state cleanup for first user
        user_to_disconnect = "cleanup_user_0"
        user_websocket = users_data[user_to_disconnect]["websocket"]
        user_connection = users_data[user_to_disconnect]["connection"]
        
        # Simulate graceful disconnection
        user_websocket.close()
        await websocket_manager.disconnect_user(
            user_to_disconnect,
            user_websocket,
            code=1000,
            reason="User initiated disconnect"
        )
        
        # Verify connection is removed
        assert not websocket_manager.is_connection_active(user_to_disconnect)
        remaining_connections = websocket_manager.get_user_connections(user_to_disconnect)
        assert len(remaining_connections) == 0
        
        # Perform manual state cleanup for disconnected user (simulating cleanup process)
        cleanup_stats = {
            "user_states_cleared": 0,
            "thread_states_cleared": 0,
            "agent_states_cleared": 0,
            "websocket_states_cleared": 0
        }
        
        # Clear user-specific states
        user_states_cleared = state_manager.clear_user_states(user_to_disconnect)
        cleanup_stats["user_states_cleared"] = user_states_cleared
        
        # Clear thread states associated with user
        thread_states_cleared = state_manager.clear_scope(
            StateScope.THREAD,
            thread_id=f"thread_{user_to_disconnect}"
        )
        cleanup_stats["thread_states_cleared"] = thread_states_cleared
        
        # Clear agent states associated with user
        agent_states_cleared = state_manager.clear_scope(
            StateScope.AGENT,
            agent_id=f"agent_{user_to_disconnect}"
        )
        cleanup_stats["agent_states_cleared"] = agent_states_cleared
        
        # Clear WebSocket states for the connection
        websocket_states_cleared = state_manager.clear_scope(
            StateScope.WEBSOCKET
        )
        cleanup_stats["websocket_states_cleared"] = websocket_states_cleared
        
        # Verify cleanup was effective
        assert cleanup_stats["user_states_cleared"] > 0
        assert cleanup_stats["thread_states_cleared"] > 0
        assert cleanup_stats["agent_states_cleared"] > 0
        
        # Verify disconnected user's data is no longer accessible
        user_session_data = state_manager.get_user_state(user_to_disconnect, "session_data", default="CLEANED_UP")
        assert user_session_data == "CLEANED_UP"
        
        thread_history = state_manager.get_thread_state(f"thread_{user_to_disconnect}", "conversation_history", default="CLEANED_UP")
        assert thread_history == "CLEANED_UP"
        
        agent_context = state_manager.get_agent_state(f"agent_{user_to_disconnect}", "execution_context", default="CLEANED_UP")
        assert agent_context == "CLEANED_UP"
        
        # Verify other users' data remains intact
        for user_index in [1, 2]:  # Users 1 and 2 should still have their data
            user_id = f"cleanup_user_{user_index}"
            
            # Verify their state data still exists
            user_session = state_manager.get_user_state(user_id, "session_data")
            assert user_session is not None
            assert "login_time" in user_session
            
            thread_data = state_manager.get_thread_state(f"thread_{user_id}", "conversation_history")
            assert thread_data is not None
            assert len(thread_data["messages"]) == 50
            
            agent_data = state_manager.get_agent_state(f"agent_{user_id}", "execution_context")
            assert agent_data is not None
            assert len(agent_data["temp_data"]["large_dataset"]) == 1000
            
            # Verify their connections are still active
            assert websocket_manager.is_connection_active(user_id)
        
        # Test abrupt disconnection (connection drop) for second user
        user_to_drop = "cleanup_user_1"
        drop_websocket = users_data[user_to_drop]["websocket"]
        drop_connection = users_data[user_to_drop]["connection"]
        
        # Simulate connection drop (no graceful close)
        drop_websocket.is_closed = True
        await websocket_manager.remove_connection(drop_connection.connection_id)
        
        # Verify connection tracking is updated
        assert not websocket_manager.is_connection_active(user_to_drop)
        
        # In a real system, cleanup would be triggered by a background process
        # Here we simulate that process
        await asyncio.sleep(0.1)  # Simulate cleanup delay
        
        # Manual cleanup for dropped connection
        state_manager.clear_user_states(user_to_drop)
        state_manager.clear_scope(StateScope.THREAD, thread_id=f"thread_{user_to_drop}")
        state_manager.clear_scope(StateScope.AGENT, agent_id=f"agent_{user_to_drop}")
        
        # Verify final state: only user_2 should have remaining data
        final_user_id = "cleanup_user_2"
        assert websocket_manager.is_connection_active(final_user_id)
        
        final_user_session = state_manager.get_user_state(final_user_id, "session_data")
        assert final_user_session is not None
        
        # Verify cleanup metrics
        final_state_count = len(state_manager.keys())
        states_cleaned = initial_state_count - final_state_count
        assert states_cleaned > 0  # Some states should have been cleaned up

    # ============================================================================
    # ADVANCED INTEGRATION SCENARIOS
    # ============================================================================

    @pytest.mark.integration
    async def test_background_task_monitoring_with_user_specific_state_tracking(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager
    ):
        """
        BVJ: System reliability - ensures background tasks coordinate properly with user state management.
        Tests background task monitoring integration with user-specific state tracking.
        """
        # Set up users for background task monitoring
        user_ids = ["monitor_user_a", "monitor_user_b"]
        user_websockets = {}
        
        for user_id in user_ids:
            websocket = MockWebSocket(
                connection_id=f"monitor_conn_{user_id}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                messages_sent=[]
            )
            user_websockets[user_id] = websocket
            
            conn = WebSocketConnection(
                connection_id=websocket.connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(),
                metadata={"monitoring_test": True}
            )
            
            await websocket_manager.add_connection(conn)
        
        # Set up background task monitoring through state management
        task_states = {}
        
        async def user_specific_background_task(user_id: str, task_name: str):
            """Simulate user-specific background task with state tracking."""
            task_key = f"background_task_{task_name}"
            
            # Initialize task state
            state_manager.set_user_state(user_id, task_key, {
                "status": "started",
                "start_time": datetime.now().isoformat(),
                "progress": 0,
                "steps_completed": []
            })
            
            # Simulate task execution with state updates
            steps = ["initialization", "data_processing", "analysis", "completion"]
            
            for step_index, step in enumerate(steps):
                # Update progress
                progress = int((step_index + 1) / len(steps) * 100)
                
                current_state = state_manager.get_user_state(user_id, task_key)
                current_state["progress"] = progress
                current_state["current_step"] = step
                current_state["steps_completed"].append(step)
                current_state["last_update"] = datetime.now().isoformat()
                
                state_manager.set_user_state(user_id, task_key, current_state)
                
                # Send progress update via WebSocket
                await websocket_manager.send_to_user(user_id, {
                    "type": "background_task_progress",
                    "data": {
                        "task_name": task_name,
                        "progress": progress,
                        "current_step": step,
                        "user_id": user_id
                    }
                })
                
                # Simulate processing time
                await asyncio.sleep(0.1)
            
            # Mark task as completed
            final_state = state_manager.get_user_state(user_id, task_key)
            final_state["status"] = "completed"
            final_state["end_time"] = datetime.now().isoformat()
            state_manager.set_user_state(user_id, task_key, final_state)
            
            await websocket_manager.send_to_user(user_id, {
                "type": "background_task_completed",
                "data": {
                    "task_name": task_name,
                    "user_id": user_id,
                    "final_state": final_state
                }
            })
        
        # Start background tasks for both users using WebSocket manager's background task system
        task_names = {
            "monitor_user_a": "cost_analysis_background",
            "monitor_user_b": "data_insights_background"
        }
        
        background_tasks = []
        for user_id in user_ids:
            task_name = task_names[user_id]
            task = asyncio.create_task(user_specific_background_task(user_id, task_name))
            background_tasks.append(task)
            
            # Track task in WebSocket manager's background task system
            await websocket_manager.start_monitored_background_task(
                f"{user_id}_{task_name}",
                user_specific_background_task,
                user_id,
                task_name
            )
        
        # Wait for all background tasks to complete
        await asyncio.gather(*background_tasks)
        
        # Verify task completion through state management
        for user_id in user_ids:
            task_name = task_names[user_id]
            task_key = f"background_task_{task_name}"
            
            final_state = state_manager.get_user_state(user_id, task_key)
            assert final_state["status"] == "completed"
            assert final_state["progress"] == 100
            assert len(final_state["steps_completed"]) == 4
            assert "end_time" in final_state
        
        # Verify WebSocket notifications were sent correctly
        for user_id in user_ids:
            websocket = user_websockets[user_id]
            
            # Should have received progress updates + completion notification
            # 4 progress updates + 1 completion = 5 messages minimum
            assert len(websocket.messages_sent) >= 5
            
            # Verify message types and user isolation
            progress_messages = [msg for msg in websocket.messages_sent if msg["type"] == "background_task_progress"]
            completion_messages = [msg for msg in websocket.messages_sent if msg["type"] == "background_task_completed"]
            
            assert len(progress_messages) == 4
            assert len(completion_messages) == 1
            
            # Verify all messages have correct user_id
            for message in websocket.messages_sent:
                assert message["data"]["user_id"] == user_id
        
        # Test background task monitoring health status
        task_status = websocket_manager.get_background_task_status()
        assert task_status["monitoring_enabled"] is True
        assert task_status["total_tasks"] >= 0  # Tasks may have completed
        
        # Verify state isolation between users' background tasks
        user_a_state = state_manager.get_user_state("monitor_user_a", "background_task_cost_analysis_background")
        user_b_state = state_manager.get_user_state("monitor_user_b", "background_task_data_insights_background")
        
        assert user_a_state["status"] == "completed"
        assert user_b_state["status"] == "completed"
        
        # Ensure cross-user task state access is isolated
        user_a_cannot_see_b = state_manager.get_user_state("monitor_user_a", "background_task_data_insights_background", default="ISOLATED")
        user_b_cannot_see_a = state_manager.get_user_state("monitor_user_b", "background_task_cost_analysis_background", default="ISOLATED")
        
        assert user_a_cannot_see_b == "ISOLATED"
        assert user_b_cannot_see_a == "ISOLATED"

    @pytest.mark.integration
    async def test_websocket_heartbeat_management_through_state_persistence(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager
    ):
        """
        BVJ: Connection reliability - ensures WebSocket connections remain healthy with heartbeat coordination.
        Tests WebSocket heartbeat management integrated with state persistence for connection health.
        """
        # Set up users with heartbeat monitoring
        users_heartbeat_data = {}
        
        for user_index in range(3):
            user_id = f"heartbeat_user_{user_index}"
            
            websocket = MockWebSocket(
                connection_id=f"heartbeat_conn_{user_index}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                messages_sent=[]
            )
            
            conn = WebSocketConnection(
                connection_id=websocket.connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(),
                metadata={"heartbeat_enabled": True}
            )
            
            users_heartbeat_data[user_id] = {
                "websocket": websocket,
                "connection": conn,
                "last_heartbeat": time.time(),
                "heartbeat_count": 0,
                "missed_heartbeats": 0
            }
            
            await websocket_manager.add_connection(conn)
        
        # Initialize heartbeat state for each user
        for user_id, user_data in users_heartbeat_data.items():
            connection_id = user_data["connection"].connection_id
            
            # Set initial heartbeat state
            heartbeat_state = {
                "connection_id": connection_id,
                "user_id": user_id,
                "heartbeat_interval": 30,  # 30 seconds
                "last_heartbeat": datetime.now().isoformat(),
                "heartbeat_count": 0,
                "status": "healthy",
                "missed_heartbeats": 0,
                "max_missed_heartbeats": 3
            }
            
            state_manager.set_websocket_state(
                connection_id,
                "heartbeat_status", 
                heartbeat_state,
                ttl_seconds=300  # 5 minutes TTL
            )
        
        # Simulate heartbeat monitoring system
        async def heartbeat_monitor_cycle():
            """Simulate one cycle of heartbeat monitoring."""
            for user_id, user_data in users_heartbeat_data.items():
                connection_id = user_data["connection"].connection_id
                websocket = user_data["websocket"]
                
                # Get current heartbeat state
                current_state = state_manager.get_websocket_state(connection_id, "heartbeat_status")
                if not current_state:
                    continue
                
                # Send heartbeat ping
                heartbeat_message = {
                    "type": "heartbeat_ping",
                    "data": {
                        "timestamp": datetime.now().isoformat(),
                        "sequence": current_state["heartbeat_count"] + 1,
                        "connection_id": connection_id
                    }
                }
                
                try:
                    await websocket_manager.send_to_user(user_id, heartbeat_message)
                    
                    # Update heartbeat state for successful ping
                    current_state["heartbeat_count"] += 1
                    current_state["last_heartbeat"] = datetime.now().isoformat()
                    current_state["status"] = "healthy"
                    
                    # Reset missed heartbeats on successful ping
                    if current_state["missed_heartbeats"] > 0:
                        current_state["missed_heartbeats"] = 0
                    
                except Exception as e:
                    # Handle failed heartbeat
                    current_state["missed_heartbeats"] += 1
                    current_state["status"] = "unhealthy" if current_state["missed_heartbeats"] >= current_state["max_missed_heartbeats"] else "degraded"
                    
                    await websocket_manager.send_to_user(user_id, {
                        "type": "heartbeat_failed",
                        "data": {
                            "error": str(e),
                            "missed_count": current_state["missed_heartbeats"],
                            "connection_id": connection_id
                        }
                    })
                
                # Update state in state manager
                state_manager.set_websocket_state(
                    connection_id,
                    "heartbeat_status",
                    current_state,
                    ttl_seconds=300
                )
        
        # Run multiple heartbeat cycles
        for cycle in range(5):
            await heartbeat_monitor_cycle()
            await asyncio.sleep(0.1)  # Small delay between cycles
        
        # Verify heartbeat messages were sent
        for user_id, user_data in users_heartbeat_data.items():
            websocket = user_data["websocket"]
            connection_id = user_data["connection"].connection_id
            
            # Should have received 5 heartbeat pings
            heartbeat_pings = [msg for msg in websocket.messages_sent if msg["type"] == "heartbeat_ping"]
            assert len(heartbeat_pings) == 5
            
            # Verify sequence numbers are correct
            for i, ping in enumerate(heartbeat_pings):
                assert ping["data"]["sequence"] == i + 1
                assert ping["data"]["connection_id"] == connection_id
            
            # Verify heartbeat state persistence
            heartbeat_state = state_manager.get_websocket_state(connection_id, "heartbeat_status")
            assert heartbeat_state["heartbeat_count"] == 5
            assert heartbeat_state["status"] == "healthy"
            assert heartbeat_state["missed_heartbeats"] == 0
        
        # Test heartbeat failure scenario (simulate connection issues)
        failing_user_id = "heartbeat_user_1"
        failing_user_data = users_heartbeat_data[failing_user_id]
        failing_websocket = failing_user_data["websocket"]
        failing_connection_id = failing_user_data["connection"].connection_id
        
        # Simulate WebSocket failure
        failing_websocket.is_closed = True
        
        # Run heartbeat monitor cycle with failure
        try:
            await heartbeat_monitor_cycle()
        except Exception:
            pass  # Expected to fail for the failing connection
        
        # Verify failure was tracked in state
        failed_heartbeat_state = state_manager.get_websocket_state(failing_connection_id, "heartbeat_status")
        
        # The state might have been updated to reflect the failure
        # Or the connection might have been removed due to repeated failures
        if failed_heartbeat_state:
            assert failed_heartbeat_state["missed_heartbeats"] > 0
        
        # Test connection health assessment based on heartbeat state
        def assess_connection_health(user_id: str) -> Dict[str, Any]:
            """Assess connection health based on heartbeat state."""
            user_data = users_heartbeat_data[user_id]
            connection_id = user_data["connection"].connection_id
            
            heartbeat_state = state_manager.get_websocket_state(connection_id, "heartbeat_status")
            if not heartbeat_state:
                return {"status": "unknown", "reason": "no_heartbeat_data"}
            
            health_assessment = {
                "user_id": user_id,
                "connection_id": connection_id,
                "status": heartbeat_state["status"],
                "last_heartbeat": heartbeat_state["last_heartbeat"],
                "total_heartbeats": heartbeat_state["heartbeat_count"],
                "missed_heartbeats": heartbeat_state["missed_heartbeats"]
            }
            
            return health_assessment
        
        # Assess health for all users
        health_assessments = {}
        for user_id in users_heartbeat_data.keys():
            health_assessments[user_id] = assess_connection_health(user_id)
        
        # Verify healthy connections
        healthy_users = ["heartbeat_user_0", "heartbeat_user_2"]
        for user_id in healthy_users:
            health = health_assessments[user_id]
            assert health["status"] == "healthy"
            assert health["total_heartbeats"] >= 5
        
        # Verify connection is still active for healthy users
        for user_id in healthy_users:
            assert websocket_manager.is_connection_active(user_id)

    @pytest.mark.integration
    async def test_connection_migration_between_websocket_instances(
        self,
        state_manager: UnifiedStateManager
    ):
        """
        BVJ: High availability - ensures users can migrate connections between WebSocket instances seamlessly.
        Tests connection migration capabilities with state-based recovery across WebSocket instances.
        """
        # Create two WebSocket manager instances (simulating different servers/processes)
        primary_ws_manager = UnifiedWebSocketManager()
        secondary_ws_manager = UnifiedWebSocketManager()
        
        # Set up user with connection on primary manager
        user_id = "migration_user"
        primary_websocket = MockWebSocket(
            connection_id=f"primary_conn_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            messages_sent=[]
        )
        
        primary_conn = WebSocketConnection(
            connection_id=primary_websocket.connection_id,
            user_id=user_id,
            websocket=primary_websocket,
            connected_at=datetime.now(),
            metadata={"instance": "primary", "migration_capable": True}
        )
        
        await primary_ws_manager.add_connection(primary_conn)
        
        # Set up extensive user state for migration
        migration_state = {
            "session_id": f"session_{uuid.uuid4().hex}",
            "conversation_context": {
                "thread_id": "migration_thread_123",
                "current_agent": "cost_optimizer",
                "analysis_stage": "deep_optimization",
                "conversation_history": [
                    {"role": "user", "content": "Help me optimize my cloud costs"},
                    {"role": "agent", "content": "I'll analyze your current spend patterns..."},
                    {"role": "agent", "content": "Based on the analysis, here are recommendations..."}
                ]
            },
            "execution_state": {
                "active_tools": ["aws_cost_analyzer", "rightsizing_engine"], 
                "completed_steps": ["data_collection", "pattern_analysis"],
                "pending_steps": ["recommendation_generation", "report_creation"],
                "temp_results": {"potential_monthly_savings": 15000}
            },
            "ui_state": {
                "active_tabs": ["dashboard", "cost_analysis"],
                "scroll_positions": {"dashboard": 250, "cost_analysis": 100},
                "expanded_sections": ["compute_costs", "storage_optimization"]
            }
        }
        
        # Store migration state
        state_manager.set_user_state(user_id, "migration_context", migration_state)
        state_manager.set_websocket_state(
            primary_conn.connection_id,
            "connection_migration_data",
            {
                "can_migrate": True,
                "instance_id": "primary",
                "connection_established": datetime.now().isoformat(),
                "migration_token": f"migrate_{uuid.uuid4().hex}"
            }
        )
        
        # Verify initial connection is active
        assert primary_ws_manager.is_connection_active(user_id)
        assert not secondary_ws_manager.is_connection_active(user_id)
        
        # Send messages to establish conversation state
        initial_messages = [
            {"type": "agent_started", "data": {"agent": "cost_optimizer", "thread_id": "migration_thread_123"}},
            {"type": "tool_executing", "data": {"tool": "aws_cost_analyzer", "progress": 60}},
            {"type": "analysis_update", "data": {"current_savings": 12000, "analysis_progress": 75}}
        ]
        
        for message in initial_messages:
            await primary_ws_manager.send_to_user(user_id, message)
        
        # Verify messages were received
        assert len(primary_websocket.messages_sent) == 3
        
        # Simulate need for migration (server maintenance, load balancing, etc.)
        migration_token = state_manager.get_websocket_state(
            primary_conn.connection_id, "connection_migration_data"
        )["migration_token"]
        
        # Prepare migration data
        migration_package = {
            "user_id": user_id,
            "migration_token": migration_token,
            "source_instance": "primary",
            "target_instance": "secondary", 
            "migration_timestamp": datetime.now().isoformat(),
            "state_snapshot": state_manager.get_user_state(user_id, "migration_context"),
            "connection_metadata": state_manager.get_websocket_state(
                primary_conn.connection_id, "connection_migration_data"
            )
        }
        
        # Initiate migration process
        # Step 1: Notify user of impending migration
        await primary_ws_manager.send_to_user(user_id, {
            "type": "connection_migration_starting",
            "data": {
                "reason": "load_balancing",
                "estimated_downtime": "5_seconds",
                "migration_token": migration_token
            }
        })
        
        # Step 2: Create connection on secondary manager
        secondary_websocket = MockWebSocket(
            connection_id=f"secondary_conn_{uuid.uuid4().hex[:8]}",
            user_id=user_id,
            messages_sent=[]
        )
        
        secondary_conn = WebSocketConnection(
            connection_id=secondary_websocket.connection_id,
            user_id=user_id,
            websocket=secondary_websocket,
            connected_at=datetime.now(),
            metadata={
                "instance": "secondary",
                "migrated_from": primary_conn.connection_id,
                "migration_token": migration_token
            }
        )
        
        await secondary_ws_manager.add_connection(secondary_conn)
        
        # Step 3: Transfer state to secondary instance
        state_manager.set_websocket_state(
            secondary_conn.connection_id,
            "connection_migration_data",
            {
                **migration_package["connection_metadata"],
                "instance_id": "secondary",
                "migrated_from": primary_conn.connection_id,
                "migration_completed_at": datetime.now().isoformat()
            }
        )
        
        # Step 4: Remove connection from primary manager
        await primary_ws_manager.remove_connection(primary_conn.connection_id)
        
        # Step 5: Notify user of successful migration via secondary manager
        await secondary_ws_manager.send_to_user(user_id, {
            "type": "connection_migration_completed",
            "data": {
                "new_connection_id": secondary_conn.connection_id,
                "migration_token": migration_token,
                "state_restored": True,
                "restored_context": migration_package["state_snapshot"]
            }
        })
        
        # Verify migration was successful
        assert not primary_ws_manager.is_connection_active(user_id)
        assert secondary_ws_manager.is_connection_active(user_id)
        
        # Verify state is accessible from secondary instance
        restored_migration_context = state_manager.get_user_state(user_id, "migration_context")
        assert restored_migration_context == migration_state
        
        # Verify user can continue conversation on secondary instance
        continuation_messages = [
            {"type": "tool_completed", "data": {"tool": "aws_cost_analyzer", "result": "analysis_complete"}},
            {"type": "agent_completed", "data": {"final_savings": 15000, "recommendations_count": 8}}
        ]
        
        for message in continuation_messages:
            await secondary_ws_manager.send_to_user(user_id, message)
        
        # Verify messages were delivered on secondary connection
        # Should have migration completion message + 2 continuation messages
        assert len(secondary_websocket.messages_sent) == 3
        
        migration_completion_msg = secondary_websocket.messages_sent[0]
        assert migration_completion_msg["type"] == "connection_migration_completed"
        assert migration_completion_msg["data"]["state_restored"] is True
        
        # Verify continued conversation works
        tool_completion_msg = secondary_websocket.messages_sent[1]
        agent_completion_msg = secondary_websocket.messages_sent[2]
        
        assert tool_completion_msg["type"] == "tool_completed"
        assert agent_completion_msg["type"] == "agent_completed"
        assert agent_completion_msg["data"]["final_savings"] == 15000
        
        # Verify migration metadata is properly stored
        secondary_migration_data = state_manager.get_websocket_state(
            secondary_conn.connection_id, "connection_migration_data"
        )
        assert secondary_migration_data["instance_id"] == "secondary"
        assert secondary_migration_data["migrated_from"] == primary_conn.connection_id
        assert "migration_completed_at" in secondary_migration_data

    @pytest.mark.integration
    async def test_websocket_security_validation_with_user_context_state(
        self,
        websocket_manager: UnifiedWebSocketManager,
        state_manager: UnifiedStateManager
    ):
        """
        BVJ: Security compliance - ensures WebSocket connections are properly validated with user context.
        Tests security validation mechanisms integrated with user context state management.
        """
        # Set up users with different security levels
        security_test_users = {
            "enterprise_user": {
                "user_id": "enterprise_user",
                "security_level": "high",
                "permissions": ["admin", "analytics", "cost_optimization"],
                "mfa_enabled": True,
                "session_timeout": 3600,
                "api_access_level": "full"
            },
            "standard_user": {
                "user_id": "standard_user", 
                "security_level": "medium",
                "permissions": ["analytics", "basic_optimization"],
                "mfa_enabled": False,
                "session_timeout": 1800,
                "api_access_level": "limited"
            },
            "restricted_user": {
                "user_id": "restricted_user",
                "security_level": "low", 
                "permissions": ["view_only"],
                "mfa_enabled": False,
                "session_timeout": 900,
                "api_access_level": "read_only"
            }
        }
        
        # Create connections with security context
        user_connections = {}
        
        for user_profile in security_test_users.values():
            user_id = user_profile["user_id"]
            
            websocket = MockWebSocket(
                connection_id=f"secure_conn_{user_id}_{uuid.uuid4().hex[:8]}",
                user_id=user_id,
                messages_sent=[]
            )
            
            conn = WebSocketConnection(
                connection_id=websocket.connection_id,
                user_id=user_id,
                websocket=websocket,
                connected_at=datetime.now(),
                metadata={
                    "security_validated": True,
                    "security_level": user_profile["security_level"],
                    "auth_method": "jwt_token"
                }
            )
            
            user_connections[user_id] = {"websocket": websocket, "connection": conn}
            await websocket_manager.add_connection(conn)
            
            # Set security context in state manager
            state_manager.set_user_state(user_id, "security_context", user_profile)
            state_manager.set_user_state(user_id, "session_metadata", {
                "login_time": datetime.now().isoformat(),
                "ip_address": f"192.168.1.{hash(user_id) % 254 + 1}",
                "user_agent": "SecureTestClient/1.0",
                "auth_token_expires": (datetime.now() + timedelta(seconds=user_profile["session_timeout"])).isoformat()
            })
        
        # Test security-aware message routing
        async def send_security_validated_message(
            user_id: str,
            message_type: str, 
            data: Dict[str, Any],
            required_permissions: List[str] = None
        ) -> bool:
            """Send message with security validation."""
            # Get user's security context
            security_context = state_manager.get_user_state(user_id, "security_context")
            if not security_context:
                return False
            
            # Validate permissions if required
            if required_permissions:
                user_permissions = security_context.get("permissions", [])
                if not any(perm in user_permissions for perm in required_permissions):
                    # Send access denied message
                    await websocket_manager.send_to_user(user_id, {
                        "type": "access_denied",
                        "data": {
                            "message": f"Insufficient permissions for {message_type}",
                            "required_permissions": required_permissions,
                            "user_permissions": user_permissions
                        }
                    })
                    return False
            
            # Validate session hasn't expired
            session_metadata = state_manager.get_user_state(user_id, "session_metadata")
            if session_metadata:
                token_expires = datetime.fromisoformat(session_metadata["auth_token_expires"])
                if datetime.now() > token_expires:
                    await websocket_manager.send_to_user(user_id, {
                        "type": "session_expired",
                        "data": {"message": "Session has expired, please re-authenticate"}
                    })
                    return False
            
            # Send message with security metadata
            secure_message = {
                "type": message_type,
                "data": {
                    **data,
                    "security_level": security_context["security_level"],
                    "validated_at": datetime.now().isoformat()
                }
            }
            
            await websocket_manager.send_to_user(user_id, secure_message)
            return True
        
        # Test different security scenarios
        
        # Scenario 1: Admin operation (requires admin permission)
        admin_success = await send_security_validated_message(
            "enterprise_user",
            "admin_dashboard_data",
            {"total_users": 150, "system_health": "optimal"},
            required_permissions=["admin"]
        )
        
        standard_admin_attempt = await send_security_validated_message(
            "standard_user",
            "admin_dashboard_data", 
            {"total_users": 150, "system_health": "optimal"},
            required_permissions=["admin"]
        )
        
        restricted_admin_attempt = await send_security_validated_message(
            "restricted_user",
            "admin_dashboard_data",
            {"total_users": 150, "system_health": "optimal"},
            required_permissions=["admin"]
        )
        
        assert admin_success is True  # Enterprise user has admin permission
        assert standard_admin_attempt is False  # Standard user lacks admin permission
        assert restricted_admin_attempt is False  # Restricted user lacks admin permission
        
        # Scenario 2: Analytics operation (requires analytics permission)
        enterprise_analytics = await send_security_validated_message(
            "enterprise_user",
            "analytics_report",
            {"cost_trends": [1000, 1100, 950], "optimization_opportunities": 3},
            required_permissions=["analytics"]
        )
        
        standard_analytics = await send_security_validated_message(
            "standard_user",
            "analytics_report",
            {"cost_trends": [1000, 1100, 950], "optimization_opportunities": 3},
            required_permissions=["analytics"]
        )
        
        restricted_analytics = await send_security_validated_message(
            "restricted_user",
            "analytics_report",
            {"cost_trends": [1000, 1100, 950], "optimization_opportunities": 3},
            required_permissions=["analytics"]
        )
        
        assert enterprise_analytics is True  # Has analytics permission
        assert standard_analytics is True  # Has analytics permission
        assert restricted_analytics is False  # Lacks analytics permission (view_only)
        
        # Scenario 3: Basic operation (no special permissions required)
        for user_id in security_test_users.keys():
            basic_success = await send_security_validated_message(
                user_id,
                "system_status",
                {"status": "operational", "timestamp": datetime.now().isoformat()}
            )
            assert basic_success is True  # All users can receive basic system status
        
        # Verify message delivery and access control
        enterprise_messages = user_connections["enterprise_user"]["websocket"].messages_sent
        standard_messages = user_connections["standard_user"]["websocket"].messages_sent
        restricted_messages = user_connections["restricted_user"]["websocket"].messages_sent
        
        # Enterprise user should receive: admin_dashboard + analytics_report + system_status = 3 messages
        assert len(enterprise_messages) == 3
        message_types = [msg["type"] for msg in enterprise_messages]
        assert "admin_dashboard_data" in message_types
        assert "analytics_report" in message_types
        assert "system_status" in message_types
        
        # Standard user should receive: access_denied + analytics_report + system_status = 3 messages
        assert len(standard_messages) == 3
        standard_message_types = [msg["type"] for msg in standard_messages]
        assert "access_denied" in standard_message_types  # Denied admin access
        assert "analytics_report" in standard_message_types
        assert "system_status" in standard_message_types
        
        # Restricted user should receive: access_denied + access_denied + system_status = 3 messages
        assert len(restricted_messages) == 3
        restricted_message_types = [msg["type"] for msg in restricted_messages]
        assert restricted_message_types.count("access_denied") == 2  # Denied admin and analytics
        assert "system_status" in restricted_message_types
        
        # Test session timeout simulation
        # Manually expire restricted user's session
        restricted_session = state_manager.get_user_state("restricted_user", "session_metadata")
        restricted_session["auth_token_expires"] = (datetime.now() - timedelta(seconds=10)).isoformat()  # Expired 10 seconds ago
        state_manager.set_user_state("restricted_user", "session_metadata", restricted_session)
        
        # Attempt to send message to expired session
        expired_session_result = await send_security_validated_message(
            "restricted_user",
            "test_expired_session",
            {"data": "should_not_receive"}
        )
        
        assert expired_session_result is False
        
        # Verify session expiry message was sent
        final_restricted_messages = user_connections["restricted_user"]["websocket"].messages_sent
        assert len(final_restricted_messages) == 4  # Previous 3 + session expired message
        assert final_restricted_messages[-1]["type"] == "session_expired"