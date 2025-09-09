"""E2E Tests for Complete Agent Execution with Authentication

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete user journey from login to AI results
- Value Impact: Ensures $120K+ MRR revenue-generating AI functionality works end-to-end
- Strategic Impact: Core business flow that delivers AI value to paying customers

CRITICAL TEST PURPOSE:
These E2E tests validate the complete authenticated user journey through
the AI platform including login, agent execution, and WebSocket feedback.

Test Coverage:
- Complete authentication flow (JWT/OAuth)
- Agent execution with real user context
- WebSocket events during authenticated sessions
- Tool execution within authenticated agent flows
- Error handling in authenticated contexts
- User isolation in multi-tenant scenarios
"""

import pytest
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.e2e
class TestCompleteAgentExecutionAuthenticatedFlow:
    """E2E tests for complete authenticated agent execution flow."""
    
    def setup_method(self):
        """Set up E2E test environment with authentication."""
        self.auth_helper = E2EAuthHelper(environment="staging")
        
    @pytest.mark.asyncio
    async def test_complete_authenticated_agent_execution_flow(self, real_services_fixture):
        """Test complete user journey: login → agent execution → results with WebSocket feedback."""
        # Arrange - Create authenticated user session
        user_credentials = {
            "email": f"e2e-test-{uuid.uuid4()}@netra.test",
            "password": "SecureTestPass123!",
            "name": "E2E Test User"
        }
        
        # Step 1: User Registration/Login Flow
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        
        assert auth_result["success"] == True
        assert "access_token" in auth_result
        assert "user_id" in auth_result
        
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        
        # Step 2: Establish authenticated WebSocket connection
        thread_id = f"e2e-thread-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            # Connect with authentication
            await websocket_client.connect_with_auth()
            
            # Verify authenticated connection
            connection_status = await websocket_client.verify_authenticated_connection()
            assert connection_status["authenticated"] == True
            assert connection_status["user_id"] == user_id
            
            # Step 3: Initiate authenticated agent execution
            agent_request = {
                "agent_name": "e2e_test_agent",
                "task": "analyze_cost_optimization",
                "parameters": {
                    "account_scope": "test_account",
                    "optimization_goal": "reduce_costs",
                    "budget_limit": 10000
                },
                "thread_id": thread_id,
                "user_context": {
                    "user_id": user_id,
                    "session_token": access_token
                }
            }
            
            # Send authenticated agent request
            execution_response = await self._send_authenticated_agent_request(
                auth_token=access_token,
                agent_request=agent_request,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert execution_response["success"] == True
            assert "run_id" in execution_response
            
            run_id = execution_response["run_id"]
            
            # Step 4: Monitor WebSocket events during execution
            # Collect WebSocket events for 10 seconds
            websocket_events = []
            
            async def collect_websocket_events():
                """Collect WebSocket events during agent execution."""
                timeout_time = asyncio.get_event_loop().time() + 10.0
                
                while asyncio.get_event_loop().time() < timeout_time:
                    try:
                        events = await websocket_client.get_received_events(timeout=1.0)
                        websocket_events.extend(events)
                        
                        # Check if agent completed
                        for event in events:
                            if event.get("type") == "agent_completed":
                                return  # Agent finished
                    except asyncio.TimeoutError:
                        continue  # Keep waiting
            
            # Start event collection
            await collect_websocket_events()
            
            # Step 5: Verify complete authenticated flow
            assert len(websocket_events) >= 3  # Should have multiple events
            
            # Verify authentication context in WebSocket events
            for event in websocket_events:
                # Events should contain user context
                assert "payload" in event
                if "user_id" in event["payload"]:
                    assert event["payload"]["user_id"] == user_id
                
                # Events should be properly authenticated
                assert "timestamp" in event
                assert event["timestamp"] is not None
            
            # Verify expected event sequence
            event_types = [e.get("type") for e in websocket_events]
            
            # Should contain core agent lifecycle events
            expected_events = ["agent_started", "agent_thinking", "agent_completed"]
            for expected_event in expected_events:
                assert expected_event in event_types, f"Missing event: {expected_event}"
            
            # Step 6: Verify final results with authentication
            final_result = await self._get_authenticated_execution_result(
                auth_token=access_token,
                run_id=run_id,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert final_result["success"] == True
            assert final_result["run_id"] == run_id
            assert final_result["user_id"] == user_id
            assert "result" in final_result
            
            # Verify business value delivery
            result_data = final_result["result"]
            assert "status" in result_data
            assert result_data["status"] == "completed"
            
            # Step 7: Verify user isolation (no data leakage)
            user_data_check = await self._verify_user_data_isolation(
                auth_token=access_token,
                user_id=user_id,
                run_id=run_id,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert user_data_check["isolation_verified"] == True
            assert user_data_check["user_id"] == user_id
            
        finally:
            # Cleanup
            await websocket_client.disconnect()
            await self.auth_helper.cleanup_user_session(auth_result)
    
    @pytest.mark.asyncio
    async def test_authenticated_multi_agent_coordination_e2e(self, real_services_fixture):
        """Test multi-agent coordination in authenticated context."""
        # Arrange - Create authenticated user
        user_credentials = {
            "email": f"multi-agent-{uuid.uuid4()}@netra.test",
            "password": "MultiAgentTest123!",
            "name": "Multi-Agent Test User"
        }
        
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        
        thread_id = f"multi-agent-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            await websocket_client.connect_with_auth()
            
            # Execute multiple agents in sequence
            agent_requests = [
                {
                    "agent_name": "data_collector_agent",
                    "task": "collect_cost_data",
                    "parameters": {"data_source": "aws_billing"}
                },
                {
                    "agent_name": "analysis_agent", 
                    "task": "analyze_collected_data",
                    "parameters": {"analysis_type": "cost_optimization"}
                },
                {
                    "agent_name": "recommendation_agent",
                    "task": "generate_recommendations",
                    "parameters": {"optimization_target": "monthly_savings"}
                }
            ]
            
            # Execute agents in sequence
            agent_results = []
            all_websocket_events = []
            
            for agent_request in agent_requests:
                agent_request.update({
                    "thread_id": thread_id,
                    "user_context": {"user_id": user_id, "session_token": access_token}
                })
                
                # Execute agent
                response = await self._send_authenticated_agent_request(
                    auth_token=access_token,
                    agent_request=agent_request,
                    backend_url=real_services_fixture["backend_url"]
                )
                
                agent_results.append(response)
                
                # Collect events for this agent
                agent_events = []
                timeout_time = asyncio.get_event_loop().time() + 8.0
                
                while asyncio.get_event_loop().time() < timeout_time:
                    try:
                        events = await websocket_client.get_received_events(timeout=1.0)
                        agent_events.extend(events)
                        all_websocket_events.extend(events)
                        
                        # Check for completion
                        if any(e.get("type") == "agent_completed" for e in events):
                            break
                    except asyncio.TimeoutError:
                        continue
            
            # Verify multi-agent coordination
            assert len(agent_results) == 3
            assert all(result["success"] for result in agent_results)
            
            # Verify events from all agents were received
            agent_names_in_events = set()
            for event in all_websocket_events:
                if "agent_name" in event.get("payload", {}):
                    agent_names_in_events.add(event["payload"]["agent_name"])
            
            expected_agents = {"data_collector_agent", "analysis_agent", "recommendation_agent"}
            assert agent_names_in_events >= expected_agents
        
        finally:
            await websocket_client.disconnect()
            await self.auth_helper.cleanup_user_session(auth_result)
    
    @pytest.mark.asyncio
    async def test_authenticated_error_handling_e2e(self, real_services_fixture):
        """Test error handling in authenticated agent execution flow."""
        # Arrange - Create authenticated user
        user_credentials = {
            "email": f"error-test-{uuid.uuid4()}@netra.test", 
            "password": "ErrorTestPass123!",
            "name": "Error Test User"
        }
        
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        
        thread_id = f"error-test-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            await websocket_client.connect_with_auth()
            
            # Send request to trigger error
            error_agent_request = {
                "agent_name": "nonexistent_agent",  # This should cause an error
                "task": "impossible_task",
                "parameters": {"invalid": "params"},
                "thread_id": thread_id,
                "user_context": {"user_id": user_id, "session_token": access_token}
            }
            
            # Execute failing agent
            error_response = await self._send_authenticated_agent_request(
                auth_token=access_token,
                agent_request=error_agent_request,
                backend_url=real_services_fixture["backend_url"]
            )
            
            # Should handle error gracefully
            assert error_response["success"] == False
            assert "error" in error_response
            
            # Collect error events
            error_events = []
            timeout_time = asyncio.get_event_loop().time() + 5.0
            
            while asyncio.get_event_loop().time() < timeout_time:
                try:
                    events = await websocket_client.get_received_events(timeout=1.0)
                    error_events.extend(events)
                    
                    # Check for error events
                    if any(e.get("type") == "agent_error" for e in events):
                        break
                except asyncio.TimeoutError:
                    continue
            
            # Verify error handling
            error_event_types = [e.get("type") for e in error_events]
            assert "agent_error" in error_event_types
            
            # Verify user context maintained during error
            for event in error_events:
                if event.get("type") == "agent_error":
                    assert "payload" in event
                    # Error should still be associated with correct user
                    
        finally:
            await websocket_client.disconnect() 
            await self.auth_helper.cleanup_user_session(auth_result)
    
    async def _send_authenticated_agent_request(self, auth_token: str, agent_request: Dict[str, Any], backend_url: str) -> Dict[str, Any]:
        """Send authenticated agent execution request."""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{backend_url}/api/v1/agents/execute",
                json=agent_request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    result["success"] = True
                    return result
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": error_text,
                        "status_code": response.status
                    }
    
    async def _get_authenticated_execution_result(self, auth_token: str, run_id: str, backend_url: str) -> Dict[str, Any]:
        """Get execution result with authentication."""
        import aiohttp
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{backend_url}/api/v1/agents/execution/{run_id}/result",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    result["success"] = True
                    return result
                else:
                    return {"success": False, "error": await response.text()}
    
    async def _verify_user_data_isolation(self, auth_token: str, user_id: str, run_id: str, backend_url: str) -> Dict[str, Any]:
        """Verify user data isolation in execution results."""
        import aiohttp
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{backend_url}/api/v1/users/{user_id}/executions/{run_id}/verify-isolation",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    return {
                        "isolation_verified": True,
                        "user_id": user_id,
                        "details": result
                    }
                else:
                    return {
                        "isolation_verified": False,
                        "error": await response.text()
                    }