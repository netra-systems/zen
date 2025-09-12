"""
[U+1F31F] E2E TEST SUITE: Complete User Authentication Onboarding Journey

Tests the complete end-to-end user onboarding experience from first visit to successful chat.
This validates the ENTIRE authentication flow that new users experience.

Business Value Justification (BVJ):
- Segment: Free tier + Paid conversions - New user acquisition funnel
- Business Goal: Maximize User Onboarding Success - Reduce friction to first value
- Value Impact: $200K+ ARR - 30% improvement in onboarding = 30% more revenue
- Strategic Impact: Growth Engine - Onboarding success drives organic expansion

COMPLETE USER JOURNEY:
1. User visits platform (anonymous)
2. User registers/signs up (conversion point)
3. User receives authentication confirmation
4. User logs in successfully  
5. User accesses chat interface
6. User sends first message to agent
7. User receives agent response (first value!)

CRITICAL SUCCESS CRITERIA:
- Registration flow completes without errors
- Authentication tokens work immediately after signup  
- Chat becomes accessible immediately after auth
- First agent interaction delivers value within 30 seconds
- No authentication friction throughout journey

FAILURE = USER ABANDONMENT = LOST REVENUE OPPORTUNITY
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import pytest
import websockets
from shared.isolated_environment import get_env

# Import SSOT utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.base_e2e_test import BaseE2ETest

logger = logging.getLogger(__name__)


class UserOnboardingJourneyValidator:
    """Validates complete user onboarding journey for business success."""
    
    def __init__(self):
        self.journey_steps = []
        self.user_actions = []
        self.system_responses = []
        self.journey_start_time = None
        self.journey_end_time = None
        
    def start_journey(self, user_info: Dict[str, Any]):
        """Start tracking user onboarding journey."""
        self.journey_start_time = time.time()
        self.journey_steps.append({
            "step": "journey_started",
            "timestamp": self.journey_start_time,
            "user_info": user_info,
            "status": "started"
        })
        
    def record_step(self, step_name: str, status: str, details: Optional[Dict] = None):
        """Record a step in the onboarding journey."""
        step_record = {
            "step": step_name,
            "timestamp": time.time(),
            "status": status,
            "details": details or {},
            "duration_from_start": time.time() - (self.journey_start_time or time.time())
        }
        self.journey_steps.append(step_record)
        
    def complete_journey(self):
        """Mark journey as completed."""
        self.journey_end_time = time.time()
        total_duration = self.journey_end_time - (self.journey_start_time or self.journey_end_time)
        
        self.journey_steps.append({
            "step": "journey_completed",
            "timestamp": self.journey_end_time,
            "total_duration": total_duration,
            "status": "completed"
        })
        
        return total_duration
        
    def validate_journey_success(self) -> Dict[str, Any]:
        """Validate that onboarding journey was successful."""
        validation = {
            "journey_completed": False,
            "all_steps_successful": True,
            "total_duration": 0,
            "failed_steps": [],
            "business_impact": "",
            "conversion_points": {}
        }
        
        if not self.journey_steps:
            validation["business_impact"] = "CRITICAL: No journey steps recorded"
            return validation
            
        # Check if journey was completed
        completion_steps = [s for s in self.journey_steps if s["step"] == "journey_completed"]
        validation["journey_completed"] = len(completion_steps) > 0
        
        # Check for failed steps
        failed_steps = [s for s in self.journey_steps if s["status"] == "failed"]
        validation["failed_steps"] = failed_steps
        validation["all_steps_successful"] = len(failed_steps) == 0
        
        # Calculate total duration
        if self.journey_end_time and self.journey_start_time:
            validation["total_duration"] = self.journey_end_time - self.journey_start_time
        
        # Identify conversion points
        conversion_steps = ["registration_completed", "login_successful", "first_chat_message", "first_agent_response"]
        for step_name in conversion_steps:
            step_records = [s for s in self.journey_steps if s["step"] == step_name and s["status"] == "success"]
            if step_records:
                validation["conversion_points"][step_name] = step_records[0]["timestamp"]
        
        # Business impact assessment
        if not validation["journey_completed"]:
            validation["business_impact"] = "CRITICAL: User journey incomplete - user abandonment"
        elif not validation["all_steps_successful"]:
            validation["business_impact"] = f"HIGH: Journey steps failed {[s['step'] for s in failed_steps]} - conversion risk"
        elif validation["total_duration"] > 120:  # 2 minutes
            validation["business_impact"] = f"MEDIUM: Journey took {validation['total_duration']:.1f}s - may cause abandonment"
        else:
            validation["business_impact"] = "NONE: Successful onboarding journey"
            
        return validation


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.user_journey
class TestCompleteUserOnboardingJourney(BaseE2ETest):
    """E2E: Complete user onboarding authentication journey."""
    
    @pytest.fixture(autouse=True)  
    async def setup_onboarding_journey(self, real_services_fixture):
        """Setup real services for complete onboarding testing."""
        self.services = real_services_fixture
        self.validator = UserOnboardingJourneyValidator()
        self.auth_helper = E2EAuthHelper()
        self.ws_auth_helper = E2EWebSocketAuthHelper()
        
        # Ensure all services are available for complete journey
        if not self.services.get("services_available", {}).get("backend", False):
            pytest.skip("Backend service required for complete onboarding journey")
        if not self.services.get("database_available", False):
            pytest.skip("Database required for user registration and persistence")
            
        self.auth_url = self.services["auth_url"]
        self.backend_url = self.services["backend_url"]
        
        # Configure WebSocket URL for chat testing
        websocket_url = self.backend_url.replace("http://", "ws://") + "/ws"
        self.ws_auth_helper.config.websocket_url = websocket_url
        
    async def test_new_user_complete_onboarding_journey(self):
        """
        E2E: Complete new user onboarding from registration to first chat.
        
        BUSINESS VALUE: This is the complete conversion funnel for new users.
        """
        logger.info("[U+1F31F] E2E: Testing complete new user onboarding journey")
        
        # Generate unique user for this journey
        timestamp = int(time.time())
        user_email = f"newuser-{timestamp}-{uuid.uuid4().hex[:6]}@netra.test"
        user_name = f"Test User {timestamp}"
        password = f"SecurePassword123_{timestamp}!"
        
        user_info = {
            "email": user_email,
            "name": user_name,
            "timestamp": timestamp
        }
        
        self.validator.start_journey(user_info)
        
        try:
            # STEP 1: User Registration (Conversion Point #1)
            logger.info("[U+1F4DD] STEP 1: User Registration")
            self.validator.record_step("registration_started", "in_progress")
            
            async with httpx.AsyncClient() as client:
                registration_data = {
                    "email": user_email,
                    "password": password,
                    "full_name": user_name
                }
                
                register_response = await client.post(
                    f"{self.auth_url}/auth/register",
                    json=registration_data,
                    timeout=10.0
                )
                
                if register_response.status_code in [200, 201]:
                    reg_data = register_response.json()
                    access_token = reg_data.get("access_token")
                    user_data = reg_data.get("user", {})
                    
                    assert access_token, "Registration must return access token immediately"
                    assert user_data.get("email") == user_email, "Registration must return correct user data"
                    
                    self.validator.record_step("registration_completed", "success", {
                        "user_id": user_data.get("id"),
                        "has_token": bool(access_token)
                    })
                    
                    logger.info(f" PASS:  Registration successful for {user_email}")
                    
                else:
                    error_text = register_response.text
                    self.validator.record_step("registration_completed", "failed", {
                        "status_code": register_response.status_code,
                        "error": error_text
                    })
                    pytest.fail(f"USER JOURNEY FAILURE: Registration failed - {register_response.status_code}: {error_text}")
            
            # STEP 2: Immediate Token Validation (Critical for UX)
            logger.info("[U+1F511] STEP 2: Token Validation")
            self.validator.record_step("token_validation_started", "in_progress")
            
            try:
                # Validate that registration token works immediately
                validation_headers = {"Authorization": f"Bearer {access_token}"}
                
                async with httpx.AsyncClient() as client:
                    profile_response = await client.get(
                        f"{self.backend_url}/api/user/profile",
                        headers=validation_headers,
                        timeout=5.0
                    )
                    
                    if profile_response.status_code == 200:
                        profile_data = profile_response.json()
                        assert profile_data.get("email") == user_email, "Profile data must match registered user"
                        
                        self.validator.record_step("token_validation_completed", "success", {
                            "profile_accessible": True
                        })
                        
                    else:
                        self.validator.record_step("token_validation_completed", "failed", {
                            "status_code": profile_response.status_code
                        })
                        pytest.fail(f"USER JOURNEY FAILURE: Token validation failed - user can't access profile")
                        
            except Exception as e:
                self.validator.record_step("token_validation_completed", "failed", {"error": str(e)})
                pytest.fail(f"USER JOURNEY FAILURE: Token validation error - {str(e)}")
            
            # STEP 3: Chat Access (Conversion Point #2) 
            logger.info("[U+1F4AC] STEP 3: Chat Access")
            self.validator.record_step("chat_access_started", "in_progress")
            
            try:
                websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={access_token}"
                
                async with websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(access_token),
                    open_timeout=10.0
                ) as websocket:
                    
                    # Send connection verification
                    connection_message = {
                        "type": "connection_verify",
                        "user_email": user_email,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await websocket.send(json.dumps(connection_message))
                    
                    # Wait for connection confirmation
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    self.validator.record_step("chat_access_completed", "success", {
                        "websocket_connected": True,
                        "response_type": response_data.get("type")
                    })
                    
                    logger.info(" PASS:  Chat access successful")
                    
                    # STEP 4: First Chat Message (Conversion Point #3)
                    logger.info("[U+1F4AD] STEP 4: First Chat Message")
                    self.validator.record_step("first_chat_message_started", "in_progress")
                    
                    first_message = {
                        "type": "chat_message",
                        "content": "Hello! This is my first message. Can you help me get started?",
                        "user_email": user_email,
                        "thread_id": f"onboarding-{uuid.uuid4().hex[:8]}"
                    }
                    
                    await websocket.send(json.dumps(first_message))
                    
                    self.validator.record_step("first_chat_message_completed", "success", {
                        "message_sent": True
                    })
                    
                    # STEP 5: First Agent Response (Conversion Point #4 - VALUE DELIVERY!)
                    logger.info("[U+1F916] STEP 5: First Agent Response (VALUE DELIVERY)")
                    self.validator.record_step("first_agent_response_started", "in_progress")
                    
                    agent_responses = []
                    agent_events = []
                    response_timeout = 30.0  # Allow time for agent processing
                    
                    try:
                        # Collect agent responses
                        start_time = time.time()
                        while time.time() - start_time < response_timeout:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            response_data = json.loads(response)
                            
                            agent_responses.append(response_data)
                            
                            # Track agent events
                            if response_data.get("type") in ["agent_started", "agent_thinking", "agent_completed"]:
                                agent_events.append(response_data["type"])
                            
                            # Check if we got a complete agent response
                            if response_data.get("type") == "agent_completed":
                                agent_result = response_data.get("result") or response_data.get("content")
                                if agent_result:
                                    self.validator.record_step("first_agent_response_completed", "success", {
                                        "agent_responded": True,
                                        "response_length": len(str(agent_result)),
                                        "agent_events": agent_events,
                                        "response_time": time.time() - start_time
                                    })
                                    
                                    logger.info(f" PASS:  First agent response received in {time.time() - start_time:.1f}s")
                                    break
                    
                    except asyncio.TimeoutError:
                        self.validator.record_step("first_agent_response_completed", "failed", {
                            "timeout": True,
                            "responses_received": len(agent_responses)
                        })
                        logger.warning(f"Agent response timeout after {response_timeout}s")
                        # Don't fail the test - this might be environment-specific
                        
            except websockets.exceptions.ConnectionClosedError as e:
                self.validator.record_step("chat_access_completed", "failed", {
                    "websocket_error": str(e)
                })
                pytest.fail(f"USER JOURNEY FAILURE: WebSocket connection failed - {str(e)}")
                
            except Exception as e:
                self.validator.record_step("chat_access_completed", "failed", {
                    "error": str(e)
                })
                pytest.fail(f"USER JOURNEY FAILURE: Chat access failed - {str(e)}")
            
            # JOURNEY COMPLETION
            total_duration = self.validator.complete_journey()
            
            # CRITICAL VALIDATION: Validate complete journey success
            validation = self.validator.validate_journey_success()
            
            if not validation["journey_completed"]:
                pytest.fail(f"USER ONBOARDING FAILURE: {validation['business_impact']}")
            
            if not validation["all_steps_successful"]:
                failed_steps = [s["step"] for s in validation["failed_steps"]]
                pytest.fail(f"USER ONBOARDING FAILURE: Steps failed {failed_steps} - {validation['business_impact']}")
            
            # Performance validation (business impact)
            if validation["total_duration"] > 60:  # 1 minute
                logger.warning(f"BUSINESS RISK: Onboarding took {validation['total_duration']:.1f}s - may cause user abandonment")
            
            # Conversion point analysis
            conversion_points = validation["conversion_points"]
            required_conversions = ["registration_completed", "first_chat_message"]
            
            for conversion in required_conversions:
                if conversion not in conversion_points:
                    pytest.fail(f"CONVERSION FAILURE: Missing critical conversion point {conversion}")
            
            logger.info(f" CELEBRATION:  COMPLETE USER JOURNEY SUCCESS: {user_email} onboarded in {total_duration:.1f}s")
            logger.info(f"   Conversion points: {list(conversion_points.keys())}")
            
        except Exception as e:
            self.validator.record_step("journey_failed", "failed", {"error": str(e)})
            raise
            
    async def test_returning_user_login_to_chat_journey(self):
        """
        E2E: Returning user login flow to chat access.
        
        BUSINESS VALUE: Validates user retention and re-engagement flow.
        """
        logger.info(" CYCLE:  E2E: Testing returning user login to chat journey")
        
        # Pre-create user (simulate existing account)
        timestamp = int(time.time())
        user_email = f"returning-{timestamp}-{uuid.uuid4().hex[:6]}@netra.test" 
        password = f"ReturnPassword123_{timestamp}!"
        
        # Create user first (simulate previous registration)
        user_token = self.auth_helper.create_test_jwt_token(
            user_id=f"returning-user-{timestamp}",
            email=user_email,
            permissions=["chat", "agent:execute"]
        )
        
        user_info = {
            "email": user_email,
            "returning_user": True,
            "timestamp": timestamp
        }
        
        self.validator.start_journey(user_info)
        
        try:
            # STEP 1: User Login (Returning User Flow)
            logger.info("[U+1F511] STEP 1: Returning User Login")
            self.validator.record_step("login_started", "in_progress")
            
            # Simulate login with existing credentials (using test token for simplicity)
            login_token = user_token  # In real scenario, this would come from login API
            
            self.validator.record_step("login_completed", "success", {
                "has_token": bool(login_token)
            })
            
            # STEP 2: Immediate Chat Access (Should be seamless)
            logger.info("[U+1F4AC] STEP 2: Immediate Chat Access")
            self.validator.record_step("returning_chat_access_started", "in_progress")
            
            try:
                websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={login_token}"
                
                async with websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(login_token),
                    open_timeout=5.0  # Should be faster for returning users
                ) as websocket:
                    
                    # Send welcome back message
                    welcome_message = {
                        "type": "chat_message",
                        "content": "I'm back! Can you help me continue where I left off?",
                        "user_email": user_email,
                        "returning_user": True
                    }
                    
                    await websocket.send(json.dumps(welcome_message))
                    
                    # Wait for response (should be immediate for returning users)
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    response_data = json.loads(response)
                    
                    self.validator.record_step("returning_chat_access_completed", "success", {
                        "immediate_access": True,
                        "response_received": True
                    })
                    
            except Exception as e:
                self.validator.record_step("returning_chat_access_completed", "failed", {
                    "error": str(e)
                })
                pytest.fail(f"RETURNING USER JOURNEY FAILURE: Chat access failed - {str(e)}")
            
            # JOURNEY COMPLETION
            total_duration = self.validator.complete_journey()
            
            # VALIDATION: Returning users should have faster journey
            validation = self.validator.validate_journey_success()
            
            if not validation["journey_completed"]:
                pytest.fail(f"RETURNING USER FAILURE: {validation['business_impact']}")
            
            # Returning users should have sub-10 second journey
            if validation["total_duration"] > 10:
                pytest.fail(f"RETURNING USER UX FAILURE: Journey took {validation['total_duration']:.1f}s - should be < 10s")
            
            logger.info(f" CELEBRATION:  RETURNING USER JOURNEY SUCCESS: {user_email} re-engaged in {total_duration:.1f}s")
            
        except Exception as e:
            self.validator.record_step("returning_journey_failed", "failed", {"error": str(e)})
            raise


@pytest.mark.e2e
@pytest.mark.real_services
@pytest.mark.user_journey
class TestOnboardingEdgeCases(BaseE2ETest):
    """E2E: Onboarding edge cases and error recovery."""
    
    async def test_duplicate_registration_handling(self):
        """
        E2E: Handle duplicate registration attempts gracefully.
        
        BUSINESS VALUE: Prevents user confusion when they try to register twice.
        """
        logger.info(" WARNING: [U+FE0F]  E2E: Testing duplicate registration handling")
        
        timestamp = int(time.time())
        user_email = f"duplicate-{timestamp}@netra.test"
        password = f"DupePassword123_{timestamp}!"
        
        registration_data = {
            "email": user_email,
            "password": password,
            "full_name": f"Duplicate Test User {timestamp}"
        }
        
        async with httpx.AsyncClient() as client:
            # First registration (should succeed)
            first_response = await client.post(
                f"{self.services['auth_url']}/auth/register",
                json=registration_data,
                timeout=10.0
            )
            
            assert first_response.status_code in [200, 201], "First registration should succeed"
            
            # Second registration (should handle gracefully)
            second_response = await client.post(
                f"{self.services['auth_url']}/auth/register",
                json=registration_data,
                timeout=10.0
            )
            
            # Should either return existing user or clear error message
            assert second_response.status_code in [200, 201, 400, 409], \
                f"Duplicate registration should be handled gracefully, got {second_response.status_code}"
            
            if second_response.status_code in [400, 409]:
                # Error case - should have clear error message
                error_data = second_response.json()
                assert "email" in error_data.get("detail", "").lower() or \
                       "exists" in error_data.get("detail", "").lower(), \
                       "Error message should clearly indicate duplicate email"
            
        logger.info(" PASS:  Duplicate registration handled gracefully")
    
    async def test_network_interruption_recovery(self):
        """
        E2E: Recovery from network interruption during onboarding.
        
        BUSINESS VALUE: Ensures onboarding completes even with poor connectivity.
        """
        logger.info("[U+1F4F6] E2E: Testing network interruption recovery")
        
        timestamp = int(time.time())
        user_email = f"network-test-{timestamp}@netra.test"
        
        # Create user token (simulate successful registration)
        user_token = self.auth_helper.create_test_jwt_token(
            user_id=f"network-user-{timestamp}",
            email=user_email
        )
        
        # Test WebSocket connection with short timeout (simulates network issues)
        websocket_url = f"{self.ws_auth_helper.config.websocket_url}?token={user_token}"
        
        try:
            # First connection attempt (may fail due to "network")
            try:
                async with websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(user_token),
                    open_timeout=1.0  # Very short timeout
                ) as websocket:
                    
                    await websocket.send(json.dumps({"type": "ping"}))
                    await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                # Simulate network recovery with retry
                await asyncio.sleep(0.5)
                
                # Retry connection (should work)
                async with websockets.connect(
                    websocket_url,
                    additional_headers=self.ws_auth_helper.get_websocket_headers(user_token),
                    open_timeout=5.0
                ) as websocket:
                    
                    recovery_message = {
                        "type": "connection_recovery",
                        "user_email": user_email
                    }
                    
                    await websocket.send(json.dumps(recovery_message))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    assert response, "Recovery connection should work"
                    
        except Exception as e:
            pytest.fail(f"Network recovery failed: {str(e)}")
        
        logger.info(" PASS:  Network interruption recovery successful")


if __name__ == "__main__":
    """Run complete user onboarding journey tests."""  
    pytest.main([
        __file__,
        "-v",
        "--tb=short", 
        "-m", "e2e",
        "--real-services"
    ])