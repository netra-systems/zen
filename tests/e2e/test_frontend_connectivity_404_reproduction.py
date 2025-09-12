"""
E2E Test: Frontend Connectivity 404 Reproduction

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Identify and reproduce 404 errors affecting user experience
- Value Impact: Ensures users can successfully interact with AI agents through frontend
- Strategic Impact: Critical for preventing revenue loss due to broken user journeys

CRITICAL: This E2E test MUST use real authentication (NO MOCKS).
This test is DESIGNED TO FAIL initially to reproduce actual 404 errors in staging environment.

This test reproduces the exact frontend-backend connectivity issues that users experience,
providing concrete evidence of failures before implementing fixes.
"""

import asyncio
import json
import pytest
import websockets
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from test_framework.base_e2e_test import BaseE2ETest
from test_framework.ssot.e2e_auth_helper import (
    E2EAuthHelper, 
    E2EWebSocketAuthHelper,
    create_authenticated_user_context
)
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import get_env

import aiohttp


class TestFrontendConnectivity404Reproduction(BaseE2ETest):
    """
    E2E test to reproduce 404 errors affecting frontend connectivity.
    
    CRITICAL: This test uses REAL authentication and REAL services to reproduce
    actual user-facing 404 errors. NO MOCKS allowed.
    """
    
    def setUp(self):
        """Set up E2E test environment with real authentication."""
        super().setUp()
        self.env = get_env()
        
        # Determine test environment - default to test, but detect staging
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        # Initialize auth helpers for real authentication
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        
        # Use appropriate URLs based on environment
        if self.test_environment == "staging":
            self.backend_url = "https://netra-backend-staging-1046653154097.us-central1.run.app"
            self.websocket_url = "wss://netra-backend-staging-1046653154097.us-central1.run.app/ws"
        else:
            self.backend_url = "http://localhost:8000"
            self.websocket_url = "ws://localhost:8000/ws"
        
        # Critical 404 endpoints that frontend expects but may be missing
        self.critical_frontend_endpoints = [
            {
                "endpoint": "/api/agent/v2/execute",
                "method": "POST",
                "description": "Agent execution v2 API",
                "payload": {
                    "type": "triage",
                    "message": "Test agent execution from frontend",
                    "context": {"source": "e2e_test"}
                }
            },
            {
                "endpoint": "/api/agents/v2/execute", 
                "method": "POST",
                "description": "Alternative agent execution v2 API",
                "payload": {
                    "type": "data",
                    "message": "Test data agent from frontend",
                    "context": {"source": "e2e_test"}
                }
            },
            {
                "endpoint": "/api/threads/{thread_id}/messages",
                "method": "GET", 
                "description": "Thread messages retrieval",
                "payload": None
            },
            {
                "endpoint": "/api/threads/{thread_id}/messages",
                "method": "POST",
                "description": "Thread message creation",
                "payload": {
                    "content": "Test message from frontend",
                    "role": "user"
                }
            }
        ]
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_agent_v2_execute_404_reproduction(self, real_services):
        """
        Reproduce 404 error on /api/agent/v2/execute endpoint.
        
        CRITICAL: Uses REAL authentication to reproduce actual user experience.
        EXPECTED RESULT: This test should FAIL with 404, demonstrating the issue.
        """
        # Create real authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="e2e_404_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Get real JWT token from context
        jwt_token = user_context.agent_context["jwt_token"]
        headers = self.auth_helper.get_auth_headers(jwt_token)
        
        endpoint_url = f"{self.backend_url}/api/agent/v2/execute"
        test_payload = {
            "type": "triage",
            "message": "E2E test: Reproduce 404 error on agent execution",
            "context": {
                "source": "frontend_connectivity_test",
                "user_id": str(user_context.user_id),
                "thread_id": str(user_context.thread_id),
                "test_environment": self.test_environment
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                print(f" SEARCH:  Testing {endpoint_url} with real authentication...")
                print(f"[U+1F511] Using JWT token: {jwt_token[:50]}...")
                print(f"[U+1F4DD] Payload: {json.dumps(test_payload, indent=2)}")
                
                async with session.post(
                    endpoint_url,
                    json=test_payload,
                    headers=headers,
                    timeout=30  # Longer timeout for staging
                ) as response:
                    
                    response_text = await response.text()
                    print(f" CHART:  Response status: {response.status}")
                    print(f"[U+1F4C4] Response: {response_text[:500]}...")
                    
                    # CRITICAL: This assertion should FAIL initially with 404
                    self.assertNotEqual(
                        response.status,
                        404,
                        f"CRITICAL 404 ERROR REPRODUCED: {endpoint_url} returned 404. "
                        f"This is the exact error users experience when frontend tries to execute agents. "
                        f"Environment: {self.test_environment}. "
                        f"Response: {response_text}"
                    )
                    
                    # If not 404, check for other errors
                    if response.status not in [200, 201]:
                        self.fail(
                            f"AGENT EXECUTION ENDPOINT ERROR: {endpoint_url} returned {response.status}. "
                            f"Users cannot execute agents. Response: {response_text}"
                        )
                    
                    # Validate successful response structure
                    try:
                        response_data = await response.json()
                        required_fields = ["id", "status"]
                        missing_fields = [f for f in required_fields if f not in response_data]
                        if missing_fields:
                            self.fail(
                                f"RESPONSE FORMAT ERROR: Missing fields {missing_fields}. "
                                f"Frontend expects: {required_fields}"
                            )
                    except json.JSONDecodeError:
                        self.fail(f"INVALID JSON RESPONSE: {response_text}")
                        
            except aiohttp.ClientError as e:
                self.fail(
                    f"CONNECTION ERROR to {endpoint_url}: {e}. "
                    f"Users cannot connect to backend from frontend. "
                    f"Environment: {self.test_environment}"
                )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_thread_messages_404_reproduction(self, real_services):
        """
        Reproduce 404 error on /api/threads/{thread_id}/messages endpoint.
        
        CRITICAL: Uses REAL authentication to reproduce actual user experience.
        EXPECTED RESULT: This test should FAIL with 404, demonstrating the issue.
        """
        # Create real authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="e2e_messages_404_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        jwt_token = user_context.agent_context["jwt_token"]
        headers = self.auth_helper.get_auth_headers(jwt_token)
        test_thread_id = str(user_context.thread_id)
        
        # Test GET /api/threads/{thread_id}/messages
        get_endpoint_url = f"{self.backend_url}/api/threads/{test_thread_id}/messages"
        
        async with aiohttp.ClientSession() as session:
            try:
                print(f" SEARCH:  Testing GET {get_endpoint_url} with real authentication...")
                print(f"[U+1F9F5] Thread ID: {test_thread_id}")
                
                async with session.get(
                    get_endpoint_url,
                    headers=headers,
                    timeout=30
                ) as response:
                    
                    response_text = await response.text()
                    print(f" CHART:  GET Response status: {response.status}")
                    print(f"[U+1F4C4] GET Response: {response_text[:500]}...")
                    
                    # CRITICAL: This assertion should FAIL initially with 404
                    self.assertNotEqual(
                        response.status,
                        404,
                        f"CRITICAL 404 ERROR REPRODUCED: GET {get_endpoint_url} returned 404. "
                        f"This is the exact error users experience when frontend tries to retrieve messages. "
                        f"Environment: {self.test_environment}. "
                        f"Thread ID: {test_thread_id}. "
                        f"Response: {response_text}"
                    )
                    
                    if response.status not in [200]:
                        self.fail(
                            f"THREAD MESSAGES GET ERROR: {get_endpoint_url} returned {response.status}. "
                            f"Users cannot retrieve conversation history. Response: {response_text}"
                        )
                        
            except aiohttp.ClientError as e:
                self.fail(
                    f"CONNECTION ERROR to {get_endpoint_url}: {e}. "
                    f"Users cannot retrieve messages from frontend."
                )
        
        # Test POST /api/threads/{thread_id}/messages
        post_endpoint_url = f"{self.backend_url}/api/threads/{test_thread_id}/messages"
        test_message_payload = {
            "content": "E2E test: Reproduce 404 error on message creation",
            "role": "user",
            "metadata": {
                "source": "frontend_connectivity_test",
                "test_environment": self.test_environment
            }
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                print(f" SEARCH:  Testing POST {post_endpoint_url} with real authentication...")
                print(f"[U+1F4DD] Message payload: {json.dumps(test_message_payload, indent=2)}")
                
                async with session.post(
                    post_endpoint_url,
                    json=test_message_payload,
                    headers=headers,
                    timeout=30
                ) as response:
                    
                    response_text = await response.text()
                    print(f" CHART:  POST Response status: {response.status}")
                    print(f"[U+1F4C4] POST Response: {response_text[:500]}...")
                    
                    # CRITICAL: This assertion should FAIL initially with 404
                    self.assertNotEqual(
                        response.status,
                        404,
                        f"CRITICAL 404 ERROR REPRODUCED: POST {post_endpoint_url} returned 404. "
                        f"This is the exact error users experience when frontend tries to send messages. "
                        f"Environment: {self.test_environment}. "
                        f"Thread ID: {test_thread_id}. "
                        f"Response: {response_text}"
                    )
                    
                    if response.status not in [200, 201]:
                        self.fail(
                            f"THREAD MESSAGE POST ERROR: {post_endpoint_url} returned {response.status}. "
                            f"Users cannot send messages. Response: {response_text}"
                        )
                        
            except aiohttp.ClientError as e:
                self.fail(
                    f"CONNECTION ERROR to {post_endpoint_url}: {e}. "
                    f"Users cannot send messages from frontend."
                )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_websocket_connectivity_with_real_auth(self, real_services):
        """
        Test WebSocket connectivity with real authentication to reproduce connection issues.
        
        CRITICAL: Uses REAL authentication and staging-compatible WebSocket connection.
        This test validates the complete WebSocket flow that users experience.
        """
        # Create real authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="e2e_websocket_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        try:
            print(f"[U+1F50C] Testing WebSocket connection with real authentication...")
            print(f"[U+1F310] Environment: {self.test_environment}")
            print(f"[U+1F517] WebSocket URL: {self.websocket_url}")
            print(f"[U+1F464] User ID: {user_context.user_id}")
            
            # Use the E2E WebSocket auth helper for proper connection
            websocket = await self.websocket_auth_helper.connect_authenticated_websocket(timeout=30.0)
            
            # Test WebSocket message sending (agent execution via WebSocket)
            test_message = {
                "type": "agent_request",
                "agent": "triage",
                "message": "E2E test: Reproduce WebSocket agent execution",
                "context": {
                    "user_id": str(user_context.user_id),
                    "thread_id": str(user_context.thread_id),
                    "test_environment": self.test_environment,
                    "source": "frontend_websocket_test"
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            print(f"[U+1F4E4] Sending WebSocket message: {json.dumps(test_message, indent=2)}")
            await websocket.send(json.dumps(test_message))
            
            # Wait for agent execution events (should receive all 5 critical events)
            events_received = []
            critical_events = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
            
            try:
                # Collect events with timeout
                timeout_duration = 60.0 if self.test_environment == "staging" else 30.0
                
                while len(events_received) < 10:  # Collect up to 10 events
                    try:
                        event_json = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=timeout_duration
                        )
                        
                        event = json.loads(event_json)
                        events_received.append(event)
                        print(f"[U+1F4E8] Received WebSocket event: {event.get('type', 'unknown')}")
                        
                        # Break if we get completion event
                        if event.get("type") == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"[U+23F0] WebSocket timeout after {timeout_duration}s")
                        break
                        
            except Exception as e:
                self.fail(
                    f"WEBSOCKET EVENT ERROR: Failed to receive agent events: {e}. "
                    f"Users cannot see agent progress. Events received: {len(events_received)}"
                )
            
            finally:
                await websocket.close()
            
            # Validate critical WebSocket events were received
            event_types = [event.get("type") for event in events_received]
            missing_critical_events = [event for event in critical_events if event not in event_types]
            
            if missing_critical_events:
                self.fail(
                    f"CRITICAL WEBSOCKET EVENTS MISSING: {missing_critical_events}. "
                    f"Users cannot see agent progress. "
                    f"Received events: {event_types}. "
                    f"Environment: {self.test_environment}"
                )
            
            print(f" PASS:  WebSocket connectivity successful. Events received: {event_types}")
            
        except Exception as e:
            self.fail(
                f"WEBSOCKET CONNECTION FAILURE: {e}. "
                f"Users cannot connect to backend via WebSocket. "
                f"Environment: {self.test_environment}. "
                f"URL: {self.websocket_url}"
            )
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.mission_critical
    async def test_comprehensive_404_reproduction(self, real_services):
        """
        Comprehensive test to reproduce all 404 errors affecting frontend connectivity.
        
        CRITICAL: This test reproduces ALL user-facing connectivity issues.
        EXPECTED RESULT: Multiple failures demonstrating the scope of the 404 problem.
        """
        # Create real authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="e2e_comprehensive_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        jwt_token = user_context.agent_context["jwt_token"]
        headers = self.auth_helper.get_auth_headers(jwt_token)
        test_thread_id = str(user_context.thread_id)
        
        failed_endpoints = []
        successful_endpoints = []
        
        print(f" SEARCH:  Comprehensive 404 reproduction test starting...")
        print(f"[U+1F310] Environment: {self.test_environment}")
        print(f"[U+1F511] Using real authentication with JWT")
        print(f"[U+1F464] User ID: {user_context.user_id}")
        print(f"[U+1F9F5] Thread ID: {test_thread_id}")
        
        async with aiohttp.ClientSession() as session:
            for endpoint_config in self.critical_frontend_endpoints:
                endpoint = endpoint_config["endpoint"]
                method = endpoint_config["method"]
                description = endpoint_config["description"]
                payload = endpoint_config["payload"]
                
                # Replace placeholders
                test_endpoint = endpoint.replace("{thread_id}", test_thread_id)
                endpoint_url = f"{self.backend_url}{test_endpoint}"
                
                try:
                    print(f"\n SEARCH:  Testing {method} {test_endpoint} ({description})")
                    
                    if method == "GET":
                        async with session.get(endpoint_url, headers=headers, timeout=30) as response:
                            result = await self._process_endpoint_response(
                                endpoint_url, method, description, response
                            )
                    elif method == "POST":
                        async with session.post(endpoint_url, json=payload, headers=headers, timeout=30) as response:
                            result = await self._process_endpoint_response(
                                endpoint_url, method, description, response
                            )
                    
                    if result["success"]:
                        successful_endpoints.append(f"{method} {test_endpoint} ({description})")
                    else:
                        failed_endpoints.append(f"{method} {test_endpoint}: {result['error']}")
                        
                except Exception as e:
                    failed_endpoints.append(f"{method} {test_endpoint}: Connection error - {e}")
        
        # CRITICAL: This should FAIL initially, showing all 404 errors
        if failed_endpoints:
            failure_message = (
                f"COMPREHENSIVE 404 REPRODUCTION - FRONTEND CONNECTIVITY FAILURES:\n"
                f"Environment: {self.test_environment}\n"
                f"Failed endpoints ({len(failed_endpoints)}):\n"
                + "\n".join(f"   FAIL:  {failure}" for failure in failed_endpoints)
            )
            
            if successful_endpoints:
                failure_message += (
                    f"\n\nWorking endpoints ({len(successful_endpoints)}):\n"
                    + "\n".join(f"   PASS:  {success}" for success in successful_endpoints)
                )
            
            failure_message += (
                f"\n\nThis demonstrates the complete scope of 404 errors affecting user experience. "
                f"Users cannot access critical frontend functionality due to missing backend endpoints."
            )
            
            self.fail(failure_message)
    
    async def _process_endpoint_response(self, url: str, method: str, description: str, response) -> Dict[str, Any]:
        """Process endpoint response and return result."""
        response_text = await response.text()
        
        print(f"   CHART:  {response.status} - {response_text[:100]}...")
        
        if response.status == 404:
            return {
                "success": False,
                "error": f"404 ERROR - {description} endpoint missing"
            }
        
        if response.status not in [200, 201]:
            return {
                "success": False,
                "error": f"{response.status} ERROR - {response_text[:200]}"
            }
        
        return {"success": True, "error": None}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])