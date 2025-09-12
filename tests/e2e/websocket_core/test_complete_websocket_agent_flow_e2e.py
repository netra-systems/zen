"""
E2E tests for Complete WebSocket Agent Flow - Testing end-to-end AI agent interactions via WebSocket.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: End-to-end AI chat functionality validation
- Value Impact: Ensures complete user journey from message to AI response works flawlessly
- Strategic Impact: Core business value delivery - validates the entire AI chat pipeline

These E2E tests validate the complete user journey: authentication  ->  WebSocket connection 
 ->  agent request  ->  real-time updates  ->  AI response delivery with full business context.

CRITICAL: All E2E tests MUST use authentication as per CLAUDE.md requirements.
"""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from test_framework.ssot.base import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.websocket import WebSocketTestUtility
from shared.isolated_environment import get_env


class TestCompleteWebSocketAgentFlowE2E(SSotBaseTestCase):
    """E2E tests for complete WebSocket agent workflows with authentication."""
    
    @pytest.fixture
    async def auth_helper(self):
        """Create authenticated E2E auth helper."""
        env = get_env()
        config = E2EAuthConfig(
            auth_service_url="http://localhost:8083",
            backend_url="http://localhost:8002",
            websocket_url="ws://localhost:8002/ws",
            jwt_secret=env.get("JWT_SECRET", "test-jwt-secret-key-unified-testing-32chars")
        )
        return E2EAuthHelper(config)
    
    @pytest.fixture
    async def websocket_utility(self):
        """Create WebSocket test utility."""
        return WebSocketTestUtility()
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_complete_cost_optimization_agent_flow(self, auth_helper, websocket_utility):
        """Test complete end-to-end cost optimization agent flow with authentication.
        
        This test validates the core business value delivery: user sends cost analysis request,
        agent processes it with real-time updates, delivers actionable business insights.
        """
        # STEP 1: Authenticate user (MANDATORY for E2E)
        auth_result = await auth_helper.authenticate_test_user(
            email="e2e_cost_optimizer@example.com",
            subscription_tier="enterprise"
        )
        
        assert auth_result.success is True, f"Authentication failed: {auth_result.error}"
        assert auth_result.access_token is not None
        assert auth_result.user_id is not None
        
        # STEP 2: Establish authenticated WebSocket connection
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=auth_result.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # STEP 3: Send cost optimization request
            cost_request = {
                "type": "start_agent",
                "agent": "cost_optimizer",
                "message": "Analyze my cloud infrastructure costs for the past 30 days and provide specific optimization recommendations with potential savings estimates.",
                "context": {
                    "priority": "high",
                    "analysis_depth": "comprehensive",
                    "include_forecasting": True
                },
                "user_id": auth_result.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send_json(cost_request)
            
            # STEP 4: Collect all WebSocket events during agent execution
            agent_events = []
            final_result = None
            max_wait_time = 60  # 60 seconds max for agent completion
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait_time:
                try:
                    event = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                    agent_events.append(event)
                    
                    # Check for agent completion
                    if event.get("type") == "agent_completed":
                        final_result = event
                        break
                    
                except asyncio.TimeoutError:
                    continue
            
            # STEP 5: Validate all critical WebSocket events were received
            event_types = [event.get("type") for event in agent_events]
            
            # These events are CRITICAL for business value delivery
            required_events = [
                "agent_started",      # User must know agent began
                "agent_thinking",     # Real-time reasoning visibility
                "tool_executing",     # Tool usage transparency (may be multiple)
                "tool_completed",     # Tool results (may be multiple)
                "agent_completed"     # Final response ready
            ]
            
            for required_event in required_events:
                assert required_event in event_types, f"Critical event '{required_event}' missing from WebSocket flow"
            
            # STEP 6: Validate final agent result contains business value
            assert final_result is not None, "Agent must complete with result"
            assert final_result["type"] == "agent_completed"
            
            agent_response = final_result.get("data", {})
            assert "result" in agent_response, "Agent must provide result data"
            
            result_content = agent_response["result"]
            
            # Validate business value content
            business_value_indicators = [
                "cost",
                "savings",
                "optimization", 
                "recommendation",
                "analysis"
            ]
            
            result_text = str(result_content).lower()
            business_indicators_found = sum(1 for indicator in business_value_indicators if indicator in result_text)
            assert business_indicators_found >= 3, f"Agent result must contain business value indicators, found {business_indicators_found}"
            
            # STEP 7: Validate response structure for actionability
            if isinstance(result_content, dict):
                # Should contain actionable insights
                actionable_keys = ["recommendations", "savings_opportunities", "action_items", "next_steps"]
                actionable_content = any(key in result_content for key in actionable_keys)
                assert actionable_content, "Agent result must contain actionable business insights"
            
            # STEP 8: Validate real-time experience quality
            # Agent should provide thinking updates during processing
            thinking_events = [event for event in agent_events if event.get("type") == "agent_thinking"]
            assert len(thinking_events) >= 1, "Agent must provide real-time thinking updates for user experience"
            
            # Tool execution should be visible for transparency  
            tool_events = [event for event in agent_events if event.get("type") in ["tool_executing", "tool_completed"]]
            assert len(tool_events) >= 2, "Agent tool usage must be visible to users (executing + completed)"
            
            # STEP 9: Validate timing for business responsiveness
            total_execution_time = asyncio.get_event_loop().time() - start_time
            assert total_execution_time < 45, f"Agent execution took {total_execution_time:.1f}s - too slow for business use"
            
            # First response should be quick
            first_event_time = None
            if agent_events:
                first_event_time = agent_events[0].get("timestamp")
                if first_event_time:
                    # Should respond within 3 seconds
                    response_delay = (datetime.fromisoformat(first_event_time.replace('Z', '+00:00')) - 
                                    datetime.fromisoformat(cost_request["timestamp"].replace('Z', '+00:00'))).total_seconds()
                    assert response_delay <= 5, f"Initial response took {response_delay:.1f}s - too slow for user experience"
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    async def test_websocket_agent_error_recovery_flow(self, auth_helper, websocket_utility):
        """Test WebSocket agent flow error recovery with authentication.
        
        Validates that errors are handled gracefully and users receive meaningful feedback.
        """
        # Authenticate user (MANDATORY for E2E)
        auth_result = await auth_helper.authenticate_test_user(
            email="e2e_error_recovery@example.com",
            subscription_tier="early"
        )
        
        assert auth_result.success is True
        
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=auth_result.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket:
            
            # Send request that might cause errors (invalid agent or complex request)
            error_prone_request = {
                "type": "start_agent",
                "agent": "nonexistent_agent",  # Should cause graceful error
                "message": "This agent doesn't exist",
                "user_id": auth_result.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send_json(error_prone_request)
            
            # Collect error handling events
            events = []
            max_wait = 30
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait:
                try:
                    event = await asyncio.wait_for(websocket.receive_json(), timeout=3.0)
                    events.append(event)
                    
                    # Look for error or completion event
                    if event.get("type") in ["error", "agent_error", "agent_completed"]:
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            # Should receive error handling
            assert len(events) > 0, "Should receive error handling events"
            
            # Find error event
            error_event = None
            for event in events:
                if event.get("type") in ["error", "agent_error"] or "error" in event.get("data", {}):
                    error_event = event
                    break
            
            # Should provide meaningful error feedback
            if error_event:
                error_data = error_event.get("data", {})
                error_message = error_data.get("message") or error_data.get("error") or str(error_event)
                
                # Error should be user-friendly, not technical
                user_friendly_indicators = ["agent", "available", "try", "support"]
                friendly_content = sum(1 for indicator in user_friendly_indicators if indicator in error_message.lower())
                assert friendly_content >= 1, "Error messages should be user-friendly"
                
                # Should not expose technical details
                technical_terms = ["exception", "traceback", "stack", "internal", "null"]
                technical_exposure = sum(1 for term in technical_terms if term in error_message.lower())
                assert technical_exposure == 0, "Should not expose technical error details to users"
            
            # Test recovery - send valid request after error
            recovery_request = {
                "type": "user_message", 
                "message": "Can you help me optimize costs?",
                "user_id": auth_result.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await websocket.send_json(recovery_request)
            
            # Should handle valid request after error
            recovery_events = []
            recovery_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - recovery_start) < 10:
                try:
                    event = await asyncio.wait_for(websocket.receive_json(), timeout=2.0)
                    recovery_events.append(event)
                    
                    if event.get("type") in ["message_received", "processing"]:
                        break
                        
                except asyncio.TimeoutError:
                    break
            
            # Should recover and process valid requests
            assert len(recovery_events) > 0, "System should recover and handle valid requests after errors"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_multi_user_websocket_isolation_e2e(self, auth_helper, websocket_utility):
        """Test multi-user WebSocket isolation with authentication.
        
        Validates that multiple users can use WebSocket simultaneously without interference.
        """
        # Create multiple authenticated users
        users = []
        for i in range(3):
            auth_result = await auth_helper.authenticate_test_user(
                email=f"e2e_multi_user_{i}@example.com",
                subscription_tier="enterprise"
            )
            assert auth_result.success is True
            users.append(auth_result)
        
        # Create WebSocket connections for all users
        websockets = []
        connection_tasks = []
        
        for user in users:
            websocket = websocket_utility.create_authenticated_websocket_client(
                access_token=user.access_token,
                websocket_url=auth_helper.config.websocket_url
            )
            websockets.append(websocket)
        
        # Connect all users simultaneously
        connected_websockets = []
        for websocket in websockets:
            connected_ws = await websocket.__aenter__()
            connected_websockets.append(connected_ws)
        
        try:
            # Send different messages from each user
            user_messages = [
                {
                    "type": "user_message",
                    "message": f"User {i}: Analyze costs for region {['us-east-1', 'eu-west-1', 'ap-southeast-1'][i]}",
                    "user_id": users[i].user_id,
                    "context": {"user_index": i}
                }
                for i in range(3)
            ]
            
            # Send messages from all users
            for i, (websocket, message) in enumerate(zip(connected_websockets, user_messages)):
                await websocket.send_json(message)
                await asyncio.sleep(0.1)  # Small delay between sends
            
            # Collect responses for each user
            user_responses = [[] for _ in range(3)]
            max_wait = 15
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait:
                # Check each websocket for messages
                for i, websocket in enumerate(connected_websockets):
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                        user_responses[i].append(event)
                    except asyncio.TimeoutError:
                        continue
                
                # Check if all users got some response
                if all(len(responses) > 0 for responses in user_responses):
                    break
                    
                await asyncio.sleep(0.1)
            
            # Validate user isolation
            for i, responses in enumerate(user_responses):
                assert len(responses) > 0, f"User {i} should receive responses"
                
                # Responses should be for correct user
                for response in responses:
                    response_user_id = response.get("user_id") or response.get("data", {}).get("user_id")
                    if response_user_id:
                        assert response_user_id == users[i].user_id, f"User {i} received message for different user"
                
                # Content should be relevant to user's request
                response_content = str(responses).lower()
                expected_region = ['us-east-1', 'eu-west-1', 'ap-southeast-1'][i]
                
                # May not always contain exact region, but should not contain other users' regions
                other_regions = [region for j, region in enumerate(['us-east-1', 'eu-west-1', 'ap-southeast-1']) if j != i]
                for other_region in other_regions:
                    # Should not receive other users' region-specific content
                    if other_region in response_content:
                        # Acceptable if it's generic content, not acceptable if it's specific analysis
                        assert "analyze" not in response_content or expected_region in response_content, \
                            f"User {i} received content specific to other users"
            
            # Test concurrent agent requests
            agent_requests = [
                {
                    "type": "start_agent",
                    "agent": "cost_optimizer",
                    "message": f"Quick cost analysis for user {i}",
                    "user_id": users[i].user_id,
                    "priority": "normal"
                }
                for i in range(3)
            ]
            
            # Send agent requests simultaneously
            for websocket, request in zip(connected_websockets, agent_requests):
                await websocket.send_json(request)
            
            # Each user should get their own agent responses
            agent_responses = [[] for _ in range(3)]
            agent_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - agent_start) < 30:
                for i, websocket in enumerate(connected_websockets):
                    try:
                        event = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                        agent_responses[i].append(event)
                        
                        # Check for completion
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        continue
                
                # Check if at least one agent completed
                completed_agents = sum(1 for responses in agent_responses 
                                     if any(r.get("type") == "agent_completed" for r in responses))
                if completed_agents >= 1:
                    break
                    
                await asyncio.sleep(0.1)
            
            # Validate agent isolation
            for i, responses in enumerate(agent_responses):
                agent_events = [r for r in responses if r.get("type") in ["agent_started", "agent_thinking", "agent_completed"]]
                if agent_events:
                    # Agent events should be for correct user
                    for event in agent_events:
                        event_user = event.get("user_id") or event.get("data", {}).get("user_id")
                        if event_user:
                            assert event_user == users[i].user_id, f"User {i} received agent event for different user"
        
        finally:
            # Cleanup all WebSocket connections
            for websocket in websockets:
                try:
                    await websocket.__aexit__(None, None, None)
                except:
                    pass
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_subscription_tier_features_e2e(self, auth_helper, websocket_utility):
        """Test WebSocket features based on subscription tiers with authentication.
        
        Validates that premium features are properly gated by subscription level.
        """
        # Test different subscription tiers
        subscription_scenarios = [
            {
                "tier": "free",
                "expected_features": ["basic_chat"],
                "premium_features": ["real_time_updates", "priority_agents", "advanced_analytics"]
            },
            {
                "tier": "enterprise", 
                "expected_features": ["basic_chat", "real_time_updates", "priority_agents", "advanced_analytics"],
                "premium_features": []
            }
        ]
        
        for scenario in subscription_scenarios:
            # Authenticate user with specific tier
            auth_result = await auth_helper.authenticate_test_user(
                email=f"e2e_tier_{scenario['tier']}@example.com",
                subscription_tier=scenario["tier"]
            )
            
            assert auth_result.success is True
            
            async with websocket_utility.create_authenticated_websocket_client(
                access_token=auth_result.access_token,
                websocket_url=auth_helper.config.websocket_url
            ) as websocket:
                
                # Test basic features (should work for all tiers)
                basic_request = {
                    "type": "user_message",
                    "message": "Hello, can you help me?",
                    "user_id": auth_result.user_id
                }
                
                await websocket.send_json(basic_request)
                
                # Should receive response
                basic_response = None
                try:
                    basic_response = await asyncio.wait_for(websocket.receive_json(), timeout=10)
                except asyncio.TimeoutError:
                    pass
                
                assert basic_response is not None, f"Basic chat should work for {scenario['tier']} tier"
                
                # Test premium features
                if scenario["tier"] == "enterprise":
                    # Test real-time updates (premium feature)
                    realtime_request = {
                        "type": "enable_realtime_updates",
                        "user_id": auth_result.user_id
                    }
                    
                    await websocket.send_json(realtime_request)
                    
                    realtime_response = None
                    try:
                        realtime_response = await asyncio.wait_for(websocket.receive_json(), timeout=5)
                    except asyncio.TimeoutError:
                        pass
                    
                    # Should enable real-time updates for enterprise
                    if realtime_response:
                        assert realtime_response.get("type") != "error", "Real-time updates should work for enterprise"
                
                elif scenario["tier"] == "free":
                    # Test that premium features are restricted
                    premium_request = {
                        "type": "enable_realtime_updates", 
                        "user_id": auth_result.user_id
                    }
                    
                    await websocket.send_json(premium_request)
                    
                    premium_response = None
                    try:
                        premium_response = await asyncio.wait_for(websocket.receive_json(), timeout=5)
                    except asyncio.TimeoutError:
                        pass
                    
                    # Should receive upgrade prompt or restriction notice
                    if premium_response:
                        response_content = str(premium_response).lower()
                        upgrade_indicators = ["upgrade", "premium", "subscription", "plan"]
                        upgrade_mentioned = any(indicator in response_content for indicator in upgrade_indicators)
                        
                        # Should mention upgrade path for premium features
                        if premium_response.get("type") in ["error", "subscription_required"]:
                            assert upgrade_mentioned, "Should provide upgrade information for premium features"
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_websocket_session_persistence_e2e(self, auth_helper, websocket_utility):
        """Test WebSocket session persistence and reconnection with authentication.
        
        Validates that users can reconnect and maintain conversation context.
        """
        # Authenticate user
        auth_result = await auth_helper.authenticate_test_user(
            email="e2e_persistence@example.com",
            subscription_tier="enterprise"
        )
        
        assert auth_result.success is True
        
        # First session - establish context
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=auth_result.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket1:
            
            # Send message to establish conversation context
            context_message = {
                "type": "start_agent",
                "agent": "cost_optimizer", 
                "message": "I'm analyzing costs for my e-commerce platform. Please remember this context.",
                "user_id": auth_result.user_id,
                "conversation_context": {
                    "domain": "e-commerce",
                    "platform_type": "web_application",
                    "previous_analysis": False
                }
            }
            
            await websocket1.send_json(context_message)
            
            # Wait for agent response
            first_response = None
            max_wait = 30
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < max_wait:
                try:
                    event = await asyncio.wait_for(websocket1.receive_json(), timeout=3)
                    if event.get("type") == "agent_completed":
                        first_response = event
                        break
                except asyncio.TimeoutError:
                    continue
            
            assert first_response is not None, "Should receive agent response in first session"
            
            # Extract conversation context
            thread_id = first_response.get("data", {}).get("thread_id")
            session_data = {
                "thread_id": thread_id,
                "last_message_time": datetime.now(timezone.utc).isoformat(),
                "context": "e-commerce cost analysis"
            }
        
        # Simulate disconnection and reconnection
        await asyncio.sleep(1)
        
        # Second session - test context persistence
        async with websocket_utility.create_authenticated_websocket_client(
            access_token=auth_result.access_token,
            websocket_url=auth_helper.config.websocket_url
        ) as websocket2:
            
            # Send follow-up message that references previous context
            followup_message = {
                "type": "user_message",
                "message": "Following up on our previous e-commerce cost discussion - can you provide more details on storage optimization?",
                "user_id": auth_result.user_id,
                "thread_id": session_data.get("thread_id") if session_data else None,
                "reference_previous": True
            }
            
            await websocket2.send_json(followup_message)
            
            # Should acknowledge context or handle gracefully
            followup_response = None
            followup_start = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - followup_start) < 20:
                try:
                    event = await asyncio.wait_for(websocket2.receive_json(), timeout=3)
                    followup_response = event
                    
                    # Look for processing or completion
                    if event.get("type") in ["message_received", "processing", "agent_completed"]:
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
            assert followup_response is not None, "Should handle follow-up message in new session"
            
            # Response should either:
            # 1. Acknowledge previous context, or  
            # 2. Handle gracefully even without context
            response_content = str(followup_response).lower()
            
            # Should not error due to missing context
            error_indicators = ["error", "failed", "cannot"]
            has_errors = any(indicator in response_content for indicator in error_indicators)
            
            if has_errors:
                # If there are errors, they should be graceful context-related errors
                context_indicators = ["context", "previous", "conversation", "history"]
                context_mentioned = any(indicator in response_content for indicator in context_indicators)
                assert context_mentioned, "Context-related errors should be clearly communicated"
            
            # Test that new conversation can start fresh if context is lost
            fresh_message = {
                "type": "user_message",
                "message": "Let's start fresh - can you help me analyze database costs?",
                "user_id": auth_result.user_id
            }
            
            await websocket2.send_json(fresh_message)
            
            fresh_response = None
            try:
                fresh_response = await asyncio.wait_for(websocket2.receive_json(), timeout=10)
            except asyncio.TimeoutError:
                pass
            
            # Should handle fresh requests regardless of previous context
            assert fresh_response is not None, "Should handle fresh requests in reconnected session"
            
            # Verify user identity is maintained across sessions
            user_id_response = fresh_response.get("user_id") or fresh_response.get("data", {}).get("user_id")
            if user_id_response:
                assert user_id_response == auth_result.user_id, "User identity should persist across sessions"