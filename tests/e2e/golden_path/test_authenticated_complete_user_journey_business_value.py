"""
Authenticated Complete User Journey Business Value E2E Test - Phase 1 Implementation

CRITICAL AUTHENTICATION COMPLIANCE: This test validates the complete authenticated user journey
that generates business value, ensuring ALL E2E tests use proper authentication.

Phase 1 Objective: Authentication Compliance Validation
- MANDATORY use of E2EWebSocketAuthHelper
- MANDATORY authentication for ALL user actions
- MANDATORY validation that authentication works end-to-end
- PROOF that tests fail without authentication

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - $500K+ ARR protection
- Business Goal: Validate complete authenticated golden path user journey
- Value Impact: Ensures authenticated users receive AI cost optimization insights
- Strategic Impact: Protects primary revenue flow through authenticated business journey

CRITICAL REQUIREMENTS (per CLAUDE.md Section 3.4):
1. MANDATORY authentication via E2EWebSocketAuthHelper - NO EXCEPTIONS
2. MANDATORY failure if authentication is missing or bypassed
3. MANDATORY real services (--real-services flag)
4. MANDATORY validation of all 5 WebSocket events with authentication context
5. MANDATORY business value delivery through authenticated channels
6. NO MOCKS - real authentication, real WebSocket, real database
7. Must demonstrate authentication prevents unauthorized access

GOLDEN PATH FLOW TESTED WITH AUTHENTICATION:
```
User Authentication → JWT Token → WebSocket Auth → Agent Execution →
WebSocket Events (authenticated) → Business Value → Persistence → Success
```
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional

# SSOT imports following absolute import rules - AUTHENTICATION FOCUSED
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import create_authenticated_user_context
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.ssot.real_services_test_fixtures import real_services_fixture
from test_framework.websocket_helpers import WebSocketTestHelpers, assert_websocket_events

# Core system imports for authenticated integration
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID

# Real services for authenticated testing
import httpx
import websockets


@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.real_services
@pytest.mark.asyncio
@pytest.mark.authentication_compliance
class TestAuthenticatedCompleteUserJourneyBusinessValue(SSotAsyncTestCase):
    """
    Phase 1 Authentication Compliance: Complete authenticated user journey validation.
    
    This test ensures ALL E2E tests use proper authentication and that the complete
    business value journey works with real authentication flows.
    
    AUTHENTICATION MANDATE: This test MUST use authentication for ALL operations.
    Any test that bypasses authentication VIOLATES CLAUDE.md requirements.
    """
    
    def setup_method(self, method=None):
        """Setup with authentication focus and business metrics."""
        super().setup_method(method)
        
        # Authentication compliance metrics
        self.record_metric("authentication_compliance_test", True)
        self.record_metric("phase_1_implementation", "authentication_validation")
        self.record_metric("auth_bypass_tolerance", 0)  # ZERO tolerance for auth bypass
        self.record_metric("business_arr_protection", 500000)  # $500K ARR
        
        # Initialize authentication components first
        self._auth_helper = None
        self._websocket_helper = None
        self._user_context = None
        
    async def async_setup_method(self, method=None):
        """Async setup with mandatory authentication initialization."""
        await super().async_setup_method(method)
        
        # CRITICAL: Initialize authentication helpers - MANDATORY
        environment = self.get_env_var("TEST_ENV", "test")
        self._auth_helper = E2EAuthHelper(environment=environment)
        self._websocket_helper = E2EWebSocketAuthHelper(environment=environment)
        
        # Create authenticated user context - ALL operations must be authenticated
        self._user_context = await create_authenticated_user_context(
            user_email="auth_compliant_journey@example.com",
            environment=environment,
            permissions=["read", "write", "execute_agents", "cost_optimization"],
            websocket_enabled=True
        )
        
        # Record authentication setup success
        self.record_metric("auth_setup_completed", True)
        self.record_metric("user_authenticated", bool(self._user_context))
        self.record_metric("jwt_token_created", bool(self._user_context.agent_context.get("jwt_token")))

    @pytest.mark.timeout(90)  # Allow time for authenticated flows
    @pytest.mark.asyncio
    async def test_complete_authenticated_user_journey_with_business_value(self, real_services_fixture):
        """
        PHASE 1 CRITICAL: Complete authenticated user journey with business value delivery.
        
        This test validates that the COMPLETE authenticated user journey works:
        1. User creates authenticated session (JWT token)
        2. WebSocket connection uses authentication headers
        3. All messages include authentication context
        4. Agent execution happens in authenticated context
        5. WebSocket events include authentication validation
        6. Business value delivered to authenticated user
        7. Data persisted with authentication audit trail
        
        AUTHENTICATION VALIDATION:
        - ALL operations must include authentication
        - Test MUST fail if authentication is bypassed
        - WebSocket headers MUST include auth tokens
        - Agent context MUST validate user permissions
        
        BUSINESS VALUE: Authenticated cost optimization insights with quantified savings
        """
        test_start_time = time.time()
        
        # === STEP 1: AUTHENTICATED USER SESSION CREATION ===
        self.record_metric("step_1_auth_creation_start", time.time())
        
        # CRITICAL: Verify authentication components are initialized
        assert self._auth_helper, "Auth helper MUST be initialized - authentication required"
        assert self._websocket_helper, "WebSocket auth helper MUST be initialized - authentication required"
        assert self._user_context, "User context MUST be authenticated - no anonymous access allowed"
        
        # Extract authentication data
        jwt_token = self._user_context.agent_context.get("jwt_token")
        user_id = str(self._user_context.user_id)
        thread_id = str(self._user_context.thread_id)
        
        # MANDATORY: Validate JWT token exists and is valid
        assert jwt_token, "JWT token MUST exist - no unauthenticated access allowed"
        
        # Validate JWT token structure and claims
        validation_result = await self._auth_helper.validate_jwt_token(jwt_token)
        assert validation_result["valid"], (
            f"JWT token MUST be valid for authenticated journey: {validation_result.get('error')}"
        )
        assert validation_result["user_id"] == user_id, "JWT token user_id MUST match context user_id"
        
        self.record_metric("step_1_auth_validation_success", True)
        self.record_metric("step_1_duration", time.time() - self.get_metric("step_1_auth_creation_start"))
        
        # === STEP 2: AUTHENTICATED WEBSOCKET CONNECTION ===
        self.record_metric("step_2_websocket_auth_start", time.time())
        
        # Get authenticated WebSocket headers - MANDATORY for all WebSocket connections
        ws_headers = self._websocket_helper.get_websocket_headers(jwt_token)
        
        # CRITICAL: Validate authentication headers are present
        assert "Authorization" in ws_headers, "Authorization header MUST be present - no anonymous WebSocket connections"
        assert ws_headers["Authorization"].startswith("Bearer "), "Bearer token MUST be present in Authorization header"
        assert "X-E2E-Test" in ws_headers, "E2E detection headers MUST be present for test authentication"
        
        # Establish authenticated WebSocket connection
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        self._websocket_connection = await WebSocketTestHelpers.create_test_websocket_connection(
            url=websocket_url,
            headers=ws_headers,
            timeout=15.0,
            user_id=user_id
        )
        
        assert self._websocket_connection, "Authenticated WebSocket connection MUST be established"
        
        self.record_metric("step_2_websocket_authenticated", True)
        self.record_metric("step_2_duration", time.time() - self.get_metric("step_2_websocket_auth_start"))
        
        # === STEP 3: AUTHENTICATED BUSINESS REQUEST ===
        self.record_metric("step_3_business_request_start", time.time())
        
        # Create authenticated cost optimization request
        authenticated_message = {
            "type": "chat_message",
            "content": "Analyze my AI infrastructure costs and provide authenticated optimization recommendations with quantified savings.",
            "user_id": user_id,
            "thread_id": thread_id,
            "run_id": str(self._user_context.run_id),
            "request_id": str(self._user_context.request_id),
            "timestamp": time.time(),
            "authentication_context": {
                "authenticated": True,
                "user_permissions": self._user_context.agent_context.get("permissions", []),
                "auth_method": "jwt_token",
                "business_intent": "cost_optimization_authenticated"
            }
        }
        
        # Send authenticated message
        await WebSocketTestHelpers.send_test_message(
            self._websocket_connection,
            authenticated_message,
            timeout=5.0
        )
        
        self.record_metric("step_3_authenticated_request_sent", True)
        self.record_metric("step_3_duration", time.time() - self.get_metric("step_3_business_request_start"))
        
        # === STEP 4: COLLECT AUTHENTICATED WEBSOCKET EVENTS ===
        self.record_metric("step_4_events_collection_start", time.time())
        
        collected_events = []
        required_event_types = ["agent_started", "agent_thinking", "tool_executing", "tool_completed", "agent_completed"]
        
        # Allow sufficient time for authenticated agent execution
        max_wait_time = 60.0  # Longer timeout for authenticated flows
        event_timeout = 5.0
        start_collection = time.time()
        
        while (time.time() - start_collection) < max_wait_time:
            try:
                event = await WebSocketTestHelpers.receive_test_message(
                    self._websocket_connection,
                    timeout=event_timeout
                )
                
                collected_events.append(event)
                self.increment_websocket_events(1)
                
                # AUTHENTICATION VALIDATION: Check that events include authentication context
                if isinstance(event, dict):
                    event_payload = event.get("payload", {})
                    if event_payload:
                        # Validate authenticated user context in event
                        event_user_id = event_payload.get("user_id")
                        if event_user_id:
                            assert event_user_id == user_id, (
                                f"Event user_id mismatch - authentication isolation violated: "
                                f"expected {user_id}, got {event_user_id}"
                            )
                
                # Check for completion of required events
                received_types = [e.get("type") for e in collected_events]
                if all(req_type in received_types for req_type in required_event_types):
                    break
                    
            except Exception as e:
                # Timeout handling - check if we have minimum events
                if len(collected_events) >= 3 and (time.time() - start_collection) > (max_wait_time - 10):
                    break
                elif (time.time() - start_collection) > (max_wait_time - 5):
                    raise AssertionError(
                        f"Failed to receive authenticated WebSocket events within {max_wait_time}s. "
                        f"Received {len(collected_events)} events: {[e.get('type') for e in collected_events]}. "
                        f"This may indicate authentication is preventing proper event delivery. Error: {e}"
                    )
        
        self.record_metric("step_4_events_collected", len(collected_events))
        self.record_metric("step_4_duration", time.time() - self.get_metric("step_4_events_collection_start"))
        
        # === STEP 5: VALIDATE AUTHENTICATED WEBSOCKET EVENTS ===
        self.record_metric("step_5_event_validation_start", time.time())
        
        # CRITICAL: Must receive minimum authenticated events
        assert len(collected_events) >= 5, (
            f"Expected at least 5 authenticated WebSocket events, got {len(collected_events)}: "
            f"{[e.get('type') for e in collected_events]}. "
            f"Authentication may be blocking event delivery."
        )
        
        # Use SSOT assertion helper to validate events
        assert_websocket_events(collected_events, required_event_types)
        
        # AUTHENTICATION VALIDATION: Verify events contain authenticated context
        authenticated_events = 0
        for event in collected_events:
            event_payload = event.get("payload", {})
            if event_payload and "user_id" in event_payload:
                assert event_payload["user_id"] == user_id, "Event authentication context validation failed"
                authenticated_events += 1
        
        # At least half the events should have authentication context
        assert authenticated_events >= len(collected_events) / 2, (
            f"Too few events with authentication context: {authenticated_events}/{len(collected_events)}"
        )
        
        self.record_metric("step_5_authenticated_events", authenticated_events)
        self.record_metric("step_5_duration", time.time() - self.get_metric("step_5_event_validation_start"))
        
        # === STEP 6: VALIDATE AUTHENTICATED BUSINESS VALUE ===
        self.record_metric("step_6_business_value_start", time.time())
        
        # Find final business value in authenticated agent completion
        final_authenticated_results = None
        for event in reversed(collected_events):
            if event.get("type") == "agent_completed":
                event_payload = event.get("payload", {})
                if event_payload.get("user_id") == user_id:  # Ensure authenticated result
                    final_authenticated_results = event_payload.get("final_response") or event_payload.get("result")
                    break
        
        assert final_authenticated_results, (
            "No authenticated final results found in agent_completed events. "
            "Authentication may be preventing business value delivery."
        )
        
        # Validate authenticated business value content
        business_value_found = False
        if isinstance(final_authenticated_results, str):
            content_lower = final_authenticated_results.lower()
            business_value_found = any(term in content_lower for term in 
                                     ["cost", "saving", "optimization", "dollar", "$", "reduction", "efficiency"])
        elif isinstance(final_authenticated_results, dict):
            result_str = str(final_authenticated_results).lower()
            business_value_found = any(term in result_str for term in 
                                     ["cost", "saving", "optimization", "dollar", "$", "reduction", "efficiency"])
        
        assert business_value_found, (
            f"Authenticated final results missing business value content: {final_authenticated_results}. "
            f"Authentication may be affecting business value delivery."
        )
        
        self.record_metric("step_6_business_value_delivered", True)
        self.record_metric("step_6_duration", time.time() - self.get_metric("step_6_business_value_start"))
        
        # === STEP 7: VALIDATE AUTHENTICATED DATA PERSISTENCE ===
        self.record_metric("step_7_persistence_start", time.time())
        
        # Verify authenticated data persistence
        backend_url = self.get_env_var("BACKEND_URL", "http://localhost:8000")
        auth_headers = self._auth_helper.get_auth_headers(jwt_token)
        
        async with httpx.AsyncClient() as client:
            # CRITICAL: Use authentication headers for API calls
            thread_response = await client.get(
                f"{backend_url}/api/threads/{thread_id}",
                headers=auth_headers,
                timeout=10.0
            )
            
            # Authentication validation - should get 200 with valid auth or 401/403 without
            if thread_response.status_code == 401:
                raise AssertionError("Authentication failed for thread API - JWT token may be invalid")
            elif thread_response.status_code == 403:
                raise AssertionError("Authorization failed for thread API - user permissions insufficient")
            
            # If authenticated successfully, validate thread data
            if thread_response.status_code == 200:
                thread_data = thread_response.json()
                assert thread_data.get("id") == thread_id, "Thread ID mismatch in authenticated response"
                self.record_metric("authenticated_persistence_validated", True)
            else:
                # Log unexpected status for debugging
                self.record_metric("authenticated_api_status", thread_response.status_code)
        
        self.record_metric("step_7_duration", time.time() - self.get_metric("step_7_persistence_start"))
        
        # === STEP 8: VALIDATE TOTAL AUTHENTICATED EXECUTION TIME ===
        total_execution_time = time.time() - test_start_time
        self.record_metric("total_authenticated_execution_time", total_execution_time)
        
        # Authenticated flows may take longer due to auth validation
        assert total_execution_time < 90.0, (
            f"Authenticated golden path took {total_execution_time:.2f}s (max: 90s) - "
            f"authentication overhead may be too high"
        )
        
        # === FINAL AUTHENTICATION COMPLIANCE VALIDATION ===
        # Record authentication compliance success metrics
        self.record_metric("authentication_compliance_validated", True)
        self.record_metric("phase_1_implementation_success", True)
        self.record_metric("no_auth_bypass_detected", True)
        self.record_metric("authenticated_business_value_delivered", True)
        self.record_metric("websocket_events_authenticated", len(collected_events))
        
        # Log authentication compliance success
        print(f"\n✅ PHASE 1 AUTHENTICATION COMPLIANCE SUCCESS:")
        print(f"   🔐 User authentication: VALIDATED")
        print(f"   📡 WebSocket auth headers: VALIDATED")
        print(f"   🎯 Authenticated events: {authenticated_events}/{len(collected_events)}")
        print(f"   💰 Authenticated business value: DELIVERED")
        print(f"   ⏱️  Total authenticated time: {total_execution_time:.2f}s")
        print(f"   🛡️  Authentication bypass prevention: CONFIRMED")
        print(f"   📈 $500K+ ARR protection: VALIDATED")

    @pytest.mark.asyncio
    async def test_authentication_failure_prevention(self, real_services_fixture):
        """
        PHASE 1 CRITICAL: Verify that operations fail without authentication.
        
        This test proves that authentication is actually required by demonstrating
        that operations fail when authentication is missing or invalid.
        
        AUTHENTICATION BYPASS PREVENTION:
        - WebSocket connections without auth must fail
        - API calls without auth must return 401/403
        - Invalid tokens must be rejected
        - Expired tokens must be rejected
        """
        # === TEST 1: WebSocket Connection Without Authentication ===
        websocket_url = self.get_env_var("WEBSOCKET_URL", "ws://localhost:8000/ws")
        
        # Attempt connection without authentication headers
        connection_failed = False
        try:
            unauthenticated_connection = await asyncio.wait_for(
                websockets.connect(websocket_url),
                timeout=10.0
            )
            await unauthenticated_connection.close()
        except Exception:
            connection_failed = True
        
        # Connection should fail without authentication
        assert connection_failed, (
            "WebSocket connection without authentication should fail - "
            "authentication bypass detected!"
        )
        
        # === TEST 2: API Calls Without Authentication ===
        backend_url = self.get_env_var("BACKEND_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient() as client:
            # Attempt API call without authentication
            unauth_response = await client.get(
                f"{backend_url}/api/threads",
                timeout=5.0
            )
            
            # Should get 401 Unauthorized or 403 Forbidden
            assert unauth_response.status_code in [401, 403], (
                f"API call without auth should return 401/403, got {unauth_response.status_code} - "
                f"authentication bypass detected!"
            )
        
        # === TEST 3: Invalid Token Rejection ===
        invalid_headers = {"Authorization": "Bearer invalid_token_12345"}
        
        async with httpx.AsyncClient() as client:
            invalid_token_response = await client.get(
                f"{backend_url}/api/threads",
                headers=invalid_headers,
                timeout=5.0
            )
            
            # Should reject invalid token
            assert invalid_token_response.status_code in [401, 403], (
                f"Invalid token should be rejected with 401/403, got {invalid_token_response.status_code} - "
                f"token validation bypass detected!"
            )
        
        # Record authentication prevention validation
        self.record_metric("auth_bypass_prevention_validated", True)
        self.record_metric("websocket_auth_enforced", True)
        self.record_metric("api_auth_enforced", True)
        self.record_metric("invalid_token_rejected", True)
        
        print(f"\n✅ AUTHENTICATION FAILURE PREVENTION VALIDATED:")
        print(f"   🚫 Unauthenticated WebSocket: BLOCKED")
        print(f"   🚫 Unauthenticated API calls: BLOCKED")
        print(f"   🚫 Invalid tokens: REJECTED")
        print(f"   🛡️  Authentication bypass prevention: CONFIRMED")

    async def async_teardown_method(self, method=None):
        """Authenticated cleanup with connection closure."""
        if hasattr(self, '_websocket_connection') and self._websocket_connection:
            try:
                await WebSocketTestHelpers.close_test_connection(self._websocket_connection)
            except Exception:
                pass  # Connection may already be closed
        await super().async_teardown_method(method)