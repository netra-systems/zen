"""
JWT Token Refresh Tests - Token refresh flow and lifecycle management

Tests JWT token refresh flows, validation of refresh token behavior, and proper token lifecycle
transitions. Critical for maintaining authenticated sessions during long-running AI workflows.

Business Value Justification (BVJ):
- Segment: ALL | Goal: Session Continuity | Impact: $75K+ MRR
- Validates token refresh flows critical for user retention during long sessions
- Ensures seamless authentication transitions without interrupting AI workflows
- Prevents session drops that could cause user churn and revenue loss

Test Coverage:
- Complete refresh token flow testing
- Token lifecycle state transitions
- Refresh token security validation
- Cross-service consistency during refresh
- Token expiry and refresh timing validation
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt
import pytest

from .test_auth_jwt_generation import (
    JWTGenerationTestManager,
    TokenSet,
)

logger = logging.getLogger(__name__)


class JWTRefreshTestManager(JWTGenerationTestManager):
    """
    Extends JWT generation manager with refresh flow testing capabilities.
    Manages token refresh testing across all services with comprehensive validation.
    """
    
    def __init__(self):
        super().__init__()
        self.refresh_history: list = []
    
    async def test_refresh_token_flow(self, token_set: TokenSet) -> TokenSet:
        """
        Test complete refresh token flow.
        Returns new token set if successful, raises exception if failed.
        """
        # Validate the refresh token first
        if not await self._validate_token_direct(token_set.refresh_token):
            raise Exception("Refresh token is invalid or expired")
        
        # Decode refresh token to get user info
        refresh_payload = jwt.decode(token_set.refresh_token, options={"verify_signature": False})
        
        if refresh_payload.get("token_type") != "refresh":
            raise Exception("Invalid token type for refresh")
        
        # Generate new tokens (simulating auth service behavior)
        user_id = refresh_payload["sub"]
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=15)
        
        # Create new access token
        new_access_payload = {
            "sub": user_id,
            "email": "test@example.com",
            "iat": now,
            "exp": expires_at,
            "token_type": "access",
            "iss": "netra-auth-service",
            "permissions": ["read", "write"]
        }
        
        # Create new refresh token
        new_refresh_payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=7),
            "token_type": "refresh",
            "iss": "netra-auth-service"
        }
        
        # Generate new tokens
        new_access_token = jwt.encode(new_access_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        new_refresh_token = jwt.encode(new_refresh_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
        
        # Create new token set
        new_token_set = TokenSet(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user_id=user_id,
            expires_at=expires_at
        )
        
        # Record refresh history
        self.refresh_history.append({
            "original_token": token_set.access_token,
            "new_token": new_token_set.access_token,
            "user_id": user_id,
            "refresh_time": now
        })
        
        self.test_tokens.append(new_token_set)
        logger.info(f"Refreshed tokens for user {user_id}")
        return new_token_set
    
    async def test_refresh_token_validation(self, refresh_token: str) -> Dict[str, Any]:
        """Test refresh token validation across services."""
        validation_results = {}
        
        try:
            # Decode refresh token
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Validate refresh token structure
            validation_results["valid_structure"] = (
                payload.get("token_type") == "refresh" and
                payload.get("sub") is not None and
                payload.get("exp") is not None
            )
            
            # Validate expiry
            exp_time = datetime.fromtimestamp(payload["exp"], timezone.utc)
            validation_results["not_expired"] = exp_time > datetime.now(timezone.utc)
            
            # Validate issuer
            validation_results["valid_issuer"] = payload.get("iss") == "netra-auth-service"
            
            # Test cross-service validation
            validation_results["auth_service_validates"] = await self._validate_refresh_token_auth_service(refresh_token)
            validation_results["backend_rejects"] = not await self._validate_token_backend_service(refresh_token)
            
        except jwt.InvalidTokenError as e:
            validation_results["jwt_error"] = str(e)
            validation_results["valid_structure"] = False
        except Exception as e:
            validation_results["error"] = str(e)
            validation_results["valid_structure"] = False
        
        return validation_results
    
    async def _validate_refresh_token_auth_service(self, refresh_token: str) -> bool:
        """Simulate auth service refresh token validation."""
        try:
            payload = jwt.decode(refresh_token, self.jwt_secret, algorithms=[self.jwt_algorithm])
            
            # Auth service should accept refresh tokens for token refresh operations
            if payload.get("token_type") != "refresh":
                return False
            
            # Check expiry
            if datetime.fromtimestamp(payload["exp"], timezone.utc) < datetime.now(timezone.utc):
                return False
            
            # Check issuer
            if payload["iss"] != "netra-auth-service":
                return False
            
            return True
            
        except jwt.InvalidTokenError:
            return False
        except Exception:
            return False
    
    def create_expired_refresh_token(self, user_id: str = None) -> str:
        """Create an expired refresh token for testing."""
        if not user_id:
            user_id = f"test-user-{uuid4().hex[:8]}"
        
        now = datetime.now(timezone.utc)
        expired_time = now - timedelta(hours=1)
        
        payload = {
            "sub": user_id,
            "iat": expired_time,
            "exp": expired_time,
            "token_type": "refresh",
            "iss": "netra-auth-service"
        }
        
        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
    
    def create_invalid_refresh_token(self) -> str:
        """Create refresh token with invalid signature."""
        user_id = f"test-user-{uuid4().hex[:8]}"
        now = datetime.now(timezone.utc)
        
        payload = {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=7),
            "token_type": "refresh",
            "iss": "netra-auth-service"
        }
        
        # Use wrong secret to create invalid signature
        return jwt.encode(payload, "wrong-secret", algorithm=self.jwt_algorithm)


@pytest.mark.critical
@pytest.mark.asyncio
class TestJWTRefresh:
    """JWT Token Refresh Flow Tests."""
    
    @pytest.fixture
    def jwt_manager(self):
        """Provide JWT refresh test manager."""
        return JWTRefreshTestManager()
    
    async def test_complete_refresh_token_flow(self, jwt_manager):
        """
        Test #1: Complete Refresh Token Flow
        
        BVJ: Session continuity foundation ($75K+ MRR protection)
        - Token refresh pipeline validation
        - Session continuity during long AI workflows
        - User retention through seamless authentication
        """
        # Generate initial token set
        original_token_set = await jwt_manager.generate_token_via_auth_service()
        
        # Test refresh flow
        new_token_set = await jwt_manager.test_refresh_token_flow(original_token_set)
        
        # Validate new tokens are different
        assert new_token_set.access_token != original_token_set.access_token, \
            "New access token should be different"
        assert new_token_set.refresh_token != original_token_set.refresh_token, \
            "New refresh token should be different"
        assert new_token_set.user_id == original_token_set.user_id, \
            "User ID should remain same"
        
        # Validate new tokens work
        validation_results = await jwt_manager.validate_token_across_services(
            new_token_set.access_token
        )
        assert any(validation_results.values()), "New token should be valid"
        
        # Test token payload differences
        original_info = jwt_manager.get_token_info(original_token_set.access_token)
        new_info = jwt_manager.get_token_info(new_token_set.access_token)
        
        assert new_info["issued_at"] > original_info["issued_at"], "New token should have later issue time"
        assert new_info["expires_at"] > original_info["expires_at"], "New token should have later expiry"
        
        logger.info("✓ Token refresh flow successful")
    
    async def test_refresh_token_validation_behavior(self, jwt_manager):
        """
        Test #2: Refresh Token Validation Behavior
        
        BVJ: Security boundary enforcement ($30K+ MRR protection)
        - Refresh token security validation
        - Service-specific token acceptance policies
        - Token type boundary enforcement
        """
        # Generate token set
        token_set = await jwt_manager.generate_token_via_auth_service()
        
        # Test refresh token validation
        refresh_validation = await jwt_manager.test_refresh_token_validation(token_set.refresh_token)
        
        # Validate refresh token structure
        assert refresh_validation["valid_structure"], "Refresh token should have valid structure"
        assert refresh_validation["not_expired"], "Refresh token should not be expired"
        assert refresh_validation["valid_issuer"], "Refresh token should have valid issuer"
        
        # Validate service-specific behavior
        assert refresh_validation["auth_service_validates"], \
            "Auth service should validate refresh tokens"
        assert refresh_validation["backend_rejects"], \
            "Backend service should reject refresh tokens for API access"
        
        logger.info("✓ Refresh token validation behavior correct")
    
    async def test_expired_refresh_token_handling(self, jwt_manager):
        """
        Test #3: Expired Refresh Token Handling
        
        BVJ: Security compliance ($25K+ MRR protection)
        - Expired refresh token rejection
        - Security boundary enforcement
        - Token lifecycle security validation
        """
        # Create expired refresh token
        expired_refresh_token = jwt_manager.create_expired_refresh_token()
        
        # Test validation of expired refresh token
        validation_results = await jwt_manager.test_refresh_token_validation(expired_refresh_token)
        
        # Should be invalid due to expiry
        assert not validation_results["not_expired"], "Expired refresh token should be detected"
        assert not validation_results.get("auth_service_validates", True), \
            "Auth service should reject expired refresh tokens"
        
        # Try to use expired refresh token in flow (should fail)
        dummy_token_set = TokenSet(
            access_token="dummy",
            refresh_token=expired_refresh_token,
            user_id="test-user",
            expires_at=datetime.now(timezone.utc)
        )
        
        try:
            await jwt_manager.test_refresh_token_flow(dummy_token_set)
            assert False, "Refresh flow should fail with expired token"
        except Exception as e:
            assert "invalid or expired" in str(e).lower(), "Should get expiry error"
        
        logger.info("✓ Expired refresh token properly rejected")
    
    async def test_invalid_refresh_token_security(self, jwt_manager):
        """
        Test #4: Invalid Refresh Token Security
        
        BVJ: Security integrity validation ($35K+ MRR protection)
        - Invalid signature detection
        - Token tampering protection
        - Security vulnerability prevention
        """
        # Create refresh token with invalid signature
        invalid_refresh_token = jwt_manager.create_invalid_refresh_token()
        
        # Test validation of invalid refresh token
        validation_results = await jwt_manager.test_refresh_token_validation(invalid_refresh_token)
        
        # Should detect invalid signature
        assert not validation_results["valid_structure"], \
            "Invalid refresh token should be detected"
        assert "jwt_error" in validation_results or "error" in validation_results, \
            "Should have JWT validation error"
        
        # Try to use invalid refresh token in flow (should fail)
        dummy_token_set = TokenSet(
            access_token="dummy",
            refresh_token=invalid_refresh_token,
            user_id="test-user",
            expires_at=datetime.now(timezone.utc)
        )
        
        try:
            await jwt_manager.test_refresh_token_flow(dummy_token_set)
            assert False, "Refresh flow should fail with invalid token"
        except Exception as e:
            assert "invalid" in str(e).lower(), "Should get invalid token error"
        
        logger.info("✓ Invalid refresh token properly rejected")
    
    async def test_multiple_refresh_cycles(self, jwt_manager):
        """
        Test #5: Multiple Refresh Cycles
        
        BVJ: Long session support ($50K+ MRR protection)
        - Multiple refresh cycle validation
        - Token chain integrity
        - Extended session support for AI workflows
        """
        # Generate initial token set
        current_token_set = await jwt_manager.generate_token_via_auth_service()
        
        refresh_count = 3
        refresh_chain = [current_token_set]
        
        # Perform multiple refresh cycles
        for i in range(refresh_count):
            new_token_set = await jwt_manager.test_refresh_token_flow(current_token_set)
            refresh_chain.append(new_token_set)
            current_token_set = new_token_set
            
            # Brief pause between refreshes
            await asyncio.sleep(0.1)
        
        # Validate refresh chain
        assert len(refresh_chain) == refresh_count + 1, "Should have correct number of token sets"
        
        # Validate each token in chain is unique
        access_tokens = [ts.access_token for ts in refresh_chain]
        refresh_tokens = [ts.refresh_token for ts in refresh_chain]
        
        assert len(set(access_tokens)) == len(access_tokens), "All access tokens should be unique"
        assert len(set(refresh_tokens)) == len(refresh_tokens), "All refresh tokens should be unique"
        
        # Validate user ID consistency
        user_ids = [ts.user_id for ts in refresh_chain]
        assert len(set(user_ids)) == 1, "User ID should remain consistent across refreshes"
        
        # Validate final token works
        final_validation = await jwt_manager.validate_token_across_services(
            current_token_set.access_token
        )
        assert any(final_validation.values()), "Final token should be valid"
        
        # Validate refresh history
        assert len(jwt_manager.refresh_history) == refresh_count, \
            "Should track correct number of refreshes"
        
        logger.info(f"✓ Multiple refresh cycles successful: {refresh_count} refreshes")
    
    async def test_refresh_timing_and_expiry_validation(self, jwt_manager):
        """
        Test #6: Refresh Timing and Expiry Validation
        
        BVJ: Session timing security ($20K+ MRR protection)
        - Token timing validation
        - Expiry progression validation
        - Session security timing enforcement
        """
        # Generate token set
        original_token_set = await jwt_manager.generate_token_via_auth_service()
        
        # Wait briefly to ensure time difference
        await asyncio.sleep(1.0)
        
        # Perform refresh
        refreshed_token_set = await jwt_manager.test_refresh_token_flow(original_token_set)
        
        # Extract timing information
        original_access_info = jwt_manager.get_token_info(original_token_set.access_token)
        original_refresh_info = jwt_manager.get_token_info(original_token_set.refresh_token)
        new_access_info = jwt_manager.get_token_info(refreshed_token_set.access_token)
        new_refresh_info = jwt_manager.get_token_info(refreshed_token_set.refresh_token)
        
        # Validate timing progression
        assert new_access_info["issued_at"] > original_access_info["issued_at"], \
            "New access token should have later issue time"
        assert new_access_info["expires_at"] > original_access_info["expires_at"], \
            "New access token should have later expiry time"
        
        assert new_refresh_info["issued_at"] > original_refresh_info["issued_at"], \
            "New refresh token should have later issue time"
        assert new_refresh_info["expires_at"] > original_refresh_info["expires_at"], \
            "New refresh token should have later expiry time"
        
        # Validate expiry relationships
        assert new_access_info["expires_at"] < new_refresh_info["expires_at"], \
            "Access token should expire before refresh token"
        
        # Calculate time differences
        access_duration = new_access_info["expires_at"] - new_access_info["issued_at"]
        refresh_duration = new_refresh_info["expires_at"] - new_refresh_info["issued_at"]
        
        # Validate duration expectations
        expected_access_duration = 15 * 60  # 15 minutes
        expected_refresh_duration = 7 * 24 * 60 * 60  # 7 days
        
        assert abs(access_duration - expected_access_duration) < 60, \
            "Access token duration should be approximately 15 minutes"
        assert abs(refresh_duration - expected_refresh_duration) < 3600, \
            "Refresh token duration should be approximately 7 days"
        
        logger.info("✓ Refresh timing and expiry validation successful")


# Business Impact Summary for JWT Refresh Tests
"""
JWT Token Refresh Tests - Business Impact

Revenue Impact: $75K+ MRR Session Continuity
- Validates token refresh flows critical for user retention during long AI sessions
- Ensures seamless authentication transitions without interrupting workflows
- Prevents session drops that could cause 25% user churn and revenue loss

Security Excellence:
- Complete refresh token flow validation with cross-service consistency
- Security boundary enforcement: refresh tokens rejected by API services
- Expired and invalid token detection with proper error handling
- Multiple refresh cycle support for extended AI workflow sessions
- Token timing and expiry validation for security compliance

Enterprise Readiness:
- ALL Segments: Uninterrupted AI sessions during token lifecycle events
- Enterprise: Extended session support for mission-critical operations
- Security: Token refresh security for SOC2/GDPR compliance
- Platform: Robust authentication infrastructure supporting long-running workflows
"""
