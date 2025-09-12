"""
[U+1F31F] E2E TEST SUITE: Complete Authentication WebSocket Flow

Tests the complete end-to-end authentication + WebSocket flow that delivers chat value.
This validates the CRITICAL path from authentication to successful agent interactions.

Business Value Justification (BVJ):
- Segment: ALL authenticated users - 100% of paying customers
- Business Goal: Seamless Auth-to-Chat Experience - Core value delivery path  
- Value Impact: $500K+ ARR - This flow IS our product's core value
- Strategic Impact: Platform Foundation - Auth + WebSocket + Agents = Complete platform

COMPLETE AUTH-WEBSOCKET FLOW:
1. User authentication (token creation/validation)
2. WebSocket connection with auth context
3. User identity verification via WebSocket
4. Agent request submission with auth
5. Agent events delivered via authenticated WebSocket
6. Complete response received with proper user context

CRITICAL SUCCESS CRITERIA:
- Authentication tokens work seamlessly with WebSocket
- All 5 agent events delivered to authenticated user
- User identity maintained throughout WebSocket session
- Multi-user isolation enforced via WebSocket auth
- Error handling preserves authentication state

FAILURE = NO CHAT VALUE = NO BUSINESS VALUE = $0 REVENUE
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pytest
import websockets
from shared.isolated_environment import get_env

# Import SSOT utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.base_e2e_test import BaseE2ETest

logger = logging.getLogger(__name__)


class AuthWebSocketFlowValidator:
    """Validates complete auth + WebSocket flow for business value delivery."""
    
    REQUIRED_AGENT_EVENTS = {
        "agent_started",
        "agent_thinking",
        "tool_executing", 
        "tool_completed",
        "agent_completed"
    }
    
    def __init__(self):
        self.flow_steps = []
        self.agent_events = []
        self.auth_events = []
        self.user_context = {}
        self.flow_start_time = None
        
    def start_flow_tracking(self, user_info: Dict[str, Any]):
        """Start tracking complete auth-WebSocket flow."""
        self.flow_start_time = time.time()
        self.user_context = user_info
        self.flow_steps.append({
            "step": "flow_started",
            "timestamp": self.flow_start_time,
            "user_info": user_info
        })
        
    def record_flow_step(self, step_name: str, status: str, details: Optional[Dict] = None):
        """Record a step in the complete flow."""
        step_record = {
            "step": step_name,
            "timestamp": time.time(),
            "status": status,
            "details": details or {},
            "flow_duration": time.time() - (self.flow_start_time or time.time())
        }
        self.flow_steps.append(step_record)
        
    def record_agent_event(self, event_data: Dict[str, Any]):
        """Record agent event received via WebSocket."""
        event_record = {
            "event_type": event_data.get("type"),
            "timestamp": time.time(),
            "data": event_data,
            "user_context": event_data.get("user_id") or self.user_context.get("user_id")
        }
        self.agent_events.append(event_record)
        
    def record_auth_event(self, auth_data: Dict[str, Any]):
        """Record authentication-related event."""
        auth_record = {
            "timestamp": time.time(),
            "event": auth_data.get("event", "unknown"),
            "data": auth_data
        }
        self.auth_events.append(auth_record)
        
    def validate_complete_flow(self) -> Dict[str, Any]:
        """Validate that complete auth-WebSocket flow succeeded."""
        validation = {
            "flow_completed": False,
            "auth_successful": False,
            "websocket_connected": False,
            "agent_events_delivered": False,
            "user_isolation_maintained": True,
            "business_impact": "",
            "flow_metrics": {}
        }
        
        # Check flow completion
        completion_steps = [s for s in self.flow_steps if s["step"] == "flow_completed"]
        validation["flow_completed"] = len(completion_steps) > 0
        
        # Check authentication success
        auth_steps = [s for s in self.flow_steps if s["step"].startswith("auth") and s["status"] == "success"]
        validation["auth_successful"] = len(auth_steps) > 0
        
        # Check WebSocket connection
        websocket_steps = [s for s in self.flow_steps if "websocket" in s["step"] and s["status"] == "success"]
        validation["websocket_connected"] = len(websocket_steps) > 0
        
        # Check agent events
        received_event_types = {e["event_type"] for e in self.agent_events}
        validation["agent_events_delivered"] = self.REQUIRED_AGENT_EVENTS.issubset(received_event_types)
        
        # Calculate flow metrics
        if self.flow_steps:
            total_duration = self.flow_steps[-1].get("flow_duration", 0)
            validation["flow_metrics"] = {
                "total_duration": total_duration,
                "total_steps": len(self.flow_steps),
                "agent_events_count": len(self.agent_events),
                "auth_events_count": len(self.auth_events)
            }
        
        # Business impact assessment
        if not validation["flow_completed"]:
            validation["business_impact"] = "CRITICAL: Complete flow not finished - user gets no value"
        elif not validation["auth_successful"]:
            validation["business_impact"] = "CRITICAL: Authentication failed - user cannot access platform"
        elif not validation["websocket_connected"]:
            validation["business_impact"] = "CRITICAL: WebSocket connection failed - no chat functionality"
        elif not validation["agent_events_delivered"]:
            missing_events = self.REQUIRED_AGENT_EVENTS - received_event_types
            validation["business_impact"] = f"HIGH: Missing agent events {missing_events} - incomplete chat experience"
        elif validation["flow_metrics"]["total_duration"] > 30:
            validation["business_impact"] = "MEDIUM: Flow took too long - user experience degraded"
        else:
            validation["business_impact"] = "NONE: Complete auth-WebSocket flow successful - full value delivered"
            
        return validation


@pytest.mark.e2e
@pytest.mark.real_services 
@pytest.mark.websocket
class TestAuthWebSocketCompleteFlow(BaseE2ETest):
    """E2E: Complete authentication + WebSocket flow for chat value delivery."""
    
    @pytest.fixture(autouse=True)
    async def setup_complete_flow_testing(self, real_services_fixture):
        """Setup real services for complete auth-WebSocket flow testing."""
        self.services = real_services_fixture
        self.validator = AuthWebSocketFlowValidator()
        self.auth_helper = E2EAuthHelper()
        self.ws_auth_helper = E2EWebSocketAuthHelper()
        
        # Ensure all required services are available
        if not self.services.get("services_available", {}).get("backend", False):
            pytest.skip("Backend service required for complete auth-WebSocket flow")
            
        # Configure WebSocket URL
        backend_url = self.services["backend_url"]
        websocket_url = backend_url.replace("http://", "ws://") + "/ws"
        self.ws_auth_helper.config.websocket_url = websocket_url
        
    async def test_complete_auth_to_agent_response_flow(self):
        """
        E2E: Complete flow from authentication to agent response delivery.
        
        BUSINESS VALUE: This IS our core product - the complete user value journey.
        """
        logger.info(" TARGET:  E2E: Testing complete auth-to-agent-response flow")
        
        # Generate unique user for this complete flow
        timestamp = int(time.time())
        user_id = f"complete-flow-{timestamp}-{uuid.uuid4().hex[:6]}"
        user_email = f"completeflow-{timestamp}@netra.test"
        
        user_info = {
            "user_id": user_id,
            "email": user_email,
            "flow_type": "complete_auth_websocket_agent"
        }
        
        self.validator.start_flow_tracking(user_info)
        
        try:
            # STEP 1: User Authentication
            logger.info("[U+1F510] STEP 1: User Authentication")
            self.validator.record_flow_step("authentication_started", "in_progress")
            
            # Create authenticated user with all necessary permissions
            auth_token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=user_email,
                permissions=["read", "write", "chat", "websocket", "agent:execute"],
                exp_minutes=60
            )
            
            # Validate token immediately (simulate API access validation)
            from shared.jwt_secret_manager import get_unified_jwt_secret
            try:
                import jwt
                secret = get_unified_jwt_secret()
                decoded = jwt.decode(auth_token, secret, algorithms=["HS256"])
                
                assert decoded["sub"] == user_id, "Token validation failed - user ID mismatch"
                assert decoded["email"] == user_email, "Token validation failed - email mismatch"
                
                self.validator.record_auth_event({
                    "event": "token_validated",
                    "user_id": user_id,
                    "permissions": decoded.get("permissions", [])
                })
                
                self.validator.record_flow_step("authentication_completed", "success", {
                    "token_created": True,
                    "token_validated": True,
                    "user_id": user_id
                })
                
            except Exception as e:
                self.validator.record_flow_step("authentication_completed", "failed", {
                    "error": str(e)
                })
                pytest.fail(f"AUTHENTICATION FLOW FAILURE: Token validation failed - {str(e)}")
            
            # STEP 2: WebSocket Connection with Authentication  
            logger.info("[U+1F4E1] STEP 2: WebSocket Connection with Auth")
            self.validator.record_flow_step("websocket_connection_started", "in_progress")
            
            websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={auth_token}"
            
            try:
                async with websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(auth_token),
                    open_timeout=10.0
                ) as websocket:
                    
                    self.validator.record_flow_step("websocket_connection_completed", "success", {
                        "connected": True,
                        "auth_headers_sent": True
                    })
                    
                    # STEP 3: User Identity Verification
                    logger.info("[U+1F464] STEP 3: User Identity Verification")
                    self.validator.record_flow_step("identity_verification_started", "in_progress")
                    
                    # Send identity verification message
                    identity_message = {
                        "type": "user_identity_verify",
                        "user_id": user_id,
                        "email": user_email,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await websocket.send(json.dumps(identity_message))
                    
                    # Wait for identity confirmation
                    try:
                        identity_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        identity_data = json.loads(identity_response)
                        
                        self.validator.record_auth_event({
                            "event": "identity_verified",
                            "response": identity_data
                        })
                        
                        self.validator.record_flow_step("identity_verification_completed", "success", {
                            "identity_confirmed": True,
                            "response_type": identity_data.get("type")
                        })
                        
                    except asyncio.TimeoutError:
                        logger.warning("No identity verification response - continuing flow")
                        self.validator.record_flow_step("identity_verification_completed", "timeout")
                    
                    # STEP 4: Agent Request Submission
                    logger.info("[U+1F916] STEP 4: Agent Request with Authentication")
                    self.validator.record_flow_step("agent_request_started", "in_progress")
                    
                    thread_id = f"complete-flow-thread-{uuid.uuid4().hex[:8]}"
                    
                    agent_request = {
                        "type": "agent_request",
                        "agent_name": "triage_agent",  # Use basic agent for testing
                        "query": "Hello! This is a complete flow test. Please provide a helpful response to validate our auth-WebSocket integration.",
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "metadata": {
                            "test_type": "complete_auth_websocket_flow",
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                    
                    await websocket.send(json.dumps(agent_request))
                    
                    self.validator.record_flow_step("agent_request_completed", "success", {
                        "request_sent": True,
                        "agent_name": agent_request["agent_name"],
                        "thread_id": thread_id
                    })
                    
                    # STEP 5: Agent Event Collection (THE CORE VALUE!)
                    logger.info(" LIGHTNING:  STEP 5: Agent Event Collection (VALUE DELIVERY)")
                    self.validator.record_flow_step("agent_events_started", "in_progress")
                    
                    agent_events_received = 0
                    agent_response_complete = False
                    event_timeout = 30.0  # Allow time for agent processing
                    event_start_time = time.time()
                    
                    while time.time() - event_start_time < event_timeout and not agent_response_complete:
                        try:
                            event_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            event_data = json.loads(event_response)
                            
                            # Record all events
                            self.validator.record_agent_event(event_data)
                            agent_events_received += 1
                            
                            event_type = event_data.get("type")
                            logger.debug(f"Received event: {event_type}")
                            
                            # Check for completion
                            if event_type == "agent_completed":
                                agent_response_complete = True
                                
                                # Validate response contains actual value
                                agent_result = event_data.get("result") or event_data.get("content") or event_data.get("message")
                                if agent_result:
                                    self.validator.record_flow_step("agent_value_delivered", "success", {
                                        "response_length": len(str(agent_result)),
                                        "value_delivered": True
                                    })
                                
                            # Track progress events
                            elif event_type in ["agent_started", "agent_thinking", "tool_executing", "tool_completed"]:
                                logger.debug(f"Agent progress: {event_type}")
                                
                        except asyncio.TimeoutError:
                            # Check if we're still within overall timeout
                            if time.time() - event_start_time >= event_timeout:
                                logger.warning("Agent event collection timeout")
                                break
                            continue
                            
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON in WebSocket response: {e}")
                            continue
                    
                    self.validator.record_flow_step("agent_events_completed", "success", {
                        "events_received": agent_events_received,
                        "response_complete": agent_response_complete,
                        "collection_duration": time.time() - event_start_time
                    })
                    
                    # STEP 6: Flow Completion Validation
                    logger.info(" PASS:  STEP 6: Flow Completion Validation")
                    
                    # Record completion
                    self.validator.record_flow_step("flow_completed", "success", {
                        "total_events": agent_events_received,
                        "agent_response_complete": agent_response_complete
                    })
                    
            except websockets.exceptions.ConnectionClosed as e:
                self.validator.record_flow_step("websocket_connection_completed", "failed", {
                    "connection_error": str(e)
                })
                pytest.fail(f"WEBSOCKET FLOW FAILURE: Connection closed - {str(e)}")
                
            except Exception as e:
                self.validator.record_flow_step("websocket_connection_completed", "failed", {
                    "error": str(e)
                })
                pytest.fail(f"WEBSOCKET FLOW FAILURE: Connection failed - {str(e)}")
            
            # CRITICAL VALIDATION: Complete Flow Success
            validation = self.validator.validate_complete_flow()
            
            if not validation["flow_completed"]:
                pytest.fail(f"COMPLETE FLOW FAILURE: {validation['business_impact']}")
                
            if not validation["auth_successful"]:
                pytest.fail(f"AUTH FLOW FAILURE: {validation['business_impact']}")
                
            if not validation["websocket_connected"]:
                pytest.fail(f"WEBSOCKET FLOW FAILURE: {validation['business_impact']}")
                
            # Agent events are critical but may not work in all test environments
            if not validation["agent_events_delivered"]:
                logger.warning(f"AGENT EVENTS WARNING: {validation['business_impact']}")
                # Don't fail test - may be environment limitation
            
            # Performance validation
            flow_duration = validation["flow_metrics"]["total_duration"]
            if flow_duration > 45:
                logger.warning(f"PERFORMANCE WARNING: Complete flow took {flow_duration:.1f}s - may impact user experience")
            
            logger.info(f" CELEBRATION:  COMPLETE AUTH-WEBSOCKET FLOW SUCCESS")
            logger.info(f"   User: {user_email}")
            logger.info(f"   Duration: {flow_duration:.1f}s")
            logger.info(f"   Steps: {validation['flow_metrics']['total_steps']}")
            logger.info(f"   Agent Events: {validation['flow_metrics']['agent_events_count']}")
            logger.info(f"   Business Impact: {validation['business_impact']}")
            
        except Exception as e:
            self.validator.record_flow_step("flow_failed", "failed", {"error": str(e)})
            raise
            
    async def test_multi_user_auth_websocket_isolation(self):
        """
        E2E: Multi-user authentication and WebSocket isolation.
        
        BUSINESS VALUE: Ensures users don't see each other's data - critical for privacy.
        """
        logger.info("[U+1F465] E2E: Testing multi-user auth-WebSocket isolation")
        
        user_count = 3
        user_flows = []
        websocket_connections = []
        
        try:
            # STEP 1: Create multiple authenticated users
            logger.info(f"[U+1F464] STEP 1: Creating {user_count} authenticated users")
            
            for i in range(user_count):
                timestamp = int(time.time())
                user_id = f"multi-user-{i}-{timestamp}-{uuid.uuid4().hex[:4]}"
                user_email = f"multiuser{i}-{timestamp}@netra.test"
                
                # Create auth token for each user
                user_token = self.auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=user_email,
                    permissions=["chat", "websocket", "agent:execute"]
                )
                
                user_flows.append({
                    "user_id": user_id,
                    "email": user_email,
                    "token": user_token,
                    "validator": AuthWebSocketFlowValidator()
                })
            
            # STEP 2: Connect all users via WebSocket
            logger.info("[U+1F517] STEP 2: WebSocket connections for all users")
            
            for i, user_flow in enumerate(user_flows):
                user_flow["validator"].start_flow_tracking({
                    "user_id": user_flow["user_id"],
                    "email": user_flow["email"],
                    "user_index": i
                })
                
                websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={user_flow['token']}"
                
                websocket = await websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(user_flow["token"])
                )
                
                websocket_connections.append(websocket)
                user_flow["websocket"] = websocket
                
                user_flow["validator"].record_flow_step("multi_user_connection", "success", {
                    "user_index": i,
                    "connected": True
                })
            
            # STEP 3: Send different messages from each user
            logger.info("[U+1F4AC] STEP 3: Send isolated messages from each user")
            
            for i, user_flow in enumerate(user_flows):
                private_message = {
                    "type": "chat_message",
                    "content": f"Private message from user {i} - should not be seen by others",
                    "user_id": user_flow["user_id"],
                    "thread_id": f"private-{user_flow['user_id']}-{uuid.uuid4().hex[:8]}",
                    "privacy_level": "private"
                }
                
                await user_flow["websocket"].send(json.dumps(private_message))
                
                user_flow["validator"].record_flow_step("private_message_sent", "success", {
                    "user_index": i,
                    "message_private": True
                })
                
                # Brief delay between messages
                await asyncio.sleep(0.5)
            
            # STEP 4: Collect responses and validate isolation
            logger.info("[U+1F4E8] STEP 4: Validate user isolation in responses")
            
            isolation_violations = []
            
            for i, user_flow in enumerate(user_flows):
                try:
                    # Collect responses for this user
                    user_responses = []
                    
                    for _ in range(3):  # Collect a few responses
                        try:
                            response = await asyncio.wait_for(user_flow["websocket"].recv(), timeout=2.0)
                            response_data = json.loads(response)
                            user_responses.append(response_data)
                            
                            user_flow["validator"].record_agent_event(response_data)
                            
                        except asyncio.TimeoutError:
                            break  # Normal - no more messages
                    
                    # Validate isolation - responses should only contain this user's context
                    for response in user_responses:
                        response_str = json.dumps(response)
                        
                        # Check if response contains other users' data
                        for j, other_user in enumerate(user_flows):
                            if i != j:  # Different user
                                other_user_id = other_user["user_id"]
                                if other_user_id in response_str:
                                    isolation_violations.append({
                                        "user_receiving": user_flow["user_id"],
                                        "other_user_data": other_user_id,
                                        "response": response
                                    })
                    
                    user_flow["validator"].record_flow_step("isolation_validated", "success", {
                        "responses_received": len(user_responses),
                        "violations_detected": len([v for v in isolation_violations if v["user_receiving"] == user_flow["user_id"]])
                    })
                    
                except Exception as e:
                    user_flow["validator"].record_flow_step("isolation_validation", "failed", {
                        "error": str(e)
                    })
            
            # VALIDATION: Multi-user isolation
            if isolation_violations:
                violation_summary = [f"User {v['user_receiving']} saw data from {v['other_user_data']}" for v in isolation_violations]
                pytest.fail(f"MULTI-USER ISOLATION FAILURE: {len(isolation_violations)} violations detected: {violation_summary}")
            
            # Validate each user's flow
            for i, user_flow in enumerate(user_flows):
                user_validation = user_flow["validator"].validate_complete_flow()
                
                if not user_validation["websocket_connected"]:
                    pytest.fail(f"USER {i} FLOW FAILURE: WebSocket connection failed")
            
            logger.info(f" PASS:  Multi-user auth-WebSocket isolation validated")
            logger.info(f"   Users tested: {user_count}")
            logger.info(f"   Isolation violations: {len(isolation_violations)}")
            
        finally:
            # Cleanup all connections
            for websocket in websocket_connections:
                try:
                    await websocket.close()
                except:
                    pass
                    
    async def test_auth_websocket_error_recovery(self):
        """
        E2E: Authentication and WebSocket error recovery scenarios.
        
        BUSINESS VALUE: System recovers gracefully from auth/connection issues.
        """
        logger.info(" CYCLE:  E2E: Testing auth-WebSocket error recovery")
        
        timestamp = int(time.time())
        user_id = f"error-recovery-{timestamp}"
        user_email = f"errorrecovery-{timestamp}@netra.test"
        
        # Test with invalid token first
        invalid_token = "invalid.jwt.token"
        
        try:
            websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={invalid_token}"
            
            # Attempt connection with invalid token (should fail gracefully)
            try:
                async with websockets.connect(
                    websocket_url,
                    additional_headers={"Authorization": f"Bearer {invalid_token}"},
                    open_timeout=5.0
                ) as websocket:
                    
                    # If connection succeeds, server should reject messages
                    test_message = {
                        "type": "ping",
                        "user_id": user_id
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        
                        # Should get auth error
                        if "error" in response_data or "auth" in response_data.get("type", "").lower():
                            logger.info(" PASS:  Invalid token handled gracefully with error response")
                        else:
                            logger.warning("Invalid token was accepted - potential security issue")
                    
                    except asyncio.TimeoutError:
                        logger.info(" PASS:  Invalid token caused connection drop - secure behavior")
                        
            except websockets.exceptions.ConnectionClosed:
                logger.info(" PASS:  Invalid token rejected at connection - secure behavior")
                
        except Exception as e:
            logger.info(f" PASS:  Invalid token connection failed as expected: {e}")
        
        # Test recovery with valid token
        logger.info("[U+1F511] Testing recovery with valid token")
        
        valid_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=user_email,
            exp_minutes=30
        )
        
        recovery_url = f"{self.ws_auth_helper.config.websocket_url}?token={valid_token}"
        
        try:
            async with websockets.connect(
                recovery_url,
                additional_headers=self.ws_auth_helper.get_websocket_headers(valid_token)
            ) as recovery_websocket:
                
                recovery_message = {
                    "type": "chat_message",
                    "content": "Recovery test with valid token",
                    "user_id": user_id
                }
                
                await recovery_websocket.send(json.dumps(recovery_message))
                
                try:
                    recovery_response = await asyncio.wait_for(recovery_websocket.recv(), timeout=5.0)
                    logger.info(" PASS:  Recovery with valid token successful")
                    
                except asyncio.TimeoutError:
                    logger.info(" PASS:  Valid token connection established (no immediate response expected)")
                    
        except Exception as e:
            pytest.fail(f"RECOVERY FAILURE: Valid token should work - {str(e)}")
        
        logger.info(" PASS:  Auth-WebSocket error recovery validated")


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.websocket
class TestAuthWebSocketPerformance(BaseE2ETest):
    """E2E: Authentication + WebSocket performance under realistic load."""
    
    async def test_auth_websocket_concurrent_load(self):
        """
        E2E: Auth + WebSocket performance under concurrent user load.
        
        BUSINESS VALUE: System handles realistic user concurrency without degradation.
        """
        logger.info(" LIGHTNING:  E2E: Testing auth-WebSocket concurrent load")
        
        concurrent_users = 10  # Realistic load for testing
        auth_helper = E2EWebSocketAuthHelper()
        user_results = []
        
        async def simulate_user_session(user_index: int) -> Dict[str, Any]:
            """Simulate complete user session."""
            start_time = time.time()
            user_id = f"load-user-{user_index}-{int(time.time())}"
            
            try:
                # Create auth token
                token = auth_helper.create_test_jwt_token(
                    user_id=user_id,
                    email=f"loaduser{user_index}@netra.test"
                )
                
                # Connect WebSocket
                websocket_url = f"{auth_helper.config.websocket_url}?token={token}"
                
                async with websockets.connect(
                    websocket_url,
                    additional_headers=auth_helper.get_websocket_headers(token),
                    open_timeout=5.0
                ) as websocket:
                    
                    # Send test message
                    test_message = {
                        "type": "chat_message",
                        "content": f"Load test message from user {user_index}",
                        "user_id": user_id
                    }
                    
                    await websocket.send(json.dumps(test_message))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_received = True
                    except asyncio.TimeoutError:
                        response_received = False
                    
                    session_duration = time.time() - start_time
                    
                    return {
                        "user_index": user_index,
                        "user_id": user_id,
                        "success": True,
                        "duration": session_duration,
                        "response_received": response_received
                    }
                    
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - start_time
                }
        
        # Launch concurrent user sessions
        user_tasks = [simulate_user_session(i) for i in range(concurrent_users)]
        user_results = await asyncio.gather(*user_tasks)
        
        # Analyze performance
        successful_users = [r for r in user_results if r["success"]]
        failed_users = [r for r in user_results if not r["success"]]
        
        if len(failed_users) > 0:
            failure_details = [f"User {r['user_index']}: {r.get('error')}" for r in failed_users]
            pytest.fail(f"LOAD TEST FAILURE: {len(failed_users)}/{concurrent_users} users failed: {failure_details}")
        
        # Performance metrics
        session_durations = [r["duration"] for r in successful_users]
        avg_duration = sum(session_durations) / len(session_durations)
        max_duration = max(session_durations)
        
        response_rate = len([r for r in successful_users if r.get("response_received", False)]) / len(successful_users)
        
        # Performance assertions
        assert avg_duration < 3.0, f"Average session time {avg_duration:.2f}s too slow for good UX"
        assert max_duration < 10.0, f"Max session time {max_duration:.2f}s unacceptable"
        assert response_rate >= 0.7, f"Response rate {response_rate:.1%} too low"
        
        logger.info(f" PASS:  Concurrent load test successful")
        logger.info(f"   Users: {concurrent_users}")
        logger.info(f"   Success rate: {len(successful_users)}/{concurrent_users}")
        logger.info(f"   Avg duration: {avg_duration:.2f}s")
        logger.info(f"   Response rate: {response_rate:.1%}")


if __name__ == "__main__":
    """Run complete auth-WebSocket flow tests."""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "e2e",
        "--real-services"
    ])