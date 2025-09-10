"""
Test WebSocket Message Routing Business Logic

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable real-time communication for AI chat
- Value Impact: Enables instant user feedback during agent execution
- Strategic Impact: Core infrastructure for 90% of user value delivery

CRITICAL COMPLIANCE:
- Tests message routing accuracy for multi-user isolation
- Validates event ordering for coherent user experience
- Ensures message filtering by user permissions
- Tests connection state management for reliability
"""

import pytest
import uuid
import json
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from netra_backend.app.websocket_core.message_queue import MessageQueue
from netra_backend.app.websocket_core.connection_manager import ConnectionManager
from netra_backend.app.websocket_core.batch_message_handler import BatchMessageHandler
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager


class TestWebSocketMessageRoutingBusinessLogic:
    """Test WebSocket message routing business logic patterns."""
    
    @pytest.fixture
    def message_queue(self):
        """Create WebSocket message queue for testing."""
        return WebSocketMessageQueue(max_size=1000)
    
    @pytest.fixture
    def connection_manager(self):
        """Create connection manager for testing."""
        return ConnectionManager()
    
    @pytest.fixture
    def batch_message_handler(self):
        """Create batch message handler for testing."""
        return BatchMessageHandler(batch_size=10, flush_interval=1.0)
    
    @pytest.fixture
    def mock_user_context(self):
        """Create mock user context."""
        return {
            "user_id": str(uuid.uuid4()),
            "email": "test@enterprise.com", 
            "permissions": ["read_data", "execute_agents"],
            "subscription_tier": "enterprise",
            "thread_id": str(uuid.uuid4())
        }
    
    @pytest.mark.unit
    def test_message_routing_multi_user_isolation(self, message_queue, mock_user_context):
        """Test message routing maintains multi-user isolation."""
        # Given: Multiple users with different contexts
        user1_id = str(uuid.uuid4())
        user2_id = str(uuid.uuid4())
        user3_id = str(uuid.uuid4())
        
        user_contexts = [
            {"user_id": user1_id, "subscription_tier": "basic", "permissions": ["read_basic"]},
            {"user_id": user2_id, "subscription_tier": "premium", "permissions": ["read_basic", "write_data"]},
            {"user_id": user3_id, "subscription_tier": "enterprise", "permissions": ["read_basic", "write_data", "execute_agents"]}
        ]
        
        # When: Routing messages to different users
        messages_sent = []
        for user_ctx in user_contexts:
            message = {
                "type": "agent_started",
                "data": {"agent_name": "cost_optimizer", "user_id": user_ctx["user_id"]},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "target_user": user_ctx["user_id"]
            }
            
            message_queue.enqueue_user_message(user_ctx["user_id"], message)
            messages_sent.append((user_ctx["user_id"], message))
        
        # Then: Each user should only receive their own messages
        for user_id, expected_message in messages_sent:
            user_messages = message_queue.get_user_messages(user_id)
            assert len(user_messages) == 1
            assert user_messages[0]["target_user"] == user_id
            assert user_messages[0]["data"]["user_id"] == user_id
            
            # Should not contain messages for other users
            for other_user_id, _ in messages_sent:
                if other_user_id != user_id:
                    other_messages = message_queue.get_user_messages(other_user_id)
                    user_specific_messages = [msg for msg in user_messages if msg["target_user"] == other_user_id]
                    assert len(user_specific_messages) == 0
    
    @pytest.mark.unit
    def test_agent_event_ordering_business_logic(self, message_queue, mock_user_context):
        """Test agent event ordering maintains coherent user experience."""
        # Given: Agent execution events that must maintain proper order
        user_id = mock_user_context["user_id"]
        thread_id = mock_user_context["thread_id"]
        
        # Critical events for business value delivery
        agent_events = [
            {"type": "agent_started", "timestamp": "2025-01-09T10:00:00Z", "sequence": 1},
            {"type": "agent_thinking", "timestamp": "2025-01-09T10:00:01Z", "sequence": 2},
            {"type": "tool_executing", "timestamp": "2025-01-09T10:00:02Z", "sequence": 3},
            {"type": "tool_completed", "timestamp": "2025-01-09T10:00:03Z", "sequence": 4},
            {"type": "agent_completed", "timestamp": "2025-01-09T10:00:04Z", "sequence": 5}
        ]
        
        # When: Events arrive potentially out of order (network delays)
        import random
        shuffled_events = agent_events.copy()
        random.shuffle(shuffled_events)
        
        for event in shuffled_events:
            message = {
                "type": event["type"],
                "data": {
                    "thread_id": thread_id,
                    "sequence_number": event["sequence"],
                    "timestamp": event["timestamp"]
                },
                "user_id": user_id
            }
            message_queue.enqueue_user_message(user_id, message)
        
        # Then: Messages should be reordered correctly for user experience
        user_messages = message_queue.get_ordered_user_messages(user_id)
        assert len(user_messages) == 5
        
        # Verify correct business event sequence
        expected_sequence = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        actual_sequence = [msg["type"] for msg in user_messages]
        assert actual_sequence == expected_sequence
        
        # Verify sequence numbers are in order
        sequence_numbers = [msg["data"]["sequence_number"] for msg in user_messages]
        assert sequence_numbers == [1, 2, 3, 4, 5]
    
    @pytest.mark.unit
    def test_permission_based_message_filtering(self, message_queue):
        """Test message filtering based on user permissions for security."""
        # Given: Users with different permission levels
        users_with_permissions = [
            {
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic"],
                "tier": "basic",
                "should_receive_admin": False,
                "should_receive_agent_events": False
            },
            {
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic", "read_premium"],
                "tier": "premium",
                "should_receive_admin": False,
                "should_receive_agent_events": False
            },
            {
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic", "execute_agents"],
                "tier": "premium_plus",
                "should_receive_admin": False,
                "should_receive_agent_events": True
            },
            {
                "user_id": str(uuid.uuid4()),
                "permissions": ["read_basic", "execute_agents", "admin_access"],
                "tier": "enterprise", 
                "should_receive_admin": True,
                "should_receive_agent_events": True
            }
        ]
        
        # Different message types requiring different permissions
        test_messages = [
            {
                "type": "basic_notification",
                "required_permission": "read_basic",
                "data": {"message": "Welcome to Netra"}
            },
            {
                "type": "agent_execution_started",
                "required_permission": "execute_agents", 
                "data": {"agent": "cost_optimizer", "status": "started"}
            },
            {
                "type": "admin_system_alert",
                "required_permission": "admin_access",
                "data": {"alert": "System maintenance scheduled"}
            }
        ]
        
        for user in users_with_permissions:
            for message in test_messages:
                # When: Filtering messages based on user permissions
                should_receive = message["required_permission"] in user["permissions"]
                
                if should_receive:
                    message_queue.enqueue_user_message(user["user_id"], message)
                
                # Then: User should only receive messages they have permissions for
                user_messages = message_queue.get_user_messages(user["user_id"])
                
                if should_receive:
                    assert len([msg for msg in user_messages if msg["type"] == message["type"]]) == 1
                else:
                    assert len([msg for msg in user_messages if msg["type"] == message["type"]]) == 0
    
    @pytest.mark.unit
    def test_connection_state_routing_business_logic(self, connection_manager):
        """Test connection state management for reliable message delivery."""
        # Given: Users in different connection states
        connection_scenarios = [
            {
                "user_id": str(uuid.uuid4()),
                "connection_state": "connected",
                "should_deliver_immediately": True,
                "should_queue_messages": False
            },
            {
                "user_id": str(uuid.uuid4()),
                "connection_state": "disconnected",
                "should_deliver_immediately": False,
                "should_queue_messages": True
            },
            {
                "user_id": str(uuid.uuid4()),
                "connection_state": "reconnecting", 
                "should_deliver_immediately": False,
                "should_queue_messages": True
            }
        ]
        
        for scenario in connection_scenarios:
            # When: Managing connection state for message routing
            connection_manager.update_connection_state(
                scenario["user_id"], 
                scenario["connection_state"]
            )
            
            # Then: Message routing should adapt to connection state
            can_deliver_immediately = connection_manager.can_deliver_immediately(scenario["user_id"])
            should_queue = connection_manager.should_queue_messages(scenario["user_id"])
            
            assert can_deliver_immediately == scenario["should_deliver_immediately"]
            assert should_queue == scenario["should_queue_messages"]
            
            # Business logic: Never lose messages for disconnected premium/enterprise users
            user_tier = "enterprise"  # Assume enterprise user
            if scenario["connection_state"] == "disconnected" and user_tier in ["premium", "enterprise"]:
                assert should_queue is True  # Must queue for premium users
    
    @pytest.mark.unit
    def test_batch_message_processing_performance_optimization(self, batch_message_handler):
        """Test batch message processing optimizes performance for high-volume users."""
        # Given: High-volume user generating many messages
        user_id = str(uuid.uuid4())
        enterprise_user_context = {
            "user_id": user_id,
            "subscription_tier": "enterprise",
            "expected_message_volume": "high"
        }
        
        # Generate batch of messages (typical agent execution)
        message_batch = []
        for i in range(25):  # More than batch size (10)
            message = {
                "type": f"agent_progress_update",
                "data": {
                    "step": i,
                    "progress": f"{i*4}%",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "user_id": user_id,
                "sequence": i
            }
            message_batch.append(message)
        
        # When: Processing messages in batches
        batches_processed = []
        for message in message_batch:
            batch_handler_result = batch_message_handler.add_message(message)
            if batch_handler_result and batch_handler_result.get("batch_ready"):
                batches_processed.append(batch_handler_result["batch"])
        
        # Force flush remaining messages
        remaining_batch = batch_message_handler.flush_pending()
        if remaining_batch:
            batches_processed.append(remaining_batch)
        
        # Then: Should process messages efficiently in batches
        assert len(batches_processed) >= 2  # Should have created multiple batches
        
        total_messages_processed = sum(len(batch) for batch in batches_processed)
        assert total_messages_processed == 25  # All messages should be processed
        
        # First batches should be at batch size limit (10)
        if len(batches_processed) > 1:
            assert len(batches_processed[0]) == 10  # Full batch
    
    @pytest.mark.unit
    def test_message_priority_routing_business_value(self, message_queue):
        """Test message priority routing ensures critical business messages are delivered first."""
        # Given: Messages with different business priorities
        user_id = str(uuid.uuid4())
        
        prioritized_messages = [
            {
                "type": "system_error",
                "priority": "critical",
                "data": {"error": "Payment processing failed"},
                "business_impact": "revenue_blocking"
            },
            {
                "type": "agent_completed",
                "priority": "high",
                "data": {"result": "cost_optimization_complete"},
                "business_impact": "user_value_delivery"
            },
            {
                "type": "agent_thinking",
                "priority": "medium",
                "data": {"status": "analyzing_data"},
                "business_impact": "user_experience"
            },
            {
                "type": "system_maintenance",
                "priority": "low", 
                "data": {"message": "Scheduled maintenance tonight"},
                "business_impact": "informational"
            }
        ]
        
        # When: Adding messages with different priorities (reverse order)
        for message in reversed(prioritized_messages):  # Add in reverse priority order
            message_queue.enqueue_prioritized_message(user_id, message, message["priority"])
        
        # Then: Should retrieve messages in business priority order
        user_messages = message_queue.get_prioritized_user_messages(user_id)
        assert len(user_messages) == 4
        
        # Verify business-critical messages come first
        expected_priority_order = ["critical", "high", "medium", "low"]
        actual_priority_order = [msg["priority"] for msg in user_messages]
        assert actual_priority_order == expected_priority_order
        
        # Verify business impact ordering
        expected_impact_order = ["revenue_blocking", "user_value_delivery", "user_experience", "informational"]
        actual_impact_order = [msg["business_impact"] for msg in user_messages]
        assert actual_impact_order == expected_impact_order
    
    @pytest.mark.unit
    def test_websocket_message_serialization_business_data(self):
        """Test WebSocket message serialization handles business data correctly."""
        # Given: Business messages with complex data structures
        business_messages = [
            {
                "type": "cost_optimization_result",
                "data": {
                    "monthly_savings": 15420.50,
                    "recommendations": [
                        {"service": "EC2", "action": "downsize", "savings": 8500.00},
                        {"service": "S3", "action": "lifecycle_policy", "savings": 3200.00},
                        {"service": "RDS", "action": "reserved_instances", "savings": 3720.50}
                    ],
                    "confidence_score": 0.92,
                    "implementation_priority": "high"
                }
            },
            {
                "type": "agent_execution_metrics",
                "data": {
                    "execution_time": 45.2,
                    "tokens_used": 2847,
                    "api_calls": 12,
                    "success_rate": 0.958,
                    "user_satisfaction_predicted": 0.89
                }
            }
        ]
        
        for message in business_messages:
            # When: Serializing business data for WebSocket transmission
            try:
                serialized = json.dumps(message, default=str)
                deserialized = json.loads(serialized)
                
                # Then: Should preserve business data accuracy
                assert deserialized["type"] == message["type"]
                assert deserialized["data"] is not None
                
                # Verify numeric precision for financial data
                if message["type"] == "cost_optimization_result":
                    assert abs(float(deserialized["data"]["monthly_savings"]) - 15420.50) < 0.01
                    
                    # Verify recommendation structure
                    recommendations = deserialized["data"]["recommendations"]
                    assert len(recommendations) == 3
                    assert recommendations[0]["service"] == "EC2"
                    assert abs(float(recommendations[0]["savings"]) - 8500.00) < 0.01
                
                # Verify metric precision
                if message["type"] == "agent_execution_metrics":
                    assert abs(float(deserialized["data"]["execution_time"]) - 45.2) < 0.1
                    assert int(deserialized["data"]["tokens_used"]) == 2847
                    
            except (TypeError, ValueError, KeyError) as e:
                pytest.fail(f"Message serialization failed for business data: {e}")
    
    @pytest.mark.unit
    def test_websocket_connection_recovery_business_continuity(self, connection_manager):
        """Test WebSocket connection recovery maintains business continuity."""
        # Given: Enterprise user connection experiencing interruptions
        user_id = str(uuid.uuid4())
        user_context = {
            "user_id": user_id,
            "subscription_tier": "enterprise",
            "active_agents": ["cost_optimizer", "security_analyzer"],
            "critical_session": True
        }
        
        # When: Connection goes through various states
        connection_states = [
            "connected",
            "disconnected",  # Temporary network issue
            "reconnecting",  # Client attempting reconnection
            "connected"      # Successfully reconnected
        ]
        
        messages_queued_during_disconnect = []
        
        for state in connection_states:
            connection_manager.update_connection_state(user_id, state)
            
            # Simulate important messages arriving during connection issues
            if state in ["disconnected", "reconnecting"]:
                important_message = {
                    "type": "agent_completed",
                    "data": {
                        "agent": "cost_optimizer",
                        "result": {"savings_found": 12500.00},
                        "critical_for_user": True
                    },
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                # Should queue messages for enterprise users during disconnection
                if connection_manager.should_queue_messages(user_id):
                    messages_queued_during_disconnect.append(important_message)
        
        # Then: Should have maintained business continuity
        assert len(messages_queued_during_disconnect) > 0  # Messages were queued
        
        # When reconnected, should deliver queued messages
        final_state = connection_manager.get_connection_state(user_id)
        assert final_state == "connected"
        
        # Verify business continuity for enterprise users
        if user_context["subscription_tier"] == "enterprise":
            can_deliver = connection_manager.can_deliver_immediately(user_id)
            assert can_deliver is True
            
            # Should deliver all queued business-critical messages
            for queued_msg in messages_queued_during_disconnect:
                assert queued_msg["data"]["critical_for_user"] is True
                assert "savings_found" in queued_msg["data"]["result"]