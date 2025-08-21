"""
L4 Integration Test: Token Validation Chain Complete
Tests entire token validation chain including JWT, refresh tokens, and service tokens
"""

import pytest
import asyncio
import time
import jwt
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
import secrets

from netra_backend.app.services.token_service import TokenService
from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.services.redis_service import RedisService
from netra_backend.app.core.config import settings
from netra_backend.app.core.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    TokenRevokedError,
    TokenTamperError
)


class TestTokenValidationChainCompleteL4:
    """Complete token validation chain testing"""
    
    @pytest.fixture
    async def token_infrastructure(self):
        """Token infrastructure setup"""
        return {
            'token_service': TokenService(),
            'auth_service': AuthService(),
            'redis_service': RedisService(),
            'revoked_tokens': set(),
            'token_cache': {},
            'validation_metrics': {
                'attempts': 0,
                'successes': 0,
                'failures': 0,
                'tampering_detected': 0
            }
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_jwt_token_complete_lifecycle(self, token_infrastructure):
        """Test complete JWT token lifecycle from creation to expiry"""
        user_id = "user_jwt_lifecycle"
        
        # Create access token
        access_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            scopes=['read', 'write'],
            expires_in=2  # 2 seconds for quick test
        )
        
        # Immediate validation should succeed
        validation = await token_infrastructure['token_service'].validate_token(access_token)
        assert validation['valid']
        assert validation['user_id'] == user_id
        assert set(validation['scopes']) == {'read', 'write'}
        
        # Token should be cached
        cache_key = f"token_valid:{hashlib.sha256(access_token.encode()).hexdigest()}"
        cached = await token_infrastructure['redis_service'].get(cache_key)
        assert cached is not None
        
        # Wait for near expiry
        await asyncio.sleep(1.5)
        
        # Should still be valid but near expiry
        validation = await token_infrastructure['token_service'].validate_token(access_token)
        assert validation['valid']
        assert validation['near_expiry']
        
        # Wait for expiry
        await asyncio.sleep(1)
        
        # Should now be expired
        with pytest.raises(TokenExpiredError):
            await token_infrastructure['token_service'].validate_token(access_token)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_refresh_token_rotation(self, token_infrastructure):
        """Test refresh token rotation mechanism"""
        user_id = "user_refresh_rotation"
        
        # Create initial refresh token
        initial_refresh = await token_infrastructure['token_service'].create_refresh_token(
            user_id=user_id,
            device_id="device_1"
        )
        
        # Use refresh token to get new access token
        tokens1 = await token_infrastructure['token_service'].refresh_tokens(initial_refresh)
        assert 'access_token' in tokens1
        assert 'refresh_token' in tokens1
        assert tokens1['refresh_token'] != initial_refresh  # Should rotate
        
        # Old refresh token should be revoked
        with pytest.raises(TokenRevokedError):
            await token_infrastructure['token_service'].refresh_tokens(initial_refresh)
        
        # Use new refresh token
        tokens2 = await token_infrastructure['token_service'].refresh_tokens(tokens1['refresh_token'])
        assert tokens2['refresh_token'] != tokens1['refresh_token']
        
        # Previous refresh token should also be revoked
        with pytest.raises(TokenRevokedError):
            await token_infrastructure['token_service'].refresh_tokens(tokens1['refresh_token'])
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_tampering_detection(self, token_infrastructure):
        """Test detection of tampered tokens"""
        user_id = "user_tamper"
        
        # Create legitimate token
        legitimate_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            scopes=['read']
        )
        
        # Decode token (without verification)
        decoded = jwt.decode(legitimate_token, options={"verify_signature": False})
        
        # Tamper with payload
        decoded['scopes'] = ['read', 'write', 'admin']  # Elevation attempt
        decoded['user_id'] = 'admin_user'  # User ID change
        
        # Re-encode with wrong secret
        tampered_token = jwt.encode(decoded, 'wrong_secret', algorithm='HS256')
        
        # Should detect tampering
        with pytest.raises(TokenTamperError) as exc_info:
            await token_infrastructure['token_service'].validate_token(tampered_token)
        
        assert 'signature' in str(exc_info.value).lower()
        
        # Track tampering attempt
        token_infrastructure['validation_metrics']['tampering_detected'] += 1
        assert token_infrastructure['validation_metrics']['tampering_detected'] > 0
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_service_to_service_token_validation(self, token_infrastructure):
        """Test service-to-service authentication tokens"""
        service_id = "api_gateway"
        target_service = "user_service"
        
        # Create service token
        service_token = await token_infrastructure['token_service'].create_service_token(
            service_id=service_id,
            target_service=target_service,
            expires_in=300,
            permissions=['user.read', 'user.list']
        )
        
        # Validate service token
        validation = await token_infrastructure['token_service'].validate_service_token(
            token=service_token,
            expected_service=service_id,
            required_permissions=['user.read']
        )
        
        assert validation['valid']
        assert validation['service_id'] == service_id
        assert validation['target_service'] == target_service
        assert 'user.read' in validation['permissions']
        
        # Should fail with wrong service
        with pytest.raises(InvalidTokenError):
            await token_infrastructure['token_service'].validate_service_token(
                token=service_token,
                expected_service="wrong_service",
                required_permissions=['user.read']
            )
        
        # Should fail with insufficient permissions
        with pytest.raises(InvalidTokenError):
            await token_infrastructure['token_service'].validate_service_token(
                token=service_token,
                expected_service=service_id,
                required_permissions=['user.delete']  # Not granted
            )
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_revocation_propagation(self, token_infrastructure):
        """Test token revocation propagation across services"""
        user_id = "user_revoke"
        
        # Create multiple tokens for same user
        tokens = []
        for i in range(5):
            token = await token_infrastructure['token_service'].create_access_token(
                user_id=user_id,
                session_id=f"session_{i}"
            )
            tokens.append(token)
        
        # All should be valid initially
        for token in tokens:
            validation = await token_infrastructure['token_service'].validate_token(token)
            assert validation['valid']
        
        # Revoke all tokens for user
        await token_infrastructure['token_service'].revoke_all_user_tokens(user_id)
        
        # All should now be revoked
        for token in tokens:
            with pytest.raises(TokenRevokedError):
                await token_infrastructure['token_service'].validate_token(token)
        
        # Revocation should be in Redis blacklist
        for token in tokens:
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            blacklisted = await token_infrastructure['redis_service'].sismember(
                "token_blacklist",
                token_hash
            )
            assert blacklisted
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_validation_under_concurrent_load(self, token_infrastructure):
        """Test token validation under concurrent load"""
        user_id = "user_concurrent"
        
        # Create token
        token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            expires_in=60
        )
        
        # Concurrent validation attempts
        async def validate_token():
            try:
                result = await token_infrastructure['token_service'].validate_token(token)
                return result['valid']
            except Exception:
                return False
        
        # Launch 100 concurrent validations
        validation_tasks = [
            asyncio.create_task(validate_token())
            for _ in range(100)
        ]
        
        results = await asyncio.gather(*validation_tasks)
        
        # All should succeed
        assert all(results)
        
        # Cache should prevent database overload
        cache_hits = await token_infrastructure['redis_service'].get("token_cache_hits")
        assert int(cache_hits or 0) > 50  # Most should hit cache
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_scope_enforcement(self, token_infrastructure):
        """Test token scope enforcement at validation"""
        user_id = "user_scopes"
        
        # Create tokens with different scopes
        read_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            scopes=['read']
        )
        
        write_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            scopes=['read', 'write']
        )
        
        admin_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            scopes=['read', 'write', 'admin']
        )
        
        # Test scope validation
        # Read token should only allow read
        validation = await token_infrastructure['token_service'].validate_token_with_scope(
            token=read_token,
            required_scope='read'
        )
        assert validation['valid']
        
        with pytest.raises(InvalidTokenError) as exc_info:
            await token_infrastructure['token_service'].validate_token_with_scope(
                token=read_token,
                required_scope='write'
            )
        assert 'insufficient scope' in str(exc_info.value).lower()
        
        # Write token should allow read and write
        for scope in ['read', 'write']:
            validation = await token_infrastructure['token_service'].validate_token_with_scope(
                token=write_token,
                required_scope=scope
            )
            assert validation['valid']
        
        # Admin token should allow all
        for scope in ['read', 'write', 'admin']:
            validation = await token_infrastructure['token_service'].validate_token_with_scope(
                token=admin_token,
                required_scope=scope
            )
            assert validation['valid']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_validation_with_audience_claim(self, token_infrastructure):
        """Test token validation with audience claim verification"""
        user_id = "user_audience"
        
        # Create tokens for different audiences
        web_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            audience='web_app'
        )
        
        mobile_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            audience='mobile_app'
        )
        
        api_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            audience='api'
        )
        
        # Validate with correct audience
        web_validation = await token_infrastructure['token_service'].validate_token(
            token=web_token,
            expected_audience='web_app'
        )
        assert web_validation['valid']
        
        # Validate with wrong audience should fail
        with pytest.raises(InvalidTokenError) as exc_info:
            await token_infrastructure['token_service'].validate_token(
                token=web_token,
                expected_audience='mobile_app'
            )
        assert 'audience' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_chain_validation(self, token_infrastructure):
        """Test validation of chained tokens (parent-child relationship)"""
        user_id = "user_chain"
        
        # Create parent token
        parent_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            token_id="parent_1",
            scopes=['read', 'write']
        )
        
        # Create child token derived from parent
        child_token = await token_infrastructure['token_service'].create_derived_token(
            parent_token=parent_token,
            token_id="child_1",
            scopes=['read'],  # Reduced scope
            expires_in=60
        )
        
        # Both should be valid
        parent_valid = await token_infrastructure['token_service'].validate_token(parent_token)
        child_valid = await token_infrastructure['token_service'].validate_token(child_token)
        
        assert parent_valid['valid']
        assert child_valid['valid']
        assert child_valid['parent_token_id'] == "parent_1"
        
        # Revoking parent should invalidate child
        await token_infrastructure['token_service'].revoke_token(parent_token)
        
        # Parent should be revoked
        with pytest.raises(TokenRevokedError):
            await token_infrastructure['token_service'].validate_token(parent_token)
        
        # Child should also be revoked (chain invalidation)
        with pytest.raises(TokenRevokedError):
            await token_infrastructure['token_service'].validate_token(child_token)
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_validation_with_ip_binding(self, token_infrastructure):
        """Test token validation with IP address binding"""
        user_id = "user_ip_bound"
        original_ip = "192.168.1.100"
        different_ip = "192.168.1.200"
        
        # Create IP-bound token
        bound_token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            bind_to_ip=original_ip,
            strict_ip_check=True
        )
        
        # Validation from same IP should succeed
        validation = await token_infrastructure['token_service'].validate_token(
            token=bound_token,
            request_ip=original_ip
        )
        assert validation['valid']
        
        # Validation from different IP should fail
        with pytest.raises(InvalidTokenError) as exc_info:
            await token_infrastructure['token_service'].validate_token(
                token=bound_token,
                request_ip=different_ip
            )
        assert 'ip mismatch' in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_token_validation_cache_invalidation(self, token_infrastructure):
        """Test token validation cache invalidation on revocation"""
        user_id = "user_cache_invalidation"
        
        # Create token
        token = await token_infrastructure['token_service'].create_access_token(
            user_id=user_id,
            expires_in=300
        )
        
        # First validation (caches result)
        validation1 = await token_infrastructure['token_service'].validate_token(token)
        assert validation1['valid']
        
        # Verify it's cached
        cache_key = f"token_valid:{hashlib.sha256(token.encode()).hexdigest()}"
        cached = await token_infrastructure['redis_service'].get(cache_key)
        assert cached is not None
        
        # Revoke token
        await token_infrastructure['token_service'].revoke_token(token)
        
        # Cache should be invalidated
        cached_after = await token_infrastructure['redis_service'].get(cache_key)
        assert cached_after is None
        
        # Validation should now fail
        with pytest.raises(TokenRevokedError):
            await token_infrastructure['token_service'].validate_token(token)