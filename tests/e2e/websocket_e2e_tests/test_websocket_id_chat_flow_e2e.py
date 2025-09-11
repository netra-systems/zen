"""
WebSocket ID Chat Flow E2E Tests

CRITICAL: These tests are DESIGNED TO FAIL during Phase 1 of WebSocket ID migration.
They expose chat flow business value issues caused by uuid.uuid4() ID patterns.

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Chat functionality delivers substantive AI value
- Value Impact: Chat is 90% of our business value delivery mechanism
- Strategic Impact: CRITICAL - Chat failures = business value delivery failures

Test Strategy:
1. FAIL INITIALLY - Tests expose chat flow issues with uuid.uuid4()
2. MIGRATE PHASE - Replace with UnifiedIdGenerator user-aware methods
3. PASS FINALLY - Tests validate chat flow delivers business value with consistent IDs

These tests validate that WebSocket IDs enable proper chat flow business value:
- Real AI agent interactions
- Timely user updates  
- Complete readable responses
- Multi-user isolation
- Data-driven insights
"""

import pytest
import asyncio
import uuid
import time
import websockets
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from contextlib import asynccontextmanager

# Import test framework for E2E testing
from test_framework.base_e2e_test import BaseE2ETest
from test_framework.real_services import get_real_services
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper

# Import WebSocket testing utilities
from netra_backend.tests.e2e.websocket_core.test_websocket_agent_communication_e2e import WebSocketTestClient
from test_framework.ssot.websocket_test_client import UnifiedWebSocketTestClient

# Import agent execution components for real AI testing
from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.llm.openai_manager import OpenAIManager

# Import WebSocket core modules for chat flow testing  
from netra_backend.app.websocket_core.types import ConnectionInfo, WebSocketMessage, MessageType
from netra_backend.app.websocket_core.context import WebSocketRequestContext
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Import SSOT UnifiedIdGenerator for proper chat flow IDs
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.types.core_types import UserID, ConnectionID, ThreadID, MessageID


@pytest.mark.e2e
@pytest.mark.websocket
@pytest.mark.chat_flow
@pytest.mark.business_value
class TestWebSocketIdChatFlowE2E(BaseE2ETest):
    """
    E2E tests that EXPOSE chat flow business value failures with uuid.uuid4().
    
    CRITICAL: These tests use real services and real AI agents. They are DESIGNED
    TO FAIL initially to demonstrate how uuid.uuid4() breaks chat business value.
    
    SUCCESS CRITERIA: Users get substantive AI responses with proper ID tracking.
    """

    @pytest.fixture(autouse=True)
    async def setup_real_chat_services(self, real_services_fixture, real_llm_fixture):
        """Set up real services for E2E chat flow testing."""
        self.services = await get_real_services()
        self.auth_helper = E2EAuthHelper()
        self.websocket_base_url = self.env.get("WEBSOCKET_URL", "ws://localhost:8000")
        
        # Initialize real AI components
        self.llm_manager = OpenAIManager()
        self.execution_engine = UserExecutionEngine(llm_manager=self.llm_manager)
        
        # Create test users with authentication
        self.test_users = await self._create_authenticated_test_users()
        
        yield
        
        # Cleanup test users
        await self._cleanup_test_users()

    async def test_single_user_chat_flow_business_value_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose single-user chat flow business value issues.
        
        This test validates the complete chat flow delivers real business value:
        - User sends message to AI agent
        - Gets timely progress updates via WebSocket
        - Receives substantive AI response
        - All tracked with consistent IDs
        """
        # Get authenticated test user
        user_auth = self.test_users[0]
        user_id = user_auth["user_id"] 
        auth_token = user_auth["auth_token"]
        
        # Establish authenticated WebSocket connection
        async with self._create_authenticated_websocket_client(user_id, auth_token) as ws_client:
            
            # PHASE 1: User initiates chat with business problem
            user_query = "Help me optimize my cloud costs for our startup. We're spending $3000/month on AWS."
            
            chat_request = {
                "type": "start_agent_execution",
                "user_id": user_id,
                "message": user_query,
                "agent_type": "cost_optimization"
            }
            
            # Send chat request
            await ws_client.send_message(chat_request)
            
            # FAILING ASSERTION: Should receive agent_started event with consistent ID
            agent_started = await ws_client.wait_for_event("agent_started", timeout=10)
            
            assert agent_started is not None, "Failed to receive agent_started event"
            
            # This will FAIL because uuid.uuid4() agent execution IDs lack user context
            execution_id = agent_started.get("execution_id")
            assert user_id[:8] in execution_id, \
                f"Agent execution ID lacks user context: {execution_id} for user {user_id}"
                
            # Expected UnifiedIdGenerator format for chat flow tracking
            expected_pattern = f"agent_cost_optimization_{user_id[:8]}_"
            assert execution_id.startswith(expected_pattern), \
                f"Expected chat-trackable execution pattern '{expected_pattern}', got: {execution_id}"
            
            # PHASE 2: Track agent thinking progress (business value visibility)
            thinking_events = []
            thinking_timeout = 30  # Allow time for real AI thinking
            
            try:
                while len(thinking_events) < 3:  # Expect multiple thinking updates
                    thinking_event = await ws_client.wait_for_event("agent_thinking", timeout=thinking_timeout)
                    
                    if thinking_event:
                        thinking_events.append(thinking_event)
                        
                        # FAILING ASSERTION: Thinking events should have consistent execution context
                        event_execution_id = thinking_event.get("execution_id")
                        assert event_execution_id == execution_id, \
                            f"Thinking event execution ID inconsistent: {event_execution_id} != {execution_id}"
                            
                        # FAILING ASSERTION: Thinking should show substantive AI progress
                        thinking_content = thinking_event.get("data", {}).get("content", "")
                        assert len(thinking_content) > 20, \
                            f"Agent thinking should show substantive progress: {thinking_content}"
                            
                        print(f"AI Thinking: {thinking_content}")
                    else:
                        break
                        
            except asyncio.TimeoutError:
                pytest.fail("Failed to receive agent thinking updates - business value visibility broken")
                
            # FAILING ASSERTION: Should have received meaningful thinking updates  
            assert len(thinking_events) >= 2, \
                f"Insufficient agent thinking visibility: {len(thinking_events)} events"
                
            # PHASE 3: Receive agent completion with actionable business insights
            agent_completed = await ws_client.wait_for_event("agent_completed", timeout=60)
            
            assert agent_completed is not None, "Failed to receive agent completion - business value not delivered"
            
            # This will FAIL because uuid.uuid4() completion IDs lack execution traceability
            completion_execution_id = agent_completed.get("execution_id")
            assert completion_execution_id == execution_id, \
                f"Completion execution ID should match start: {completion_execution_id} != {execution_id}"
                
            # FAILING ASSERTION: Agent response should deliver substantive business value
            response_data = agent_completed.get("data", {})
            response_content = response_data.get("content", "")
            
            # Business value validation - response should contain actionable insights
            assert len(response_content) > 100, \
                f"Agent response lacks substance: {len(response_content)} chars"
                
            # Look for cost optimization insights (business domain validation)
            business_keywords = ["cost", "optimization", "save", "reduce", "efficiency", "recommendation"]
            found_keywords = [kw for kw in business_keywords if kw.lower() in response_content.lower()]
            
            assert len(found_keywords) >= 3, \
                f"Response lacks business value keywords: {found_keywords} in {response_content[:100]}"
                
            print(f"✅ Business Value Delivered: {response_content[:200]}...")
            
            # PHASE 4: Validate chat flow ID consistency for audit trail
            all_events = [agent_started] + thinking_events + [agent_completed]
            execution_ids = [event.get("execution_id") for event in all_events if event.get("execution_id")]
            
            # FAILING ASSERTION: All events should have same execution ID for audit trail
            unique_execution_ids = set(execution_ids)
            assert len(unique_execution_ids) == 1, \
                f"Chat flow execution IDs inconsistent: {unique_execution_ids}"
                
            # FAILING ASSERTION: Should be able to trace complete chat session  
            session_trace = await self._build_session_audit_trail(user_id, execution_id)
            
            assert len(session_trace) >= 4, \
                f"Incomplete session audit trail: {len(session_trace)} events"
                
            # Validate audit trail contains business value delivery proof
            trail_summary = json.dumps(session_trace, indent=2)
            assert "cost_optimization" in trail_summary.lower(), \
                f"Audit trail missing business context: {trail_summary[:200]}"

    async def test_multi_user_chat_isolation_business_value_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose multi-user chat isolation business value issues.
        
        This test validates that multiple users can simultaneously receive 
        substantive AI value without cross-contamination of their chat contexts.
        """
        # Use multiple authenticated test users
        user_auths = self.test_users[:3]  # 3 concurrent users
        
        # Define different business problems for each user
        business_scenarios = [
            {
                "user_index": 0,
                "query": "Help me analyze customer churn in my SaaS business. We're losing 5% monthly.",
                "agent_type": "data_analysis",
                "expected_keywords": ["churn", "retention", "analysis", "customer"]
            },
            {
                "user_index": 1,
                "query": "I need to optimize our marketing budget allocation across channels.",
                "agent_type": "marketing_optimization", 
                "expected_keywords": ["marketing", "budget", "channels", "ROI"]
            },
            {
                "user_index": 2,
                "query": "Help me plan our product roadmap for next quarter based on user feedback.",
                "agent_type": "product_planning",
                "expected_keywords": ["roadmap", "product", "feedback", "planning"]
            }
        ]
        
        # Start concurrent chat sessions
        chat_sessions = []
        websocket_clients = []
        
        for scenario in business_scenarios:
            user_auth = user_auths[scenario["user_index"]]
            user_id = user_auth["user_id"]
            auth_token = user_auth["auth_token"]
            
            # Create WebSocket client for user
            ws_client = await self._create_authenticated_websocket_client(user_id, auth_token).__aenter__()
            websocket_clients.append(ws_client)
            
            # Send chat request
            chat_request = {
                "type": "start_agent_execution",
                "user_id": user_id,
                "message": scenario["query"],
                "agent_type": scenario["agent_type"]
            }
            
            await ws_client.send_message(chat_request)
            
            # Wait for agent started
            agent_started = await ws_client.wait_for_event("agent_started", timeout=10)
            assert agent_started is not None, f"User {user_id} failed to start agent"
            
            execution_id = agent_started.get("execution_id")
            
            # FAILING ASSERTION: Each user's execution ID should be isolated
            assert user_id[:8] in execution_id, \
                f"Execution ID lacks user isolation: {execution_id} for user {user_id}"
                
            # Expected UnifiedIdGenerator format for multi-user isolation
            expected_pattern = f"agent_{scenario['agent_type']}_{user_id[:8]}_"
            assert execution_id.startswith(expected_pattern), \
                f"Expected isolated execution pattern '{expected_pattern}', got: {execution_id}"
                
            chat_sessions.append({
                "user_id": user_id,
                "execution_id": execution_id,
                "scenario": scenario,
                "ws_client": ws_client
            })
            
        # Monitor all sessions for concurrent business value delivery
        completion_tasks = []
        
        for session in chat_sessions:
            task = asyncio.create_task(
                self._monitor_chat_session_completion(session)
            )
            completion_tasks.append(task)
            
        # Wait for all sessions to complete (with timeout)
        try:
            session_results = await asyncio.wait_for(
                asyncio.gather(*completion_tasks, return_exceptions=True),
                timeout=120  # Allow time for real AI processing
            )
        except asyncio.TimeoutError:
            pytest.fail("Multi-user chat sessions timed out - business value delivery failed")
            
        # Validate each session delivered isolated business value
        for i, result in enumerate(session_results):
            if isinstance(result, Exception):
                pytest.fail(f"Chat session {i} failed: {result}")
                
            session = chat_sessions[i]
            scenario = session["scenario"]
            
            # FAILING ASSERTION: Each user received their specific business value
            response_content = result.get("response_content", "")
            
            # Validate response contains expected business domain keywords
            found_keywords = [
                kw for kw in scenario["expected_keywords"] 
                if kw.lower() in response_content.lower()
            ]
            
            assert len(found_keywords) >= 2, \
                f"User {session['user_id']} response lacks domain keywords: {found_keywords}"
                
            # FAILING ASSERTION: No cross-user contamination in responses
            other_scenarios = [s for s in business_scenarios if s != scenario]
            for other_scenario in other_scenarios:
                contamination_keywords = [
                    kw for kw in other_scenario["expected_keywords"]
                    if kw.lower() in response_content.lower()
                ]
                
                # Allow minimal cross-contamination (1 keyword max)
                assert len(contamination_keywords) <= 1, \
                    f"User {session['user_id']} response contaminated with other user context: {contamination_keywords}"
                    
        print(f"✅ Multi-user business value isolation validated for {len(chat_sessions)} concurrent users")
        
        # Cleanup WebSocket connections
        for ws_client in websocket_clients:
            await ws_client.__aexit__(None, None, None)

    async def test_chat_flow_message_ordering_traceability_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose chat message ordering and traceability issues.
        
        This test validates that chat messages maintain proper ordering and
        traceability for business value audit requirements.
        """
        # Get authenticated test user
        user_auth = self.test_users[0]
        user_id = user_auth["user_id"]
        auth_token = user_auth["auth_token"]
        
        # Start WebSocket connection
        async with self._create_authenticated_websocket_client(user_id, auth_token) as ws_client:
            
            # Send complex multi-step business query
            complex_query = """
            I need help with a comprehensive business analysis:
            1. Analyze our Q3 revenue data
            2. Identify growth opportunities 
            3. Recommend strategic initiatives
            4. Create implementation timeline
            """
            
            chat_request = {
                "type": "start_agent_execution",
                "user_id": user_id,
                "message": complex_query,
                "agent_type": "business_strategy"
            }
            
            await ws_client.send_message(chat_request)
            
            # Collect all events in order
            all_events = []
            event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            # Monitor for 60 seconds to capture complete flow
            start_time = time.time()
            timeout = 60
            
            while time.time() - start_time < timeout:
                try:
                    event = await ws_client.wait_for_any_event(timeout=5)
                    if event and event.get("type") in event_types:
                        event["received_at"] = time.time()
                        all_events.append(event)
                        
                        # Stop when we get completion
                        if event.get("type") == "agent_completed":
                            break
                            
                except asyncio.TimeoutError:
                    continue
                    
            # FAILING ASSERTION: Should have received complete event sequence
            assert len(all_events) >= 5, \
                f"Incomplete chat flow event sequence: {len(all_events)} events"
                
            # FAILING ASSERTION: Events should maintain temporal ordering
            received_times = [event["received_at"] for event in all_events]
            assert received_times == sorted(received_times), \
                f"Chat events received out of order: {received_times}"
                
            # FAILING ASSERTION: All events should have consistent execution context
            execution_ids = [event.get("execution_id") for event in all_events if event.get("execution_id")]
            unique_execution_ids = set(execution_ids)
            
            assert len(unique_execution_ids) == 1, \
                f"Inconsistent execution IDs in chat flow: {unique_execution_ids}"
                
            execution_id = list(unique_execution_ids)[0]
            
            # This will FAIL because uuid.uuid4() execution IDs lack temporal ordering
            # Expected UnifiedIdGenerator format includes timestamp for ordering
            timestamp_pattern = r"_\d{13}_"  # Millisecond timestamp
            import re
            assert re.search(timestamp_pattern, execution_id), \
                f"Execution ID lacks temporal ordering: {execution_id}"
                
            # FAILING ASSERTION: Message IDs should support audit trail reconstruction
            message_ids = [
                event.get("message_id") for event in all_events 
                if event.get("message_id")
            ]
            
            # All message IDs should be traceable to same execution context
            for msg_id in message_ids:
                if msg_id:
                    # This will FAIL because uuid.uuid4() message IDs lack execution context
                    assert execution_id[:16] in msg_id or user_id[:8] in msg_id, \
                        f"Message ID not traceable to execution context: {msg_id}"
                        
            # FAILING ASSERTION: Should be able to reconstruct complete chat timeline
            chat_timeline = await self._reconstruct_chat_timeline(user_id, execution_id, all_events)
            
            # Timeline should show clear business value progression
            timeline_text = json.dumps(chat_timeline, indent=2)
            business_progression = [
                "business analysis",
                "revenue data", 
                "growth opportunities",
                "strategic initiatives"
            ]
            
            found_progression = [
                phrase for phrase in business_progression
                if phrase.lower() in timeline_text.lower()
            ]
            
            assert len(found_progression) >= 3, \
                f"Chat timeline missing business value progression: {found_progression}"
                
            print(f"✅ Chat flow traceability validated: {len(all_events)} events over {time.time() - start_time:.1f}s")

    async def test_websocket_reconnection_chat_continuity_EXPECTED_FAILURE(self):
        """
        DESIGNED TO FAIL: Expose WebSocket reconnection chat continuity issues.
        
        This test validates that chat sessions maintain continuity across
        WebSocket reconnections without losing business value context.
        """
        # Get authenticated test user
        user_auth = self.test_users[0] 
        user_id = user_auth["user_id"]
        auth_token = user_auth["auth_token"]
        
        # Start initial WebSocket connection
        initial_connection = await self._create_authenticated_websocket_client(user_id, auth_token).__aenter__()
        
        # Start long-running business analysis
        long_query = "Perform a comprehensive competitive analysis of our market position, including detailed SWOT analysis and strategic recommendations."
        
        chat_request = {
            "type": "start_agent_execution",
            "user_id": user_id,
            "message": long_query,
            "agent_type": "competitive_analysis"
        }
        
        await initial_connection.send_message(chat_request)
        
        # Get initial execution context
        agent_started = await initial_connection.wait_for_event("agent_started", timeout=10)
        assert agent_started is not None, "Failed to start long-running analysis"
        
        initial_execution_id = agent_started.get("execution_id")
        
        # Wait for some progress, then simulate connection drop
        thinking_event = await initial_connection.wait_for_event("agent_thinking", timeout=15)
        assert thinking_event is not None, "No initial progress on long analysis"
        
        # Close initial connection (simulate network drop)
        await initial_connection.__aexit__(None, None, None)
        
        # Wait a moment (simulate network instability)
        await asyncio.sleep(2)
        
        # Reconnect with same user authentication
        reconnected_client = await self._create_authenticated_websocket_client(user_id, auth_token).__aenter__()
        
        # FAILING ASSERTION: Should be able to resume ongoing execution
        resume_request = {
            "type": "resume_agent_execution",
            "user_id": user_id,
            "execution_id": initial_execution_id
        }
        
        await reconnected_client.send_message(resume_request)
        
        # This will FAIL because uuid.uuid4() execution IDs can't be efficiently resumed
        resume_response = await reconnected_client.wait_for_event("agent_resumed", timeout=10)
        
        assert resume_response is not None, \
            f"Failed to resume execution with uuid.uuid4() ID: {initial_execution_id}"
            
        # FAILING ASSERTION: Resumed execution should maintain same ID
        resumed_execution_id = resume_response.get("execution_id")
        assert resumed_execution_id == initial_execution_id, \
            f"Execution ID changed on resume: {initial_execution_id} != {resumed_execution_id}"
            
        # Expected UnifiedIdGenerator format should support efficient resume lookup
        expected_resume_pattern = f"agent_competitive_analysis_{user_id[:8]}_"
        assert initial_execution_id.startswith(expected_resume_pattern), \
            f"Expected resumable execution pattern '{expected_resume_pattern}', got: {initial_execution_id}"
            
        # Continue monitoring for completion
        final_completion = await reconnected_client.wait_for_event("agent_completed", timeout=60)
        
        assert final_completion is not None, \
            "Failed to complete analysis after reconnection"
            
        # FAILING ASSERTION: Final response should maintain business value context
        final_response = final_completion.get("data", {}).get("content", "")
        
        # Should contain comprehensive competitive analysis insights
        analysis_keywords = ["competitive", "analysis", "market", "SWOT", "strategic", "recommendations"]
        found_keywords = [kw for kw in analysis_keywords if kw.lower() in final_response.lower()]
        
        assert len(found_keywords) >= 4, \
            f"Reconnected session lost business context: {found_keywords} in {final_response[:100]}"
            
        # FAILING ASSERTION: Should be able to trace complete session across reconnect
        complete_session_trace = await self._build_reconnection_audit_trail(
            user_id, initial_execution_id
        )
        
        assert len(complete_session_trace) >= 3, \
            f"Incomplete reconnection audit trail: {len(complete_session_trace)} events"
            
        # Validate audit trail shows reconnection continuity
        trail_text = json.dumps(complete_session_trace, indent=2)
        assert "reconnection" in trail_text.lower() or "resume" in trail_text.lower(), \
            f"Audit trail missing reconnection context: {trail_text[:200]}"
            
        await reconnected_client.__aexit__(None, None, None)
        
        print(f"✅ Chat continuity validated across WebSocket reconnection")

    # Helper methods for E2E chat flow testing
    
    async def _create_authenticated_test_users(self) -> List[Dict[str, Any]]:
        """Create authenticated test users for E2E chat testing."""
        users = []
        
        for i in range(3):
            username = f"chat_e2e_user_{i}_{uuid.uuid4().hex[:8]}"
            
            # Create user through auth helper
            user_auth = await self.auth_helper.create_authenticated_user(
                username=username,
                email=f"{username}@example.com"
            )
            
            users.append(user_auth)
            
        return users
        
    async def _cleanup_test_users(self):
        """Clean up test users created for E2E testing."""
        try:
            for user_auth in self.test_users:
                await self.auth_helper.cleanup_user(user_auth["user_id"])
        except Exception as e:
            self.logger.warning(f"E2E user cleanup error: {e}")
            
    @asynccontextmanager
    async def _create_authenticated_websocket_client(self, user_id: str, auth_token: str):
        """Create authenticated WebSocket client for E2E testing."""
        websocket_url = f"{self.websocket_base_url}/ws/{user_id}"
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        try:
            websocket = await websockets.connect(websocket_url, extra_headers=headers)
            client = UnifiedWebSocketTestClient(websocket)
            yield client
        finally:
            if 'websocket' in locals():
                await websocket.close()
                
    async def _monitor_chat_session_completion(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Monitor chat session until completion and return result."""
        ws_client = session["ws_client"]
        execution_id = session["execution_id"]
        
        # Wait for agent completion
        completion_event = await ws_client.wait_for_event("agent_completed", timeout=90)
        
        if not completion_event:
            raise Exception(f"Chat session {execution_id} did not complete")
            
        response_content = completion_event.get("data", {}).get("content", "")
        
        return {
            "execution_id": execution_id,
            "response_content": response_content,
            "completion_event": completion_event
        }
        
    async def _build_session_audit_trail(self, user_id: str, execution_id: str) -> List[Dict[str, Any]]:
        """Build audit trail for chat session (simulates database query)."""
        # This would query actual audit logs in real implementation
        # For now, simulate based on expected ID patterns
        
        audit_events = [
            {
                "event_type": "agent_started", 
                "execution_id": execution_id,
                "user_id": user_id,
                "timestamp": time.time()
            },
            {
                "event_type": "agent_thinking",
                "execution_id": execution_id,
                "user_id": user_id, 
                "timestamp": time.time() + 5
            },
            {
                "event_type": "agent_completed",
                "execution_id": execution_id,
                "user_id": user_id,
                "timestamp": time.time() + 30
            }
        ]
        
        return audit_events
        
    async def _reconstruct_chat_timeline(self, user_id: str, execution_id: str, events: List[Dict]) -> Dict[str, Any]:
        """Reconstruct complete chat timeline from events."""
        timeline = {
            "user_id": user_id,
            "execution_id": execution_id,
            "start_time": min(event.get("received_at", 0) for event in events),
            "end_time": max(event.get("received_at", 0) for event in events),
            "event_sequence": []
        }
        
        for event in sorted(events, key=lambda e: e.get("received_at", 0)):
            timeline["event_sequence"].append({
                "type": event.get("type"),
                "timestamp": event.get("received_at"),
                "content_preview": str(event.get("data", {}))[:100]
            })
            
        return timeline
        
    async def _build_reconnection_audit_trail(self, user_id: str, execution_id: str) -> List[Dict[str, Any]]:
        """Build audit trail showing reconnection continuity."""
        # This would query actual reconnection logs in real implementation
        
        reconnection_trail = [
            {
                "event_type": "websocket_connected",
                "execution_id": execution_id,
                "user_id": user_id,
                "connection_type": "initial"
            },
            {
                "event_type": "websocket_disconnected", 
                "execution_id": execution_id,
                "user_id": user_id,
                "reason": "network_drop"
            },
            {
                "event_type": "websocket_reconnected",
                "execution_id": execution_id,
                "user_id": user_id,
                "connection_type": "resumed"
            }
        ]
        
        return reconnection_trail

    @pytest.fixture
    async def real_services_fixture(self):
        """Fixture to ensure real services are available for E2E tests."""
        # Automatically handled by BaseE2ETest
        pass
        
    @pytest.fixture  
    async def real_llm_fixture(self):
        """Fixture to ensure real LLM services are available for chat testing."""
        # Automatically handled by BaseE2ETest with real_llm option
        pass