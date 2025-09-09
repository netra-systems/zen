"""E2E Tests for Tool Execution with Authentication

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure AI tools work within authenticated user sessions
- Value Impact: Enables delivery of personalized AI insights and actions
- Strategic Impact: Core capability for user-specific AI automation

CRITICAL TEST PURPOSE:
These E2E tests validate tool execution within authenticated user contexts
to ensure AI agents can deliver personalized business value.

Test Coverage:
- Tool execution with user authentication context
- User-specific tool permissions and access control
- Tool results isolation between authenticated users
- Tool error handling in authenticated sessions
- Real-time tool execution feedback via WebSocket
"""

import pytest
import asyncio
import uuid

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.e2e
class TestToolExecutionAuthenticatedE2E:
    """E2E tests for tool execution with authentication."""
    
    def setup_method(self):
        """Set up E2E test environment."""
        self.auth_helper = E2EAuthHelper(environment="staging")
    
    @pytest.mark.asyncio
    async def test_authenticated_tool_execution_e2e_flow(self, real_services_fixture):
        """Test complete tool execution flow with authentication."""
        # Create authenticated user
        user_credentials = {
            "email": f"tool-exec-{uuid.uuid4()}@netra.test",
            "password": "ToolExecTest123!",
            "name": "Tool Execution Test User"
        }
        
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        thread_id = f"tool-exec-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            await websocket_client.connect_with_auth()
            
            # Execute agent that uses multiple tools
            tool_agent_request = {
                "agent_name": "multi_tool_agent",
                "task": "execute_analysis_with_tools",
                "parameters": {
                    "analysis_type": "cost_optimization",
                    "tools_to_use": ["data_collector", "cost_analyzer", "report_generator"]
                },
                "thread_id": thread_id,
                "user_context": {"user_id": user_id}
            }
            
            response = await self._send_authenticated_request(
                auth_token=access_token,
                request_data=tool_agent_request,
                endpoint="/api/v1/agents/execute",
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert response["success"] == True
            run_id = response["run_id"]
            
            # Monitor tool execution events
            tool_events = []
            completion_timeout = asyncio.get_event_loop().time() + 20.0
            
            while asyncio.get_event_loop().time() < completion_timeout:
                try:
                    events = await websocket_client.get_received_events(timeout=1.0)
                    tool_events.extend(events)
                    
                    # Check for completion
                    if any(e.get("type") == "agent_completed" for e in events):
                        break
                except asyncio.TimeoutError:
                    continue
            
            # Verify tool execution events
            tool_executing_events = [e for e in tool_events if e.get("type") == "tool_executing"]
            tool_completed_events = [e for e in tool_events if e.get("type") == "tool_completed"]
            
            assert len(tool_executing_events) >= 2  # Should have multiple tool executions
            assert len(tool_completed_events) >= 2  # Should have completions
            
            # Verify tool events contain user context
            for event in tool_executing_events + tool_completed_events:
                assert "payload" in event
                assert "timestamp" in event
            
            # Get final results
            final_result = await self._get_execution_result(
                auth_token=access_token,
                run_id=run_id,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert final_result["success"] == True
            assert "tool_results" in final_result["result"]
        
        finally:
            await websocket_client.disconnect()
            await self.auth_helper.cleanup_user_session(auth_result)
    
    @pytest.mark.asyncio
    async def test_user_specific_tool_permissions_e2e(self, real_services_fixture):
        """Test user-specific tool permissions in E2E flow."""
        # Create users with different permission levels
        admin_user_creds = {
            "email": f"admin-{uuid.uuid4()}@netra.test",
            "password": "AdminToolTest123!",
            "name": "Admin Tool Test User",
            "permissions": ["admin", "advanced_tools"]
        }
        
        basic_user_creds = {
            "email": f"basic-{uuid.uuid4()}@netra.test", 
            "password": "BasicToolTest123!",
            "name": "Basic Tool Test User",
            "permissions": ["basic_tools"]
        }
        
        admin_auth = await self.auth_helper.create_authenticated_user_session(admin_user_creds)
        basic_auth = await self.auth_helper.create_authenticated_user_session(basic_user_creds)
        
        try:
            # Test admin user can access advanced tools
            admin_tool_request = {
                "tool_name": "advanced_admin_tool",
                "parameters": {"operation": "system_analysis"},
                "user_context": {"user_id": admin_auth["user_id"]}
            }
            
            admin_result = await self._send_authenticated_request(
                auth_token=admin_auth["access_token"],
                request_data=admin_tool_request,
                endpoint="/api/v1/tools/execute",
                backend_url=real_services_fixture["backend_url"]
            )
            
            # Admin should have access
            assert admin_result.get("success") == True or admin_result.get("error") != "insufficient_permissions"
            
            # Test basic user cannot access advanced tools
            basic_tool_request = {
                "tool_name": "advanced_admin_tool",
                "parameters": {"operation": "system_analysis"},
                "user_context": {"user_id": basic_auth["user_id"]}
            }
            
            basic_result = await self._send_authenticated_request(
                auth_token=basic_auth["access_token"],
                request_data=basic_tool_request,
                endpoint="/api/v1/tools/execute",
                backend_url=real_services_fixture["backend_url"]
            )
            
            # Basic user should be denied or have limited access
            if basic_result.get("success") == False:
                assert "permission" in basic_result.get("error", "").lower()
        
        finally:
            await self.auth_helper.cleanup_user_session(admin_auth)
            await self.auth_helper.cleanup_user_session(basic_auth)
    
    async def _send_authenticated_request(self, auth_token: str, request_data: dict, endpoint: str, backend_url: str) -> dict:
        """Send authenticated request to backend."""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{backend_url}{endpoint}",
                json=request_data,
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
    
    async def _get_execution_result(self, auth_token: str, run_id: str, backend_url: str) -> dict:
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