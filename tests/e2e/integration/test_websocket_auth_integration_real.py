"""
WebSocket Authentication Integration Test - REAL SERVICES ONLY

Critical E2E test for WebSocket authentication integration using real services.
Validates complete auth flow: registration  ->  login  ->  WebSocket auth  ->  agent interaction.

Business Value Justification (BVJ):
1. Segment: ALL user tiers (critical authentication path)
2. Business Goal: Ensure reliable WebSocket authentication for chat functionality
3. Value Impact: Protects $500K+ ARR core chat feature from auth failures
4. Revenue Impact: Each auth failure blocks user access to paid features

ARCHITECTURAL COMPLIANCE:
- Uses IsolatedEnvironment for test isolation
- REAL services only (Auth, Backend, WebSocket) - NO MOCKS per CLAUDE.md
- Docker-compose for service dependencies 
- Real JWT validation and WebSocket handshake
- Performance validation with real latency
- Complete user journey testing

TECHNICAL DETAILS:
- Real user registration and login flow
- Real JWT token generation and validation
- Real WebSocket connection with auth headers
- Real agent request/response flow validation
- Real session persistence testing
"""

import asyncio
import json
import time
import uuid
from typing import Dict, Any, Optional, List
import pytest
import pytest_asyncio

# Import test framework - NO MOCKS
from test_framework.environment_isolation import isolated_test_env, get_test_env_manager
from tests.clients.websocket_client import WebSocketTestClient
from tests.clients.backend_client import BackendTestClient
from tests.clients.auth_client import AuthTestClient

# Import for validation
from netra_backend.app.schemas.user_plan import PlanTier


class RealWebSocketAuthTestCore:
    """Core infrastructure for real WebSocket authentication testing."""
    
    def __init__(self):
        self.auth_client = None
        self.backend_client = None
        self.test_users = {}
        self.active_connections = []
        
    async def setup_real_auth_infrastructure(self, isolated_env) -> Dict[str, Any]:
        """Setup real authentication test infrastructure."""
        
        # Ensure real services are configured
        assert isolated_env.get("USE_REAL_SERVICES") == "true", "Must use real services for auth testing"
        assert isolated_env.get("TESTING") == "1", "Must be in testing mode"
        
        # Get real service endpoints
        auth_host = isolated_env.get("AUTH_SERVICE_HOST", "localhost")
        auth_port = isolated_env.get("AUTH_SERVICE_PORT", "8001")
        backend_host = isolated_env.get("BACKEND_HOST", "localhost")
        backend_port = isolated_env.get("BACKEND_PORT", "8000")
        
        # Initialize real service clients
        self.auth_client = AuthTestClient(f"http://{auth_host}:{auth_port}")
        self.backend_client = BackendTestClient(f"http://{backend_host}:{backend_port}")
        
        # Validate real service connectivity
        auth_health = await self._validate_auth_service_connectivity()
        backend_health = await self._validate_backend_service_connectivity()
        
        return {
            "auth_client": self.auth_client,
            "backend_client": self.backend_client,
            "auth_healthy": auth_health,
            "backend_healthy": backend_health,
            "env": isolated_env
        }
    
    async def _validate_auth_service_connectivity(self) -> bool:
        """Validate real auth service is accessible."""
        try:
            health_response = await self.auth_client.health_check()
            return health_response.get("status") == "healthy"
        except Exception:
            # Service may not be running - that's also a valid test scenario
            return False
            
    async def _validate_backend_service_connectivity(self) -> bool:
        """Validate real backend service is accessible."""
        try:
            health_response = await self.backend_client.health_check()
            return health_response.get("status") == "healthy"
        except Exception:
            # Service may not be running - that's also a valid test scenario
            return False
    
    async def create_real_authenticated_user(self, plan_tier: PlanTier = PlanTier.PRO) -> Dict[str, Any]:
        """Create and authenticate a real user through the complete flow."""
        # Generate unique test user credentials
        test_email = f"wsauth-test-{uuid.uuid4()}@netra-test.com"
        test_password = "WebSocketAuthTest123!"
        test_name = f"WebSocket Auth Test User {plan_tier.value}"
        
        # Step 1: Real user registration
        register_response = await self.auth_client.register(
            email=test_email,
            password=test_password,
            name=test_name
        )
        
        if not register_response.get("success"):
            raise Exception(f"Real user registration failed: {register_response}")
        
        # Step 2: Real user login to get JWT token
        login_response = await self.auth_client.login(test_email, test_password)
        
        if not login_response.get("access_token"):
            raise Exception(f"Real user login failed: {login_response}")
        
        user_token = login_response["access_token"]
        user_id = login_response.get("user_id")
        
        # Step 3: Validate JWT token is real and valid
        token_validation = await self._validate_real_jwt_token(user_token)
        if not token_validation["valid"]:
            raise Exception(f"Real JWT token validation failed: {token_validation}")
        
        user_data = {
            "user_id": user_id,
            "email": test_email,
            "token": user_token,
            "plan_tier": plan_tier,
            "token_expires_at": token_validation.get("expires_at"),
            "created_at": time.time()
        }
        
        self.test_users[user_id] = user_data
        return user_data
    
    async def _validate_real_jwt_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token using real auth service validation."""
        try:
            # Use real auth service token validation
            validation_response = await self.auth_client.validate_token(token)
            return {
                "valid": validation_response.get("valid", False),
                "user_id": validation_response.get("user_id"),
                "expires_at": validation_response.get("expires_at")
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    async def establish_real_websocket_connection(self, user_data: Dict[str, Any]) -> WebSocketTestClient:
        """Establish real WebSocket connection with authentication."""
        backend_host = self.backend_client.base_url.replace("http://", "").replace("https://", "")
        ws_url = f"ws://{backend_host}/ws"
        
        # Create real WebSocket client
        ws_client = WebSocketTestClient(ws_url)
        
        # Connect with real JWT token authentication
        connection_success = await ws_client.connect(
            token=user_data["token"],
            timeout=10.0
        )
        
        if not connection_success or not ws_client.is_connected:
            raise Exception(f"Real WebSocket connection failed for user {user_data['user_id']}")
        
        self.active_connections.append(ws_client)
        return ws_client
    
    async def test_real_agent_interaction(self, ws_client: WebSocketTestClient, 
                                        test_message: str) -> Dict[str, Any]:
        """Test real agent interaction through WebSocket."""
        # Send real chat message
        await ws_client.send_chat(test_message)
        
        # Collect real agent responses
        responses = []
        agent_started = False
        agent_completed = False
        timeout_start = time.time()
        
        while time.time() - timeout_start < 30.0:  # 30s timeout for real agents
            event = await ws_client.receive(timeout=2.0)
            if event:
                responses.append(event)
                
                # Track agent lifecycle
                if event.get("type") == "agent_started":
                    agent_started = True
                elif event.get("type") in ["agent_completed", "final_report"]:
                    agent_completed = True
                    break
        
        return {
            "responses": responses,
            "agent_started": agent_started,
            "agent_completed": agent_completed,
            "response_count": len(responses),
            "total_time": time.time() - timeout_start
        }
    
    async def teardown_real_connections(self):
        """Clean up all real connections."""
        # Close WebSocket connections
        for ws_client in self.active_connections:
            if ws_client.is_connected:
                await ws_client.disconnect()
        
        # Close service clients
        if self.auth_client:
            await self.auth_client.close()
        if self.backend_client:
            await self.backend_client.close()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.integration
class TestRealWebSocketAuthIntegration:
    """Real WebSocket authentication integration tests."""
    
    @pytest_asyncio.fixture
    async def auth_test_core(self, isolated_test_env):
        """Setup real authentication test infrastructure."""
        core = RealWebSocketAuthTestCore()
        infrastructure = await core.setup_real_auth_infrastructure(isolated_test_env)
        yield core
        await core.teardown_real_connections()
    
    async def test_complete_real_auth_websocket_flow(self, auth_test_core):
        """
        CRITICAL: Test complete authentication to WebSocket flow with real services.
        
        Validates: Registration  ->  Login  ->  JWT  ->  WebSocket Auth  ->  Agent Interaction
        """
        # Step 1: Create real authenticated user
        user_data = await auth_test_core.create_real_authenticated_user(PlanTier.PRO)
        
        assert user_data["token"] is not None, "Real JWT token not generated"
        assert user_data["user_id"] is not None, "Real user ID not assigned"
        
        # Step 2: Establish real WebSocket connection with authentication
        ws_client = await auth_test_core.establish_real_websocket_connection(user_data)
        
        assert ws_client.is_connected, "Real WebSocket connection with auth failed"
        
        # Step 3: Test real agent interaction through authenticated WebSocket
        test_message = "Test authenticated WebSocket agent interaction"
        interaction_result = await auth_test_core.test_real_agent_interaction(ws_client, test_message)
        
        # Validate complete flow
        assert interaction_result["agent_started"], "Real agent did not start after authenticated request"
        assert interaction_result["response_count"] > 0, "No responses received through authenticated WebSocket"
        assert interaction_result["total_time"] < 25.0, f"Real agent response too slow: {interaction_result['total_time']:.2f}s"
        
        # Connection should remain stable
        assert ws_client.is_connected, "WebSocket connection lost during agent interaction"
    
    async def test_real_jwt_token_validation_websocket(self, auth_test_core):
        """
        CRITICAL: Test JWT token validation in WebSocket authentication.
        
        Validates that real JWT tokens are properly validated during WebSocket handshake.
        """
        # Create real user with valid token
        user_data = await auth_test_core.create_real_authenticated_user(PlanTier.ENTERPRISE)
        
        # Test 1: Valid token should allow connection
        ws_client = await auth_test_core.establish_real_websocket_connection(user_data)
        assert ws_client.is_connected, "Valid JWT token rejected by WebSocket auth"
        
        # Test 2: Connection should remain stable with valid token
        await ws_client.send_ping()
        pong_response = await ws_client.receive(timeout=5.0)
        assert pong_response is not None, "WebSocket ping/pong failed with valid auth"
        
        await ws_client.disconnect()
        
        # Test 3: Invalid token should fail connection
        backend_host = auth_test_core.backend_client.base_url.replace("http://", "").replace("https://", "")
        ws_url = f"ws://{backend_host}/ws"
        
        invalid_ws_client = WebSocketTestClient(ws_url)
        invalid_connection = await invalid_ws_client.connect(
            token="invalid.jwt.token",
            timeout=5.0
        )
        
        assert not invalid_connection, "Invalid JWT token should not allow WebSocket connection"
        assert not invalid_ws_client.is_connected, "WebSocket should not be connected with invalid token"
        
        await invalid_ws_client.disconnect()
    
    async def test_real_websocket_session_persistence(self, auth_test_core):
        """
        CRITICAL: Test WebSocket session persistence with real authentication.
        
        Validates that authenticated sessions persist correctly across interactions.
        """
        user_data = await auth_test_core.create_real_authenticated_user(PlanTier.PRO)
        ws_client = await auth_test_core.establish_real_websocket_connection(user_data)
        
        # Test session persistence across multiple interactions
        messages = [
            "First authenticated message for session test",
            "Second authenticated message - session should persist",
            "Third authenticated message - validate continued access"
        ]
        
        interaction_results = []
        
        for i, message in enumerate(messages):
            result = await auth_test_core.test_real_agent_interaction(ws_client, message)
            interaction_results.append(result)
            
            # Validate session persists
            assert ws_client.is_connected, f"Session lost after interaction {i+1}"
            assert result["response_count"] > 0, f"No response to interaction {i+1} - session may be invalid"
            
            # Brief pause between interactions
            await asyncio.sleep(1.0)
        
        # Final validation
        assert len(interaction_results) == len(messages), "Not all interactions completed"
        assert all(r["response_count"] > 0 for r in interaction_results), "Some interactions failed"
        
        # Session should still be active
        assert ws_client.is_connected, "WebSocket session not persistent"
    
    async def test_real_concurrent_authenticated_connections(self, auth_test_core):
        """
        CRITICAL: Test concurrent authenticated WebSocket connections.
        
        Validates that multiple users can maintain authenticated WebSocket sessions simultaneously.
        """
        # Create multiple real authenticated users
        user_count = 3
        users = []
        ws_clients = []
        
        for i in range(user_count):
            user = await auth_test_core.create_real_authenticated_user(PlanTier.PRO)
            ws_client = await auth_test_core.establish_real_websocket_connection(user)
            
            users.append(user)
            ws_clients.append(ws_client)
        
        # All connections should be active
        for i, ws_client in enumerate(ws_clients):
            assert ws_client.is_connected, f"Concurrent connection {i+1} failed"
        
        # Test concurrent interactions
        concurrent_tasks = []
        for i, ws_client in enumerate(ws_clients):
            message = f"Concurrent authenticated message from user {i+1}"
            task = auth_test_core.test_real_agent_interaction(ws_client, message)
            concurrent_tasks.append(task)
        
        # Execute all interactions concurrently
        results = await asyncio.gather(*concurrent_tasks)
        
        # Validate all concurrent interactions succeeded
        for i, result in enumerate(results):
            assert result["response_count"] > 0, f"Concurrent user {i+1} received no responses"
            assert ws_clients[i].is_connected, f"Concurrent connection {i+1} lost during interaction"
        
        # Cleanup concurrent connections
        for ws_client in ws_clients:
            await ws_client.disconnect()
    
    async def test_real_websocket_auth_error_handling(self, auth_test_core):
        """
        CRITICAL: Test WebSocket authentication error handling with real services.
        
        Validates proper error handling for auth failures without breaking the service.
        """
        # Test 1: Create valid user first
        valid_user = await auth_test_core.create_real_authenticated_user(PlanTier.PRO)
        valid_ws_client = await auth_test_core.establish_real_websocket_connection(valid_user)
        
        # Valid connection should work
        assert valid_ws_client.is_connected, "Valid auth connection should work"
        
        # Test 2: Try connection with various invalid auth scenarios
        backend_host = auth_test_core.backend_client.base_url.replace("http://", "").replace("https://", "")
        ws_url = f"ws://{backend_host}/ws"
        
        invalid_scenarios = [
            ("expired.jwt.token", "Expired token test"),
            ("malformed-token", "Malformed token test"),
            ("", "Empty token test"),
            (None, "No token test")
        ]
        
        for token, test_name in invalid_scenarios:
            invalid_client = WebSocketTestClient(ws_url)
            
            # Invalid auth should fail gracefully
            connection_result = await invalid_client.connect(token=token, timeout=5.0)
            assert not connection_result, f"{test_name}: Invalid auth should not succeed"
            assert not invalid_client.is_connected, f"{test_name}: Connection should not be established"
            
            await invalid_client.disconnect()
        
        # Test 3: Valid connection should still work after auth failures
        assert valid_ws_client.is_connected, "Valid connection should remain stable after auth failures"
        
        # Send test message to validate continued functionality
        test_result = await auth_test_core.test_real_agent_interaction(
            valid_ws_client, 
            "Test message after auth error scenarios"
        )
        assert test_result["response_count"] > 0, "Valid connection should work after auth failures"
        
        await valid_ws_client.disconnect()
    
    async def test_real_websocket_auth_performance(self, auth_test_core):
        """
        CRITICAL: Test WebSocket authentication performance with real services.
        
        Validates that auth handshake and first interaction meet performance requirements.
        """
        # Measure auth flow timing
        auth_start = time.time()
        
        # Real user creation and authentication
        user_data = await auth_test_core.create_real_authenticated_user(PlanTier.ENTERPRISE)
        auth_time = time.time() - auth_start
        
        # Measure WebSocket connection timing
        connection_start = time.time()
        ws_client = await auth_test_core.establish_real_websocket_connection(user_data)
        connection_time = time.time() - connection_start
        
        # Measure first interaction timing
        interaction_start = time.time()
        interaction_result = await auth_test_core.test_real_agent_interaction(
            ws_client, 
            "Performance test message for auth validation"
        )
        interaction_time = time.time() - interaction_start
        
        # Performance validation
        assert auth_time < 10.0, f"Auth flow too slow: {auth_time:.2f}s (max 10s)"
        assert connection_time < 5.0, f"WebSocket auth connection too slow: {connection_time:.2f}s (max 5s)"
        assert interaction_time < 30.0, f"First authenticated interaction too slow: {interaction_time:.2f}s (max 30s)"
        assert interaction_result["response_count"] > 0, "Performance test received no responses"
        
        # Validate total end-to-end timing
        total_time = auth_time + connection_time + interaction_time
        assert total_time < 40.0, f"Total auth-to-interaction time too slow: {total_time:.2f}s (max 40s)"
        
        await ws_client.disconnect()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.integration
@pytest.mark.stress
class TestRealWebSocketAuthStress:
    """Stress tests for WebSocket authentication with real services."""
    
    @pytest_asyncio.fixture
    async def auth_test_core(self, isolated_test_env):
        """Setup real authentication test infrastructure."""
        core = RealWebSocketAuthTestCore()
        infrastructure = await core.setup_real_auth_infrastructure(isolated_test_env)
        yield core
        await core.teardown_real_connections()
    
    async def test_real_auth_connection_stability_under_load(self, auth_test_core):
        """
        STRESS TEST: WebSocket auth stability under sustained load.
        
        Validates that auth system remains stable with continuous real connections.
        """
        test_duration = 60.0  # 1 minute stress test
        connection_interval = 5.0  # New connection every 5 seconds
        start_time = time.time()
        
        successful_auths = 0
        failed_auths = 0
        active_connections = []
        
        while time.time() - start_time < test_duration:
            try:
                # Create new authenticated connection
                user_data = await auth_test_core.create_real_authenticated_user(PlanTier.PRO)
                ws_client = await auth_test_core.establish_real_websocket_connection(user_data)
                
                if ws_client.is_connected:
                    successful_auths += 1
                    active_connections.append(ws_client)
                    
                    # Test basic interaction
                    await ws_client.send_chat(f"Stress test message {successful_auths}")
                    response = await ws_client.receive(timeout=5.0)
                    
                    if response:
                        # Connection and interaction successful
                        pass
                else:
                    failed_auths += 1
                    
            except Exception as e:
                failed_auths += 1
                print(f"Stress test auth failure: {e}")
            
            # Wait before next connection
            await asyncio.sleep(connection_interval)
            
            # Cleanup old connections periodically to avoid resource exhaustion
            if len(active_connections) > 5:
                old_connection = active_connections.pop(0)
                await old_connection.disconnect()
        
        # Final validation
        total_time = time.time() - start_time
        total_attempts = successful_auths + failed_auths
        success_rate = successful_auths / total_attempts if total_attempts > 0 else 0
        
        assert total_time >= test_duration * 0.9, f"Stress test ended prematurely: {total_time:.1f}s"
        assert successful_auths >= 5, f"Too few successful auths: {successful_auths}"
        assert success_rate >= 0.7, f"Auth success rate too low: {success_rate:.2f} (expected >= 0.7)"
        
        # Cleanup remaining connections
        for ws_client in active_connections:
            await ws_client.disconnect()


if __name__ == '__main__':
    # Run the real WebSocket auth integration tests
    pytest.main([__file__, '-v', '--tb=short', '-m', 'integration'])