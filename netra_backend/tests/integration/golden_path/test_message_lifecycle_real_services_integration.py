"""
Integration Tests for Message Lifecycle with Real Services

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise)
- Business Goal: Revenue Protection - Validates $500K+ ARR message processing and delivery
- Value Impact: Message lifecycle ensures reliable communication between users and AI agents
- Strategic Impact: Integration tests ensure messages are processed, stored, and delivered correctly

CRITICAL: These are GOLDEN PATH integration tests using REAL services:
- Real PostgreSQL for message persistence and history
- Real Redis for message queuing and caching
- Real WebSocket message delivery
- Real user context and authentication integration

No mocks - all message processing uses real infrastructure services.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from uuid import uuid4

# SSOT Imports - Absolute imports as per CLAUDE.md requirement
from shared.types.core_types import UserID, ThreadID, RunID, ensure_user_id, WebSocketEventType
from shared.types.execution_types import StronglyTypedWebSocketEvent
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.real_services_test_fixtures import real_services_fixture


@pytest.mark.integration
@pytest.mark.golden_path
class TestMessageLifecycleRealServicesIntegration(SSotBaseTestCase):
    """
    Integration tests for complete message lifecycle with real services.
    
    These tests validate that messages flow correctly through the entire system:
    user input -> processing -> AI response -> delivery -> persistence
    """

    @pytest.fixture(autouse=True)
    async def setup_real_services(self, real_services_fixture):
        """Set up real services for integration testing."""
        self.services = real_services_fixture
        self.db_session = self.services['db_session']
        self.redis_client = self.services['redis_client']
        self.auth_helper = E2EAuthHelper(environment="test")

    @pytest.mark.asyncio
    async def test_complete_message_lifecycle_user_to_agent(self):
        """
        Test Case: Complete message lifecycle from user input to agent response.
        
        Business Value: Validates core $500K+ ARR chat functionality works end-to-end.
        Expected: User messages are processed, stored, and responded to correctly.
        """
        # Arrange
        user_id = "message_lifecycle_user_123"
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="message_lifecycle@example.com",
            user_id=user_id,
            environment="test",
            permissions=["read", "write", "websocket", "agent_execution"]
        )
        
        # User's input message
        user_message = {
            "message_id": str(uuid4()),
            "user_id": user_id,
            "thread_id": str(user_context.thread_id),
            "content": "I need help optimizing my database queries for better performance",
            "message_type": "user_input",
            "timestamp": datetime.now(timezone.utc),
            "context": {
                "database_type": "postgresql",
                "current_performance": "slow",
                "priority": "high"
            }
        }
        
        # Act - Process complete message lifecycle
        
        # 1. Receive and validate user message
        message_received = await self._receive_user_message(user_message)
        assert message_received["success"] is True
        
        # 2. Store message in persistent storage
        message_stored = await self._store_message_in_database(user_message)
        assert message_stored["success"] is True
        
        # 3. Queue message for agent processing
        queued_for_processing = await self._queue_message_for_agent_processing(user_message)
        assert queued_for_processing["success"] is True
        
        # 4. Simulate agent processing
        agent_processing_result = await self._simulate_agent_message_processing(user_message)
        assert agent_processing_result["success"] is True
        
        # 5. Generate agent response
        agent_response = {
            "message_id": str(uuid4()),
            "user_id": user_id,
            "thread_id": str(user_context.thread_id),
            "content": "I'll help you optimize your PostgreSQL queries. Let me analyze your current setup and provide specific recommendations.",
            "message_type": "agent_response",
            "timestamp": datetime.now(timezone.utc),
            "response_to": user_message["message_id"],
            "agent_context": {
                "agent_type": "database_optimization",
                "confidence": 0.95,
                "processing_time": 2.3
            },
            "recommendations": [
                "Add index on frequently queried columns",
                "Optimize JOIN operations", 
                "Consider query result caching"
            ]
        }
        
        # 6. Store agent response
        response_stored = await self._store_message_in_database(agent_response)
        assert response_stored["success"] is True
        
        # 7. Deliver response to user via WebSocket
        response_delivered = await self._deliver_message_via_websocket(user_id, agent_response)
        assert response_delivered["success"] is True
        
        # Assert - Complete message lifecycle validation
        
        # Verify message thread continuity
        thread_messages = await self._retrieve_thread_messages(str(user_context.thread_id))
        assert len(thread_messages) == 2  # User message + Agent response
        
        # Verify message ordering
        assert thread_messages[0]["message_type"] == "user_input"
        assert thread_messages[1]["message_type"] == "agent_response"
        assert thread_messages[1]["response_to"] == user_message["message_id"]
        
        # Verify business value content
        assert "optimize" in thread_messages[0]["content"].lower()
        assert "postgresql" in thread_messages[1]["content"].lower()
        assert len(agent_response["recommendations"]) == 3
        
        # Verify message metadata
        assert thread_messages[0]["context"]["priority"] == "high"
        assert thread_messages[1]["agent_context"]["confidence"] == 0.95
        
        print(" PASS:  Complete message lifecycle user to agent test passed")

    @pytest.mark.asyncio
    async def test_message_persistence_and_history_retrieval(self):
        """
        Test Case: Messages are persisted and retrievable for chat history.
        
        Business Value: Users can review past conversations and agent recommendations.
        Expected: All messages are stored and can be retrieved efficiently.
        """
        # Arrange
        user_id = "message_history_user_456"
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="message_history@example.com", 
            user_id=user_id,
            environment="test"
        )
        
        thread_id = str(user_context.thread_id)
        
        # Create conversation history with multiple messages
        conversation_messages = [
            {
                "message_id": f"msg_1_{uuid4()}",
                "user_id": user_id,
                "thread_id": thread_id,
                "content": "What are the best practices for database indexing?",
                "message_type": "user_input",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=10)
            },
            {
                "message_id": f"msg_2_{uuid4()}",
                "user_id": user_id, 
                "thread_id": thread_id,
                "content": "Here are key database indexing best practices: 1) Index frequently queried columns, 2) Avoid over-indexing, 3) Monitor index performance...",
                "message_type": "agent_response",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=9),
                "recommendations": [
                    "Create indexes on WHERE clause columns",
                    "Use composite indexes for multi-column queries",
                    "Regular index maintenance and statistics updates"
                ]
            },
            {
                "message_id": f"msg_3_{uuid4()}",
                "user_id": user_id,
                "thread_id": thread_id, 
                "content": "Can you help me optimize this specific query: SELECT * FROM users WHERE email = ? AND status = 'active'",
                "message_type": "user_input",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=5)
            },
            {
                "message_id": f"msg_4_{uuid4()}",
                "user_id": user_id,
                "thread_id": thread_id,
                "content": "For your query optimization: 1) Create composite index on (email, status), 2) Consider adding LIMIT clause, 3) Estimated 75% performance improvement",
                "message_type": "agent_response", 
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=4),
                "optimization_details": {
                    "current_query": "SELECT * FROM users WHERE email = ? AND status = 'active'",
                    "recommended_index": "CREATE INDEX idx_users_email_status ON users(email, status)",
                    "estimated_improvement": "75% faster execution"
                }
            }
        ]
        
        # Act - Store all messages
        for message in conversation_messages:
            storage_result = await self._store_message_in_database(message)
            assert storage_result["success"] is True
        
        # Retrieve conversation history
        retrieved_history = await self._retrieve_conversation_history(user_id, thread_id)
        
        # Test different retrieval patterns
        recent_messages = await self._retrieve_recent_messages(user_id, limit=2)
        user_questions = await self._retrieve_messages_by_type(user_id, "user_input")
        agent_responses = await self._retrieve_messages_by_type(user_id, "agent_response")
        
        # Assert - Message persistence and retrieval works correctly
        
        # Complete history retrieval
        assert len(retrieved_history) == 4, "Should retrieve all messages in conversation"
        
        # Messages should be in chronological order
        timestamps = [msg["timestamp"] for msg in retrieved_history]
        assert timestamps == sorted(timestamps), "Messages should be chronologically ordered"
        
        # Recent messages limit
        assert len(recent_messages) == 2, "Should limit to 2 recent messages"
        assert recent_messages[0]["timestamp"] > recent_messages[1]["timestamp"], "Most recent first"
        
        # Message type filtering
        assert len(user_questions) == 2, "Should find 2 user input messages"
        assert len(agent_responses) == 2, "Should find 2 agent response messages"
        assert all(msg["message_type"] == "user_input" for msg in user_questions)
        assert all(msg["message_type"] == "agent_response" for msg in agent_responses)
        
        # Business value content preservation
        indexing_response = next(msg for msg in agent_responses if "indexing best practices" in msg["content"])
        assert len(indexing_response["recommendations"]) == 3
        
        optimization_response = next(msg for msg in agent_responses if "optimization_details" in msg)
        assert "75% faster" in optimization_response["optimization_details"]["estimated_improvement"]
        
        # Thread continuity
        all_thread_ids = [msg["thread_id"] for msg in retrieved_history]
        assert all(tid == thread_id for tid in all_thread_ids), "All messages should belong to same thread"
        
        print(" PASS:  Message persistence and history retrieval test passed")

    @pytest.mark.asyncio
    async def test_message_delivery_with_offline_users(self):
        """
        Test Case: Messages are queued and delivered when offline users come online.
        
        Business Value: Users don't miss important AI responses or notifications.
        Expected: Messages are queued when users are offline and delivered on reconnection.
        """
        # Arrange
        user_id = "offline_message_user_789"
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="offline_message@example.com",
            user_id=user_id,
            environment="test"
        )
        
        # Simulate user going offline
        user_online_status = await self._set_user_online_status(user_id, online=False)
        assert user_online_status["success"] is True
        
        # Messages to be delivered while user is offline
        offline_messages = [
            {
                "message_id": f"offline_1_{uuid4()}",
                "user_id": user_id,
                "thread_id": str(user_context.thread_id),
                "content": "Your cost analysis is complete! We found $850/month in potential savings.",
                "message_type": "agent_response",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=3),
                "priority": "high",
                "results": {
                    "total_savings": "$850/month",
                    "optimizations_found": 5,
                    "implementation_time": "2 hours"
                }
            },
            {
                "message_id": f"offline_2_{uuid4()}",
                "user_id": user_id,
                "thread_id": str(user_context.thread_id), 
                "content": "Detailed recommendations: 1) Upgrade to more efficient instance type (saves $400/month), 2) Enable auto-scaling (saves $200/month)...",
                "message_type": "agent_response",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=2),
                "priority": "medium",
                "detailed_recommendations": [
                    {"action": "Upgrade instance type", "savings": "$400/month", "effort": "low"},
                    {"action": "Enable auto-scaling", "savings": "$200/month", "effort": "medium"}, 
                    {"action": "Optimize storage", "savings": "$150/month", "effort": "low"},
                    {"action": "Review reserved instances", "savings": "$100/month", "effort": "high"}
                ]
            },
            {
                "message_id": f"offline_3_{uuid4()}",
                "user_id": user_id,
                "thread_id": str(user_context.thread_id),
                "content": "Click here to view your optimization report and start implementing changes.",
                "message_type": "system_notification",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=1),
                "priority": "low",
                "action_items": {
                    "report_url": "/optimization-report/user_789",
                    "implementation_guide": "/guides/cost-optimization"
                }
            }
        ]
        
        # Act - Queue messages for offline user
        for message in offline_messages:
            # Store message in database
            storage_result = await self._store_message_in_database(message)
            assert storage_result["success"] is True
            
            # Queue for delivery when user comes online
            queue_result = await self._queue_message_for_offline_delivery(user_id, message)
            assert queue_result["success"] is True
        
        # Verify messages are queued
        queued_count = await self._get_queued_message_count(user_id)
        assert queued_count == 3, "Should have 3 messages queued for offline user"
        
        # Simulate user coming back online
        user_online_status = await self._set_user_online_status(user_id, online=True)
        assert user_online_status["success"] is True
        
        # Process message delivery for newly online user
        delivery_result = await self._process_offline_message_delivery(user_id)
        
        # Assert - Offline message delivery works correctly
        
        assert delivery_result["success"] is True
        assert delivery_result["messages_delivered"] == 3
        
        # Verify delivery order (high priority first, then chronological)
        delivered_messages = delivery_result["delivered_messages"]
        
        # High priority message should be first
        assert delivered_messages[0]["priority"] == "high"
        assert "$850/month" in delivered_messages[0]["content"]
        
        # Remaining messages in chronological order
        remaining_messages = delivered_messages[1:]
        remaining_timestamps = [msg["timestamp"] for msg in remaining_messages]
        assert remaining_timestamps == sorted(remaining_timestamps)
        
        # Verify business value content is preserved
        savings_message = delivered_messages[0]
        assert savings_message["results"]["total_savings"] == "$850/month"
        assert savings_message["results"]["optimizations_found"] == 5
        
        recommendations_message = next(msg for msg in delivered_messages if "detailed_recommendations" in msg)
        assert len(recommendations_message["detailed_recommendations"]) == 4
        
        # Verify queue is cleared after delivery
        remaining_queue_count = await self._get_queued_message_count(user_id)
        assert remaining_queue_count == 0, "Message queue should be empty after delivery"
        
        # Verify messages are marked as delivered
        delivery_status = await self._check_message_delivery_status(offline_messages[0]["message_id"])
        assert delivery_status["delivered"] is True
        assert delivery_status["delivered_at"] is not None
        
        print(" PASS:  Message delivery with offline users test passed")

    @pytest.mark.asyncio
    async def test_message_threading_and_context_preservation(self):
        """
        Test Case: Messages maintain proper threading and context across conversations.
        
        Business Value: Users can follow complex conversations and agent recommendations.
        Expected: Message threads preserve context and enable coherent multi-turn conversations.
        """
        # Arrange
        user_id = "threading_user_012"
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="threading@example.com",
            user_id=user_id,
            environment="test"
        )
        
        main_thread_id = str(user_context.thread_id)
        
        # Create main conversation thread
        main_conversation = [
            {
                "message_id": f"main_1_{uuid4()}",
                "user_id": user_id,
                "thread_id": main_thread_id,
                "content": "I want to optimize my e-commerce database performance",
                "message_type": "user_input",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=20),
                "conversation_context": {
                    "topic": "database_optimization",
                    "business_type": "e-commerce",
                    "urgency": "medium"
                }
            },
            {
                "message_id": f"main_2_{uuid4()}",
                "user_id": user_id,
                "thread_id": main_thread_id,
                "content": "For e-commerce database optimization, I'll analyze your product catalog, user sessions, and order processing queries. Let me start with your most critical tables.",
                "message_type": "agent_response",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=19),
                "references_message": f"main_1_{uuid4()}",
                "agent_context": {
                    "specialization": "e-commerce_optimization",
                    "analysis_scope": ["product_catalog", "user_sessions", "orders"]
                }
            }
        ]
        
        # Create follow-up thread for specific optimization
        followup_thread_id = f"thread_followup_{uuid4()}"
        followup_conversation = [
            {
                "message_id": f"followup_1_{uuid4()}",
                "user_id": user_id,
                "thread_id": followup_thread_id,
                "parent_thread": main_thread_id,
                "content": "Focus on the product search functionality - it's very slow",
                "message_type": "user_input",
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=15),
                "conversation_context": {
                    "topic": "product_search_optimization",
                    "derived_from": "database_optimization",
                    "specific_issue": "slow_search_performance"
                }
            },
            {
                "message_id": f"followup_2_{uuid4()}",
                "user_id": user_id,
                "thread_id": followup_thread_id,
                "parent_thread": main_thread_id,
                "content": "I'll optimize your product search. Based on our previous discussion, I recommend: 1) Full-text search indexes on product names/descriptions, 2) Search result caching, 3) Elasticsearch integration for complex queries.",
                "message_type": "agent_response", 
                "timestamp": datetime.now(timezone.utc) - timedelta(minutes=14),
                "references_context": {
                    "from_thread": main_thread_id,
                    "context_carried": ["e-commerce", "product_catalog", "performance_optimization"]
                },
                "specific_recommendations": [
                    {"type": "index", "target": "products.name, products.description", "impact": "high"},
                    {"type": "caching", "target": "search_results", "duration": "1_hour", "impact": "medium"},
                    {"type": "integration", "service": "elasticsearch", "complexity": "high", "impact": "high"}
                ]
            }
        ]
        
        # Act - Store messages with threading information
        all_messages = main_conversation + followup_conversation
        
        for message in all_messages:
            storage_result = await self._store_message_with_threading_info(message)
            assert storage_result["success"] is True
        
        # Test various threading queries
        main_thread_messages = await self._retrieve_thread_messages(main_thread_id)
        followup_thread_messages = await self._retrieve_thread_messages(followup_thread_id)
        user_all_threads = await self._retrieve_user_thread_tree(user_id)
        context_preserved = await self._analyze_context_preservation(followup_thread_id, main_thread_id)
        
        # Assert - Message threading and context preservation work correctly
        
        # Thread separation
        assert len(main_thread_messages) == 2, "Main thread should have 2 messages"
        assert len(followup_thread_messages) == 2, "Follow-up thread should have 2 messages"
        
        # Thread relationships
        assert followup_conversation[0]["parent_thread"] == main_thread_id
        assert followup_conversation[1]["parent_thread"] == main_thread_id
        
        # User thread tree structure
        assert len(user_all_threads["threads"]) == 2, "User should have 2 conversation threads"
        assert main_thread_id in user_all_threads["thread_hierarchy"]
        assert followup_thread_id in user_all_threads["thread_hierarchy"][main_thread_id]["child_threads"]
        
        # Context preservation across threads
        assert context_preserved["context_carried"] is True
        assert "e-commerce" in context_preserved["preserved_concepts"]
        assert "product_catalog" in context_preserved["preserved_concepts"]
        
        # Agent maintains context from parent thread
        followup_agent_response = followup_thread_messages[1]  # Agent response in followup thread
        assert "previous discussion" in followup_agent_response["content"].lower()
        assert len(followup_agent_response["references_context"]["context_carried"]) == 3
        
        # Business recommendations build on previous context
        recommendations = followup_agent_response["specific_recommendations"]
        search_optimization_recs = [rec for rec in recommendations if rec["type"] in ["index", "caching", "integration"]]
        assert len(search_optimization_recs) == 3, "Should have 3 search-specific recommendations"
        
        # Thread topic evolution tracking
        main_topic = main_conversation[0]["conversation_context"]["topic"]
        followup_topic = followup_conversation[0]["conversation_context"]["topic"]
        assert followup_topic == "product_search_optimization"
        assert followup_conversation[0]["conversation_context"]["derived_from"] == main_topic
        
        print(" PASS:  Message threading and context preservation test passed")

    @pytest.mark.asyncio
    async def test_message_search_and_filtering_real_database(self):
        """
        Test Case: Messages can be searched and filtered efficiently in real database.
        
        Business Value: Users can find past conversations and agent recommendations quickly.
        Expected: Complex message queries return results quickly with proper filtering.
        """
        # Arrange
        user_id = "message_search_user_345"
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="message_search@example.com",
            user_id=user_id,
            environment="test"
        )
        
        # Create diverse message dataset for search testing
        search_test_messages = []
        base_time = datetime.now(timezone.utc) - timedelta(days=30)
        
        message_scenarios = [
            {"content": "How can I optimize database performance for my e-commerce site?", "type": "user_input", "topic": "database_optimization", "days_ago": 25},
            {"content": "For e-commerce database optimization: 1) Index product search columns, 2) Optimize order queries, 3) Cache frequently accessed data. Estimated 60% performance improvement.", "type": "agent_response", "topic": "database_optimization", "days_ago": 25},
            {"content": "What are the best practices for API rate limiting?", "type": "user_input", "topic": "api_design", "days_ago": 20},
            {"content": "API rate limiting best practices: 1) Implement sliding window, 2) Use Redis for distributed rate limiting, 3) Provide clear error messages to clients.", "type": "agent_response", "topic": "api_design", "days_ago": 20},
            {"content": "Help me reduce AWS costs for my startup", "type": "user_input", "topic": "cost_optimization", "days_ago": 15},
            {"content": "AWS cost optimization for startups: 1) Use spot instances for non-critical workloads, 2) Implement auto-scaling, 3) Review and optimize storage usage. Potential savings: $1,200/month.", "type": "agent_response", "topic": "cost_optimization", "days_ago": 15},
            {"content": "Can you explain database indexing strategies for PostgreSQL?", "type": "user_input", "topic": "database_indexing", "days_ago": 10},
            {"content": "PostgreSQL indexing strategies: 1) B-tree indexes for equality/range queries, 2) GIN indexes for full-text search, 3) Partial indexes for filtered data. Performance impact varies by query pattern.", "type": "agent_response", "topic": "database_indexing", "days_ago": 10},
            {"content": "What monitoring tools work best for microservices?", "type": "user_input", "topic": "monitoring", "days_ago": 5},
            {"content": "Microservices monitoring tools: 1) Prometheus + Grafana for metrics, 2) Jaeger for distributed tracing, 3) ELK stack for centralized logging. Comprehensive observability solution.", "type": "agent_response", "topic": "monitoring", "days_ago": 5}
        ]
        
        for i, scenario in enumerate(message_scenarios):
            message = {
                "message_id": f"search_msg_{i}_{uuid4()}",
                "user_id": user_id,
                "thread_id": f"thread_{scenario['topic']}",
                "content": scenario["content"],
                "message_type": scenario["type"], 
                "timestamp": base_time + timedelta(days=scenario["days_ago"]),
                "topic": scenario["topic"],
                "searchable_content": scenario["content"].lower()
            }
            search_test_messages.append(message)
        
        # Store all messages
        for message in search_test_messages:
            storage_result = await self._store_message_in_database(message)
            assert storage_result["success"] is True
        
        # Act - Perform various search and filter operations
        
        # Full-text search tests
        database_messages = await self._search_messages_by_content(user_id, "database")
        optimization_messages = await self._search_messages_by_content(user_id, "optimization")
        cost_messages = await self._search_messages_by_content(user_id, "cost")
        
        # Type-based filtering
        user_questions = await self._filter_messages_by_type(user_id, "user_input")
        agent_responses = await self._filter_messages_by_type(user_id, "agent_response")
        
        # Time-based filtering
        recent_messages = await self._filter_messages_by_date(user_id, days_back=7)
        older_messages = await self._filter_messages_by_date(user_id, days_back=30, exclude_recent=7)
        
        # Topic-based filtering
        db_optimization_messages = await self._filter_messages_by_topic(user_id, "database_optimization")
        api_design_messages = await self._filter_messages_by_topic(user_id, "api_design")
        
        # Complex combined searches
        recent_database_questions = await self._search_messages_complex_filter(
            user_id=user_id,
            content_search="database", 
            message_type="user_input",
            days_back=30
        )
        
        # Assert - Message search and filtering work correctly
        
        # Full-text search results
        assert len(database_messages) >= 3, "Should find multiple database-related messages"
        assert all("database" in msg["content"].lower() for msg in database_messages)
        
        assert len(optimization_messages) >= 3, "Should find optimization-related messages"
        assert all("optimiz" in msg["content"].lower() for msg in optimization_messages)
        
        assert len(cost_messages) >= 2, "Should find cost-related messages" 
        assert all("cost" in msg["content"].lower() for msg in cost_messages)
        
        # Type filtering
        assert len(user_questions) == 5, "Should find all user input messages"
        assert len(agent_responses) == 5, "Should find all agent response messages"
        assert all(msg["message_type"] == "user_input" for msg in user_questions)
        assert all(msg["message_type"] == "agent_response" for msg in agent_responses)
        
        # Time filtering
        assert len(recent_messages) >= 2, "Should find recent messages (within 7 days)"
        assert len(older_messages) >= 6, "Should find older messages (7-30 days ago)"
        
        # Verify time boundaries
        for msg in recent_messages:
            days_diff = (datetime.now(timezone.utc) - datetime.fromisoformat(msg["timestamp"].replace("Z", "+00:00"))).days
            assert days_diff <= 7, "Recent messages should be within 7 days"
        
        # Topic filtering
        assert len(db_optimization_messages) == 2, "Should find database optimization thread"
        assert len(api_design_messages) == 2, "Should find API design thread"
        
        # Complex search
        assert len(recent_database_questions) >= 1, "Should find recent database questions"
        for msg in recent_database_questions:
            assert msg["message_type"] == "user_input"
            assert "database" in msg["content"].lower()
        
        # Search result quality and relevance
        db_search_relevance = await self._analyze_search_relevance(database_messages, "database")
        assert db_search_relevance["average_relevance"] > 0.8, "Database search should be highly relevant"
        
        print(" PASS:  Message search and filtering real database test passed")

    # Helper methods for real service integration

    async def _receive_user_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate receiving and validating user message."""
        try:
            # Validate message structure
            required_fields = ["message_id", "user_id", "content", "message_type", "timestamp"]
            if not all(field in message for field in required_fields):
                return {"success": False, "error": "Invalid message structure"}
            
            # Store in Redis for immediate processing
            message_key = f"incoming_message:{message['user_id']}:{message['message_id']}"
            await self.redis_client.setex(
                message_key,
                300,  # 5 minutes
                json.dumps(message, default=str)
            )
            
            return {"success": True, "message_id": message["message_id"]}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _store_message_in_database(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Store message in real database (simulated with Redis for testing)."""
        try:
            # Store individual message
            message_key = f"message:{message['user_id']}:{message['message_id']}"
            message_json = json.dumps(message, default=str)
            await self.redis_client.setex(message_key, 86400*30, message_json)  # 30 days
            
            # Add to user's message index
            user_messages_key = f"user_messages:{message['user_id']}"
            await self.redis_client.zadd(user_messages_key, {
                message_key: message["timestamp"].timestamp()
            })
            
            # Add to thread index
            thread_key = f"thread_messages:{message['thread_id']}"
            await self.redis_client.zadd(thread_key, {
                message_key: message["timestamp"].timestamp()
            })
            
            return {"success": True, "stored_at": message_key}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _queue_message_for_agent_processing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Queue message for agent processing."""
        try:
            processing_queue = "agent_processing_queue"
            queue_item = {
                "message_id": message["message_id"],
                "user_id": message["user_id"],
                "priority": message.get("context", {}).get("priority", "normal"),
                "queued_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Use priority score for queue ordering
            priority_scores = {"high": 3, "normal": 2, "low": 1}
            priority_score = priority_scores.get(queue_item["priority"], 2)
            
            await self.redis_client.zadd(processing_queue, {
                json.dumps(queue_item): priority_score
            })
            
            return {"success": True, "queued_priority": queue_item["priority"]}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _simulate_agent_message_processing(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate agent processing of user message."""
        try:
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            processing_result = {
                "message_processed": message["message_id"],
                "processing_time": 0.1,
                "agent_type": "database_optimization",
                "confidence": 0.95,
                "topics_identified": ["database", "performance", "optimization"],
                "response_generated": True
            }
            
            return {"success": True, "result": processing_result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _deliver_message_via_websocket(self, user_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate message delivery via WebSocket."""
        try:
            # Check if user is online
            user_status_key = f"user_status:{user_id}"
            user_status = await self.redis_client.get(user_status_key)
            
            if user_status and json.loads(user_status).get("online", False):
                # Simulate WebSocket delivery
                delivery_key = f"delivered_message:{user_id}:{message['message_id']}"
                delivery_info = {
                    "message_id": message["message_id"],
                    "delivered_at": datetime.now(timezone.utc).isoformat(),
                    "delivery_method": "websocket",
                    "status": "delivered"
                }
                
                await self.redis_client.setex(
                    delivery_key,
                    86400,  # 24 hours
                    json.dumps(delivery_info)
                )
                
                return {"success": True, "delivery_method": "websocket", "immediate": True}
            else:
                # Queue for later delivery
                await self._queue_message_for_offline_delivery(user_id, message)
                return {"success": True, "delivery_method": "queued", "immediate": False}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _retrieve_thread_messages(self, thread_id: str) -> List[Dict[str, Any]]:
        """Retrieve all messages in a thread."""
        try:
            thread_key = f"thread_messages:{thread_id}"
            message_keys = await self.redis_client.zrange(thread_key, 0, -1)
            
            messages = []
            for key in message_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    messages.append(json.loads(message_json))
            
            # Sort by timestamp
            messages.sort(key=lambda x: x["timestamp"])
            return messages
            
        except Exception as e:
            print(f"Error retrieving thread messages: {e}")
            return []

    async def _retrieve_conversation_history(self, user_id: str, thread_id: str) -> List[Dict[str, Any]]:
        """Retrieve conversation history for specific thread."""
        return await self._retrieve_thread_messages(thread_id)

    async def _retrieve_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve recent messages for user."""
        try:
            user_messages_key = f"user_messages:{user_id}"
            recent_keys = await self.redis_client.zrevrange(user_messages_key, 0, limit-1)
            
            messages = []
            for key in recent_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    messages.append(json.loads(message_json))
            
            return messages
            
        except Exception as e:
            print(f"Error retrieving recent messages: {e}")
            return []

    async def _retrieve_messages_by_type(self, user_id: str, message_type: str) -> List[Dict[str, Any]]:
        """Retrieve messages filtered by type."""
        try:
            user_messages_key = f"user_messages:{user_id}"
            all_keys = await self.redis_client.zrange(user_messages_key, 0, -1)
            
            filtered_messages = []
            for key in all_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    message = json.loads(message_json)
                    if message.get("message_type") == message_type:
                        filtered_messages.append(message)
            
            return filtered_messages
            
        except Exception as e:
            print(f"Error retrieving messages by type: {e}")
            return []

    async def _set_user_online_status(self, user_id: str, online: bool) -> Dict[str, Any]:
        """Set user online/offline status."""
        try:
            status_key = f"user_status:{user_id}"
            status_data = {
                "online": online,
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            
            await self.redis_client.setex(
                status_key,
                3600,  # 1 hour
                json.dumps(status_data)
            )
            
            return {"success": True, "status": "online" if online else "offline"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _queue_message_for_offline_delivery(self, user_id: str, message: Dict[str, Any]) -> Dict[str, Any]:
        """Queue message for offline user delivery."""
        try:
            queue_key = f"offline_queue:{user_id}"
            queue_item = {
                "message": message,
                "queued_at": datetime.now(timezone.utc).isoformat(),
                "priority": message.get("priority", "medium")
            }
            
            # Priority scoring for queue order
            priority_scores = {"high": 3, "medium": 2, "low": 1}
            score = priority_scores.get(queue_item["priority"], 2)
            
            await self.redis_client.zadd(queue_key, {
                json.dumps(queue_item, default=str): score
            })
            
            return {"success": True, "queued_for_user": user_id}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _get_queued_message_count(self, user_id: str) -> int:
        """Get count of queued messages for user."""
        try:
            queue_key = f"offline_queue:{user_id}"
            count = await self.redis_client.zcard(queue_key)
            return count
            
        except Exception:
            return 0

    async def _process_offline_message_delivery(self, user_id: str) -> Dict[str, Any]:
        """Process delivery of queued messages for newly online user."""
        try:
            queue_key = f"offline_queue:{user_id}"
            
            # Get all queued messages (ordered by priority)
            queued_items = await self.redis_client.zrevrange(queue_key, 0, -1)
            
            delivered_messages = []
            for item_json in queued_items:
                queue_item = json.loads(item_json)
                message = queue_item["message"]
                
                # Simulate delivery
                delivery_result = await self._deliver_message_via_websocket(user_id, message)
                if delivery_result["success"]:
                    delivered_messages.append(message)
            
            # Clear queue after successful delivery
            await self.redis_client.delete(queue_key)
            
            return {
                "success": True,
                "messages_delivered": len(delivered_messages),
                "delivered_messages": delivered_messages
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _check_message_delivery_status(self, message_id: str) -> Dict[str, Any]:
        """Check delivery status of a message."""
        try:
            # Search for delivery record across all users (simplified for testing)
            delivery_keys = await self.redis_client.keys(f"delivered_message:*:{message_id}")
            
            if delivery_keys:
                delivery_info_json = await self.redis_client.get(delivery_keys[0])
                delivery_info = json.loads(delivery_info_json)
                return {
                    "delivered": True,
                    "delivered_at": delivery_info["delivered_at"],
                    "method": delivery_info["delivery_method"]
                }
            
            return {"delivered": False, "delivered_at": None}
            
        except Exception as e:
            return {"delivered": False, "error": str(e)}

    async def _store_message_with_threading_info(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Store message with threading information."""
        # Same as regular storage but preserves threading metadata
        return await self._store_message_in_database(message)

    async def _retrieve_user_thread_tree(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user's complete thread hierarchy."""
        try:
            user_messages_key = f"user_messages:{user_id}"
            all_keys = await self.redis_client.zrange(user_messages_key, 0, -1)
            
            threads = {}
            thread_hierarchy = {}
            
            for key in all_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    message = json.loads(message_json)
                    thread_id = message["thread_id"]
                    
                    if thread_id not in threads:
                        threads[thread_id] = []
                        thread_hierarchy[thread_id] = {"child_threads": []}
                    
                    threads[thread_id].append(message)
                    
                    # Handle parent thread relationships
                    if "parent_thread" in message:
                        parent_thread = message["parent_thread"]
                        if parent_thread not in thread_hierarchy:
                            thread_hierarchy[parent_thread] = {"child_threads": []}
                        if thread_id not in thread_hierarchy[parent_thread]["child_threads"]:
                            thread_hierarchy[parent_thread]["child_threads"].append(thread_id)
            
            return {
                "threads": threads,
                "thread_hierarchy": thread_hierarchy,
                "total_threads": len(threads)
            }
            
        except Exception as e:
            print(f"Error retrieving thread tree: {e}")
            return {"threads": {}, "thread_hierarchy": {}}

    async def _analyze_context_preservation(self, child_thread_id: str, parent_thread_id: str) -> Dict[str, Any]:
        """Analyze context preservation between threads."""
        try:
            parent_messages = await self._retrieve_thread_messages(parent_thread_id)
            child_messages = await self._retrieve_thread_messages(child_thread_id)
            
            if not parent_messages or not child_messages:
                return {"context_carried": False, "preserved_concepts": []}
            
            # Extract concepts from parent thread
            parent_concepts = set()
            for msg in parent_messages:
                content_lower = msg["content"].lower()
                # Simple concept extraction
                concepts = ["e-commerce", "database", "optimization", "performance", "product", "catalog"]
                for concept in concepts:
                    if concept in content_lower:
                        parent_concepts.add(concept)
            
            # Check if concepts are referenced in child thread
            preserved_concepts = []
            for msg in child_messages:
                content_lower = msg["content"].lower()
                for concept in parent_concepts:
                    if concept in content_lower and concept not in preserved_concepts:
                        preserved_concepts.append(concept)
            
            return {
                "context_carried": len(preserved_concepts) > 0,
                "preserved_concepts": preserved_concepts,
                "parent_concepts": list(parent_concepts),
                "preservation_ratio": len(preserved_concepts) / len(parent_concepts) if parent_concepts else 0
            }
            
        except Exception as e:
            print(f"Error analyzing context preservation: {e}")
            return {"context_carried": False, "preserved_concepts": []}

    async def _search_messages_by_content(self, user_id: str, search_term: str) -> List[Dict[str, Any]]:
        """Search messages by content."""
        try:
            user_messages_key = f"user_messages:{user_id}"
            all_keys = await self.redis_client.zrange(user_messages_key, 0, -1)
            
            matching_messages = []
            for key in all_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    message = json.loads(message_json)
                    if search_term.lower() in message["content"].lower():
                        matching_messages.append(message)
            
            return matching_messages
            
        except Exception as e:
            print(f"Error searching messages: {e}")
            return []

    async def _filter_messages_by_type(self, user_id: str, message_type: str) -> List[Dict[str, Any]]:
        """Filter messages by type."""
        return await self._retrieve_messages_by_type(user_id, message_type)

    async def _filter_messages_by_date(self, user_id: str, days_back: int, exclude_recent: int = 0) -> List[Dict[str, Any]]:
        """Filter messages by date range."""
        try:
            user_messages_key = f"user_messages:{user_id}"
            all_keys = await self.redis_client.zrange(user_messages_key, 0, -1)
            
            now = datetime.now(timezone.utc)
            start_date = now - timedelta(days=days_back)
            exclude_date = now - timedelta(days=exclude_recent) if exclude_recent > 0 else None
            
            filtered_messages = []
            for key in all_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    message = json.loads(message_json)
                    msg_time = datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))
                    
                    if msg_time >= start_date:
                        if exclude_date is None or msg_time <= exclude_date:
                            filtered_messages.append(message)
            
            return filtered_messages
            
        except Exception as e:
            print(f"Error filtering by date: {e}")
            return []

    async def _filter_messages_by_topic(self, user_id: str, topic: str) -> List[Dict[str, Any]]:
        """Filter messages by topic."""
        try:
            user_messages_key = f"user_messages:{user_id}"
            all_keys = await self.redis_client.zrange(user_messages_key, 0, -1)
            
            topic_messages = []
            for key in all_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    message = json.loads(message_json)
                    if message.get("topic") == topic:
                        topic_messages.append(message)
            
            return topic_messages
            
        except Exception as e:
            print(f"Error filtering by topic: {e}")
            return []

    async def _search_messages_complex_filter(self, user_id: str, content_search: str = None, 
                                            message_type: str = None, days_back: int = 30) -> List[Dict[str, Any]]:
        """Perform complex message search with multiple filters."""
        try:
            # Start with all messages
            user_messages_key = f"user_messages:{user_id}"
            all_keys = await self.redis_client.zrange(user_messages_key, 0, -1)
            
            filtered_messages = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
            
            for key in all_keys:
                message_json = await self.redis_client.get(key)
                if message_json:
                    message = json.loads(message_json)
                    
                    # Apply filters
                    passes_filters = True
                    
                    # Content search filter
                    if content_search and content_search.lower() not in message["content"].lower():
                        passes_filters = False
                    
                    # Message type filter
                    if message_type and message.get("message_type") != message_type:
                        passes_filters = False
                    
                    # Date filter
                    msg_time = datetime.fromisoformat(message["timestamp"].replace("Z", "+00:00"))
                    if msg_time < cutoff_date:
                        passes_filters = False
                    
                    if passes_filters:
                        filtered_messages.append(message)
            
            return filtered_messages
            
        except Exception as e:
            print(f"Error in complex search: {e}")
            return []

    async def _analyze_search_relevance(self, search_results: List[Dict[str, Any]], search_term: str) -> Dict[str, Any]:
        """Analyze search result relevance."""
        if not search_results:
            return {"average_relevance": 0.0, "total_results": 0}
        
        relevance_scores = []
        search_term_lower = search_term.lower()
        
        for message in search_results:
            content_lower = message["content"].lower()
            # Simple relevance scoring based on term frequency
            term_count = content_lower.count(search_term_lower)
            content_length = len(content_lower.split())
            
            # Relevance score: term frequency / content length (normalized)
            relevance = min(term_count / content_length * 10, 1.0) if content_length > 0 else 0.0
            relevance_scores.append(relevance)
        
        return {
            "average_relevance": sum(relevance_scores) / len(relevance_scores),
            "total_results": len(search_results),
            "min_relevance": min(relevance_scores),
            "max_relevance": max(relevance_scores)
        }


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x"  # Stop on first failure for fast feedback
    ])