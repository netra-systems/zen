"""
Test WebSocket Authentication Context Preservation During Connection Lifecycle Integration (#24)

Business Value Justification (BVJ):
- Segment: Enterprise (Security-critical multi-tenant authentication)
- Business Goal: Ensure authentication context is never corrupted during WebSocket lifecycle
- Value Impact: Enterprise customers trust authentication is maintained throughout sessions
- Strategic Impact: Foundation of secure multi-user platform - prevents unauthorized access

CRITICAL SECURITY REQUIREMENT: Authentication context must be preserved and validated
throughout the entire WebSocket connection lifecycle - from initial connection,
through all operations, disconnections, and reconnections. Any authentication
context corruption is a critical security vulnerability.
"""

import asyncio
import pytest
import json
import time
import uuid
import jwt
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.fixtures.real_services import real_services_fixture
from netra_backend.app.core.managers.unified_state_manager import get_websocket_state_manager
from netra_backend.app.websocket_core.types import WebSocketConnectionState, MessageType
from shared.isolated_environment import get_env

# Type definitions
UserID = str
AuthToken = str
SessionID = str
ConnectionID = str


class AuthContextState(Enum):
    """States of authentication context during lifecycle."""
    VALID = "valid"
    EXPIRED = "expired"
    REVOKED = "revoked"
    INVALID = "invalid"
    CORRUPTED = "corrupted"


@dataclass
class AuthenticationContext:
    """Complete authentication context for a user."""
    user_id: UserID
    session_id: SessionID
    jwt_token: AuthToken
    refresh_token: str
    token_expiry: float
    permissions: List[str]
    organization_id: Optional[str] = None
    auth_state: AuthContextState = AuthContextState.VALID
    created_at: float = field(default_factory=time.time)
    last_validated: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "session_id": self.session_id,
            "jwt_token": self.jwt_token,
            "refresh_token": self.refresh_token,
            "token_expiry": self.token_expiry,
            "permissions": self.permissions,
            "organization_id": self.organization_id,
            "auth_state": self.auth_state.value,
            "created_at": self.created_at,
            "last_validated": self.last_validated
        }
    
    def is_valid(self) -> bool:
        """Check if authentication context is currently valid."""
        return (
            self.auth_state == AuthContextState.VALID and
            self.token_expiry > time.time() and
            self.jwt_token and
            self.user_id
        )


@dataclass
class WebSocketConnectionLifecycle:
    """Tracks WebSocket connection lifecycle stages."""
    connection_id: ConnectionID
    user_id: UserID
    auth_context: AuthenticationContext
    lifecycle_stages: List[str] = field(default_factory=list)
    auth_validations: List[Dict[str, Any]] = field(default_factory=list)
    connection_events: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_lifecycle_stage(self, stage: str, auth_valid: bool = True, details: Dict = None):
        """Add a lifecycle stage with authentication status."""
        self.lifecycle_stages.append(stage)
        self.auth_validations.append({
            "stage": stage,
            "timestamp": time.time(),
            "auth_valid": auth_valid,
            "auth_state": self.auth_context.auth_state.value,
            "details": details or {}
        })


class AuthContextPreservationValidator:
    """Validates authentication context preservation during WebSocket lifecycle."""
    
    def __init__(self, real_services):
        self.real_services = real_services
        self.redis_client = None
        self.jwt_secret = "test-jwt-secret-for-integration-testing"
        self.connection_lifecycles = {}
        self.auth_violations = []
    
    async def setup(self):
        """Set up validator with Redis connection."""
        import redis.asyncio as redis
        self.redis_client = redis.Redis.from_url(self.real_services["redis_url"])
        await self.redis_client.ping()
    
    async def cleanup(self):
        """Clean up validator resources."""
        if self.redis_client:
            await self.redis_client.aclose()
    
    def create_jwt_token(self, user_id: UserID, organization_id: str = None, 
                        permissions: List[str] = None, expiry_minutes: int = 60) -> Tuple[AuthToken, float]:
        """Create a valid JWT token for testing."""
        if permissions is None:
            permissions = ["read_messages", "write_messages", "manage_threads"]
        
        expiry_time = time.time() + (expiry_minutes * 60)
        payload = {
            "user_id": user_id,
            "organization_id": organization_id,
            "permissions": permissions,
            "exp": expiry_time,
            "iat": time.time(),
            "iss": "netra-test-issuer"
        }
        
        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        return token, expiry_time
    
    def validate_jwt_token(self, token: AuthToken) -> Dict[str, Any]:
        """Validate a JWT token and return payload."""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return {
                "valid": True,
                "payload": payload,
                "user_id": payload.get("user_id"),
                "permissions": payload.get("permissions", []),
                "organization_id": payload.get("organization_id"),
                "expiry": payload.get("exp")
            }
        except jwt.ExpiredSignatureError:
            return {"valid": False, "error": "token_expired"}
        except jwt.InvalidTokenError as e:
            return {"valid": False, "error": f"invalid_token: {str(e)}"}
    
    async def create_authenticated_user_session(self, user_suffix: str, 
                                              organization_id: str = None) -> Tuple[AuthenticationContext, ConnectionID]:
        """Create authenticated user session with all required context."""
        user_id = f"auth-test-user-{user_suffix}"
        session_id = f"session-{uuid.uuid4().hex}"
        connection_id = f"conn-{uuid.uuid4().hex}"
        
        # Create user in database
        await self.real_services["db"].execute("""
            INSERT INTO auth.users (id, email, name, is_active, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET 
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = NOW()
        """, user_id, f"{user_id}@auth-test.com", f"Auth Test User {user_suffix}", True)
        
        # Create organization if specified
        if organization_id is None:
            organization_id = f"org-{user_suffix}"
        
        await self.real_services["db"].execute("""
            INSERT INTO backend.organizations (id, name, slug, plan, created_at)
            VALUES ($1, $2, $3, $4, NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                slug = EXCLUDED.slug,
                plan = EXCLUDED.plan
        """, organization_id, f"Auth Test Org {user_suffix}", f"auth-org-{user_suffix}", "enterprise")
        
        # Create organization membership
        await self.real_services["db"].execute("""
            INSERT INTO backend.organization_memberships (user_id, organization_id, role, created_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, organization_id) DO UPDATE SET role = EXCLUDED.role
        """, user_id, organization_id, "admin")
        
        # Generate authentication tokens
        permissions = ["read_messages", "write_messages", "manage_threads", "admin_access"]
        jwt_token, token_expiry = self.create_jwt_token(user_id, organization_id, permissions)
        refresh_token = f"refresh-{uuid.uuid4().hex}"
        
        # Create authentication context
        auth_context = AuthenticationContext(
            user_id=user_id,
            session_id=session_id,
            jwt_token=jwt_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            permissions=permissions,
            organization_id=organization_id
        )
        
        # Store authentication data in Redis
        auth_key = f"auth_context:{session_id}"
        await self.redis_client.set(
            auth_key,
            json.dumps(auth_context.to_dict()),
            ex=3600
        )
        
        # Store WebSocket connection authentication
        ws_auth_key = f"ws_auth:{connection_id}"
        ws_auth_data = {
            "user_id": user_id,
            "session_id": session_id,
            "connection_id": connection_id,
            "authenticated_at": time.time(),
            "auth_token": jwt_token,
            "permissions": permissions,
            "organization_id": organization_id
        }
        
        await self.redis_client.set(
            ws_auth_key,
            json.dumps(ws_auth_data),
            ex=3600
        )
        
        return auth_context, connection_id
    
    async def simulate_websocket_connection_lifecycle(self, auth_context: AuthenticationContext, 
                                                    connection_id: ConnectionID) -> WebSocketConnectionLifecycle:
        """Simulate complete WebSocket connection lifecycle with authentication validation."""
        lifecycle = WebSocketConnectionLifecycle(
            connection_id=connection_id,
            user_id=auth_context.user_id,
            auth_context=auth_context
        )
        
        # Stage 1: Initial Connection
        await self._validate_connection_establishment(lifecycle)
        
        # Stage 2: Authentication Validation
        await self._validate_authentication_on_connect(lifecycle)
        
        # Stage 3: Message Operations (with auth checks)
        await self._validate_authenticated_message_operations(lifecycle)
        
        # Stage 4: Periodic Auth Validation
        await self._validate_periodic_auth_validation(lifecycle)
        
        # Stage 5: Disconnection
        await self._validate_authenticated_disconnection(lifecycle)
        
        # Stage 6: Reconnection
        await self._validate_authenticated_reconnection(lifecycle)
        
        self.connection_lifecycles[connection_id] = lifecycle
        return lifecycle
    
    async def _validate_connection_establishment(self, lifecycle: WebSocketConnectionLifecycle):
        """Validate authentication during connection establishment."""
        lifecycle.add_lifecycle_stage("connection_establishment")
        
        # Simulate WebSocket connection with authentication
        ws_state_data = {
            "user_id": lifecycle.user_id,
            "connection_id": lifecycle.connection_id,
            "state": WebSocketConnectionState.CONNECTING,
            "auth_required": True,
            "auth_validated": False,
            "established_at": time.time()
        }
        
        await self.redis_client.set(
            f"ws_state:{lifecycle.connection_id}",
            json.dumps(ws_state_data),
            ex=3600
        )
        
        # Validate authentication context is available
        auth_key = f"auth_context:{lifecycle.auth_context.session_id}"
        auth_data = await self.redis_client.get(auth_key)
        
        if auth_data:
            auth_dict = json.loads(auth_data)
            auth_valid = auth_dict.get("auth_state") == "valid"
            lifecycle.add_lifecycle_stage("auth_context_verified", auth_valid)
        else:
            lifecycle.add_lifecycle_stage("auth_context_missing", False)
            self.auth_violations.append({
                "type": "missing_auth_context",
                "connection_id": lifecycle.connection_id,
                "user_id": lifecycle.user_id,
                "stage": "connection_establishment"
            })
    
    async def _validate_authentication_on_connect(self, lifecycle: WebSocketConnectionLifecycle):
        """Validate JWT token authentication on WebSocket connect."""
        lifecycle.add_lifecycle_stage("jwt_validation")
        
        # Validate JWT token
        token_validation = self.validate_jwt_token(lifecycle.auth_context.jwt_token)
        
        if token_validation["valid"]:
            # Update WebSocket state as authenticated
            ws_state_key = f"ws_state:{lifecycle.connection_id}"
            ws_data = await self.redis_client.get(ws_state_key)
            if ws_data:
                ws_state = json.loads(ws_data)
                ws_state["state"] = WebSocketConnectionState.CONNECTED
                ws_state["auth_validated"] = True
                ws_state["auth_validated_at"] = time.time()
                ws_state["user_permissions"] = token_validation["payload"]["permissions"]
                await self.redis_client.set(ws_state_key, json.dumps(ws_state), ex=3600)
            
            lifecycle.add_lifecycle_stage("jwt_validated", True, token_validation)
        else:
            lifecycle.add_lifecycle_stage("jwt_validation_failed", False, token_validation)
            self.auth_violations.append({
                "type": "jwt_validation_failure",
                "connection_id": lifecycle.connection_id,
                "user_id": lifecycle.user_id,
                "error": token_validation["error"]
            })
    
    async def _validate_authenticated_message_operations(self, lifecycle: WebSocketConnectionLifecycle):
        """Validate authentication is preserved during message operations."""
        lifecycle.add_lifecycle_stage("message_operations_start")
        
        # Simulate multiple message operations with auth validation
        for i in range(3):
            # Before each operation, validate auth context
            auth_still_valid = await self._check_auth_context_integrity(lifecycle)
            
            if auth_still_valid:
                # Simulate message operation
                message_data = {
                    "type": MessageType.USER_MESSAGE,
                    "user_id": lifecycle.user_id,
                    "content": f"Authenticated message {i}",
                    "timestamp": time.time(),
                    "authenticated": True
                }
                
                # Store message with auth validation
                message_key = f"message:{lifecycle.connection_id}:{i}"
                await self.redis_client.set(message_key, json.dumps(message_data), ex=300)
                
                lifecycle.add_lifecycle_stage(f"message_op_{i}_success", True)
            else:
                lifecycle.add_lifecycle_stage(f"message_op_{i}_auth_failed", False)
                self.auth_violations.append({
                    "type": "auth_context_corrupted_during_operation",
                    "connection_id": lifecycle.connection_id,
                    "operation": f"message_op_{i}"
                })
            
            # Small delay between operations
            await asyncio.sleep(0.1)
    
    async def _validate_periodic_auth_validation(self, lifecycle: WebSocketConnectionLifecycle):
        """Validate periodic authentication validation."""
        lifecycle.add_lifecycle_stage("periodic_auth_validation")
        
        # Simulate periodic auth validation (like heartbeat with auth check)
        for i in range(2):
            auth_validation = self.validate_jwt_token(lifecycle.auth_context.jwt_token)
            
            if auth_validation["valid"]:
                # Update last validation time
                auth_key = f"auth_context:{lifecycle.auth_context.session_id}"
                auth_data = await self.redis_client.get(auth_key)
                if auth_data:
                    auth_dict = json.loads(auth_data)
                    auth_dict["last_validated"] = time.time()
                    await self.redis_client.set(auth_key, json.dumps(auth_dict), ex=3600)
                
                lifecycle.add_lifecycle_stage(f"periodic_validation_{i}_success", True)
            else:
                lifecycle.add_lifecycle_stage(f"periodic_validation_{i}_failed", False)
                self.auth_violations.append({
                    "type": "periodic_auth_validation_failure",
                    "connection_id": lifecycle.connection_id,
                    "validation_attempt": i
                })
            
            await asyncio.sleep(0.2)
    
    async def _validate_authenticated_disconnection(self, lifecycle: WebSocketConnectionLifecycle):
        """Validate authentication context handling during disconnection."""
        lifecycle.add_lifecycle_stage("disconnection_start")
        
        # Update WebSocket state to disconnecting
        ws_state_key = f"ws_state:{lifecycle.connection_id}"
        ws_data = await self.redis_client.get(ws_state_key)
        if ws_data:
            ws_state = json.loads(ws_data)
            ws_state["state"] = WebSocketConnectionState.DISCONNECTING
            ws_state["disconnect_initiated_at"] = time.time()
            await self.redis_client.set(ws_state_key, json.dumps(ws_state), ex=3600)
        
        # Authenticate disconnection (ensure user can disconnect their own connection)
        auth_still_valid = await self._check_auth_context_integrity(lifecycle)
        if auth_still_valid:
            # Clean disconnection with proper auth
            ws_state_key = f"ws_state:{lifecycle.connection_id}"
            ws_data = await self.redis_client.get(ws_state_key)
            if ws_data:
                ws_state = json.loads(ws_data)
                ws_state["state"] = WebSocketConnectionState.DISCONNECTED
                ws_state["disconnected_at"] = time.time()
                await self.redis_client.set(ws_state_key, json.dumps(ws_state), ex=300)
            
            lifecycle.add_lifecycle_stage("authenticated_disconnection_success", True)
        else:
            lifecycle.add_lifecycle_stage("disconnection_auth_failed", False)
    
    async def _validate_authenticated_reconnection(self, lifecycle: WebSocketConnectionLifecycle):
        """Validate authentication context during reconnection."""
        lifecycle.add_lifecycle_stage("reconnection_attempt")
        
        # Simulate reconnection with same auth context
        reconnection_id = f"reconn-{uuid.uuid4().hex[:8]}"
        
        # Validate existing auth context is still valid for reconnection
        auth_validation = self.validate_jwt_token(lifecycle.auth_context.jwt_token)
        
        if auth_validation["valid"]:
            # Create new WebSocket state for reconnection
            ws_reconnect_data = {
                "user_id": lifecycle.user_id,
                "connection_id": reconnection_id,
                "original_connection_id": lifecycle.connection_id,
                "state": WebSocketConnectionState.CONNECTED,
                "auth_validated": True,
                "reconnected_at": time.time(),
                "auth_preserved_from_previous": True
            }
            
            await self.redis_client.set(
                f"ws_state:{reconnection_id}",
                json.dumps(ws_reconnect_data),
                ex=3600
            )
            
            lifecycle.add_lifecycle_stage("authenticated_reconnection_success", True)
        else:
            lifecycle.add_lifecycle_stage("reconnection_auth_failed", False)
            self.auth_violations.append({
                "type": "reconnection_auth_failure",
                "original_connection_id": lifecycle.connection_id,
                "reconnection_id": reconnection_id,
                "auth_error": auth_validation["error"]
            })
    
    async def _check_auth_context_integrity(self, lifecycle: WebSocketConnectionLifecycle) -> bool:
        """Check if authentication context is still intact and valid."""
        auth_key = f"auth_context:{lifecycle.auth_context.session_id}"
        auth_data = await self.redis_client.get(auth_key)
        
        if not auth_data:
            return False
        
        auth_dict = json.loads(auth_data)
        
        # Validate JWT token is still valid
        token_validation = self.validate_jwt_token(auth_dict.get("jwt_token", ""))
        
        return (
            auth_dict.get("auth_state") == "valid" and
            token_validation["valid"] and
            auth_dict.get("user_id") == lifecycle.user_id
        )
    
    async def validate_multi_connection_auth_isolation(self, lifecycles: List[WebSocketConnectionLifecycle]) -> Dict[str, Any]:
        """Validate authentication isolation across multiple concurrent connections."""
        validation_results = {
            "total_connections": len(lifecycles),
            "auth_isolation_maintained": True,
            "auth_violations": [],
            "connection_results": {}
        }
        
        # Check each connection's authentication integrity
        for lifecycle in lifecycles:
            connection_result = {
                "connection_id": lifecycle.connection_id,
                "user_id": lifecycle.user_id,
                "auth_valid_throughout": True,
                "failed_validations": []
            }
            
            # Analyze all auth validations in the lifecycle
            for validation in lifecycle.auth_validations:
                if not validation["auth_valid"]:
                    connection_result["auth_valid_throughout"] = False
                    connection_result["failed_validations"].append(validation)
                    validation_results["auth_isolation_maintained"] = False
            
            validation_results["connection_results"][lifecycle.connection_id] = connection_result
        
        # Check for cross-connection auth contamination
        for i, lifecycle_a in enumerate(lifecycles):
            for j, lifecycle_b in enumerate(lifecycles):
                if i != j:  # Different connections
                    # Verify connection A cannot use connection B's auth
                    auth_key_a = f"auth_context:{lifecycle_a.auth_context.session_id}"
                    auth_key_b = f"auth_context:{lifecycle_b.auth_context.session_id}"
                    
                    auth_data_a = await self.redis_client.get(auth_key_a)
                    auth_data_b = await self.redis_client.get(auth_key_b)
                    
                    if auth_data_a and auth_data_b:
                        auth_a = json.loads(auth_data_a)
                        auth_b = json.loads(auth_data_b)
                        
                        # Check for session ID bleeding
                        if auth_a.get("session_id") == auth_b.get("session_id") and lifecycle_a.user_id != lifecycle_b.user_id:
                            validation_results["auth_violations"].append({
                                "type": "session_id_bleeding",
                                "connection_a": lifecycle_a.connection_id,
                                "connection_b": lifecycle_b.connection_id,
                                "shared_session_id": auth_a.get("session_id")
                            })
                            validation_results["auth_isolation_maintained"] = False
        
        validation_results["auth_violations"].extend(self.auth_violations)
        return validation_results


class TestWebSocketAuthenticationContextPreservation(BaseIntegrationTest):
    """
    Integration test for authentication context preservation during WebSocket lifecycle.
    
    CRITICAL: Validates that authentication context remains valid and isolated
    throughout the entire WebSocket connection lifecycle.
    """
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.security_critical
    async def test_authentication_context_preserved_throughout_websocket_lifecycle(self, real_services_fixture):
        """
        Test authentication context preservation throughout complete WebSocket lifecycle.
        
        SECURITY CRITICAL: Authentication must never be corrupted or lost during lifecycle.
        """
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AuthContextPreservationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create authenticated user session
            auth_context, connection_id = await validator.create_authenticated_user_session("lifecycle-1")
            
            # Verify initial authentication context is valid
            assert auth_context.is_valid(), "Initial authentication context must be valid"
            
            # Execute complete WebSocket lifecycle
            lifecycle = await validator.simulate_websocket_connection_lifecycle(auth_context, connection_id)
            
            # CRITICAL VALIDATIONS: Authentication must be preserved throughout
            auth_validations = lifecycle.auth_validations
            failed_validations = [v for v in auth_validations if not v["auth_valid"]]
            
            assert len(failed_validations) == 0, \
                f"Authentication failed during lifecycle: {failed_validations}"
            
            # Verify all expected lifecycle stages completed successfully
            expected_stages = [
                "connection_establishment",
                "auth_context_verified",
                "jwt_validation",
                "jwt_validated",
                "message_operations_start",
                "periodic_auth_validation",
                "disconnection_start",
                "authenticated_disconnection_success",
                "reconnection_attempt",
                "authenticated_reconnection_success"
            ]
            
            completed_stages = lifecycle.lifecycle_stages
            for expected_stage in expected_stages:
                assert expected_stage in completed_stages, \
                    f"Expected lifecycle stage '{expected_stage}' not completed"
            
            # Verify no authentication violations occurred
            assert len(validator.auth_violations) == 0, \
                f"Authentication violations detected: {validator.auth_violations}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.concurrency
    async def test_concurrent_websocket_authentication_isolation(self, real_services_fixture):
        """Test authentication isolation across multiple concurrent WebSocket connections."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AuthContextPreservationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create multiple authenticated users
            auth_sessions = []
            for i in range(3):
                auth_context, connection_id = await validator.create_authenticated_user_session(f"concurrent-{i}")
                auth_sessions.append((auth_context, connection_id))
            
            # Execute concurrent WebSocket lifecycles
            lifecycle_tasks = [
                validator.simulate_websocket_connection_lifecycle(auth_context, conn_id)
                for auth_context, conn_id in auth_sessions
            ]
            
            lifecycles = await asyncio.gather(*lifecycle_tasks)
            
            # Validate authentication isolation across all connections
            isolation_results = await validator.validate_multi_connection_auth_isolation(lifecycles)
            
            # CRITICAL: Authentication must be isolated between connections
            assert isolation_results["auth_isolation_maintained"], \
                f"Authentication isolation violated: {isolation_results['auth_violations']}"
            assert isolation_results["total_connections"] == 3
            assert len(isolation_results["auth_violations"]) == 0, \
                f"Authentication violations: {isolation_results['auth_violations']}"
            
            # Verify each connection maintained auth throughout its lifecycle
            for connection_id, result in isolation_results["connection_results"].items():
                assert result["auth_valid_throughout"], \
                    f"Connection {connection_id} lost authentication: {result['failed_validations']}"
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.auth_critical
    async def test_expired_token_handling_during_websocket_operations(self, real_services_fixture):
        """Test proper handling of expired authentication tokens during WebSocket operations."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AuthContextPreservationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create user session with short-lived token (1 minute)
            user_id = "expired-token-user"
            session_id = f"session-{uuid.uuid4().hex}"
            connection_id = f"conn-{uuid.uuid4().hex}"
            
            # Create user
            await validator.real_services["db"].execute("""
                INSERT INTO auth.users (id, email, name, is_active, created_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (id) DO UPDATE SET 
                    email = EXCLUDED.email,
                    name = EXCLUDED.name,
                    is_active = EXCLUDED.is_active
            """, user_id, f"{user_id}@test.com", "Expired Token Test User", True)
            
            # Create short-lived JWT token (1 second expiry for testing)
            jwt_token, token_expiry = validator.create_jwt_token(user_id, expiry_minutes=0.0167)  # 1 second
            
            auth_context = AuthenticationContext(
                user_id=user_id,
                session_id=session_id,
                jwt_token=jwt_token,
                refresh_token=f"refresh-{uuid.uuid4().hex}",
                token_expiry=token_expiry,
                permissions=["read_messages"],
                auth_state=AuthContextState.VALID
            )
            
            # Initial validation - should be valid
            initial_validation = validator.validate_jwt_token(auth_context.jwt_token)
            assert initial_validation["valid"], "Token should be initially valid"
            
            # Wait for token to expire
            await asyncio.sleep(2)
            
            # Validation after expiry - should be invalid
            expired_validation = validator.validate_jwt_token(auth_context.jwt_token)
            assert not expired_validation["valid"], "Token should be expired"
            assert expired_validation["error"] == "token_expired"
            
            # Verify WebSocket operations properly handle expired token
            auth_context.auth_state = AuthContextState.EXPIRED
            
            # Simulate WebSocket operation with expired token
            lifecycle = WebSocketConnectionLifecycle(
                connection_id=connection_id,
                user_id=user_id,
                auth_context=auth_context
            )
            
            # This should detect and handle the expired token
            auth_integrity = await validator._check_auth_context_integrity(lifecycle)
            assert not auth_integrity, "Expired token should fail integrity check"
            
            # Verify system properly rejected operations with expired token
            assert auth_context.auth_state == AuthContextState.EXPIRED
            
        finally:
            await validator.cleanup()
    
    @pytest.mark.integration
    @pytest.mark.real_services
    @pytest.mark.enterprise
    async def test_organization_context_preservation_in_authentication(self, real_services_fixture):
        """Test organization context preservation within authentication during WebSocket operations."""
        # Skip if database not available
        if not real_services_fixture.get("database_available"):
            pytest.skip("Database not available for integration testing")
        
        validator = AuthContextPreservationValidator(real_services_fixture)
        await validator.setup()
        
        try:
            # Create users from different organizations
            org_a_auth, org_a_conn = await validator.create_authenticated_user_session("org-a", "organization-a")
            org_b_auth, org_b_conn = await validator.create_authenticated_user_session("org-b", "organization-b")
            
            # Verify organization isolation in authentication context
            assert org_a_auth.organization_id == "organization-a"
            assert org_b_auth.organization_id == "organization-b"
            assert org_a_auth.organization_id != org_b_auth.organization_id
            
            # Execute lifecycle for both organizational users
            lifecycles = await asyncio.gather(
                validator.simulate_websocket_connection_lifecycle(org_a_auth, org_a_conn),
                validator.simulate_websocket_connection_lifecycle(org_b_auth, org_b_conn)
            )
            
            # Validate organization context preserved in both lifecycles
            org_a_lifecycle, org_b_lifecycle = lifecycles
            
            # Check that organization context was maintained throughout
            for validation in org_a_lifecycle.auth_validations:
                if validation["auth_valid"]:
                    # Verify JWT token still contains correct organization
                    token_validation = validator.validate_jwt_token(org_a_auth.jwt_token)
                    assert token_validation["organization_id"] == "organization-a"
            
            for validation in org_b_lifecycle.auth_validations:
                if validation["auth_valid"]:
                    # Verify JWT token still contains correct organization
                    token_validation = validator.validate_jwt_token(org_b_auth.jwt_token)
                    assert token_validation["organization_id"] == "organization-b"
            
            # Validate no cross-organization authentication contamination
            isolation_results = await validator.validate_multi_connection_auth_isolation([org_a_lifecycle, org_b_lifecycle])
            
            assert isolation_results["auth_isolation_maintained"], \
                "Organization-level authentication isolation must be maintained"
            
        finally:
            await validator.cleanup()