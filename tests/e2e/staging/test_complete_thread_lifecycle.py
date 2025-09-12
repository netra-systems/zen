"""
Test Complete Thread Lifecycle in Staging Environment

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable thread management for sustained user engagement and conversation continuity
- Value Impact: Thread lifecycle failures break user chat experience and lead to data loss, directly impacting customer retention
- Strategic Impact: Core foundation for multi-user chat platform - thread management is critical for delivering AI value

This comprehensive E2E test suite validates complete thread lifecycle in staging environment:
1. Full thread creation to completion lifecycle with real user scenarios
2. Thread persistence across user sessions and reconnections  
3. Message continuity and ordering throughout thread lifecycle
4. Agent execution context preservation within thread lifecycle
5. Thread state management during concurrent operations
6. Recovery scenarios and error handling in thread lifecycle
7. Performance validation under realistic load conditions

CRITICAL REQUIREMENTS:
- MANDATORY OAuth/JWT authentication flows for all operations
- ALL 5 WebSocket events MUST be sent and validated (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- Real staging environment with actual services - NO MOCKS
- Real LLM agent execution within authenticated thread context
- Comprehensive Business Value delivery validation

CRITICAL: This test demonstrates substantive AI value delivery through complete thread lifecycle.
Expected: 5-7 test methods that prove end-to-end business value in staging environment.
"""

import asyncio
import json
import time
import uuid
import pytest
import websockets
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from unittest.mock import patch

# Test framework and authentication
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig,
    create_authenticated_user_context
)

# Staging configuration and utilities
from tests.e2e.staging.conftest import staging_services_fixture
from tests.e2e.staging_config import StagingTestConfig, staging_urls

# Strongly typed IDs and execution context
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.isolated_environment import get_env

# WebSocket event validation
from test_framework.websocket_helpers import (
    WebSocketTestClient, assert_websocket_events, wait_for_agent_completion
)


class TestCompleteThreadLifecycleStaging(BaseIntegrationTest):
    """
    Comprehensive E2E test suite for complete thread lifecycle in staging environment.
    
    This test suite validates that thread management delivers substantive business value
    through the complete lifecycle from creation to completion, ensuring users receive
    consistent AI-powered insights across extended conversations.
    """

    @pytest.fixture(autouse=True)
    async def setup_staging_auth(self):
        """Setup authenticated staging environment for all tests."""
        self.env = get_env()
        self.staging_config = StagingTestConfig()
        
        # Initialize E2E auth helper for staging environment
        self.auth_helper = E2EAuthHelper(environment="staging")
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        # Get staging authentication token - MANDATORY for all operations
        self.staging_token = await self.auth_helper.get_staging_token_async()
        assert self.staging_token, "CRITICAL: Failed to obtain staging authentication token"
        
        # Setup authenticated headers for API calls
        self.auth_headers = self.auth_helper.get_auth_headers(self.staging_token)
        self.websocket_headers = self.auth_helper.get_websocket_headers(self.staging_token)
        
        self.logger.info(" PASS:  Staging authentication setup complete - ready for authenticated E2E testing")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    @pytest.mark.mission_critical
    async def test_complete_thread_creation_to_completion_lifecycle_with_business_value(self):
        """
        Test complete thread lifecycle from creation to completion delivers business value.
        
        CRITICAL: This test validates the ENTIRE value delivery chain:
        1. Authenticated user creates thread
        2. Sends optimization request to agent
        3. Receives ALL 5 WebSocket events with real-time updates
        4. Agent delivers actionable business insights
        5. Thread state persists across operations
        6. User receives substantive AI value
        
        Business Value: Users get complete AI-powered cost optimization insights through authenticated thread lifecycle.
        """
        # Create authenticated user context with all required IDs
        user_context = await create_authenticated_user_context(
            user_email=f"lifecycle_test_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            permissions=["read", "write", "agent_execute"],
            websocket_enabled=True
        )
        
        self.logger.info(f"[U+1F680] Starting complete thread lifecycle test for user: {user_context.user_id}")
        self.logger.info(f"[U+1F4CB] Thread ID: {user_context.thread_id}")
        self.logger.info(f"[U+1F527] Run ID: {user_context.run_id}")
        
        # Track WebSocket events for validation
        websocket_events = []
        business_value_metrics = {
            "agent_response_time": None,
            "insights_delivered": 0,
            "actionable_recommendations": 0,
            "cost_savings_identified": 0
        }
        
        try:
            # PHASE 1: Thread Creation with Authentication
            start_time = time.time()
            
            async with websockets.connect(
                self.staging_config.urls.websocket_url,
                additional_headers=self.websocket_headers,
                open_timeout=15.0,  # Staging timeout optimization
                close_timeout=5.0
            ) as websocket:
                
                self.logger.info(" PASS:  WebSocket connection established with staging authentication")
                
                # Send thread creation request with business context
                thread_creation_message = {
                    "type": "create_thread",
                    "thread_id": str(user_context.thread_id),
                    "user_id": str(user_context.user_id),
                    "context": {
                        "business_segment": "enterprise",
                        "use_case": "cost_optimization",
                        "expected_value": "actionable_savings_recommendations"
                    },
                    "metadata": {
                        "test_type": "complete_lifecycle",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                
                await websocket.send(json.dumps(thread_creation_message))
                self.logger.info(f"[U+1F4E4] Sent thread creation request for {user_context.thread_id}")
                
                # Wait for thread creation confirmation
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                thread_response = json.loads(response)
                websocket_events.append(thread_response)
                
                assert thread_response["type"] == "thread_created", f"Expected thread_created, got {thread_response['type']}"
                assert thread_response["thread_id"] == str(user_context.thread_id), "Thread ID mismatch in creation response"
                
                self.logger.info(f" PASS:  Thread created successfully: {thread_response['thread_id']}")
                
                # PHASE 2: Send Business-Critical Agent Request
                optimization_request = {
                    "type": "agent_request",
                    "thread_id": str(user_context.thread_id),
                    "run_id": str(user_context.run_id),
                    "agent": "cost_optimizer",
                    "message": "Analyze my cloud infrastructure costs and provide specific optimization recommendations for a $50,000/month AWS environment. Focus on compute, storage, and networking optimization opportunities.",
                    "context": {
                        "monthly_spend": 50000,
                        "infrastructure": "aws",
                        "priority": "cost_optimization",
                        "expected_savings_target": 15  # 15% target savings
                    },
                    "metadata": {
                        "business_criticality": "high",
                        "request_timestamp": datetime.now(timezone.utc).isoformat()
                    }
                }
                
                await websocket.send(json.dumps(optimization_request))
                self.logger.info("[U+1F4E4] Sent cost optimization request to agent")
                
                # PHASE 3: Collect ALL 5 CRITICAL WebSocket Events
                agent_events = []
                event_tracker = {
                    "agent_started": 0,
                    "agent_thinking": 0, 
                    "tool_executing": 0,
                    "tool_completed": 0,
                    "agent_completed": 0
                }
                
                # Wait for agent execution with comprehensive event collection
                timeout_duration = 60.0  # Extended timeout for real LLM processing
                start_agent_time = time.time()
                
                while time.time() - start_agent_time < timeout_duration:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        agent_events.append(event)
                        websocket_events.append(event)
                        
                        event_type = event.get("type")
                        if event_type in event_tracker:
                            event_tracker[event_type] += 1
                            self.logger.info(f"[U+1F4E8] Received {event_type} event ({event_tracker[event_type]})")
                        
                        # Track business value metrics from events
                        if event_type == "agent_thinking":
                            thinking_content = event.get("data", {}).get("content", "")
                            if "cost" in thinking_content.lower() or "optimization" in thinking_content.lower():
                                business_value_metrics["insights_delivered"] += 1
                        
                        elif event_type == "tool_completed":
                            tool_result = event.get("data", {}).get("result", {})
                            if isinstance(tool_result, dict):
                                if "savings" in str(tool_result).lower():
                                    business_value_metrics["cost_savings_identified"] += 1
                        
                        elif event_type == "agent_completed":
                            # Agent execution completed - capture final business value
                            agent_response = event.get("data", {}).get("response", {})
                            if isinstance(agent_response, dict):
                                # Count actionable recommendations
                                response_text = str(agent_response).lower()
                                if "recommend" in response_text:
                                    business_value_metrics["actionable_recommendations"] += response_text.count("recommend")
                            
                            business_value_metrics["agent_response_time"] = time.time() - start_agent_time
                            self.logger.info(f" TARGET:  Agent completed in {business_value_metrics['agent_response_time']:.2f}s")
                            break
                            
                    except asyncio.TimeoutError:
                        self.logger.warning(f"[U+23F0] Event timeout - continuing to wait for completion")
                        continue
                    except json.JSONDecodeError as e:
                        self.logger.warning(f" WARNING: [U+FE0F] JSON decode error: {e}")
                        continue
                
                # CRITICAL VALIDATION: ALL 5 WebSocket Events MUST be present
                missing_events = [event_type for event_type, count in event_tracker.items() if count == 0]
                if missing_events:
                    self.logger.error(f" FAIL:  CRITICAL: Missing required WebSocket events: {missing_events}")
                    self.logger.error(f" CHART:  Event counts: {event_tracker}")
                    raise AssertionError(f"CRITICAL: Missing required WebSocket events: {missing_events}. All 5 events are mandatory for business value delivery!")
                
                self.logger.info(f" PASS:  ALL 5 critical WebSocket events received: {event_tracker}")
                
                # PHASE 4: Validate Business Value Delivery
                total_lifecycle_time = time.time() - start_time
                
                # Business value assertions
                assert business_value_metrics["insights_delivered"] > 0, \
                    "BUSINESS VALUE FAILURE: Agent delivered no cost optimization insights"
                
                assert business_value_metrics["actionable_recommendations"] > 0, \
                    "BUSINESS VALUE FAILURE: Agent provided no actionable recommendations"
                
                assert business_value_metrics["agent_response_time"] is not None, \
                    "BUSINESS VALUE FAILURE: Agent did not complete processing"
                
                assert business_value_metrics["agent_response_time"] < 45.0, \
                    f"PERFORMANCE FAILURE: Agent took {business_value_metrics['agent_response_time']:.2f}s - exceeds 45s SLA"
                
                # PHASE 5: Thread State Persistence Validation
                # Send thread status request to verify persistence
                thread_status_request = {
                    "type": "get_thread_status",
                    "thread_id": str(user_context.thread_id)
                }
                
                await websocket.send(json.dumps(thread_status_request))
                status_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                status_data = json.loads(status_response)
                
                assert status_data["type"] == "thread_status", "Failed to get thread status"
                assert status_data["thread_id"] == str(user_context.thread_id), "Thread ID mismatch in status"
                assert "messages" in status_data["data"], "Thread status missing message history"
                
                # Verify message continuity
                message_count = len(status_data["data"]["messages"])
                assert message_count >= 2, f"Expected at least 2 messages (user + agent), got {message_count}"
                
                self.logger.info(f" PASS:  Thread persistence validated: {message_count} messages preserved")
                
        except Exception as e:
            self.logger.error(f" FAIL:  Complete thread lifecycle test failed: {e}")
            self.logger.error(f" CHART:  WebSocket events collected: {len(websocket_events)}")
            self.logger.error(f"[U+1F4C8] Business value metrics: {business_value_metrics}")
            raise
        
        # SUCCESS METRICS REPORTING
        self.logger.info(" CELEBRATION:  COMPLETE THREAD LIFECYCLE TEST SUCCESS")
        self.logger.info(f"[U+23F1][U+FE0F]  Total lifecycle time: {total_lifecycle_time:.2f}s")
        self.logger.info(f" CHART:  WebSocket events: {len(websocket_events)} total")
        self.logger.info(f" TARGET:  Business insights delivered: {business_value_metrics['insights_delivered']}")
        self.logger.info(f" IDEA:  Actionable recommendations: {business_value_metrics['actionable_recommendations']}")
        self.logger.info(f"[U+1F4B0] Cost savings opportunities identified: {business_value_metrics['cost_savings_identified']}")
        
        # Validate minimum business value thresholds
        assert business_value_metrics["insights_delivered"] >= 1, "Insufficient business insights delivered"
        assert business_value_metrics["actionable_recommendations"] >= 1, "Insufficient actionable recommendations"
        assert total_lifecycle_time < 75.0, f"Thread lifecycle too slow: {total_lifecycle_time:.2f}s"

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_thread_persistence_across_user_session_reconnections(self):
        """
        Test thread state persistence across user session disconnections and reconnections.
        
        Business Value: Users maintain conversation context when they disconnect and reconnect,
        enabling continued AI assistance without losing progress or context.
        """
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email=f"persistence_test_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            websocket_enabled=True
        )
        
        initial_messages = []
        reconnect_messages = []
        
        # SESSION 1: Create thread and add initial messages
        self.logger.info("[U+1F517] SESSION 1: Creating thread with initial messages")
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=15.0
        ) as ws1:
            
            # Send initial message
            initial_message = {
                "type": "send_message",
                "thread_id": str(user_context.thread_id),
                "message": "I need help optimizing my database performance. Currently experiencing slow query times.",
                "role": "user",
                "metadata": {"session": 1, "message_order": 1}
            }
            
            await ws1.send(json.dumps(initial_message))
            response1 = await asyncio.wait_for(ws1.recv(), timeout=10.0)
            initial_messages.append(json.loads(response1))
            
            # Send agent request
            agent_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "database_optimizer",
                "message": "Analyze database performance issues and suggest optimization strategies.",
                "metadata": {"session": 1, "request_type": "performance_analysis"}
            }
            
            await ws1.send(json.dumps(agent_request))
            
            # Collect initial agent response events
            session1_events = []
            while len(session1_events) < 3:  # Collect at least 3 events
                event_data = await asyncio.wait_for(ws1.recv(), timeout=15.0)
                event = json.loads(event_data)
                session1_events.append(event)
                initial_messages.append(event)
                
                if event.get("type") == "agent_completed":
                    break
            
            # Verify initial session received agent response
            assert any(e.get("type") == "agent_completed" for e in session1_events), \
                "Initial session did not receive complete agent response"
            
            self.logger.info(f" PASS:  Session 1 completed with {len(initial_messages)} messages")
        
        # DISCONNECT PERIOD: Simulate user disconnect (WebSocket closed automatically)
        await asyncio.sleep(2.0)  # Brief disconnect period
        self.logger.info("[U+1F50C] Simulated user disconnect and reconnection")
        
        # SESSION 2: Reconnect and verify thread persistence
        self.logger.info("[U+1F517] SESSION 2: Reconnecting and verifying thread persistence")
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url, 
            additional_headers=self.websocket_headers,
            open_timeout=15.0
        ) as ws2:
            
            # Request thread history to verify persistence
            history_request = {
                "type": "get_thread_history",
                "thread_id": str(user_context.thread_id),
                "limit": 50
            }
            
            await ws2.send(json.dumps(history_request))
            history_response = await asyncio.wait_for(ws2.recv(), timeout=10.0)
            history_data = json.loads(history_response)
            
            # Validate thread history preservation
            assert history_data["type"] == "thread_history", "Failed to retrieve thread history"
            assert "messages" in history_data["data"], "Thread history missing messages"
            
            preserved_messages = history_data["data"]["messages"]
            assert len(preserved_messages) >= 2, \
                f"Expected at least 2 preserved messages, got {len(preserved_messages)}"
            
            # Verify message content preservation
            user_message_found = False
            agent_response_found = False
            
            for msg in preserved_messages:
                if "database performance" in str(msg).lower():
                    user_message_found = True
                if "optim" in str(msg).lower():  # Agent response about optimization
                    agent_response_found = True
            
            assert user_message_found, "User's database performance message not preserved"
            assert agent_response_found, "Agent's optimization response not preserved"
            
            # Continue conversation in new session
            followup_message = {
                "type": "send_message", 
                "thread_id": str(user_context.thread_id),
                "message": "Based on your previous recommendations, I implemented indexing. What should I check next?",
                "role": "user",
                "metadata": {"session": 2, "followup": True}
            }
            
            await ws2.send(json.dumps(followup_message))
            followup_response = await asyncio.wait_for(ws2.recv(), timeout=10.0)
            reconnect_messages.append(json.loads(followup_response))
            
            self.logger.info(f" PASS:  Session 2 completed with {len(reconnect_messages)} new messages")
        
        # Business Value Validation
        total_messages = len(initial_messages) + len(reconnect_messages)
        assert total_messages >= 3, f"Insufficient conversation continuity: {total_messages} total messages"
        
        self.logger.info(" CELEBRATION:  THREAD PERSISTENCE TEST SUCCESS")
        self.logger.info(f" CHART:  Session 1 messages: {len(initial_messages)}")
        self.logger.info(f" CHART:  Session 2 messages: {len(reconnect_messages)}")
        self.logger.info(f" IDEA:  Business Value: User maintained conversation context across sessions")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_message_ordering_and_continuity_throughout_lifecycle(self):
        """
        Test message ordering and continuity throughout complete thread lifecycle.
        
        Business Value: Ensures users receive coherent conversation flow and agents have
        proper context to deliver increasingly valuable insights over extended interactions.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"ordering_test_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            websocket_enabled=True
        )
        
        conversation_log = []
        message_sequence = []
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=15.0
        ) as websocket:
            
            # PHASE 1: Initial Problem Statement
            messages = [
                "I'm experiencing high cloud costs in my data pipeline. Current spend is $25,000/month.",
                "The main cost drivers seem to be compute instances running 24/7 for batch processing.",
                "We process about 500GB of data daily with peak loads during business hours.",
                "What specific optimization strategies would you recommend?"
            ]
            
            for i, message_content in enumerate(messages):
                timestamp = datetime.now(timezone.utc).isoformat()
                
                user_message = {
                    "type": "send_message",
                    "thread_id": str(user_context.thread_id),
                    "message": message_content,
                    "role": "user",
                    "metadata": {
                        "sequence": i + 1,
                        "timestamp": timestamp,
                        "phase": "problem_statement"
                    }
                }
                
                await websocket.send(json.dumps(user_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                conversation_log.append({
                    "sequence": i + 1,
                    "type": "user_message",
                    "content": message_content,
                    "timestamp": timestamp,
                    "response": response_data
                })
                
                message_sequence.append(f"user_msg_{i+1}")
                
                # Brief pause between messages for realistic conversation flow
                await asyncio.sleep(1.0)
            
            # PHASE 2: Agent Analysis Request
            analysis_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "cost_optimizer",
                "message": "Based on the information provided, analyze the data pipeline costs and provide specific optimization recommendations with estimated savings.",
                "metadata": {
                    "analysis_type": "comprehensive",
                    "expected_deliverables": ["cost_breakdown", "optimization_plan", "savings_estimate"]
                }
            }
            
            await websocket.send(json.dumps(analysis_request))
            
            # Collect agent analysis with event ordering validation
            agent_events = []
            event_sequence = []
            
            while len(agent_events) < 10:  # Collect comprehensive event sequence
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    agent_events.append(event)
                    
                    event_type = event.get("type")
                    event_sequence.append(event_type)
                    
                    conversation_log.append({
                        "sequence": len(conversation_log) + 1,
                        "type": event_type,
                        "timestamp": event.get("timestamp", datetime.now(timezone.utc).isoformat()),
                        "data": event.get("data", {})
                    })
                    
                    if event_type == "agent_completed":
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            # PHASE 3: Follow-up Questions for Context Continuity
            followup_questions = [
                "How would you prioritize these optimizations by ROI?",
                "What are the implementation risks for the serverless migration?",
                "Can you estimate the timeline for achieving these savings?"
            ]
            
            for j, question in enumerate(followup_questions):
                followup_message = {
                    "type": "send_message",
                    "thread_id": str(user_context.thread_id), 
                    "message": question,
                    "role": "user",
                    "metadata": {
                        "sequence": len(message_sequence) + 1,
                        "phase": "followup",
                        "question_number": j + 1
                    }
                }
                
                await websocket.send(json.dumps(followup_message))
                response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                response_data = json.loads(response)
                
                conversation_log.append({
                    "sequence": len(conversation_log) + 1,
                    "type": "followup_response",
                    "question": question,
                    "response": response_data
                })
                
                message_sequence.append(f"followup_{j+1}")
                await asyncio.sleep(0.5)
        
        # VALIDATION: Message Ordering and Continuity
        
        # Verify conversation log completeness
        assert len(conversation_log) >= 8, \
            f"Insufficient conversation depth: {len(conversation_log)} events"
        
        # Verify event sequence contains critical events in correct order
        assert "agent_started" in event_sequence, "Missing agent_started event"
        assert "agent_completed" in event_sequence, "Missing agent_completed event"
        
        # Validate timestamp ordering
        timestamps = [
            entry.get("timestamp") for entry in conversation_log 
            if entry.get("timestamp")
        ]
        
        # Verify chronological ordering
        for i in range(1, len(timestamps)):
            prev_time = datetime.fromisoformat(timestamps[i-1].replace('Z', '+00:00'))
            curr_time = datetime.fromisoformat(timestamps[i].replace('Z', '+00:00'))
            assert curr_time >= prev_time, \
                f"Message ordering violation at position {i}: {prev_time} -> {curr_time}"
        
        # Verify context continuity in agent responses
        agent_responses = [
            entry for entry in conversation_log 
            if entry.get("type") in ["agent_completed", "followup_response"]
        ]
        
        assert len(agent_responses) >= 2, \
            f"Insufficient agent responses for continuity test: {len(agent_responses)}"
        
        # Business Value: Check for context awareness in responses
        context_references = 0
        for response in agent_responses:
            response_content = str(response.get("data", {})).lower()
            if any(keyword in response_content for keyword in ["previous", "mentioned", "discussed", "pipeline", "batch"]):
                context_references += 1
        
        assert context_references >= 1, \
            "Agent responses show no context continuity - business value compromised"
        
        self.logger.info(" CELEBRATION:  MESSAGE ORDERING AND CONTINUITY TEST SUCCESS")
        self.logger.info(f" CHART:  Total conversation events: {len(conversation_log)}")
        self.logger.info(f"[U+1F517] Message sequence: {' -> '.join(message_sequence[:10])}")
        self.logger.info(f" IDEA:  Context references found: {context_references}")
        self.logger.info(f"[U+23F1][U+FE0F]  Conversation spanned {len(timestamps)} timestamped events")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_agent_execution_context_preservation_within_thread(self):
        """
        Test agent execution context preservation within thread lifecycle.
        
        Business Value: Ensures agents maintain context across multiple interactions within
        a thread, enabling progressively more valuable and personalized recommendations.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"context_test_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            permissions=["read", "write", "agent_execute"],
            websocket_enabled=True
        )
        
        execution_contexts = []
        agent_memory_test = {
            "company_info": None,
            "use_case_details": None,
            "previous_recommendations": None,
            "context_carried_forward": False
        }
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=15.0
        ) as websocket:
            
            # INTERACTION 1: Establish Context
            context_establishment = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "run_id": str(user_context.run_id),
                "agent": "business_advisor",
                "message": "I'm the CTO of a 50-person SaaS company spending $30,000/month on AWS. We're growing 20% monthly and need scalable cost optimization strategies for our microservices architecture.",
                "context": {
                    "company_size": 50,
                    "monthly_aws_spend": 30000,
                    "growth_rate": 0.20,
                    "architecture": "microservices",
                    "role": "CTO"
                },
                "metadata": {"interaction": 1, "purpose": "context_establishment"}
            }
            
            await websocket.send(json.dumps(context_establishment))
            
            # Collect first interaction response
            interaction1_events = []
            while len(interaction1_events) < 5:
                event_data = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                event = json.loads(event_data)
                interaction1_events.append(event)
                
                if event.get("type") == "agent_completed":
                    # Extract context from agent response
                    agent_response = event.get("data", {}).get("response", {})
                    response_text = str(agent_response).lower()
                    
                    if "cto" in response_text and "50" in response_text:
                        agent_memory_test["company_info"] = True
                    if "microservices" in response_text:
                        agent_memory_test["use_case_details"] = True
                    
                    execution_contexts.append({
                        "interaction": 1,
                        "context_recognized": agent_memory_test.copy(),
                        "response_length": len(str(agent_response)),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    break
            
            # Brief pause between interactions
            await asyncio.sleep(2.0)
            
            # INTERACTION 2: Test Context Continuity
            context_followup = {
                "type": "agent_request", 
                "thread_id": str(user_context.thread_id),
                "agent": "business_advisor",
                "message": "Based on your previous analysis, we implemented auto-scaling for our API gateway. What should be our next priority for the database layer optimization?",
                "metadata": {"interaction": 2, "purpose": "context_continuity_test"}
            }
            
            await websocket.send(json.dumps(context_followup))
            
            # Collect second interaction response  
            interaction2_events = []
            while len(interaction2_events) < 5:
                event_data = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                event = json.loads(event_data)
                interaction2_events.append(event)
                
                if event.get("type") == "agent_completed":
                    agent_response = event.get("data", {}).get("response", {})
                    response_text = str(agent_response).lower()
                    
                    # Check if agent references previous context
                    context_indicators = [
                        "previous" in response_text,
                        "mentioned" in response_text,
                        "analysis" in response_text,
                        "api gateway" in response_text,
                        "microservices" in response_text,
                        "30" in response_text and "000" in response_text  # $30,000 reference
                    ]
                    
                    if sum(context_indicators) >= 2:
                        agent_memory_test["context_carried_forward"] = True
                    
                    execution_contexts.append({
                        "interaction": 2,
                        "context_indicators": context_indicators,
                        "context_continuity": agent_memory_test["context_carried_forward"],
                        "response_length": len(str(agent_response)),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    break
            
            # INTERACTION 3: Deep Context Test
            deep_context_test = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "business_advisor", 
                "message": "Given our rapid growth trajectory, how should we modify the optimization strategy you recommended earlier?",
                "metadata": {"interaction": 3, "purpose": "deep_context_validation"}
            }
            
            await websocket.send(json.dumps(deep_context_test))
            
            # Collect third interaction response
            interaction3_events = []
            while len(interaction3_events) < 5:
                event_data = await asyncio.wait_for(websocket.recv(), timeout=20.0)
                event = json.loads(event_data)
                interaction3_events.append(event)
                
                if event.get("type") == "agent_completed":
                    agent_response = event.get("data", {}).get("response", {})
                    response_text = str(agent_response).lower()
                    
                    # Check for deep context understanding
                    deep_context_indicators = [
                        "growth" in response_text,
                        "rapid" in response_text or "20%" in response_text,
                        "strategy" in response_text,
                        "recommended" in response_text or "previous" in response_text
                    ]
                    
                    execution_contexts.append({
                        "interaction": 3,
                        "deep_context_indicators": deep_context_indicators,
                        "context_depth": sum(deep_context_indicators),
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    break
        
        # VALIDATION: Agent Context Preservation
        
        # Verify all interactions completed
        assert len(execution_contexts) == 3, \
            f"Expected 3 completed interactions, got {len(execution_contexts)}"
        
        # Verify context establishment
        assert agent_memory_test["company_info"] or agent_memory_test["use_case_details"], \
            "Agent failed to recognize initial context establishment"
        
        # Verify context continuity
        assert agent_memory_test["context_carried_forward"], \
            "CRITICAL: Agent failed to maintain context across interactions - business value compromised"
        
        # Verify progressive context depth
        if len(execution_contexts) >= 3:
            context_depth = execution_contexts[2].get("context_depth", 0)
            assert context_depth >= 2, \
                f"Insufficient deep context understanding: {context_depth}/4 indicators"
        
        # Business Value: Verify response quality improvement
        response_lengths = [ctx.get("response_length", 0) for ctx in execution_contexts]
        avg_response_length = sum(response_lengths) / len(response_lengths)
        
        assert avg_response_length > 100, \
            f"Agent responses too brief for business value: {avg_response_length} chars average"
        
        self.logger.info(" CELEBRATION:  AGENT CONTEXT PRESERVATION TEST SUCCESS")
        self.logger.info(f" CHART:  Completed interactions: {len(execution_contexts)}")
        self.logger.info(f"[U+1F9E0] Context indicators met: {agent_memory_test}")
        self.logger.info(f"[U+1F4C8] Average response length: {avg_response_length:.0f} characters")
        self.logger.info(f" IDEA:  Business Value: Agent demonstrated memory and context continuity")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    async def test_thread_lifecycle_performance_under_load(self):
        """
        Test thread lifecycle performance under realistic load conditions.
        
        Business Value: Ensures platform can handle realistic user loads while maintaining
        response quality and delivering consistent AI value under pressure.
        """
        # Create multiple concurrent user contexts
        concurrent_users = 3  # Moderate load for staging environment
        user_contexts = []
        
        for i in range(concurrent_users):
            context = await create_authenticated_user_context(
                user_email=f"load_test_{i}_{uuid.uuid4().hex[:6]}@staging.test.com",
                environment="staging",
                websocket_enabled=True
            )
            user_contexts.append(context)
        
        performance_metrics = {
            "thread_creation_times": [],
            "agent_response_times": [],
            "websocket_connection_times": [],
            "concurrent_success_rate": 0,
            "total_events_processed": 0
        }
        
        async def execute_user_thread_lifecycle(user_context: 'StronglyTypedUserExecutionContext', user_index: int):
            """Execute complete thread lifecycle for a single user."""
            try:
                connection_start = time.time()
                
                async with websockets.connect(
                    self.staging_config.urls.websocket_url,
                    additional_headers=self.websocket_headers,
                    open_timeout=20.0  # Extended timeout for load testing
                ) as websocket:
                    
                    connection_time = time.time() - connection_start
                    performance_metrics["websocket_connection_times"].append(connection_time)
                    
                    # Thread creation performance
                    creation_start = time.time()
                    
                    thread_message = {
                        "type": "create_thread",
                        "thread_id": str(user_context.thread_id),
                        "user_id": str(user_context.user_id),
                        "metadata": {"load_test": True, "user_index": user_index}
                    }
                    
                    await websocket.send(json.dumps(thread_message))
                    creation_response = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    
                    creation_time = time.time() - creation_start
                    performance_metrics["thread_creation_times"].append(creation_time)
                    
                    # Agent execution performance
                    agent_start = time.time()
                    
                    optimization_request = {
                        "type": "agent_request",
                        "thread_id": str(user_context.thread_id),
                        "agent": "triage_agent",  # Use lighter agent for load testing
                        "message": f"User {user_index}: Quick analysis of cloud costs for small business with $5,000 monthly spend.",
                        "metadata": {"load_test": True, "priority": "fast_response"}
                    }
                    
                    await websocket.send(json.dumps(optimization_request))
                    
                    # Collect agent events with timeout
                    events_collected = 0
                    agent_completed = False
                    
                    while events_collected < 10 and time.time() - agent_start < 30.0:
                        try:
                            event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            event = json.loads(event_data)
                            events_collected += 1
                            performance_metrics["total_events_processed"] += 1
                            
                            if event.get("type") == "agent_completed":
                                agent_completed = True
                                break
                                
                        except asyncio.TimeoutError:
                            break
                    
                    agent_time = time.time() - agent_start
                    if agent_completed:
                        performance_metrics["agent_response_times"].append(agent_time)
                        return True  # Success
                    else:
                        self.logger.warning(f"User {user_index}: Agent did not complete within timeout")
                        return False
                        
            except Exception as e:
                self.logger.error(f"User {user_index} lifecycle failed: {e}")
                return False
        
        # Execute concurrent thread lifecycles
        self.logger.info(f"[U+1F680] Starting load test with {concurrent_users} concurrent users")
        load_test_start = time.time()
        
        results = await asyncio.gather(*[
            execute_user_thread_lifecycle(context, i) 
            for i, context in enumerate(user_contexts)
        ], return_exceptions=True)
        
        total_load_time = time.time() - load_test_start
        
        # Calculate performance metrics
        successful_users = sum(1 for result in results if result is True)
        performance_metrics["concurrent_success_rate"] = successful_users / concurrent_users
        
        # Performance validation
        assert performance_metrics["concurrent_success_rate"] >= 0.8, \
            f"Load test success rate too low: {performance_metrics['concurrent_success_rate']:.1%}"
        
        if performance_metrics["thread_creation_times"]:
            avg_creation_time = sum(performance_metrics["thread_creation_times"]) / len(performance_metrics["thread_creation_times"])
            assert avg_creation_time < 5.0, \
                f"Thread creation too slow under load: {avg_creation_time:.2f}s average"
        
        if performance_metrics["agent_response_times"]:
            avg_agent_time = sum(performance_metrics["agent_response_times"]) / len(performance_metrics["agent_response_times"])
            assert avg_agent_time < 25.0, \
                f"Agent response too slow under load: {avg_agent_time:.2f}s average"
        
        self.logger.info(" CELEBRATION:  THREAD LIFECYCLE LOAD TEST SUCCESS")
        self.logger.info(f"[U+1F465] Concurrent users: {concurrent_users}")
        self.logger.info(f" PASS:  Success rate: {performance_metrics['concurrent_success_rate']:.1%}")
        self.logger.info(f"[U+23F1][U+FE0F]  Total load test time: {total_load_time:.2f}s")
        self.logger.info(f" CHART:  Events processed: {performance_metrics['total_events_processed']}")
        
        if performance_metrics["thread_creation_times"]:
            self.logger.info(f"[U+1F3D7][U+FE0F]  Avg thread creation: {sum(performance_metrics['thread_creation_times'])/len(performance_metrics['thread_creation_times']):.2f}s")
        
        if performance_metrics["agent_response_times"]:
            self.logger.info(f"[U+1F916] Avg agent response: {sum(performance_metrics['agent_response_times'])/len(performance_metrics['agent_response_times']):.2f}s")

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.real_llm
    async def test_thread_recovery_scenarios_and_error_handling(self):
        """
        Test thread recovery scenarios and error handling throughout lifecycle.
        
        Business Value: Ensures users receive reliable AI assistance even when encountering
        errors, maintaining trust and continuous value delivery.
        """
        user_context = await create_authenticated_user_context(
            user_email=f"recovery_test_{uuid.uuid4().hex[:8]}@staging.test.com",
            environment="staging",
            websocket_enabled=True
        )
        
        recovery_scenarios = []
        error_handling_metrics = {
            "graceful_degradation": 0,
            "error_recovery": 0,
            "user_experience_maintained": 0
        }
        
        async with websockets.connect(
            self.staging_config.urls.websocket_url,
            additional_headers=self.websocket_headers,
            open_timeout=15.0
        ) as websocket:
            
            # SCENARIO 1: Invalid Agent Request Recovery
            self.logger.info("[U+1F527] Testing invalid agent request recovery")
            
            invalid_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "nonexistent_agent",  # Invalid agent
                "message": "Test invalid agent handling",
                "metadata": {"test_scenario": "invalid_agent"}
            }
            
            await websocket.send(json.dumps(invalid_request))
            
            # Expect error handling response
            error_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            error_data = json.loads(error_response)
            
            if error_data.get("type") in ["error", "agent_error"]:
                recovery_scenarios.append({
                    "scenario": "invalid_agent",
                    "error_handled": True,
                    "graceful": "error" in error_data.get("type", "")
                })
                error_handling_metrics["graceful_degradation"] += 1
            
            # SCENARIO 2: Recovery with Valid Request
            self.logger.info("[U+1F527] Testing recovery with valid agent request")
            
            recovery_request = {
                "type": "agent_request",
                "thread_id": str(user_context.thread_id),
                "agent": "triage_agent",  # Valid agent
                "message": "After the previous error, can you help me with basic cost analysis?",
                "metadata": {"test_scenario": "error_recovery"}
            }
            
            await websocket.send(json.dumps(recovery_request))
            
            # Collect recovery response
            recovery_events = []
            recovery_successful = False
            
            while len(recovery_events) < 5:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    recovery_events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        recovery_successful = True
                        error_handling_metrics["error_recovery"] += 1
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            recovery_scenarios.append({
                "scenario": "post_error_recovery",
                "successful": recovery_successful,
                "events_received": len(recovery_events)
            })
            
            # SCENARIO 3: Network Interruption Simulation
            self.logger.info("[U+1F527] Testing network interruption handling")
            
            # Send message and then test rapid succession (stress test)
            stress_messages = [
                {"type": "send_message", "thread_id": str(user_context.thread_id), "message": f"Stress message {i}", "metadata": {"stress_test": i}}
                for i in range(3)
            ]
            
            for msg in stress_messages:
                await websocket.send(json.dumps(msg))
                await asyncio.sleep(0.1)  # Rapid succession
            
            # Verify system handles rapid messages gracefully
            stress_responses = []
            for _ in range(3):
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    stress_responses.append(json.loads(response))
                except asyncio.TimeoutError:
                    break
            
            if len(stress_responses) >= 2:  # At least some responses received
                error_handling_metrics["user_experience_maintained"] += 1
                recovery_scenarios.append({
                    "scenario": "stress_handling",
                    "responses_received": len(stress_responses),
                    "graceful_handling": True
                })
        
        # Validation: Error Handling and Recovery
        
        # Verify at least one recovery scenario succeeded
        successful_scenarios = sum(1 for scenario in recovery_scenarios if scenario.get("successful", False) or scenario.get("graceful_handling", False))
        assert successful_scenarios >= 1, \
            f"No recovery scenarios succeeded: {recovery_scenarios}"
        
        # Verify error handling metrics
        total_error_handling_score = sum(error_handling_metrics.values())
        assert total_error_handling_score >= 2, \
            f"Insufficient error handling capability: {error_handling_metrics}"
        
        # Business Value: Verify user experience maintained despite errors
        assert error_handling_metrics["user_experience_maintained"] >= 1, \
            "User experience not maintained during error scenarios - business value compromised"
        
        self.logger.info(" CELEBRATION:  THREAD RECOVERY AND ERROR HANDLING TEST SUCCESS")
        self.logger.info(f" CHART:  Recovery scenarios tested: {len(recovery_scenarios)}")
        self.logger.info(f" PASS:  Successful scenarios: {successful_scenarios}")
        self.logger.info(f"[U+1F6E1][U+FE0F]  Error handling metrics: {error_handling_metrics}")
        self.logger.info(f" IDEA:  Business Value: Platform maintains reliability during error conditions")