"""WebSocket Connection Lifecycle Compliance Tests.

Tests real WebSocket connection lifecycle per SPEC compliance requirements:
- JWT authentication integration (SPEC/websockets.xml authorization)
- Database session handling (SPEC/websockets.xml critical implementation note)
- Real functionality testing (SPEC/no_test_stubs.xml)
- Type safety compliance (SPEC/type_safety.xml)

Business Value: Ensures reliable WebSocket connection lifecycle preventing
user frustration and churn from connection failures.

BVJ: Enterprise/Mid - Platform Stability - Real connection testing prevents
production failures and ensures auth/DB integration works correctly.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest

from tests.clients.backend_client import BackendTestClient
from tests.clients.websocket_client import WebSocketTestClient
from tests.e2e.config import UnifiedTestConfig


@pytest.mark.e2e
class TestWebSocketConnectionLifecycleCompliant:
    """Compliance-focused WebSocket connection lifecycle tests."""
    
    @pytest.fixture
    async def backend_client(self):
        """Get authenticated backend client for real testing."""
        client = BackendTestClient()
        await client.authenticate()
        try:
            yield client
        finally:
            await client.close()
    
    @pytest.fixture
    @pytest.mark.e2e
    async def test_user_credentials(self, backend_client) -> Dict[str, str]:
        """Get real test user credentials for lifecycle testing."""
        # Create or get test user for lifecycle testing
        test_user_data = {
            "email": f"lifecycle_test_{int(datetime.now().timestamp())}@example.com",
            "password": "TestPassword123!",
            "name": "WebSocket Lifecycle Test User"
        }
        
        try:
            # Try to create test user
            response = await backend_client.post("/auth/register", json=test_user_data)
            if response.status_code in [200, 201]:
                return test_user_data
        except:
            pass
        
        # Fallback to existing test credentials
        return {
            "email": "test@example.com",
            "password": "testpassword",
            "name": "Test User"
        }
    
    @pytest.mark.e2e
    async def test_jwt_authentication_connection_establishment(self, test_user_credentials):
        """Test WebSocket connection with real JWT authentication."""
        # Get JWT token through real auth flow
        auth_client = BackendTestClient()
        await auth_client.authenticate(
            test_user_credentials["email"], 
            test_user_credentials["password"]
        )
        
        jwt_token = await auth_client.get_jwt_token()
        assert jwt_token, "Failed to obtain JWT token for WebSocket auth test"
        
        # Test WebSocket connection with JWT
        ws_client = WebSocketTestClient()
        
        try:
            # Real connection attempt with JWT
            await ws_client.connect(jwt_token)
            
            # Verify connection is authenticated
            assert ws_client.is_connected(), "WebSocket connection failed with valid JWT"
            
            # Test connection remains authenticated
            await ws_client.send_message({
                "type": "auth_verification",
                "payload": {"test": "jwt_connection_test"}
            })
            
            # Should receive response without auth errors
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        ws_client.receive_message(),
                        timeout=1.0
                    )
                    
                    if isinstance(message, str):
                        message = json.loads(message)
                    
                    if isinstance(message, dict):
                        # Should not receive auth error
                        assert "auth_error" not in message.get("type", ""), (
                            f"Received auth error with valid JWT: {message}"
                        )
                        break
                        
                except asyncio.TimeoutError:
                    continue
            
        finally:
            await ws_client.disconnect()
            await auth_client.close()
    
    @pytest.mark.e2e
    async def test_database_session_handling_compliance(self, backend_client):
        """Test database session handling per SPEC/websockets.xml critical note."""
        # Get token for WebSocket connection
        jwt_token = await backend_client.get_jwt_token()
        ws_client = WebSocketTestClient()
        
        try:
            await ws_client.connect(jwt_token)
            
            # Send message that requires database operations
            await ws_client.send_message({
                "type": "user_message",
                "payload": {"content": "Database session test - fetch user data"}
            })
            
            # Monitor for database session errors
            database_errors = []
            successful_db_operations = []
            timeout = 10.0
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        ws_client.receive_message(),
                        timeout=2.0
                    )
                    
                    if isinstance(message, str):
                        message = json.loads(message)
                    
                    if isinstance(message, dict):
                        message_str = str(message).lower()
                        
                        # Check for database session errors per spec
                        db_error_indicators = [
                            "_asyncgeneratorcontextmanager",
                            "no attribute 'execute'", 
                            "depends() injection",
                            "database session error"
                        ]
                        
                        if any(error_indicator in message_str for error_indicator in db_error_indicators):
                            database_errors.append(message)
                        
                        # Check for successful database operations
                        if any(success_indicator in message_str for success_indicator in ["user", "session", "data"]):
                            successful_db_operations.append(message)
                            
                except asyncio.TimeoutError:
                    continue
            
            # Validate database session compliance
            assert len(database_errors) == 0, (
                f"Database session handling violations detected: {database_errors}. "
                f"WebSocket endpoints must use 'async with get_async_db() as db_session' pattern."
            )
            
            # Should have successful database operations
            assert len(successful_db_operations) > 0, (
                "No successful database operations detected. WebSocket should handle DB sessions correctly."
            )
            
        finally:
            await ws_client.disconnect()
    
    @pytest.mark.e2e
    async def test_connection_lifecycle_state_transitions(self, backend_client):
        """Test real connection lifecycle state transitions."""
        jwt_token = await backend_client.get_jwt_token()
        ws_client = WebSocketTestClient()
        
        # Track connection state transitions
        state_transitions = []
        
        try:
            # Initial state
            assert not ws_client.is_connected(), "WebSocket should start disconnected"
            state_transitions.append("initial_disconnected")
            
            # Connection establishment
            await ws_client.connect(jwt_token)
            assert ws_client.is_connected(), "WebSocket should be connected after connect()"
            state_transitions.append("connected")
            
            # Active communication
            await ws_client.send_message({
                "type": "connection_test",
                "payload": {"lifecycle_test": True}
            })
            
            # Verify active communication
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()
            received_response = False
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        ws_client.receive_message(),
                        timeout=1.0
                    )
                    received_response = True
                    break
                except asyncio.TimeoutError:
                    continue
            
            assert received_response, "WebSocket should support active bidirectional communication"
            state_transitions.append("active_communication")
            
            # Graceful disconnection
            await ws_client.disconnect()
            assert not ws_client.is_connected(), "WebSocket should be disconnected after disconnect()"
            state_transitions.append("graceful_disconnect")
            
            # Validate complete lifecycle
            expected_transitions = ["initial_disconnected", "connected", "active_communication", "graceful_disconnect"]
            assert state_transitions == expected_transitions, (
                f"Unexpected lifecycle transitions: {state_transitions}"
            )
            
        except Exception as e:
            # Ensure cleanup even if test fails
            if ws_client.is_connected():
                await ws_client.disconnect()
            raise e
    
    @pytest.mark.e2e
    async def test_concurrent_connection_handling(self, backend_client):
        """Test real concurrent WebSocket connections."""
        jwt_token = await backend_client.get_jwt_token()
        
        # Create multiple real WebSocket connections
        connections = []
        connection_count = 3
        
        try:
            # Establish concurrent connections
            for i in range(connection_count):
                ws_client = WebSocketTestClient()
                await ws_client.connect(jwt_token)
                connections.append(ws_client)
            
            # Verify all connections are active
            for i, ws_client in enumerate(connections):
                assert ws_client.is_connected(), f"Connection {i} failed to establish"
            
            # Test concurrent message handling
            for i, ws_client in enumerate(connections):
                await ws_client.send_message({
                    "type": "concurrent_test",
                    "payload": {"connection_id": i, "test": "concurrent_handling"}
                })
            
            # Verify each connection receives responses
            response_counts = []
            timeout = 8.0
            
            for i, ws_client in enumerate(connections):
                responses = 0
                start_time = asyncio.get_event_loop().time()
                
                while (asyncio.get_event_loop().time() - start_time) < timeout / connection_count:
                    try:
                        message = await asyncio.wait_for(
                            ws_client.receive_message(),
                            timeout=1.0
                        )
                        if message:
                            responses += 1
                            break
                    except asyncio.TimeoutError:
                        break
                
                response_counts.append(responses)
            
            # All connections should receive responses
            successful_connections = sum(1 for count in response_counts if count > 0)
            assert successful_connections == connection_count, (
                f"Only {successful_connections}/{connection_count} connections received responses"
            )
            
        finally:
            # Clean up all connections
            for ws_client in connections:
                try:
                    if ws_client.is_connected():
                        await ws_client.disconnect()
                except:
                    pass  # Best effort cleanup
    
    @pytest.mark.e2e
    async def test_connection_recovery_after_network_interruption(self, backend_client):
        """Test connection recovery mechanisms."""
        jwt_token = await backend_client.get_jwt_token()
        ws_client = WebSocketTestClient()
        
        try:
            # Establish initial connection
            await ws_client.connect(jwt_token)
            assert ws_client.is_connected(), "Initial connection failed"
            
            # Simulate network interruption by forcing disconnect
            await ws_client.disconnect()
            assert not ws_client.is_connected(), "Disconnect simulation failed"
            
            # Test reconnection capability
            await asyncio.sleep(1.0)  # Brief pause to simulate network recovery
            
            await ws_client.connect(jwt_token)
            assert ws_client.is_connected(), "Reconnection failed after network interruption"
            
            # Verify functionality after reconnection
            await ws_client.send_message({
                "type": "recovery_test",
                "payload": {"test": "post_interruption_functionality"}
            })
            
            # Should receive response after reconnection
            timeout = 5.0
            start_time = asyncio.get_event_loop().time()
            received_response = False
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        ws_client.receive_message(),
                        timeout=1.0
                    )
                    received_response = True
                    break
                except asyncio.TimeoutError:
                    continue
            
            assert received_response, "WebSocket functionality not restored after reconnection"
            
        finally:
            if ws_client.is_connected():
                await ws_client.disconnect()
    
    @pytest.mark.e2e
    async def test_authentication_expiry_handling(self, test_user_credentials):
        """Test WebSocket handling of JWT token expiry."""
        # This test would require a short-lived token, which may not be available
        # in all test environments, so we'll test the error handling path
        
        # Test with invalid/expired token
        invalid_token = "invalid.jwt.token"
        ws_client = WebSocketTestClient()
        
        try:
            # Should handle invalid token gracefully
            connection_failed = False
            try:
                await ws_client.connect(invalid_token)
            except Exception:
                connection_failed = True
            
            # Either connection should fail gracefully, or we should detect auth errors
            if not connection_failed:
                # If connection succeeded despite invalid token, send message to trigger auth check
                await ws_client.send_message({
                    "type": "auth_required_operation",
                    "payload": {"test": "invalid_token_handling"}
                })
                
                # Should receive auth error
                timeout = 5.0
                start_time = asyncio.get_event_loop().time()
                auth_error_received = False
                
                while (asyncio.get_event_loop().time() - start_time) < timeout:
                    try:
                        message = await asyncio.wait_for(
                            ws_client.receive_message(),
                            timeout=1.0
                        )
                        
                        if isinstance(message, str):
                            message = json.loads(message)
                        
                        if isinstance(message, dict):
                            message_str = str(message).lower()
                            if any(error_indicator in message_str for error_indicator in ["auth", "unauthorized", "token", "invalid"]):
                                auth_error_received = True
                                break
                                
                    except asyncio.TimeoutError:
                        continue
                
                # Should handle auth errors appropriately
                assert auth_error_received or connection_failed, (
                    "Invalid token should either prevent connection or trigger auth error"
                )
            
        finally:
            if ws_client.is_connected():
                await ws_client.disconnect()
    
    @pytest.mark.e2e
    async def test_message_structure_compliance_during_lifecycle(self, backend_client):
        """Test message structure compliance throughout connection lifecycle."""
        jwt_token = await backend_client.get_jwt_token()
        ws_client = WebSocketTestClient()
        
        try:
            await ws_client.connect(jwt_token)
            
            # Send test message
            await ws_client.send_message({
                "type": "structure_compliance_test",
                "payload": {"test": "message_structure_validation"}
            })
            
            # Validate all received messages use {type, payload} structure
            timeout = 8.0
            start_time = asyncio.get_event_loop().time()
            structure_violations = []
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    message = await asyncio.wait_for(
                        ws_client.receive_message(),
                        timeout=1.0
                    )
                    
                    if isinstance(message, str):
                        try:
                            message = json.loads(message)
                        except json.JSONDecodeError:
                            structure_violations.append(f"Invalid JSON: {message}")
                            continue
                    
                    if isinstance(message, dict):
                        # Validate {type, payload} structure
                        if "type" not in message:
                            structure_violations.append(f"Missing 'type' field: {message}")
                        elif not isinstance(message["type"], str):
                            structure_violations.append(f"'type' field not string: {message}")
                        
                        if "payload" not in message:
                            structure_violations.append(f"Missing 'payload' field: {message}")
                        elif not isinstance(message["payload"], dict):
                            structure_violations.append(f"'payload' field not dict: {message}")
                        
                        # Check for forbidden legacy fields
                        if "event" in message or "data" in message:
                            structure_violations.append(f"Legacy structure detected: {message}")
                            
                except asyncio.TimeoutError:
                    continue
            
            # Report structure violations
            assert len(structure_violations) == 0, (
                f"Message structure violations detected:\n" +
                "\n".join(structure_violations)
            )
            
        finally:
            await ws_client.disconnect()
    
    # Helper methods (each  <= 8 lines)
    def _validate_connection_state(self, ws_client: WebSocketTestClient, expected_state: bool) -> bool:
        """Validate WebSocket connection state matches expectation."""
        actual_state = ws_client.is_connected()
        return actual_state == expected_state
    
    def _extract_auth_info_from_message(self, message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract authentication-related information from WebSocket message."""
        payload = message.get("payload", {})
        auth_fields = {k: v for k, v in payload.items() if "auth" in k.lower() or "user" in k.lower()}
        return auth_fields if auth_fields else None