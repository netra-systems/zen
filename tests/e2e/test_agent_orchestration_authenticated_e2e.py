"""E2E Tests for Agent Orchestration with Authentication

Business Value Justification:
- Segment: Enterprise (complex multi-agent workflows)
- Business Goal: Ensure complex AI orchestration works in authenticated contexts
- Value Impact: Enables sophisticated AI-driven business process automation
- Strategic Impact: Advanced platform capability for enterprise customers

CRITICAL TEST PURPOSE:
These E2E tests validate complex agent orchestration scenarios with
authentication to ensure enterprise-grade AI workflow capabilities.

Test Coverage:
- Multi-agent orchestration with authentication
- Agent handoff and state transfer in authenticated contexts
- Complex workflow execution with user permissions
- Error recovery in orchestrated authenticated flows
- Resource coordination between authenticated agents
"""

import pytest
import asyncio
import uuid

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from test_framework.ssot.real_services_test_fixtures import *
from netra_backend.app.services.user_execution_context import UserExecutionContext


@pytest.mark.e2e
class TestAgentOrchestrationAuthenticatedE2E:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.from_request(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """E2E tests for agent orchestration with authentication."""
    
    def setup_method(self):
        """Set up E2E test environment."""
        self.auth_helper = E2EAuthHelper(environment="staging")
    
    @pytest.mark.asyncio
    async def test_multi_agent_orchestration_authenticated_e2e(self, real_services_fixture):
        """Test complete multi-agent orchestration with authentication."""
        # Create authenticated user
        user_credentials = {
            "email": f"orchestration-{uuid.uuid4()}@netra.test",
            "password": "OrchestrationTest123!",
            "name": "Orchestration Test User"
        }
        
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        thread_id = f"orchestration-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            await websocket_client.connect_with_auth()
            
            # Execute complex orchestrated workflow
            orchestration_request = {
                "workflow_name": "cost_optimization_orchestration",
                "workflow_steps": [
                    {
                        "agent": "data_collection_agent",
                        "task": "collect_billing_data", 
                        "parameters": {"sources": ["aws", "azure", "gcp"]}
                    },
                    {
                        "agent": "analysis_agent",
                        "task": "analyze_usage_patterns",
                        "depends_on": ["data_collection_agent"],
                        "parameters": {"analysis_depth": "comprehensive"}
                    },
                    {
                        "agent": "optimization_agent", 
                        "task": "generate_optimization_plan",
                        "depends_on": ["analysis_agent"],
                        "parameters": {"optimization_goals": ["cost", "performance"]}
                    },
                    {
                        "agent": "report_agent",
                        "task": "generate_executive_summary",
                        "depends_on": ["optimization_agent"],
                        "parameters": {"format": "executive_dashboard"}
                    }
                ],
                "thread_id": thread_id,
                "user_context": {"user_id": user_id}
            }
            
            response = await self._send_authenticated_orchestration_request(
                auth_token=access_token,
                orchestration_request=orchestration_request,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert response["success"] == True
            workflow_id = response["workflow_id"]
            
            # Monitor orchestration events
            orchestration_events = []
            agents_completed = set()
            timeout = asyncio.get_event_loop().time() + 45.0  # Longer timeout for orchestration
            
            while asyncio.get_event_loop().time() < timeout:
                try:
                    events = await websocket_client.get_received_events(timeout=2.0)
                    orchestration_events.extend(events)
                    
                    # Track completed agents
                    for event in events:
                        if event.get("type") == "agent_completed":
                            agent_name = event.get("payload", {}).get("agent_name")
                            if agent_name:
                                agents_completed.add(agent_name)
                        
                        # Check for workflow completion
                        if event.get("type") == "workflow_completed":
                            break
                    
                    # If we've seen completion of workflow or enough agents, break
                    if len(agents_completed) >= 3 or any(e.get("type") == "workflow_completed" for e in events):
                        break
                
                except asyncio.TimeoutError:
                    continue
            
            # Verify orchestration execution
            assert len(orchestration_events) >= 8  # Should have many orchestration events
            
            # Verify agent sequence events
            agent_started_events = [e for e in orchestration_events if e.get("type") == "agent_started"]
            agent_completed_events = [e for e in orchestration_events if e.get("type") == "agent_completed"]
            
            assert len(agent_started_events) >= 3  # Multiple agents should start
            assert len(agent_completed_events) >= 2  # Multiple agents should complete
            
            # Verify orchestration metadata
            orchestration_specific_events = [e for e in orchestration_events if "orchestration" in str(e).lower()]
            assert len(orchestration_specific_events) >= 1  # Should have orchestration events
            
            # Get final workflow result
            workflow_result = await self._get_workflow_result(
                auth_token=access_token,
                workflow_id=workflow_id,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert workflow_result["success"] == True
            assert "workflow_results" in workflow_result["result"]
            
        finally:
            await websocket_client.disconnect()
            await self.auth_helper.cleanup_user_session(auth_result)
    
    @pytest.mark.asyncio
    async def test_orchestration_error_recovery_authenticated_e2e(self, real_services_fixture):
        """Test orchestration error recovery with authentication."""
        user_credentials = {
            "email": f"error-recovery-{uuid.uuid4()}@netra.test",
            "password": "ErrorRecoveryTest123!",
            "name": "Error Recovery Test User"
        }
        
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        thread_id = f"error-recovery-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            await websocket_client.connect_with_auth()
            
            # Execute workflow with intentional failure in middle
            error_prone_workflow = {
                "workflow_name": "error_recovery_test",
                "workflow_steps": [
                    {
                        "agent": "reliable_agent",
                        "task": "initial_task",
                        "parameters": {"should_succeed": True}
                    },
                    {
                        "agent": "failing_agent",  # This agent will fail
                        "task": "failing_task",
                        "depends_on": ["reliable_agent"],
                        "parameters": {"should_fail": True}
                    },
                    {
                        "agent": "recovery_agent",
                        "task": "recovery_task",
                        "depends_on": ["failing_agent"],
                        "parameters": {"handle_failure": True}
                    }
                ],
                "error_handling": {
                    "retry_failed_steps": True,
                    "continue_on_failure": True,
                    "max_retries": 2
                },
                "thread_id": thread_id,
                "user_context": {"user_id": user_id}
            }
            
            response = await self._send_authenticated_orchestration_request(
                auth_token=access_token,
                orchestration_request=error_prone_workflow,
                backend_url=real_services_fixture["backend_url"]
            )
            
            # Should start successfully even though it will have errors
            assert response["success"] == True
            workflow_id = response["workflow_id"]
            
            # Monitor error recovery events
            error_events = []
            recovery_events = []
            timeout = asyncio.get_event_loop().time() + 30.0
            
            while asyncio.get_event_loop().time() < timeout:
                try:
                    events = await websocket_client.get_received_events(timeout=2.0)
                    
                    for event in events:
                        if event.get("type") == "agent_error":
                            error_events.append(event)
                        elif "recovery" in str(event).lower() or event.get("type") == "workflow_recovery":
                            recovery_events.append(event)
                        elif event.get("type") == "workflow_completed":
                            break  # Workflow completed despite errors
                
                except asyncio.TimeoutError:
                    continue
            
            # Verify error handling and recovery
            assert len(error_events) >= 1  # Should have detected errors
            
            # Verify final result shows error recovery
            final_result = await self._get_workflow_result(
                auth_token=access_token,
                workflow_id=workflow_id,
                backend_url=real_services_fixture["backend_url"]
            )
            
            # Result may be success (recovered) or failure (handled gracefully)
            assert "error_recovery_attempted" in str(final_result).lower() or final_result["success"] == True
        
        finally:
            await websocket_client.disconnect()
            await self.auth_helper.cleanup_user_session(auth_result)
    
    async def _send_authenticated_orchestration_request(self, auth_token: str, orchestration_request: dict, backend_url: str) -> dict:
        """Send authenticated orchestration request."""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{backend_url}/api/v1/orchestration/execute",
                json=orchestration_request,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=15)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    result["success"] = True
                    return result
                else:
                    return {
                        "success": False,
                        "error": await response.text(),
                        "status_code": response.status
                    }
    
    async def _get_workflow_result(self, auth_token: str, workflow_id: str, backend_url: str) -> dict:
        """Get workflow execution result."""
        import aiohttp
        
        headers = {"Authorization": f"Bearer {auth_token}"}
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{backend_url}/api/v1/orchestration/workflow/{workflow_id}/result",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                
                if response.status == 200:
                    result = await response.json()
                    result["success"] = True
                    return result
                else:
                    return {"success": False, "error": await response.text()}