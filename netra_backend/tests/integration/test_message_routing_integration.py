"""
Test Message Routing and Processing Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable message processing and routing for real-time chat functionality
- Value Impact: Message routing failures break the core user experience of AI-powered chat
- Strategic Impact: Message processing is the foundation of platform value delivery

This test suite validates message routing and processing integration:
1. Message pipeline processing from WebSocket to agent execution
2. Quality message routing and filtering
3. Message persistence and retrieval with proper user isolation
"""

import asyncio
import uuid
import pytest
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.fixtures.isolated_environment import isolated_env
from shared.isolated_environment import get_env
from shared.types.core_types import (
    UserID, ThreadID, RunID, RequestID, WebSocketID,
    WebSocketEventType, WebSocketMessage, ensure_user_id, ensure_thread_id
)

# Message routing components
from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
from netra_backend.app.services.websocket.quality_metrics_handler import QualityMetricsHandler
from netra_backend.app.services.websocket.quality_validation_handler import QualityValidationHandler
from netra_backend.app.services.message_service import MessageService, MessageProcessor
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Models for message testing
from netra_backend.app.models.user import User
from netra_backend.app.models.thread import Thread, Message


class TestMessageRoutingIntegration(BaseIntegrationTest):
    """Test message routing and processing with real service integration."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_pipeline_websocket_to_agent_execution(self, real_services_fixture, isolated_env):
        """Test complete message pipeline from WebSocket receipt to agent execution."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        redis = real_services_fixture.get("redis") or self._create_test_redis_connection()
        
        # Setup test user and thread
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        websocket_id = WebSocketID(str(uuid.uuid4()))
        
        test_user = User(id=str(user_id), email="pipeline@test.com", name="Pipeline Test User")
        test_thread = Thread(id=str(thread_id), user_id=str(user_id), title="Pipeline Test Thread")
        
        db.add_all([test_user, test_thread])
        await db.commit()
        
        # Initialize message processing components
        message_service = MessageService(database_session=db, redis_connection=redis)
        message_processor = MessageProcessor(message_service)
        websocket_manager = UnifiedWebSocketManager()
        
        # Create incoming WebSocket message
        incoming_message = {
            "type": "user_message",
            "user_id": str(user_id),
            "thread_id": str(thread_id),
            "websocket_id": str(websocket_id),
            "content": "Please analyze my data and provide optimization recommendations",
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": str(uuid.uuid4())
        }
        
        # Track message processing stages
        processing_stages = []
        
        # Mock agent execution to track pipeline progression
        async def mock_agent_execution(message_data):
            processing_stages.append("agent_execution_started")
            
            # Simulate agent processing
            await asyncio.sleep(0.1)
            
            agent_response = {
                "type": "agent_response",
                "content": "Based on your data analysis request, I've identified several optimization opportunities...",
                "agent_type": "data_optimizer",
                "processing_time_ms": 150,
                "confidence_score": 0.92
            }
            
            processing_stages.append("agent_execution_completed")
            return agent_response
        
        # Process message through pipeline
        with patch('netra_backend.app.agents.supervisor_consolidated.SupervisorAgent.execute_agent_request',
                  side_effect=mock_agent_execution):
            
            # Stage 1: Message receipt and validation
            processing_stages.append("message_received")
            validated_message = await message_processor.validate_message(incoming_message)
            processing_stages.append("message_validated")
            
            # Stage 2: Message persistence  
            persisted_message = await message_service.store_message(
                thread_id=thread_id,
                user_id=user_id,
                content=validated_message["content"],
                message_type="user",
                metadata={"websocket_id": str(websocket_id)}
            )
            processing_stages.append("message_persisted")
            
            # Stage 3: Message routing to agent
            processing_stages.append("routing_to_agent")
            agent_response = await message_processor.route_to_agent(validated_message)
            processing_stages.append("agent_response_received")
            
            # Stage 4: Response processing and WebSocket notification
            response_message = await message_service.store_message(
                thread_id=thread_id,
                user_id=user_id,
                content=agent_response["content"],
                message_type="agent",
                metadata={
                    "agent_type": agent_response["agent_type"],
                    "processing_time_ms": agent_response["processing_time_ms"],
                    "confidence_score": agent_response["confidence_score"]
                }
            )
            processing_stages.append("response_persisted")
            
            # Stage 5: WebSocket notification to user
            websocket_response = WebSocketMessage(
                event_type=WebSocketEventType.AGENT_COMPLETED,
                user_id=user_id,
                thread_id=thread_id,
                request_id=RequestID(validated_message["request_id"]),
                data=agent_response
            )
            
            # Mock WebSocket send
            await websocket_manager.broadcast_to_user(user_id, websocket_response.dict())
            processing_stages.append("websocket_notification_sent")
        
        # Verify complete pipeline execution
        expected_stages = [
            "message_received",
            "message_validated", 
            "message_persisted",
            "routing_to_agent",
            "agent_execution_started",
            "agent_execution_completed",
            "agent_response_received",
            "response_persisted",
            "websocket_notification_sent"
        ]
        
        for expected_stage in expected_stages:
            assert expected_stage in processing_stages, f"Missing pipeline stage: {expected_stage}"
        
        # Verify message persistence
        assert persisted_message.id is not None
        assert persisted_message.thread_id == str(thread_id)
        assert persisted_message.user_id == str(user_id)
        assert persisted_message.content == "Please analyze my data and provide optimization recommendations"
        
        # Verify response persistence
        assert response_message.id is not None
        assert response_message.message_type == "agent"
        assert "optimization opportunities" in response_message.content
        
        await db.close()

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_quality_message_routing_and_filtering(self, real_services_fixture, isolated_env):
        """Test quality message routing with filtering and validation."""
        
        redis = real_services_fixture.get("redis") or self._create_test_redis_connection()
        
        # Initialize quality routing components
        quality_router = QualityMessageRouter()
        quality_metrics_handler = QualityMetricsHandler(redis_connection=redis)
        quality_validator = QualityValidationHandler()
        websocket_manager = UnifiedWebSocketManager()
        
        user_id = ensure_user_id(str(uuid.uuid4()))
        thread_id = ensure_thread_id(str(uuid.uuid4()))
        
        # Create different types of quality messages
        quality_messages = [
            {
                "type": "quality_alert",
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "severity": "high",
                "metric": "response_accuracy",
                "current_value": 0.65,
                "threshold": 0.80,
                "message": "Response accuracy below threshold",
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "type": "quality_report", 
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "overall_score": 0.87,
                "metrics": {
                    "accuracy": 0.92,
                    "relevance": 0.85,
                    "completeness": 0.84,
                    "response_time": 2.3
                },
                "recommendations": [
                    "Consider providing more specific examples",
                    "Response time is within acceptable range"
                ],
                "timestamp": datetime.utcnow().isoformat()
            },
            {
                "type": "quality_validation",
                "user_id": str(user_id),
                "thread_id": str(thread_id),
                "validation_result": "passed",
                "checks": {
                    "content_safety": True,
                    "factual_accuracy": True,
                    "relevance_check": True,
                    "completeness_check": False
                },
                "flagged_issues": ["incomplete_analysis"],
                "timestamp": datetime.utcnow().isoformat()
            }
        ]
        
        # Process each message type through quality routing
        routing_results = []
        
        for quality_message in quality_messages:
            # Validate message format
            validation_result = await quality_validator.validate_quality_message(quality_message)
            assert validation_result.is_valid, f"Quality message validation failed: {validation_result.error}"
            
            # Route message based on type
            routing_result = await quality_router.route_quality_message(quality_message, websocket_manager)
            routing_results.append(routing_result)
            
            # Update quality metrics
            await quality_metrics_handler.update_metrics(quality_message)
        
        # Verify routing results
        assert len(routing_results) == 3
        
        # Check quality alert routing
        alert_result = routing_results[0]
        assert alert_result["routed_to"] == "alert_handler"
        assert alert_result["priority"] == "high"
        assert alert_result["notification_sent"] is True
        
        # Check quality report routing
        report_result = routing_results[1]
        assert report_result["routed_to"] == "report_processor"
        assert report_result["metrics_updated"] is True
        assert report_result["overall_score"] == 0.87
        
        # Check quality validation routing
        validation_routing_result = routing_results[2]
        assert validation_routing_result["routed_to"] == "validation_processor"
        assert validation_routing_result["validation_status"] == "passed"
        assert "incomplete_analysis" in validation_routing_result["flagged_issues"]
        
        # Verify metrics were updated correctly
        user_quality_metrics = await quality_metrics_handler.get_user_quality_metrics(user_id)
        assert user_quality_metrics["recent_score"] == 0.87
        assert user_quality_metrics["alert_count"] == 1
        assert user_quality_metrics["validation_pass_rate"] > 0

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_message_persistence_with_user_isolation(self, real_services_fixture, isolated_env):
        """Test message persistence maintains proper user isolation."""
        
        db = real_services_fixture.get("db") or self._create_test_db_session()
        
        # Create multiple users and threads
        users_and_threads = []
        for i in range(3):
            user_id = ensure_user_id(str(uuid.uuid4()))
            thread_id = ensure_thread_id(str(uuid.uuid4()))
            
            user = User(id=str(user_id), email=f"message.user.{i}@test.com", name=f"Message User {i}")
            thread = Thread(id=str(thread_id), user_id=str(user_id), title=f"Message Thread {i}")
            
            users_and_threads.append((user, thread, user_id, thread_id))
        
        # Add all users and threads to database
        all_users = [u for u, t, uid, tid in users_and_threads]
        all_threads = [t for u, t, uid, tid in users_and_threads]
        db.add_all(all_users + all_threads)
        await db.commit()
        
        # Create message service instances for each user
        message_services = {}
        for user, thread, user_id, thread_id in users_and_threads:
            message_service = MessageService(
                database_session=db,
                user_isolation=True,
                current_user_id=user_id
            )
            message_services[user_id] = message_service
        
        # Create messages for each user
        user_messages = {}
        for user, thread, user_id, thread_id in users_and_threads:
            message_service = message_services[user_id]
            
            # Create multiple messages per user
            messages = []
            for msg_idx in range(3):
                message = await message_service.store_message(
                    thread_id=thread_id,
                    user_id=user_id,
                    content=f"Test message {msg_idx} from user {user_id}",
                    message_type="user",
                    metadata={"test_source": "isolation_test"}
                )
                messages.append(message)
            
            user_messages[user_id] = messages
        
        # Test isolation - each service should only access its user's messages
        for user, thread, user_id, thread_id in users_and_threads:
            message_service = message_services[user_id]
            
            # Get messages through user-isolated service
            thread_messages = await message_service.get_thread_messages(thread_id)
            
            # Should only see own messages
            assert len(thread_messages) == 3, f"User {user_id} should see exactly 3 messages"
            
            for message in thread_messages:
                assert message.user_id == str(user_id), f"User {user_id} can see other user's message: {message.user_id}"
                assert message.thread_id == str(thread_id), f"Message from wrong thread: {message.thread_id}"
                assert f"user {user_id}" in message.content, "Message content doesn't match expected user"
        
        # Test cross-user access prevention
        user1_id = users_and_threads[0][2]  # First user ID
        user2_thread_id = users_and_threads[1][3]  # Second user's thread ID
        
        user1_service = message_services[user1_id]
        
        # User 1 service should not be able to access User 2's thread messages
        user2_messages_via_user1 = await user1_service.get_thread_messages(user2_thread_id)
        assert len(user2_messages_via_user1) == 0, "Cross-user message access was allowed - isolation failure!"
        
        # Verify direct database access without isolation would show all messages
        all_messages_query = await db.execute(
            db.select(Message).where(Message.metadata.contains({"test_source": "isolation_test"}))
        )
        all_messages = all_messages_query.scalars().all()
        assert len(all_messages) == 9, "Expected 9 total messages across all users"  # 3 users × 3 messages each
        
        await db.close()

    def _create_test_db_session(self):
        """Create test database session."""
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_session.add_all = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.get = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.select = MagicMock()
        mock_session.close = AsyncMock()
        return mock_session
    
    def _create_test_redis_connection(self):
        """Create test Redis connection."""
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.get = AsyncMock() 
        mock_redis.hset = AsyncMock()
        mock_redis.hget = AsyncMock()
        mock_redis.hgetall = AsyncMock(return_value={})
        return mock_redis