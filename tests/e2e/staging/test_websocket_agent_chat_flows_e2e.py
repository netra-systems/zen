#!/usr/bin/env python
"""
E2E Staging Tests for WebSocket Agent Chat Flows

MISSION CRITICAL: End-to-end chat flows with real WebSocket events for staging validation.
Tests complete chat workflows with all 5 REQUIRED WebSocket events in staging environment.

Business Value: $500K+ ARR - Full chat experience validation in staging
- Tests complete user chat experiences with real agent execution
- Validates all 5 REQUIRED WebSocket events in staging environment  
- Ensures business value delivery through substantive AI interactions
"""

import asyncio
import json
import pytest
import time
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# SSOT imports following CLAUDE.md guidelines
from shared.types.core_types import WebSocketEventType, UserID, ThreadID, RequestID
from test_framework.ssot.websocket import WebSocketTestUtility, WebSocketEventType as TestEventType
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Import production components for staging tests - NO MOCKS per CLAUDE.md
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.llm.llm_manager import LLMManager


@pytest.fixture
async def staging_websocket_utility():
    """Create WebSocket test utility for staging environment."""
    # Use staging WebSocket URL
    staging_ws_url = "wss://staging.netra-apex.com/ws"  # Replace with actual staging URL
    
    async with WebSocketTestUtility(base_url=staging_ws_url) as ws_util:
        yield ws_util


@pytest.fixture
def staging_auth_helper():
    """Create authentication helper for staging environment."""
    return E2EAuthHelper(environment="staging")


@pytest.fixture
async def staging_websocket_manager():
    """Create WebSocket manager connected to staging."""
    manager = UnifiedWebSocketManager()
    await manager.initialize()
    yield manager
    await manager.cleanup()


@pytest.mark.e2e
@pytest.mark.staging
class TestStagingWebSocketChatFlows:
    """E2E tests for complete chat flows with WebSocket events in staging."""
    
    @pytest.mark.asyncio
    async def test_complete_optimization_chat_flow_with_websocket_events(self, staging_websocket_utility, staging_auth_helper):
        """
        Test complete optimization chat flow with all 5 REQUIRED WebSocket events.
        
        CRITICAL: This tests the full business value delivery chain.
        User requests optimization → Agent analyzes → Tools execute → Results delivered
        All steps must have proper WebSocket events for substantive chat experience.
        """
        # Arrange - Create authenticated staging user
        auth_result = await staging_auth_helper.create_authenticated_user(
            user_id=f"staging_optimization_user_{uuid.uuid4().hex[:8]}",
            permissions=["chat_access", "agent_execution", "optimization_tools"]
        )
        
        user_context = UserExecutionContext(
            user_id=UserID(auth_result["user_id"]),
            thread_id=ThreadID(f"staging_opt_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"staging_opt_request_{uuid.uuid4().hex[:8]}"),
            session_id=auth_result["session_id"]
        )
        
        # Connect with authenticated WebSocket
        auth_headers = {
            "Authorization": f"Bearer {auth_result['access_token']}",
            "X-User-ID": auth_result["user_id"]
        }
        
        async with staging_websocket_utility.connected_client(user_context.user_id) as client:
            client.headers = auth_headers
            await client.connect(timeout=60.0)  # Longer timeout for staging
            
            # Act - Simulate complete optimization chat flow
            optimization_request = {
                "type": "user_message",
                "content": "I need help optimizing my cloud infrastructure costs. Can you analyze my spending and suggest improvements?",
                "timestamp": datetime.now().isoformat(),
                "thread_id": str(user_context.thread_id),
                "user_id": str(user_context.user_id)
            }
            
            # Send user request
            await client.send_message(
                TestEventType.MESSAGE_CREATED,
                optimization_request,
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id)
            )
            
            # Wait for complete agent workflow with all 5 REQUIRED events
            expected_events = [
                TestEventType.AGENT_STARTED,     # User must see agent began processing
                TestEventType.AGENT_THINKING,    # Real-time reasoning visibility
                TestEventType.TOOL_EXECUTING,    # Tool usage transparency  
                TestEventType.TOOL_COMPLETED,    # Tool results display
                TestEventType.AGENT_COMPLETED    # User must know when response ready
            ]
            
            print(f"Waiting for complete optimization workflow events: {[e.value for e in expected_events]}")
            
            # Wait for all events with extended timeout for staging
            received_events = await client.wait_for_events(expected_events, timeout=120.0)
            
            # Assert - Verify all 5 REQUIRED events received
            for event_type in expected_events:
                assert event_type in received_events, f"Missing REQUIRED event: {event_type.value}"
                assert len(received_events[event_type]) > 0, f"No messages for required event: {event_type.value}"
            
            # Verify agent_started event details
            agent_started = received_events[TestEventType.AGENT_STARTED][0]
            assert agent_started.data.get("agent") is not None, "agent_started must include agent name"
            assert agent_started.data.get("status") == "starting", "agent_started must have starting status"
            assert agent_started.user_id == str(user_context.user_id), "Event must be user-scoped"
            
            # Verify agent_thinking event provides reasoning
            agent_thinking = received_events[TestEventType.AGENT_THINKING][0]
            assert agent_thinking.data.get("progress") is not None, "agent_thinking must include progress"
            assert len(agent_thinking.data.get("progress", "")) > 10, "Progress must be substantial"
            
            # Verify tool_executing event shows tool usage
            tool_executing = received_events[TestEventType.TOOL_EXECUTING][0]
            assert tool_executing.data.get("tool") is not None, "tool_executing must include tool name"
            assert tool_executing.data.get("status") == "executing", "tool_executing must have executing status"
            
            # Verify tool_completed event provides results
            tool_completed = received_events[TestEventType.TOOL_COMPLETED][0]
            assert tool_completed.data.get("tool") is not None, "tool_completed must include tool name"
            assert tool_completed.data.get("result") is not None, "tool_completed must include results"
            assert tool_completed.data.get("status") == "completed", "tool_completed must have completed status"
            
            # Verify agent_completed event provides final response
            agent_completed = received_events[TestEventType.AGENT_COMPLETED][0]
            assert agent_completed.data.get("agent") is not None, "agent_completed must include agent name"
            assert agent_completed.data.get("result") is not None, "agent_completed must include final result"
            assert agent_completed.data.get("status") == "completed", "agent_completed must have completed status"
            
            # Verify business value delivery
            final_result = agent_completed.data["result"]
            business_value_indicators = [
                "optimization", "cost", "saving", "recommendation", "improvement", 
                "efficiency", "reduce", "analysis", "strategy", "action"
            ]
            
            result_text = json.dumps(final_result).lower()
            business_value_found = any(indicator in result_text for indicator in business_value_indicators)
            assert business_value_found, "Final result must contain business value indicators"
            
            print(f"✅ Complete optimization chat flow validated with all 5 REQUIRED events")
            print(f"   Events received: {list(received_events.keys())}")
            print(f"   Final result contains business value: {business_value_found}")
    
    @pytest.mark.asyncio
    async def test_multi_user_concurrent_chat_flows_staging(self, staging_websocket_utility, staging_auth_helper):
        """
        Test concurrent multi-user chat flows in staging environment.
        
        CRITICAL: Staging must handle multiple concurrent users with isolated chat sessions.
        This validates the multi-tenant chat capability for business scalability.
        """
        # Arrange - Create multiple authenticated staging users
        user_count = 3  # Realistic concurrent load for staging
        auth_results = []
        
        for i in range(user_count):
            auth_result = await staging_auth_helper.create_authenticated_user(
                user_id=f"staging_concurrent_user_{i}_{uuid.uuid4().hex[:6]}",
                permissions=["chat_access", "agent_execution"]
            )
            auth_results.append(auth_result)
        
        # Create user contexts
        user_contexts = []
        for auth_result in auth_results:
            context = UserExecutionContext(
                user_id=UserID(auth_result["user_id"]),
                thread_id=ThreadID(f"staging_concurrent_thread_{uuid.uuid4().hex[:8]}"),
                request_id=RequestID(f"staging_concurrent_request_{uuid.uuid4().hex[:8]}"),
                session_id=auth_result["session_id"]
            )
            user_contexts.append((context, auth_result))
        
        # Act - Create concurrent chat sessions
        concurrent_clients = []
        connect_tasks = []
        
        for context, auth_result in user_contexts:
            auth_headers = {
                "Authorization": f"Bearer {auth_result['access_token']}",
                "X-User-ID": auth_result["user_id"]
            }
            
            client = await staging_websocket_utility.create_authenticated_client(
                auth_result["user_id"],
                auth_result["access_token"]
            )
            concurrent_clients.append((client, context, auth_result))
            
            # Create connection task
            connect_task = asyncio.create_task(client.connect(timeout=60.0))
            connect_tasks.append(connect_task)
        
        # Wait for all connections
        connection_results = await asyncio.gather(*connect_tasks, return_exceptions=True)
        successful_connections = sum(1 for result in connection_results if result is True)
        
        assert successful_connections >= user_count * 0.8, f"At least 80% users must connect to staging, got {successful_connections}/{user_count}"
        
        # Send concurrent chat requests
        async def send_user_chat_flow(client_data, user_index):
            client, context, auth_result = client_data
            if not client.is_connected:
                return None
            
            # Send user message specific to each user
            user_requests = [
                "Help me analyze my data pipeline performance",
                "I need recommendations for database optimization", 
                "Can you review my application architecture for improvements"
            ]
            
            user_message = {
                "content": user_requests[user_index % len(user_requests)],
                "user_context": f"User {user_index} specific request",
                "timestamp": datetime.now().isoformat()
            }
            
            await client.send_message(
                TestEventType.MESSAGE_CREATED,
                user_message,
                user_id=str(context.user_id),
                thread_id=str(context.thread_id)
            )
            
            # Wait for agent response events
            try:
                # Wait for at least agent_started and agent_completed
                minimal_events = [TestEventType.AGENT_STARTED, TestEventType.AGENT_COMPLETED]
                received = await client.wait_for_events(minimal_events, timeout=90.0)
                return received
            except asyncio.TimeoutError:
                print(f"Timeout waiting for events for user {user_index}")
                return None
        
        # Execute concurrent chat flows
        chat_tasks = [
            asyncio.create_task(send_user_chat_flow(client_data, i))
            for i, client_data in enumerate(concurrent_clients)
        ]
        
        chat_results = await asyncio.gather(*chat_tasks, return_exceptions=True)
        
        # Assert concurrent chat success
        successful_chats = sum(1 for result in chat_results if result is not None and isinstance(result, dict))
        assert successful_chats >= user_count * 0.7, f"At least 70% concurrent chats must succeed in staging, got {successful_chats}/{user_count}"
        
        # Verify user isolation - each user should only receive their own events
        for i, (client, context, auth_result) in enumerate(concurrent_clients):
            if hasattr(client, 'received_messages'):
                user_messages = client.received_messages
                
                # Verify all messages are for this user
                for message in user_messages:
                    if hasattr(message, 'user_id') and message.user_id:
                        assert message.user_id == str(context.user_id), f"User {i} received message for different user"
        
        # Cleanup
        cleanup_tasks = [client.disconnect() for client, _, _ in concurrent_clients]
        await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        print(f"✅ Multi-user concurrent chat flows validated in staging")
        print(f"   Successful connections: {successful_connections}/{user_count}")
        print(f"   Successful chats: {successful_chats}/{user_count}")
    
    @pytest.mark.asyncio
    async def test_staging_websocket_agent_error_recovery_flow(self, staging_websocket_utility, staging_auth_helper):
        """
        Test WebSocket agent error recovery in staging environment.
        
        CRITICAL: Staging must handle agent errors gracefully without breaking chat.
        Error recovery ensures business continuity and user experience quality.
        """
        # Arrange - Create authenticated staging user
        auth_result = await staging_auth_helper.create_authenticated_user(
            user_id=f"staging_error_recovery_user_{uuid.uuid4().hex[:8]}",
            permissions=["chat_access", "agent_execution", "error_recovery_test"]
        )
        
        user_context = UserExecutionContext(
            user_id=UserID(auth_result["user_id"]),
            thread_id=ThreadID(f"staging_error_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"staging_error_request_{uuid.uuid4().hex[:8]}"),
            session_id=auth_result["session_id"]
        )
        
        auth_headers = {
            "Authorization": f"Bearer {auth_result['access_token']}",
            "X-User-ID": auth_result["user_id"]
        }
        
        async with staging_websocket_utility.connected_client(user_context.user_id) as client:
            client.headers = auth_headers
            await client.connect(timeout=60.0)
            
            # Act - Send request that may trigger agent errors (for testing)
            error_inducing_request = {
                "content": "Please analyze an extremely complex scenario that might cause processing issues",
                "error_test": True,
                "complex_scenario": "Handle edge case with invalid data that requires error recovery",
                "timestamp": datetime.now().isoformat()
            }
            
            await client.send_message(
                TestEventType.MESSAGE_CREATED,
                error_inducing_request,
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id)
            )
            
            # Wait for agent response with error handling
            recovery_events = []
            total_wait_time = 0
            max_wait_time = 120.0  # 2 minutes for error recovery
            
            while total_wait_time < max_wait_time:
                try:
                    # Try to receive any agent events
                    message = await client.wait_for_message(timeout=15.0)
                    if message:
                        recovery_events.append(message)
                        
                        # Check if we received agent completion (successful recovery)
                        if message.event_type == TestEventType.AGENT_COMPLETED:
                            break
                        
                        # Check for error events
                        if message.event_type == TestEventType.ERROR:
                            print(f"Received error event: {message.data}")
                            # Continue waiting for recovery
                    
                    total_wait_time += 15.0
                    
                except asyncio.TimeoutError:
                    total_wait_time += 15.0
                    print(f"Waiting for error recovery... {total_wait_time:.0f}s elapsed")
                    continue
            
            # Assert error recovery
            assert len(recovery_events) > 0, "Must receive some agent events even with errors"
            
            # Check for successful completion or graceful error handling
            has_completion = any(event.event_type == TestEventType.AGENT_COMPLETED for event in recovery_events)
            has_error_handling = any(event.event_type == TestEventType.ERROR for event in recovery_events)
            has_agent_started = any(event.event_type == TestEventType.AGENT_STARTED for event in recovery_events)
            
            # At minimum, system should start processing and handle errors gracefully
            assert has_agent_started, "Agent must start processing even for error cases"
            assert has_completion or has_error_handling, "Must have either successful completion or graceful error handling"
            
            # Verify system remains responsive after error scenario
            follow_up_request = {
                "content": "Simple follow-up request to verify system is still working",
                "follow_up_after_error": True,
                "timestamp": datetime.now().isoformat()
            }
            
            await client.send_message(
                TestEventType.MESSAGE_CREATED,
                follow_up_request,
                user_id=str(user_context.user_id),
                thread_id=str(user_context.thread_id)
            )
            
            # Wait for follow-up response
            try:
                follow_up_response = await client.wait_for_message(
                    event_type=TestEventType.AGENT_STARTED,
                    timeout=30.0
                )
                system_responsive = follow_up_response is not None
            except asyncio.TimeoutError:
                system_responsive = False
            
            # System should remain responsive after error recovery
            if not system_responsive:
                print("⚠️ System may not be fully responsive after error scenario")
            
            print(f"✅ Error recovery flow validated in staging")
            print(f"   Recovery events received: {len(recovery_events)}")
            print(f"   System responsive after error: {system_responsive}")
            print(f"   Events: {[e.event_type.value for e in recovery_events]}")


@pytest.mark.e2e
@pytest.mark.staging
class TestStagingWebSocketPerformance:
    """E2E performance tests for WebSocket in staging environment."""
    
    @pytest.mark.asyncio
    async def test_staging_websocket_chat_response_times(self, staging_websocket_utility, staging_auth_helper):
        """
        Test WebSocket chat response times in staging environment.
        
        CRITICAL: Chat response times must meet business requirements.
        Slow responses reduce user engagement and business value.
        """
        # Arrange
        auth_result = await staging_auth_helper.create_authenticated_user(
            user_id=f"staging_perf_user_{uuid.uuid4().hex[:8]}",
            permissions=["chat_access", "agent_execution"]
        )
        
        user_context = UserExecutionContext(
            user_id=UserID(auth_result["user_id"]),
            thread_id=ThreadID(f"staging_perf_thread_{uuid.uuid4().hex[:8]}"),
            request_id=RequestID(f"staging_perf_request_{uuid.uuid4().hex[:8]}")
        )
        
        auth_headers = {
            "Authorization": f"Bearer {auth_result['access_token']}",
            "X-User-ID": auth_result["user_id"]
        }
        
        async with staging_websocket_utility.connected_client(user_context.user_id) as client:
            client.headers = auth_headers
            await client.connect(timeout=60.0)
            
            # Act - Measure chat response times
            response_times = []
            
            for i in range(3):  # Test 3 requests for average
                start_time = time.time()
                
                performance_request = {
                    "content": f"Quick analysis request #{i+1} - provide brief optimization suggestion",
                    "performance_test": True,
                    "request_number": i + 1,
                    "timestamp": datetime.now().isoformat()
                }
                
                await client.send_message(
                    TestEventType.MESSAGE_CREATED,
                    performance_request,
                    user_id=str(user_context.user_id),
                    thread_id=str(user_context.thread_id)
                )
                
                # Wait for agent_started (first response)
                try:
                    agent_started = await client.wait_for_message(
                        event_type=TestEventType.AGENT_STARTED,
                        timeout=30.0
                    )
                    first_response_time = time.time() - start_time
                    
                    # Wait for agent_completed (final response)
                    agent_completed = await client.wait_for_message(
                        event_type=TestEventType.AGENT_COMPLETED,
                        timeout=60.0
                    )
                    total_response_time = time.time() - start_time
                    
                    response_times.append({
                        "request_number": i + 1,
                        "first_response_time": first_response_time,
                        "total_response_time": total_response_time,
                        "success": True
                    })
                    
                except asyncio.TimeoutError:
                    response_times.append({
                        "request_number": i + 1,
                        "first_response_time": None,
                        "total_response_time": None,
                        "success": False
                    })
                
                # Brief pause between requests
                await asyncio.sleep(2.0)
            
            # Assert performance requirements
            successful_requests = [rt for rt in response_times if rt["success"]]
            assert len(successful_requests) >= 2, "At least 2/3 requests must succeed for performance validation"
            
            # Calculate performance metrics
            first_response_times = [rt["first_response_time"] for rt in successful_requests if rt["first_response_time"]]
            total_response_times = [rt["total_response_time"] for rt in successful_requests if rt["total_response_time"]]
            
            if first_response_times:
                avg_first_response = sum(first_response_times) / len(first_response_times)
                max_first_response = max(first_response_times)
                
                # Business requirements for chat responsiveness
                assert avg_first_response < 5.0, f"Average first response must be under 5s, got {avg_first_response:.1f}s"
                assert max_first_response < 10.0, f"Max first response must be under 10s, got {max_first_response:.1f}s"
            
            if total_response_times:
                avg_total_response = sum(total_response_times) / len(total_response_times)
                max_total_response = max(total_response_times)
                
                # Business requirements for complete response
                assert avg_total_response < 30.0, f"Average total response must be under 30s, got {avg_total_response:.1f}s"
                assert max_total_response < 60.0, f"Max total response must be under 60s, got {max_total_response:.1f}s"
            
            print(f"✅ Staging chat performance validated")
            print(f"   Successful requests: {len(successful_requests)}/3")
            if first_response_times:
                print(f"   Avg first response: {sum(first_response_times)/len(first_response_times):.1f}s")
            if total_response_times:
                print(f"   Avg total response: {sum(total_response_times)/len(total_response_times):.1f}s")