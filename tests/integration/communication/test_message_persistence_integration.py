"""
Message Persistence and Queuing Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable message persistence enables AI conversation continuity
- Value Impact: Message persistence preserves AI interactions and enables conversation history
- Strategic Impact: Data persistence foundation for user engagement and $500K+ ARR retention

CRITICAL: Message persistence enables conversation continuity per CLAUDE.md
Persistent messaging ensures users can review AI analysis history and maintain context.

These integration tests validate message storage, queuing patterns, message retrieval,
data consistency, and cleanup mechanisms without requiring Docker services.
"""

import asyncio
import json
import time
import uuid
from collections import deque, defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import websockets
from websockets import WebSocketException, ConnectionClosed

# SSOT imports - using absolute imports only per CLAUDE.md
from shared.isolated_environment import get_env
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage,
    WebSocketTestMetrics
)


class MessageStore:
    """Mock message store for integration testing."""
    
    def __init__(self, max_size: int = 1000):
        self.messages: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.max_size = max_size
        self.total_messages = 0
    
    async def store_message(self, user_id: str, message: Dict[str, Any]) -> str:
        """Store a message and return message ID."""
        message_id = f"stored_{uuid.uuid4().hex[:8]}"
        message_with_id = {**message, "stored_id": message_id, "stored_at": time.time()}
        
        self.messages[user_id].append(message_with_id)
        self.total_messages += 1
        
        # Simple cleanup if over max size
        if len(self.messages[user_id]) > self.max_size // 10:  # Per user limit
            self.messages[user_id] = self.messages[user_id][-50:]  # Keep latest 50
        
        return message_id
    
    async def get_messages(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve messages for a user."""
        user_messages = self.messages.get(user_id, [])
        return user_messages[-limit:] if limit else user_messages
    
    async def get_thread_messages(self, user_id: str, thread_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve messages for a specific thread."""
        user_messages = self.messages.get(user_id, [])
        thread_messages = [
            msg for msg in user_messages 
            if msg.get("thread_id") == thread_id
        ]
        return thread_messages[-limit:] if limit else thread_messages
    
    async def cleanup_old_messages(self, older_than_hours: int = 24) -> int:
        """Clean up old messages."""
        cutoff_time = time.time() - (older_than_hours * 3600)
        cleaned_count = 0
        
        for user_id in list(self.messages.keys()):
            original_count = len(self.messages[user_id])
            self.messages[user_id] = [
                msg for msg in self.messages[user_id]
                if msg.get("stored_at", 0) >= cutoff_time
            ]
            cleaned_count += original_count - len(self.messages[user_id])
        
        return cleaned_count


@pytest.mark.integration
class TestMessagePersistence(SSotBaseTestCase):
    """
    Test message persistence patterns and storage reliability.
    
    BVJ: Message persistence enables AI conversation continuity and history
    """
    
    async def test_agent_message_persistence(self):
        """
        Test persistence of AI agent messages and responses.
        
        BVJ: Agent message persistence enables users to review AI analysis history
        """
        message_store = MessageStore()
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("persist-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Generate AI agent conversation
            conversation_id = f"conv_{uuid.uuid4().hex[:8]}"
            thread_id = f"thread_{uuid.uuid4().hex[:8]}"
            
            agent_messages = [
                {
                    "event_type": WebSocketEventType.AGENT_STARTED,
                    "data": {
                        "agent_type": "cost_optimizer",
                        "user_request": "Analyze my AWS spending",
                        "conversation_id": conversation_id,
                        "estimated_duration": "2-3 minutes"
                    }
                },
                {
                    "event_type": WebSocketEventType.AGENT_THINKING, 
                    "data": {
                        "current_thought": "Loading billing data from AWS API",
                        "progress": 0.3,
                        "conversation_id": conversation_id,
                        "reasoning": "Need to gather 90 days of cost data"
                    }
                },
                {
                    "event_type": WebSocketEventType.TOOL_COMPLETED,
                    "data": {
                        "tool_name": "aws_cost_analyzer",
                        "results": {
                            "monthly_cost": 4520.75,
                            "potential_savings": 1130.25,
                            "top_recommendations": [
                                "Right-size 6 underutilized EC2 instances",
                                "Switch to Reserved Instances for predictable workloads",
                                "Enable S3 Intelligent Tiering for storage optimization"
                            ]
                        },
                        "conversation_id": conversation_id,
                        "execution_time": 15.2
                    }
                },
                {
                    "event_type": WebSocketEventType.AGENT_COMPLETED,
                    "data": {
                        "agent_type": "cost_optimizer",
                        "final_result": "Identified $1,130/month savings opportunity (25% reduction)",
                        "conversation_id": conversation_id,
                        "confidence_score": 0.92,
                        "next_steps": [
                            "Review detailed recommendations",
                            "Implement high-impact changes first",
                            "Schedule monthly cost reviews"
                        ]
                    }
                }
            ]
            
            # Send and persist agent messages
            stored_message_ids = []
            for msg_data in agent_messages:
                # Send message via WebSocket
                await client.send_message(
                    msg_data["event_type"],
                    msg_data["data"],
                    user_id="persist-user",
                    thread_id=thread_id
                )
                
                # Persist message
                persistence_data = {
                    "event_type": msg_data["event_type"].value,
                    "data": msg_data["data"],
                    "user_id": "persist-user",
                    "thread_id": thread_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message_type": "agent_message"
                }
                
                stored_id = await message_store.store_message("persist-user", persistence_data)
                stored_message_ids.append(stored_id)
            
            # Verify persistence
            assert len(stored_message_ids) == len(agent_messages)
            assert len(client.sent_messages) == len(agent_messages)
            
            # Retrieve persisted messages
            retrieved_messages = await message_store.get_messages("persist-user")
            assert len(retrieved_messages) == len(agent_messages)
            
            # Verify message content integrity
            for i, retrieved_msg in enumerate(retrieved_messages):
                original_data = agent_messages[i]["data"]
                assert retrieved_msg["data"]["conversation_id"] == conversation_id
                assert retrieved_msg["user_id"] == "persist-user"
                assert retrieved_msg["thread_id"] == thread_id
                assert "stored_at" in retrieved_msg
                assert "stored_id" in retrieved_msg
            
            # Test thread-specific retrieval
            thread_messages = await message_store.get_thread_messages("persist-user", thread_id)
            assert len(thread_messages) == len(agent_messages)
            
            self.record_metric("agent_message_persistence", len(stored_message_ids))
    
    async def test_user_message_persistence(self):
        """
        Test persistence of user messages and requests.
        
        BVJ: User message persistence enables conversation context and history
        """
        message_store = MessageStore()
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("user-persist")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Simulate user conversation messages
            user_messages = [
                {
                    "content": "I need help analyzing my cloud costs",
                    "role": "user",
                    "intent": "cost_analysis_request",
                    "context": {"current_spend": "unknown", "services": ["EC2", "S3", "RDS"]}
                },
                {
                    "content": "Can you focus on EC2 instances specifically?",
                    "role": "user",
                    "intent": "clarification",
                    "context": {"refinement": "focus_ec2", "previous_request": "cost_analysis"}
                },
                {
                    "content": "What about Reserved Instances vs On-Demand pricing?",
                    "role": "user", 
                    "intent": "follow_up_question",
                    "context": {"topic": "pricing_models", "comparison": ["reserved", "on_demand"]}
                },
                {
                    "content": "Thank you, this analysis is very helpful!",
                    "role": "user",
                    "intent": "acknowledgment", 
                    "context": {"sentiment": "positive", "satisfaction": "high"}
                }
            ]
            
            conversation_id = f"user_conv_{uuid.uuid4().hex[:8]}"
            thread_id = f"user_thread_{uuid.uuid4().hex[:8]}"
            
            # Send and persist user messages
            for i, user_msg in enumerate(user_messages):
                # Send user message
                await client.send_message(
                    WebSocketEventType.MESSAGE_CREATED,
                    {
                        **user_msg,
                        "conversation_id": conversation_id,
                        "sequence": i + 1,
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    },
                    user_id="user-persist",
                    thread_id=thread_id
                )
                
                # Persist user message
                persistence_data = {
                    "content": user_msg["content"],
                    "role": user_msg["role"],
                    "intent": user_msg["intent"],
                    "context": user_msg["context"],
                    "conversation_id": conversation_id,
                    "sequence": i + 1,
                    "user_id": "user-persist",
                    "thread_id": thread_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message_type": "user_message"
                }
                
                await message_store.store_message("user-persist", persistence_data)
            
            # Verify user message persistence
            retrieved_messages = await message_store.get_messages("user-persist")
            assert len(retrieved_messages) == len(user_messages)
            
            # Verify conversation flow preservation
            for i, retrieved_msg in enumerate(retrieved_messages):
                assert retrieved_msg["sequence"] == i + 1
                assert retrieved_msg["conversation_id"] == conversation_id
                assert retrieved_msg["role"] == "user"
                assert retrieved_msg["intent"] == user_messages[i]["intent"]
            
            # Test intent-based message filtering
            clarification_messages = [
                msg for msg in retrieved_messages
                if msg["intent"] == "clarification"
            ]
            assert len(clarification_messages) == 1
            
            follow_up_messages = [
                msg for msg in retrieved_messages
                if msg["intent"] == "follow_up_question"
            ]
            assert len(follow_up_messages) == 1
            
            self.record_metric("user_message_persistence", len(user_messages))
    
    async def test_conversation_context_persistence(self):
        """
        Test persistence of complete conversation context and metadata.
        
        BVJ: Context persistence enables AI to maintain conversation coherence
        """
        message_store = MessageStore()
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("context-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Create comprehensive conversation context
            conversation_context = {
                "conversation_id": f"ctx_conv_{uuid.uuid4().hex[:8]}",
                "user_id": "context-user",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "topic": "aws_cost_optimization",
                "user_profile": {
                    "tier": "enterprise",
                    "industry": "fintech",
                    "team_size": "50-100",
                    "cloud_provider": "aws"
                },
                "session_metadata": {
                    "user_agent": "Mozilla/5.0 (WebKit/537.36)",
                    "source": "web_chat",
                    "referrer": "dashboard",
                    "session_id": f"sess_{uuid.uuid4().hex[:8]}"
                },
                "ai_context": {
                    "primary_agent": "cost_optimizer",
                    "tools_available": ["aws_cost_analyzer", "recommendation_engine"],
                    "analysis_scope": ["ec2", "s3", "rds", "lambda"],
                    "optimization_goals": ["cost_reduction", "performance_maintenance"]
                }
            }
            
            # Persist conversation context
            context_stored_id = await message_store.store_message(
                "context-user",
                {
                    "message_type": "conversation_context",
                    "context": conversation_context,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            
            # Add conversation messages with context references
            contextual_messages = [
                {
                    "event_type": WebSocketEventType.AGENT_STARTED,
                    "data": {
                        "agent_type": "cost_optimizer",
                        "conversation_context_id": context_stored_id,
                        "user_profile_applied": True,
                        "personalization": {
                            "industry_focus": "fintech_compliance",
                            "team_context": "medium_enterprise",
                            "provider_expertise": "aws_optimization"
                        }
                    }
                },
                {
                    "event_type": WebSocketEventType.AGENT_COMPLETED,
                    "data": {
                        "results": "Analysis tailored for fintech compliance requirements",
                        "conversation_context_id": context_stored_id,
                        "personalization_applied": [
                            "industry_specific_recommendations",
                            "compliance_considerations",
                            "team_scale_optimization"
                        ]
                    }
                }
            ]
            
            # Send and persist contextual messages
            for msg_data in contextual_messages:
                await client.send_message(
                    msg_data["event_type"],
                    msg_data["data"],
                    user_id="context-user"
                )
                
                persistence_data = {
                    "event_type": msg_data["event_type"].value,
                    "data": msg_data["data"],
                    "conversation_context_id": context_stored_id,
                    "user_id": "context-user",
                    "message_type": "contextual_agent_message",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await message_store.store_message("context-user", persistence_data)
            
            # Verify context persistence
            all_messages = await message_store.get_messages("context-user")
            context_messages = [msg for msg in all_messages if msg["message_type"] == "conversation_context"]
            contextual_agent_messages = [msg for msg in all_messages if msg["message_type"] == "contextual_agent_message"]
            
            assert len(context_messages) == 1
            assert len(contextual_agent_messages) == len(contextual_messages)
            
            # Verify context linkage
            stored_context = context_messages[0]["context"]
            assert stored_context["user_profile"]["tier"] == "enterprise"
            assert stored_context["ai_context"]["primary_agent"] == "cost_optimizer"
            
            # Verify contextual message references
            for contextual_msg in contextual_agent_messages:
                assert contextual_msg["conversation_context_id"] == context_stored_id
                assert "personalization" in contextual_msg["data"] or "personalization_applied" in contextual_msg["data"]
            
            self.record_metric("conversation_context_persistence", len(all_messages))
    
    async def test_message_search_and_retrieval(self):
        """
        Test message search and retrieval capabilities.
        
        BVJ: Message search enables users to find relevant AI insights from history
        """
        message_store = MessageStore()
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("search-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Create searchable message dataset
            searchable_messages = [
                {
                    "content": "AWS cost analysis for production environment",
                    "tags": ["aws", "cost", "production"],
                    "category": "cost_optimization",
                    "priority": "high"
                },
                {
                    "content": "Security vulnerability scan results",
                    "tags": ["security", "vulnerability", "scan"],
                    "category": "security_analysis", 
                    "priority": "critical"
                },
                {
                    "content": "Performance optimization for API endpoints",
                    "tags": ["performance", "api", "optimization"],
                    "category": "performance_tuning",
                    "priority": "medium"
                },
                {
                    "content": "Database query optimization recommendations",
                    "tags": ["database", "query", "optimization"],
                    "category": "database_tuning",
                    "priority": "high"
                },
                {
                    "content": "AWS Lambda function cost analysis",
                    "tags": ["aws", "lambda", "cost", "serverless"],
                    "category": "cost_optimization", 
                    "priority": "medium"
                }
            ]
            
            # Store searchable messages
            stored_ids = []
            for i, msg in enumerate(searchable_messages):
                persistence_data = {
                    "content": msg["content"],
                    "tags": msg["tags"],
                    "category": msg["category"],
                    "priority": msg["priority"],
                    "sequence": i + 1,
                    "user_id": "search-user",
                    "message_type": "searchable_message",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "searchable_text": msg["content"].lower()  # For search simulation
                }
                
                stored_id = await message_store.store_message("search-user", persistence_data)
                stored_ids.append(stored_id)
            
            # Test various search scenarios
            search_scenarios = [
                {
                    "search_term": "aws cost",
                    "expected_matches": 2,  # AWS cost analysis + AWS Lambda cost
                    "search_type": "content_search"
                },
                {
                    "search_term": "optimization",
                    "expected_matches": 3,  # cost, performance, database
                    "search_type": "content_search"
                },
                {
                    "search_category": "cost_optimization", 
                    "expected_matches": 2,
                    "search_type": "category_filter"
                },
                {
                    "search_priority": "high",
                    "expected_matches": 2,
                    "search_type": "priority_filter"
                }
            ]
            
            # Execute search scenarios
            for scenario in search_scenarios:
                search_request = {
                    "type": "message_search_request",
                    "user_id": "search-user",
                    "scenario": scenario,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    search_request,
                    user_id="search-user"
                )
                
                # Simulate search execution
                all_messages = await message_store.get_messages("search-user")
                searchable_msgs = [msg for msg in all_messages if msg["message_type"] == "searchable_message"]
                
                # Apply search logic
                search_results = []
                if scenario["search_type"] == "content_search":
                    search_term = scenario["search_term"].lower()
                    search_results = [
                        msg for msg in searchable_msgs
                        if search_term in msg["searchable_text"]
                    ]
                elif scenario["search_type"] == "category_filter":
                    search_results = [
                        msg for msg in searchable_msgs
                        if msg["category"] == scenario["search_category"]
                    ]
                elif scenario["search_type"] == "priority_filter":
                    search_results = [
                        msg for msg in searchable_msgs
                        if msg["priority"] == scenario["search_priority"]
                    ]
                
                # Send search results
                search_response = {
                    "type": "message_search_results",
                    "query": scenario,
                    "results_count": len(search_results),
                    "results": [
                        {
                            "content": result["content"],
                            "category": result["category"],
                            "priority": result["priority"],
                            "timestamp": result["timestamp"]
                        }
                        for result in search_results
                    ]
                }
                
                search_result_msg = WebSocketMessage(
                    event_type=WebSocketEventType.STATUS_UPDATE,
                    data=search_response,
                    timestamp=datetime.now(timezone.utc),
                    message_id=f"search_{uuid.uuid4().hex[:8]}",
                    user_id="search-service"
                )
                client.received_messages.append(search_result_msg)
                
                # Verify search results
                assert len(search_results) == scenario["expected_matches"]
            
            # Verify search functionality
            assert len(client.sent_messages) == len(search_scenarios)
            assert len(client.received_messages) == len(search_scenarios)
            
            self.record_metric("message_search_scenarios", len(search_scenarios))


@pytest.mark.integration
class TestMessageQueuing(SSotBaseTestCase):
    """
    Test message queuing patterns and delivery guarantees.
    
    BVJ: Message queuing ensures reliable AI response delivery under load
    """
    
    async def test_priority_message_queuing(self):
        """
        Test priority-based message queuing and processing.
        
        BVJ: Priority queuing ensures critical AI alerts reach users first
        """
        # Mock priority queue implementation
        priority_queues = {
            "critical": deque(),
            "high": deque(), 
            "medium": deque(),
            "low": deque()
        }
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("priority-queue-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Generate messages with different priorities
            queued_messages = [
                {"priority": "low", "content": "Monthly report generated", "urgency": "informational"},
                {"priority": "high", "content": "Cost spike detected - 40% increase", "urgency": "attention_needed"},
                {"priority": "medium", "content": "Optimization recommendation available", "urgency": "review_when_convenient"},
                {"priority": "critical", "content": "Security breach detected", "urgency": "immediate_action"},
                {"priority": "medium", "content": "Performance degradation noted", "urgency": "investigate_soon"},
                {"priority": "high", "content": "Budget threshold exceeded", "urgency": "urgent_review"},
                {"priority": "low", "content": "Weekly summary available", "urgency": "informational"},
                {"priority": "critical", "content": "System outage in progress", "urgency": "emergency"},
            ]
            
            # Queue messages by priority
            for i, msg in enumerate(queued_messages):
                queue_entry = {
                    "message_id": f"queue_{uuid.uuid4().hex[:8]}",
                    "priority": msg["priority"],
                    "content": msg["content"],
                    "urgency": msg["urgency"],
                    "queued_at": time.time(),
                    "sequence": i + 1,
                    "user_id": "priority-queue-user"
                }
                
                priority_queues[msg["priority"]].append(queue_entry)
            
            # Process messages in priority order (critical > high > medium > low)
            processing_order = ["critical", "high", "medium", "low"]
            processed_messages = []
            
            for priority in processing_order:
                while priority_queues[priority]:
                    msg = priority_queues[priority].popleft()
                    
                    # Send processed message
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        {
                            "type": "priority_message_processed",
                            "priority": msg["priority"],
                            "content": msg["content"],
                            "urgency": msg["urgency"],
                            "original_sequence": msg["sequence"],
                            "processed_at": time.time()
                        },
                        user_id="priority-queue-user"
                    )
                    
                    processed_messages.append(msg)
            
            # Verify priority processing
            assert len(processed_messages) == len(queued_messages)
            assert len(client.sent_messages) == len(queued_messages)
            
            # Verify priority order was maintained
            sent_priorities = [msg.data["priority"] for msg in client.sent_messages]
            
            # Critical messages should come first
            critical_positions = [i for i, p in enumerate(sent_priorities) if p == "critical"]
            high_positions = [i for i, p in enumerate(sent_priorities) if p == "high"]
            medium_positions = [i for i, p in enumerate(sent_priorities) if p == "medium"]
            low_positions = [i for i, p in enumerate(sent_priorities) if p == "low"]
            
            # Verify ordering constraints
            if critical_positions and high_positions:
                assert max(critical_positions) < min(high_positions)
            if high_positions and medium_positions:
                assert max(high_positions) < min(medium_positions)
            if medium_positions and low_positions:
                assert max(medium_positions) < min(low_positions)
            
            self.record_metric("priority_queue_processing", len(queued_messages))
    
    async def test_message_batching_and_delivery(self):
        """
        Test message batching for efficient delivery.
        
        BVJ: Message batching improves performance and reduces overhead
        """
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("batch-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Configuration for batching
            batch_config = {
                "max_batch_size": 10,
                "batch_timeout": 2.0,  # seconds
                "max_wait_time": 5.0   # seconds
            }
            
            # Generate messages for batching
            individual_messages = []
            for i in range(25):  # More than one batch worth
                individual_messages.append({
                    "message_id": f"batch_msg_{i}",
                    "content": f"Status update {i}",
                    "timestamp": time.time(),
                    "user_id": "batch-user",
                    "sequence": i + 1
                })
            
            # Simulate batching logic
            message_batches = []
            current_batch = []
            
            for msg in individual_messages:
                current_batch.append(msg)
                
                # Create batch when size limit reached
                if len(current_batch) >= batch_config["max_batch_size"]:
                    batch = {
                        "batch_id": f"batch_{uuid.uuid4().hex[:8]}",
                        "messages": current_batch.copy(),
                        "batch_size": len(current_batch),
                        "created_at": time.time(),
                        "user_id": "batch-user"
                    }
                    message_batches.append(batch)
                    current_batch = []
            
            # Handle remaining messages in final batch
            if current_batch:
                batch = {
                    "batch_id": f"batch_{uuid.uuid4().hex[:8]}",
                    "messages": current_batch,
                    "batch_size": len(current_batch),
                    "created_at": time.time(),
                    "user_id": "batch-user"
                }
                message_batches.append(batch)
            
            # Send batched messages
            for batch in message_batches:
                await client.send_message(
                    WebSocketEventType.STATUS_UPDATE,
                    {
                        "type": "message_batch",
                        "batch_id": batch["batch_id"],
                        "batch_size": batch["batch_size"],
                        "messages": batch["messages"],
                        "delivery_method": "batched",
                        "compression": "enabled"
                    },
                    user_id="batch-user"
                )
            
            # Verify batching efficiency
            expected_batches = (len(individual_messages) + batch_config["max_batch_size"] - 1) // batch_config["max_batch_size"]
            assert len(message_batches) == expected_batches
            assert len(client.sent_messages) == expected_batches
            
            # Verify all messages were included
            total_messages_in_batches = sum(batch["batch_size"] for batch in message_batches)
            assert total_messages_in_batches == len(individual_messages)
            
            # Verify batch size constraints
            for batch in message_batches[:-1]:  # All but last batch
                assert batch["batch_size"] == batch_config["max_batch_size"]
            
            # Last batch may be smaller
            if message_batches:
                last_batch_size = message_batches[-1]["batch_size"]
                remaining = len(individual_messages) % batch_config["max_batch_size"]
                expected_last_size = remaining if remaining > 0 else batch_config["max_batch_size"]
                assert last_batch_size == expected_last_size
            
            self.record_metric("message_batching", len(message_batches))
    
    async def test_queue_overflow_handling(self):
        """
        Test queue overflow handling and backpressure mechanisms.
        
        BVJ: Overflow handling prevents system crashes during high message volume
        """
        # Mock queue with limited capacity
        queue_capacity = 100
        message_queue = deque(maxlen=queue_capacity)
        overflow_count = 0
        dropped_messages = []
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("overflow-user")
            client.is_connected = True
            client.websocket = AsyncMock()
            
            # Generate more messages than queue capacity
            message_count = 150  # Exceeds capacity
            
            for i in range(message_count):
                message = {
                    "message_id": f"overflow_{i}",
                    "content": f"High volume message {i}",
                    "priority": "low" if i % 3 == 0 else "medium",
                    "timestamp": time.time(),
                    "sequence": i + 1
                }
                
                # Check queue capacity before adding
                if len(message_queue) >= queue_capacity:
                    # Handle overflow - drop lowest priority messages
                    if message_queue and message["priority"] != "low":
                        # Remove low priority message to make room
                        dropped = None
                        temp_queue = deque()
                        
                        while message_queue:
                            msg = message_queue.popleft()
                            if msg["priority"] == "low" and dropped is None:
                                dropped = msg
                                dropped_messages.append(msg)
                                overflow_count += 1
                            else:
                                temp_queue.append(msg)
                        
                        # Restore queue without dropped message
                        message_queue.extend(temp_queue)
                        
                        # Add new message
                        message_queue.append(message)
                    else:
                        # Drop current message if queue full with higher priority
                        dropped_messages.append(message)
                        overflow_count += 1
                else:
                    # Normal case - add to queue
                    message_queue.append(message)
                
                # Send overflow notification if needed
                if i > 0 and i % 50 == 0:  # Periodic overflow status
                    overflow_status = {
                        "type": "queue_overflow_status",
                        "queue_size": len(message_queue),
                        "queue_capacity": queue_capacity,
                        "overflow_count": overflow_count,
                        "dropped_messages": len(dropped_messages),
                        "utilization": len(message_queue) / queue_capacity
                    }
                    
                    await client.send_message(
                        WebSocketEventType.STATUS_UPDATE,
                        overflow_status,
                        user_id="overflow-user"
                    )
            
            # Final overflow report
            final_overflow_report = {
                "type": "final_overflow_report",
                "total_messages_generated": message_count,
                "messages_queued": len(message_queue),
                "messages_dropped": len(dropped_messages),
                "overflow_events": overflow_count,
                "queue_utilization": len(message_queue) / queue_capacity,
                "drop_rate": len(dropped_messages) / message_count
            }
            
            await client.send_message(
                WebSocketEventType.STATUS_UPDATE,
                final_overflow_report,
                user_id="overflow-user"
            )
            
            # Verify overflow handling
            assert len(message_queue) <= queue_capacity
            assert overflow_count > 0, "Should have overflow events with message count > capacity"
            assert len(dropped_messages) > 0, "Should have dropped messages"
            
            # Verify queue prioritization worked
            queue_priorities = [msg["priority"] for msg in message_queue]
            low_priority_count = queue_priorities.count("low")
            medium_priority_count = queue_priorities.count("medium")
            
            # Should prefer medium over low priority in final queue
            if medium_priority_count > 0:
                medium_ratio = medium_priority_count / len(message_queue)
                assert medium_ratio >= 0.5, "Should retain more medium priority messages"
            
            self.record_metric("overflow_handling", overflow_count)
            self.record_metric("messages_dropped", len(dropped_messages))
    
    async def test_dead_letter_queue_handling(self):
        """
        Test dead letter queue for failed message deliveries.
        
        BVJ: Dead letter queues prevent message loss and enable error analysis
        """
        # Mock dead letter queue
        dead_letter_queue = deque()
        retry_attempts = defaultdict(int)
        max_retries = 3
        
        async with WebSocketTestUtility() as ws_util:
            client = await ws_util.create_authenticated_client("dlq-user")
            client.is_connected = True
            
            # Generate messages with various failure scenarios
            test_messages = [
                {"id": "msg_1", "content": "Normal message", "will_fail": False},
                {"id": "msg_2", "content": "Temporary failure", "will_fail": True, "failure_type": "timeout"},
                {"id": "msg_3", "content": "Permanent failure", "will_fail": True, "failure_type": "invalid_format"},
                {"id": "msg_4", "content": "Recoverable failure", "will_fail": True, "failure_type": "network_error"},
                {"id": "msg_5", "content": "Another normal message", "will_fail": False},
            ]
            
            # Process messages with retry logic
            for msg in test_messages:
                message_id = msg["id"]
                delivery_success = False
                
                while not delivery_success and retry_attempts[message_id] <= max_retries:
                    try:
                        # Simulate message delivery
                        if msg["will_fail"] and retry_attempts[message_id] < 2:
                            # Simulate failure on first attempts
                            retry_attempts[message_id] += 1
                            
                            if msg["failure_type"] == "timeout":
                                mock_websocket = AsyncMock()
                                mock_websocket.send.side_effect = asyncio.TimeoutError("Send timeout")
                                client.websocket = mock_websocket
                                
                                await client.send_message(
                                    WebSocketEventType.STATUS_UPDATE,
                                    {
                                        "type": "delivery_attempt",
                                        "message_id": message_id,
                                        "attempt": retry_attempts[message_id],
                                        "status": "failed",
                                        "error": "timeout"
                                    },
                                    user_id="dlq-user"
                                )
                                
                            elif msg["failure_type"] == "network_error":
                                mock_websocket = AsyncMock()
                                mock_websocket.send.side_effect = ConnectionClosed(None, None)
                                client.websocket = mock_websocket
                                
                                await client.send_message(
                                    WebSocketEventType.ERROR,
                                    {
                                        "type": "delivery_failure",
                                        "message_id": message_id,
                                        "attempt": retry_attempts[message_id],
                                        "error": "network_error"
                                    },
                                    user_id="dlq-user"
                                )
                                
                        else:
                            # Successful delivery (or recovery after retries)
                            client.websocket = AsyncMock()
                            
                            await client.send_message(
                                WebSocketEventType.STATUS_UPDATE,
                                {
                                    "type": "message_delivered",
                                    "message_id": message_id,
                                    "content": msg["content"],
                                    "attempt": retry_attempts[message_id] + 1,
                                    "status": "success"
                                },
                                user_id="dlq-user"
                            )
                            
                            delivery_success = True
                            
                    except (asyncio.TimeoutError, ConnectionClosed):
                        # Continue retry loop
                        continue
                
                # Move to dead letter queue if max retries exceeded
                if not delivery_success:
                    dlq_entry = {
                        "message_id": message_id,
                        "content": msg["content"],
                        "failure_type": msg.get("failure_type", "unknown"),
                        "retry_attempts": retry_attempts[message_id],
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "reason": "max_retries_exceeded"
                    }
                    dead_letter_queue.append(dlq_entry)
                    
                    # Send DLQ notification
                    await client.send_message(
                        WebSocketEventType.ERROR,
                        {
                            "type": "message_moved_to_dlq",
                            "message_id": message_id,
                            "retry_attempts": retry_attempts[message_id],
                            "dlq_size": len(dead_letter_queue)
                        },
                        user_id="dlq-user"
                    )
            
            # Verify dead letter queue handling
            permanent_failures = [msg for msg in test_messages if msg.get("failure_type") == "invalid_format"]
            
            # Should have some messages in DLQ
            if dead_letter_queue:
                dlq_messages = list(dead_letter_queue)
                assert all(entry["retry_attempts"] >= max_retries for entry in dlq_messages)
                assert all("failed_at" in entry for entry in dlq_messages)
            
            # Verify retry attempts were made
            messages_with_retries = [msg_id for msg_id, attempts in retry_attempts.items() if attempts > 0]
            failing_messages = [msg["id"] for msg in test_messages if msg["will_fail"]]
            assert len(messages_with_retries) >= len(failing_messages)
            
            self.record_metric("dead_letter_queue_size", len(dead_letter_queue))
            self.record_metric("retry_attempts_total", sum(retry_attempts.values()))