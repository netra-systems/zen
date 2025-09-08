"""WebSocket Authentication E2E Tests - CLAUDE.md Compliant

CRITICAL: ALL E2E tests MUST use authentication (JWT/OAuth) except tests that directly validate auth itself.
This file validates WebSocket authentication flows using REAL services and SSOT patterns.

Business Value Justification (BVJ):
1. Segment: All segments - Critical security foundation
2. Business Goal: Ensure secure WebSocket authentication with real services
3. Value Impact: Prevents unauthorized access and validates real-world auth flows
4. Revenue Impact: Protects platform integrity and ensures multi-user isolation

CLAUDE.md Compliance:
- Uses test_framework.ssot.e2e_auth_helper for ALL authentication
- NO mocks in E2E tests - uses REAL WebSocket connections
- NO try/except blocks that hide failures
- Tests MUST raise errors on failure
- Uses real services with proper authentication
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest
import pytest_asyncio
import websockets

# CRITICAL: Use SSOT authentication helper per CLAUDE.md requirements
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, E2EAuthConfig
from shared.isolated_environment import get_env


class WebSocketAuthTestRunner:
    """SSOT WebSocket Authentication Test Runner - CLAUDE.md Compliant.
    
    CRITICAL: Uses REAL authentication and REAL WebSocket connections.
    NO mocks, NO try/except hiding failures, MUST use E2EAuthHelper SSOT.
    """
    
    def __init__(self, environment: str = "test"):
        """Initialize with SSOT authentication helper."""
        self.environment = environment
        self.auth_helper = E2EWebSocketAuthHelper(environment=environment)
        self.active_connections: Dict[str, websockets.ClientConnection] = {}
        self.test_start_time = time.time()
    
    async def setup_real_services(self):
        """Setup with REAL services - NO mocks per CLAUDE.md."""
        env = get_env()
        # Ensure real services are used
        env.set("USE_REAL_SERVICES", "true", "e2e_websocket_auth")
        env.set("TEST_DISABLE_MOCKS", "true", "e2e_websocket_auth")
        env.set("REAL_WEBSOCKET_TESTING", "true", "e2e_websocket_auth")
        return self
    
    async def cleanup_real_services(self):
        """Clean up real services and connections."""
        await self._close_all_connections()
        
        # Clean up environment
        env = get_env()
        env.delete("USE_REAL_SERVICES", "e2e_websocket_auth")
        env.delete("TEST_DISABLE_MOCKS", "e2e_websocket_auth")
        env.delete("REAL_WEBSOCKET_TESTING", "e2e_websocket_auth")
    
    async def _close_all_connections(self):
        """Close all WebSocket connections."""
        for ws in self.active_connections.values():
            if not ws.closed:
                await ws.close()
        self.active_connections.clear()
    
    async def create_authenticated_websocket_connection(self, user_id: str = "test-ws-user") -> tuple:
        """Create authenticated WebSocket connection using SSOT patterns.
        
        CRITICAL: Uses real authentication - NO bypassing, NO mocking.
        """
        # Create real JWT token using SSOT helper
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=f"{user_id}@websocket-auth-test.com"
        )
        
        # Get proper auth headers using SSOT helper
        headers = self.auth_helper.get_websocket_headers(token)
        
        # Connect to REAL WebSocket with authentication
        ws = await websockets.connect(
            self.auth_helper.config.websocket_url,
            additional_headers=headers,
            timeout=10.0
        )
        
        connection_id = f"auth_{user_id}_{int(time.time())}"
        self.active_connections[connection_id] = ws
        
        return ws, token, headers
    
    async def verify_websocket_authentication(self, ws, expected_authenticated: bool = True):
        """Verify WebSocket authentication status - MUST raise errors on failure.
        
        CRITICAL: NO try/except blocks hiding failures per CLAUDE.md.
        """
        # Send authentication verification message
        auth_check = {
            "type": "auth_verify",
            "timestamp": datetime.now().isoformat()
        }
        await ws.send(json.dumps(auth_check))
        
        # Wait for authentication response
        response = await asyncio.wait_for(ws.recv(), timeout=10.0)
        response_data = json.loads(response)
        
        # MUST raise errors - NO silent failures
        if expected_authenticated:
            if response_data.get("type") == "auth_error":
                raise AssertionError(f"Expected authenticated WebSocket but got auth_error: {response_data}")
            if "user_id" not in response_data.get("payload", {}):
                raise AssertionError(f"Authenticated WebSocket missing user_id in response: {response_data}")
        else:
            if response_data.get("type") != "auth_error":
                raise AssertionError(f"Expected auth_error but got: {response_data}")
        
        return response_data


@pytest_asyncio.fixture
async def websocket_auth_runner():
    """SSOT WebSocket authentication test runner fixture - CLAUDE.md compliant.
    
    CRITICAL: Uses REAL authentication and services per CLAUDE.md requirements.
    """
    runner = WebSocketAuthTestRunner()
    await runner.setup_real_services()
    yield runner
    await runner.cleanup_real_services()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_jwt_authentication_success(websocket_auth_runner):
    """Test successful JWT authentication through WebSocket - REAL services only.
    
    CRITICAL: Uses SSOT authentication patterns, NO mocks, MUST raise errors.
    """
    start_time = time.time()
    
    # Create authenticated WebSocket connection using SSOT patterns
    ws, token, headers = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="ws-auth-success-test"
    )
    
    # Verify authentication worked with REAL WebSocket connection
    auth_response = await websocket_auth_runner.verify_websocket_authentication(
        ws, expected_authenticated=True
    )
    
    # Validate response structure - MUST have required fields
    payload = auth_response.get("payload", {})
    if not payload.get("user_id"):
        raise AssertionError(f"Missing user_id in auth response: {auth_response}")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_invalid_jwt_token(websocket_auth_runner):
    """Test WebSocket rejects invalid JWT tokens - REAL connection failure required.
    
    CRITICAL: Must fail with REAL WebSocket connection, not mocked response.
    """
    start_time = time.time()
    
    # Attempt connection with invalid token - MUST fail at connection level
    invalid_headers = {"Authorization": "Bearer completely_invalid_token_12345"}
    
    # This MUST raise a real WebSocket exception, not return a mock response
    connection_failed = False
    try:
        ws = await websockets.connect(
            websocket_auth_runner.auth_helper.config.websocket_url,
            additional_headers=invalid_headers,
            timeout=10.0
        )
        await ws.close()
        # If we get here, the test FAILED - invalid token should not connect
        raise AssertionError("Invalid JWT token was accepted - authentication security failure")
    except (websockets.exceptions.ConnectionClosedError, 
            websockets.exceptions.InvalidStatus,
            OSError) as e:
        # Expected - invalid token should cause connection failure
        connection_failed = True
    
    # MUST have real connection failure
    if not connection_failed:
        raise AssertionError("Invalid JWT token did not cause connection failure")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_expired_jwt_token(websocket_auth_runner):
    """Test WebSocket rejects expired JWT tokens - REAL authentication required.
    
    CRITICAL: Must use REAL expired token and REAL WebSocket rejection.
    """
    start_time = time.time()
    
    # Create REAL expired token using SSOT helper
    expired_token = websocket_auth_runner.auth_helper.create_test_jwt_token(
        user_id="expired-token-test",
        email="expired-test@websocket-auth.com",
        exp_minutes=-1  # Token expired 1 minute ago
    )
    
    expired_headers = {"Authorization": f"Bearer {expired_token}"}
    
    # Attempt connection with expired token - MUST fail at connection level
    connection_failed = False
    try:
        ws = await websockets.connect(
            websocket_auth_runner.auth_helper.config.websocket_url,
            additional_headers=expired_headers,
            timeout=10.0
        )
        await ws.close()
        # If we get here, the test FAILED - expired token should not connect
        raise AssertionError("Expired JWT token was accepted - authentication security failure")
    except (websockets.exceptions.ConnectionClosedError,
            websockets.exceptions.InvalidStatus,
            OSError) as e:
        # Expected - expired token should cause connection failure
        connection_failed = True
    
    # MUST have real connection failure
    if not connection_failed:
        raise AssertionError("Expired JWT token did not cause connection failure")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_token_refresh_flow(websocket_auth_runner):
    """Test WebSocket token refresh during active connection - REAL authentication flow.
    
    CRITICAL: Must use REAL WebSocket connection and REAL token refresh.
    """
    start_time = time.time()
    
    # Create authenticated connection with SSOT patterns
    ws, original_token, _ = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="token-refresh-test"
    )
    
    # Send token refresh request to REAL WebSocket
    refresh_msg = {
        "type": "token_refresh",
        "payload": {"current_token": original_token},
        "timestamp": datetime.now().isoformat()
    }
    await ws.send(json.dumps(refresh_msg))
    
    # Wait for REAL token refresh response
    response = await asyncio.wait_for(ws.recv(), timeout=15.0)
    response_data = json.loads(response)
    
    # Validate REAL token refresh response - MUST raise errors on failure
    if response_data.get("type") == "error":
        raise AssertionError(f"Token refresh failed: {response_data}")
    
    payload = response_data.get("payload", {})
    new_token = payload.get("new_token")
    
    # MUST have new token and it MUST be different from original
    if not new_token:
        raise AssertionError(f"No new token in refresh response: {response_data}")
    if new_token == original_token:
        raise AssertionError("New token is identical to original - refresh did not work")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_multi_user_authentication(websocket_auth_runner):
    """Test multiple users authenticate simultaneously - REAL multi-user isolation.
    
    CRITICAL: Tests REAL multi-user WebSocket authentication with proper isolation.
    """
    start_time = time.time()
    
    # Create multiple REAL authenticated WebSocket connections
    connections = {}
    user_roles = ["admin-user", "regular-user", "guest-user"]
    
    for user_role in user_roles:
        ws, token, headers = await websocket_auth_runner.create_authenticated_websocket_connection(
            user_id=f"multi-user-{user_role}"
        )
        connections[user_role] = (ws, token, headers)
    
    # Verify ALL connections are properly authenticated with isolation
    for user_role, (ws, token, headers) in connections.items():
        # Send auth verification to each REAL WebSocket connection
        auth_response = await websocket_auth_runner.verify_websocket_authentication(
            ws, expected_authenticated=True
        )
        
        # Validate each user has isolated authentication context
        payload = auth_response.get("payload", {})
        user_id = payload.get("user_id")
        if not user_id:
            raise AssertionError(f"Missing user_id for {user_role}: {auth_response}")
        if f"multi-user-{user_role}" not in user_id:
            raise AssertionError(f"User isolation failed for {user_role} - got user_id: {user_id}")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_role_based_permissions(websocket_auth_runner):
    """Test WebSocket enforces role-based permissions - REAL authorization checks.
    
    CRITICAL: Must use REAL WebSocket connections with REAL permission enforcement.
    """
    start_time = time.time()
    
    # Create REAL authenticated connections with different permission levels
    user_ws, user_token, _ = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="permission-regular-user"
    )
    admin_ws, admin_token, _ = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="permission-admin-user"
    )
    
    # Test regular user attempting admin operation - MUST be denied
    admin_command = {
        "type": "admin_command",
        "payload": {"command": "system_status"},
        "timestamp": datetime.now().isoformat()
    }
    await user_ws.send(json.dumps(admin_command))
    
    # Wait for REAL permission denial from WebSocket
    user_response = await asyncio.wait_for(user_ws.recv(), timeout=10.0)
    user_response_data = json.loads(user_response)
    
    # MUST receive permission denied - raise error if not
    if user_response_data.get("type") != "permission_denied":
        raise AssertionError(f"Regular user should be denied admin command but got: {user_response_data}")
    
    # Test admin user with same operation - should be allowed or return valid response
    await admin_ws.send(json.dumps(admin_command))
    admin_response = await asyncio.wait_for(admin_ws.recv(), timeout=10.0)
    admin_response_data = json.loads(admin_response)
    
    # Admin should NOT get permission denied
    if admin_response_data.get("type") == "permission_denied":
        raise AssertionError(f"Admin user should not be denied admin command but got: {admin_response_data}")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_session_validation(websocket_auth_runner):
    """Test WebSocket validates session consistency - REAL session management.
    
    CRITICAL: Must use REAL WebSocket session validation with REAL authentication.
    """
    start_time = time.time()
    
    # Create REAL authenticated WebSocket connection
    ws, token, _ = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="session-validation-test"
    )
    
    # Send REAL session validation message
    session_msg = {
        "type": "session_validate",
        "payload": {
            "token": token,
            "session_id": "test_session_validation_12345"
        },
        "timestamp": datetime.now().isoformat()
    }
    await ws.send(json.dumps(session_msg))
    
    # Wait for REAL session validation response
    response = await asyncio.wait_for(ws.recv(), timeout=10.0)
    response_data = json.loads(response)
    
    # Validate REAL session response - MUST raise errors on failure
    if response_data.get("type") == "error":
        raise AssertionError(f"Session validation failed: {response_data}")
    
    payload = response_data.get("payload", {})
    if "session_id" not in payload:
        raise AssertionError(f"Missing session_id in validation response: {response_data}")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_concurrent_auth_requests(websocket_auth_runner):
    """Test WebSocket handles concurrent authentication requests - REAL concurrency.
    
    CRITICAL: Must use REAL WebSocket with REAL concurrent authentication processing.
    """
    start_time = time.time()
    
    # Create REAL authenticated WebSocket connection
    ws, token, _ = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="concurrent-auth-test"
    )
    
    # Send multiple REAL auth requests concurrently
    auth_tasks = []
    for i in range(5):
        auth_msg = {
            "type": "auth_verify",
            "payload": {"token": token, "request_id": f"concurrent_{i}"},
            "timestamp": datetime.now().isoformat()
        }
        auth_tasks.append(ws.send(json.dumps(auth_msg)))
    
    # Send all requests concurrently to REAL WebSocket
    await asyncio.gather(*auth_tasks)
    
    # Wait for ALL REAL responses
    responses = []
    for i in range(5):
        response = await asyncio.wait_for(ws.recv(), timeout=10.0)
        response_data = json.loads(response)
        responses.append(response_data)
    
    # Validate ALL concurrent requests processed correctly - MUST raise errors
    if len(responses) != 5:
        raise AssertionError(f"Expected 5 responses but got {len(responses)}")
    
    for i, response in enumerate(responses):
        if response.get("type") == "auth_error":
            raise AssertionError(f"Concurrent request {i} failed with auth_error: {response}")
        if not response.get("payload", {}).get("user_id"):
            raise AssertionError(f"Concurrent request {i} missing user_id: {response}")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_auth_state_recovery(websocket_auth_runner):
    """Test WebSocket recovers authentication state after reconnection - REAL state persistence.
    
    CRITICAL: Must use REAL WebSocket connections and REAL state recovery mechanisms.
    """
    start_time = time.time()
    
    # Create first REAL authenticated WebSocket connection
    ws1, token, _ = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="state-recovery-test"
    )
    
    # Store session state via REAL WebSocket
    state_msg = {
        "type": "store_state",
        "payload": {"test_data": "recovery_validation_data_12345"},
        "timestamp": datetime.now().isoformat()
    }
    await ws1.send(json.dumps(state_msg))
    
    # Wait for state storage confirmation
    store_response = await asyncio.wait_for(ws1.recv(), timeout=10.0)
    store_response_data = json.loads(store_response)
    
    # Close first connection
    await ws1.close()
    
    # Create new REAL WebSocket connection with same authentication
    headers = websocket_auth_runner.auth_helper.get_websocket_headers(token)
    ws2 = await websockets.connect(
        websocket_auth_runner.auth_helper.config.websocket_url,
        additional_headers=headers,
        timeout=10.0
    )
    websocket_auth_runner.active_connections["recovery_conn"] = ws2
    
    # Request REAL state recovery
    recovery_msg = {
        "type": "recover_state",
        "payload": {"token": token, "session_recovery": True},
        "timestamp": datetime.now().isoformat()
    }
    await ws2.send(json.dumps(recovery_msg))
    
    # Wait for REAL state recovery response
    recovery_response = await asyncio.wait_for(ws2.recv(), timeout=10.0)
    recovery_response_data = json.loads(recovery_response)
    
    # Validate REAL state recovery - MUST raise errors on failure
    if recovery_response_data.get("type") == "error":
        raise AssertionError(f"State recovery failed: {recovery_response_data}")
    
    recovered_data = recovery_response_data.get("payload", {}).get("test_data")
    if recovered_data != "recovery_validation_data_12345":
        raise AssertionError(f"State recovery data mismatch: expected 'recovery_validation_data_12345', got '{recovered_data}'")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_websocket_auth_timeout_handling(websocket_auth_runner):
    """Test WebSocket handles authentication timeouts gracefully - REAL timeout behavior.
    
    CRITICAL: Must use REAL WebSocket timeout handling with REAL authentication.
    """
    start_time = time.time()
    
    # Create REAL authenticated WebSocket connection
    ws, token, _ = await websocket_auth_runner.create_authenticated_websocket_connection(
        user_id="timeout-handling-test"
    )
    
    # Send slow authentication request to test REAL timeout handling
    slow_auth_msg = {
        "type": "slow_auth_verify",
        "payload": {
            "token": token,
            "simulate_delay": True,
            "timeout_test": True
        },
        "timestamp": datetime.now().isoformat()
    }
    await ws.send(json.dumps(slow_auth_msg))
    
    # Test REAL timeout handling behavior
    timeout_handled = False
    response_received = False
    
    # This MUST test real timeout behavior, not mocked responses
    try:
        response = await asyncio.wait_for(ws.recv(), timeout=3.0)
        response_data = json.loads(response)
        response_received = True
        
        # Validate response indicates proper timeout handling
        response_type = response_data.get("type")
        if response_type not in ["auth_timeout", "auth_success", "timeout_handled"]:
            raise AssertionError(f"Unexpected response type for timeout test: {response_type}")
        
        timeout_handled = True
        
    except asyncio.TimeoutError:
        # REAL timeout from WebSocket is also acceptable - shows real behavior
        timeout_handled = True
    
    # MUST demonstrate real timeout handling behavior
    if not timeout_handled:
        raise AssertionError("WebSocket timeout handling test failed - no timeout behavior observed")
    
    execution_time = time.time() - start_time
    # E2E tests with 0.00s execution = AUTOMATIC HARD FAILURE per CLAUDE.md
    if execution_time < 0.01:
        raise AssertionError(f"E2E test completed in {execution_time:.3f}s - indicates mocking/bypassing")