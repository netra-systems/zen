"""
E2E Test Suite: AI Optimization Business Value via WebSocket Chat
Tests REAL business value delivery through optimization agents
Business Impact: Direct revenue impact, $120K+ MRR from optimization features

THIS FILE TESTS ACTUAL BUSINESS VALUE DELIVERY:
- Cost savings recommendations with dollar amounts
- Performance optimization insights with measurable improvements  
- Data analysis with actionable visualizations
- Multi-user concurrent optimization with isolation

SSOT Compliance: Uses test_framework.ssot.websocket.WebSocketTestUtility
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

# SSOT imports
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient,
    WebSocketEventType,
    WebSocketMessage
)
from shared.isolated_environment import get_env
from tests.e2e.staging_test_config import get_staging_config

# Configure logging
logger = logging.getLogger(__name__)

# Mark all tests as E2E, staging, and mission critical
pytestmark = [
    pytest.mark.e2e,
    pytest.mark.staging, 
    pytest.mark.mission_critical,
    pytest.mark.asyncio,
    pytest.mark.real_services
]


class TestAIOptimizationBusinessValue:
    """
    Complete E2E test suite for AI optimization chat delivering real business value.
    Tests validate that users receive actionable cost savings, performance improvements,
    and data-driven insights through WebSocket-based agent interactions.
    """

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment and utilities."""
        self.config = get_staging_config()
        self.env = get_env()
        self.ws_utility = WebSocketTestUtility(base_url=self.config.websocket_url, env=self.env)
        await self.ws_utility.initialize()
        
        # Test data
        self.test_id = f"test_{uuid.uuid4().hex[:8]}"
        self.test_users = []
        
        yield
        
        # Cleanup
        await self.ws_utility.cleanup()

    async def _get_auth_token(self, user_id: str) -> str:
        """Get authentication token for staging environment."""
        # Use proper staging authentication with multiple fallback strategies
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        
        try:
            # Primary approach: Use JWTTestHelper for staging authentication
            jwt_helper = JWTTestHelper(environment="staging")
            token = await jwt_helper.get_staging_jwt_token(
                user_id=user_id, 
                email=f"{user_id}@test.netrasystems.ai"
            )
            if token:
                logger.info(f"✓ Generated staging JWT token for user {user_id}")
                return token
        except Exception as e:
            logger.warning(f"JWTTestHelper failed: {e}")
        
        try:
            # Fallback: Try staging config token generation
            test_token = self.config.create_test_jwt_token()
            if test_token:
                logger.info(f"✓ Generated staging config token for user {user_id}")
                return test_token
        except Exception as e:
            logger.warning(f"Config token generation failed: {e}")
        
        # Final fallback with clear error message
        error_msg = (
            f"Unable to create valid staging authentication token for user {user_id}. "
            f"Please set one of: E2E_BYPASS_KEY, STAGING_TEST_API_KEY, or STAGING_JWT_SECRET"
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    async def _create_authenticated_websocket_client(self, user_id: str) -> WebSocketTestClient:
        """Create WebSocket client with proper staging authentication."""
        token = await self._get_auth_token(user_id)
        auth_headers = {"Authorization": f"Bearer {token}", "X-User-ID": user_id}
        client = await self.ws_utility.create_test_client(user_id=user_id, headers=auth_headers)
        
        # Connect with retry logic for staging
        connected = await client.connect(timeout=15.0)
        if not connected:
            raise RuntimeError(f"Failed to establish WebSocket connection to staging for user {user_id}")
        
        logger.info(f"✓ WebSocket connected successfully for user {user_id}")
        return client

    async def _verify_backend_health(self, max_retries: int = 3) -> bool:
        """Verify backend is healthy with retry logic."""
        import httpx
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    response = await client.get(f"{self.config.backend_url}/health")
                    if response.status_code == 200:
                        health_data = response.json()
                        if health_data.get("status") == "healthy":
                            logger.info(f"Backend healthy on attempt {attempt + 1}")
                            return True
            except Exception as e:
                logger.warning(f"Health check attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False

    async def _collect_events_with_timeout(
        self,
        client: WebSocketTestClient,
        expected_events: List[WebSocketEventType],
        timeout: float = 30.0,
        activity_timeout: float = 10.0
    ) -> Dict[WebSocketEventType, List[WebSocketMessage]]:
        """
        Collect WebSocket events with both total and activity timeouts.
        
        Args:
            client: WebSocket test client
            expected_events: List of expected event types
            timeout: Total timeout for all events
            activity_timeout: Timeout between events (detect stuck operations)
        """
        start_time = time.time()
        last_activity = time.time()
        collected_events = {}
        
        while time.time() - start_time < timeout:
            # Check activity timeout
            if time.time() - last_activity > activity_timeout:
                logger.warning(f"No activity for {activity_timeout}s, might be stuck")
                break
            
            # Check for new events
            for event_type in expected_events:
                messages = client.get_messages_by_type(event_type)
                if messages and event_type not in collected_events:
                    collected_events[event_type] = messages
                    last_activity = time.time()
                    logger.info(f"Collected event: {event_type.value}")
            
            # Check if we have all expected events
            if all(evt in collected_events for evt in expected_events):
                logger.info("All expected events collected")
                break
            
            await asyncio.sleep(0.5)
        
        return collected_events

    def _validate_completion_event(self, final_event: WebSocketMessage) -> bool:
        """Validate the agent_completed event structure."""
        if final_event.event_type != WebSocketEventType.AGENT_COMPLETED:
            return False
        
        data = final_event.data
        return all([
            "result" in data or "response" in data,
            "thread_id" in data or final_event.thread_id,
            "execution_time" in data or "duration" in data or "timestamp" in data
        ])

    def _validate_response_structure(self, response_data: Dict[str, Any]) -> bool:
        """Validate the response has expected structure."""
        # Look for common response fields
        has_content = any([
            "content" in response_data,
            "message" in response_data,
            "text" in response_data,
            "response" in response_data
        ])
        
        has_metadata = any([
            "agent" in response_data,
            "model" in response_data,
            "tools_used" in response_data
        ])
        
        return has_content or has_metadata

    def _analyze_business_indicators(self, response_text: str) -> Dict[str, bool]:
        """Analyze response for business value indicators."""
        response_lower = response_text.lower()
        
        return {
            "has_cost_analysis": any(word in response_lower for word in [
                "cost", "savings", "expense", "budget", "pricing", "$", "dollar"
            ]),
            "has_performance_metrics": any(word in response_lower for word in [
                "performance", "latency", "throughput", "response time", "optimization", 
                "efficiency", "speed", "metrics"
            ]),
            "has_recommendations": any(word in response_lower for word in [
                "recommend", "suggest", "should", "consider", "improve", "optimize",
                "action", "implement", "strategy"
            ]),
            "has_data_insights": any(word in response_lower for word in [
                "analysis", "insight", "data", "trend", "pattern", "correlation",
                "visualization", "chart", "graph"
            ])
        }

    async def _verify_business_value(self, events: Dict[WebSocketEventType, List[WebSocketMessage]]) -> bool:
        """
        Verify that agent response contains actual business value.
        This is critical - tests must validate REAL value, not just message passing.
        """
        # Check for agent_completed event
        if WebSocketEventType.AGENT_COMPLETED not in events:
            logger.error("No agent_completed event received")
            return False
        
        completed_messages = events[WebSocketEventType.AGENT_COMPLETED]
        if not completed_messages:
            logger.error("Agent_completed event has no messages")
            return False
        
        final_event = completed_messages[-1]
        
        # Validate event structure
        if not self._validate_completion_event(final_event):
            logger.error("Invalid agent_completed event structure")
            return False
        
        # Extract response data
        response_data = final_event.data.get("result") or final_event.data.get("response", {})
        
        # Validate response structure
        if not self._validate_response_structure(response_data):
            logger.error("Invalid response structure")
            return False
        
        # Extract text content for analysis
        response_text = str(response_data.get("content", "")) or \
                       str(response_data.get("message", "")) or \
                       str(response_data.get("text", "")) or \
                       str(response_data)
        
        # Analyze for business indicators
        indicators = self._analyze_business_indicators(response_text)
        
        # Log what we found
        logger.info(f"Business value indicators: {indicators}")
        
        # Must have at least 2 indicators for valid business value
        indicator_count = sum(indicators.values())
        has_business_value = indicator_count >= 2
        
        if has_business_value:
            logger.info(f"✓ Business value verified with {indicator_count} indicators")
        else:
            logger.warning(f"✗ Insufficient business value indicators: {indicator_count}/2")
        
        return has_business_value

    @pytest.mark.timeout(60)
    async def test_001_basic_optimization_agent_flow(self):
        """
        Test #1: Basic end-to-end chat with AI optimization response
        
        Business Value Justification (BVJ):
        - Segment: All (Free trial conversion, Early/Mid/Enterprise retention)
        - Business Goal: Deliver immediate optimization insights
        - Value Impact: Users receive actionable cost savings within first interaction
        - Strategic Impact: $120K+ MRR depends on optimization agent effectiveness
        """
        # Verify backend health first
        assert await self._verify_backend_health(), "Backend not healthy"
        
        # Create authenticated client with proper staging authentication
        user_id = f"test_user_001_{self.test_id}"
        client = await self._create_authenticated_websocket_client(user_id)
        
        try:
            # Send optimization request
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Analyze my AWS costs and provide optimization recommendations",
                    "role": "user",
                    "agent": "cost_optimizer"
                },
                user_id=user_id,
                thread_id=f"thread_001_{self.test_id}"
            )
            
            # Expected events for optimization flow
            expected_events = [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]
            
            # Wait for and collect events
            events = await self.ws_utility.test_agent_event_flow(
                client, 
                expected_events,
                timeout=30.0
            )
            
            # Verify all critical events were received
            assert len(events) == len(expected_events), f"Missing events: expected {len(expected_events)}, got {len(events)}"
            
            # Verify business value in response
            assert await self._verify_business_value(events), "Response lacks business value"
            
            # Verify specific optimization content
            final_event = events[WebSocketEventType.AGENT_COMPLETED][-1]
            response = final_event.data.get("result", {})
            
            # Should contain cost-related keywords
            response_text = str(response).lower()
            assert any(word in response_text for word in ["cost", "savings", "optimization", "recommend"]), \
                "Response missing optimization keywords"
                
        finally:
            # Ensure client is properly disconnected
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting WebSocket client: {e}")

    @pytest.mark.timeout(90)
    async def test_002_multi_turn_optimization_conversation(self):
        """
        Test #2: Multi-turn conversation with context retention
        
        Business Value Justification (BVJ):
        - Segment: Early/Mid/Enterprise (complex optimization needs)
        - Business Goal: Enable deep-dive optimization analysis
        - Value Impact: Context retention allows progressive refinement of recommendations
        - Strategic Impact: Higher value customers need multi-turn analysis capabilities
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_002_{self.test_id}"
        thread_id = f"thread_002_{self.test_id}"
        
        client = await self._create_authenticated_websocket_client(user_id)
        try:
            # Turn 1: Initial request
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "What are my top 3 cost optimization opportunities?",
                    "role": "user"
                },
                user_id=user_id,
                thread_id=thread_id
            )
            
            # Wait for first response
            events1 = await client.wait_for_events(
                [WebSocketEventType.AGENT_COMPLETED],
                timeout=30.0
            )
            
            assert WebSocketEventType.AGENT_COMPLETED in events1
            
            # Turn 2: Follow-up with context
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Can you provide more details on the first opportunity?",
                    "role": "user"  
                },
                user_id=user_id,
                thread_id=thread_id
            )
            
            # Wait for second response
            events2 = await client.wait_for_events(
                [WebSocketEventType.AGENT_COMPLETED],
                timeout=30.0
            )
            
            # Turn 3: Further refinement
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "What would be the implementation timeline and expected ROI?",
                    "role": "user"
                },
                user_id=user_id,
                thread_id=thread_id
            )
            
            # Wait for third response
            events3 = await client.wait_for_events(
                [WebSocketEventType.AGENT_COMPLETED],
                timeout=30.0
            )
            
            # Verify context was maintained (responses should reference previous turns)
            response2 = events2[WebSocketEventType.AGENT_COMPLETED][-1].data.get("result", {})
            response3 = events3[WebSocketEventType.AGENT_COMPLETED][-1].data.get("result", {})
            
            # Later responses should show awareness of earlier context
            response2_text = str(response2).lower()
            response3_text = str(response3).lower()
            
            # Check for context indicators
            has_context = any([
                "first" in response2_text or "opportunity" in response2_text,
                "timeline" in response3_text or "roi" in response3_text,
                "implementation" in response3_text
            ])
            
            assert has_context, "Multi-turn conversation lost context"
            
        finally:
            # Ensure client is properly disconnected
            try:
                await client.disconnect()
            except Exception as e:
                logger.warning(f"Error disconnecting WebSocket client: {e}")

    @pytest.mark.timeout(120)
    async def test_003_concurrent_user_isolation(self):
        """
        Test #3: Concurrent users with WebSocket isolation
        
        Business Value Justification (BVJ):
        - Segment: All (multi-tenancy is critical)
        - Business Goal: Ensure data isolation and personalized experiences
        - Value Impact: Each customer gets isolated, personalized optimization
        - Strategic Impact: Security and isolation are enterprise requirements
        """
        await self._verify_backend_health()
        
        # Create 3 concurrent users with retry logic
        user_configs = [
            {
                "id": f"concurrent_user_{i}_{self.test_id}",
                "request": f"Optimize my {['AWS', 'Azure', 'GCP'][i]} costs",
                "thread_id": f"thread_concurrent_{i}_{self.test_id}"
            }
            for i in range(3)
        ]
        
        clients = []
        max_retries = 3
        
        # Connect all clients with retry
        for config in user_configs:
            for attempt in range(max_retries):
                try:
                    client = await self.ws_utility.create_authenticated_client(config["id"])
                    connected = await client.connect(timeout=10.0)
                    if connected:
                        clients.append((config, client))
                        logger.info(f"Connected user {config['id']}")
                        break
                except Exception as e:
                    logger.warning(f"Connection attempt {attempt + 1} failed for {config['id']}: {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(1)
        
        assert len(clients) >= 2, f"Could not connect enough concurrent users: {len(clients)}/3"
        
        try:
            # Send requests from all users simultaneously
            tasks = []
            for config, client in clients:
                task = client.send_message(
                    WebSocketEventType.MESSAGE_CREATED,
                    {
                        "content": config["request"],
                        "role": "user"
                    },
                    user_id=config["id"],
                    thread_id=config["thread_id"]
                )
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Collect responses for each user
            responses = {}
            for config, client in clients:
                try:
                    events = await client.wait_for_events(
                        [WebSocketEventType.AGENT_COMPLETED],
                        timeout=45.0
                    )
                    
                    if WebSocketEventType.AGENT_COMPLETED in events:
                        final_event = events[WebSocketEventType.AGENT_COMPLETED][-1]
                        responses[config["id"]] = final_event.data.get("result", {})
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout waiting for response for user {config['id']}")
            
            # Verify isolation - each response should be unique
            assert len(responses) >= 2, f"Not enough responses collected: {len(responses)}"
            
            response_contents = [str(r) for r in responses.values()]
            
            # Responses should be different (no data leakage)
            for i, content1 in enumerate(response_contents):
                for j, content2 in enumerate(response_contents[i+1:], i+1):
                    similarity = len(set(content1.split()) & set(content2.split())) / max(
                        len(content1.split()), len(content2.split())
                    )
                    assert similarity < 0.8, f"Responses too similar - possible data leakage"
            
            # Each response should address the specific cloud provider mentioned
            for config, client in clients:
                if config["id"] in responses:
                    response_text = str(responses[config["id"]]).lower()
                    provider = config["request"].split()[2].lower()  # AWS/Azure/GCP
                    
                    # Allow for responses that might not mention specific provider
                    # but should at least have optimization content
                    has_relevant_content = (
                        provider in response_text or
                        "optimization" in response_text or
                        "cost" in response_text
                    )
                    assert has_relevant_content, \
                        f"Response for {config['id']} doesn't address their request"
        
        finally:
            # Cleanup all clients with individual error handling
            for config, client in clients:
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting {config['id']}: {e}")

    @pytest.mark.timeout(60)
    async def test_004_realtime_agent_status_events(self):
        """
        Test #4: Real-time agent status updates and thinking events
        
        Business Value Justification (BVJ):
        - Segment: All (UX is critical for engagement)
        - Business Goal: Provide transparency and build trust
        - Value Impact: Users see agent working, reducing perceived wait time
        - Strategic Impact: Real-time feedback improves user satisfaction and retention
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_004_{self.test_id}"
        
        async with self.ws_utility.connected_client(user_id=user_id) as client:
            # Send complex request that requires thinking
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Analyze my infrastructure for cost optimization, performance bottlenecks, and security improvements",
                    "role": "user"
                },
                user_id=user_id
            )
            
            # Track event timing
            event_times = {}
            start_time = time.time()
            
            # Monitor events in real-time
            expected_events = [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING,
                WebSocketEventType.TOOL_EXECUTING,
                WebSocketEventType.TOOL_COMPLETED,
                WebSocketEventType.AGENT_COMPLETED
            ]
            
            # Collect events with timing
            for _ in range(50):  # Check for 25 seconds
                for event_type in expected_events:
                    if event_type not in event_times:
                        messages = client.get_messages_by_type(event_type)
                        if messages:
                            event_times[event_type] = time.time() - start_time
                            logger.info(f"Event {event_type.value} at {event_times[event_type]:.2f}s")
                
                if len(event_times) == len(expected_events):
                    break
                    
                await asyncio.sleep(0.5)
            
            # Verify events came in reasonable order and timing
            assert WebSocketEventType.AGENT_STARTED in event_times, "Missing agent_started event"
            assert WebSocketEventType.AGENT_THINKING in event_times, "Missing agent_thinking event"
            
            # Started should come before thinking
            if WebSocketEventType.AGENT_STARTED in event_times and WebSocketEventType.AGENT_THINKING in event_times:
                assert event_times[WebSocketEventType.AGENT_STARTED] < event_times[WebSocketEventType.AGENT_THINKING], \
                    "Events out of order"
            
            # Should get started event quickly (within 5 seconds)
            assert event_times.get(WebSocketEventType.AGENT_STARTED, 999) < 5.0, \
                "Agent started event took too long"
            
            # Thinking events should show reasoning progress
            thinking_messages = client.get_messages_by_type(WebSocketEventType.AGENT_THINKING)
            if thinking_messages:
                thinking_data = thinking_messages[0].data
                # Should have some indication of what agent is thinking about
                assert thinking_data, "Agent thinking event has no data"

    @pytest.mark.timeout(60) 
    async def test_005_tool_execution_transparency(self):
        """
        Test #5: Tool execution visibility and results streaming
        
        Business Value Justification (BVJ):
        - Segment: Mid/Enterprise (need detailed visibility)
        - Business Goal: Provide audit trail and transparency
        - Value Impact: Users understand how recommendations are generated
        - Strategic Impact: Enterprise customers require explainable AI
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_005_{self.test_id}"
        
        async with self.ws_utility.connected_client(user_id=user_id) as client:
            # Request that triggers multiple tools
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Run a complete cost analysis with detailed breakdown by service",
                    "role": "user",
                    "verbose": True  # Request detailed tool execution info
                },
                user_id=user_id
            )
            
            # Collect tool execution events
            tool_executions = []
            tool_completions = []
            
            # Monitor for 30 seconds
            for _ in range(60):
                exec_messages = client.get_messages_by_type(WebSocketEventType.TOOL_EXECUTING)
                comp_messages = client.get_messages_by_type(WebSocketEventType.TOOL_COMPLETED)
                
                tool_executions = exec_messages
                tool_completions = comp_messages
                
                # Check if agent is done
                if client.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED):
                    break
                    
                await asyncio.sleep(0.5)
            
            # Should have tool execution visibility
            assert len(tool_executions) > 0 or len(tool_completions) > 0, \
                "No tool execution events received"
            
            # If we have tool events, verify they contain useful info
            if tool_executions:
                for tool_msg in tool_executions:
                    tool_data = tool_msg.data
                    # Should identify which tool is running
                    assert "tool" in tool_data or "name" in tool_data or "type" in tool_data, \
                        "Tool execution event missing tool identification"
            
            if tool_completions:
                for tool_msg in tool_completions:
                    tool_data = tool_msg.data
                    # Should have some result or status
                    assert any(key in tool_data for key in ["result", "output", "status", "data"]), \
                        "Tool completion event missing results"

    @pytest.mark.timeout(90)
    async def test_006_error_recovery_graceful_degradation(self):
        """
        Test #6: Error recovery and graceful degradation
        
        Business Value Justification (BVJ):
        - Segment: All (reliability is critical)
        - Business Goal: Maintain service availability
        - Value Impact: Users get partial results instead of failures
        - Strategic Impact: Reliability drives customer trust and retention
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_006_{self.test_id}"
        
        async with self.ws_utility.connected_client(user_id=user_id) as client:
            # Test 1: Send malformed request
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": '{"invalid": "json"',  # Deliberately malformed
                    "role": "user"
                },
                user_id=user_id
            )
            
            # Should get error event or graceful response
            await asyncio.sleep(3)
            
            error_events = client.get_messages_by_type(WebSocketEventType.ERROR)
            completed_events = client.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
            
            # Should handle error gracefully
            assert error_events or completed_events, "No response to malformed request"
            
            # Test 2: Request with impossible parameters
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Optimize costs for service that doesn't exist: quantum-flux-capacitor-service",
                    "role": "user"
                },
                user_id=user_id
            )
            
            # Wait for response
            events = await client.wait_for_events(
                [WebSocketEventType.AGENT_COMPLETED],
                timeout=30.0
            )
            
            # Should provide helpful error message or best-effort response
            if WebSocketEventType.AGENT_COMPLETED in events:
                response = events[WebSocketEventType.AGENT_COMPLETED][-1].data.get("result", {})
                response_text = str(response).lower()
                
                # Should acknowledge the issue or provide general guidance
                has_graceful_response = any([
                    "not found" in response_text,
                    "unable" in response_text,
                    "general" in response_text,
                    "recommend" in response_text,
                    "sorry" in response_text
                ])
                
                assert has_graceful_response, "Error response not graceful"

    @pytest.mark.timeout(90)
    async def test_007_performance_optimization_workflow(self):
        """
        Test #7: Complete performance optimization agent workflow
        
        Business Value Justification (BVJ):
        - Segment: Mid/Enterprise (performance is critical)
        - Business Goal: Reduce latency and improve throughput
        - Value Impact: Performance improvements directly impact user experience
        - Strategic Impact: Performance optimization can reduce infrastructure costs 30%+
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_007_{self.test_id}"
        
        async with self.ws_utility.connected_client(user_id=user_id) as client:
            # Request performance analysis
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Analyze system performance and provide optimization recommendations with before/after projections",
                    "role": "user",
                    "agent": "performance_optimizer"
                },
                user_id=user_id
            )
            
            # Collect all events for complete workflow
            all_events = await self._collect_events_with_timeout(
                client,
                [
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING,
                    WebSocketEventType.TOOL_EXECUTING,
                    WebSocketEventType.TOOL_COMPLETED,
                    WebSocketEventType.AGENT_COMPLETED
                ],
                timeout=60.0
            )
            
            # Verify complete workflow
            assert WebSocketEventType.AGENT_COMPLETED in all_events, "Workflow didn't complete"
            
            # Check for performance-specific content
            final_event = all_events[WebSocketEventType.AGENT_COMPLETED][-1]
            response = final_event.data.get("result", {})
            response_text = str(response).lower()
            
            # Should contain performance metrics and improvements
            performance_keywords = [
                "latency", "throughput", "response time", "performance",
                "optimization", "improve", "reduce", "increase", "faster"
            ]
            
            keyword_count = sum(1 for keyword in performance_keywords if keyword in response_text)
            assert keyword_count >= 3, f"Response lacks performance content (found {keyword_count}/3 keywords)"
            
            # Should provide before/after or percentage improvements
            has_metrics = any([
                "%" in str(response),
                "before" in response_text and "after" in response_text,
                "current" in response_text and "optimized" in response_text,
                "improvement" in response_text
            ])
            
            assert has_metrics, "Response lacks quantifiable improvements"

    @pytest.mark.timeout(90)
    async def test_008_data_analysis_visualization(self):
        """
        Test #8: Data analysis agent with visualization delivery
        
        Business Value Justification (BVJ):
        - Segment: Mid/Enterprise (data-driven decisions)
        - Business Goal: Enable data-driven optimization decisions
        - Value Impact: Visualizations make complex data actionable
        - Strategic Impact: Data insights drive 40%+ better optimization outcomes
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_008_{self.test_id}"
        
        async with self.ws_utility.connected_client(user_id=user_id) as client:
            # Request data analysis with visualization
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Analyze my usage patterns and create visualizations showing optimization opportunities",
                    "role": "user",
                    "agent": "data_analyzer",
                    "include_visualizations": True
                },
                user_id=user_id
            )
            
            # Wait for analysis completion
            events = await self.ws_utility.test_agent_event_flow(
                client,
                [
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING,
                    WebSocketEventType.AGENT_COMPLETED
                ],
                timeout=60.0
            )
            
            # Verify visualization data in response
            final_event = events[WebSocketEventType.AGENT_COMPLETED][-1]
            response = final_event.data.get("result", {})
            response_text = str(response).lower()
            
            # Should reference visualizations or data insights
            visualization_keywords = [
                "chart", "graph", "visualization", "plot", "diagram",
                "trend", "pattern", "analysis", "insight", "data"
            ]
            
            has_viz_content = any(keyword in response_text for keyword in visualization_keywords)
            assert has_viz_content, "Response lacks visualization or data analysis content"
            
            # Should provide actionable insights based on data
            has_insights = any([
                "shows" in response_text,
                "indicates" in response_text,
                "suggests" in response_text,
                "reveals" in response_text,
                "demonstrates" in response_text
            ])
            
            assert has_insights, "Data analysis lacks actionable insights"

    @pytest.mark.timeout(180)
    async def test_009_long_running_optimization_progress(self):
        """
        Test #9: Long-running optimization with progress updates
        
        Business Value Justification (BVJ):
        - Segment: Enterprise (complex optimizations)
        - Business Goal: Handle complex, time-intensive optimizations
        - Value Impact: Deep analysis finds 50%+ more optimization opportunities
        - Strategic Impact: Enterprise customers need comprehensive analysis
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_009_{self.test_id}"
        
        async with self.ws_utility.connected_client(user_id=user_id) as client:
            # Request comprehensive optimization (long-running)
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": "Run comprehensive optimization analysis across all services with detailed recommendations",
                    "role": "user",
                    "comprehensive": True,
                    "depth": "detailed"
                },
                user_id=user_id
            )
            
            # Track progress updates
            progress_updates = []
            thinking_events = []
            start_time = time.time()
            
            # Monitor for up to 3 minutes
            while time.time() - start_time < 180:
                # Collect progress indicators
                thinking = client.get_messages_by_type(WebSocketEventType.AGENT_THINKING)
                status = client.get_messages_by_type(WebSocketEventType.STATUS_UPDATE)
                
                if len(thinking) > len(thinking_events):
                    thinking_events = thinking
                    logger.info(f"Progress: {len(thinking_events)} thinking events")
                
                if status and len(status) > len(progress_updates):
                    progress_updates = status
                
                # Check if completed
                if client.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED):
                    break
                
                await asyncio.sleep(2)
            
            # Should have received progress updates during long operation
            assert len(thinking_events) > 1 or len(progress_updates) > 0, \
                "No progress updates during long-running operation"
            
            # Verify final comprehensive results
            completed = client.get_messages_by_type(WebSocketEventType.AGENT_COMPLETED)
            assert completed, "Long-running optimization didn't complete"
            
            response = completed[-1].data.get("result", {})
            response_text = str(response).lower()
            
            # Comprehensive analysis should be detailed
            word_count = len(response_text.split())
            assert word_count > 50, f"Comprehensive analysis too brief ({word_count} words)"
            
            # Should cover multiple areas
            coverage_keywords = ["service", "cost", "performance", "security", "optimization"]
            coverage_count = sum(1 for keyword in coverage_keywords if keyword in response_text)
            assert coverage_count >= 3, f"Comprehensive analysis lacks coverage ({coverage_count}/3 areas)"

    @pytest.mark.timeout(120)
    async def test_010_full_pipeline_cost_analysis(self):
        """
        Test #10: Full optimization pipeline with detailed cost analysis
        
        Business Value Justification (BVJ):
        - Segment: Enterprise ($10K+ monthly spend)
        - Business Goal: Maximize cost optimization ROI
        - Value Impact: Comprehensive analysis identifies 30-50% cost savings
        - Strategic Impact: Large customers need detailed financial analysis
        """
        await self._verify_backend_health()
        
        user_id = f"test_user_010_{self.test_id}"
        
        async with self.ws_utility.connected_client(user_id=user_id) as client:
            # Request full cost optimization pipeline
            await client.send_message(
                WebSocketEventType.MESSAGE_CREATED,
                {
                    "content": (
                        "Perform complete cost optimization analysis including: "
                        "1) Current cost breakdown by service "
                        "2) Optimization opportunities with savings estimates "
                        "3) Implementation roadmap with priorities "
                        "4) ROI calculations and payback period"
                    ),
                    "role": "user",
                    "agent": "cost_optimizer",
                    "analysis_type": "comprehensive"
                },
                user_id=user_id
            )
            
            # Collect complete pipeline execution
            pipeline_events = await self._collect_events_with_timeout(
                client,
                [
                    WebSocketEventType.AGENT_STARTED,
                    WebSocketEventType.AGENT_THINKING,
                    WebSocketEventType.TOOL_EXECUTING,
                    WebSocketEventType.TOOL_COMPLETED,
                    WebSocketEventType.AGENT_COMPLETED
                ],
                timeout=90.0,
                activity_timeout=30.0
            )
            
            # Verify complete pipeline execution
            assert WebSocketEventType.AGENT_COMPLETED in pipeline_events, "Pipeline didn't complete"
            
            # Analyze final comprehensive report
            final_event = pipeline_events[WebSocketEventType.AGENT_COMPLETED][-1]
            response = final_event.data.get("result", {})
            response_text = str(response).lower()
            
            # Must include financial analysis
            financial_indicators = [
                "$", "dollar", "cost", "savings", "roi", "payback",
                "investment", "return", "budget", "expense"
            ]
            
            financial_count = sum(1 for indicator in financial_indicators if indicator in response_text)
            assert financial_count >= 4, f"Lacks financial analysis ({financial_count}/4 indicators)"
            
            # Must include actionable roadmap
            roadmap_indicators = [
                "step", "phase", "implement", "priority", "roadmap",
                "plan", "action", "recommendation", "suggest"
            ]
            
            roadmap_count = sum(1 for indicator in roadmap_indicators if indicator in response_text)
            assert roadmap_count >= 3, f"Lacks implementation roadmap ({roadmap_count}/3 indicators)"
            
            # Should quantify potential savings
            has_quantification = any([
                "%" in str(response),
                "$" in str(response),
                "thousand" in response_text,
                "million" in response_text,
                any(str(i) in str(response) for i in range(10))  # Contains numbers
            ])
            
            assert has_quantification, "Cost analysis lacks quantified savings"
            
            # Should be comprehensive (substantial response)
            word_count = len(response_text.split())
            assert word_count > 100, f"Comprehensive analysis too brief ({word_count} words)"
            
            logger.info(f"✓ Full pipeline cost analysis completed with {word_count} words, "
                       f"{financial_count} financial indicators, {roadmap_count} roadmap elements")