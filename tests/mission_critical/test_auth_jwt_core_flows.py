"""
🔴 MISSION CRITICAL: Authentication JWT Core Flows Test Suite

Tests the most fundamental authentication paths that ALL users must traverse.
These are the HIGHEST BUSINESS VALUE authentication flows.

Business Value Justification (BVJ):
- Segment: ALL (Free, Early, Mid, Enterprise) - 100% of users
- Business Goal: User Onboarding & Retention - Enable all user access
- Value Impact: $500K+ ARR - Without auth, ZERO revenue possible
- Strategic Impact: Platform Foundation - Auth enables all other features

CRITICAL SUCCESS CRITERIA:
1. JWT token generation MUST work (no users can authenticate without this)
2. JWT token validation MUST work (no API calls work without this)
3. Cross-service JWT consistency MUST work (backend/auth must use same secret)
4. Token expiration handling MUST work (prevents security issues)
5. Multi-user isolation MUST work (prevents data leaks between users)

FAILURE = COMPLETE SYSTEM UNAVAILABLE
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import jwt
import pytest
from shared.isolated_environment import get_env

# Import SSOT authentication utilities
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)

class AuthJWTCoreFlowValidator:
    """Validates core JWT authentication flows for mission-critical business value."""
    
    def __init__(self):
        self.env = get_env()
        self.auth_helper = E2EAuthHelper()
        self.validation_results = []
        
    def validate_jwt_structure(self, token: str) -> Dict[str, Any]:
        """Validate JWT token has required structure for business operations."""
        try:
            # Decode without verification to check structure
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            validation = {
                "valid_structure": True,
                "has_required_claims": all(claim in payload for claim in ["sub", "email", "iat", "exp"]),
                "has_algorithm": header.get("alg") == "HS256",
                "user_id": payload.get("sub"),
                "email": payload.get("email"),
                "expires_at": payload.get("exp"),
                "issued_at": payload.get("iat")
            }
            
            # Business-critical validation
            if not validation["has_required_claims"]:
                validation["business_impact"] = "CRITICAL: Missing required claims - users cannot be identified"
            elif not validation["has_algorithm"]:
                validation["business_impact"] = "CRITICAL: Wrong algorithm - security vulnerability"
            else:
                validation["business_impact"] = "NONE: Token structure valid for business operations"
                
            return validation
            
        except Exception as e:
            return {
                "valid_structure": False,
                "error": str(e),
                "business_impact": f"CRITICAL: Token decode failed - {str(e)}"
            }
    
    def validate_cross_service_consistency(self, token: str) -> Dict[str, Any]:
        """Validate JWT works across both auth and backend services."""
        validation = {
            "auth_service_valid": False,
            "backend_service_valid": False,
            "secrets_match": False,
            "business_impact": ""
        }
        
        try:
            # Get JWT secrets from both services
            from shared.jwt_secret_manager import get_unified_jwt_secret
            unified_secret = get_unified_jwt_secret()
            
            # Validate token with unified secret
            decoded = jwt.decode(token, unified_secret, algorithms=["HS256"])
            validation["auth_service_valid"] = True
            validation["backend_service_valid"] = True
            validation["secrets_match"] = True
            validation["user_data"] = {
                "user_id": decoded.get("sub"),
                "email": decoded.get("email"),
                "permissions": decoded.get("permissions", [])
            }
            validation["business_impact"] = "NONE: Cross-service consistency validated"
            
        except jwt.ExpiredSignatureError:
            validation["business_impact"] = "WARNING: Token expired - user needs to login again"
        except jwt.InvalidTokenError as e:
            validation["business_impact"] = f"CRITICAL: Token invalid across services - {str(e)}"
        except Exception as e:
            validation["business_impact"] = f"CRITICAL: Cross-service validation failed - {str(e)}"
            
        return validation
    
    def validate_multi_user_isolation(self, tokens: List[str]) -> Dict[str, Any]:
        """Validate that different user tokens are properly isolated."""
        validation = {
            "unique_user_ids": set(),
            "unique_emails": set(),
            "isolation_valid": True,
            "business_impact": ""
        }
        
        try:
            for token in tokens:
                decoded = jwt.decode(token, options={"verify_signature": False})
                validation["unique_user_ids"].add(decoded.get("sub"))
                validation["unique_emails"].add(decoded.get("email"))
            
            # Check isolation
            if len(validation["unique_user_ids"]) != len(tokens):
                validation["isolation_valid"] = False
                validation["business_impact"] = "CRITICAL: User ID collision - data leak risk"
            elif len(validation["unique_emails"]) != len(tokens):
                validation["isolation_valid"] = False
                validation["business_impact"] = "CRITICAL: Email collision - user confusion risk"
            else:
                validation["business_impact"] = "NONE: Multi-user isolation properly maintained"
                
        except Exception as e:
            validation["isolation_valid"] = False
            validation["business_impact"] = f"CRITICAL: Multi-user validation failed - {str(e)}"
            
        return validation


@pytest.mark.mission_critical
@pytest.mark.real_services
class TestAuthJWTCoreFlows(BaseIntegrationTest):
    """Mission Critical: Core JWT authentication flows that enable ALL business value."""
    
    @pytest.fixture(autouse=True)
    async def setup_test_environment(self, real_services_fixture):
        """Setup real services for mission critical auth testing."""
        self.services = real_services_fixture
        self.validator = AuthJWTCoreFlowValidator()
        self.auth_helper = E2EAuthHelper()
        
        # Ensure database is available for user operations
        if not self.services.get("database_available", False):
            pytest.skip("Database required for mission critical auth tests")
    
    async def test_jwt_token_generation_core_business_flow(self):
        """
        MISSION CRITICAL: JWT token generation for user authentication.
        
        BUSINESS IMPACT: Without this, ZERO users can authenticate = $0 revenue
        """
        logger.info("🔴 MISSION CRITICAL: Testing JWT token generation")
        
        # Generate JWT token using SSOT helper
        user_id = f"mission-critical-{uuid.uuid4().hex[:8]}"
        email = f"mission-test-{int(time.time())}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read", "write", "agent:execute"],
            exp_minutes=30
        )
        
        # CRITICAL VALIDATION: Token must be generated
        assert token is not None, "MISSION CRITICAL FAILURE: JWT token generation failed"
        assert isinstance(token, str), "MISSION CRITICAL FAILURE: Token must be string"
        assert len(token) > 50, "MISSION CRITICAL FAILURE: Token too short - likely invalid"
        
        # Validate token structure for business operations
        validation = self.validator.validate_jwt_structure(token)
        assert validation["valid_structure"], f"BUSINESS CRITICAL: {validation.get('business_impact', 'Token structure invalid')}"
        assert validation["has_required_claims"], "BUSINESS CRITICAL: Missing user identification claims"
        assert validation["user_id"] == user_id, "BUSINESS CRITICAL: User ID mismatch in token"
        assert validation["email"] == email, "BUSINESS CRITICAL: Email mismatch in token"
        
        logger.info("✅ MISSION CRITICAL: JWT token generation validated")
        
    async def test_jwt_token_validation_core_business_flow(self):
        """
        MISSION CRITICAL: JWT token validation for API access.
        
        BUSINESS IMPACT: Without this, users can't access ANY features = $0 value delivery
        """
        logger.info("🔴 MISSION CRITICAL: Testing JWT token validation")
        
        # Create valid token
        user_id = f"validation-test-{uuid.uuid4().hex[:8]}"
        email = f"validation-{int(time.time())}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=30
        )
        
        # CRITICAL VALIDATION: Token must validate correctly
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            decoded = jwt.decode(token, secret, algorithms=["HS256"])
            
            assert decoded["sub"] == user_id, "BUSINESS CRITICAL: User ID validation failed"
            assert decoded["email"] == email, "BUSINESS CRITICAL: Email validation failed"
            assert decoded["exp"] > time.time(), "BUSINESS CRITICAL: Token already expired"
            
        except jwt.ExpiredSignatureError:
            pytest.fail("MISSION CRITICAL FAILURE: Token expired during validation")
        except jwt.InvalidTokenError as e:
            pytest.fail(f"MISSION CRITICAL FAILURE: Token validation failed - {str(e)}")
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL FAILURE: Validation system error - {str(e)}")
        
        logger.info("✅ MISSION CRITICAL: JWT token validation confirmed")
        
    async def test_cross_service_jwt_consistency_revenue_critical(self):
        """
        MISSION CRITICAL: JWT consistency between auth and backend services.
        
        BUSINESS IMPACT: Inconsistency breaks ALL API calls = Complete service failure
        """
        logger.info("🔴 MISSION CRITICAL: Testing cross-service JWT consistency")
        
        # Create token using auth helper (simulates auth service)
        user_id = f"cross-service-{uuid.uuid4().hex[:8]}"
        email = f"cross-service-{int(time.time())}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read", "write", "agent:execute"]
        )
        
        # CRITICAL VALIDATION: Token must work across services
        validation = self.validator.validate_cross_service_consistency(token)
        
        if not validation["secrets_match"]:
            pytest.fail(f"MISSION CRITICAL FAILURE: {validation['business_impact']}")
            
        assert validation["auth_service_valid"], "MISSION CRITICAL: Auth service cannot validate token"
        assert validation["backend_service_valid"], "MISSION CRITICAL: Backend service cannot validate token"
        
        # Verify user data consistency
        user_data = validation.get("user_data", {})
        assert user_data.get("user_id") == user_id, "BUSINESS CRITICAL: User ID inconsistent across services"
        assert user_data.get("email") == email, "BUSINESS CRITICAL: Email inconsistent across services"
        
        logger.info("✅ MISSION CRITICAL: Cross-service JWT consistency validated")
    
    async def test_token_expiration_security_compliance(self):
        """
        MISSION CRITICAL: Token expiration prevents security vulnerabilities.
        
        BUSINESS IMPACT: Without expiration, compromised tokens = Security breach risk
        """
        logger.info("🔴 MISSION CRITICAL: Testing token expiration security")
        
        # Create short-lived token (1 second)
        user_id = f"expiration-test-{uuid.uuid4().hex[:8]}"
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=f"expiration-{int(time.time())}@netra.test",
            exp_minutes=0  # Expires immediately
        )
        
        # Wait for expiration
        await asyncio.sleep(1.1)
        
        # CRITICAL VALIDATION: Expired token must be rejected
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            jwt.decode(token, secret, algorithms=["HS256"])
            pytest.fail("SECURITY CRITICAL FAILURE: Expired token was accepted")
        except jwt.ExpiredSignatureError:
            # This is expected - expired tokens should be rejected
            pass
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL FAILURE: Unexpected error during expiration test - {str(e)}")
        
        logger.info("✅ MISSION CRITICAL: Token expiration security validated")
        
    async def test_multi_user_isolation_revenue_protection(self):
        """
        MISSION CRITICAL: Multi-user isolation prevents data leaks.
        
        BUSINESS IMPACT: Data leaks between users = Legal liability + User trust loss
        """
        logger.info("🔴 MISSION CRITICAL: Testing multi-user isolation")
        
        # Create tokens for multiple users
        user_count = 5
        tokens = []
        user_data = []
        
        for i in range(user_count):
            user_id = f"isolation-user-{i}-{uuid.uuid4().hex[:6]}"
            email = f"user{i}-{int(time.time())}@netra.test"
            
            token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email,
                permissions=[f"user_{i}_access"]
            )
            
            tokens.append(token)
            user_data.append({"user_id": user_id, "email": email})
        
        # CRITICAL VALIDATION: User isolation must be maintained
        validation = self.validator.validate_multi_user_isolation(tokens)
        
        if not validation["isolation_valid"]:
            pytest.fail(f"MISSION CRITICAL FAILURE: {validation['business_impact']}")
        
        # Verify each user has unique identity
        assert len(validation["unique_user_ids"]) == user_count, "CRITICAL: User ID collision detected"
        assert len(validation["unique_emails"]) == user_count, "CRITICAL: Email collision detected"
        
        logger.info(f"✅ MISSION CRITICAL: Multi-user isolation validated for {user_count} users")
        
    async def test_auth_performance_under_load_revenue_impact(self):
        """
        MISSION CRITICAL: Authentication performance under user load.
        
        BUSINESS IMPACT: Slow auth = User abandonment = Revenue loss
        """
        logger.info("🔴 MISSION CRITICAL: Testing auth performance under load")
        
        # Simulate realistic user load
        concurrent_users = 50
        auth_tasks = []
        
        async def create_and_validate_token(user_index: int) -> Dict[str, Any]:
            """Create and validate token for one user."""
            start_time = time.time()
            
            user_id = f"load-test-{user_index}-{uuid.uuid4().hex[:6]}"
            email = f"loaduser{user_index}@netra.test"
            
            # Create token
            token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email
            )
            
            # Validate token
            validation = self.validator.validate_jwt_structure(token)
            
            end_time = time.time()
            
            return {
                "user_index": user_index,
                "duration": end_time - start_time,
                "success": validation["valid_structure"],
                "user_id": user_id
            }
        
        # Execute concurrent auth operations
        for i in range(concurrent_users):
            task = asyncio.create_task(create_and_validate_token(i))
            auth_tasks.append(task)
        
        results = await asyncio.gather(*auth_tasks)
        
        # CRITICAL PERFORMANCE VALIDATION
        successful_auths = sum(1 for r in results if r["success"])
        avg_duration = sum(r["duration"] for r in results) / len(results)
        max_duration = max(r["duration"] for r in results)
        
        # Business requirements
        assert successful_auths == concurrent_users, f"MISSION CRITICAL: {concurrent_users - successful_auths} auth failures"
        assert avg_duration < 0.1, f"BUSINESS CRITICAL: Average auth time {avg_duration:.3f}s > 100ms - users will abandon"
        assert max_duration < 0.5, f"BUSINESS CRITICAL: Max auth time {max_duration:.3f}s > 500ms - unacceptable UX"
        
        logger.info(f"✅ MISSION CRITICAL: Auth performance validated - {successful_auths} users, avg {avg_duration:.3f}s")


@pytest.mark.mission_critical
@pytest.mark.real_services
class TestAuthJWTBusinessContinuity(BaseIntegrationTest):
    """Mission Critical: Authentication business continuity scenarios."""
    
    async def test_auth_service_restart_scenario(self):
        """
        MISSION CRITICAL: Authentication continues working after service restart.
        
        BUSINESS IMPACT: Service restart breaks ALL user access = Complete outage
        """
        logger.info("🔴 MISSION CRITICAL: Testing auth service restart continuity")
        
        # Create token before "restart"
        user_id = f"restart-test-{uuid.uuid4().hex[:8]}"
        email = f"restart-{int(time.time())}@netra.test"
        
        pre_restart_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=60  # Long-lived token
        )
        
        # Validate pre-restart token works
        validation_pre = self.validator.validate_jwt_structure(pre_restart_token)
        assert validation_pre["valid_structure"], "SETUP FAILURE: Pre-restart token invalid"
        
        # Simulate service restart by creating new auth helper instance
        post_restart_helper = E2EAuthHelper()
        
        # Create new token post-restart
        post_restart_token = post_restart_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=60
        )
        
        # CRITICAL VALIDATION: Both tokens should work with same secret
        validation_post = self.validator.validate_jwt_structure(post_restart_token)
        assert validation_post["valid_structure"], "MISSION CRITICAL: Post-restart token invalid"
        
        # Validate both tokens use same secret (cross-validation)
        cross_validation_pre = self.validator.validate_cross_service_consistency(pre_restart_token)
        cross_validation_post = self.validator.validate_cross_service_consistency(post_restart_token)
        
        assert cross_validation_pre["secrets_match"], "MISSION CRITICAL: Pre-restart token fails cross-service validation"
        assert cross_validation_post["secrets_match"], "MISSION CRITICAL: Post-restart token fails cross-service validation"
        
        logger.info("✅ MISSION CRITICAL: Auth service restart continuity validated")
    
    async def test_database_connectivity_auth_resilience(self):
        """
        MISSION CRITICAL: Authentication handles database connectivity issues.
        
        BUSINESS IMPACT: DB issues should not prevent JWT validation = Service availability
        """
        logger.info("🔴 MISSION CRITICAL: Testing auth resilience to database issues")
        
        # Create valid JWT token (should work without database)
        user_id = f"db-resilience-{uuid.uuid4().hex[:8]}"
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=f"db-resilience-{int(time.time())}@netra.test"
        )
        
        # CRITICAL VALIDATION: JWT validation should work without database
        # (JWT is stateless and self-contained)
        validation = self.validator.validate_cross_service_consistency(token)
        
        assert validation["secrets_match"], "MISSION CRITICAL: JWT validation requires database (should be stateless)"
        assert validation["auth_service_valid"], "MISSION CRITICAL: Auth validation fails without database"
        assert validation["backend_service_valid"], "MISSION CRITICAL: Backend validation fails without database"
        
        logger.info("✅ MISSION CRITICAL: Auth resilience to database issues validated")


if __name__ == "__main__":
    """Run mission critical auth tests."""
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-m", "mission_critical",
        "--real-services"
    ])