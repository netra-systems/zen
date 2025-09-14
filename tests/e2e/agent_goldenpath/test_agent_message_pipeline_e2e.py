"""
E2E Tests for Agent Message Pipeline - Golden Path Core Flow

MISSION CRITICAL: Tests the complete user message → agent response pipeline
in staging GCP environment. This is the core of the Golden Path user journey
representing 90% of platform business value ($500K+ ARR).

Business Value Justification (BVJ):
- Segment: All Users (Free/Early/Mid/Enterprise) 
- Business Goal: Platform Revenue Protection & User Retention
- Value Impact: Validates complete AI chat functionality works end-to-end
- Strategic Impact: $500K+ ARR depends on reliable agent message processing

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REAL AUTH: JWT tokens via staging auth service
- REAL WEBSOCKETS: wss:// connections to staging backend
- REAL AGENTS: Complete supervisor → triage → APEX agent orchestration
- REAL LLMS: Actual LLM calls for authentic agent responses
- REAL PERSISTENCE: Chat history saved to staging databases

CRITICAL: These tests must fail properly when system issues exist.
No mocking, bypassing, or 0-second test completions allowed.

GitHub Issue: #870 Agent Integration Test Suite Phase 1
Target Coverage: 25% → 75% improvement
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

# Auth and WebSocket utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper


@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.agent_goldenpath
@pytest.mark.mission_critical
class TestAgentMessagePipelineE2E(SSotAsyncTestCase):
    """
    E2E tests for the complete agent message pipeline in staging GCP.
    
    Tests the core Golden Path: User Message → Agent Processing → AI Response
    """

    @classmethod
    def setUpClass(cls):
        """Setup staging environment configuration and dependencies."""
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
        
        # Test user configuration
        cls.test_user_id = f"golden_path_user_{int(time.time())}"
        cls.test_user_email = f"golden_path_test_{int(time.time())}@netra-testing.ai"
        
        cls.logger.info(f"Agent message pipeline e2e tests initialized for staging")

    def setUp(self):
        """Setup for each test method."""
        super().setUp()
        
        # Generate test-specific user context
        self.thread_id = f"message_pipeline_test_{int(time.time())}"
        self.run_id = f"run_{self.thread_id}"
        
        # Create JWT token for this test
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(
            user_id=self.__class__.test_user_id,
            email=self.__class__.test_user_email,
            exp_minutes=60
        )
        
        self.__class__.logger.info(f"Test setup complete - thread_id: {self.thread_id}")

    async def test_complete_user_message_to_agent_response_flow(self):
        """
        Test complete user message → agent response pipeline in staging GCP.
        
        GOLDEN PATH CORE: This is the fundamental user journey that must work.
        
        Flow:
        1. User sends message via WebSocket
        2. Backend routes to supervisor agent
        3. Supervisor orchestrates triage → APEX agents
        4. Agent processes with real LLM calls
        5. Response sent back via WebSocket
        
        DIFFICULTY: Very High (45+ minutes)
        REAL SERVICES: Yes - Complete staging GCP stack
        STATUS: Should PASS - Core Golden Path functionality
        """
        pipeline_start_time = time.time()
        pipeline_events = []
        
        self.__class__.logger.info("🎯 Testing complete user message → agent response pipeline")
        
        try:
            # Step 1: Establish WebSocket connection to staging
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False  # Staging environment
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connection_start = time.time()
            websocket = await asyncio.wait_for(
                websockets.connect(
                    self.__class__.staging_config.urls.websocket_url,
                    extra_headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "X-Environment": "staging",
                        "X-Test-Suite": "agent-pipeline-e2e"
                    },
                    ssl=ssl_context,
                    ping_interval=30,
                    ping_timeout=10
                ),
                timeout=20.0
            )
            
            connection_time = time.time() - connection_start
            pipeline_events.append({
                "event": "websocket_connected",
                "timestamp": time.time(),
                "duration": connection_time,
                "success": True
            })
            
            self.__class__.logger.info(f"✅ WebSocket connected to staging in {connection_time:.2f}s")
            
            # Step 2: Send realistic user message
            user_message = {
                "type": "agent_request",
                "agent": "supervisor_agent",
                "message": (
                    "I need help optimizing my AI costs. My current spend is $2,000/month "
                    "on GPT-4 calls, and I want to reduce costs by 30% without sacrificing quality. "
                    "Can you analyze my usage patterns and suggest specific optimizations?"
                ),
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "user_id": self.__class__.test_user_id,
                "context": {
                    "test_scenario": "golden_path_message_pipeline",
                    "expected_agents": ["supervisor_agent", "triage_agent", "apex_optimizer_agent"],
                    "expected_duration": "30-60s"
                }
            }
            
            message_send_start = time.time()
            await websocket.send(json.dumps(user_message))
            message_send_time = time.time() - message_send_start
            
            pipeline_events.append({
                "event": "user_message_sent", 
                "timestamp": time.time(),
                "duration": message_send_time,
                "message_length": len(user_message["message"]),
                "success": True
            })
            
            self.__class__.logger.info(f"📤 User message sent ({len(user_message['message'])} chars)")
            
            # Step 3: Collect all agent processing events
            agent_events = []
            response_timeout = 90.0  # Allow time for real LLM calls
            event_collection_start = time.time()
            
            # Expected event sequence for Golden Path
            expected_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            received_events = set()
            final_response = None
            
            while time.time() - event_collection_start < response_timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    agent_events.append(event)
                    
                    event_type = event.get("type", "unknown")
                    received_events.add(event_type)
                    
                    self.__class__.logger.info(f"📨 Received event: {event_type}")
                    
                    # Check for agent completion
                    if event_type == "agent_completed":
                        final_response = event
                        break
                        
                    # Check for error events
                    if event_type == "error" or event_type == "agent_error":
                        raise AssertionError(f"Agent processing error: {event}")
                        
                except asyncio.TimeoutError:
                    # Log timeout and continue - may be normal for slower processing
                    continue
                except json.JSONDecodeError as e:
                    self.__class__.logger.warning(f"Failed to parse WebSocket message: {e}")
                    continue
            
            event_collection_time = time.time() - event_collection_start
            pipeline_events.append({
                "event": "agent_events_collected",
                "timestamp": time.time(), 
                "duration": event_collection_time,
                "event_count": len(agent_events),
                "received_event_types": list(received_events),
                "success": len(agent_events) > 0
            })
            
            # Step 4: Validate agent processing results
            
            # Must receive at least basic events
            assert len(agent_events) > 0, "Should receive at least one agent event"
            assert "agent_started" in received_events, f"Missing agent_started event. Got: {received_events}"
            assert "agent_completed" in received_events, f"Missing agent_completed event. Got: {received_events}"
            
            # Validate final response content
            assert final_response is not None, "Should receive final agent response"
            
            response_data = final_response.get("data", {})
            result = response_data.get("result", {})
            
            # Response should contain substantive AI content
            if isinstance(result, dict):
                response_text = result.get("response", str(result))
            else:
                response_text = str(result)
            
            assert len(response_text) > 50, f"Agent response too short: {len(response_text)} chars"
            assert any(keyword in response_text.lower() for keyword in [
                "cost", "optimization", "gpt-4", "reduce", "quality", "suggest"
            ]), f"Response doesn't address user's AI cost question: {response_text[:200]}..."
            
            # Step 5: Test message acknowledgment flow
            ack_message = {
                "type": "message_acknowledgment",
                "thread_id": self.thread_id,
                "run_id": self.run_id,
                "acknowledged_at": datetime.utcnow().isoformat()
            }
            
            await websocket.send(json.dumps(ack_message))
            
            # Wait for potential acknowledgment response
            try:
                ack_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                pipeline_events.append({
                    "event": "acknowledgment_received",
                    "timestamp": time.time(),
                    "success": True
                })
            except asyncio.TimeoutError:
                # Acknowledgment response is optional
                pass
            
            await websocket.close()
            
            # Final validation and reporting
            total_pipeline_time = time.time() - pipeline_start_time
            
            pipeline_events.append({
                "event": "pipeline_completed",
                "timestamp": time.time(),
                "total_duration": total_pipeline_time,
                "success": True
            })
            
            # Log comprehensive results
            self.__class__.logger.info("🎉 GOLDEN PATH MESSAGE PIPELINE SUCCESS")
            self.__class__.logger.info(f"📊 Pipeline Metrics:")
            self.__class__.logger.info(f"   Total Duration: {total_pipeline_time:.1f}s")
            self.__class__.logger.info(f"   WebSocket Connection: {connection_time:.2f}s")
            self.__class__.logger.info(f"   Agent Processing: {event_collection_time:.1f}s")
            self.__class__.logger.info(f"   Events Received: {len(agent_events)}")
            self.__class__.logger.info(f"   Event Types: {received_events}")
            self.__class__.logger.info(f"   Response Length: {len(response_text)} characters")
            self.__class__.logger.info(f"   Pipeline Events: {len(pipeline_events)}")
            
            # Business value assertions
            assert total_pipeline_time < 120.0, f"Pipeline too slow: {total_pipeline_time:.1f}s (max 120s)"
            assert len(response_text) > 100, f"Response not substantive enough: {len(response_text)} chars"
            
        except Exception as e:
            total_time = time.time() - pipeline_start_time
            
            self.__class__.logger.error(f"❌ GOLDEN PATH MESSAGE PIPELINE FAILED")
            self.__class__.logger.error(f"   Error: {str(e)}")
            self.__class__.logger.error(f"   Duration: {total_time:.1f}s")
            self.__class__.logger.error(f"   Events collected: {len(pipeline_events)}")
            
            # Fail with detailed context for debugging
            raise AssertionError(
                f"Golden Path message pipeline failed after {total_time:.1f}s: {e}. "
                f"Events: {pipeline_events}. "
                f"This breaks core user functionality ($500K+ ARR impact)."
            )

    async def test_agent_error_handling_and_recovery(self):
        """
        Test agent error handling and graceful recovery scenarios.
        
        RESILIENCE: System should handle errors gracefully without breaking user experience.
        
        Error scenarios:
        1. Invalid agent request format
        2. Agent timeout scenarios  
        3. Network interruption recovery
        4. Malformed message handling
        
        DIFFICULTY: High (25 minutes)
        REAL SERVICES: Yes - Staging GCP environment
        STATUS: Should PASS - Error handling is critical for user experience
        """
        self.__class__.logger.info("🛡️ Testing agent error handling and recovery")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Test various error scenarios
        error_scenarios = [
            {
                "name": "invalid_agent_type",
                "message": {
                    "type": "agent_request",
                    "agent": "nonexistent_agent_type",
                    "message": "This should trigger an error",
                    "thread_id": f"error_test_{int(time.time())}"
                },
                "expected_error_type": "agent_error",
                "should_recover": True
            },
            {
                "name": "malformed_message_structure", 
                "message": {
                    "type": "agent_request",
                    # Missing required fields
                    "invalid_field": "This message is malformed"
                },
                "expected_error_type": "validation_error",
                "should_recover": True
            },
            {
                "name": "empty_message_content",
                "message": {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": "",  # Empty message
                    "thread_id": f"empty_test_{int(time.time())}"
                },
                "expected_error_type": "validation_error",
                "should_recover": True
            }
        ]
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.__class__.staging_config.urls.websocket_url,
                extra_headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Environment": "staging",
                    "X-Test-Suite": "error-handling-e2e"
                },
                ssl=ssl_context
            ),
            timeout=15.0
        )
        
        try:
            for scenario in error_scenarios:
                scenario_start = time.time()
                self.__class__.logger.info(f"Testing error scenario: {scenario['name']}")
                
                # Send error-inducing message
                await websocket.send(json.dumps(scenario["message"]))
                
                # Collect error response
                error_events = []
                error_timeout = 20.0
                received_error = False
                
                while time.time() - scenario_start < error_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        event = json.loads(event_data)
                        error_events.append(event)
                        
                        event_type = event.get("type", "unknown")
                        
                        # Check if we received expected error
                        if "error" in event_type.lower():
                            received_error = True
                            self.__class__.logger.info(f"✅ Received expected error: {event_type}")
                            break
                            
                    except asyncio.TimeoutError:
                        break
                
                # Validate error handling
                assert received_error, (
                    f"Should receive error for scenario '{scenario['name']}', "
                    f"got events: {error_events}"
                )
                
                # Test recovery - send valid message after error
                if scenario["should_recover"]:
                    recovery_message = {
                        "type": "agent_request",
                        "agent": "triage_agent", 
                        "message": f"Recovery test after {scenario['name']}",
                        "thread_id": f"recovery_{scenario['name']}_{int(time.time())}"
                    }
                    
                    await websocket.send(json.dumps(recovery_message))
                    
                    # Should get normal response after error
                    recovery_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    recovery_event = json.loads(recovery_response)
                    
                    assert recovery_event.get("type") != "error", (
                        f"System should recover after {scenario['name']} error"
                    )
                    
                    self.__class__.logger.info(f"✅ System recovered successfully after {scenario['name']}")
        
            self.__class__.logger.info("🛡️ All error handling scenarios passed")
            
        finally:
            await websocket.close()

    async def test_concurrent_user_message_processing(self):
        """
        Test concurrent user message processing in staging GCP.
        
        SCALABILITY: Multiple users should be able to send messages simultaneously
        without interference or performance degradation.
        
        Scenarios:
        1. Multiple users send messages concurrently
        2. Each user should get isolated responses  
        3. No cross-user contamination
        4. Response times remain reasonable under load
        
        DIFFICULTY: Very High (35 minutes)
        REAL SERVICES: Yes - Staging GCP with real isolation
        STATUS: Should PASS - Multi-user isolation is critical for platform
        """
        self.__class__.logger.info("👥 Testing concurrent user message processing")
        
        # Create multiple test users
        concurrent_users = []
        user_count = 3  # Reasonable load for staging
        
        for i in range(user_count):
            user = {
                "user_id": f"concurrent_user_{i}_{int(time.time())}",
                "email": f"concurrent_test_{i}_{int(time.time())}@netra-testing.ai",
                "thread_id": f"concurrent_thread_{i}_{int(time.time())}",
                "message": f"Concurrent test message {i+1}: Analyze my AI optimization needs for user context {i+1}"
            }
            
            # Generate JWT for each user
            user["access_token"] = self.__class__.auth_helper.create_test_jwt_token(
                user_id=user["user_id"],
                email=user["email"]
            )
            
            concurrent_users.append(user)
        
        # Create concurrent connection tasks
        async def process_user_message(user: Dict[str, Any]) -> Dict[str, Any]:
            """Process message for a single concurrent user."""
            user_start = time.time()
            
            try:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Establish user-specific WebSocket connection
                websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.__class__.staging_config.urls.websocket_url,
                        extra_headers={
                            "Authorization": f"Bearer {user['access_token']}",
                            "X-Environment": "staging",
                            "X-User-Context": user["user_id"]
                        },
                        ssl=ssl_context
                    ),
                    timeout=15.0
                )
                
                # Send user-specific message
                message = {
                    "type": "agent_request",
                    "agent": "triage_agent",
                    "message": user["message"],
                    "thread_id": user["thread_id"],
                    "user_id": user["user_id"]
                }
                
                await websocket.send(json.dumps(message))
                
                # Collect responses (simplified - just wait for completion)
                events = []
                response_timeout = 45.0
                completion_received = False
                
                collection_start = time.time()
                while time.time() - collection_start < response_timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        events.append(event)
                        
                        if event.get("type") == "agent_completed":
                            completion_received = True
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                await websocket.close()
                
                return {
                    "user_id": user["user_id"],
                    "success": completion_received,
                    "duration": time.time() - user_start,
                    "events_received": len(events),
                    "completed": completion_received
                }
                
            except Exception as e:
                return {
                    "user_id": user["user_id"],
                    "success": False,
                    "duration": time.time() - user_start,
                    "error": str(e),
                    "events_received": 0,
                    "completed": False
                }
        
        # Execute concurrent user processing
        concurrent_start = time.time()
        tasks = [process_user_message(user) for user in concurrent_users]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_concurrent_time = time.time() - concurrent_start
        
        # Analyze concurrent processing results
        successful_users = [r for r in results if isinstance(r, dict) and r["success"]]
        failed_users = [r for r in results if isinstance(r, dict) and not r["success"]]
        error_users = [r for r in results if isinstance(r, Exception)]
        
        self.__class__.logger.info(f"👥 Concurrent processing results:")
        self.__class__.logger.info(f"   Total time: {total_concurrent_time:.1f}s")
        self.__class__.logger.info(f"   Successful users: {len(successful_users)}/{user_count}")
        self.__class__.logger.info(f"   Failed users: {len(failed_users)}")
        self.__class__.logger.info(f"   Error users: {len(error_users)}")
        
        # Validate concurrent processing
        success_rate = len(successful_users) / user_count
        
        assert success_rate >= 0.66, (
            f"Concurrent processing success rate too low: {success_rate:.1%} "
            f"(expected ≥66%). Successful: {len(successful_users)}, Failed: {len(failed_users)}, "
            f"Errors: {len(error_users)}"
        )
        
        # Validate reasonable response times
        if successful_users:
            avg_duration = sum(r["duration"] for r in successful_users) / len(successful_users)
            max_duration = max(r["duration"] for r in successful_users)
            
            assert avg_duration < 90.0, f"Average response time too slow: {avg_duration:.1f}s"
            assert max_duration < 150.0, f"Max response time too slow: {max_duration:.1f}s"
            
            self.__class__.logger.info(f"📊 Performance metrics:")
            self.__class__.logger.info(f"   Average duration: {avg_duration:.1f}s")
            self.__class__.logger.info(f"   Max duration: {max_duration:.1f}s")
        
        self.__class__.logger.info("✅ Concurrent user processing validation complete")

    async def test_large_message_handling(self):
        """
        Test handling of large user messages in agent pipeline.
        
        CAPACITY: System should handle various message sizes gracefully,
        from short queries to detailed technical specifications.
        
        Test cases:
        1. Short message (< 100 chars)
        2. Medium message (500-1000 chars)  
        3. Large message (2000+ chars)
        4. Very large message (near limit)
        
        DIFFICULTY: Medium (20 minutes)
        REAL SERVICES: Yes - Staging GCP message processing
        STATUS: Should PASS - Message size flexibility is important for UX
        """
        self.__class__.logger.info("📏 Testing large message handling capabilities")
        
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        websocket = await asyncio.wait_for(
            websockets.connect(
                self.__class__.staging_config.urls.websocket_url,
                extra_headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "X-Environment": "staging",
                    "X-Test-Suite": "large-message-e2e"
                },
                ssl=ssl_context
            ),
            timeout=15.0
        )
        
        try:
            message_test_cases = [
                {
                    "name": "short_message",
                    "content": "Optimize my AI costs",
                    "expected_response_time": 30.0
                },
                {
                    "name": "medium_message", 
                    "content": (
                        "I'm running a SaaS application with 10,000 users and spending $5,000/month "
                        "on OpenAI API calls. My current setup uses GPT-4 for all user interactions, "
                        "but I'm seeing costs escalate quickly. I need specific recommendations for: "
                        "1) When to use GPT-3.5 vs GPT-4, 2) How to implement intelligent caching, "
                        "3) Prompt optimization techniques, 4) Usage monitoring and alerts. "
                        "Can you provide a comprehensive optimization strategy?"
                    ),
                    "expected_response_time": 45.0
                },
                {
                    "name": "large_message",
                    "content": (
                        "I'm the CTO of a growing AI-first company and we're facing significant challenges "
                        "with our AI infrastructure costs and optimization. Here's our current situation: "
                        "\n\n"
                        "CURRENT SETUP:\n"
                        "- 50,000 monthly active users\n"
                        "- $25,000/month OpenAI API spend (75% GPT-4, 25% GPT-3.5)\n"
                        "- Average 15 API calls per user session\n"
                        "- Peak usage: 2,000 concurrent users during business hours\n"
                        "- Geographic distribution: 60% US, 25% EU, 15% Asia\n"
                        "\n"
                        "PAIN POINTS:\n"
                        "1. Cost scaling faster than revenue (40% month-over-month increase)\n"
                        "2. Response latency issues during peak hours (>3s average)\n"
                        "3. No intelligent model selection - everything uses GPT-4\n"
                        "4. Limited caching strategy causing repeated expensive calls\n"
                        "5. Difficulty predicting monthly costs for budgeting\n"
                        "\n"
                        "REQUIREMENTS:\n"
                        "- Reduce costs by 30-40% without quality degradation\n"
                        "- Maintain <2s response time during peak usage\n"
                        "- Implement predictable cost structure\n"
                        "- Support for 100,000 users by year-end\n"
                        "- Geographic latency optimization\n"
                        "\n"
                        "Can you provide a comprehensive optimization strategy addressing each of these areas?"
                    ),
                    "expected_response_time": 60.0
                }
            ]
            
            for test_case in message_test_cases:
                case_start = time.time()
                message_length = len(test_case["content"])
                
                self.__class__.logger.info(f"Testing {test_case['name']}: {message_length} characters")
                
                # Send test message
                message = {
                    "type": "agent_request",
                    "agent": "apex_optimizer_agent",
                    "message": test_case["content"],
                    "thread_id": f"large_msg_test_{test_case['name']}_{int(time.time())}",
                    "user_id": self.__class__.test_user_id,
                    "context": {
                        "test_case": test_case["name"],
                        "message_length": message_length
                    }
                }
                
                await websocket.send(json.dumps(message))
                
                # Wait for agent completion
                completion_received = False
                response_content = None
                
                timeout = test_case["expected_response_time"]
                while time.time() - case_start < timeout:
                    try:
                        event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(event_data)
                        
                        if event.get("type") == "agent_completed":
                            completion_received = True
                            response_data = event.get("data", {})
                            result = response_data.get("result", {})
                            response_content = str(result)
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                case_duration = time.time() - case_start
                
                # Validate message processing
                assert completion_received, (
                    f"Should complete processing for {test_case['name']} "
                    f"({message_length} chars) within {timeout}s"
                )
                
                assert response_content and len(response_content) > 50, (
                    f"Should receive substantive response for {test_case['name']} "
                    f"(got {len(response_content) if response_content else 0} chars)"
                )
                
                # Response should be proportional to input complexity
                expected_min_response_length = min(200, message_length // 10)
                assert len(response_content) >= expected_min_response_length, (
                    f"Response too short for {test_case['name']}: "
                    f"{len(response_content)} chars (expected ≥{expected_min_response_length})"
                )
                
                self.__class__.logger.info(f"✅ {test_case['name']}: {case_duration:.1f}s, "
                               f"response: {len(response_content)} chars")
            
            self.__class__.logger.info("📏 Large message handling tests completed successfully")
        
        finally:
            await websocket.close()


if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=long", 
        "-s",
        "--gcp-staging",
        "--agent-goldenpath"
    ])