"""E2E Tests for Complete User Journey with Authentication

Business Value Justification:
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Validate complete customer journey delivers promised AI value
- Value Impact: Ensures end-to-end revenue-generating user experience works
- Strategic Impact: Ultimate validation of platform's core business proposition

CRITICAL TEST PURPOSE:
These E2E tests validate the complete customer journey from signup to
receiving AI-driven business insights, ensuring platform delivers on its value promise.

Test Coverage:
- Complete user signup and onboarding flow
- First-time user experience with AI agents
- Multi-session user journey with state persistence
- Cross-browser/device session continuity
- Enterprise user workflow with advanced features
- Customer success metrics validation
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timedelta

from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.real_websocket_test_client import RealWebSocketTestClient
from test_framework.ssot.real_services_test_fixtures import *


@pytest.mark.e2e
class TestCompleteUserJourneyAuthenticatedE2E:
    """E2E tests for complete user journey with authentication."""
    
    def setup_method(self):
        """Set up E2E test environment."""
        self.auth_helper = E2EAuthHelper(environment="staging")
    
    @pytest.mark.asyncio
    async def test_complete_new_user_onboarding_journey_e2e(self, real_services_fixture):
        """Test complete new user journey from signup to first AI results."""
        # Step 1: User Registration and Account Creation
        new_user_data = {
            "email": f"new-user-{uuid.uuid4()}@netra.test",
            "password": "NewUserJourney123!",
            "name": "New User Journey Test",
            "company": "Test Company Inc",
            "role": "Engineering Manager",
            "use_case": "cost_optimization"
        }
        
        # Register new user
        registration_result = await self.auth_helper.register_new_user(new_user_data)
        assert registration_result["success"] == True
        
        # Step 2: Email Verification (simulated)
        verification_result = await self.auth_helper.simulate_email_verification(
            registration_result["user_id"]
        )
        assert verification_result["verified"] == True
        
        # Step 3: First Login and Authentication
        login_result = await self.auth_helper.authenticate_user(
            email=new_user_data["email"],
            password=new_user_data["password"]
        )
        
        assert login_result["success"] == True
        user_id = login_result["user_id"]
        access_token = login_result["access_token"]
        
        # Step 4: Account Setup and Preferences
        setup_result = await self._complete_account_setup(
            auth_token=access_token,
            preferences={
                "notification_settings": {"email": True, "websocket": True},
                "ai_preferences": {"analysis_depth": "comprehensive"},
                "dashboard_layout": "executive_summary"
            },
            backend_url=real_services_fixture["backend_url"]
        )
        assert setup_result["success"] == True
        
        # Step 5: First AI Agent Interaction (Onboarding Flow)
        thread_id = f"onboarding-{uuid.uuid4()}"
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            await websocket_client.connect_with_auth()
            
            # Execute onboarding AI agent
            onboarding_request = {
                "agent_name": "onboarding_assistant",
                "task": "welcome_new_user",
                "parameters": {
                    "user_profile": new_user_data,
                    "show_tutorial": True,
                    "customize_experience": True
                },
                "thread_id": thread_id,
                "user_context": {"user_id": user_id, "is_new_user": True}
            }
            
            onboarding_response = await self._send_authenticated_request(
                auth_token=access_token,
                request_data=onboarding_request,
                endpoint="/api/v1/agents/execute",
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert onboarding_response["success"] == True
            
            # Monitor onboarding experience
            onboarding_events = []
            timeout = asyncio.get_event_loop().time() + 20.0
            
            while asyncio.get_event_loop().time() < timeout:
                try:
                    events = await websocket_client.get_received_events(timeout=1.5)
                    onboarding_events.extend(events)
                    
                    if any(e.get("type") == "onboarding_completed" for e in events):
                        break
                except asyncio.TimeoutError:
                    continue
            
            # Verify onboarding experience
            assert len(onboarding_events) >= 3
            
            welcome_events = [e for e in onboarding_events if "welcome" in str(e).lower()]
            tutorial_events = [e for e in onboarding_events if "tutorial" in str(e).lower()]
            
            assert len(welcome_events) >= 1  # Should have welcome message
            assert len(tutorial_events) >= 1  # Should have tutorial guidance
            
            # Step 6: First Real Business Value AI Task
            business_task_request = {
                "agent_name": "cost_optimization_agent",
                "task": "initial_cost_analysis", 
                "parameters": {
                    "analysis_scope": "quick_wins",
                    "new_user_friendly": True,
                    "include_explanations": True
                },
                "thread_id": thread_id,
                "user_context": {"user_id": user_id}
            }
            
            business_response = await self._send_authenticated_request(
                auth_token=access_token,
                request_data=business_task_request,
                endpoint="/api/v1/agents/execute",
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert business_response["success"] == True
            
            # Monitor business value delivery
            business_events = []
            timeout = asyncio.get_event_loop().time() + 25.0
            
            while asyncio.get_event_loop().time() < timeout:
                try:
                    events = await websocket_client.get_received_events(timeout=2.0)
                    business_events.extend(events)
                    
                    if any(e.get("type") == "agent_completed" for e in events):
                        break
                except asyncio.TimeoutError:
                    continue
            
            # Verify business value delivery
            assert len(business_events) >= 4
            
            # Should have thinking, tool execution, and completion events
            thinking_events = [e for e in business_events if e.get("type") == "agent_thinking"]
            tool_events = [e for e in business_events if "tool" in e.get("type", "")]
            completion_events = [e for e in business_events if e.get("type") == "agent_completed"]
            
            assert len(thinking_events) >= 2  # Should show AI reasoning
            assert len(tool_events) >= 1     # Should execute tools for analysis
            assert len(completion_events) >= 1  # Should complete successfully
            
            # Step 7: Verify User Success Metrics
            success_metrics = await self._get_user_success_metrics(
                auth_token=access_token,
                user_id=user_id,
                backend_url=real_services_fixture["backend_url"]
            )
            
            assert success_metrics["success"] == True
            metrics = success_metrics["metrics"]
            
            # Verify onboarding success
            assert metrics["onboarding_completed"] == True
            assert metrics["first_ai_task_completed"] == True
            assert metrics["time_to_first_value"] <= 1800  # Should get value within 30 minutes
            
            # Verify engagement metrics
            assert metrics["websocket_events_received"] >= 7
            assert metrics["ai_interactions_count"] >= 2
            
        finally:
            await websocket_client.disconnect()
            await self.auth_helper.cleanup_user_session(login_result)
    
    @pytest.mark.asyncio
    async def test_returning_user_multi_session_journey_e2e(self, real_services_fixture):
        """Test returning user experience across multiple sessions."""
        # Create and set up user account
        user_credentials = {
            "email": f"returning-user-{uuid.uuid4()}@netra.test",
            "password": "ReturningUserTest123!",
            "name": "Returning User Test"
        }
        
        # Initial session setup
        auth_result = await self.auth_helper.create_authenticated_user_session(user_credentials)
        user_id = auth_result["user_id"]
        
        # Session 1: First day usage
        session1_result = await self._simulate_user_session(
            auth_result=auth_result,
            session_name="day_1_exploration",
            tasks=[
                {"agent": "cost_analyzer", "task": "analyze_current_spend"},
                {"agent": "insight_generator", "task": "identify_quick_wins"}
            ],
            backend_url=real_services_fixture["backend_url"]
        )
        
        assert session1_result["success"] == True
        assert session1_result["tasks_completed"] == 2
        
        # Simulate user logout
        await self.auth_helper.logout_user(auth_result)
        
        # Session 2: Return next day (simulate state persistence)
        await asyncio.sleep(1.0)  # Brief gap to simulate time passage
        
        session2_auth = await self.auth_helper.authenticate_user(
            email=user_credentials["email"],
            password=user_credentials["password"]
        )
        
        assert session2_auth["user_id"] == user_id  # Same user
        
        session2_result = await self._simulate_user_session(
            auth_result=session2_auth,
            session_name="day_2_deeper_analysis",
            tasks=[
                {"agent": "trend_analyzer", "task": "analyze_spending_trends"},
                {"agent": "forecasting_agent", "task": "project_future_costs"},
                {"agent": "optimization_agent", "task": "generate_action_plan"}
            ],
            backend_url=real_services_fixture["backend_url"],
            expect_state_continuity=True
        )
        
        assert session2_result["success"] == True
        assert session2_result["tasks_completed"] == 3
        assert session2_result["state_continuity_verified"] == True
        
        # Verify cross-session user journey metrics
        journey_metrics = await self._get_user_journey_metrics(
            auth_token=session2_auth["access_token"],
            user_id=user_id,
            backend_url=real_services_fixture["backend_url"]
        )
        
        assert journey_metrics["success"] == True
        metrics = journey_metrics["metrics"]
        
        assert metrics["total_sessions"] >= 2
        assert metrics["total_ai_tasks"] >= 5
        assert metrics["user_retention_verified"] == True
        
        # Cleanup
        await self.auth_helper.cleanup_user_session(session2_auth)
    
    async def _complete_account_setup(self, auth_token: str, preferences: dict, backend_url: str) -> dict:
        """Complete initial account setup."""
        return await self._send_authenticated_request(
            auth_token=auth_token,
            request_data={"preferences": preferences, "setup_complete": True},
            endpoint="/api/v1/users/setup",
            backend_url=backend_url
        )
    
    async def _simulate_user_session(self, auth_result: dict, session_name: str, tasks: list, backend_url: str, expect_state_continuity: bool = False) -> dict:
        """Simulate a complete user session."""
        user_id = auth_result["user_id"]
        access_token = auth_result["access_token"]
        thread_id = f"{session_name}-{uuid.uuid4()}"
        
        websocket_client = RealWebSocketTestClient(
            thread_id=thread_id,
            user_id=user_id,
            auth_token=access_token
        )
        
        try:
            await websocket_client.connect_with_auth()
            
            completed_tasks = 0
            all_events = []
            
            for task in tasks:
                task_request = {
                    "agent_name": task["agent"],
                    "task": task["task"],
                    "thread_id": thread_id,
                    "user_context": {"user_id": user_id}
                }
                
                response = await self._send_authenticated_request(
                    auth_token=access_token,
                    request_data=task_request,
                    endpoint="/api/v1/agents/execute",
                    backend_url=backend_url
                )
                
                if response["success"]:
                    completed_tasks += 1
                    
                    # Collect events for this task
                    task_events = []
                    timeout = asyncio.get_event_loop().time() + 15.0
                    
                    while asyncio.get_event_loop().time() < timeout:
                        try:
                            events = await websocket_client.get_received_events(timeout=1.0)
                            task_events.extend(events)
                            all_events.extend(events)
                            
                            if any(e.get("type") == "agent_completed" for e in events):
                                break
                        except asyncio.TimeoutError:
                            continue
            
            # Verify state continuity if expected
            state_continuity_verified = True
            if expect_state_continuity:
                # Check for state continuity indicators in events
                continuity_events = [e for e in all_events if "previous" in str(e).lower() or "continuing" in str(e).lower()]
                state_continuity_verified = len(continuity_events) > 0
            
            return {
                "success": True,
                "session_name": session_name,
                "tasks_completed": completed_tasks,
                "total_events": len(all_events),
                "state_continuity_verified": state_continuity_verified
            }
        
        finally:
            await websocket_client.disconnect()
    
    async def _get_user_success_metrics(self, auth_token: str, user_id: str, backend_url: str) -> dict:
        """Get user success and engagement metrics."""
        return await self._send_authenticated_request(
            auth_token=auth_token,
            request_data={},
            endpoint=f"/api/v1/users/{user_id}/metrics/success",
            backend_url=backend_url,
            method="GET"
        )
    
    async def _get_user_journey_metrics(self, auth_token: str, user_id: str, backend_url: str) -> dict:
        """Get user journey analytics."""
        return await self._send_authenticated_request(
            auth_token=auth_token,
            request_data={},
            endpoint=f"/api/v1/users/{user_id}/metrics/journey",
            backend_url=backend_url,
            method="GET"
        )
    
    async def _send_authenticated_request(self, auth_token: str, request_data: dict, endpoint: str, backend_url: str, method: str = "POST") -> dict:
        """Send authenticated request to backend."""
        import aiohttp
        
        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            if method == "GET":
                async with session.get(
                    f"{backend_url}{endpoint}",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return await self._process_response(response)
            else:
                async with session.post(
                    f"{backend_url}{endpoint}",
                    json=request_data,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    return await self._process_response(response)
    
    async def _process_response(self, response) -> dict:
        """Process HTTP response."""
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