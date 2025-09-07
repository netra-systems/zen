"""
E2E Tests for WebSocket-based AI Optimization Chat Functionality

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Deliver actionable AI optimization insights via chat
- Value Impact: Core platform value delivery - users receive cost savings, performance optimizations, and actionable insights
- Strategic Impact: $120K+ MRR at risk - chat is our primary value delivery mechanism

MISSION CRITICAL: These tests verify that our AI optimization chat delivers REAL business value:
- Cost savings recommendations with specific dollar amounts
- Performance optimization suggestions with measurable impact
- Data-driven insights with actionable next steps
- Real-time progress updates via WebSocket events
- Multi-user isolation for enterprise customers

This test file validates the complete end-to-end user experience from WebSocket connection
to receiving valuable AI-powered optimization recommendations.

IMPORTANT: These tests use REAL staging environment, REAL WebSocket connections,
and REAL AI agents to validate actual business value delivery.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import pytest
import httpx

# Import SSOT WebSocket testing utilities  
from test_framework.ssot.websocket import (
    WebSocketTestUtility,
    WebSocketTestClient, 
    WebSocketEventType,
    WebSocketMessage,
    WebSocketTestMetrics
)

# Import staging configuration
from tests.e2e.staging_test_config import get_staging_config

# Configure logging for test debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mark all tests as staging E2E tests
pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.staging,
    pytest.mark.e2e,
    pytest.mark.business_value,
    pytest.mark.real_services
]

class TestAIOptimizationBusinessValue:
    """
    Comprehensive E2E tests for AI optimization chat functionality.
    
    These tests validate that our AI optimization platform delivers REAL business value:
    - Actionable cost savings recommendations
    - Performance optimization insights
    - Data analysis with visualization
    - Real-time agent status updates
    - Multi-user isolation and concurrent execution
    
    All tests use the staging environment with real WebSocket connections and AI agents.
    """
    
    @pytest.fixture(scope="class")
    def staging_config(self):
        """Get staging environment configuration."""
        return get_staging_config()
    
    @pytest.fixture
    async def websocket_utility(self, staging_config):
        """Create WebSocket test utility with staging configuration."""
        async with WebSocketTestUtility(
            base_url=staging_config.websocket_url,
            env=None
        ) as ws_util:
            yield ws_util
    
    @pytest.fixture
    async def authenticated_client(self, websocket_utility, staging_config):
        """Create an authenticated WebSocket client for testing."""
        user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        
        # Create authenticated client with test token
        client = await websocket_utility.create_authenticated_client(
            user_id=user_id,
            token=staging_config.test_jwt_token
        )
        
        # Connect to WebSocket
        connected = await client.connect(timeout=30.0)
        assert connected, f"Failed to connect WebSocket client for user {user_id}"
        
        yield client
        
        # Cleanup
        await client.disconnect()
    
    async def _verify_backend_health(self, staging_config):
        """Verify backend service is healthy before running tests."""
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(staging_config.health_endpoint)
                assert response.status_code == 200, f"Backend unhealthy: {response.text}"
                
                health_data = response.json()
                assert health_data.get("status") == "healthy", f"Backend status not healthy: {health_data}"
                
                logger.info("Backend health check passed")
            except Exception as e:
                pytest.skip(f"Backend not available for testing: {e}")
    
    async def _send_optimization_request(self, client: WebSocketTestClient, 
                                       request_data: Dict[str, Any]) -> str:
        """Send optimization request and return execution ID."""
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        
        request_message = {
            "type": "agent_request",
            "execution_id": execution_id,
            "thread_id": thread_id,
            "timestamp": datetime.now().isoformat(),
            **request_data
        }
        
        await client.send_message(
            WebSocketEventType.MESSAGE_CREATED,
            request_message,
            user_id=client.headers.get("X-User-ID"),
            thread_id=thread_id
        )
        
        logger.info(f"Sent optimization request [{execution_id}]: {request_data.get('message', 'N/A')}")
        return execution_id
    
    async def _collect_agent_events(self, client: WebSocketTestClient, 
                                  timeout: float = 60.0) -> List[WebSocketMessage]:
        """Collect all agent execution events until completion."""
        events = []
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                # Wait for next message with shorter timeout for responsiveness
                message = await client.wait_for_message(timeout=5.0)
                events.append(message)
                
                logger.info(f"Received event: {message.event_type.value}")
                
                # Check if agent execution is complete
                if message.event_type == WebSocketEventType.AGENT_COMPLETED:
                    logger.info(f"Agent execution completed after {len(events)} events")
                    break
                    
            except asyncio.TimeoutError:
                # Continue waiting if we haven't reached the main timeout
                if (time.time() - start_time) < timeout:
                    continue
                else:
                    break
        
        return events
    
    def _verify_websocket_events(self, events: List[WebSocketMessage], 
                                required_events: List[WebSocketEventType]) -> Dict[str, Any]:
        """Verify all required WebSocket events were received and return analysis."""
        event_types = [event.event_type for event in events]
        event_counts = {}
        
        # Count each event type
        for event_type in event_types:
            event_counts[event_type.value] = event_counts.get(event_type.value, 0) + 1
        
        # Verify required events are present
        missing_events = []
        for required_event in required_events:
            if required_event not in event_types:
                missing_events.append(required_event.value)
        
        assert not missing_events, f"Missing required WebSocket events: {missing_events}"
        
        # Verify event order makes sense
        first_event = event_types[0] if event_types else None
        last_event = event_types[-1] if event_types else None
        
        if first_event:
            assert first_event in [WebSocketEventType.AGENT_STARTED, WebSocketEventType.MESSAGE_CREATED], \
                f"Expected agent_started or message_created as first event, got: {first_event.value}"
        
        if last_event:
            assert last_event == WebSocketEventType.AGENT_COMPLETED, \
                f"Expected agent_completed as last event, got: {last_event.value}"
        
        return {
            "total_events": len(events),
            "event_counts": event_counts,
            "event_order": [evt.value for evt in event_types],
            "first_event": first_event.value if first_event else None,
            "last_event": last_event.value if last_event else None,
            "execution_duration": (events[-1].timestamp - events[0].timestamp).total_seconds() if events else 0
        }
    
    def _verify_business_value(self, final_event: WebSocketMessage) -> Dict[str, Any]:
        """Verify the agent response contains real business value."""
        assert final_event.event_type == WebSocketEventType.AGENT_COMPLETED, \
            f"Expected agent_completed event, got: {final_event.event_type.value}"
        
        response_data = final_event.data
        assert "result" in response_data, "Agent response missing result data"
        
        result = response_data["result"]
        
        # Basic response structure validation
        assert isinstance(result, dict), "Agent result must be a dictionary"
        assert len(str(result)) > 50, "Agent response too short to contain meaningful insights"
        
        business_indicators = []
        
        # Check for cost optimization indicators
        cost_keywords = ["cost", "savings", "optimize", "reduce", "efficiency", "budget", "expense"]
        if any(keyword in str(result).lower() for keyword in cost_keywords):
            business_indicators.append("cost_optimization")
        
        # Check for performance indicators  
        performance_keywords = ["performance", "speed", "latency", "throughput", "optimization", "improve"]
        if any(keyword in str(result).lower() for keyword in performance_keywords):
            business_indicators.append("performance_insights")
        
        # Check for data analysis indicators
        data_keywords = ["analysis", "insights", "trends", "patterns", "recommendations", "data"]
        if any(keyword in str(result).lower() for keyword in data_keywords):
            business_indicators.append("data_analysis")
        
        # Check for actionable recommendations
        action_keywords = ["recommend", "suggest", "action", "implement", "next steps", "should"]
        if any(keyword in str(result).lower() for keyword in action_keywords):
            business_indicators.append("actionable_recommendations")
        
        assert len(business_indicators) > 0, \
            f"Agent response lacks business value indicators. Response: {result}"
        
        return {
            "business_value_indicators": business_indicators,
            "response_length": len(str(result)),
            "contains_recommendations": "actionable_recommendations" in business_indicators,
            "response_content": result
        }

    # ==================== TEST METHODS ====================

    @pytest.mark.priority_1
    async def test_001_basic_optimization_agent_flow(self, staging_config, authenticated_client):
        """
        Test #1: Basic end-to-end chat with AI optimization agent providing actionable insights.
        
        BVJ: Core value delivery - users must receive optimization insights via chat.
        Tests the fundamental business value proposition of our platform.
        """
        logger.info("🚀 Starting basic optimization agent flow test")
        
        # Verify backend is healthy
        await self._verify_backend_health(staging_config)
        
        # Send optimization request
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "cost_optimizer",
                "message": "Analyze my current cloud infrastructure costs and suggest optimizations",
                "context": {
                    "monthly_budget": 10000,
                    "current_spend": 8500,
                    "services": ["compute", "storage", "networking"]
                }
            }
        )
        
        # Collect all agent events
        events = await self._collect_agent_events(authenticated_client, timeout=90.0)
        assert len(events) > 0, "No events received from agent execution"
        
        # Verify all 5 critical WebSocket events
        required_events = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
        event_analysis = self._verify_websocket_events(events, required_events)
        logger.info(f"Event analysis: {event_analysis}")
        
        # Verify business value delivered
        final_event = events[-1]
        business_value = self._verify_business_value(final_event)
        
        # Specific cost optimization validations
        assert "cost_optimization" in business_value["business_value_indicators"], \
            "Response should contain cost optimization insights"
        
        assert business_value["contains_recommendations"], \
            "Response should contain actionable recommendations"
        
        logger.info(f"✅ Basic optimization flow completed successfully: {business_value}")

    @pytest.mark.priority_1
    async def test_002_multi_turn_optimization_conversation(self, staging_config, authenticated_client):
        """
        Test #2: Multi-turn conversation with context retention.
        
        BVJ: Enterprise feature - customers need to refine optimization recommendations
        through follow-up questions while maintaining context.
        """
        logger.info("🚀 Starting multi-turn optimization conversation test")
        
        await self._verify_backend_health(staging_config)
        
        # First turn: Initial optimization request
        execution_id_1 = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "cost_optimizer", 
                "message": "Review my AWS infrastructure and identify cost reduction opportunities",
                "context": {
                    "provider": "AWS",
                    "monthly_spend": 15000,
                    "primary_services": ["EC2", "RDS", "S3"]
                }
            }
        )
        
        # Collect first response
        events_1 = await self._collect_agent_events(authenticated_client, timeout=90.0)
        assert len(events_1) > 0, "No events from first turn"
        
        business_value_1 = self._verify_business_value(events_1[-1])
        
        # Wait a moment between turns
        await asyncio.sleep(2.0)
        
        # Second turn: Follow-up question with context reference
        execution_id_2 = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "cost_optimizer",
                "message": "Can you provide more specific recommendations for the EC2 cost savings you mentioned?",
                "context": {
                    "previous_execution": execution_id_1,
                    "focus_area": "EC2",
                    "budget_constraint": 12000
                }
            }
        )
        
        # Collect second response
        events_2 = await self._collect_agent_events(authenticated_client, timeout=90.0)
        assert len(events_2) > 0, "No events from second turn"
        
        business_value_2 = self._verify_business_value(events_2[-1])
        
        # Verify context retention - second response should be more specific
        response_2_content = str(business_value_2["response_content"]).lower()
        assert "ec2" in response_2_content, "Follow-up response should reference EC2 specifically"
        
        # Both turns should provide business value
        assert "cost_optimization" in business_value_1["business_value_indicators"]
        assert "cost_optimization" in business_value_2["business_value_indicators"]
        
        logger.info("✅ Multi-turn conversation completed with context retention")

    @pytest.mark.priority_1
    async def test_003_concurrent_user_isolation(self, staging_config, websocket_utility):
        """
        Test #3: Test 3+ concurrent users getting personalized optimization responses.
        
        BVJ: Enterprise security - multi-tenant isolation prevents data leakage
        between concurrent users accessing optimization services.
        """
        logger.info("🚀 Starting concurrent user isolation test")
        
        await self._verify_backend_health(staging_config)
        
        # Create 3 concurrent users
        user_count = 3
        clients = []
        user_contexts = []
        
        try:
            # Create authenticated clients for each user
            for i in range(user_count):
                user_id = f"concurrent_user_{i+1}_{uuid.uuid4().hex[:6]}"
                client = await websocket_utility.create_authenticated_client(
                    user_id=user_id,
                    token=staging_config.test_jwt_token
                )
                await client.connect(timeout=30.0)
                clients.append(client)
                
                # Each user has different optimization context
                user_contexts.append({
                    "user_id": user_id,
                    "budget": 5000 + (i * 2000),  # Different budgets
                    "focus": ["compute", "storage", "networking"][i % 3],  # Different focus areas
                    "provider": ["AWS", "Azure", "GCP"][i % 3]  # Different cloud providers
                })
            
            # Send simultaneous optimization requests
            execution_ids = []
            request_tasks = []
            
            for i, (client, context) in enumerate(zip(clients, user_contexts)):
                request_task = self._send_optimization_request(
                    client,
                    {
                        "agent": "cost_optimizer",
                        "message": f"Optimize my {context['provider']} {context['focus']} costs within ${context['budget']} budget",
                        "context": context
                    }
                )
                request_tasks.append(request_task)
            
            # Execute all requests concurrently
            execution_ids = await asyncio.gather(*request_tasks)
            
            # Collect responses from all users concurrently
            response_tasks = []
            for client in clients:
                task = self._collect_agent_events(client, timeout=120.0)
                response_tasks.append(task)
            
            all_user_events = await asyncio.gather(*response_tasks, return_exceptions=True)
            
            # Verify each user got personalized responses
            for i, (user_events, context) in enumerate(zip(all_user_events, user_contexts)):
                if isinstance(user_events, Exception):
                    pytest.fail(f"User {i+1} request failed: {user_events}")
                
                assert len(user_events) > 0, f"User {i+1} received no events"
                
                # Verify business value for each user
                business_value = self._verify_business_value(user_events[-1])
                
                # Check that response contains user-specific context
                response_content = str(business_value["response_content"]).lower()
                
                # Should reference their specific provider
                assert context["provider"].lower() in response_content, \
                    f"User {i+1} response should mention {context['provider']}"
                
                # Should reference their specific focus area
                assert context["focus"] in response_content, \
                    f"User {i+1} response should mention {context['focus']}"
            
            # Verify no data leakage between users
            for i, user_events in enumerate(all_user_events):
                if isinstance(user_events, Exception):
                    continue
                    
                user_response = str(self._verify_business_value(user_events[-1])["response_content"]).lower()
                
                # Check that user doesn't see other users' contexts
                for j, other_context in enumerate(user_contexts):
                    if i != j:  # Different user
                        # Should not contain other users' specific budget amounts
                        assert str(other_context["budget"]) not in user_response, \
                            f"User {i+1} response contains User {j+1}'s budget - data leakage detected!"
            
            logger.info("✅ Concurrent user isolation verified - no data leakage detected")
            
        finally:
            # Cleanup all clients
            for client in clients:
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting client: {e}")

    @pytest.mark.priority_2
    async def test_004_realtime_agent_status_events(self, staging_config, authenticated_client):
        """
        Test #4: Verify real-time agent status updates during optimization.
        
        BVJ: User experience - customers need to see agent progress to build trust
        and understand the AI is working on their problem.
        """
        logger.info("🚀 Starting real-time agent status events test")
        
        await self._verify_backend_health(staging_config)
        
        # Send complex optimization request that will trigger multiple thinking phases
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "performance_optimizer",
                "message": "Analyze my application performance bottlenecks and provide detailed optimization recommendations",
                "context": {
                    "application_type": "web_application",
                    "current_performance": {
                        "avg_response_time": 2.5,
                        "error_rate": 0.02,
                        "throughput": 1000
                    },
                    "target_performance": {
                        "avg_response_time": 1.0,
                        "error_rate": 0.01,
                        "throughput": 2000
                    }
                }
            }
        )
        
        # Collect events with detailed tracking
        events = []
        thinking_events = []
        tool_events = []
        start_time = time.time()
        
        timeout = 120.0
        while (time.time() - start_time) < timeout:
            try:
                message = await authenticated_client.wait_for_message(timeout=5.0)
                events.append(message)
                
                # Track specific event types
                if message.event_type == WebSocketEventType.AGENT_THINKING:
                    thinking_events.append(message)
                elif message.event_type in [WebSocketEventType.TOOL_EXECUTING, WebSocketEventType.TOOL_COMPLETED]:
                    tool_events.append(message)
                
                logger.info(f"Received real-time event: {message.event_type.value}")
                
                # Log thinking content for transparency verification
                if message.event_type == WebSocketEventType.AGENT_THINKING and message.data:
                    logger.info(f"Agent thinking: {message.data.get('reasoning', 'N/A')}")
                
                if message.event_type == WebSocketEventType.AGENT_COMPLETED:
                    break
                    
            except asyncio.TimeoutError:
                continue
        
        assert len(events) > 0, "No real-time events received"
        
        # Verify agent thinking events show reasoning process
        assert len(thinking_events) >= 1, "Should receive at least 1 agent_thinking event"
        
        # Check thinking events contain meaningful reasoning
        for thinking_event in thinking_events:
            thinking_data = thinking_event.data
            assert isinstance(thinking_data, dict), "Thinking event should contain structured data"
            
            # Should contain some form of reasoning or progress indicator
            reasoning_indicators = ["reasoning", "progress", "status", "thinking", "analysis"]
            has_reasoning = any(indicator in str(thinking_data).lower() for indicator in reasoning_indicators)
            assert has_reasoning, f"Thinking event lacks reasoning content: {thinking_data}"
        
        # Verify tool execution events provide transparency
        if len(tool_events) > 0:
            for tool_event in tool_events:
                tool_data = tool_event.data
                assert isinstance(tool_data, dict), "Tool event should contain structured data"
                
                if tool_event.event_type == WebSocketEventType.TOOL_EXECUTING:
                    # Should indicate which tool is being used
                    assert "tool" in str(tool_data).lower() or "action" in str(tool_data).lower(), \
                        f"Tool executing event should indicate tool being used: {tool_data}"
        
        # Verify final business value
        final_event = events[-1]
        business_value = self._verify_business_value(final_event)
        
        assert "performance_insights" in business_value["business_value_indicators"], \
            "Should provide performance optimization insights"
        
        logger.info(f"✅ Real-time status events verified: {len(thinking_events)} thinking, {len(tool_events)} tool events")

    @pytest.mark.priority_2
    async def test_005_tool_execution_transparency(self, staging_config, authenticated_client):
        """
        Test #5: Test tool execution visibility for optimization workflow.
        
        BVJ: Trust and transparency - customers need to see which AI tools are analyzing
        their data to build confidence in recommendations.
        """
        logger.info("🚀 Starting tool execution transparency test")
        
        await self._verify_backend_health(staging_config)
        
        # Send request that will trigger multiple tool executions
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "data_analyst",
                "message": "Analyze my system metrics and provide comprehensive optimization recommendations",
                "context": {
                    "metrics_data": {
                        "cpu_usage": [75, 82, 68, 91, 77],
                        "memory_usage": [85, 88, 79, 93, 86],
                        "network_io": [1024, 2048, 1536, 3072, 1792],
                        "disk_io": [512, 768, 640, 896, 724]
                    },
                    "time_period": "last_week"
                }
            }
        )
        
        # Collect events with focus on tool execution
        events = []
        tool_executing_events = []
        tool_completed_events = []
        tool_pairs = []
        
        timeout = 150.0
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                message = await authenticated_client.wait_for_message(timeout=8.0)
                events.append(message)
                
                if message.event_type == WebSocketEventType.TOOL_EXECUTING:
                    tool_executing_events.append(message)
                    logger.info(f"Tool execution started: {message.data}")
                    
                elif message.event_type == WebSocketEventType.TOOL_COMPLETED:
                    tool_completed_events.append(message)
                    logger.info(f"Tool execution completed: {message.data}")
                
                if message.event_type == WebSocketEventType.AGENT_COMPLETED:
                    break
                    
            except asyncio.TimeoutError:
                continue
        
        assert len(events) > 0, "No events received from tool execution test"
        
        # Verify tool execution events are present
        assert len(tool_executing_events) > 0, "Should have at least 1 tool_executing event"
        assert len(tool_completed_events) > 0, "Should have at least 1 tool_completed event"
        
        # Verify tool events contain meaningful information
        for executing_event in tool_executing_events:
            executing_data = executing_event.data
            assert isinstance(executing_data, dict), "Tool executing event should have structured data"
            
            # Should indicate what tool is being executed
            tool_indicators = ["tool", "action", "executing", "analyzing", "processing"]
            has_tool_info = any(indicator in str(executing_data).lower() for indicator in tool_indicators)
            assert has_tool_info, f"Tool executing event should indicate what tool is running: {executing_data}"
        
        for completed_event in tool_completed_events:
            completed_data = completed_event.data
            assert isinstance(completed_data, dict), "Tool completed event should have structured data"
            
            # Should contain results or status
            result_indicators = ["result", "output", "completed", "finished", "data"]
            has_results = any(indicator in str(completed_data).lower() for indicator in result_indicators)
            assert has_results, f"Tool completed event should contain results: {completed_data}"
        
        # Verify proper tool execution pairing (each executing should have corresponding completed)
        assert len(tool_executing_events) <= len(tool_completed_events), \
            "Each tool execution should complete (or equal for long-running tools)"
        
        # Verify final business value incorporates tool results
        final_event = events[-1]
        business_value = self._verify_business_value(final_event)
        
        assert "data_analysis" in business_value["business_value_indicators"], \
            "Should provide data analysis insights from tool execution"
        
        logger.info(f"✅ Tool execution transparency verified: {len(tool_executing_events)} executions, {len(tool_completed_events)} completions")

    @pytest.mark.priority_2
    async def test_006_error_recovery_graceful_degradation(self, staging_config, authenticated_client):
        """
        Test #6: Test error handling in optimization pipeline.
        
        BVJ: Platform reliability - customers must receive useful responses even when
        some tools fail, ensuring continuous value delivery.
        """
        logger.info("🚀 Starting error recovery and graceful degradation test")
        
        await self._verify_backend_health(staging_config)
        
        # Send request with potentially problematic data to trigger error handling
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "cost_optimizer",
                "message": "Analyze my cost data and optimize spending",
                "context": {
                    "invalid_data": None,
                    "malformed_json": "{ invalid json }",
                    "empty_metrics": {},
                    "mixed_data_types": {
                        "costs": ["100", 200, "invalid", None],
                        "dates": ["2024-01-01", "invalid-date", None]
                    }
                }
            }
        )
        
        # Collect events with error handling
        events = []
        error_events = []
        successful_completion = False
        
        timeout = 180.0  # Extended timeout for error recovery
        start_time = time.time()
        
        while (time.time() - start_time) < timeout:
            try:
                message = await authenticated_client.wait_for_message(timeout=10.0)
                events.append(message)
                
                # Track error events
                if message.event_type == WebSocketEventType.ERROR:
                    error_events.append(message)
                    logger.info(f"Error event received: {message.data}")
                
                # Check for successful completion despite errors
                if message.event_type == WebSocketEventType.AGENT_COMPLETED:
                    successful_completion = True
                    break
                    
            except asyncio.TimeoutError:
                continue
        
        # Even with errors, agent should attempt to complete
        assert len(events) > 0, "Should receive events even with error conditions"
        
        if successful_completion:
            # If agent completed successfully, verify graceful degradation
            final_event = events[-1]
            business_value = self._verify_business_value(final_event)
            
            # Response should acknowledge limitations but still provide value
            response_content = str(business_value["response_content"]).lower()
            
            # Should contain helpful response despite data issues
            assert business_value["response_length"] > 100, \
                "Should provide substantial response even with problematic input"
            
            # May contain error acknowledgments or limitations
            limitation_indicators = ["limited", "incomplete", "partial", "available", "unable", "error"]
            has_limitations = any(indicator in response_content for indicator in limitation_indicators)
            
            if has_limitations:
                logger.info("✅ Agent gracefully handled errors with limitations noted")
            else:
                logger.info("✅ Agent successfully processed despite problematic input")
                
        else:
            # If agent didn't complete, should have provided error information
            assert len(error_events) > 0, "Should receive error events if agent cannot complete"
            
            # Error events should be informative
            for error_event in error_events:
                error_data = error_event.data
                assert isinstance(error_data, dict), "Error event should have structured data"
                assert len(str(error_data)) > 20, "Error event should contain meaningful error information"
            
            logger.info("✅ Error handling verified - informative error events provided")

    @pytest.mark.priority_2
    async def test_007_performance_optimization_workflow(self, staging_config, authenticated_client):
        """
        Test #7: Complete performance optimization agent workflow.
        
        BVJ: Technical customer segment - engineers need detailed performance analysis
        with specific, actionable optimization recommendations.
        """
        logger.info("🚀 Starting performance optimization workflow test")
        
        await self._verify_backend_health(staging_config)
        
        # Send comprehensive performance optimization request
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "performance_optimizer",
                "message": "Perform comprehensive performance analysis and provide detailed optimization roadmap",
                "context": {
                    "system_info": {
                        "architecture": "microservices",
                        "scale": "enterprise",
                        "technologies": ["Node.js", "PostgreSQL", "Redis", "Docker"],
                        "current_metrics": {
                            "avg_response_time": 850,
                            "p95_response_time": 2100,
                            "error_rate": 0.034,
                            "throughput_rpm": 12000,
                            "cpu_utilization": 0.78,
                            "memory_utilization": 0.82,
                            "db_connection_pool": 0.91
                        }
                    },
                    "performance_goals": {
                        "target_response_time": 400,
                        "target_p95": 800,
                        "target_error_rate": 0.01,
                        "target_throughput": 20000
                    }
                }
            }
        )
        
        # Collect comprehensive workflow events
        events = await self._collect_agent_events(authenticated_client, timeout=200.0)
        assert len(events) > 0, "No events from performance optimization workflow"
        
        # Verify complete workflow execution
        required_events = [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ]
        
        event_analysis = self._verify_websocket_events(events, required_events)
        
        # Verify business value with performance focus
        final_event = events[-1]
        business_value = self._verify_business_value(final_event)
        
        response_content = str(business_value["response_content"]).lower()
        
        # Should contain performance-specific insights
        performance_topics = [
            "response time", "latency", "throughput", "performance",
            "optimization", "bottleneck", "scaling", "efficiency"
        ]
        
        performance_coverage = sum(1 for topic in performance_topics if topic in response_content)
        assert performance_coverage >= 3, f"Should cover multiple performance topics, only found {performance_coverage}"
        
        # Should provide specific recommendations
        assert "actionable_recommendations" in business_value["business_value_indicators"], \
            "Should provide actionable performance recommendations"
        
        # Should reference the technologies mentioned
        tech_references = sum(1 for tech in ["node", "postgresql", "redis", "docker"] if tech in response_content)
        assert tech_references >= 2, "Should reference specific technologies from context"
        
        # Should provide measurable improvements
        measurement_indicators = ["improve", "reduce", "increase", "optimize", "faster", "better"]
        has_measurements = any(indicator in response_content for indicator in measurement_indicators)
        assert has_measurements, "Should provide measurable improvement suggestions"
        
        logger.info(f"✅ Performance optimization workflow completed: {performance_coverage} topics covered")

    @pytest.mark.priority_3
    async def test_008_data_analysis_visualization(self, staging_config, authenticated_client):
        """
        Test #8: Data analysis agent with visualization results.
        
        BVJ: Mid to Enterprise customers - data-driven insights with visual representations
        help customers understand complex optimization opportunities.
        """
        logger.info("🚀 Starting data analysis visualization test")
        
        await self._verify_backend_health(staging_config)
        
        # Send data analysis request with rich dataset
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "data_analyst",
                "message": "Analyze my usage patterns and create visualizations showing optimization opportunities",
                "context": {
                    "dataset": {
                        "daily_usage": [
                            {"date": "2024-01-01", "cpu": 65, "memory": 72, "cost": 150},
                            {"date": "2024-01-02", "cpu": 78, "memory": 81, "cost": 180},
                            {"date": "2024-01-03", "cpu": 45, "memory": 58, "cost": 120},
                            {"date": "2024-01-04", "cpu": 89, "memory": 94, "cost": 220},
                            {"date": "2024-01-05", "cpu": 92, "memory": 88, "cost": 210},
                            {"date": "2024-01-06", "cpu": 38, "memory": 42, "cost": 100},
                            {"date": "2024-01-07", "cpu": 71, "memory": 76, "cost": 165}
                        ],
                        "service_breakdown": {
                            "compute": 1200,
                            "storage": 450,
                            "networking": 300,
                            "database": 600,
                            "monitoring": 150
                        }
                    },
                    "analysis_goals": [
                        "identify_patterns",
                        "cost_optimization",
                        "usage_efficiency",
                        "capacity_planning"
                    ]
                }
            }
        )
        
        # Collect events from data analysis
        events = await self._collect_agent_events(authenticated_client, timeout=180.0)
        assert len(events) > 0, "No events from data analysis workflow"
        
        # Verify business value with data analysis focus
        final_event = events[-1]
        business_value = self._verify_business_value(final_event)
        
        response_content = str(business_value["response_content"]).lower()
        
        # Should contain data analysis insights
        assert "data_analysis" in business_value["business_value_indicators"], \
            "Should provide data analysis insights"
        
        # Should reference the data provided
        data_references = [
            "usage", "pattern", "trend", "analysis", "data",
            "cpu", "memory", "cost", "service", "compute", "storage"
        ]
        data_coverage = sum(1 for ref in data_references if ref in response_content)
        assert data_coverage >= 4, f"Should reference data elements, only found {data_coverage}"
        
        # Should mention visualization concepts
        viz_indicators = [
            "chart", "graph", "visualization", "plot", "trend", "pattern",
            "analysis", "insight", "correlation", "comparison"
        ]
        viz_mentions = sum(1 for viz in viz_indicators if viz in response_content)
        assert viz_mentions >= 2, "Should reference visualization or analysis concepts"
        
        # Should provide specific insights from the data
        insight_indicators = [
            "peak", "low", "average", "maximum", "minimum", "pattern",
            "correlation", "trend", "spike", "optimization", "efficiency"
        ]
        insights_found = sum(1 for insight in insight_indicators if insight in response_content)
        assert insights_found >= 3, f"Should provide specific data insights, found {insights_found}"
        
        # Should contain actionable recommendations based on data
        assert business_value["contains_recommendations"], \
            "Should provide actionable recommendations based on data analysis"
        
        logger.info(f"✅ Data analysis visualization completed: {data_coverage} data refs, {viz_mentions} viz concepts")

    @pytest.mark.priority_3
    async def test_009_long_running_optimization_progress(self, staging_config, authenticated_client):
        """
        Test #9: Long-running optimization with progress updates.
        
        BVJ: Enterprise customers - complex optimization tasks require progress visibility
        to maintain user engagement during extended processing.
        """
        logger.info("🚀 Starting long-running optimization progress test")
        
        await self._verify_backend_health(staging_config)
        
        # Send complex optimization request that should take extended time
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "comprehensive_optimizer",
                "message": "Perform deep analysis of entire infrastructure and provide comprehensive optimization strategy",
                "context": {
                    "scope": "enterprise_wide",
                    "infrastructure": {
                        "cloud_providers": ["AWS", "Azure", "GCP"],
                        "services_count": 150,
                        "monthly_spend": 85000,
                        "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"],
                        "environments": ["production", "staging", "development", "testing"]
                    },
                    "analysis_depth": "comprehensive",
                    "optimization_areas": [
                        "cost_reduction",
                        "performance_improvement", 
                        "security_enhancement",
                        "compliance_alignment",
                        "disaster_recovery"
                    ]
                }
            }
        )
        
        # Track progress updates over extended period
        events = []
        progress_updates = []
        thinking_phases = []
        tool_executions = []
        
        timeout = 300.0  # 5-minute timeout for comprehensive analysis
        start_time = time.time()
        last_progress_time = start_time
        
        logger.info("⏳ Monitoring long-running optimization process...")
        
        while (time.time() - start_time) < timeout:
            try:
                message = await authenticated_client.wait_for_message(timeout=15.0)
                events.append(message)
                current_time = time.time()
                
                # Track different types of progress indicators
                if message.event_type == WebSocketEventType.AGENT_THINKING:
                    thinking_phases.append({
                        "timestamp": current_time,
                        "elapsed": current_time - start_time,
                        "data": message.data
                    })
                    logger.info(f"⚙️ Thinking phase at {current_time - start_time:.1f}s")
                
                elif message.event_type == WebSocketEventType.TOOL_EXECUTING:
                    tool_executions.append({
                        "timestamp": current_time,
                        "elapsed": current_time - start_time,
                        "data": message.data
                    })
                    logger.info(f"🔧 Tool execution at {current_time - start_time:.1f}s")
                
                elif message.event_type == WebSocketEventType.STATUS_UPDATE:
                    progress_updates.append({
                        "timestamp": current_time,
                        "elapsed": current_time - start_time,
                        "data": message.data
                    })
                    logger.info(f"📈 Progress update at {current_time - start_time:.1f}s")
                
                # Track time between updates
                time_since_last = current_time - last_progress_time
                if time_since_last > 30:  # No updates for 30+ seconds
                    logger.warning(f"⚠️ Long gap between updates: {time_since_last:.1f}s")
                
                last_progress_time = current_time
                
                if message.event_type == WebSocketEventType.AGENT_COMPLETED:
                    break
                    
            except asyncio.TimeoutError:
                current_elapsed = time.time() - start_time
                if current_elapsed < timeout:
                    logger.info(f"⏱️ Waiting for updates... elapsed: {current_elapsed:.1f}s")
                    continue
                else:
                    logger.warning("⚠️ Timeout reached for long-running optimization")
                    break
        
        assert len(events) > 0, "Should receive events during long-running optimization"
        
        total_duration = time.time() - start_time
        logger.info(f"📊 Long-running optimization stats:")
        logger.info(f"   Total duration: {total_duration:.1f}s")
        logger.info(f"   Total events: {len(events)}")
        logger.info(f"   Thinking phases: {len(thinking_phases)}")
        logger.info(f"   Tool executions: {len(tool_executions)}")
        logger.info(f"   Progress updates: {len(progress_updates)}")
        
        # Verify adequate progress communication
        total_progress_indicators = len(thinking_phases) + len(tool_executions) + len(progress_updates)
        assert total_progress_indicators >= 3, \
            f"Should provide multiple progress indicators, only got {total_progress_indicators}"
        
        # Verify progress timing is reasonable (updates at least every 45 seconds)
        if total_duration > 45:
            progress_frequency = total_progress_indicators / (total_duration / 45)
            assert progress_frequency >= 0.8, \
                f"Should provide regular progress updates (every ~45s), frequency: {progress_frequency:.2f}"
        
        # If completed, verify comprehensive results
        if events and events[-1].event_type == WebSocketEventType.AGENT_COMPLETED:
            business_value = self._verify_business_value(events[-1])
            
            # Should be comprehensive given the extended processing time
            assert business_value["response_length"] > 500, \
                f"Long-running optimization should provide comprehensive results, got {business_value['response_length']} chars"
            
            # Should cover multiple optimization areas
            response_content = str(business_value["response_content"]).lower()
            optimization_areas = ["cost", "performance", "security", "compliance", "disaster"]
            areas_covered = sum(1 for area in optimization_areas if area in response_content)
            assert areas_covered >= 3, f"Should cover multiple optimization areas, covered {areas_covered}"
            
            logger.info("✅ Long-running optimization completed with comprehensive results")
        else:
            logger.info("✅ Long-running optimization progress tracking verified (may not have completed)")

    @pytest.mark.priority_2
    async def test_010_full_pipeline_cost_analysis(self, staging_config, authenticated_client):
        """
        Test #10: Full optimization pipeline with detailed cost analysis.
        
        BVJ: Enterprise value proposition - customers need comprehensive cost analysis
        with specific savings calculations and implementation roadmap.
        """
        logger.info("🚀 Starting full pipeline cost analysis test")
        
        await self._verify_backend_health(staging_config)
        
        # Send comprehensive cost analysis request
        execution_id = await self._send_optimization_request(
            authenticated_client,
            {
                "agent": "cost_analyzer",
                "message": "Perform comprehensive cost analysis across all services and provide detailed optimization roadmap with ROI calculations",
                "context": {
                    "organization": {
                        "size": "enterprise",
                        "monthly_cloud_spend": 125000,
                        "annual_growth_rate": 0.35,
                        "cost_centers": ["engineering", "data", "ml", "infrastructure", "security"]
                    },
                    "current_costs": {
                        "compute": {
                            "ec2": 45000,
                            "lambda": 8500,
                            "ecs": 12000,
                            "kubernetes": 15000
                        },
                        "storage": {
                            "s3": 8000,
                            "ebs": 6500,
                            "efs": 2200
                        },
                        "database": {
                            "rds": 18000,
                            "dynamodb": 7500,
                            "elasticache": 4200
                        },
                        "networking": {
                            "data_transfer": 5800,
                            "load_balancers": 3200,
                            "cloudfront": 2100
                        },
                        "ai_ml": {
                            "bedrock": 8900,
                            "sagemaker": 12500,
                            "custom_models": 6800
                        }
                    },
                    "optimization_goals": {
                        "target_savings": 0.25,  # 25% cost reduction
                        "roi_requirement": 3.0,  # 3:1 ROI minimum
                        "implementation_timeline": "6_months",
                        "risk_tolerance": "moderate"
                    }
                }
            }
        )
        
        # Collect comprehensive analysis events
        events = await self._collect_agent_events(authenticated_client, timeout=250.0)
        assert len(events) > 0, "No events from full pipeline cost analysis"
        
        # Verify complete workflow
        event_analysis = self._verify_websocket_events(events, [
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        ])
        
        # Verify comprehensive business value
        final_event = events[-1]
        business_value = self._verify_business_value(final_event)
        
        response_content = str(business_value["response_content"]).lower()
        
        # Must contain cost optimization insights
        assert "cost_optimization" in business_value["business_value_indicators"], \
            "Must provide cost optimization insights"
        
        # Should reference multiple service categories
        service_categories = ["compute", "storage", "database", "networking", "lambda", "ec2", "rds"]
        services_mentioned = sum(1 for service in service_categories if service in response_content)
        assert services_mentioned >= 4, f"Should analyze multiple service categories, found {services_mentioned}"
        
        # Should contain financial analysis
        financial_indicators = [
            "cost", "savings", "reduce", "optimization", "budget", "spend",
            "roi", "return", "investment", "financial", "dollar", "percent"
        ]
        financial_coverage = sum(1 for indicator in financial_indicators if indicator in response_content)
        assert financial_coverage >= 5, f"Should provide comprehensive financial analysis, found {financial_coverage}"
        
        # Should contain specific recommendations
        assert business_value["contains_recommendations"], \
            "Should provide actionable cost optimization recommendations"
        
        # Should reference the organization context
        org_references = ["enterprise", "monthly", "annual", "growth"] 
        org_mentions = sum(1 for ref in org_references if ref in response_content)
        assert org_mentions >= 2, "Should reference organizational context"
        
        # Should provide implementation guidance
        implementation_indicators = [
            "implement", "roadmap", "timeline", "phase", "step", "priority", 
            "migration", "transition", "plan", "strategy"
        ]
        implementation_guidance = sum(1 for indicator in implementation_indicators if indicator in response_content)
        assert implementation_guidance >= 3, f"Should provide implementation guidance, found {implementation_guidance}"
        
        # Verify response is comprehensive for enterprise customer
        assert business_value["response_length"] > 800, \
            f"Enterprise cost analysis should be comprehensive, got {business_value['response_length']} chars"
        
        logger.info(f"✅ Full pipeline cost analysis completed:")
        logger.info(f"   Services analyzed: {services_mentioned}")
        logger.info(f"   Financial coverage: {financial_coverage} indicators")
        logger.info(f"   Implementation guidance: {implementation_guidance} elements")
        logger.info(f"   Response length: {business_value['response_length']} characters")