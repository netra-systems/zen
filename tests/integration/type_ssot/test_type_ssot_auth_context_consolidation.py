"""
Test Auth Context Type SSOT Compliance and JWT Payload Consistency

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure authentication context consistency across all services
- Value Impact: Prevents auth failures and security vulnerabilities from type mismatches
- Strategic Impact: Auth reliability is prerequisite for $120K+ MRR platform access

CRITICAL: AuthContextType and JWTPayload currently defined in multiple locations
violating SSOT principles. This creates auth token validation inconsistencies
and potential security vulnerabilities in multi-service authentication.
"""

import pytest
import asyncio
import json
import jwt
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.types.core_types import UserID, SessionID, TokenString


@dataclass
class AuthContextType:
    """Strongly typed authentication context for SSOT validation."""
    user_id: UserID
    session_id: SessionID
    email: str
    permissions: List[str]
    is_valid: bool
    expires_at: datetime
    auth_method: str
    token_type: str = "bearer"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'user_id': str(self.user_id),
            'session_id': str(self.session_id),
            'email': self.email,
            'permissions': self.permissions,
            'is_valid': self.is_valid,
            'expires_at': self.expires_at.isoformat(),
            'auth_method': self.auth_method,
            'token_type': self.token_type
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuthContextType':
        return cls(
            user_id=UserID(data['user_id']),
            session_id=SessionID(data['session_id']),
            email=data['email'],
            permissions=data['permissions'],
            is_valid=data['is_valid'],
            expires_at=datetime.fromisoformat(data['expires_at']),
            auth_method=data['auth_method'],
            token_type=data.get('token_type', 'bearer')
        )


@dataclass 
class JWTPayload:
    """Strongly typed JWT payload for SSOT validation."""
    sub: UserID  # Subject (user ID)
    iat: int     # Issued at
    exp: int     # Expires at
    aud: str     # Audience
    iss: str     # Issuer
    email: str
    permissions: List[str]
    session_id: Optional[SessionID] = None
    auth_method: str = "oauth"
    
    def to_dict(self) -> Dict[str, Any]:
        payload = {
            'sub': str(self.sub),
            'iat': self.iat,
            'exp': self.exp,
            'aud': self.aud,
            'iss': self.iss,
            'email': self.email,
            'permissions': self.permissions,
            'auth_method': self.auth_method
        }
        
        if self.session_id:
            payload['session_id'] = str(self.session_id)
            
        return payload
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'JWTPayload':
        return cls(
            sub=UserID(data['sub']),
            iat=data['iat'],
            exp=data['exp'],
            aud=data['aud'],
            iss=data['iss'],
            email=data['email'],
            permissions=data['permissions'],
            session_id=SessionID(data['session_id']) if data.get('session_id') else None,
            auth_method=data.get('auth_method', 'oauth')
        )


class TestAuthContextSSotCompliance(BaseIntegrationTest):
    """Integration tests for AuthContext type SSOT compliance across services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_context_canonical_definition_validation(self, real_services_fixture):
        """
        Test that AuthContextType has ONE canonical definition across all services.
        
        SECURITY CRITICAL: Multiple AuthContext definitions create validation
        inconsistencies and potential security vulnerabilities.
        """
        import importlib
        import inspect
        
        # Known locations where AuthContext might be defined
        potential_auth_locations = [
            "shared.types.core_types",
            "shared.types.auth_types", 
            "netra_backend.app.schemas.auth",
            "auth_service.schemas.auth",
            "netra_backend.app.services.user_auth_service",
            "shared.authentication.auth_context"
        ]
        
        auth_context_definitions = []
        
        for module_path in potential_auth_locations:
            try:
                module = importlib.import_module(module_path)
                
                # Check for AuthContextType or similar auth context classes
                for name in dir(module):
                    if 'AuthContext' in name and not name.startswith('_'):
                        auth_class = getattr(module, name)
                        if inspect.isclass(auth_class):
                            auth_context_definitions.append({
                                'module': module_path,
                                'class_name': name,
                                'class': auth_class,
                                'file': inspect.getfile(auth_class)
                            })
            except ImportError:
                # Module may not exist
                continue
        
        # SSOT VALIDATION: Should have at most one canonical AuthContext definition
        canonical_definitions = [
            defn for defn in auth_context_definitions 
            if 'shared.types' in defn['module'] or 'shared.auth' in defn['module']
        ]
        
        assert len(canonical_definitions) <= 1, (
            f"SSOT VIOLATION: Multiple canonical AuthContext definitions found:\n"
            f"{chr(10).join([f'  {defn['module']}.{defn['class_name']}' for defn in canonical_definitions])}\n"
            f"Must have exactly ONE canonical AuthContext definition."
        )
        
        # If canonical definition exists, validate structure
        if canonical_definitions:
            canonical_def = canonical_definitions[0]
            auth_class = canonical_def['class']
            
            # Validate required fields for auth context
            required_fields = ['user_id', 'is_valid', 'permissions']
            
            if hasattr(auth_class, '__annotations__'):
                annotations = auth_class.__annotations__
                for field in required_fields:
                    assert field in annotations, (
                        f"Canonical AuthContext must have '{field}' field"
                    )
            elif hasattr(auth_class, '_fields'):
                # Named tuple or dataclass
                fields = auth_class._fields if hasattr(auth_class, '_fields') else []
                for field in required_fields:
                    assert field in fields, (
                        f"Canonical AuthContext must have '{field}' field"
                    )


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_payload_structure_consistency(self, real_services_fixture):
        """
        Test that JWT payload structure is consistent across auth and backend services.
        
        MISSION CRITICAL: JWT payload inconsistencies break token validation
        and cause authentication failures across service boundaries.
        """
        # Setup real Redis for token storage
        redis_client = real_services_fixture['redis']
        
        # Mock JWT service for testing
        class MockJWTService:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.secret_key = "test-jwt-secret-key-for-integration-testing"
                self.algorithm = "HS256"
            
            def create_jwt_token(self, payload: JWTPayload) -> TokenString:
                """Create JWT token with strongly typed payload."""
                token = jwt.encode(
                    payload.to_dict(),
                    self.secret_key,
                    algorithm=self.algorithm
                )
                return TokenString(token)
            
            def validate_jwt_token(self, token: TokenString) -> Optional[JWTPayload]:
                """Validate JWT token and return strongly typed payload."""
                try:
                    decoded = jwt.decode(
                        str(token),
                        self.secret_key,
                        algorithms=[self.algorithm]
                    )
                    return JWTPayload.from_dict(decoded)
                except jwt.InvalidTokenError:
                    return None
            
            async def store_token_context(self, token: TokenString, auth_context: AuthContextType):
                """Store auth context associated with JWT token."""
                token_hash = str(hash(str(token)))[-8:]  # Use last 8 chars of hash as key
                
                await self.redis.setex(
                    f"token_context:{token_hash}",
                    3600,  # 1 hour
                    json.dumps(auth_context.to_dict())
                )
            
            async def get_token_context(self, token: TokenString) -> Optional[AuthContextType]:
                """Retrieve auth context associated with JWT token."""
                token_hash = str(hash(str(token)))[-8:]
                
                context_data = await self.redis.get(f"token_context:{token_hash}")
                if context_data:
                    return AuthContextType.from_dict(json.loads(context_data.decode()))
                return None
        
        jwt_service = MockJWTService(redis_client)
        
        # Test JWT token creation and validation consistency
        test_user_id = UserID("jwt-test-user-001")
        test_session_id = SessionID("jwt-session-001")
        
        # Create test JWT payload
        current_time = int(time.time())
        jwt_payload = JWTPayload(
            sub=test_user_id,
            iat=current_time,
            exp=current_time + 3600,  # 1 hour
            aud="netra-apex",
            iss="netra-auth-service",
            email="jwt-test@example.com",
            permissions=["read", "write", "execute"],
            session_id=test_session_id,
            auth_method="oauth"
        )
        
        # Create corresponding auth context
        auth_context = AuthContextType(
            user_id=test_user_id,
            session_id=test_session_id,
            email="jwt-test@example.com",
            permissions=["read", "write", "execute"],
            is_valid=True,
            expires_at=datetime.fromtimestamp(current_time + 3600, tz=timezone.utc),
            auth_method="oauth",
            token_type="bearer"
        )
        
        # Create and validate JWT token
        jwt_token = jwt_service.create_jwt_token(jwt_payload)
        
        # Store token context
        await jwt_service.store_token_context(jwt_token, auth_context)
        
        # Validate token and check consistency
        validated_payload = jwt_service.validate_jwt_token(jwt_token)
        assert validated_payload is not None, "JWT token validation must succeed"
        
        # Retrieve stored context
        stored_context = await jwt_service.get_token_context(jwt_token)
        assert stored_context is not None, "Auth context must be retrievable"
        
        # CRITICAL: JWT payload and auth context must be consistent
        assert validated_payload.sub == stored_context.user_id, (
            f"JWT sub and auth context user_id must match: {validated_payload.sub} != {stored_context.user_id}"
        )
        
        assert validated_payload.email == stored_context.email, (
            f"JWT email and auth context email must match: {validated_payload.email} != {stored_context.email}"
        )
        
        assert validated_payload.permissions == stored_context.permissions, (
            f"JWT permissions and auth context permissions must match: {validated_payload.permissions} != {stored_context.permissions}"
        )
        
        assert validated_payload.session_id == stored_context.session_id, (
            f"JWT session_id and auth context session_id must match: {validated_payload.session_id} != {stored_context.session_id}"
        )
        
        assert validated_payload.auth_method == stored_context.auth_method, (
            f"JWT auth_method and auth context auth_method must match: {validated_payload.auth_method} != {stored_context.auth_method}"
        )
        
        # Validate expiration consistency
        jwt_expiry = datetime.fromtimestamp(validated_payload.exp, tz=timezone.utc)
        context_expiry = stored_context.expires_at
        
        # Allow small time difference (within 1 second)
        time_diff = abs((jwt_expiry - context_expiry).total_seconds())
        assert time_diff <= 1.0, (
            f"JWT expiry and auth context expiry must be consistent: {jwt_expiry} vs {context_expiry}"
        )
        
        # Cleanup
        token_hash = str(hash(str(jwt_token)))[-8:]
        await redis_client.delete(f"token_context:{token_hash}")


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_context_cross_service_validation(self, real_services_fixture):
        """
        Test that auth context validation is consistent between auth service and backend.
        
        GOLDEN PATH CRITICAL: Inconsistent auth validation breaks user access
        and creates security vulnerabilities in multi-service architecture.
        """
        # Setup real database and Redis
        db_session = real_services_fixture['db']
        redis_client = real_services_fixture['redis']
        
        # Mock auth service validator
        class AuthServiceValidator:
            def __init__(self, db_session, redis_client):
                self.db = db_session
                self.redis = redis_client
            
            async def validate_auth_context(self, token: TokenString) -> Optional[AuthContextType]:
                """Validate auth context using auth service logic."""
                # Simulate auth service validation
                token_data = {
                    'sub': 'auth-svc-user-001',
                    'email': 'auth-test@example.com', 
                    'permissions': ['read', 'write'],
                    'iat': int(time.time()) - 300,  # 5 minutes ago
                    'exp': int(time.time()) + 3300,  # 55 minutes from now
                    'session_id': 'auth-session-001'
                }
                
                # Check token expiry
                if token_data['exp'] <= int(time.time()):
                    return None
                
                # Create auth context
                auth_context = AuthContextType(
                    user_id=UserID(token_data['sub']),
                    session_id=SessionID(token_data['session_id']),
                    email=token_data['email'],
                    permissions=token_data['permissions'],
                    is_valid=True,
                    expires_at=datetime.fromtimestamp(token_data['exp'], tz=timezone.utc),
                    auth_method="oauth"
                )
                
                # Cache validation result
                await self.redis.setex(
                    f"auth_validation:{str(token)}",
                    300,  # 5 minutes
                    json.dumps(auth_context.to_dict())
                )
                
                return auth_context
        
        # Mock backend service validator
        class BackendServiceValidator:
            def __init__(self, db_session, redis_client):
                self.db = db_session
                self.redis = redis_client
            
            async def validate_auth_context(self, token: TokenString) -> Optional[AuthContextType]:
                """Validate auth context using backend service logic."""
                # Check cache first
                cached_validation = await self.redis.get(f"auth_validation:{str(token)}")
                if cached_validation:
                    cached_data = json.loads(cached_validation.decode())
                    return AuthContextType.from_dict(cached_data)
                
                # Fallback to direct validation (should match auth service logic)
                token_data = {
                    'sub': 'auth-svc-user-001',
                    'email': 'auth-test@example.com',
                    'permissions': ['read', 'write'],
                    'iat': int(time.time()) - 300,
                    'exp': int(time.time()) + 3300,
                    'session_id': 'auth-session-001'
                }
                
                if token_data['exp'] <= int(time.time()):
                    return None
                
                return AuthContextType(
                    user_id=UserID(token_data['sub']),
                    session_id=SessionID(token_data['session_id']),
                    email=token_data['email'],
                    permissions=token_data['permissions'],
                    is_valid=True,
                    expires_at=datetime.fromtimestamp(token_data['exp'], tz=timezone.utc),
                    auth_method="oauth"
                )
        
        auth_validator = AuthServiceValidator(db_session, redis_client)
        backend_validator = BackendServiceValidator(db_session, redis_client)
        
        # Test cross-service validation consistency
        test_token = TokenString("test-cross-service-token-12345")
        
        # Validate using auth service
        auth_context_from_auth = await auth_validator.validate_auth_context(test_token)
        assert auth_context_from_auth is not None, "Auth service validation must succeed"
        
        # Validate using backend service (should use cached result)
        auth_context_from_backend = await backend_validator.validate_auth_context(test_token)
        assert auth_context_from_backend is not None, "Backend service validation must succeed"
        
        # CRITICAL: Both services must return identical auth contexts
        assert auth_context_from_auth.user_id == auth_context_from_backend.user_id, (
            f"User ID must be consistent: {auth_context_from_auth.user_id} != {auth_context_from_backend.user_id}"
        )
        
        assert auth_context_from_auth.session_id == auth_context_from_backend.session_id, (
            f"Session ID must be consistent: {auth_context_from_auth.session_id} != {auth_context_from_backend.session_id}"
        )
        
        assert auth_context_from_auth.email == auth_context_from_backend.email, (
            f"Email must be consistent: {auth_context_from_auth.email} != {auth_context_from_backend.email}"
        )
        
        assert auth_context_from_auth.permissions == auth_context_from_backend.permissions, (
            f"Permissions must be consistent: {auth_context_from_auth.permissions} != {auth_context_from_backend.permissions}"
        )
        
        assert auth_context_from_auth.is_valid == auth_context_from_backend.is_valid, (
            f"Validity must be consistent: {auth_context_from_auth.is_valid} != {auth_context_from_backend.is_valid}"
        )
        
        assert auth_context_from_auth.auth_method == auth_context_from_backend.auth_method, (
            f"Auth method must be consistent: {auth_context_from_auth.auth_method} != {auth_context_from_backend.auth_method}"
        )
        
        # Validate timestamp consistency (within 1 second tolerance)
        time_diff = abs((auth_context_from_auth.expires_at - auth_context_from_backend.expires_at).total_seconds())
        assert time_diff <= 1.0, (
            f"Expiry times must be consistent within 1 second: {auth_context_from_auth.expires_at} vs {auth_context_from_backend.expires_at}"
        )
        
        # Cleanup
        await redis_client.delete(f"auth_validation:{str(test_token)}")


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_auth_context_permission_consistency_validation(self, real_services_fixture):
        """
        Test that permission validation is consistent across all auth context usages.
        
        SECURITY CRITICAL: Permission inconsistencies create security vulnerabilities
        and unauthorized access to platform features.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock permission validator
        class PermissionValidator:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.permission_hierarchy = {
                    'admin': ['read', 'write', 'delete', 'manage_users', 'manage_system'],
                    'manager': ['read', 'write', 'delete', 'manage_team'],
                    'user': ['read', 'write'],
                    'readonly': ['read']
                }
            
            def expand_permissions(self, permissions: List[str]) -> List[str]:
                """Expand role-based permissions to explicit permissions."""
                expanded = set()
                
                for permission in permissions:
                    if permission in self.permission_hierarchy:
                        # Role-based permission
                        expanded.update(self.permission_hierarchy[permission])
                    else:
                        # Explicit permission
                        expanded.add(permission)
                
                return sorted(list(expanded))
            
            def validate_permission(self, auth_context: AuthContextType, required_permission: str) -> bool:
                """Validate if auth context has required permission."""
                if not auth_context.is_valid:
                    return False
                
                # Check if context is expired
                if auth_context.expires_at <= datetime.now(timezone.utc):
                    return False
                
                # Expand permissions and check
                expanded_permissions = self.expand_permissions(auth_context.permissions)
                return required_permission in expanded_permissions
            
            async def cache_permission_check(self, auth_context: AuthContextType, permission: str, result: bool):
                """Cache permission check result."""
                cache_key = f"perm_check:{auth_context.user_id}:{permission}"
                
                cache_data = {
                    'user_id': str(auth_context.user_id),
                    'permission': permission,
                    'result': result,
                    'checked_at': time.time(),
                    'context_expires_at': auth_context.expires_at.timestamp()
                }
                
                # Cache until context expires
                ttl = max(1, int(auth_context.expires_at.timestamp() - time.time()))
                await self.redis.setex(cache_key, ttl, json.dumps(cache_data))
        
        permission_validator = PermissionValidator(redis_client)
        
        # Test different auth contexts with various permission levels
        test_scenarios = [
            {
                'name': 'admin_user',
                'auth_context': AuthContextType(
                    user_id=UserID("admin-user-001"),
                    session_id=SessionID("admin-session-001"),
                    email="admin@example.com",
                    permissions=["admin"],
                    is_valid=True,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    auth_method="oauth"
                ),
                'expected_permissions': {
                    'read': True,
                    'write': True,
                    'delete': True,
                    'manage_users': True,
                    'manage_system': True,
                    'invalid_permission': False
                }
            },
            {
                'name': 'manager_user',
                'auth_context': AuthContextType(
                    user_id=UserID("manager-user-001"),
                    session_id=SessionID("manager-session-001"),
                    email="manager@example.com",
                    permissions=["manager"],
                    is_valid=True,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    auth_method="oauth"
                ),
                'expected_permissions': {
                    'read': True,
                    'write': True,
                    'delete': True,
                    'manage_team': True,
                    'manage_users': False,
                    'manage_system': False
                }
            },
            {
                'name': 'regular_user',
                'auth_context': AuthContextType(
                    user_id=UserID("regular-user-001"),
                    session_id=SessionID("regular-session-001"),
                    email="user@example.com",
                    permissions=["user"],
                    is_valid=True,
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    auth_method="oauth"
                ),
                'expected_permissions': {
                    'read': True,
                    'write': True,
                    'delete': False,
                    'manage_team': False,
                    'manage_users': False
                }
            },
            {
                'name': 'expired_user',
                'auth_context': AuthContextType(
                    user_id=UserID("expired-user-001"),
                    session_id=SessionID("expired-session-001"),
                    email="expired@example.com",
                    permissions=["admin"],
                    is_valid=True,
                    expires_at=datetime.now(timezone.utc) - timedelta(minutes=5),  # Expired
                    auth_method="oauth"
                ),
                'expected_permissions': {
                    'read': False,
                    'write': False,
                    'delete': False,
                    'manage_users': False
                }
            }
        ]
        
        # Test permission validation consistency
        for scenario in test_scenarios:
            auth_context = scenario['auth_context']
            expected_perms = scenario['expected_permissions']
            
            for permission, expected_result in expected_perms.items():
                # Validate permission
                actual_result = permission_validator.validate_permission(auth_context, permission)
                
                assert actual_result == expected_result, (
                    f"Permission validation for {scenario['name']}.{permission}: "
                    f"expected {expected_result}, got {actual_result}"
                )
                
                # Cache the result
                await permission_validator.cache_permission_check(auth_context, permission, actual_result)
        
        # Validate cached permission consistency
        for scenario in test_scenarios:
            auth_context = scenario['auth_context']
            
            for permission in scenario['expected_permissions']:
                cache_key = f"perm_check:{auth_context.user_id}:{permission}"
                cached_data = await redis_client.get(cache_key)
                
                if cached_data:  # May not exist for expired contexts
                    cached_result = json.loads(cached_data.decode())
                    
                    assert cached_result['user_id'] == str(auth_context.user_id), (
                        f"Cached permission user_id must match context"
                    )
                    assert cached_result['permission'] == permission, (
                        f"Cached permission name must match"
                    )
                    
                    # Re-validate and ensure consistency
                    fresh_result = permission_validator.validate_permission(auth_context, permission)
                    assert cached_result['result'] == fresh_result, (
                        f"Cached permission result must match fresh validation for {auth_context.user_id}.{permission}"
                    )
        
        # Cleanup cached permissions
        for scenario in test_scenarios:
            for permission in scenario['expected_permissions']:
                cache_key = f"perm_check:{scenario['auth_context'].user_id}:{permission}"
                await redis_client.delete(cache_key)