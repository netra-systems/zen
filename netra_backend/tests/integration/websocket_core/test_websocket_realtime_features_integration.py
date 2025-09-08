"""
Integration tests for WebSocket Real-time Features - Testing real-time updates and notifications.

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise
- Business Goal: Enhanced user experience through real-time updates
- Value Impact: Users see agent progress immediately, improving perceived responsiveness
- Strategic Impact: Differentiator for premium tiers - real-time AI interaction experience

These integration tests validate real-time features like typing indicators, progress updates,
live agent reasoning, and collaborative features that enhance the AI chat experience.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.websocket import WebSocketTestUtility
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from netra_backend.app.models import User, Thread
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestWebSocketRealTimeFeaturesIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket real-time features."""
    
    @pytest.fixture
    async def test_user(self, real_services_fixture) -> User:
        """Create test user with enterprise subscription."""
        db = real_services_fixture["db"]
        
        user = User(
            email="realtime_test@example.com",
            name="Real-time Test User",
            subscription_tier="enterprise"  # Enable real-time features
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @pytest.fixture
    async def test_thread(self, real_services_fixture, test_user) -> Thread:
        """Create test thread for real-time testing."""
        db = real_services_fixture["db"]
        
        thread = Thread(
            user_id=test_user.id,
            title="Real-time Features Test Chat",
            metadata={"real_time_enabled": True, "features": ["typing", "progress", "live_reasoning"]}
        )
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
        return thread
    
    @pytest.fixture
    async def websocket_manager(self):
        """Create WebSocket manager for testing."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_typing_indicator_real_time_updates(self, real_services_fixture, test_user, test_thread,
                                                     websocket_manager, websocket_utility):
        """Test real-time typing indicators during agent processing."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="typing_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"real_time_features": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Send user message to trigger agent response
        user_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Analyze my cloud costs and provide recommendations",
                "thread_id": str(test_thread.id),
                "enable_typing_indicator": True
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=user_message
        )
        
        # Simulate agent starting to "type" (think)
        typing_started = WebSocketMessage(
            message_type=MessageType.TYPING_INDICATOR,
            payload={
                "typing": True,
                "agent_name": "cost_optimizer", 
                "status": "thinking",
                "estimated_duration_seconds": 15
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.send_to_user(
            user_id=str(test_user.id),
            message=typing_started
        )
        
        # Simulate intermediate typing updates
        typing_updates = [
            {"status": "analyzing_data", "progress": 25},
            {"status": "calculating_costs", "progress": 50}, 
            {"status": "generating_recommendations", "progress": 75},
            {"status": "finalizing_response", "progress": 95}
        ]
        
        for update in typing_updates:
            typing_update = WebSocketMessage(
                message_type=MessageType.TYPING_INDICATOR,
                payload={
                    "typing": True,
                    "agent_name": "cost_optimizer",
                    **update
                },
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            await websocket_manager.send_to_user(
                user_id=str(test_user.id),
                message=typing_update
            )
            await asyncio.sleep(0.1)  # Simulate processing time
        
        # Send typing stopped
        typing_stopped = WebSocketMessage(
            message_type=MessageType.TYPING_INDICATOR,
            payload={
                "typing": False,
                "agent_name": "cost_optimizer"
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.send_to_user(
            user_id=str(test_user.id),
            message=typing_stopped
        )
        
        # Verify typing indicators were sent
        sent_messages = mock_websocket.sent_messages
        typing_messages = [
            msg for msg in sent_messages 
            if hasattr(msg, 'message_type') and msg.message_type == MessageType.TYPING_INDICATOR
        ]
        
        assert len(typing_messages) >= 6  # Start + 4 updates + stop
        
        # Verify typing progression
        typing_states = []
        for msg in typing_messages:
            if hasattr(msg, 'payload'):
                typing_states.append(msg.payload)
        
        # Should start with typing=True
        assert typing_states[0]["typing"] is True
        
        # Should have progress updates
        progress_values = [state.get("progress", 0) for state in typing_states if state.get("typing")]
        progress_values = [p for p in progress_values if p > 0]
        assert len(progress_values) >= 4
        assert sorted(progress_values) == progress_values  # Should be ascending
        
        # Should end with typing=False
        assert typing_states[-1]["typing"] is False
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_live_agent_reasoning_updates(self, real_services_fixture, test_user, test_thread,
                                              websocket_manager, websocket_utility):
        """Test live updates of agent reasoning process."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="reasoning_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"live_reasoning": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Simulate live agent reasoning updates
        reasoning_steps = [
            {
                "step": "data_collection",
                "description": "Gathering cloud cost data from APIs...",
                "reasoning": "I need to collect current cost data to provide accurate analysis",
                "progress": 10,
                "confidence": 0.9
            },
            {
                "step": "pattern_analysis", 
                "description": "Analyzing spending patterns over time...",
                "reasoning": "Looking for trends and anomalies in cost patterns to identify optimization opportunities",
                "progress": 30,
                "confidence": 0.85
            },
            {
                "step": "resource_evaluation",
                "description": "Evaluating resource utilization...",
                "reasoning": "Checking if resources are over-provisioned or underutilized for potential savings",
                "progress": 60,
                "confidence": 0.92
            },
            {
                "step": "recommendation_generation",
                "description": "Generating optimization recommendations...",
                "reasoning": "Synthesizing findings into actionable recommendations with cost impact estimates",
                "progress": 85,
                "confidence": 0.88
            }
        ]
        
        # Send each reasoning step as live update
        for step_data in reasoning_steps:
            reasoning_update = WebSocketMessage(
                message_type=MessageType.AGENT_REASONING,
                payload={
                    "agent_name": "cost_optimizer",
                    "reasoning_type": "live_thinking",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    **step_data
                },
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            await websocket_manager.send_to_user(
                user_id=str(test_user.id),
                message=reasoning_update
            )
            await asyncio.sleep(0.05)  # Simulate thinking time
        
        # Verify reasoning updates were delivered
        sent_messages = mock_websocket.sent_messages
        reasoning_messages = [
            msg for msg in sent_messages
            if hasattr(msg, 'message_type') and msg.message_type == MessageType.AGENT_REASONING
        ]
        
        assert len(reasoning_messages) == len(reasoning_steps)
        
        # Verify reasoning content and progression
        for i, msg in enumerate(reasoning_messages):
            payload = msg.payload
            expected_step = reasoning_steps[i]
            
            assert payload["step"] == expected_step["step"]
            assert payload["description"] == expected_step["description"]
            assert payload["reasoning"] == expected_step["reasoning"]
            assert payload["progress"] == expected_step["progress"]
            assert payload["confidence"] == expected_step["confidence"]
        
        # Verify progress is ascending
        progress_values = [msg.payload["progress"] for msg in reasoning_messages]
        assert progress_values == sorted(progress_values)
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_progress_tracking(self, real_services_fixture, test_user, test_thread,
                                             websocket_manager, websocket_utility):
        """Test real-time progress tracking for long-running operations."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="progress_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"progress_tracking": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Start long-running operation
        operation_started = WebSocketMessage(
            message_type=MessageType.OPERATION_PROGRESS,
            payload={
                "operation_id": "cost_analysis_001",
                "operation_type": "comprehensive_cost_analysis",
                "status": "started",
                "progress_percentage": 0,
                "estimated_completion_time": (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat(),
                "current_step": "initializing"
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.send_to_user(
            user_id=str(test_user.id),
            message=operation_started
        )
        
        # Send progress updates
        progress_updates = [
            {"progress": 15, "step": "connecting_to_cloud_apis", "details": "Authenticating with AWS, Azure, GCP"},
            {"progress": 35, "step": "collecting_cost_data", "details": "Retrieving 30 days of cost data"},
            {"progress": 55, "step": "analyzing_patterns", "details": "Identifying cost trends and anomalies"},
            {"progress": 75, "step": "calculating_optimizations", "details": "Computing potential savings"},
            {"progress": 90, "step": "generating_report", "details": "Creating detailed recommendations"},
            {"progress": 100, "step": "completed", "details": "Analysis complete"}
        ]
        
        for update in progress_updates:
            progress_message = WebSocketMessage(
                message_type=MessageType.OPERATION_PROGRESS,
                payload={
                    "operation_id": "cost_analysis_001",
                    "operation_type": "comprehensive_cost_analysis",
                    "status": "in_progress" if update["progress"] < 100 else "completed",
                    "progress_percentage": update["progress"],
                    "current_step": update["step"],
                    "step_details": update["details"],
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            await websocket_manager.send_to_user(
                user_id=str(test_user.id),
                message=progress_message
            )
            await asyncio.sleep(0.1)  # Simulate processing time
        
        # Verify progress updates were delivered
        sent_messages = mock_websocket.sent_messages
        progress_messages = [
            msg for msg in sent_messages
            if hasattr(msg, 'message_type') and msg.message_type == MessageType.OPERATION_PROGRESS
        ]
        
        assert len(progress_messages) >= 7  # Start + 6 updates
        
        # Verify progress tracking
        progress_values = []
        for msg in progress_messages:
            if hasattr(msg, 'payload') and 'progress_percentage' in msg.payload:
                progress_values.append(msg.payload['progress_percentage'])
        
        # Progress should be monotonically increasing
        assert progress_values == sorted(progress_values)
        assert progress_values[0] == 0  # Starts at 0
        assert progress_values[-1] == 100  # Ends at 100
        
        # Verify operation lifecycle
        first_msg = progress_messages[0]
        last_msg = progress_messages[-1]
        
        assert first_msg.payload["status"] == "started"
        assert first_msg.payload["current_step"] == "initializing"
        
        assert last_msg.payload["status"] == "completed"
        assert last_msg.payload["current_step"] == "completed"
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_collaboration_features(self, real_services_fixture, websocket_manager, websocket_utility):
        """Test real-time collaboration features for multiple users."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create multiple users
        users = []
        for i in range(3):
            user = User(
                email=f"collab_user_{i}@example.com",
                name=f"Collaboration User {i}",
                subscription_tier="enterprise"
            )
            db.add(user)
            users.append(user)
        
        await db.commit()
        for user in users:
            await db.refresh(user)
        
        # Create shared thread
        shared_thread = Thread(
            user_id=users[0].id,
            title="Collaborative Cost Analysis",
            metadata={
                "collaboration_enabled": True,
                "participants": [str(user.id) for user in users]
            }
        )
        db.add(shared_thread)
        await db.commit()
        await db.refresh(shared_thread)
        
        # Create WebSocket connections for all users
        connections = []
        websockets = []
        
        for i, user in enumerate(users):
            websocket = await websocket_utility.create_mock_websocket()
            connection = await websocket_manager.create_connection(
                connection_id=f"collab_conn_{i}",
                user_id=str(user.id),
                websocket=websocket,
                metadata={"collaboration": True, "thread_id": str(shared_thread.id)}
            )
            await websocket_manager.add_connection(connection)
            connections.append(connection)
            websockets.append(websocket)
        
        # User 0 sends message - should notify other users
        collaboration_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Let's analyze our Q4 cloud costs together",
                "thread_id": str(shared_thread.id),
                "collaboration_context": {
                    "shared_session": True,
                    "notify_participants": True
                }
            },
            user_id=str(users[0].id),
            thread_id=str(shared_thread.id)
        )
        
        await websocket_manager.handle_message(
            user_id=str(users[0].id),
            websocket=websockets[0],
            message=collaboration_message
        )
        
        # Send collaboration notifications to other participants
        for i in range(1, len(users)):
            notification = WebSocketMessage(
                message_type=MessageType.COLLABORATION_UPDATE,
                payload={
                    "event_type": "new_message",
                    "thread_id": str(shared_thread.id),
                    "participant_id": str(users[0].id),
                    "participant_name": users[0].name,
                    "message_preview": "Let's analyze our Q4 cloud costs together",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                user_id=str(users[i].id),
                thread_id=str(shared_thread.id)
            )
            
            await websocket_manager.send_to_user(
                user_id=str(users[i].id),
                message=notification
            )
        
        # Simulate user presence updates
        presence_updates = [
            {"user_id": str(users[0].id), "status": "active", "activity": "typing"},
            {"user_id": str(users[1].id), "status": "active", "activity": "viewing"},
            {"user_id": str(users[2].id), "status": "active", "activity": "reviewing_results"}
        ]
        
        for update in presence_updates:
            presence_message = WebSocketMessage(
                message_type=MessageType.USER_PRESENCE,
                payload={
                    "thread_id": str(shared_thread.id),
                    "presence_update": update,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                user_id=update["user_id"],
                thread_id=str(shared_thread.id)
            )
            
            # Broadcast to all other users
            for i, user in enumerate(users):
                if str(user.id) != update["user_id"]:
                    await websocket_manager.send_to_user(
                        user_id=str(user.id),
                        message=presence_message
                    )
        
        # Verify collaboration features work
        # Check that other users received collaboration notifications
        for i in range(1, len(users)):
            user_messages = websockets[i].sent_messages
            collaboration_msgs = [
                msg for msg in user_messages
                if hasattr(msg, 'message_type') and msg.message_type == MessageType.COLLABORATION_UPDATE
            ]
            assert len(collaboration_msgs) >= 1
            
            # Verify notification content
            notification = collaboration_msgs[0]
            assert notification.payload["event_type"] == "new_message"
            assert notification.payload["participant_id"] == str(users[0].id)
            assert "Q4 cloud costs" in notification.payload["message_preview"]
        
        # Check presence updates
        for i, websocket in enumerate(websockets):
            presence_msgs = [
                msg for msg in websocket.sent_messages
                if hasattr(msg, 'message_type') and msg.message_type == MessageType.USER_PRESENCE
            ]
            
            # Each user should receive presence updates from other users
            assert len(presence_msgs) >= 2  # Updates from other 2 users
        
        # Cleanup
        for connection in connections:
            await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_real_time_system_notifications(self, real_services_fixture, test_user, test_thread,
                                                 websocket_manager, websocket_utility):
        """Test real-time system notifications and alerts."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="notifications_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"system_notifications": True}
        )
        await websocket_manager.add_connection(connection)
        
        # Send various system notifications
        system_notifications = [
            {
                "type": "cost_alert",
                "priority": "high",
                "title": "Cost Spike Detected",
                "message": "Your AWS costs increased by 45% this week",
                "action_required": True,
                "data": {"current_cost": 15420, "previous_cost": 10640}
            },
            {
                "type": "optimization_opportunity", 
                "priority": "medium",
                "title": "New Optimization Found",
                "message": "Potential savings of $800/month identified in us-east-1",
                "action_required": False,
                "data": {"potential_savings": 800, "region": "us-east-1"}
            },
            {
                "type": "system_maintenance",
                "priority": "low",
                "title": "Scheduled Maintenance",
                "message": "System maintenance scheduled for tonight 2-4 AM UTC",
                "action_required": False,
                "data": {"start_time": "2024-01-15T02:00:00Z", "duration_hours": 2}
            }
        ]
        
        for notification_data in system_notifications:
            notification = WebSocketMessage(
                message_type=MessageType.SYSTEM_NOTIFICATION,
                payload={
                    "notification_id": f"notif_{hash(notification_data['title'])}",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "expires_at": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat(),
                    **notification_data
                },
                user_id=str(test_user.id)
            )
            
            await websocket_manager.send_to_user(
                user_id=str(test_user.id),
                message=notification
            )
            await asyncio.sleep(0.05)
        
        # Verify system notifications were delivered
        sent_messages = mock_websocket.sent_messages
        notification_messages = [
            msg for msg in sent_messages
            if hasattr(msg, 'message_type') and msg.message_type == MessageType.SYSTEM_NOTIFICATION
        ]
        
        assert len(notification_messages) == len(system_notifications)
        
        # Verify notification priorities and content
        for i, msg in enumerate(notification_messages):
            payload = msg.payload
            expected = system_notifications[i]
            
            assert payload["type"] == expected["type"]
            assert payload["priority"] == expected["priority"]
            assert payload["title"] == expected["title"]
            assert payload["message"] == expected["message"]
            assert payload["action_required"] == expected["action_required"]
            assert payload["data"] == expected["data"]
        
        # Verify high priority notifications come first (if ordering is implemented)
        priorities = [msg.payload["priority"] for msg in notification_messages]
        high_priority_indices = [i for i, p in enumerate(priorities) if p == "high"]
        
        if high_priority_indices:
            # High priority should come early
            assert min(high_priority_indices) <= 1
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)