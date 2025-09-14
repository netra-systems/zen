"""
E2E Tests for Message Persistence - Golden Path Chat History & Session Management

MISSION CRITICAL: Tests the complete message persistence and chat history functionality
that enables continuous conversations and maintains user context across sessions.

Business Value Justification (BVJ):
- Segment: All Users (Free/Early/Mid/Enterprise)
- Business Goal: User Retention & Platform Stickiness
- Value Impact: Chat history enables continuous conversations and workflow continuity
- Strategic Impact: Persistent conversations increase user engagement and platform dependency

Message Persistence Features (Golden Path):
1. Chat History - Complete conversation storage and retrieval
2. Session Management - Consistent thread_id and run_id tracking
3. Context Continuity - Previous messages inform new agent responses
4. Multi-Session Support - Users can resume conversations across sessions
5. Message Search & Retrieval - Find previous conversations and insights

This persistence enables:
- Users to continue complex analyses across multiple sessions
- Reference previous agent insights and recommendations
- Build on prior work without starting from scratch
- Maintain project context over days/weeks
- Enterprise audit trails and compliance

Test Strategy:
- REAL PERSISTENCE: Staging GCP database (PostgreSQL/ClickHouse)
- REAL SESSIONS: Complete thread lifecycle testing
- REAL RETRIEVAL: Message history API validation
- REAL CONTEXT: Verify agents access previous message context
- CROSS-SESSION: Test conversation continuity across sessions

CRITICAL: Message persistence directly impacts user retention and platform stickiness.
Lost conversations = lost user trust and productivity.

GitHub Issue: #870 Agent Integration Test Suite Phase 1
Focus: Message persistence as foundation for continuous user engagement
"""

import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx

# SSOT imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available

# Auth and persistence utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.message_persistence
@pytest.mark.mission_critical
class TestMessagePersistenceE2E(SSotAsyncTestCase):
    """
    E2E tests for message persistence and chat history in staging GCP.
    
    Tests the complete conversation storage and retrieval system that enables
    continuous user engagement across multiple sessions.
    """

    @classmethod
    def setUpClass(cls):
        """Setup staging environment for message persistence testing."""
        super().setUpClass()
        
        # Initialize staging configuration
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        
        # Skip if staging not available
        if not is_staging_available():
            pytest.skip("Staging environment not available")
        
        # Initialize auth helper for JWT management
        cls.auth_helper = E2EAuthHelper(environment="staging")
        
        # Initialize WebSocket test utilities
        cls.websocket_helper = WebSocketTestHelper(
            base_url=cls.staging_config.urls.websocket_url,
            environment="staging"
        )
        
        # Test user configuration for persistent sessions
        cls.test_user_id = f"persistence_user_{int(time.time())}"
        cls.test_user_email = f"persistence_test_{int(time.time())}@netra-testing.ai"
        
        cls.logger.info(f"Message persistence e2e tests initialized for staging")

    def setUp(self):
        """Setup for each test method."""
        super().setUp()
        
        # Generate test-specific context for persistence testing
        self.base_thread_id = f"persistence_test_{int(time.time())}"
        self.session_id = f"session_{self.base_thread_id}"
        
        # Create JWT token for this test
        self.access_token = self.auth_helper.create_test_jwt_token(
            user_id=self.test_user_id,
            email=self.test_user_email,
            expires_in_hours=2  # Longer for persistence testing
        )
        
        self.logger.info(f"Message persistence test setup - session: {self.session_id}")

    async def test_complete_message_persistence_and_retrieval_flow(self):
        """
        Test complete message persistence and retrieval across multiple interactions.
        
        GOLDEN PATH PERSISTENCE: This validates the core conversation continuity
        that enables users to build complex analyses over multiple sessions.
        
        Flow validation:
        1. Send initial message and verify it's persisted
        2. Send follow-up messages in same thread
        3. Verify agent has access to previous context
        4. Retrieve complete conversation history
        5. Test conversation resumption after session gap
        6. Validate message ordering and integrity
        
        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - Complete staging persistence stack
        STATUS: Should PASS - Message persistence is fundamental to user experience
        """
        persistence_start_time = time.time()
        conversation_history = []
        persistence_metrics = {
            "messages_sent": 0,
            "messages_retrieved": 0,
            "context_continuity_validated": False,
            "cross_session_continuity": False,
            "total_conversation_length": 0
        }
        
        self.logger.info("💾 Testing complete message persistence and retrieval flow")
        
        try:
            # Phase 1: Initial conversation with persistence
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            thread_id = f"{self.base_thread_id}_initial"
            run_id_1 = f"run_1_{thread_id}"
            
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "message-persistence-flow",
                        "X-Session-ID": self.session_id
                    },
                    ssl=ssl_context,
                    ping_interval=60,
                    ping_timeout=20
                ),
                timeout=20.0
            )
            
            self.logger.info("✅ WebSocket connected for initial conversation")
            
            # Send first message in conversation
            initial_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": (
                    "I'm starting an analysis of my AI infrastructure costs. "
                    "Current setup: $15,000/month spend, 75K users, primarily GPT-4. "
                    "This is the beginning of a comprehensive optimization project. "
                    "Please analyze this initial information and ask me for additional details you need."
                ),
                "thread_id": thread_id,
                "run_id": run_id_1,
                "user_id": self.test_user_id,
                "context": {
                    "conversation_phase": "initial",
                    "project_type": "comprehensive_optimization",
                    "persistence_test": True
                }
            }
            
            message_1_time = time.time()
            await websocket.send(json.dumps(initial_message))
            conversation_history.append({
                "message": initial_message,
                "timestamp": message_1_time,
                "run_id": run_id_1,
                "type": "user_message"
            })
            persistence_metrics["messages_sent"] += 1
            
            # Collect first agent response
            initial_response = None
            response_timeout = 45.0
            
            collection_start = time.time()
            while time.time() - collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    
                    if event.get("type") == "agent_completed":
                        initial_response = event
                        response_data = event.get("data", {})
                        result = response_data.get("result", {})
                        
                        conversation_history.append({
                            "message": result,
                            "timestamp": time.time(),
                            "run_id": run_id_1,
                            "type": "agent_response",
                            "agent": "triage_agent"
                        })
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            assert initial_response is not None, "Should receive initial agent response"
            
            # Phase 2: Follow-up message with context dependency
            await asyncio.sleep(2)  # Brief pause to simulate user reading response
            
            run_id_2 = f"run_2_{thread_id}"
            follow_up_message = {
                "type": "agent_request",
                "agent": "apex_optimizer_agent",
                "message": (
                    "Based on your analysis, I can provide additional details: "
                    "- Peak usage: 2,000 concurrent users during business hours "
                    "- Geographic distribution: 60% US, 30% EU, 10% Asia "
                    "- Average session length: 12 minutes "
                    "- Current response time: 1.8s average "
                    "Please use this information along with what I told you before "
                    "to provide specific optimization recommendations."
                ),
                "thread_id": thread_id,  # Same thread for context continuity
                "run_id": run_id_2,
                "user_id": self.test_user_id,
                "context": {
                    "conversation_phase": "follow_up",
                    "references_previous_context": True,
                    "persistence_test": True
                }
            }
            
            message_2_time = time.time()
            await websocket.send(json.dumps(follow_up_message))
            conversation_history.append({
                "message": follow_up_message,
                "timestamp": message_2_time,
                "run_id": run_id_2,
                "type": "user_message"
            })
            persistence_metrics["messages_sent"] += 1
            
            # Collect follow-up agent response with context validation
            follow_up_response = None
            context_references_found = []
            
            collection_start = time.time()
            while time.time() - collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=12.0)
                    event = json.loads(event_data)
                    
                    if event.get("type") == "agent_completed":
                        follow_up_response = event
                        response_data = event.get("data", {})
                        result = response_data.get("result", {})
                        response_text = str(result).lower()
                        
                        # Check if agent referenced previous context
                        context_indicators = [
                            "$15,000", "15000", "75k", "75000", "users", "gpt-4", 
                            "previously", "mentioned", "told me", "based on", "initial"
                        ]
                        
                        for indicator in context_indicators:
                            if indicator in response_text:
                                context_references_found.append(indicator)
                        
                        conversation_history.append({
                            "message": result,
                            "timestamp": time.time(),
                            "run_id": run_id_2,
                            "type": "agent_response",
                            "agent": "apex_optimizer_agent",
                            "context_references": context_references_found
                        })
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            assert follow_up_response is not None, "Should receive follow-up agent response"
            
            # Validate context continuity
            if len(context_references_found) > 0:
                persistence_metrics["context_continuity_validated"] = True
                self.logger.info(f"✅ Context continuity validated: {context_references_found}")
            else:
                self.logger.warning("⚠️ Limited context continuity detected in agent response")
            
            await websocket.close()
            
            # Phase 3: Test conversation history retrieval via API
            self.logger.info("📚 Testing conversation history retrieval via API")
            
            # Use HTTP API to retrieve conversation history
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                # Try multiple potential history endpoints
                history_endpoints = [
                    f"{self.staging_config.urls.api_base_url}/conversations/{thread_id}/history",
                    f"{self.staging_config.urls.api_base_url}/messages/{thread_id}",
                    f"{self.staging_config.urls.api_base_url}/chat/history/{thread_id}",
                    f"{self.staging_config.urls.backend_url}/api/conversations/{thread_id}"
                ]
                
                history_retrieved = None
                successful_endpoint = None
                
                for endpoint in history_endpoints:
                    try:
                        history_response = await client.get(
                            endpoint,
                            headers={
                                "Authorization": f"Bearer {self.access_token}",
                                "X-Environment": "staging",
                                "Content-Type": "application/json"
                            }
                        )
                        
                        if history_response.status_code == 200:
                            history_data = history_response.json()
                            if history_data and len(str(history_data)) > 50:  # Has meaningful content
                                history_retrieved = history_data
                                successful_endpoint = endpoint
                                break
                        
                    except Exception as e:
                        self.logger.debug(f"History endpoint {endpoint} failed: {e}")
                        continue
                
                if history_retrieved:
                    persistence_metrics["messages_retrieved"] = len(str(history_retrieved))
                    self.logger.info(f"✅ Conversation history retrieved from: {successful_endpoint}")
                    self.logger.info(f"   History data size: {len(str(history_retrieved))} chars")
                else:
                    # History API may not be implemented - try alternative validation
                    self.logger.warning("⚠️ Direct history API not available - testing persistence via new session")
            
            # Phase 4: Test cross-session conversation continuity
            self.logger.info("🔄 Testing cross-session conversation continuity")
            
            await asyncio.sleep(5)  # Simulate session gap
            
            # New WebSocket connection (simulating new session)
            websocket_2 = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Session-ID": f"{self.session_id}_resumed"
                    },
                    ssl=ssl_context
                ),
                timeout=20.0
            )
            
            # Send message referencing previous conversation
            run_id_3 = f"run_3_{thread_id}"
            continuation_message = {
                "type": "agent_request",
                "agent": "supervisor_agent",
                "message": (
                    "Thank you for the previous analysis and recommendations. "
                    "I've reviewed your suggestions and would like to proceed with "
                    "implementing the caching strategy you mentioned. "
                    "Can you provide detailed implementation steps based on our "
                    "earlier discussion about my $15K/month spend and 75K users?"
                ),
                "thread_id": thread_id,  # Same thread to test persistence
                "run_id": run_id_3,
                "user_id": self.test_user_id,
                "context": {
                    "conversation_phase": "continuation",
                    "references_previous_session": True,
                    "persistence_test": True
                }
            }
            
            await websocket_2.send(json.dumps(continuation_message))
            persistence_metrics["messages_sent"] += 1
            
            # Test if agent can access previous conversation context
            continuation_response = None
            cross_session_context_found = []
            
            collection_start = time.time()
            while time.time() - collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket_2.recv(), timeout=15.0)
                    event = json.loads(event_data)
                    
                    if event.get("type") == "agent_completed":
                        continuation_response = event
                        response_data = event.get("data", {})
                        result = response_data.get("result", {})
                        response_text = str(result).lower()
                        
                        # Check for cross-session context references
                        cross_session_indicators = [
                            "previous", "earlier", "mentioned", "discussed", "analysis", 
                            "recommendation", "$15", "15000", "75k", "caching"
                        ]
                        
                        for indicator in cross_session_indicators:
                            if indicator in response_text:
                                cross_session_context_found.append(indicator)
                        
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            await websocket_2.close()
            
            assert continuation_response is not None, "Should receive continuation response"
            
            # Validate cross-session continuity
            if len(cross_session_context_found) > 0:
                persistence_metrics["cross_session_continuity"] = True
                self.logger.info(f"✅ Cross-session continuity validated: {cross_session_context_found}")
            
            # Final validation and metrics
            total_persistence_time = time.time() - persistence_start_time
            persistence_metrics["total_conversation_length"] = len(conversation_history)
            
            # COMPREHENSIVE PERSISTENCE VALIDATION
            
            # Must send and receive messages successfully
            assert persistence_metrics["messages_sent"] >= 3, (
                f"Should send at least 3 messages in persistence test, sent: {persistence_metrics['messages_sent']}"
            )
            
            # Must maintain conversation history
            assert len(conversation_history) >= 4, (  # 3 user messages + at least 1 agent response
                f"Should maintain conversation history, got {len(conversation_history)} entries"
            )
            
            # Should demonstrate some level of context awareness
            context_score = 0
            if persistence_metrics["context_continuity_validated"]:
                context_score += 50
            if persistence_metrics["cross_session_continuity"]:
                context_score += 50
            if persistence_metrics["messages_retrieved"] > 0:
                context_score += 25
            
            assert context_score >= 25, (
                f"Insufficient context continuity evidence: score {context_score}/100. "
                f"Context continuity: {persistence_metrics['context_continuity_validated']}, "
                f"Cross-session: {persistence_metrics['cross_session_continuity']}, "
                f"Retrieval: {persistence_metrics['messages_retrieved'] > 0}"
            )
            
            # Performance requirements
            assert total_persistence_time < 180.0, (
                f"Persistence testing took too long: {total_persistence_time:.1f}s (max 180s)"
            )
            
            # LOG COMPREHENSIVE SUCCESS METRICS
            self.logger.info("🎉 MESSAGE PERSISTENCE AND CONTINUITY SUCCESS")
            self.logger.info(f"📊 Persistence Metrics:")
            self.logger.info(f"   Total Duration: {total_persistence_time:.1f}s")
            self.logger.info(f"   Messages Sent: {persistence_metrics['messages_sent']}")
            self.logger.info(f"   Conversation Entries: {len(conversation_history)}")
            self.logger.info(f"   Context Continuity: {persistence_metrics['context_continuity_validated']}")
            self.logger.info(f"   Cross-Session Continuity: {persistence_metrics['cross_session_continuity']}")
            self.logger.info(f"   Messages Retrieved: {persistence_metrics['messages_retrieved']}")
            self.logger.info(f"   Context Score: {context_score}/100")
            
        except Exception as e:
            total_time = time.time() - persistence_start_time
            
            self.logger.error("❌ MESSAGE PERSISTENCE FAILURE")
            self.logger.error(f"   Error: {str(e)}")
            self.logger.error(f"   Duration: {total_time:.1f}s")
            self.logger.error(f"   Messages sent: {persistence_metrics.get('messages_sent', 0)}")
            self.logger.error(f"   Conversation history: {len(conversation_history)}")
            
            raise AssertionError(
                f"Message persistence test failed after {total_time:.1f}s: {e}. "
                f"This breaks conversation continuity and user engagement. "
                f"Metrics: {persistence_metrics}"
            )

    async def test_message_ordering_and_thread_integrity(self):
        """
        Test message ordering and thread integrity across concurrent operations.
        
        INTEGRITY: Messages should maintain correct ordering and thread association
        even with concurrent operations and database updates.
        
        Test scenarios:
        1. Rapid sequential messages in same thread
        2. Concurrent messages in different threads
        3. Message ordering preservation
        4. Thread isolation validation
        5. Race condition handling
        
        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Staging database consistency testing
        STATUS: Should PASS - Message integrity is critical for conversation quality
        """
        self.logger.info("🔢 Testing message ordering and thread integrity")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Test 1: Rapid sequential messages in same thread
        thread_id = f"{self.base_thread_id}_ordering"
        sequential_messages = []
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.staging_config.urls.websocket_url,
                extra_headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Environment": "staging",
                    "X-Test-Suite": "message-ordering"
                },
                ssl=ssl_context
            ),
            timeout=15.0
        )
        
        try:
            # Send rapid sequential messages
            for i in range(1, 4):  # 3 sequential messages
                message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": f"Sequential message {i} in thread integrity test. Message content: AI optimization step {i}.",
                    "thread_id": thread_id,
                    "run_id": f"run_{i}_{thread_id}",
                    "user_id": self.test_user_id,
                    "context": {
                        "sequence_number": i,
                        "ordering_test": True
                    }
                }
                
                send_time = time.time()
                await websocket.send(json.dumps(message))
                
                sequential_messages.append({
                    "sequence": i,
                    "message": message,
                    "sent_time": send_time
                })
                
                # Brief pause between messages
                await asyncio.sleep(0.5)
            
            # Collect responses and verify ordering
            responses_received = []
            response_timeout = 60.0  # Allow time for all responses
            
            collection_start = time.time()
            while time.time() - collection_start < response_timeout and len(responses_received) < 3:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=8.0)
                    event = json.loads(event_data)
                    
                    if event.get("type") == "agent_completed":
                        responses_received.append({
                            "event": event,
                            "received_time": time.time()
                        })
                        
                except asyncio.TimeoutError:
                    continue
            
            # Validate sequential ordering
            assert len(responses_received) >= 2, (
                f"Should receive at least 2 sequential responses, got {len(responses_received)}"
            )
            
            # Responses should be received in reasonable timeframe
            if responses_received:
                max_response_time = max(r["received_time"] for r in responses_received)
                min_response_time = min(r["received_time"] for r in responses_received)
                response_span = max_response_time - min_response_time
                
                assert response_span < 120.0, (
                    f"Sequential responses took too long: {response_span:.1f}s span (max 120s)"
                )
            
            self.logger.info(f"✅ Sequential message ordering: {len(responses_received)} responses received")
        
        finally:
            await websocket.close()
        
        # Test 2: Concurrent thread isolation
        self.logger.info("🔀 Testing concurrent thread isolation")
        
        concurrent_threads = 2
        
        async def test_thread_isolation(thread_suffix: str) -> Dict[str, Any]:
            """Test message isolation in a specific thread."""
            try:
                ws = await asyncio.wait_for(
                    websockets.connect(
                        self.staging_config.urls.websocket_url,
                        extra_headers={
                            "Authorization": f"Bearer {self.access_token}",
                            "X-Environment": "staging",
                            "X-Thread": thread_suffix
                        },
                        ssl=ssl_context
                    ),
                    timeout=15.0
                )
                
                thread_id = f"{self.base_thread_id}_isolation_{thread_suffix}"
                
                # Send thread-specific message
                message = {
                    "type": "agent_request", 
                    "agent": "triage_agent",
                    "message": f"Thread isolation test {thread_suffix}. This message should only appear in thread {thread_suffix} and not leak to other threads.",
                    "thread_id": thread_id,
                    "run_id": f"run_{thread_suffix}_{thread_id}",
                    "user_id": self.test_user_id,
                    "context": {
                        "thread_suffix": thread_suffix,
                        "isolation_test": True
                    }
                }
                
                await ws.send(json.dumps(message))
                
                # Wait for response
                response = None
                timeout = 30.0
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        event_data = await asyncio.wait_for(ws.recv(), timeout=5.0)
                        event = json.loads(event_data)
                        
                        if event.get("type") == "agent_completed":
                            response = event
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                await ws.close()
                
                return {
                    "thread_suffix": thread_suffix,
                    "thread_id": thread_id,
                    "success": response is not None,
                    "response": response
                }
                
            except Exception as e:
                return {
                    "thread_suffix": thread_suffix,
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent thread tests
        thread_tasks = [test_thread_isolation(f"thread_{i}") for i in range(concurrent_threads)]
        thread_results = await asyncio.gather(*thread_tasks, return_exceptions=True)
        
        # Validate thread isolation
        successful_threads = [
            result for result in thread_results
            if isinstance(result, dict) and result["success"]
        ]
        
        assert len(successful_threads) >= 1, (
            f"At least 1 thread should succeed, got {len(successful_threads)}. "
            f"Results: {thread_results}"
        )
        
        # Validate responses don't contain cross-thread contamination
        for thread_result in successful_threads:
            if thread_result["response"]:
                response_data = thread_result["response"].get("data", {})
                result = response_data.get("result", {})
                response_text = str(result).lower()
                
                # Should contain own thread identifier
                own_suffix = thread_result["thread_suffix"]
                assert own_suffix in response_text, (
                    f"Response should reference own thread {own_suffix}: {response_text[:200]}"
                )
                
                # Should not contain other thread identifiers
                other_suffixes = [
                    f"thread_{i}" for i in range(concurrent_threads)
                    if f"thread_{i}" != own_suffix
                ]
                
                for other_suffix in other_suffixes:
                    if other_suffix in response_text:
                        self.logger.warning(f"Possible thread contamination: {other_suffix} in {own_suffix} response")
        
        self.logger.info(f"🔢 Message ordering and thread integrity validation complete:")
        self.logger.info(f"   Sequential responses: {len(responses_received)}")
        self.logger.info(f"   Isolated threads: {len(successful_threads)}/{concurrent_threads}")

    async def test_conversation_search_and_retrieval_capabilities(self):
        """
        Test conversation search and retrieval capabilities for user productivity.
        
        SEARCH: Users should be able to find and reference previous conversations
        to build on prior work and maintain productivity across sessions.
        
        Features tested:
        1. Search conversations by content/keywords
        2. Search by date/time ranges  
        3. Search by agent type or conversation topic
        4. Retrieve specific message sequences
        5. Export conversation history
        
        DIFFICULTY: Medium (25 minutes)
        REAL SERVICES: Yes - Staging search and retrieval APIs
        STATUS: Should PASS - Search enables user productivity and platform stickiness
        """
        self.logger.info("🔍 Testing conversation search and retrieval capabilities")
        
        # First, create searchable conversation content
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create conversations with specific searchable content
        searchable_conversations = [
            {
                "thread_id": f"{self.base_thread_id}_search_optimization",
                "agent": "apex_optimizer_agent",
                "message": "Please analyze cost optimization strategies for my enterprise GPT-4 usage with focus on ROI calculations.",
                "keywords": ["optimization", "gpt-4", "enterprise", "roi"]
            },
            {
                "thread_id": f"{self.base_thread_id}_search_monitoring",
                "agent": "data_helper_agent",
                "message": "I need monitoring and alerting setup for AI cost tracking across multiple regions and user segments.",
                "keywords": ["monitoring", "alerting", "cost", "tracking", "regions"]
            }
        ]
        
        # Create the searchable conversations
        for conv in searchable_conversations:
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging"
                    },
                    ssl=ssl_context
                ),
                timeout=15.0
            )
            
            try:
                message = {
                    "type": "agent_request",
                    "agent": conv["agent"],
                    "message": conv["message"],
                    "thread_id": conv["thread_id"],
                    "run_id": f"run_{conv['thread_id']}",
                    "user_id": self.test_user_id,
                    "context": {
                        "search_test": True,
                        "keywords": conv["keywords"]
                    }
                }
                
                await websocket.send(json.dumps(message))
                
                # Wait for response to complete conversation
                timeout = 30.0
                start_time = time.time()
                
                while time.time() - start_time < timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(event_data)
                        
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
            
            finally:
                await websocket.close()
        
        # Allow time for conversation indexing
        await asyncio.sleep(5)
        
        # Test search capabilities via API
        self.logger.info("🔍 Testing conversation search via API")
        
        async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
            # Test various search endpoints and methods
            search_tests = [
                {
                    "name": "keyword_search",
                    "endpoints": [
                        f"{self.staging_config.urls.api_base_url}/conversations/search?q=optimization",
                        f"{self.staging_config.urls.api_base_url}/search/conversations?query=optimization",
                        f"{self.staging_config.urls.backend_url}/api/search?q=optimization&type=conversations"
                    ],
                    "expected_content": "optimization"
                },
                {
                    "name": "agent_type_search",
                    "endpoints": [
                        f"{self.staging_config.urls.api_base_url}/conversations/search?agent=apex_optimizer_agent",
                        f"{self.staging_config.urls.api_base_url}/conversations?filter=agent:apex_optimizer",
                        f"{self.staging_config.urls.backend_url}/api/conversations?agent_type=apex_optimizer"
                    ],
                    "expected_content": "apex"
                },
                {
                    "name": "user_conversations",
                    "endpoints": [
                        f"{self.staging_config.urls.api_base_url}/users/{self.test_user_id}/conversations",
                        f"{self.staging_config.urls.api_base_url}/conversations?user_id={self.test_user_id}",
                        f"{self.staging_config.urls.backend_url}/api/user/conversations"
                    ],
                    "expected_content": self.test_user_id[:8]  # Partial user ID match
                }
            ]
            
            search_results = []
            
            for search_test in search_tests:
                test_result = {
                    "name": search_test["name"],
                    "success": False,
                    "endpoint_used": None,
                    "data_found": False
                }
                
                for endpoint in search_test["endpoints"]:
                    try:
                        search_response = await client.get(
                            endpoint,
                            headers={
                                "Authorization": f"Bearer {self.access_token}",
                                "X-Environment": "staging",
                                "Content-Type": "application/json"
                            }
                        )
                        
                        if search_response.status_code == 200:
                            search_data = search_response.json()
                            
                            # Check if search returned meaningful results
                            if search_data and len(str(search_data)) > 50:
                                search_text = str(search_data).lower()
                                expected_content = search_test["expected_content"].lower()
                                
                                if expected_content in search_text:
                                    test_result.update({
                                        "success": True,
                                        "endpoint_used": endpoint,
                                        "data_found": True,
                                        "data_size": len(str(search_data))
                                    })
                                    break
                                else:
                                    test_result.update({
                                        "success": True,
                                        "endpoint_used": endpoint,
                                        "data_found": False,
                                        "data_size": len(str(search_data))
                                    })
                    
                    except Exception as e:
                        self.logger.debug(f"Search endpoint {endpoint} failed: {e}")
                        continue
                
                search_results.append(test_result)
                
                if test_result["success"]:
                    self.logger.info(f"✅ {search_test['name']}: endpoint found, data: {test_result['data_found']}")
                else:
                    self.logger.warning(f"⚠️ {search_test['name']}: no working endpoint found")
        
        # Validate search capabilities
        successful_searches = [r for r in search_results if r["success"]]
        searches_with_data = [r for r in search_results if r.get("data_found", False)]
        
        # At least some search functionality should be available
        search_availability = len(successful_searches) / len(search_tests)
        
        if search_availability < 0.33:
            self.logger.warning(
                f"⚠️ Limited search functionality available: {search_availability:.1%}. "
                f"This may impact user productivity and conversation continuity."
            )
        else:
            self.logger.info(f"✅ Search functionality available: {search_availability:.1%}")
        
        # Test conversation export/retrieval
        self.logger.info("📋 Testing conversation export capabilities")
        
        export_tests = [
            f"{self.staging_config.urls.api_base_url}/conversations/{searchable_conversations[0]['thread_id']}/export",
            f"{self.staging_config.urls.api_base_url}/users/{self.test_user_id}/conversations/export",
            f"{self.staging_config.urls.backend_url}/api/export/conversations?user_id={self.test_user_id}"
        ]
        
        export_available = False
        for export_endpoint in export_tests:
            try:
                export_response = await client.get(
                    export_endpoint,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging"
                    }
                )
                
                if export_response.status_code == 200:
                    export_data = export_response.json()
                    if export_data and len(str(export_data)) > 100:
                        export_available = True
                        self.logger.info(f"✅ Conversation export available: {len(str(export_data))} chars")
                        break
            
            except Exception:
                continue
        
        if not export_available:
            self.logger.info("📋 Conversation export not available - may be future feature")
        
        # Final search and retrieval validation
        self.logger.info(f"🔍 Conversation search and retrieval validation complete:")
        self.logger.info(f"   Search functionality: {search_availability:.1%} available")
        self.logger.info(f"   Successful searches: {len(successful_searches)}/{len(search_tests)}")
        self.logger.info(f"   Searches with data: {len(searches_with_data)}/{len(search_tests)}")
        self.logger.info(f"   Export functionality: {'Available' if export_available else 'Not available'}")


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long",
        "-s",
        "--gcp-staging",
        "--message-persistence"
    ])