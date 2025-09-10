"""
Test JWT Payload Type SSOT Compliance and Token Validation Consistency

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure JWT token validation consistency across all services
- Value Impact: Prevents token validation failures and auth service disruptions
- Strategic Impact: Authentication reliability is foundation for platform access

CRITICAL: JWTPayload structure must be consistent across auth service, backend,
and frontend to prevent token validation failures and authentication breakdowns
that directly impact user access and platform reliability.
"""

import pytest
import asyncio
import json
import jwt
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.types.core_types import UserID, SessionID, TokenString


@dataclass
class StandardJWTPayload:
    """Standard JWT payload structure for SSOT validation."""
    sub: str         # Subject (user ID)
    iat: int         # Issued at timestamp
    exp: int         # Expires at timestamp
    aud: str         # Audience
    iss: str         # Issuer
    jti: Optional[str] = None  # JWT ID
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StandardJWTPayload':
        return cls(
            sub=data['sub'],
            iat=data['iat'],
            exp=data['exp'],
            aud=data['aud'],
            iss=data['iss'],
            jti=data.get('jti')
        )


@dataclass
class ExtendedJWTPayload(StandardJWTPayload):
    """Extended JWT payload with application-specific claims."""
    email: str
    permissions: List[str]
    session_id: Optional[str] = None
    auth_method: str = "oauth"
    user_role: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtendedJWTPayload':
        return cls(
            sub=data['sub'],
            iat=data['iat'],
            exp=data['exp'],
            aud=data['aud'],
            iss=data['iss'],
            jti=data.get('jti'),
            email=data['email'],
            permissions=data['permissions'],
            session_id=data.get('session_id'),
            auth_method=data.get('auth_method', 'oauth'),
            user_role=data.get('user_role')
        )


class TestJWTPayloadSSotCompliance(BaseIntegrationTest):
    """Integration tests for JWT payload SSOT compliance across services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_payload_structure_standardization(self, real_services_fixture):
        """
        Test that JWT payload structure follows standard claims and extensions.
        
        MISSION CRITICAL: Consistent JWT structure prevents token validation
        failures between services and maintains authentication reliability.
        """
        # Setup real Redis for token storage
        redis_client = real_services_fixture['redis']
        
        # Mock JWT token manager with standardized payload handling
        class StandardJWTTokenManager:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.secret_key = "integration-test-jwt-secret-key"
                self.algorithm = "HS256"
                self.issuer = "netra-auth-service"
                self.audience = "netra-platform"
            
            def create_standard_token(self, user_id: str, email: str, permissions: List[str], session_id: Optional[str] = None) -> TokenString:
                """Create JWT with standardized payload structure."""
                current_time = int(time.time())
                
                # Standard claims
                standard_payload = StandardJWTPayload(
                    sub=user_id,
                    iat=current_time,
                    exp=current_time + 3600,  # 1 hour
                    aud=self.audience,
                    iss=self.issuer,
                    jti=f"jwt-{user_id}-{current_time}"
                )
                
                # Extended claims
                extended_payload = ExtendedJWTPayload(
                    sub=standard_payload.sub,
                    iat=standard_payload.iat,
                    exp=standard_payload.exp,
                    aud=standard_payload.aud,
                    iss=standard_payload.iss,
                    jti=standard_payload.jti,
                    email=email,
                    permissions=permissions,
                    session_id=session_id,
                    auth_method="oauth"
                )
                
                # Create token
                token = jwt.encode(
                    extended_payload.to_dict(),
                    self.secret_key,
                    algorithm=self.algorithm
                )
                
                return TokenString(token)
            
            def validate_token_structure(self, token: TokenString) -> Optional[ExtendedJWTPayload]:
                """Validate token and return structured payload."""
                try:
                    decoded = jwt.decode(
                        str(token),
                        self.secret_key,
                        algorithms=[self.algorithm],
                        audience=self.audience,
                        issuer=self.issuer
                    )
                    
                    # Validate required standard claims
                    required_claims = ['sub', 'iat', 'exp', 'aud', 'iss']
                    for claim in required_claims:
                        if claim not in decoded:
                            raise ValueError(f"Missing required claim: {claim}")
                    
                    # Validate extended claims
                    if 'email' not in decoded:
                        raise ValueError("Missing required email claim")
                    if 'permissions' not in decoded:
                        raise ValueError("Missing required permissions claim")
                    
                    return ExtendedJWTPayload.from_dict(decoded)
                    
                except jwt.InvalidTokenError:
                    return None
                except ValueError:
                    return None
            
            async def store_token_metadata(self, token: TokenString, payload: ExtendedJWTPayload):
                """Store token metadata for validation tracking."""
                token_id = payload.jti or f"token-{payload.sub}-{payload.iat}"
                
                metadata = {
                    'token_id': token_id,
                    'user_id': payload.sub,
                    'issued_at': payload.iat,
                    'expires_at': payload.exp,
                    'email': payload.email,
                    'session_id': payload.session_id,
                    'permissions': payload.permissions,
                    'created_at': time.time()
                }
                
                # Store with TTL matching token expiry
                ttl = max(1, payload.exp - int(time.time()))
                await self.redis.setex(f"token_metadata:{token_id}", ttl, json.dumps(metadata))
        
        token_manager = StandardJWTTokenManager(redis_client)
        
        # Test standard JWT payload creation and validation
        test_scenarios = [
            {
                'name': 'admin_user_token',
                'user_id': 'jwt-admin-001',
                'email': 'admin@netra.ai',
                'permissions': ['admin', 'read', 'write', 'delete'],
                'session_id': 'admin-session-001'
            },
            {
                'name': 'regular_user_token',
                'user_id': 'jwt-user-001',
                'email': 'user@example.com',
                'permissions': ['read', 'write'],
                'session_id': 'user-session-001'
            },
            {
                'name': 'readonly_user_token',
                'user_id': 'jwt-readonly-001',
                'email': 'readonly@example.com',
                'permissions': ['read'],
                'session_id': None  # No session for readonly
            }
        ]
        
        created_tokens = []
        
        for scenario in test_scenarios:
            # Create token with standard structure
            token = token_manager.create_standard_token(
                user_id=scenario['user_id'],
                email=scenario['email'],
                permissions=scenario['permissions'],
                session_id=scenario['session_id']
            )
            
            # Validate token structure
            validated_payload = token_manager.validate_token_structure(token)
            assert validated_payload is not None, f"Token validation failed for {scenario['name']}"
            
            # Validate standard claims
            assert validated_payload.sub == scenario['user_id'], f"Subject mismatch for {scenario['name']}"
            assert validated_payload.aud == token_manager.audience, f"Audience mismatch for {scenario['name']}"
            assert validated_payload.iss == token_manager.issuer, f"Issuer mismatch for {scenario['name']}"
            assert validated_payload.exp > validated_payload.iat, f"Expiry must be after issuance for {scenario['name']}"
            
            # Validate extended claims
            assert validated_payload.email == scenario['email'], f"Email mismatch for {scenario['name']}"
            assert validated_payload.permissions == scenario['permissions'], f"Permissions mismatch for {scenario['name']}"
            assert validated_payload.session_id == scenario['session_id'], f"Session ID mismatch for {scenario['name']}"
            assert validated_payload.auth_method == "oauth", f"Auth method must be oauth for {scenario['name']}"
            
            # Store token metadata
            await token_manager.store_token_metadata(token, validated_payload)
            
            created_tokens.append({
                'scenario': scenario,
                'token': token,
                'payload': validated_payload
            })
        
        # Validate all tokens can be processed consistently
        for token_info in created_tokens:
            token = token_info['token']
            original_payload = token_info['payload']
            
            # Re-validate token
            revalidated_payload = token_manager.validate_token_structure(token)
            assert revalidated_payload is not None, "Token re-validation must succeed"
            
            # Ensure consistency
            assert revalidated_payload.sub == original_payload.sub, "Subject must remain consistent"
            assert revalidated_payload.email == original_payload.email, "Email must remain consistent"
            assert revalidated_payload.permissions == original_payload.permissions, "Permissions must remain consistent"
            assert revalidated_payload.exp == original_payload.exp, "Expiry must remain consistent"
        
        # Cleanup token metadata
        for token_info in created_tokens:
            if token_info['payload'].jti:
                await redis_client.delete(f"token_metadata:{token_info['payload'].jti}")


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_cross_service_validation_consistency(self, real_services_fixture):
        """
        Test that JWT validation is consistent between auth service and backend.
        
        BUSINESS CRITICAL: Cross-service JWT validation inconsistencies cause
        authentication failures and break user access to platform features.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock auth service JWT validator
        class AuthServiceJWTValidator:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.secret_key = "shared-jwt-secret-key"
                self.algorithm = "HS256"
                self.service_name = "auth_service"
            
            async def validate_jwt(self, token: TokenString) -> Optional[Dict[str, Any]]:
                """Validate JWT using auth service logic."""
                try:
                    # Decode without audience/issuer validation (more permissive)
                    decoded = jwt.decode(
                        str(token),
                        self.secret_key,
                        algorithms=[self.algorithm]
                    )
                    
                    # Auth service specific validation
                    current_time = int(time.time())
                    
                    # Check expiry
                    if decoded.get('exp', 0) <= current_time:
                        return None
                    
                    # Check required fields
                    if not decoded.get('sub') or not decoded.get('email'):
                        return None
                    
                    # Add validation metadata
                    decoded['validated_by'] = self.service_name
                    decoded['validated_at'] = current_time
                    
                    # Cache validation result
                    cache_key = f"auth_jwt_validation:{decoded['sub']}:{decoded.get('jti', 'no-jti')}"
                    await self.redis.setex(cache_key, 300, json.dumps(decoded))  # 5 min cache
                    
                    return decoded
                    
                except jwt.InvalidTokenError:
                    return None
        
        # Mock backend service JWT validator  
        class BackendServiceJWTValidator:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.secret_key = "shared-jwt-secret-key"
                self.algorithm = "HS256"
                self.service_name = "backend_service"
            
            async def validate_jwt(self, token: TokenString) -> Optional[Dict[str, Any]]:
                """Validate JWT using backend service logic."""
                try:
                    # Decode with strict validation
                    decoded = jwt.decode(
                        str(token),
                        self.secret_key,
                        algorithms=[self.algorithm]
                    )
                    
                    # Backend service specific validation
                    current_time = int(time.time())
                    
                    # Strict expiry check
                    if decoded.get('exp', 0) <= current_time:
                        return None
                    
                    # Strict field validation
                    required_fields = ['sub', 'email', 'permissions', 'iat', 'exp']
                    for field in required_fields:
                        if field not in decoded:
                            return None
                    
                    # Check cached auth service validation
                    cache_key = f"auth_jwt_validation:{decoded['sub']}:{decoded.get('jti', 'no-jti')}"
                    cached_validation = await self.redis.get(cache_key)
                    
                    if cached_validation:
                        cached_data = json.loads(cached_validation.decode())
                        # Use cached validation if it matches
                        if cached_data.get('sub') == decoded['sub'] and cached_data.get('exp') == decoded['exp']:
                            decoded['validated_by'] = f"{cached_data.get('validated_by')},{self.service_name}"
                            decoded['validated_at'] = current_time
                            return decoded
                    
                    # Independent validation
                    decoded['validated_by'] = self.service_name
                    decoded['validated_at'] = current_time
                    
                    return decoded
                    
                except jwt.InvalidTokenError:
                    return None
        
        auth_validator = AuthServiceJWTValidator(redis_client)
        backend_validator = BackendServiceJWTValidator(redis_client)
        
        # Create test JWT tokens
        current_time = int(time.time())
        test_tokens = []
        
        for i in range(3):
            payload = {
                'sub': f'cross-svc-user-{i:03d}',
                'email': f'user{i}@crossservice.test',
                'permissions': ['read', 'write'] if i % 2 == 0 else ['read'],
                'iat': current_time - 300,  # 5 minutes ago
                'exp': current_time + 3300,  # 55 minutes from now
                'jti': f'cross-svc-jwt-{i:03d}',
                'aud': 'netra-platform',
                'iss': 'netra-auth',
                'auth_method': 'oauth'
            }
            
            token = jwt.encode(payload, auth_validator.secret_key, algorithm=auth_validator.algorithm)
            test_tokens.append({
                'token': TokenString(token),
                'payload': payload,
                'user_id': payload['sub']
            })
        
        # Test cross-service validation consistency
        for token_info in test_tokens:
            token = token_info['token']
            expected_payload = token_info['payload']
            
            # Validate with auth service first
            auth_result = await auth_validator.validate_jwt(token)
            assert auth_result is not None, f"Auth service validation failed for {token_info['user_id']}"
            
            # Validate with backend service
            backend_result = await backend_validator.validate_jwt(token)
            assert backend_result is not None, f"Backend service validation failed for {token_info['user_id']}"
            
            # CRITICAL: Core claims must be identical between services
            core_claims = ['sub', 'email', 'permissions', 'iat', 'exp', 'jti']
            
            for claim in core_claims:
                auth_value = auth_result.get(claim)
                backend_value = backend_result.get(claim)
                
                assert auth_value == backend_value, (
                    f"Claim '{claim}' mismatch for {token_info['user_id']}: "
                    f"auth={auth_value}, backend={backend_value}"
                )
            
            # Validate both services see the same user
            assert auth_result['sub'] == backend_result['sub'], (
                f"Subject mismatch: auth={auth_result['sub']}, backend={backend_result['sub']}"
            )
            
            # Validate both services have same expiry understanding
            assert auth_result['exp'] == backend_result['exp'], (
                f"Expiry mismatch: auth={auth_result['exp']}, backend={backend_result['exp']}"
            )
            
            # Validate permissions are consistent
            assert auth_result['permissions'] == backend_result['permissions'], (
                f"Permissions mismatch: auth={auth_result['permissions']}, backend={backend_result['permissions']}"
            )
        
        # Test edge case: expired token
        expired_payload = {
            'sub': 'expired-user-001',
            'email': 'expired@test.com',
            'permissions': ['read'],
            'iat': current_time - 7200,  # 2 hours ago
            'exp': current_time - 3600,  # 1 hour ago (expired)
            'jti': 'expired-jwt-001'
        }
        
        expired_token = TokenString(jwt.encode(expired_payload, auth_validator.secret_key, algorithm=auth_validator.algorithm))
        
        # Both services must reject expired token
        auth_expired_result = await auth_validator.validate_jwt(expired_token)
        backend_expired_result = await backend_validator.validate_jwt(expired_token)
        
        assert auth_expired_result is None, "Auth service must reject expired token"
        assert backend_expired_result is None, "Backend service must reject expired token"
        
        # Cleanup cached validations
        for token_info in test_tokens:
            cache_key = f"auth_jwt_validation:{token_info['user_id']}:{token_info['payload']['jti']}"
            await redis_client.delete(cache_key)


    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_payload_type_safety_enforcement(self, real_services_fixture):
        """
        Test that JWT payload types are strictly enforced to prevent runtime errors.
        
        GOLDEN PATH CRITICAL: Type safety in JWT handling prevents runtime errors
        and ensures reliable authentication across the platform.
        """
        redis_client = real_services_fixture['redis']
        
        # Mock type-safe JWT processor
        class TypeSafeJWTProcessor:
            def __init__(self, redis_client):
                self.redis = redis_client
                self.secret_key = "type-safe-jwt-secret"
                self.algorithm = "HS256"
            
            def create_typed_jwt(self, user_id: UserID, session_id: SessionID, email: str, permissions: List[str]) -> TokenString:
                """Create JWT with strong typing enforcement."""
                current_time = int(time.time())
                
                # Enforce type safety
                assert isinstance(user_id, UserID), f"user_id must be UserID, got {type(user_id)}"
                assert isinstance(session_id, SessionID), f"session_id must be SessionID, got {type(session_id)}"
                assert isinstance(email, str), f"email must be str, got {type(email)}"
                assert isinstance(permissions, list), f"permissions must be list, got {type(permissions)}"
                assert all(isinstance(p, str) for p in permissions), "All permissions must be strings"
                
                payload = {
                    'sub': str(user_id),  # Convert to string for JWT
                    'session_id': str(session_id),  # Convert to string for JWT
                    'email': email,
                    'permissions': permissions,
                    'iat': current_time,
                    'exp': current_time + 3600,
                    'jti': f"typed-jwt-{str(user_id)}-{current_time}",
                    'type_safe': True  # Marker for type-safe tokens
                }
                
                token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
                return TokenString(token)
            
            def validate_typed_jwt(self, token: TokenString) -> Optional[Dict[str, Any]]:
                """Validate JWT with type safety enforcement."""
                try:
                    assert isinstance(token, TokenString), f"token must be TokenString, got {type(token)}"
                    
                    decoded = jwt.decode(str(token), self.secret_key, algorithms=[self.algorithm])
                    
                    # Enforce type safety on decoded payload
                    required_types = {
                        'sub': str,
                        'session_id': str,
                        'email': str,
                        'permissions': list,
                        'iat': int,
                        'exp': int,
                        'jti': str
                    }
                    
                    for field, expected_type in required_types.items():
                        if field not in decoded:
                            raise ValueError(f"Missing required field: {field}")
                        
                        actual_value = decoded[field]
                        if not isinstance(actual_value, expected_type):
                            raise ValueError(f"Field {field} must be {expected_type.__name__}, got {type(actual_value).__name__}")
                    
                    # Special validation for permissions list
                    permissions = decoded['permissions']
                    if not all(isinstance(p, str) for p in permissions):
                        raise ValueError("All permissions must be strings")
                    
                    # Check type-safe marker
                    if not decoded.get('type_safe', False):
                        raise ValueError("Token is not marked as type-safe")
                    
                    return decoded
                    
                except (jwt.InvalidTokenError, ValueError, AssertionError):
                    return None
            
            async def store_typed_token_data(self, token: TokenString, user_id: UserID, session_id: SessionID):
                """Store token data with type safety."""
                assert isinstance(token, TokenString), f"token must be TokenString"
                assert isinstance(user_id, UserID), f"user_id must be UserID"
                assert isinstance(session_id, SessionID), f"session_id must be SessionID"
                
                token_data = {
                    'user_id': str(user_id),
                    'session_id': str(session_id),
                    'token_created_at': time.time(),
                    'type_safe': True
                }
                
                key = f"typed_token:{str(user_id)}:{str(session_id)}"
                await self.redis.setex(key, 3600, json.dumps(token_data))
            
            async def get_typed_token_data(self, user_id: UserID, session_id: SessionID) -> Optional[Dict[str, Any]]:
                """Retrieve token data with type safety."""
                assert isinstance(user_id, UserID), f"user_id must be UserID"
                assert isinstance(session_id, SessionID), f"session_id must be SessionID"
                
                key = f"typed_token:{str(user_id)}:{str(session_id)}"
                data = await self.redis.get(key)
                
                if data:
                    return json.loads(data.decode())
                return None
        
        jwt_processor = TypeSafeJWTProcessor(redis_client)
        
        # Test type-safe JWT creation and validation
        test_users = [
            {
                'user_id': UserID('type-safe-user-001'),
                'session_id': SessionID('type-session-001'),
                'email': 'typesafe1@example.com',
                'permissions': ['read', 'write']
            },
            {
                'user_id': UserID('type-safe-user-002'),
                'session_id': SessionID('type-session-002'),
                'email': 'typesafe2@example.com',
                'permissions': ['admin', 'read', 'write', 'delete']
            },
            {
                'user_id': UserID('type-safe-user-003'),
                'session_id': SessionID('type-session-003'),
                'email': 'typesafe3@example.com',
                'permissions': ['read']
            }
        ]
        
        created_tokens = []
        
        for user_info in test_users:
            # Create type-safe JWT
            token = jwt_processor.create_typed_jwt(
                user_id=user_info['user_id'],
                session_id=user_info['session_id'],
                email=user_info['email'],
                permissions=user_info['permissions']
            )
            
            # Validate type-safe JWT
            validated_payload = jwt_processor.validate_typed_jwt(token)
            assert validated_payload is not None, f"Type-safe validation failed for {user_info['user_id']}"
            
            # Verify strong typing was preserved
            assert validated_payload['sub'] == str(user_info['user_id']), "User ID conversion error"
            assert validated_payload['session_id'] == str(user_info['session_id']), "Session ID conversion error"
            assert validated_payload['email'] == user_info['email'], "Email mismatch"
            assert validated_payload['permissions'] == user_info['permissions'], "Permissions mismatch"
            assert validated_payload['type_safe'] is True, "Type-safe marker missing"
            
            # Store token data
            await jwt_processor.store_typed_token_data(token, user_info['user_id'], user_info['session_id'])
            
            created_tokens.append({
                'user_info': user_info,
                'token': token,
                'payload': validated_payload
            })
        
        # Test type safety enforcement with invalid inputs
        with pytest.raises(AssertionError):
            # Invalid user_id type
            jwt_processor.create_typed_jwt(
                user_id="not-a-userid-type",  # Should be UserID
                session_id=SessionID('test-session'),
                email="test@example.com",
                permissions=["read"]
            )
        
        with pytest.raises(AssertionError):
            # Invalid session_id type
            jwt_processor.create_typed_jwt(
                user_id=UserID('test-user'),
                session_id="not-a-sessionid-type",  # Should be SessionID
                email="test@example.com",
                permissions=["read"]
            )
        
        with pytest.raises(AssertionError):
            # Invalid permissions type
            jwt_processor.create_typed_jwt(
                user_id=UserID('test-user'),
                session_id=SessionID('test-session'),
                email="test@example.com",
                permissions="not-a-list"  # Should be List[str]
            )
        
        # Test retrieval type safety
        for token_info in created_tokens:
            user_info = token_info['user_info']
            
            # Retrieve with correct types
            stored_data = await jwt_processor.get_typed_token_data(
                user_info['user_id'], 
                user_info['session_id']
            )
            
            assert stored_data is not None, f"Stored data retrieval failed for {user_info['user_id']}"
            assert stored_data['user_id'] == str(user_info['user_id']), "Stored user_id mismatch"
            assert stored_data['session_id'] == str(user_info['session_id']), "Stored session_id mismatch"
            assert stored_data['type_safe'] is True, "Type-safe marker missing in stored data"
        
        # Test retrieval type enforcement
        with pytest.raises(AssertionError):
            await jwt_processor.get_typed_token_data(
                "not-userid-type",  # Should be UserID
                SessionID('test-session')
            )
        
        with pytest.raises(AssertionError):
            await jwt_processor.get_typed_token_data(
                UserID('test-user'),
                "not-sessionid-type"  # Should be SessionID
            )
        
        # Cleanup
        for token_info in created_tokens:
            user_info = token_info['user_info']
            key = f"typed_token:{str(user_info['user_id'])}:{str(user_info['session_id'])}"
            await redis_client.delete(key)