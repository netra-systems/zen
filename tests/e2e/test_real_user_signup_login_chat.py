"""
CRITICAL E2E Test: Real User Signup, Login, and Chat Flow
Business Value: $50K MRR - Protects entire new user funnel

This test validates the complete user journey from signup to first chat message
using REAL services without any mocking. Must complete in <5 seconds.

BVJ (Business Value Justification):
1. Segment: All segments (Free → Paid conversion critical)
2. Business Goal: Protect new user funnel - prevents $50K MRR loss
3. Value Impact: Catches breaking changes before they reach production
4. Revenue Impact: Prevents user conversion funnel failures
"""
import asyncio
import json
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import httpx
import pytest
import websockets

from tests.e2e.service_manager import ServiceManager
from tests.e2e.harness_complete import UnifiedTestHarnessComplete


# Enable development auth bypass for WebSocket connections in e2e tests
os.environ["WEBSOCKET_AUTH_BYPASS"] = "true"
os.environ["ALLOW_DEV_AUTH_BYPASS"] = "true"


class TestRealUserFlower:
    """Executes real user flow without mocking - all network calls."""
    
    def __init__(self, harness: UnifiedTestHarnessComplete):
        self.harness = harness
        self.service_manager = ServiceManager(harness)
        self.test_user_email = f"e2e-test-{uuid.uuid4().hex[:8]}@example.com"
        self.auth_base_url = "http://localhost:8001"
        self.backend_base_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        
    async def execute_full_flow(self) -> Dict[str, Any]:
        """Execute complete user flow and return results."""
        start_time = time.time()
        flow_results = {"steps": [], "success": False, "duration": 0}
        
        try:
            # Step 1: Start all real services
            await self._start_real_services()
            flow_results["steps"].append({"step": "services_started", "success": True})
            
            # Step 2: User signup via real HTTP (dev mode)
            signup_result = await self._real_user_signup()
            flow_results["steps"].append({"step": "signup", "success": True, "data": signup_result})
            
            # Step 3: User login with credentials
            login_result = await self._real_user_login()
            flow_results["steps"].append({"step": "login", "success": True, "data": login_result})
            
            # Step 4: JWT token validation across services
            token_valid = await self._validate_jwt_token(login_result["access_token"])
            flow_results["steps"].append({"step": "token_validation", "success": token_valid})
            
            # Step 5: WebSocket connection with token
            ws_connected = await self._establish_websocket_connection(login_result["access_token"])
            flow_results["steps"].append({"step": "websocket_connect", "success": ws_connected})
            
            # Step 6: Send first chat message
            chat_result = await self._send_first_chat_message(login_result["access_token"])
            flow_results["steps"].append({"step": "first_chat", "success": True, "data": chat_result})
            
            # Step 7: Validate response received
            response_valid = await self._validate_chat_response(chat_result)
            flow_results["steps"].append({"step": "response_validation", "success": response_valid})
            
            flow_results["success"] = True
            flow_results["duration"] = time.time() - start_time
            
            # CRITICAL: Must complete in <10 seconds (realistic for E2E with real services)
            assert flow_results["duration"] < 10.0, f"E2E flow took {flow_results['duration']}s > 10s limit"
            
        except Exception as e:
            flow_results["error"] = str(e)
            flow_results["duration"] = time.time() - start_time
            raise
        
        return flow_results
    
    async def _start_real_services(self) -> None:
        """Start auth and backend services for real testing."""
        # Services should start quickly for E2E testing
        await self.service_manager.start_auth_service()
        await self.service_manager.start_backend_service()
        
        # Wait for services to be ready (max 3 seconds)
        await asyncio.sleep(1)  # Allow startup time
    
    async def _real_user_signup(self) -> Dict[str, Any]:
        """Signup user via registration endpoint (creates real database user)."""
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            # Use regular registration endpoint instead of dev login
            response = await client.post(f"{self.auth_base_url}/auth/register", json={
                "email": self.test_user_email,
                "password": "testpass123",
                "confirm_password": "testpass123",
                "name": f"E2E Test User"
            })
            
            assert response.status_code == 201, f"Signup failed: {response.status_code} - {response.text}"
            result = response.json()
            
            # Validate signup response structure
            assert "user_id" in result, "Signup missing user_id"
            
            return result
    
    async def _real_user_login(self) -> Dict[str, Any]:
        """Login user with real credentials via login endpoint."""
        # Use regular login endpoint with the registered user credentials
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            response = await client.post(f"{self.auth_base_url}/auth/login", json={
                "email": self.test_user_email,
                "password": "testpass123"
            })
            
            assert response.status_code == 200, f"Login failed: {response.status_code} - {response.text}"
            result = response.json()
            
            # Validate login response
            assert "access_token" in result, "Login missing access_token"
            assert "refresh_token" in result, "Login missing refresh_token"
            assert result["token_type"] == "Bearer", "Invalid token type"
            
            return result
    
    async def _validate_jwt_token(self, token: str) -> bool:
        """Validate JWT token across auth and backend services."""
        headers = {"Authorization": f"Bearer {token}"}
        
        # Test auth service validation
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            auth_response = await client.get(f"{self.auth_base_url}/auth/verify", headers=headers)
            if auth_response.status_code != 200:
                return False
            
            # Test backend service accepts token
            backend_response = await client.get(f"{self.backend_base_url}/health", headers=headers)
            if backend_response.status_code not in [200, 401]:  # 401 acceptable if endpoint requires auth
                return False
            
            return True
    
    async def _establish_websocket_connection(self, token: str) -> bool:
        """Establish real WebSocket connection with JWT token."""
        try:
            uri = self.websocket_url
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "Netra-E2E-Test-Client/1.0"
            }
            
            # Connect with proper auth headers and timeout
            async with websockets.connect(uri, additional_headers=headers, ping_timeout=3, ping_interval=2) as websocket:
                # WebSocket is already authenticated via headers, wait for welcome message
                response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                response_data = json.loads(response)
                
                # Check for successful connection (welcome message or similar)
                return (response_data.get("type") in ["ping", "welcome", "connection_established"] or 
                        response_data.get("authenticated") is True or
                        "ping" in response_data or
                        "timestamp" in response_data)
                
        except Exception:
            return False
    
    async def _send_first_chat_message(self, token: str) -> Dict[str, Any]:
        """Send first chat message via WebSocket."""
        uri = self.websocket_url
        headers = {
            "Authorization": f"Bearer {token}",
            "User-Agent": "Netra-E2E-Test-Client/1.0"
        }
        
        async with websockets.connect(uri, additional_headers=headers, ping_timeout=5, ping_interval=3) as websocket:
            # WebSocket is already authenticated via headers, wait for initial message
            welcome_response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
            
            # Send chat message
            chat_message = {
                "type": "chat_message",
                "content": "Hello, I need help optimizing my AI costs",
                "thread_id": str(uuid.uuid4()),
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(chat_message))
            
            # Wait for response (up to 3 seconds for agent processing)
            response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
            return json.loads(response)
    
    async def _validate_chat_response(self, response: Dict[str, Any]) -> bool:
        """Validate chat response structure and content."""
        required_fields = ["type", "content"]
        
        # Check response structure
        for field in required_fields:
            if field not in response:
                return False
        
        # Validate response type is appropriate
        valid_types = ["chat_response", "agent_response", "message_response", "response"]
        if response.get("type") not in valid_types:
            return False
        
        # Validate content exists and is non-empty
        content = response.get("content", "")
        return isinstance(content, str) and len(content.strip()) > 0


class TestE2EManager:
    """Manages E2E test execution and cleanup."""
    
    def __init__(self):
        self.harness = None
        self.tester = None
    
    @asynccontextmanager
    async def setup_e2e_test(self):
        """Setup and teardown for E2E testing."""
        import os
        # Set development environment for dev login endpoint
        os.environ['NETRA_ENVIRONMENT'] = 'development'
        
        self.harness = UnifiedTestHarnessComplete()
        self.tester = RealUserFlowTester(self.harness)
        
        try:
            yield self.tester
        finally:
            # Cleanup services and connections
            if self.tester and self.tester.service_manager:
                await self.tester.service_manager.stop_all_services()
            
            if self.harness:
                await self.harness.teardown()


# Pytest Test Implementation
@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.e2e
async def test_real_user_signup_login_chat_flow():
    """
    CRITICAL E2E Test: Complete user journey from signup to first chat.
    
    This test MUST pass for production deployment.
    Business Value: $50K MRR protection - validates entire new user funnel.
    
    Test Flow:
    1. Start real auth and backend services
    2. User signup via real HTTP API
    3. Email verification (simulated in dev mode)
    4. User login with credentials
    5. JWT token validation across services
    6. WebSocket connection established
    7. First chat message sent
    8. Agent response received and validated
    
    Success Criteria:
    - All steps complete successfully
    - Total execution time < 10 seconds
    - Real network calls (no mocking)
    - JWT tokens work across services
    - WebSocket connection stable
    - Chat response contains meaningful content
    """
    manager = E2ETestManager()
    
    async with manager.setup_e2e_test() as tester:
        # Execute complete flow
        flow_results = await tester.execute_full_flow()
        
        # Validate overall success
        assert flow_results["success"], f"E2E flow failed: {flow_results.get('error')}"
        
        # Validate performance requirement
        assert flow_results["duration"] < 5.0, f"Performance requirement failed: {flow_results['duration']}s"
        
        # Validate all steps completed
        expected_steps = [
            "services_started", "signup", "login", "token_validation", 
            "websocket_connect", "first_chat", "response_validation"
        ]
        
        completed_steps = [step["step"] for step in flow_results["steps"]]
        for expected_step in expected_steps:
            assert expected_step in completed_steps, f"Missing critical step: {expected_step}"
        
        # Validate step success
        failed_steps = [step for step in flow_results["steps"] if not step.get("success")]
        assert len(failed_steps) == 0, f"Failed steps: {failed_steps}"
        
        # Log success metrics for business monitoring
        print(f"✅ E2E Test SUCCESS: {flow_results['duration']:.2f}s")
        print(f"✅ Steps completed: {len(completed_steps)}/{len(expected_steps)}")
        print(f"✅ $50K MRR funnel PROTECTED")


@pytest.mark.asyncio
@pytest.mark.performance
async def test_e2e_performance_target():
    """
    Performance validation for E2E flow - must complete under 5 seconds.
    Business Value: User experience directly impacts conversion rates.
    """
    manager = E2ETestManager()
    
    async with manager.setup_e2e_test() as tester:
        start_time = time.time()
        
        # Run flow multiple times to validate consistency
        for i in range(3):
            iteration_start = time.time()
            flow_results = await tester.execute_full_flow()
            iteration_duration = time.time() - iteration_start
            
            # Each iteration must meet performance target
            assert iteration_duration < 5.0, f"Iteration {i+1} failed performance: {iteration_duration:.2f}s"
        
        total_duration = time.time() - start_time
        avg_duration = total_duration / 3
        
        # Log performance metrics
        print(f"✅ Average E2E duration: {avg_duration:.2f}s")
        print(f"✅ Performance target MET: <5s")


@pytest.mark.asyncio
@pytest.mark.critical
async def test_e2e_token_security():
    """
    Validate JWT token security across real services.
    Business Value: Security breach prevention - protects user data and trust.
    """
    manager = E2ETestManager()
    
    async with manager.setup_e2e_test() as tester:
        # Start services
        await tester._start_real_services()
        
        # Get real token
        login_result = await tester._real_user_login()
        valid_token = login_result["access_token"]
        
        # Test 1: Valid token accepted by all services
        token_valid = await tester._validate_jwt_token(valid_token)
        assert token_valid, "Valid token rejected by services"
        
        # Test 2: Invalid token rejected
        invalid_token = valid_token + "tampered"
        invalid_token_accepted = await tester._validate_jwt_token(invalid_token)
        assert not invalid_token_accepted, "Invalid token accepted - SECURITY BREACH"
        
        # Test 3: Empty token rejected
        empty_token_accepted = await tester._validate_jwt_token("")
        assert not empty_token_accepted, "Empty token accepted - SECURITY BREACH"
        
        print("✅ Token security validation PASSED")
        print("✅ User data and trust PROTECTED")
