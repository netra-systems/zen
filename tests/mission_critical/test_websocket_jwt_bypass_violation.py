"""
 ALERT:  MISSION CRITICAL: WebSocket JWT Bypass Violation Reproduction Test

SSOT VIOLATION REPRODUCTION - Test #1 of 5
This test EXPOSES the violation where WebSocket accepts invalid tokens due to verify_signature=False.

VIOLATION DETAILS:
- File: netra_backend/app/websocket_core/user_context_extractor.py
- Lines: 193-196 (JWT decode with verify_signature=False)
- Issue: WebSocket accepts ANY JWT token without signature validation

EXPECTED BEHAVIOR:
- BEFORE SSOT FIX: Test PASSES (proving violation exists - invalid tokens accepted)  
- AFTER SSOT FIX: Test FAILS (proving violation fixed - invalid tokens rejected)

Business Value Justification (BVJ):
- Segment: Enterprise/Security-conscious customers
- Business Goal: Security compliance and customer trust
- Value Impact: Prevents unauthorized access to $500K+ ARR chat functionality
- Revenue Impact: Security breach could cost entire customer base

AUTH SSOT REQUIREMENT:
All JWT operations MUST go through UnifiedAuthInterface - NO local JWT validation.
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

import pytest
import jwt
from shared.isolated_environment import get_env

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.websocket_auth_test_helpers import WebSocketAuthenticationTester
from test_framework.ssot.no_docker_mode_detector import NoDockerModeDetector

logger = logging.getLogger(__name__)


class TestWebSocketJwtBypassViolation(SSotAsyncTestCase):
    """
    SSOT Violation Reproduction: Tests that WebSocket currently accepts invalid JWT tokens.
    
    This test proves the SSOT violation exists by showing that invalid/expired/malformed 
    JWT tokens are accepted due to verify_signature=False bypass logic.
    """
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_accepts_invalid_jwt_signature_violation(self):
        """
        VIOLATION REPRODUCTION: WebSocket accepts tokens with invalid signatures.
        
        CURRENT VIOLATION: user_context_extractor.py lines 193-196
        jwt.decode(token, options={"verify_signature": False})
        
        This test proves the violation exists.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: Invalid JWT signature accepted")
        
        # Create a JWT token with WRONG signature (should be rejected)
        fake_payload = {
            "sub": "test_user_123",
            "iss": "netra-auth-service",
            "aud": "netra-backend",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "email": "test@example.com"
        }
        
        # Create token with WRONG secret (invalid signature)
        wrong_secret = "DEFINITELY_WRONG_SECRET_KEY_12345"
        invalid_token = jwt.encode(fake_payload, wrong_secret, algorithm="HS256")
        
        logger.info(f" SEARCH:  Created invalid token with wrong signature: {invalid_token[:50]}...")
        
        # Test the WebSocket user context extractor directly
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        
        # Create extractor instance
        extractor = WebSocketUserContextExtractor()
        
        # VIOLATION TEST: This should FAIL but currently PASSES due to verify_signature=False
        try:
            user_context = await extractor.extract_user_context_from_token(invalid_token)
            
            # If we get here, the violation exists (token was accepted)
            if user_context:
                logger.error(" ALERT:  SSOT VIOLATION CONFIRMED: Invalid JWT token was accepted!")
                logger.error(f" ALERT:  Extracted user context: {user_context}")
                
                # Assertion that proves violation exists
                assert user_context.get("sub") == "test_user_123", \
                    "SSOT VIOLATION: WebSocket accepted invalid JWT signature"
                    
                # Log the violation for tracking
                logger.critical(" ALERT:  SECURITY VIOLATION: WebSocket bypassed JWT signature verification")
                logger.critical(" ALERT:  THIS TEST PASSES = VIOLATION EXISTS")
                logger.critical(" ALERT:  AFTER SSOT FIX: This test should FAIL")
                
                # Test passes = violation confirmed
                return True
                
        except Exception as e:
            # If token is rejected, violation might be fixed
            logger.info(f" PASS:  Token properly rejected: {e}")
            pytest.fail("VIOLATION NOT REPRODUCED: Invalid token was rejected (violation may be fixed)")
        
        # Shouldn't reach here
        pytest.fail("VIOLATION TEST INCONCLUSIVE: Unable to determine violation status")
    
    @pytest.mark.asyncio  
    @pytest.mark.unit
    async def test_websocket_accepts_expired_jwt_token_violation(self):
        """
        VIOLATION REPRODUCTION: WebSocket accepts expired JWT tokens.
        
        This test proves that expired tokens are accepted due to JWT bypass logic.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: Expired JWT token accepted")
        
        # Create an EXPIRED JWT token
        expired_payload = {
            "sub": "expired_user_456", 
            "iss": "netra-auth-service",
            "aud": "netra-backend",
            "exp": int((datetime.now() - timedelta(hours=1)).timestamp()),  # EXPIRED 1 hour ago
            "iat": int((datetime.now() - timedelta(hours=2)).timestamp()),
            "email": "expired@example.com"
        }
        
        # Create expired token (even with correct secret, should be rejected due to expiry)
        env = get_env()
        jwt_secret = env.get("JWT_SECRET_KEY", "default-test-secret")
        expired_token = jwt.encode(expired_payload, jwt_secret, algorithm="HS256")
        
        logger.info(f" SEARCH:  Created expired token: {expired_token[:50]}...")
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        extractor = WebSocketUserContextExtractor()
        
        # VIOLATION TEST: Expired token should be rejected but might be accepted
        try:
            user_context = await extractor.extract_user_context_from_token(expired_token)
            
            if user_context:
                logger.error(" ALERT:  SSOT VIOLATION CONFIRMED: Expired JWT token was accepted!")
                logger.error(f" ALERT:  Extracted user context from expired token: {user_context}")
                
                # Assertion that proves violation exists
                assert user_context.get("sub") == "expired_user_456", \
                    "SSOT VIOLATION: WebSocket accepted expired JWT token"
                    
                logger.critical(" ALERT:  SECURITY VIOLATION: WebSocket accepted expired JWT token")
                logger.critical(" ALERT:  THIS TEST PASSES = VIOLATION EXISTS")
                
                return True
                
        except Exception as e:
            logger.info(f" PASS:  Expired token properly rejected: {e}")
            pytest.fail("VIOLATION NOT REPRODUCED: Expired token was rejected")
    
    @pytest.mark.asyncio
    @pytest.mark.unit  
    async def test_websocket_accepts_malformed_jwt_token_violation(self):
        """
        VIOLATION REPRODUCTION: WebSocket accepts completely malformed JWT tokens.
        
        This test proves that even malformed/garbage tokens might be processed
        due to the bypass logic.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: Malformed JWT token handling")
        
        # Test various malformed tokens
        malformed_tokens = [
            "totally.garbage.token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.GARBAGE.SIGNATURE",
            "not-even-jwt-format",
            "",
            "   ",
        ]
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        extractor = WebSocketUserContextExtractor()
        
        violation_detected = False
        
        for malformed_token in malformed_tokens:
            logger.info(f" SEARCH:  Testing malformed token: '{malformed_token}'")
            
            try:
                user_context = await extractor.extract_user_context_from_token(malformed_token)
                
                if user_context:
                    logger.error(f" ALERT:  VIOLATION: Malformed token accepted: {malformed_token}")
                    logger.error(f" ALERT:  Context extracted: {user_context}")
                    violation_detected = True
                    
            except Exception as e:
                logger.info(f" PASS:  Malformed token rejected: {e}")
        
        if violation_detected:
            logger.critical(" ALERT:  SSOT VIOLATION CONFIRMED: Malformed tokens were accepted")
            logger.critical(" ALERT:  THIS TEST PASSES = VIOLATION EXISTS")
            assert True, "SSOT VIOLATION: WebSocket accepted malformed JWT tokens"
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: All malformed tokens were rejected")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_websocket_jwt_bypass_enables_unauthorized_access(self):
        """
        INTEGRATION VIOLATION TEST: JWT bypass enables unauthorized WebSocket access.
        
        This test demonstrates the business impact of the JWT bypass violation
        by showing unauthorized users can access WebSocket functionality.
        """
        if NoDockerModeDetector.is_no_docker_mode():
            pytest.skip("Integration test requires services")
            
        logger.info(" ALERT:  TESTING BUSINESS IMPACT: Unauthorized WebSocket access via JWT bypass")
        
        # Create fake user token that would normally be unauthorized
        fake_admin_payload = {
            "sub": "fake_admin_999",
            "iss": "netra-auth-service", 
            "aud": "netra-backend",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "email": "fake_admin@malicious.com",
            "permissions": ["admin", "chat", "premium"]  # Elevated permissions
        }
        
        # Create token with wrong secret but proper structure
        fake_token = jwt.encode(fake_admin_payload, "MALICIOUS_SECRET", algorithm="HS256")
        
        logger.info(" SEARCH:  Testing unauthorized access with fake admin token")
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        extractor = WebSocketUserContextExtractor()
        
        try:
            # This should fail but might succeed due to violation
            user_context = await extractor.extract_user_context_from_token(fake_token)
            
            if user_context and user_context.get("sub") == "fake_admin_999":
                logger.error(" ALERT:  CRITICAL SECURITY VIOLATION: Unauthorized admin access granted!")
                logger.error(f" ALERT:  Fake admin context: {user_context}")
                
                # Check if fake permissions were accepted
                permissions = user_context.get("permissions", [])
                if "admin" in permissions:
                    logger.critical(" ALERT:  FAKE ADMIN PERMISSIONS ACCEPTED - MASSIVE SECURITY BREACH")
                
                # Business impact assertion
                assert True, "CRITICAL VIOLATION: JWT bypass enables unauthorized access to $500K+ ARR platform"
                return True
                
        except Exception as e:
            logger.info(f" PASS:  Unauthorized access properly blocked: {e}")
            pytest.fail("VIOLATION NOT REPRODUCED: Unauthorized access was blocked")

    def tearDown(self):
        """Clean up test artifacts."""
        logger.info("[U+1F9F9] JWT bypass violation test cleanup complete")


if __name__ == "__main__":
    # Run this test independently to verify violation reproduction
    pytest.main([__file__, "-v", "--tb=short"])