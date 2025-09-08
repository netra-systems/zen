"""
Integration tests for WebSocket Database Persistence - Testing message persistence and recovery.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Data integrity and conversation continuity 
- Value Impact: Ensures chat history is preserved and recoverable across sessions
- Strategic Impact: Critical for enterprise users requiring audit trails and conversation history

These integration tests validate WebSocket message persistence to database,
ensuring reliable storage and retrieval of chat interactions for business continuity.
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
from netra_backend.app.models import User, Thread, Message
from netra_backend.app.services.user_execution_context import UserExecutionContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class TestWebSocketDatabasePersistenceIntegration(BaseIntegrationTest):
    """Integration tests for WebSocket database persistence."""
    
    @pytest.fixture
    async def test_user(self, real_services_fixture) -> User:
        """Create test user in database."""
        db: AsyncSession = real_services_fixture["db"]
        
        user = User(
            email="websocket_test@example.com",
            name="WebSocket Test User",
            subscription_tier="enterprise"
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user
    
    @pytest.fixture 
    async def test_thread(self, real_services_fixture, test_user) -> Thread:
        """Create test thread in database."""
        db: AsyncSession = real_services_fixture["db"]
        
        thread = Thread(
            user_id=test_user.id,
            title="WebSocket Integration Test Chat",
            metadata={"test": True, "websocket_integration": True}
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
    async def test_user_message_persistence(self, real_services_fixture, test_user, test_thread,
                                          websocket_manager, websocket_utility):
        """Test persistence of user messages to database."""
        db: AsyncSession = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="persistence_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"thread_id": str(test_thread.id)}
        )
        await websocket_manager.add_connection(connection)
        
        # Create user message
        user_message = WebSocketMessage(
            message_type=MessageType.USER_MESSAGE,
            payload={
                "content": "Please analyze my cloud infrastructure costs and provide optimization recommendations.",
                "thread_id": str(test_thread.id),
                "message_id": "test_msg_001",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        # Process message (this should trigger persistence)
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=user_message
        )
        
        # Allow time for async persistence
        await asyncio.sleep(0.2)
        
        # Verify message was persisted to database
        query = select(Message).where(
            Message.thread_id == test_thread.id,
            Message.content.contains("analyze my cloud infrastructure")
        )
        result = await db.execute(query)
        persisted_message = result.scalar_one_or_none()
        
        assert persisted_message is not None
        assert persisted_message.user_id == test_user.id
        assert persisted_message.thread_id == test_thread.id
        assert persisted_message.role == "user"
        assert "analyze my cloud infrastructure" in persisted_message.content
        assert persisted_message.created_at is not None
        
        # Verify message metadata
        assert persisted_message.metadata is not None
        assert persisted_message.metadata.get("websocket_delivered") is True
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_agent_response_persistence(self, real_services_fixture, test_user, test_thread,
                                            websocket_manager, websocket_utility):
        """Test persistence of agent responses to database."""
        db: AsyncSession = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="agent_persistence_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket
        )
        await websocket_manager.add_connection(connection)
        
        # Simulate complete agent execution sequence
        agent_messages = [
            {
                "type": MessageType.AGENT_STARTED,
                "payload": {
                    "agent_name": "cost_optimizer",
                    "request": "Analyze cloud costs",
                    "started_at": datetime.now(timezone.utc).isoformat()
                }
            },
            {
                "type": MessageType.AGENT_THINKING, 
                "payload": {
                    "status": "Analyzing current cloud spend patterns...",
                    "progress": 25
                }
            },
            {
                "type": MessageType.TOOL_EXECUTING,
                "payload": {
                    "tool_name": "cloud_cost_analyzer",
                    "parameters": {"time_range": "30_days"}
                }
            },
            {
                "type": MessageType.TOOL_COMPLETED,
                "payload": {
                    "tool_name": "cloud_cost_analyzer",
                    "result": {
                        "total_cost": 15420.50,
                        "cost_breakdown": {"compute": 8500, "storage": 3200, "network": 2720.50},
                        "optimization_opportunities": 3
                    }
                }
            },
            {
                "type": MessageType.AGENT_COMPLETED,
                "payload": {
                    "agent_name": "cost_optimizer",
                    "final_result": {
                        "analysis_summary": "Found 3 optimization opportunities totaling $2,300/month savings",
                        "recommendations": [
                            "Right-size underutilized EC2 instances (saves $1,200/month)",
                            "Implement reserved instances for predictable workloads (saves $800/month)",
                            "Optimize storage tiering for infrequently accessed data (saves $300/month)"
                        ],
                        "confidence_score": 0.92
                    },
                    "completed_at": datetime.now(timezone.utc).isoformat()
                }
            }
        ]
        
        # Send each agent message
        for msg_data in agent_messages:
            message = WebSocketMessage(
                message_type=msg_data["type"],
                payload=msg_data["payload"],
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            await websocket_manager.send_to_user(
                user_id=str(test_user.id),
                message=message
            )
            
            await asyncio.sleep(0.05)  # Small delay between messages
        
        # Allow time for persistence
        await asyncio.sleep(0.3)
        
        # Verify agent completion message was persisted
        query = select(Message).where(
            Message.thread_id == test_thread.id,
            Message.role == "assistant",
            Message.content.contains("optimization opportunities")
        )
        result = await db.execute(query)
        agent_message = result.scalar_one_or_none()
        
        assert agent_message is not None
        assert agent_message.user_id == test_user.id  
        assert agent_message.thread_id == test_thread.id
        assert agent_message.role == "assistant"
        assert "optimization opportunities" in agent_message.content
        
        # Verify agent execution metadata
        assert agent_message.metadata is not None
        assert "agent_name" in agent_message.metadata
        assert agent_message.metadata["agent_name"] == "cost_optimizer"
        assert "websocket_events" in agent_message.metadata
        
        # Should track all websocket events sent
        websocket_events = agent_message.metadata["websocket_events"]
        expected_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        for event in expected_events:
            assert event in websocket_events
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_recovery_after_connection_loss(self, real_services_fixture, test_user, test_thread,
                                                         websocket_manager, websocket_utility):
        """Test recovery of messages from database after connection loss."""
        db: AsyncSession = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Pre-populate database with messages (simulating previous conversation)
        existing_messages = [
            Message(
                thread_id=test_thread.id,
                user_id=test_user.id,
                role="user",
                content="What are my current cloud costs?",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                metadata={"websocket_delivered": True, "message_order": 1}
            ),
            Message(
                thread_id=test_thread.id,
                user_id=test_user.id, 
                role="assistant",
                content="Your current cloud costs are $15,420/month. Here's the breakdown...",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=9),
                metadata={
                    "agent_name": "cost_analyzer",
                    "websocket_delivered": True,
                    "message_order": 2,
                    "websocket_events": ["agent_started", "agent_completed"]
                }
            ),
            Message(
                thread_id=test_thread.id,
                user_id=test_user.id,
                role="user", 
                content="Can you provide optimization recommendations?",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=5),
                metadata={"websocket_delivered": False, "message_order": 3}  # Not delivered due to disconnect
            )
        ]
        
        for msg in existing_messages:
            db.add(msg)
        await db.commit()
        
        # Create new WebSocket connection (simulating reconnection)
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="recovery_test_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket,
            metadata={"thread_id": str(test_thread.id)}
        )
        await websocket_manager.add_connection(connection)
        
        # Request message history recovery
        recovery_request = WebSocketMessage(
            message_type=MessageType.REQUEST_HISTORY,
            payload={
                "thread_id": str(test_thread.id),
                "last_received_message_id": None,  # Request full history
                "max_messages": 10
            },
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=recovery_request
        )
        
        # Allow time for recovery processing
        await asyncio.sleep(0.2)
        
        # Verify messages were recovered and sent via WebSocket
        sent_messages = mock_websocket.sent_messages
        assert len(sent_messages) >= 3  # Should include all messages + recovery confirmation
        
        # Find history messages in sent data
        history_messages = []
        for msg in sent_messages:
            if hasattr(msg, 'message_type') and msg.message_type == MessageType.HISTORY_MESSAGE:
                history_messages.append(msg)
            elif isinstance(msg, dict) and msg.get('type') == 'history_message':
                history_messages.append(msg)
        
        assert len(history_messages) >= 3
        
        # Verify message content and ordering
        message_contents = []
        for msg in history_messages:
            if hasattr(msg, 'payload') and 'content' in msg.payload:
                message_contents.append(msg.payload['content'])
            elif isinstance(msg, dict) and 'content' in msg.get('payload', {}):
                message_contents.append(msg['payload']['content'])
        
        assert "What are my current cloud costs?" in str(message_contents)
        assert "$15,420/month" in str(message_contents)
        assert "optimization recommendations" in str(message_contents)
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_message_persistence(self, real_services_fixture, test_user, test_thread,
                                                websocket_manager, websocket_utility):
        """Test persistence of concurrent messages from multiple connections."""
        db: AsyncSession = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create multiple WebSocket connections for same user (different devices)
        connections = []
        websockets = []
        
        for i in range(3):
            websocket = await websocket_utility.create_mock_websocket()
            connection = await websocket_manager.create_connection(
                connection_id=f"concurrent_conn_{i}",
                user_id=str(test_user.id),
                websocket=websocket,
                metadata={"device": f"device_{i}", "thread_id": str(test_thread.id)}
            )
            await websocket_manager.add_connection(connection)
            connections.append(connection)
            websockets.append(websocket)
        
        # Send concurrent messages from different connections
        concurrent_tasks = []
        for i, websocket in enumerate(websockets):
            message = WebSocketMessage(
                message_type=MessageType.USER_MESSAGE,
                payload={
                    "content": f"Message from device {i}: Please analyze costs for region {i+1}",
                    "device_info": f"device_{i}",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                user_id=str(test_user.id),
                thread_id=str(test_thread.id)
            )
            
            task = asyncio.create_task(
                websocket_manager.handle_message(
                    user_id=str(test_user.id),
                    websocket=websocket,
                    message=message
                )
            )
            concurrent_tasks.append(task)
        
        # Wait for all concurrent operations
        await asyncio.gather(*concurrent_tasks)
        await asyncio.sleep(0.3)  # Allow persistence time
        
        # Verify all messages were persisted correctly
        query = select(Message).where(
            Message.thread_id == test_thread.id,
            Message.role == "user",
            Message.content.contains("analyze costs for region")
        ).order_by(Message.created_at)
        
        result = await db.execute(query)
        persisted_messages = result.scalars().all()
        
        assert len(persisted_messages) == 3
        
        # Verify each message has correct content and metadata
        for i, msg in enumerate(persisted_messages):
            assert msg.user_id == test_user.id
            assert msg.thread_id == test_thread.id
            assert f"region {i+1}" in msg.content or f"Message from device" in msg.content
            assert msg.metadata is not None
            
            # Each message should have device info in metadata
            device_found = any(f"device_{j}" in str(msg.metadata) for j in range(3))
            assert device_found
        
        # Verify no message corruption from concurrent access
        for msg in persisted_messages:
            assert msg.content is not None
            assert len(msg.content) > 0
            assert msg.created_at is not None
        
        # Cleanup
        for connection in connections:
            await websocket_manager.remove_connection(connection.connection_id)
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_large_message_persistence_performance(self, real_services_fixture, test_user, test_thread,
                                                        websocket_manager, websocket_utility):
        """Test performance of persisting large messages to database."""
        db: AsyncSession = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        # Create WebSocket connection
        mock_websocket = await websocket_utility.create_mock_websocket()
        connection = await websocket_manager.create_connection(
            connection_id="large_persistence_conn",
            user_id=str(test_user.id),
            websocket=mock_websocket
        )
        await websocket_manager.add_connection(connection)
        
        # Create large message (simulating comprehensive agent result)
        large_payload = {
            "analysis_type": "comprehensive_cost_audit",
            "detailed_findings": {
                "cost_analysis": "Detailed cost breakdown analysis. " * 500,  # Large text
                "resource_inventory": [
                    {"resource_id": f"resource_{i}", "cost": i * 1.5, "utilization": f"{i%100}%"}
                    for i in range(1000)  # Large array
                ],
                "optimization_recommendations": [
                    {
                        "recommendation_id": f"rec_{i}",
                        "title": f"Optimization {i}",
                        "description": f"Detailed recommendation description {i}. " * 20,
                        "potential_savings": i * 100,
                        "implementation_steps": [f"Step {j}" for j in range(5)]
                    }
                    for i in range(50)  # Complex nested data
                ]
            },
            "metadata": {
                "processing_time": 45.7,
                "data_points_analyzed": 10000,
                "confidence_metrics": {"overall": 0.95, "cost_accuracy": 0.98}
            }
        }
        
        large_message = WebSocketMessage(
            message_type=MessageType.AGENT_COMPLETED,
            payload=large_payload,
            user_id=str(test_user.id),
            thread_id=str(test_thread.id)
        )
        
        # Measure persistence performance
        start_time = datetime.now()
        
        await websocket_manager.handle_message(
            user_id=str(test_user.id),
            websocket=mock_websocket,
            message=large_message
        )
        
        # Wait for persistence with timeout
        await asyncio.sleep(1.0)
        
        persistence_time = datetime.now() - start_time
        
        # Verify large message was persisted
        query = select(Message).where(
            Message.thread_id == test_thread.id,
            Message.role == "assistant",
            Message.content.contains("comprehensive_cost_audit")
        )
        result = await db.execute(query)
        persisted_message = result.scalar_one_or_none()
        
        assert persisted_message is not None
        
        # Verify data integrity of large message
        assert "comprehensive_cost_audit" in persisted_message.content
        
        # Parse JSON content to verify structure preservation
        try:
            parsed_content = json.loads(persisted_message.content)
            assert "analysis_type" in parsed_content
            assert "detailed_findings" in parsed_content
            assert len(parsed_content["detailed_findings"]["resource_inventory"]) == 1000
            assert len(parsed_content["detailed_findings"]["optimization_recommendations"]) == 50
        except json.JSONDecodeError:
            pytest.fail("Large message content was not properly serialized as JSON")
        
        # Verify performance is reasonable (should persist large message within 2 seconds)
        assert persistence_time.total_seconds() < 2.0, f"Large message persistence took {persistence_time.total_seconds()}s (too slow)"
        
        # Cleanup
        await websocket_manager.remove_connection(connection.connection_id)