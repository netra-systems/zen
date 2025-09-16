"""
Auth Token Refresh Mechanism Integration Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Enable seamless session continuation without frequent re-authentication
- Value Impact: Users maintain authenticated sessions for extended periods, improving UX and engagement
- Strategic Impact: Core session management that reduces authentication friction and increases user retention

CRITICAL: These tests use REAL PostgreSQL and Redis services (no mocks).
Tests validate token refresh mechanisms with real service persistence and coordination.
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List
import jwt
import secrets

from shared.isolated_environment import get_env
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from auth_service.auth_core.config import AuthConfig
from auth_service.services.jwt_service import JWTService
from auth_service.services.redis_service import RedisService
from auth_service.services.token_refresh_service import TokenRefreshService
from auth_service.services.user_service import UserService
from auth_service.database import get_database


class TestTokenRefreshIntegration(BaseIntegrationTest):
    """Integration tests for token refresh mechanisms with real services."""
    
    @pytest.fixture(autouse=True)
    async def setup(self):
        """Set up test environment with real services."""
        self.env = get_env()
        self.auth_helper = E2EAuthHelper(environment="test")
        
        # Use real auth service configuration
        self.auth_config = AuthConfig()
        
        # Real service instances
        self.redis_service = RedisService(self.auth_config)
        await self.redis_service.connect()
        
        self.jwt_service = JWTService(self.auth_config)
        self.user_service = UserService(self.auth_config, get_database())
        self.token_refresh_service = TokenRefreshService(
            self.auth_config,
            self.jwt_service,
            self.redis_service,
            self.user_service
        )
        
        # Test user data
        self.test_user_data = {
            "user_id": "refresh-test-user-123",
            "email": "refresh-test@example.com",
            "name": "Token Refresh Test User",
            "permissions": ["read", "write"]
        }
        
        self.created_refresh_tokens = []  # Track for cleanup
        
        yield
        
        # Cleanup
        await self.cleanup_test_data()
    
    async def cleanup_test_data(self):
        """Clean up test data from real services."""
        try:
            # Clean refresh tokens from Redis
            refresh_keys = await self.redis_service.keys("refresh:*refresh-test*")
            if refresh_keys:
                await self.redis_service.delete(*refresh_keys)
            
            # Clean token blacklist entries
            blacklist_keys = await self.redis_service.keys("blacklist:*refresh-test*")
            if blacklist_keys:
                await self.redis_service.delete(*blacklist_keys)
                
            # Clean session data
            session_keys = await self.redis_service.keys("session:*refresh-test*")
            if session_keys:
                await self.redis_service.delete(*session_keys)
                
            await self.redis_service.close()
        except Exception as e:
            self.logger.warning(f"Cleanup warning: {e}")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_refresh_token_generation_and_storage(self):
        """
        Test refresh token generation and Redis storage.
        
        BVJ: Enables long-lived sessions through secure refresh token mechanism.
        """
        user_data = self.test_user_data
        
        # Generate refresh token
        refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        assert len(refresh_token) > 100  # Refresh tokens are long
        
        # Verify refresh token structure (should be JWT)
        parts = refresh_token.split('.')
        assert len(parts) == 3  # header.payload.signature
        
        # Decode refresh token to verify claims
        decoded = jwt.decode(
            refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        assert decoded["sub"] == user_data["user_id"]
        assert decoded["email"] == user_data["email"]
        assert decoded["type"] == "refresh"
        assert "exp" in decoded
        assert "iat" in decoded
        assert "jti" in decoded
        
        # Store refresh token in Redis
        refresh_key = f"refresh:{user_data['user_id']}:{decoded['jti']}"
        refresh_metadata = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "token_id": decoded["jti"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
            "device_info": "integration-test"
        }
        
        await self.redis_service.set(
            refresh_key,
            json.dumps(refresh_metadata),
            ex=2592000  # 30 days
        )
        
        self.created_refresh_tokens.append(refresh_key)
        
        # Verify storage in Redis
        stored_metadata = await self.redis_service.get(refresh_key)
        assert stored_metadata is not None
        
        metadata = json.loads(stored_metadata)
        assert metadata["user_id"] == user_data["user_id"]
        assert metadata["email"] == user_data["email"]
        assert metadata["is_active"] is True
        assert metadata["token_id"] == decoded["jti"]
        
        # Verify TTL
        ttl = await self.redis_service.ttl(refresh_key)
        assert ttl > 2591000  # Close to 30 days
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_access_token_refresh_flow(self):
        """
        Test complete access token refresh using refresh token.
        
        BVJ: Users can extend their sessions without re-entering credentials.
        """
        user_data = self.test_user_data
        
        # Step 1: Create original access token (short-lived)
        original_access_token = await self.jwt_service.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"],
            expires_delta=timedelta(minutes=5)  # Short-lived
        )
        
        # Step 2: Create refresh token (long-lived)
        refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        
        # Step 3: Store refresh token metadata in Redis
        decoded_refresh = jwt.decode(
            refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        refresh_key = f"refresh:{user_data['user_id']}:{decoded_refresh['jti']}"
        refresh_metadata = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "token_id": decoded_refresh["jti"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "is_active": True,
            "original_access_token_jti": jwt.decode(
                original_access_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )["jti"]
        }
        
        await self.redis_service.set(
            refresh_key,
            json.dumps(refresh_metadata),
            ex=2592000
        )
        
        self.created_refresh_tokens.append(refresh_key)
        
        # Step 4: Use refresh token to get new access token
        new_access_token = await self.token_refresh_service.refresh_access_token(
            refresh_token=refresh_token,
            user_id=user_data["user_id"],
            permissions=user_data["permissions"]
        )
        
        assert new_access_token is not None
        assert new_access_token != original_access_token  # Should be different
        
        # Step 5: Verify new access token is valid and has correct claims
        new_token_valid = await self.jwt_service.validate_token(new_access_token)
        assert new_token_valid is True
        
        decoded_new = jwt.decode(
            new_access_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        assert decoded_new["sub"] == user_data["user_id"]
        assert decoded_new["email"] == user_data["email"]
        assert decoded_new["permissions"] == user_data["permissions"]
        assert decoded_new["type"] == "access"
        
        # Step 6: Update refresh token metadata with usage info
        updated_metadata = {
            **refresh_metadata,
            "last_used": datetime.now(timezone.utc).isoformat(),
            "usage_count": 1,
            "latest_access_token_jti": decoded_new["jti"]
        }
        
        await self.redis_service.set(
            refresh_key,
            json.dumps(updated_metadata),
            ex=2592000
        )
        
        # Verify refresh token is still active and updated
        stored_updated = await self.redis_service.get(refresh_key)
        updated_data = json.loads(stored_updated)
        assert updated_data["usage_count"] == 1
        assert "last_used" in updated_data
        assert updated_data["latest_access_token_jti"] == decoded_new["jti"]
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_refresh_token_validation_and_security(self):
        """
        Test refresh token validation and security measures.
        
        BVJ: Ensures refresh tokens cannot be abused and maintain security standards.
        """
        user_data = self.test_user_data
        
        # Create valid refresh token
        valid_refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        
        decoded_valid = jwt.decode(
            valid_refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        # Store in Redis
        refresh_key = f"refresh:{user_data['user_id']}:{decoded_valid['jti']}"
        await self.redis_service.set(
            refresh_key,
            json.dumps({
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat()
            }),
            ex=2592000
        )
        
        self.created_refresh_tokens.append(refresh_key)
        
        # Test 1: Valid refresh token should validate
        is_valid = await self.token_refresh_service.validate_refresh_token(
            refresh_token=valid_refresh_token,
            user_id=user_data["user_id"]
        )
        assert is_valid is True
        
        # Test 2: Invalid signature should fail
        tampered_token = valid_refresh_token[:-10] + "tamperedsig"
        
        with pytest.raises(jwt.InvalidSignatureError):
            await self.token_refresh_service.validate_refresh_token(
                refresh_token=tampered_token,
                user_id=user_data["user_id"]
            )
        
        # Test 3: Wrong user ID should fail
        wrong_user_valid = await self.token_refresh_service.validate_refresh_token(
            refresh_token=valid_refresh_token,
            user_id="wrong-user-id"
        )
        assert wrong_user_valid is False
        
        # Test 4: Expired token should fail
        expired_refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            expires_delta=timedelta(seconds=1)  # Expires in 1 second
        )
        
        # Wait for expiry
        await asyncio.sleep(2)
        
        with pytest.raises(jwt.ExpiredSignatureError):
            await self.token_refresh_service.validate_refresh_token(
                refresh_token=expired_refresh_token,
                user_id=user_data["user_id"]
            )
        
        # Test 5: Inactive token (disabled in Redis) should fail
        await self.redis_service.set(
            refresh_key,
            json.dumps({
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "is_active": False,  # Deactivated
                "deactivated_at": datetime.now(timezone.utc).isoformat(),
                "reason": "security_policy"
            }),
            ex=2592000
        )
        
        inactive_valid = await self.token_refresh_service.validate_refresh_token(
            refresh_token=valid_refresh_token,
            user_id=user_data["user_id"]
        )
        assert inactive_valid is False
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_refresh_token_rotation_security(self):
        """
        Test refresh token rotation for enhanced security.
        
        BVJ: Provides enhanced security through token rotation, reducing attack surface.
        """
        user_data = self.test_user_data
        
        # Create initial refresh token
        initial_refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        
        initial_decoded = jwt.decode(
            initial_refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        # Store initial token
        initial_key = f"refresh:{user_data['user_id']}:{initial_decoded['jti']}"
        await self.redis_service.set(
            initial_key,
            json.dumps({
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "generation": 1
            }),
            ex=2592000
        )
        
        self.created_refresh_tokens.append(initial_key)
        
        # Perform token rotation (use refresh token and get new one)
        rotation_result = await self.token_refresh_service.rotate_refresh_token(
            current_refresh_token=initial_refresh_token,
            user_id=user_data["user_id"],
            permissions=user_data["permissions"]
        )
        
        assert rotation_result is not None
        assert "access_token" in rotation_result
        assert "refresh_token" in rotation_result
        
        new_access_token = rotation_result["access_token"]
        new_refresh_token = rotation_result["refresh_token"]
        
        # Verify new tokens are different
        assert new_access_token != initial_refresh_token
        assert new_refresh_token != initial_refresh_token
        assert new_refresh_token != new_access_token
        
        # Verify old refresh token is invalidated
        old_token_valid = await self.token_refresh_service.validate_refresh_token(
            refresh_token=initial_refresh_token,
            user_id=user_data["user_id"]
        )
        assert old_token_valid is False
        
        # Verify old token is marked as rotated in Redis
        old_token_data = await self.redis_service.get(initial_key)
        if old_token_data:
            old_metadata = json.loads(old_token_data)
            assert old_metadata.get("is_active") is False
            assert old_metadata.get("rotation_reason") == "token_rotated"
        
        # Verify new refresh token works
        new_decoded = jwt.decode(
            new_refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        new_key = f"refresh:{user_data['user_id']}:{new_decoded['jti']}"
        new_token_valid = await self.token_refresh_service.validate_refresh_token(
            refresh_token=new_refresh_token,
            user_id=user_data["user_id"]
        )
        assert new_token_valid is True
        
        self.created_refresh_tokens.append(new_key)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_refresh_operations(self):
        """
        Test concurrent refresh token operations for multi-user system.
        
        BVJ: Ensures system can handle multiple simultaneous token refreshes without conflicts.
        """
        # Create multiple users for concurrent testing
        concurrent_users = [
            {
                "user_id": f"concurrent-refresh-user-{i}",
                "email": f"concurrent-refresh-{i}@example.com",
                "permissions": ["read", "write"]
            }
            for i in range(3)
        ]
        
        # Create refresh tokens for all users
        user_tokens = {}
        for user_data in concurrent_users:
            refresh_token = await self.jwt_service.create_refresh_token(
                user_id=user_data["user_id"],
                email=user_data["email"]
            )
            
            # Store in Redis
            decoded = jwt.decode(
                refresh_token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            refresh_key = f"refresh:{user_data['user_id']}:{decoded['jti']}"
            await self.redis_service.set(
                refresh_key,
                json.dumps({
                    "user_id": user_data["user_id"],
                    "email": user_data["email"],
                    "is_active": True,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }),
                ex=2592000
            )
            
            user_tokens[user_data["user_id"]] = {
                "refresh_token": refresh_token,
                "refresh_key": refresh_key,
                "user_data": user_data
            }
            self.created_refresh_tokens.append(refresh_key)
        
        async def refresh_user_token(user_info):
            """Refresh token for a single user."""
            user_data = user_info["user_data"]
            refresh_token = user_info["refresh_token"]
            
            try:
                new_access_token = await self.token_refresh_service.refresh_access_token(
                    refresh_token=refresh_token,
                    user_id=user_data["user_id"],
                    permissions=user_data["permissions"]
                )
                
                # Validate new token
                is_valid = await self.jwt_service.validate_token(new_access_token)
                
                return {
                    "user_id": user_data["user_id"],
                    "success": True,
                    "new_token": new_access_token,
                    "token_valid": is_valid
                }
            except Exception as e:
                return {
                    "user_id": user_data["user_id"],
                    "success": False,
                    "error": str(e)
                }
        
        # Execute concurrent refresh operations
        tasks = [refresh_user_token(user_info) for user_info in user_tokens.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify all refresh operations succeeded
        successful_refreshes = [r for r in results if not isinstance(r, Exception) and r.get("success")]
        failed_refreshes = [r for r in results if isinstance(r, Exception) or not r.get("success")]
        
        assert len(successful_refreshes) == len(concurrent_users)
        assert len(failed_refreshes) == 0
        
        # Verify each new token is unique and valid
        new_tokens = []
        for result in successful_refreshes:
            assert result["token_valid"] is True
            assert result["new_token"] is not None
            assert result["new_token"] not in new_tokens  # Ensure uniqueness
            new_tokens.append(result["new_token"])
        
        # Verify all users have different tokens
        assert len(set(new_tokens)) == len(concurrent_users)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_refresh_token_family_tracking(self):
        """
        Test refresh token family tracking for security audit.
        
        BVJ: Enables security monitoring and detection of token abuse patterns.
        """
        user_data = self.test_user_data
        
        # Create initial refresh token (generation 1)
        gen1_refresh_token = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"]
        )
        
        gen1_decoded = jwt.decode(
            gen1_refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        # Store with family tracking
        gen1_key = f"refresh:{user_data['user_id']}:{gen1_decoded['jti']}"
        gen1_metadata = {
            "user_id": user_data["user_id"],
            "email": user_data["email"],
            "is_active": True,
            "family_id": f"family-{secrets.token_hex(8)}",
            "generation": 1,
            "parent_token_id": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "device_fingerprint": "integration-test-device"
        }
        
        await self.redis_service.set(
            gen1_key,
            json.dumps(gen1_metadata),
            ex=2592000
        )
        
        self.created_refresh_tokens.append(gen1_key)
        
        # Rotate token (generation 2)
        gen2_rotation = await self.token_refresh_service.rotate_refresh_token(
            current_refresh_token=gen1_refresh_token,
            user_id=user_data["user_id"],
            permissions=user_data["permissions"]
        )
        
        gen2_refresh_token = gen2_rotation["refresh_token"]
        gen2_decoded = jwt.decode(
            gen2_refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        # Update generation 2 metadata with family tracking
        gen2_key = f"refresh:{user_data['user_id']}:{gen2_decoded['jti']}"
        gen2_metadata = {
            **gen1_metadata,
            "generation": 2,
            "parent_token_id": gen1_decoded["jti"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rotation_from": gen1_key
        }
        
        await self.redis_service.set(
            gen2_key,
            json.dumps(gen2_metadata),
            ex=2592000
        )
        
        self.created_refresh_tokens.append(gen2_key)
        
        # Rotate again (generation 3)
        gen3_rotation = await self.token_refresh_service.rotate_refresh_token(
            current_refresh_token=gen2_refresh_token,
            user_id=user_data["user_id"],
            permissions=user_data["permissions"]
        )
        
        gen3_refresh_token = gen3_rotation["refresh_token"]
        gen3_decoded = jwt.decode(
            gen3_refresh_token,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        gen3_key = f"refresh:{user_data['user_id']}:{gen3_decoded['jti']}"
        gen3_metadata = {
            **gen2_metadata,
            "generation": 3,
            "parent_token_id": gen2_decoded["jti"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "rotation_from": gen2_key
        }
        
        await self.redis_service.set(
            gen3_key,
            json.dumps(gen3_metadata),
            ex=2592000
        )
        
        self.created_refresh_tokens.append(gen3_key)
        
        # Verify family tracking
        family_tokens = []
        for key in [gen1_key, gen2_key, gen3_key]:
            token_data = await self.redis_service.get(key)
            if token_data:
                metadata = json.loads(token_data)
                family_tokens.append(metadata)
        
        # Verify family relationships
        assert len(family_tokens) == 3
        
        # All tokens should have same family_id and user_id
        family_id = family_tokens[0]["family_id"]
        for token_metadata in family_tokens:
            assert token_metadata["family_id"] == family_id
            assert token_metadata["user_id"] == user_data["user_id"]
        
        # Verify generation progression
        generations = [token["generation"] for token in family_tokens]
        assert generations == [1, 2, 3]
        
        # Verify parent-child relationships
        gen1_token = next(t for t in family_tokens if t["generation"] == 1)
        gen2_token = next(t for t in family_tokens if t["generation"] == 2)
        gen3_token = next(t for t in family_tokens if t["generation"] == 3)
        
        assert gen1_token["parent_token_id"] is None  # Root token
        assert gen2_token["parent_token_id"] == gen1_decoded["jti"]
        assert gen3_token["parent_token_id"] == gen2_decoded["jti"]
        
        # Only latest generation should be active
        assert gen1_token.get("is_active") is False  # Rotated out
        assert gen2_token.get("is_active") is False  # Rotated out
        # gen3_token should be active (implied by successful validation)
        
        # Verify latest token is still functional
        gen3_valid = await self.token_refresh_service.validate_refresh_token(
            refresh_token=gen3_refresh_token,
            user_id=user_data["user_id"]
        )
        assert gen3_valid is True
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_refresh_token_cleanup_and_expiry(self):
        """
        Test refresh token cleanup and expiry management.
        
        BVJ: Maintains system performance and security by properly managing token lifecycle.
        """
        user_data = self.test_user_data
        
        # Create refresh token with short expiry for testing
        short_lived_refresh = await self.jwt_service.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            expires_delta=timedelta(seconds=5)  # 5 seconds
        )
        
        decoded_short = jwt.decode(
            short_lived_refresh,
            self.auth_config.jwt_secret_key,
            algorithms=[self.auth_config.jwt_algorithm]
        )
        
        # Store in Redis with matching expiry
        short_key = f"refresh:{user_data['user_id']}:{decoded_short['jti']}"
        await self.redis_service.set(
            short_key,
            json.dumps({
                "user_id": user_data["user_id"],
                "email": user_data["email"],
                "is_active": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()
            }),
            ex=5  # Redis expiry matches token expiry
        )
        
        # Token should be valid initially
        initially_valid = await self.token_refresh_service.validate_refresh_token(
            refresh_token=short_lived_refresh,
            user_id=user_data["user_id"]
        )
        assert initially_valid is True
        
        # Redis key should exist
        stored_data = await self.redis_service.get(short_key)
        assert stored_data is not None
        
        # Wait for expiry
        await asyncio.sleep(6)
        
        # Token should now be expired
        with pytest.raises(jwt.ExpiredSignatureError):
            await self.token_refresh_service.validate_refresh_token(
                refresh_token=short_lived_refresh,
                user_id=user_data["user_id"]
            )
        
        # Redis key should be automatically cleaned up
        expired_data = await self.redis_service.get(short_key)
        assert expired_data is None
        
        # Create multiple refresh tokens to test bulk cleanup
        cleanup_tokens = []
        for i in range(3):
            token = await self.jwt_service.create_refresh_token(
                user_id=f"{user_data['user_id']}-cleanup-{i}",
                email=f"cleanup-{i}@example.com",
                expires_delta=timedelta(seconds=2)
            )
            
            decoded = jwt.decode(
                token,
                self.auth_config.jwt_secret_key,
                algorithms=[self.auth_config.jwt_algorithm]
            )
            
            key = f"refresh:{user_data['user_id']}-cleanup-{i}:{decoded['jti']}"
            await self.redis_service.set(
                key,
                json.dumps({
                    "user_id": f"{user_data['user_id']}-cleanup-{i}",
                    "is_active": True,
                    "cleanup_test": True
                }),
                ex=2
            )
            
            cleanup_tokens.append(key)
        
        # Verify all tokens exist initially
        for key in cleanup_tokens:
            token_data = await self.redis_service.get(key)
            assert token_data is not None
        
        # Wait for cleanup
        await asyncio.sleep(3)
        
        # Verify all tokens are cleaned up
        for key in cleanup_tokens:
            token_data = await self.redis_service.get(key)
            assert token_data is None