#!/usr/bin/env python3
"""
Complete Agent Chat Flow E2E Test

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete chat flow delivers core AI optimization value to users
- Value Impact: Ensures agents execute correctly and provide actionable insights to users
- Strategic Impact: Core platform functionality that drives $500K+ ARR - Complete chat workflow

This test validates the complete user journey for agent-powered chat:
1. User authenticates via real JWT/OAuth flow
2. User connects via authenticated WebSocket
3. User sends chat message requesting agent assistance
4. System processes with real agent execution pipeline
5. All 5 required WebSocket events are sent (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
6. User receives meaningful, problem-solving AI response
7. Complete business value delivery is verified

CRITICAL REQUIREMENTS:
- MANDATORY AUTHENTICATION: Uses real JWT tokens and authentication flows
- NO MOCKS: All services (WebSocket, database, Redis, agents) are real
- ALL 5 WEBSOCKET EVENTS: Every agent execution must emit required events
- REAL BUSINESS VALUE: Tests actual AI optimization insights delivery

Compliance with CLAUDE.md:
- Uses real services only (NO MOCKS = compliance with "MOCKS = ABOMINATION")
- IsolatedEnvironment for all environment access
- Absolute imports only
- Mission-critical event validation per Section 6.1
- Complete user journey validation
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest
from loguru import logger

# Test framework imports - SSOT patterns
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    create_authenticated_user,
    create_authenticated_user_context
)
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import (
    assert_websocket_events_sent,
    WebSocketTestHelpers,
    create_test_websocket_connection
)

# Shared utilities
from shared.isolated_environment import get_env
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID


class TestCompleteAgentChatFlowE2E(BaseE2ETest):
    """
    E2E test for complete agent chat flow using REAL services only.
    
    This test validates the complete business value delivery cycle:
    - Real authentication (JWT/OAuth)
    - Real WebSocket connections
    - Real agent execution with LLM
    - Real database persistence
    - All mission-critical WebSocket events
    """

    @pytest.fixture(autouse=True)
    async def setup_test_environment(self):
        """Set up isolated test environment with real services."""
        await self.initialize_test_environment()
        
        # Initialize E2E auth helper
        self.auth_helper = E2EAuthHelper(environment="test")
        
        yield
        
        # Cleanup handled by base class

    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_complete_agent_chat_flow_real_authentication(self, real_services_fixture):
        """
        Test complete user chat flow with agent from authentication to response.
        
        BVJ: Complete chat flow delivers core AI optimization value to users.
        This test validates that users can successfully interact with AI agents
        to get actionable business insights through the chat interface.
        
        CRITICAL: This test MUST use real authentication and validate all 5 WebSocket events.
        """
        logger.info("[U+1F680] Starting complete agent chat flow E2E test with REAL authentication")
        
        # Step 1: Create authenticated user with real JWT token
        auth_user = await self.auth_helper.create_authenticated_user(
            email="complete_chat_test@example.com",
            permissions=["read", "write", "agent_execute"]
        )
        
        logger.info(f" PASS:  Created authenticated user: {auth_user.email}")
        
        # Step 2: Create strongly typed user execution context
        user_context = await create_authenticated_user_context(
            user_email=auth_user.email,
            user_id=auth_user.user_id,
            environment="test",
            permissions=auth_user.permissions,
            websocket_enabled=True
        )
        
        logger.info(f" PASS:  Created execution context: {user_context.user_id}")
        
        # Step 3: Establish authenticated WebSocket connection
        websocket_url = "ws://localhost:8000/ws/chat"
        headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
        
        received_events = []
        websocket_connection = None
        
        try:
            # Connect with authentication headers
            websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
                websocket_url,
                headers=headers,
                timeout=15.0,
                max_retries=3,
                user_id=auth_user.user_id
            )
            
            logger.info(" PASS:  Established authenticated WebSocket connection")
            
            # Step 4: Send agent request message
            chat_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "Please analyze my current infrastructure costs and provide optimization recommendations. I need actionable insights to reduce spending.",
                "user_id": auth_user.user_id,
                "thread_id": str(user_context.thread_id),
                "request_id": str(user_context.request_id),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"[U+1F4E4] Sending agent request: {chat_message['message'][:50]}...")
            await WebSocketTestHelpers.send_test_message(websocket_connection, chat_message)
            
            # Step 5: Collect all WebSocket events with timeout
            collection_timeout = 30.0  # Allow sufficient time for agent execution
            start_time = time.time()
            
            logger.info("[U+1F442] Collecting WebSocket events...")
            
            while time.time() - start_time < collection_timeout:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        websocket_connection, 
                        timeout=2.0
                    )
                    received_events.append(event)
                    
                    event_type = event.get("type", "unknown")
                    logger.info(f"[U+1F4E8] Received event: {event_type}")
                    
                    # Stop collecting when agent completion is received
                    if event_type == "agent_completed":
                        logger.info(" PASS:  Agent completed event received - stopping collection")
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower():
                        # Check if we have completion event, if not continue waiting
                        completion_events = [e for e in received_events if e.get("type") == "agent_completed"]
                        if completion_events:
                            logger.info(" PASS:  Found completion event in previous messages")
                            break
                        else:
                            logger.debug("[U+23F3] Timeout waiting for events, continuing...")
                            continue
                    else:
                        logger.error(f" FAIL:  Error receiving WebSocket message: {e}")
                        break
            
            logger.info(f" CHART:  Collected {len(received_events)} WebSocket events")
            
            # Step 6: Validate all required WebSocket events (MISSION CRITICAL)
            required_events = [
                "agent_started",
                "agent_thinking", 
                "tool_executing",
                "tool_completed",
                "agent_completed"
            ]
            
            # Use SSOT assertion function
            assert_websocket_events_sent(received_events, required_events)
            logger.info(" PASS:  All 5 required WebSocket events validated")
            
            # Step 7: Validate business value delivery
            event_types = [event.get("type") for event in received_events]
            
            # Ensure user saw processing started
            assert "agent_started" in event_types, "CRITICAL: User never knew processing started - UX FAILURE"
            
            # Ensure user saw progress updates  
            has_progress = any(t in event_types for t in ["agent_thinking", "partial_result"])
            assert has_progress, "CRITICAL: User saw no progress updates - feels unresponsive"
            
            # Ensure user saw tool execution (actual work being done)
            has_tool_work = any(t in event_types for t in ["tool_executing", "tool_completed"])
            assert has_tool_work, "CRITICAL: User has no visibility into system work being done"
            
            # Ensure user knows when processing completed
            assert "agent_completed" in event_types, "CRITICAL: User doesn't know when processing finished - UX FAILURE"
            
            # Step 8: Validate meaningful response content
            completion_events = [e for e in received_events if e.get("type") == "agent_completed"]
            assert len(completion_events) > 0, "No agent completion event found"
            
            completion_data = completion_events[0].get("data", {})
            final_response = completion_data.get("result", "") or completion_data.get("response", "")
            
            # Validate response contains actionable business value
            assert len(final_response) > 50, f"Response too short ({len(final_response)} chars) - likely not actionable"
            
            # Check for business value indicators in response
            business_indicators = ["cost", "optimize", "recommend", "save", "efficiency", "improve", "reduce"]
            has_business_value = any(indicator in final_response.lower() for indicator in business_indicators)
            assert has_business_value, f"Response lacks business value indicators: {final_response[:200]}..."
            
            logger.info(" PASS:  Agent response contains actionable business value")
            
            # Step 9: Validate authentication context preservation
            auth_events = [e for e in received_events if "user_id" in e.get("data", {})]
            assert len(auth_events) > 0, "No events preserved user authentication context"
            
            for event in auth_events:
                event_user_id = event.get("data", {}).get("user_id")
                if event_user_id:
                    assert event_user_id == auth_user.user_id, f"User ID mismatch in event: {event_user_id} != {auth_user.user_id}"
            
            logger.info(" PASS:  Authentication context preserved throughout agent execution")
            
            # Step 10: Validate response timing (user experience)
            if len(received_events) >= 2:
                first_event_time = received_events[0].get("timestamp")
                last_event_time = received_events[-1].get("timestamp")
                
                if first_event_time and last_event_time:
                    # Parse ISO timestamps
                    try:
                        first_time = datetime.fromisoformat(first_event_time.replace('Z', '+00:00'))
                        last_time = datetime.fromisoformat(last_event_time.replace('Z', '+00:00'))
                        
                        total_time = (last_time - first_time).total_seconds()
                        assert total_time < 30.0, f"Agent execution took too long: {total_time}s (max: 30s)"
                        
                        logger.info(f" PASS:  Agent execution completed in {total_time:.2f}s (acceptable for UX)")
                    except Exception as e:
                        logger.warning(f"Could not parse event timestamps for timing validation: {e}")
            
            logger.info(" CELEBRATION:  COMPLETE AGENT CHAT FLOW E2E TEST PASSED")
            logger.info(f"   [U+1F464] User: {auth_user.email}")
            logger.info(f"   [U+1F4E8] Events: {len(received_events)}")
            logger.info(f"    TARGET:  Business Value: AI-powered cost optimization insights delivered")
            logger.info(f"    PASS:  All mission-critical requirements satisfied")
            
        finally:
            # Clean up WebSocket connection
            if websocket_connection:
                await WebSocketTestHelpers.close_test_connection(websocket_connection)
                logger.info("[U+1F9F9] WebSocket connection closed")

    @pytest.mark.e2e
    @pytest.mark.real_services
    async def test_agent_chat_flow_with_tool_execution_validation(self, real_services_fixture):
        """
        Test agent chat flow with detailed tool execution validation.
        
        This test focuses specifically on the tool execution aspect of agent workflows,
        ensuring tools are properly executed and their results are communicated to users.
        """
        logger.info("[U+1F680] Starting agent chat flow with tool execution validation")
        
        # Create authenticated user
        auth_user = await self.auth_helper.create_authenticated_user(
            email="tool_execution_test@example.com",
            permissions=["read", "write", "agent_execute", "tool_execute"]
        )
        
        websocket_url = "ws://localhost:8000/ws/chat"
        headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
        
        received_events = []
        websocket_connection = None
        
        try:
            websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
                websocket_url,
                headers=headers,
                timeout=15.0,
                user_id=auth_user.user_id
            )
            
            # Send message that requires tool execution
            chat_message = {
                "type": "agent_request",
                "agent": "data_helper_agent",  # Agent that typically uses tools
                "message": "Please search for information about cloud cost optimization best practices and analyze current trends.",
                "user_id": auth_user.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket_connection, chat_message)
            
            # Collect events with focus on tool execution
            start_time = time.time()
            tool_executing_events = []
            tool_completed_events = []
            
            while time.time() - start_time < 25.0:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        websocket_connection,
                        timeout=2.0
                    )
                    received_events.append(event)
                    
                    event_type = event.get("type")
                    
                    if event_type == "tool_executing":
                        tool_executing_events.append(event)
                        logger.info(f"[U+1F527] Tool executing: {event.get('data', {}).get('tool_name', 'unknown')}")
                    elif event_type == "tool_completed":
                        tool_completed_events.append(event) 
                        logger.info(f" PASS:  Tool completed: {event.get('data', {}).get('tool_name', 'unknown')}")
                    elif event_type == "agent_completed":
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower():
                        continue
                    break
            
            # Validate tool execution pairing
            assert len(tool_executing_events) > 0, "No tool_executing events received - tools not being executed"
            assert len(tool_completed_events) > 0, "No tool_completed events received - tool results not communicated"
            
            # Validate tool event pairing (each executing should have corresponding completed)
            assert len(tool_executing_events) == len(tool_completed_events), \
                f"Tool events not paired: {len(tool_executing_events)} executing, {len(tool_completed_events)} completed"
            
            # Validate tool event data structure
            for event in tool_executing_events:
                event_data = event.get("data", {})
                assert "tool_name" in event_data, "tool_executing event missing tool_name"
                assert event_data["tool_name"], "tool_executing event has empty tool_name"
            
            for event in tool_completed_events:
                event_data = event.get("data", {})
                assert "tool_name" in event_data, "tool_completed event missing tool_name"
                assert "result" in event_data, "tool_completed event missing result"
                assert event_data["tool_name"], "tool_completed event has empty tool_name"
            
            logger.info(f" PASS:  Tool execution validation passed: {len(tool_executing_events)} tools executed")
            
        finally:
            if websocket_connection:
                await WebSocketTestHelpers.close_test_connection(websocket_connection)

    @pytest.mark.e2e
    @pytest.mark.real_services  
    async def test_agent_chat_flow_response_quality_validation(self, real_services_fixture):
        """
        Test agent chat flow with focus on response quality and business value.
        
        This test validates that agents provide high-quality, actionable responses
        that deliver real business value to users.
        """
        logger.info("[U+1F680] Starting agent chat flow response quality validation")
        
        # Create authenticated user
        auth_user = await self.auth_helper.create_authenticated_user(
            email="response_quality_test@example.com"
        )
        
        websocket_url = "ws://localhost:8000/ws/chat"
        headers = self.auth_helper.get_websocket_headers(auth_user.jwt_token)
        
        received_events = []
        websocket_connection = None
        
        try:
            websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
                websocket_url,
                headers=headers,
                timeout=15.0,
                user_id=auth_user.user_id
            )
            
            # Send message requesting specific business insights
            chat_message = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": "I need to reduce my AWS costs by 20% this quarter. What are the most effective strategies and specific actions I can take?",
                "user_id": auth_user.user_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await WebSocketTestHelpers.send_test_message(websocket_connection, chat_message)
            
            # Collect all events
            start_time = time.time()
            
            while time.time() - start_time < 30.0:
                try:
                    event = await WebSocketTestHelpers.receive_test_message(
                        websocket_connection,
                        timeout=2.0
                    )
                    received_events.append(event)
                    
                    if event.get("type") == "agent_completed":
                        break
                        
                except Exception as e:
                    if "timeout" in str(e).lower():
                        continue
                    break
            
            # Validate response quality
            completion_events = [e for e in received_events if e.get("type") == "agent_completed"]
            assert len(completion_events) > 0, "No agent completion event found"
            
            completion_data = completion_events[0].get("data", {})
            final_response = completion_data.get("result", "") or completion_data.get("response", "")
            
            # Quality checks
            assert len(final_response) >= 100, f"Response too brief ({len(final_response)} chars) for complex business question"
            
            # Check for specific business value elements
            cost_terms = ["cost", "save", "reduce", "optimize", "efficiency", "budget"]
            has_cost_focus = any(term in final_response.lower() for term in cost_terms)
            assert has_cost_focus, f"Response doesn't address cost optimization: {final_response[:150]}..."
            
            # Check for actionable advice
            action_terms = ["recommend", "suggest", "action", "step", "implement", "configure", "review"]
            has_actionable_content = any(term in final_response.lower() for term in action_terms)
            assert has_actionable_content, f"Response lacks actionable recommendations: {final_response[:150]}..."
            
            logger.info(" PASS:  Agent response quality validation passed")
            logger.info(f"   [U+1F4DD] Response length: {len(final_response)} characters")
            logger.info(f"    TARGET:  Contains cost optimization focus:  PASS: ")
            logger.info(f"    TARGET:  Contains actionable recommendations:  PASS: ")
            
        finally:
            if websocket_connection:
                await WebSocketTestHelpers.close_test_connection(websocket_connection)


if __name__ == "__main__":
    # Run this E2E test standalone for development
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "-s",  # Show real-time output
        "--timeout=120",  # Allow time for real agent execution
    ])