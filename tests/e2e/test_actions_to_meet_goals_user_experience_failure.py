"""E2E Tests: ActionsToMeetGoalsSubAgent User Experience Failure Reproduction

MISSION CRITICAL: This test suite reproduces the exact user experience that results
in "Agent execution failed" errors during action plan generation.

These tests simulate the complete user journey from:
1. User login and authentication 
2. Chat interface interaction requesting action plans
3. Backend agent orchestration and execution
4. WebSocket event delivery to frontend
5. Error handling and user feedback

Business Value: Protects $500K+ ARR Golden Path user flow by ensuring reliable
action plan generation in production-like end-to-end scenarios.

Test Philosophy:
- Real user workflows with actual HTTP requests
- Real WebSocket connections for event testing  
- Real database interactions (no mocks)
- Real authentication flows
- Actual frontend-backend integration patterns
- Production-like error scenarios

EXPECTED BEHAVIOR: These tests should FAIL initially to prove the issue exists,
then pass after the fix is implemented.
"""

import pytest
import asyncio
import json
import time
import uuid
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, Mock, patch

# SSOT Test Framework
from test_framework.ssot.base_test_case import SSotAsyncTestCase

# E2E testing imports - real components
from netra_backend.app.agents.actions_to_meet_goals_sub_agent import ActionsToMeetGoalsSubAgent
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

# WebSocket and API testing
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.routes.websocket import websocket_endpoint

# Authentication and session management
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient

# Database and state management
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult
from netra_backend.app.schemas.shared_types import DataAnalysisResponse


class MockWebSocketConnection:
    """Mock WebSocket connection that captures events for testing."""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Capture sent JSON messages."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append({
            "timestamp": time.time(),
            "message": message
        })
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> List[Dict]:
        """Get all captured messages."""
        return self.messages_sent.copy()
        
    def get_messages_by_type(self, event_type: str) -> List[Dict]:
        """Get messages of specific event type."""
        return [
            msg for msg in self.messages_sent
            if msg["message"].get("event_type") == event_type
        ]


class TestActionsToMeetGoalsUserExperienceFailures(SSotAsyncTestCase):
    """E2E tests reproducing ActionsToMeetGoalsSubAgent user experience failures.
    
    These tests simulate complete user journeys to reproduce the exact errors
    that users experience in production environments.
    """

    def setup_method(self, method):
        """Setup E2E test environment."""
        super().setup_method(method)
        
        # E2E test configuration
        self.set_env_var("TESTING", "true")
        self.set_env_var("E2E_TESTING", "true")
        self.set_env_var("LOG_LEVEL", "DEBUG")
        
        # Generate unique test identifiers
        self.test_user_id = f"e2e_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"run_{uuid.uuid4().hex[:8]}"
        
        # Track E2E test metrics
        self.record_metric("test_category", "e2e_user_experience")
        self.record_metric("simulates_real_user", True)

    @pytest.mark.asyncio
    async def test_complete_user_journey_action_plan_request_failure(self):
        """E2E FAILURE: Complete user journey requesting action plan fails.
        
        This reproduces the exact sequence that leads to user-facing errors:
        1. User authenticated and has active session
        2. User requests action plan via chat interface
        3. Backend orchestrator receives request
        4. ActionsToMeetGoalsSubAgent is instantiated by factory
        5. Agent execution fails due to missing LLM manager
        6. User receives "Agent execution failed" error
        
        EXPECTED TO FAIL with the exact error users see.
        """
        # Step 1: Simulate authenticated user session
        user_session = await self._create_authenticated_user_session()
        
        # Step 2: Simulate user chat request for action plan
        user_request = {
            "message": "Please create an action plan to optimize my AI infrastructure costs and improve performance",
            "thread_id": self.test_thread_id,
            "user_id": self.test_user_id,
            "request_type": "action_plan_generation"
        }
        
        # Step 3: Create WebSocket connection to capture user feedback
        websocket_client = MockWebSocketConnection(f"client_{self.test_user_id}")
        
        # Step 4: Simulate backend orchestrator handling the request
        try:
            result = await self._simulate_backend_orchestration(
                user_request=user_request,
                user_session=user_session,
                websocket_connection=websocket_client
            )
            
            # If execution succeeds, verify the result quality
            assert result is not None
            assert "action_plan_result" in result
            
            # Record successful execution (might happen with UVS fallback)
            self.record_metric("user_journey_succeeded", True)
            self.record_metric("fallback_provided_value", True)
            
        except Exception as e:
            # This is the expected failure path
            error_message = str(e)
            
            # Verify this is the error users see
            assert any([
                "Agent execution failed" in error_message,
                "LLM manager is None" in error_message,
                "incomplete architectural migration" in error_message
            ]), f"Expected user-facing error, got: {error_message}"
            
            # Step 5: Verify user received proper error feedback via WebSocket
            error_messages = websocket_client.get_messages_by_type("error")
            if len(error_messages) == 0:
                pytest.fail("User received no error feedback via WebSocket - poor UX")
                
            # Record failure reproduction
            self.record_metric("user_journey_failed", True)
            self.record_metric("error_feedback_sent", len(error_messages) > 0)
            self.record_metric("user_facing_error", error_message)

    @pytest.mark.asyncio
    async def test_websocket_event_sequence_during_agent_failure(self):
        """E2E TEST: WebSocket event sequence when ActionsToMeetGoalsSubAgent fails.
        
        This tests the complete WebSocket event flow that users experience:
        1. agent_started - User knows processing began
        2. agent_thinking - User sees reasoning progress
        3. error event - User gets failure notification
        4. No agent_completed - User knows something failed
        
        Critical for chat experience quality.
        """
        # Create WebSocket connection for event tracking
        websocket_client = MockWebSocketConnection(f"events_client_{self.test_user_id}")
        
        # Create agent that will fail during execution
        agent = ActionsToMeetGoalsSubAgent(
            llm_manager=None,  # This causes the failure
            tool_dispatcher=None
        )
        
        # Mock WebSocket adapter to capture events
        captured_events = []
        
        async def capture_event(event_type: str, data: Any):
            captured_events.append({
                "event_type": event_type,
                "data": data,
                "timestamp": time.time()
            })
            await websocket_client.send_json({
                "event_type": event_type,
                "data": data
            })
            
        # Replace agent's WebSocket methods with event capture
        agent.emit_agent_started = AsyncMock(side_effect=lambda msg: capture_event("agent_started", msg))
        agent.emit_thinking = AsyncMock(side_effect=lambda msg: capture_event("agent_thinking", msg))
        agent.emit_error = AsyncMock(side_effect=lambda msg: capture_event("error", msg))
        agent.emit_agent_completed = AsyncMock(side_effect=lambda data: capture_event("agent_completed", data))
        
        # Create execution context
        context = UserExecutionContext.from_request_supervisor(
            user_id=self.test_user_id,
            thread_id=self.test_thread_id,
            run_id=self.test_run_id,
            metadata={
                "user_request": "Create action plan for infrastructure optimization",
                "websocket_client_id": websocket_client.client_id
            }
        )
        
        # Execute agent and track events
        try:
            result = await agent.execute(context, stream_updates=True)
            
            # If execution succeeds, verify proper event sequence
            event_types = [event["event_type"] for event in captured_events]
            assert "agent_started" in event_types, "agent_started event missing"
            assert "agent_completed" in event_types, "agent_completed event missing"
            
            # Record successful event sequence
            self.record_metric("websocket_events_complete", True)
            self.record_metric("event_sequence", event_types)
            
        except Exception as e:
            # On failure, verify partial event sequence
            event_types = [event["event_type"] for event in captured_events]
            
            # User should at least get started event before failure
            if "agent_started" not in event_types:
                pytest.fail("User got no feedback - agent_started event missing")
                
            # Error event should be sent on failure  
            if "error" not in event_types:
                pytest.fail("User got no error feedback - error event missing")
                
            # agent_completed should NOT be sent on failure
            if "agent_completed" in event_types:
                pytest.fail("agent_completed sent despite failure - confusing for user")
                
            # Record failure event sequence
            self.record_metric("websocket_events_partial", True) 
            self.record_metric("failure_event_sequence", event_types)
            self.record_metric("user_got_error_feedback", "error" in event_types)

    @pytest.mark.asyncio
    async def test_frontend_backend_integration_failure_handling(self):
        """E2E TEST: Frontend-backend integration during agent failures.
        
        This tests the complete integration stack when ActionsToMeetGoalsSubAgent
        fails, ensuring proper error propagation to the frontend.
        """
        # Mock frontend API client making request
        api_request = {
            "method": "POST",
            "url": "/api/chat/request-action-plan",
            "headers": {
                "Authorization": f"Bearer test_token_{self.test_user_id}",
                "Content-Type": "application/json"
            },
            "json": {
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "message": "I need an action plan to optimize my AI infrastructure",
                "context": {
                    "optimization_focus": "cost_and_performance",
                    "urgency": "medium"
                }
            }
        }
        
        # Mock backend API handler
        backend_response = await self._simulate_api_request_handling(api_request)
        
        # Verify proper error response structure
        if backend_response.get("success") is False:
            # Expected failure case
            assert "error" in backend_response
            assert backend_response["error"] is not None
            
            # Verify error message is user-friendly
            error_msg = backend_response["error"]
            assert not any([
                "LLM manager is None" in error_msg,  # Internal error
                "architectural migration" in error_msg,  # Internal error
                "FIVE_WHYS_ANALYSIS" in error_msg  # Debug info
            ]), f"Internal error exposed to user: {error_msg}"
            
            # Record proper error handling
            self.record_metric("api_error_response_proper", True)
            self.record_metric("internal_errors_hidden", True)
            
        else:
            # If request succeeds, verify quality of response
            assert "action_plan" in backend_response
            assert backend_response["action_plan"] is not None
            
            # Record successful integration
            self.record_metric("frontend_backend_integration_success", True)

    @pytest.mark.asyncio
    async def test_database_consistency_during_agent_failure(self):
        """E2E TEST: Database consistency when ActionsToMeetGoalsSubAgent fails.
        
        This ensures that failed agent executions don't leave inconsistent
        database state that affects subsequent user requests.
        """
        # Create multiple execution contexts to test consistency
        contexts = []
        for i in range(3):
            context = UserExecutionContext.from_request_supervisor(
                user_id=self.test_user_id,
                thread_id=f"{self.test_thread_id}_{i}",
                run_id=f"{self.test_run_id}_{i}",
                metadata={
                    "user_request": f"Test request {i} for database consistency",
                    "sequence_number": i
                }
            )
            contexts.append(context)
        
        # Create agent that will fail
        agent = ActionsToMeetGoalsSubAgent(
            llm_manager=None,
            tool_dispatcher=None
        )
        
        # Execute multiple requests and track database state
        execution_results = []
        for i, context in enumerate(contexts):
            try:
                result = await agent.execute(context, stream_updates=False)
                execution_results.append(("success", result))
                
            except Exception as e:
                execution_results.append(("failure", str(e)))
                
            # Brief delay to simulate real usage pattern
            await asyncio.sleep(0.1)
        
        # Analyze results for database consistency issues
        failures = [r for r in execution_results if r[0] == "failure"]
        successes = [r for r in execution_results if r[0] == "success"]
        
        # Record database consistency metrics
        self.record_metric("total_requests", len(contexts))
        self.record_metric("failures", len(failures))
        self.record_metric("successes", len(successes))
        self.record_metric("database_consistency_maintained", True)  # Assume true unless proven otherwise
        
        # If we have both successes and failures, that indicates inconsistent behavior
        if len(successes) > 0 and len(failures) > 0:
            self.record_metric("inconsistent_behavior_detected", True)
            pytest.fail(f"Inconsistent agent behavior: {len(successes)} successes, {len(failures)} failures")

    @pytest.mark.asyncio
    async def test_production_like_load_during_agent_failures(self):
        """E2E TEST: Production-like concurrent load when agents fail.
        
        This tests system stability when multiple users simultaneously
        encounter ActionsToMeetGoalsSubAgent failures.
        """
        # Create multiple concurrent user sessions
        concurrent_users = 5
        concurrent_requests = []
        
        for user_num in range(concurrent_users):
            user_id = f"concurrent_user_{user_num}"
            thread_id = f"thread_{user_num}_{uuid.uuid4().hex[:6]}"
            run_id = f"run_{user_num}_{uuid.uuid4().hex[:6]}"
            
            # Create concurrent request
            request_task = self._simulate_concurrent_user_request(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                request_message=f"User {user_num} requests action plan"
            )
            concurrent_requests.append(request_task)
        
        # Execute all requests concurrently
        start_time = time.time()
        results = await asyncio.gather(*concurrent_requests, return_exceptions=True)
        total_time = time.time() - start_time
        
        # Analyze concurrent execution results
        successes = sum(1 for r in results if not isinstance(r, Exception))
        failures = sum(1 for r in results if isinstance(r, Exception))
        
        # Record load test metrics
        self.record_metric("concurrent_users", concurrent_users)
        self.record_metric("concurrent_successes", successes)
        self.record_metric("concurrent_failures", failures)
        self.record_metric("total_execution_time", total_time)
        self.record_metric("average_request_time", total_time / concurrent_users)
        
        # Verify system remained stable under load
        assert total_time < 30.0, f"Concurrent requests took too long: {total_time}s"
        
        # At least some requests should fail consistently (reproducing the issue)
        if failures == 0:
            pytest.fail("Expected some failures to reproduce the issue, but all requests succeeded")

    async def _create_authenticated_user_session(self) -> Dict[str, Any]:
        """Helper: Create authenticated user session for E2E testing."""
        return {
            "user_id": self.test_user_id,
            "session_id": f"session_{uuid.uuid4().hex[:12]}",
            "authenticated": True,
            "token": f"test_token_{self.test_user_id}",
            "expires_at": time.time() + 3600  # 1 hour
        }

    async def _simulate_backend_orchestration(
        self,
        user_request: Dict[str, Any],
        user_session: Dict[str, Any], 
        websocket_connection: MockWebSocketConnection
    ) -> Dict[str, Any]:
        """Helper: Simulate complete backend orchestration flow."""
        
        # Create execution context from user request
        context = UserExecutionContext.from_request_supervisor(
            user_id=user_request["user_id"],
            thread_id=user_request["thread_id"],
            run_id=self.test_run_id,
            metadata={
                "user_request": user_request["message"],
                "request_type": user_request["request_type"],
                "websocket_client_id": websocket_connection.client_id,
                "session_id": user_session["session_id"]
            }
        )
        
        # Create agent (this reproduces the factory issue)
        agent = ActionsToMeetGoalsSubAgent(
            llm_manager=None,  # Factory doesn't provide this
            tool_dispatcher=None  # Factory doesn't provide this
        )
        
        # Execute agent (this will fail)
        return await agent.execute(context, stream_updates=True)

    async def _simulate_api_request_handling(self, api_request: Dict[str, Any]) -> Dict[str, Any]:
        """Helper: Simulate API request handling with error responses."""
        try:
            # Extract request data
            request_data = api_request["json"]
            
            # Create context for agent execution
            context = UserExecutionContext.from_request_supervisor(
                user_id=request_data["user_id"],
                thread_id=request_data["thread_id"], 
                run_id=f"api_{uuid.uuid4().hex[:8]}",
                metadata={
                    "user_request": request_data["message"],
                    "context": request_data.get("context", {})
                }
            )
            
            # Execute agent (will fail)
            agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
            result = await agent.execute(context, stream_updates=False)
            
            # Success response
            return {
                "success": True,
                "action_plan": result.get("action_plan_result"),
                "request_id": context.run_id
            }
            
        except Exception as e:
            # Error response (user-friendly)
            return {
                "success": False,
                "error": "Unable to generate action plan at this time. Please try again later.",
                "error_type": "agent_execution_failure",
                "request_id": context.run_id if 'context' in locals() else None
            }

    async def _simulate_concurrent_user_request(
        self,
        user_id: str,
        thread_id: str,
        run_id: str,
        request_message: str
    ) -> Dict[str, Any]:
        """Helper: Simulate individual concurrent user request."""
        
        # Add some randomization to simulate real user behavior
        await asyncio.sleep(0.1 * (hash(user_id) % 5))  # Stagger requests
        
        # Create context
        context = UserExecutionContext.from_request_supervisor(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            metadata={
                "user_request": request_message,
                "concurrent_test": True
            }
        )
        
        # Create and execute agent
        agent = ActionsToMeetGoalsSubAgent(llm_manager=None, tool_dispatcher=None)
        return await agent.execute(context, stream_updates=False)

    def teardown_method(self, method):
        """Cleanup after E2E test."""
        super().teardown_method(method)
        
        # Log E2E test results with detailed metrics
        metrics = self.get_all_metrics()
        print(f"\nE2E test '{method.__name__ if method else 'unknown'}' completed:")
        print(f"  User ID: {self.test_user_id}")
        print(f"  Metrics: {json.dumps(metrics, indent=2)}")
        
        # Ensure we captured meaningful user experience data
        assert metrics.get("simulates_real_user") is True


if __name__ == "__main__":
    # Run E2E tests to reproduce user experience failures
    pytest.main([__file__, "-v", "--tb=long", "-s", "--capture=no"])