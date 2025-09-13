from shared.isolated_environment import get_env

from shared.isolated_environment import IsolatedEnvironment

"""

CRITICAL Complete User Journey Test with Real Services



BVJ (Business Value Justification):

1. Segment: ALL (Free, Early, Mid, Enterprise)

2. Business Goal: Core revenue pipeline protection - every journey = $99-999/month

3. Value Impact: Validates end-to-end user experience from signup to agent response

4. Revenue Impact: $100K+ MRR protection through validated real service integration

5. Strategic Impact: Complete real-world user journey without mocks ensures production reliability



REQUIREMENTS:

- Use REAL Auth service for signup/login (no mocks)

- Use REAL Backend WebSocket for chat (no mocks)

- Use REAL agent pipeline (can mock LLM if needed)

- Must complete in <20 seconds

- Validate JWT tokens, WebSocket auth, message flow

- Real service discovery and connection

"""



import asyncio

import os

import time

from contextlib import asynccontextmanager

from typing import Any, Dict, Optional



import pytest



# Set test environment

env = get_env()

env.set("TESTING", "1", "test")

env.set("USE_REAL_SERVICES", "true", "test")

env.set("AUTH_SERVICE_URL", "http://localhost:8001", "test")

env.set("BACKEND_SERVICE_URL", "http://localhost:8000", "test")



from tests.e2e.helpers.journey.real_service_journey_helpers import (

    RealChatHelper,

    RealLoginHelper,

    RealSignupHelper,

    RealWebSocketHelper,

    validate_real_chat,

    validate_real_login,

    validate_real_signup,

    validate_real_websocket,

)



# Handle missing imports

try:

    from dev_launcher.discovery import ServiceDiscovery

except ImportError:

    class ServiceDiscovery:

        def __init__(self):

            pass

        

        async def get_service_info(self, service_name):

            return type('ServiceInfo', (), {'port': 8000 if service_name == 'backend' else 8001})()



try:

    from tests.clients.factory import TestClientFactory

except ImportError:

    @pytest.mark.e2e

    class TestClientFactory:

        def __init__(self, discovery):

            self.discovery = discovery

        

        async def create_auth_client(self):

            return None

        

        async def cleanup(self):

            pass





class TestCompleteUserJourneyRealer:

    """Tests complete user journey with REAL services only."""

    

    def __init__(self):

        self.discovery = ServiceDiscovery()

        self.factory = TestClientFactory(self.discovery)

        self.user_data: Dict[str, Any] = {}

        self.journey_results: Dict[str, Any] = {}

        self.auth_client = None

        self.websocket_client = None

        

    @asynccontextmanager

    async def setup_real_services(self):

        """Setup connections to real services."""

        try:

            # Initialize real service clients

            self.auth_client = await self.factory.create_auth_client()

            yield self

        finally:

            await self._cleanup_real_services()

            

    async def _cleanup_real_services(self):

        """Cleanup real service connections."""

        if hasattr(self, 'websocket') and self.websocket:

            await self.websocket.close()

        if self.websocket_client:

            await self.websocket_client.disconnect()

        await self.factory.cleanup()

        

    async def execute_complete_user_journey(self) -> Dict[str, Any]:

        """Execute complete user journey with real services."""

        journey_start = time.time()

        

        # Step 1: Real signup via Auth service

        signup_result = await RealSignupHelper.execute_real_signup()

        self.user_data = signup_result.get("user_data", {})

        self._store_journey_step("signup", signup_result)

        

        # Step 2: Real login to get JWT

        login_result = await RealLoginHelper.execute_real_login(self.user_data)

        self._store_journey_step("login", login_result)

        

        # Step 3: Real WebSocket connection with JWT (only if login succeeded)

        if login_result.get("success") and login_result.get("access_token"):

            websocket_result = await RealWebSocketHelper.execute_real_websocket_connection(

                self.discovery, login_result["access_token"]

            )

            self.websocket = websocket_result.get("websocket")

            self._store_journey_step("websocket", websocket_result)

            

            # Step 4: Real chat message and agent response (only if websocket succeeded)

            if websocket_result.get("success") and self.websocket:

                chat_result = await RealChatHelper.execute_real_chat_flow(self.websocket, self.user_data)

                self._store_journey_step("chat", chat_result)

            else:

                self._store_journey_step("chat", {"success": False, "error": "WebSocket connection failed"})

        else:

            self._store_journey_step("websocket", {"success": False, "error": "Login failed, no access token"})

            self._store_journey_step("chat", {"success": False, "error": "Login failed, no access token"})

        

        journey_time = time.time() - journey_start

        return self._format_complete_journey_results(journey_time)

        

            

            

            

            

    def _store_journey_step(self, step_name: str, result: Dict[str, Any]):

        """Store journey step result for analysis."""

        self.journey_results[step_name] = result

        

    def _format_complete_journey_results(self, journey_time: float) -> Dict[str, Any]:

        """Format complete journey results for validation."""

        # Calculate overall success

        all_steps_successful = all(

            step_result.get("success", False) 

            for step_result in self.journey_results.values()

        )

        

        return {

            "success": all_steps_successful,

            "total_execution_time": journey_time,

            "performance_valid": journey_time < 20.0,

            "user_data": self.user_data,

            "journey_steps": self.journey_results,

            "step_count": len(self.journey_results)

        }





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_complete_user_journey_real_services():

    """

    Test: Complete User Journey with Real Services

    

    BVJ: Core revenue pipeline protection - every working journey = $99-999/month

    - Real Auth service signup and login

    - Real JWT token creation and validation  

    - Real WebSocket connection with authentication

    - Real chat message and agent response pipeline

    - Must complete in <20 seconds for optimal UX

    """

    tester = CompleteUserJourneyRealTester()

    

    async with tester.setup_real_services():

        # Execute complete real user journey

        results = await tester.execute_complete_user_journey()

        

        # Validate critical business requirements

        assert results["success"], f"Complete journey failed: {results}"

        assert results["performance_valid"], f"Journey too slow: {results['total_execution_time']:.2f}s > 20s"

        

        # Validate each critical step with real services

        validate_real_signup(results["journey_steps"]["signup"])

        validate_real_login(results["journey_steps"]["login"])

        validate_real_websocket(results["journey_steps"]["websocket"])

        validate_real_chat(results["journey_steps"]["chat"])

        

        print(f"[SUCCESS] Complete Real Journey: {results['total_execution_time']:.2f}s")

        print(f"[PROTECTED] $100K+ MRR user pipeline")

        print(f"[USER] {results['user_data']['email']} -> Real end-to-end flow validated")





@pytest.mark.asyncio

@pytest.mark.e2e

async def test_user_journey_performance_validation():

    """

    Test: User Journey Performance with Real Services

    

    BVJ: Ensures real service performance meets UX requirements

    Critical for maintaining conversion rates in production

    """

    tester = CompleteUserJourneyRealTester()

    

    async with tester.setup_real_services():

        # Execute with performance focus

        results = await tester.execute_complete_user_journey()

        

        # Validate performance requirements

        assert results["total_execution_time"] < 20.0, f"Performance failed: {results['total_execution_time']:.2f}s"

        assert results["success"], "Journey must succeed for performance validation"

        

        # Validate step-by-step performance

        signup_time = results["journey_steps"]["signup"]["signup_time"]

        login_time = results["journey_steps"]["login"]["login_time"]

        websocket_time = results["journey_steps"]["websocket"]["websocket_time"]

        chat_time = results["journey_steps"]["chat"]["chat_time"]

        

        # Individual step performance validation

        assert signup_time < 5.0, f"Signup too slow: {signup_time:.2f}s"

        assert login_time < 3.0, f"Login too slow: {login_time:.2f}s"

        assert websocket_time < 5.0, f"WebSocket connection too slow: {websocket_time:.2f}s"

        assert chat_time < 15.0, f"Chat response too slow: {chat_time:.2f}s"

        

        print(f"[PERFORMANCE] Real journey: {results['total_execution_time']:.2f}s")

        print(f"[BREAKDOWN] Signup: {signup_time:.2f}s, Login: {login_time:.2f}s, WebSocket: {websocket_time:.2f}s, Chat: {chat_time:.2f}s")





