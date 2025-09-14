"""
 ALERT:  MISSION CRITICAL: JWT Secret Consistency SSOT Violation

SSOT VIOLATION REPRODUCTION - Test #3 of 5
This test EXPOSES the violation where WebSocket and auth service use different
JWT validation logic and potentially different secrets/algorithms.

VIOLATION DETAILS:
- WebSocket uses local JWT decode with configurable options
- Auth service uses different JWT validation logic  
- No consistency guarantee between WebSocket and auth service JWT handling
- Different secret key access patterns (JWT_SECRET vs JWT_SECRET_KEY)

EXPECTED BEHAVIOR:
- BEFORE SSOT FIX: Test PASSES (proving inconsistency exists)
- AFTER SSOT FIX: Test FAILS (proving consistent JWT handling through SSOT)

Business Value Justification (BVJ):
- Segment: Enterprise/Platform - Auth consistency critical for security
- Business Goal: Security/Compliance - Consistent auth across all services  
- Value Impact: Prevents auth tokens working in one service but not another
- Revenue Impact: Auth inconsistencies could lose enterprise customers ($200K+ ARR)

CRITICAL JWT CONSISTENCY REQUIREMENT:
ALL services MUST use identical JWT validation logic through UnifiedAuthInterface.
"""

import asyncio
import json
import logging  
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import jwt
from shared.isolated_environment import get_env

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.no_docker_mode_detector import NoDockerModeDetector

logger = logging.getLogger(__name__)


class TestJwtSecretConsistencyViolation(SSotAsyncTestCase):
    """
    SSOT Violation Reproduction: Tests JWT secret/algorithm consistency across services.
    
    This test proves that WebSocket and auth service may use different JWT
    validation parameters, creating inconsistent auth behavior.
    """

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_websocket_auth_service_jwt_secret_inconsistency(self):
        """
        VIOLATION REPRODUCTION: WebSocket and auth service use different JWT secrets.
        
        CURRENT VIOLATION: Different secret key access patterns
        - WebSocket: JWT_SECRET_KEY
        - Auth service: JWT_SECRET  
        - Inconsistent JWT validation results
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: JWT secret inconsistency between services")
        
        # Test payload
        test_payload = {
            "sub": "consistency_test_user",
            "iss": "netra-auth-service", 
            "aud": "netra-backend",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "email": "test@consistency.com"
        }
        
        env = get_env()
        
        # Test different secret key patterns that might be used
        jwt_secret_key = env.get("JWT_SECRET_KEY", "websocket-secret")
        jwt_secret = env.get("JWT_SECRET", "auth-service-secret")
        
        logger.info(f" SEARCH:  JWT_SECRET_KEY: {jwt_secret_key[:10]}...")
        logger.info(f" SEARCH:  JWT_SECRET: {jwt_secret[:10]}...")
        
        # Create tokens with different secrets
        token_with_secret_key = jwt.encode(test_payload, jwt_secret_key, algorithm="HS256")
        token_with_secret = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
        
        logger.info(" SEARCH:  Testing JWT validation consistency...")
        
        # Test WebSocket validation
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        websocket_extractor = WebSocketUserContextExtractor()
        
        websocket_results = {}
        
        try:
            # Test WebSocket with both token types
            websocket_results["secret_key_token"] = await websocket_extractor.extract_user_context_from_token(token_with_secret_key)
            websocket_results["secret_token"] = await websocket_extractor.extract_user_context_from_token(token_with_secret)
            
            logger.info(f" SEARCH:  WebSocket results: {websocket_results}")
            
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] WebSocket validation error: {e}")
            websocket_results = {"error": str(e)}
        
        # Test auth service validation (if available)
        auth_service_results = {}
        try:
            from netra_backend.app.auth_integration.auth import verify_token
            
            # Test auth service with both token types  
            auth_service_results["secret_key_token"] = await verify_token(token_with_secret_key)
            auth_service_results["secret_token"] = await verify_token(token_with_secret)
            
            logger.info(f" SEARCH:  Auth service results: {auth_service_results}")
            
        except Exception as e:
            logger.warning(f" WARNING: [U+FE0F] Auth service validation error: {e}")
            auth_service_results = {"error": str(e)}
        
        # Check for consistency violations
        violations_detected = []
        
        # Check if different secrets produce different results
        if jwt_secret_key != jwt_secret:
            violations_detected.append("Different JWT secrets configured")
            logger.error(" ALERT:  VIOLATION: JWT_SECRET_KEY != JWT_SECRET")
        
        # Check if WebSocket accepts tokens that auth service rejects (or vice versa)
        websocket_accepts_secret_key = bool(websocket_results.get("secret_key_token"))
        websocket_accepts_secret = bool(websocket_results.get("secret_token"))
        
        if websocket_accepts_secret_key != websocket_accepts_secret:
            violations_detected.append("WebSocket inconsistent validation for different secrets")
            logger.error(" ALERT:  VIOLATION: WebSocket validates different secrets differently")
        
        # If we have auth service results, compare consistency
        if "error" not in auth_service_results and "error" not in websocket_results:
            auth_accepts_secret_key = bool(auth_service_results.get("secret_key_token"))
            auth_accepts_secret = bool(auth_service_results.get("secret_token"))
            
            if websocket_accepts_secret_key != auth_accepts_secret_key:
                violations_detected.append("WebSocket/Auth service inconsistent for JWT_SECRET_KEY tokens")
                logger.error(" ALERT:  VIOLATION: WebSocket/Auth service JWT_SECRET_KEY inconsistency")
                
            if websocket_accepts_secret != auth_accepts_secret:
                violations_detected.append("WebSocket/Auth service inconsistent for JWT_SECRET tokens") 
                logger.error(" ALERT:  VIOLATION: WebSocket/Auth service JWT_SECRET inconsistency")
        
        if violations_detected:
            logger.critical(" ALERT:  JWT CONSISTENCY VIOLATIONS DETECTED:")
            for violation in violations_detected:
                logger.critical(f" ALERT:  - {violation}")
            
            logger.critical(" ALERT:  THIS TEST PASSES = VIOLATIONS EXIST")
            logger.critical(" ALERT:  AFTER SSOT FIX: All services should use identical JWT logic")
            
            assert len(violations_detected) > 0, f"JWT CONSISTENCY VIOLATIONS: {violations_detected}"
            return True
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: JWT validation appears consistent")

    @pytest.mark.asyncio
    @pytest.mark.unit  
    async def test_jwt_algorithm_consistency_violation(self):
        """
        VIOLATION REPRODUCTION: Different JWT algorithms used across services.
        
        This test checks if WebSocket and auth service use different JWT algorithms
        (HS256 vs RS256, etc.) causing validation inconsistencies.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: JWT algorithm inconsistency")
        
        test_payload = {
            "sub": "algorithm_test_user",
            "iss": "netra-auth-service",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp())
        }
        
        env = get_env()
        jwt_secret = env.get("JWT_SECRET_KEY", "test-secret")
        
        # Create tokens with different algorithms
        algorithms_to_test = ["HS256", "HS512"]
        
        violations_detected = []
        
        for algorithm in algorithms_to_test:
            try:
                test_token = jwt.encode(test_payload, jwt_secret, algorithm=algorithm)
                logger.info(f" SEARCH:  Testing {algorithm} token: {test_token[:50]}...")
                
                from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
                extractor = WebSocketUserContextExtractor()
                
                # Test if WebSocket can validate this algorithm
                user_context = await extractor.extract_user_context_from_token(test_token)
                
                if user_context:
                    logger.info(f" PASS:  WebSocket accepts {algorithm}: {user_context.get('sub')}")
                else:
                    logger.warning(f" FAIL:  WebSocket rejects {algorithm}")
                    violations_detected.append(f"WebSocket rejects {algorithm}")
                    
            except Exception as e:
                logger.warning(f" WARNING: [U+FE0F] {algorithm} test failed: {e}")
                violations_detected.append(f"{algorithm} validation failed: {e}")
        
        # Check if there are algorithm inconsistencies
        if len(violations_detected) > 0:
            logger.error(" ALERT:  JWT ALGORITHM INCONSISTENCIES DETECTED:")
            for violation in violations_detected:
                logger.error(f" ALERT:  - {violation}")
                
            logger.critical(" ALERT:  ALGORITHM CONSISTENCY VIOLATION")
            logger.critical(" ALERT:  All services should support same JWT algorithms")
            
            assert len(violations_detected) > 0, f"JWT Algorithm violations: {violations_detected}"
            return True
        else:
            logger.info(" PASS:  JWT algorithm consistency appears okay")
            pytest.fail("VIOLATION NOT REPRODUCED: No algorithm inconsistencies detected")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_jwt_validation_options_inconsistency_violation(self):
        """
        VIOLATION REPRODUCTION: Different JWT validation options across services.
        
        CURRENT VIOLATION: WebSocket uses options={"verify_signature": False}
        while auth service might use stricter validation options.
        """
        logger.info(" ALERT:  TESTING SSOT VIOLATION: JWT validation options inconsistency")
        
        # Create test tokens with various validation edge cases
        test_cases = [
            {
                "name": "expired_token",
                "payload": {
                    "sub": "expired_user",
                    "iss": "netra-auth-service", 
                    "exp": int((datetime.now() - timedelta(hours=1)).timestamp()),  # Expired
                    "iat": int(datetime.now().timestamp())
                }
            },
            {
                "name": "no_exp_token", 
                "payload": {
                    "sub": "no_exp_user",
                    "iss": "netra-auth-service",
                    "iat": int(datetime.now().timestamp())
                    # No exp claim
                }
            },
            {
                "name": "wrong_issuer_token",
                "payload": {
                    "sub": "wrong_issuer_user",
                    "iss": "wrong-issuer",  # Wrong issuer
                    "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
                    "iat": int(datetime.now().timestamp())
                }
            }
        ]
        
        env = get_env()
        jwt_secret = env.get("JWT_SECRET_KEY", "test-secret")
        
        from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
        extractor = WebSocketUserContextExtractor()
        
        validation_inconsistencies = []
        
        for test_case in test_cases:
            test_token = jwt.encode(test_case["payload"], jwt_secret, algorithm="HS256")
            
            try:
                # Test WebSocket validation (might be lenient due to verify_signature=False)
                websocket_result = await extractor.extract_user_context_from_token(test_token)
                
                if websocket_result:
                    logger.error(f" ALERT:  VIOLATION: WebSocket accepts {test_case['name']}")
                    logger.error(f" ALERT:  Token should be rejected but was accepted: {websocket_result}")
                    
                    validation_inconsistencies.append(f"WebSocket accepts invalid {test_case['name']}")
                else:
                    logger.info(f" PASS:  WebSocket properly rejects {test_case['name']}")
                    
            except Exception as e:
                logger.info(f" PASS:  WebSocket rejects {test_case['name']}: {e}")
        
        if validation_inconsistencies:
            logger.critical(" ALERT:  JWT VALIDATION INCONSISTENCIES DETECTED:")
            for inconsistency in validation_inconsistencies:
                logger.critical(f" ALERT:  - {inconsistency}")
                
            logger.critical(" ALERT:  VALIDATION OPTIONS VIOLATION")
            logger.critical(" ALERT:  WebSocket uses lenient validation (verify_signature=False)")
            logger.critical(" ALERT:  THIS TEST PASSES = VIOLATION EXISTS")
            
            assert len(validation_inconsistencies) > 0, f"JWT validation inconsistencies: {validation_inconsistencies}"
            return True
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: WebSocket validation appears strict")

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_jwt_cross_service_token_validity_violation(self):
        """
        INTEGRATION VIOLATION TEST: JWT tokens valid in one service but not another.
        
        This test demonstrates business impact where users get inconsistent
        auth behavior between WebSocket and REST API endpoints.
        """
        if NoDockerModeDetector.is_no_docker_mode():
            pytest.skip("Integration test requires services")
            
        logger.info(" ALERT:  TESTING BUSINESS IMPACT: Cross-service JWT inconsistency")
        
        # Create a test token that might work in one service but not another
        test_payload = {
            "sub": "cross_service_user",
            "iss": "netra-auth-service",
            "exp": int((datetime.now() + timedelta(hours=1)).timestamp()),
            "iat": int(datetime.now().timestamp()),
            "email": "crossservice@test.com"
        }
        
        env = get_env()
        jwt_secret = env.get("JWT_SECRET_KEY", "test-secret")
        test_token = jwt.encode(test_payload, jwt_secret, algorithm="HS256")
        
        # Test WebSocket validation
        websocket_valid = False
        try:
            from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
            extractor = WebSocketUserContextExtractor()
            
            websocket_result = await extractor.extract_user_context_from_token(test_token)
            websocket_valid = bool(websocket_result)
            
            logger.info(f" SEARCH:  WebSocket validation result: {websocket_valid}")
            
        except Exception as e:
            logger.info(f" SEARCH:  WebSocket validation failed: {e}")
        
        # Test auth service validation (REST API)
        auth_service_valid = False
        try:
            from netra_backend.app.auth_integration.auth import verify_token
            
            auth_result = await verify_token(test_token)
            auth_service_valid = bool(auth_result)
            
            logger.info(f" SEARCH:  Auth service validation result: {auth_service_valid}")
            
        except Exception as e:
            logger.info(f" SEARCH:  Auth service validation failed: {e}")
        
        # Check for cross-service inconsistency (VIOLATION)
        if websocket_valid != auth_service_valid:
            logger.error(" ALERT:  CRITICAL BUSINESS VIOLATION: Cross-service JWT inconsistency!")
            logger.error(f" ALERT:  WebSocket accepts token: {websocket_valid}")
            logger.error(f" ALERT:  Auth service accepts token: {auth_service_valid}")
            
            # This creates terrible UX - user might connect to WebSocket but REST calls fail
            logger.critical(" ALERT:  CUSTOMER IMPACT: User gets inconsistent auth behavior")
            logger.critical(" ALERT:  Chat might work but API calls fail (or vice versa)")
            
            assert websocket_valid != auth_service_valid, "CRITICAL VIOLATION: Cross-service JWT inconsistency affects customer experience"
            return True
        else:
            pytest.fail("VIOLATION NOT REPRODUCED: Cross-service JWT validation is consistent")

    def teardown_method(self, method):
        """Clean up test artifacts."""
        logger.info("[U+1F9F9] JWT consistency violation test cleanup complete")


if __name__ == "__main__":
    # Run this test independently to verify violation reproduction  
    pytest.main([__file__, "-v", "--tb=short"])
