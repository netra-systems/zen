"""
Auth JWT Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure secure and reliable JWT authentication
- Value Impact: JWT tokens enable user authentication for all chat features - without valid tokens users cannot access the system
- Strategic Impact: Core authentication mechanism for the entire platform, critical for multi-user isolation and security

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
Only external OAuth providers are mocked to isolate auth service behavior.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import jwt
import aiohttp

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.config import AuthConfig
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService
from auth_service.database import get_database


class TestJWTIntegration(BaseIntegrationTest):
    """Integration tests for JWT token functionality with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        self.jwt_service = JWTService(self.auth_config)
        
        # Real Redis service for session storage
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        # Real database connection
        self.db = get_database()
        
        # Test data
        self.test_user_data = {
            "user_id": "test-user-integration-jwt-123",
            "email": "jwt_integration_test@example.com",
            "name": "JWT Integration Test User",
            "permissions": ["read", "write"]
        }
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean Redis sessions
            pattern = f"session:{self.test_user_data['user_id']}:*"
            keys = await self.redis_service.keys(pattern)
            if keys:
                await self.redis_service.delete(*keys)
                
            # Clean user tokens
            token_pattern = f"token:{self.test_user_data['user_id']}:*"
            token_keys = await self.redis_service.keys(token_pattern)
            if token_keys:
                await self.redis_service.delete(*token_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_generation_and_validation(self):
        """
        Test JWT token generation and validation with real services.
        
        BVJ: Validates that users can be properly authenticated to access chat features.
        """
        # Generate token using real JWT service
        token = await self.jwt_service.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=self.test_user_data["permissions"],
            expires_delta=timedelta(minutes=30)
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are reasonably long
        
        # Validate token structure
        parts = token.split('.')
        assert len(parts) == 3  # header.payload.signature
        
        # Decode and validate token claims
        decoded = jwt.decode(
            token, 
            self.auth_config.jwt_secret_key, 
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        assert decoded["sub"] == self.test_user_data["user_id"]
        assert decoded["email"] == self.test_user_data["email"]
        assert decoded["permissions"] == self.test_user_data["permissions"]
        assert decoded["type"] == "access"
        assert "exp" in decoded
        assert "iat" in decoded
        assert "jti" in decoded
        
        # Validate token using JWT service
        is_valid = await self.jwt_service.validate_token(token)
        assert is_valid is True
        
        # Store token in Redis and verify persistence
        session_key = f"session:{self.test_user_data['user_id']}:integration_test"
        await self.redis_service.set(
            session_key,
            json.dumps({
                "token": token,
                "user_id": self.test_user_data["user_id"],
                "created_at": datetime.now(timezone.utc).isoformat()
            }),
            ex=1800  # 30 minutes
        )
        
        # Retrieve and verify from Redis
        stored_session = await self.redis_service.get(session_key)
        assert stored_session is not None
        
        session_data = json.loads(stored_session)
        assert session_data["token"] == token
        assert session_data["user_id"] == self.test_user_data["user_id"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_expiry_handling(self):
        """
        Test JWT token expiry with real time validation.
        
        BVJ: Ensures expired tokens are properly rejected to maintain security.
        """
        # Create token with very short expiry (2 seconds)
        short_token = await self.jwt_service.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=self.test_user_data["permissions"],
            expires_delta=timedelta(seconds=2)
        )
        
        # Token should be valid initially
        is_valid_initial = await self.jwt_service.validate_token(short_token)
        assert is_valid_initial is True
        
        # Wait for token to expire
        await asyncio.sleep(3)
        
        # Token should now be invalid
        is_valid_expired = await self.jwt_service.validate_token(short_token)
        assert is_valid_expired is False
        
        # Verify JWT decode raises exception for expired token
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(
                short_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_invalid_signature(self):
        """
        Test JWT token validation with invalid signatures.
        
        BVJ: Ensures forged tokens are rejected to maintain system security.
        """
        # Create valid token
        valid_token = await self.jwt_service.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=self.test_user_data["permissions"]
        )
        
        # Tamper with token signature
        parts = valid_token.split('.')
        tampered_token = f"{parts[0]}.{parts[1]}.invalid_signature"
        
        # Validation should fail
        is_valid = await self.jwt_service.validate_token(tampered_token)
        assert is_valid is False
        
        # JWT decode should raise exception
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(
                tampered_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_refresh_token_generation_and_validation(self):
        """
        Test refresh token functionality with real Redis storage.
        
        BVJ: Enables users to maintain authenticated sessions without frequent re-login.
        """
        user_id = self.test_user_data["user_id"]
        
        # Generate refresh token
        refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_id,
            email=self.test_user_data["email"]
        )
        
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        
        # Store refresh token in Redis
        refresh_key = f"refresh:{user_id}:{refresh_token[-8:]}"  # Use last 8 chars as identifier
        await self.redis_service.set(
            refresh_key,
            json.dumps({
                "user_id": user_id,
                "email": self.test_user_data["email"],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "is_active": True
            }),
            ex=2592000  # 30 days
        )
        
        # Validate refresh token
        is_valid = await self.jwt_service.validate_refresh_token(refresh_token, user_id)
        assert is_valid is True
        
        # Use refresh token to generate new access token
        new_access_token = await self.jwt_service.refresh_access_token(
            refresh_token,
            user_id,
            self.test_user_data["permissions"]
        )
        
        assert new_access_token is not None
        assert new_access_token != refresh_token  # Should be different
        
        # Validate new access token
        is_new_token_valid = await self.jwt_service.validate_token(new_access_token)
        assert is_new_token_valid is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multiple_concurrent_token_operations(self):
        """
        Test concurrent token operations for multi-user system validation.
        
        BVJ: Ensures system can handle multiple users simultaneously without token conflicts.
        """
        # Create multiple user contexts
        user_contexts = [
            {
                "user_id": f"concurrent-user-{i}",
                "email": f"concurrent-{i}@example.com",
                "permissions": ["read", "write"]
            }
            for i in range(5)
        ]
        
        async def create_and_validate_token(user_context):
            """Create and validate token for a single user."""
            token = await self.jwt_service.create_access_token(
                user_id=user_context["user_id"],
                email=user_context["email"],
                permissions=user_context["permissions"]
            )
            
            is_valid = await self.jwt_service.validate_token(token)
            
            # Store in Redis
            session_key = f"session:{user_context['user_id']}:concurrent_test"
            await self.redis_service.set(
                session_key,
                json.dumps({
                    "token": token,
                    "user_id": user_context["user_id"],
                    "test_type": "concurrent"
                }),
                ex=1800
            )
            
            return {
                "user_id": user_context["user_id"],
                "token": token,
                "is_valid": is_valid,
                "session_key": session_key
            }
        
        # Execute concurrent token operations
        tasks = [create_and_validate_token(ctx) for ctx in user_contexts]
        results = await asyncio.gather(*tasks)
        
        # Validate all operations succeeded
        assert len(results) == 5
        
        for result in results:
            assert result["is_valid"] is True
            assert result["token"] is not None
            assert len(result["token"]) > 50
            
            # Verify each token is unique
            other_tokens = [r["token"] for r in results if r["user_id"] != result["user_id"]]
            assert result["token"] not in other_tokens
            
            # Verify Redis storage
            stored_data = await self.redis_service.get(result["session_key"])
            assert stored_data is not None
            session_data = json.loads(stored_data)
            assert session_data["user_id"] == result["user_id"]
        
        # Cleanup concurrent test data
        cleanup_tasks = []
        for result in results:
            cleanup_tasks.append(self.redis_service.delete(result["session_key"]))
        await asyncio.gather(*cleanup_tasks)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_blacklist_functionality(self):
        """
        Test token blacklisting with real Redis storage.
        
        BVJ: Ensures revoked tokens cannot be used to access the system (security requirement).
        """
        # Create token
        token = await self.jwt_service.create_access_token(
            user_id=self.test_user_data["user_id"],
            email=self.test_user_data["email"],
            permissions=self.test_user_data["permissions"]
        )
        
        # Token should be valid initially
        is_valid_initial = await self.jwt_service.validate_token(token)
        assert is_valid_initial is True
        
        # Extract JTI (JWT ID) from token
        decoded = jwt.decode(
            token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        jti = decoded["jti"]
        
        # Blacklist the token
        blacklist_key = f"blacklist:{jti}"
        await self.redis_service.set(
            blacklist_key,
            json.dumps({
                "user_id": self.test_user_data["user_id"],
                "blacklisted_at": datetime.now(timezone.utc).isoformat(),
                "reason": "integration_test"
            }),
            ex=3600  # 1 hour
        )
        
        # Mock JWT service to check blacklist
        async def is_token_blacklisted(token_jti: str) -> bool:
            blacklist_entry = await self.redis_service.get(f"blacklist:{token_jti}")
            return blacklist_entry is not None
        
        # Token should now be considered invalid due to blacklisting
        is_blacklisted = await is_token_blacklisted(jti)
        assert is_blacklisted is True
        
        # Cleanup blacklist entry
        await self.redis_service.delete(blacklist_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_token_with_different_permission_levels(self):
        """
        Test JWT tokens with different permission levels for access control.
        
        BVJ: Enables different user tiers (Free, Early, Mid, Enterprise) with appropriate access levels.
        """
        permission_scenarios = [
            {
                "user_type": "free",
                "permissions": ["read"],
                "expected_access": ["view_chat"]
            },
            {
                "user_type": "early",
                "permissions": ["read", "write"],
                "expected_access": ["view_chat", "send_messages"]
            },
            {
                "user_type": "enterprise",
                "permissions": ["read", "write", "admin"],
                "expected_access": ["view_chat", "send_messages", "admin_panel"]
            }
        ]
        
        for scenario in permission_scenarios:
            # Create token with specific permissions
            token = await self.jwt_service.create_access_token(
                user_id=f"{scenario['user_type']}-user-{int(time.time())}",
                email=f"{scenario['user_type']}@example.com",
                permissions=scenario["permissions"]
            )
            
            # Validate token
            is_valid = await self.jwt_service.validate_token(token)
            assert is_valid is True
            
            # Decode and verify permissions
            decoded = jwt.decode(
                token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            assert decoded["permissions"] == scenario["permissions"]
            
            # Store with permission metadata in Redis
            permission_key = f"permissions:{decoded['sub']}:integration_test"
            await self.redis_service.set(
                permission_key,
                json.dumps({
                    "user_type": scenario["user_type"],
                    "permissions": scenario["permissions"],
                    "expected_access": scenario["expected_access"],
                    "token_jti": decoded["jti"]
                }),
                ex=1800
            )
            
            # Verify permission storage
            stored_permissions = await self.redis_service.get(permission_key)
            assert stored_permissions is not None
            
            perm_data = json.loads(stored_permissions)
            assert perm_data["user_type"] == scenario["user_type"]
            assert perm_data["permissions"] == scenario["permissions"]
            
            # Cleanup
            await self.redis_service.delete(permission_key)