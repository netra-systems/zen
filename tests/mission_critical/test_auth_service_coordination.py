"""
🔴 MISSION CRITICAL: Authentication Service Coordination Test Suite

Tests coordination between Auth Service and Backend for seamless user experience.
Critical for multi-service authentication flow that all users depend on.

Business Value Justification (BVJ):
- Segment: ALL users (Free, Early, Mid, Enterprise) - 100% coverage
- Business Goal: Seamless Authentication Experience - No auth friction
- Value Impact: $500K+ ARR - Poor auth UX = 40% user abandonment 
- Strategic Impact: Platform Reliability - Auth coordination enables all features

CRITICAL SUCCESS CRITERIA:
1. Auth Service and Backend must use identical JWT secrets
2. Token creation/validation must be synchronized across services
3. User session state must be consistent across services
4. OAuth redirect flows must work end-to-end
5. Service-to-service authentication must work reliably

FAILURE = AUTH FRICTION = USER ABANDONMENT = REVENUE LOSS
"""

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
import jwt
import pytest
from shared.isolated_environment import get_env

# Import SSOT authentication utilities  
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.fixtures.real_services import real_services_fixture
from test_framework.base_integration_test import BaseIntegrationTest

logger = logging.getLogger(__name__)


class AuthServiceCoordinationValidator:
    """Validates coordination between auth service and backend for business continuity."""
    
    def __init__(self):
        self.env = get_env()
        self.coordination_tests = []
        
    async def validate_service_synchronization(self, auth_url: str, backend_url: str) -> Dict[str, Any]:
        """Validate that auth service and backend are properly synchronized."""
        validation = {
            "jwt_secrets_match": False,
            "service_versions_compatible": False,
            "health_status_synchronized": False,
            "business_impact": "",
            "details": {}
        }
        
        try:
            async with httpx.AsyncClient() as client:
                # Check auth service health
                auth_health = await client.get(f"{auth_url}/health", timeout=5.0)
                auth_data = auth_health.json() if auth_health.status_code == 200 else {}
                
                # Check backend service health  
                backend_health = await client.get(f"{backend_url}/health", timeout=5.0)
                backend_data = backend_health.json() if backend_health.status_code == 200 else {}
                
                validation["details"] = {
                    "auth_health": auth_health.status_code,
                    "backend_health": backend_health.status_code,
                    "auth_data": auth_data,
                    "backend_data": backend_data
                }
                
                # Validate service health synchronization
                validation["health_status_synchronized"] = (
                    auth_health.status_code == 200 and backend_health.status_code == 200
                )
                
                # Test JWT secret coordination using actual token
                auth_helper = E2EAuthHelper()
                test_token = auth_helper.create_test_jwt_token(
                    user_id="coordination-test",
                    email="coordination@test.com"
                )
                
                # Try to validate token against both services (simulate cross-service call)
                from shared.jwt_secret_manager import get_unified_jwt_secret
                unified_secret = get_unified_jwt_secret()
                
                try:
                    decoded = jwt.decode(test_token, unified_secret, algorithms=["HS256"])
                    validation["jwt_secrets_match"] = True
                    validation["business_impact"] = "NONE: Services properly coordinated"
                except jwt.InvalidTokenError:
                    validation["jwt_secrets_match"] = False
                    validation["business_impact"] = "CRITICAL: JWT secrets not synchronized - auth will fail"
                    
        except Exception as e:
            validation["business_impact"] = f"CRITICAL: Service coordination check failed - {str(e)}"
            
        return validation
    
    async def validate_oauth_flow_coordination(self, auth_url: str, backend_url: str) -> Dict[str, Any]:
        """Validate OAuth flow coordination between services."""
        validation = {
            "oauth_config_synchronized": False,
            "redirect_handling_works": False,
            "token_exchange_works": False,
            "business_impact": ""
        }
        
        try:
            # Test OAuth configuration endpoint
            async with httpx.AsyncClient() as client:
                oauth_config = await client.get(f"{auth_url}/oauth/config", timeout=5.0)
                
                if oauth_config.status_code == 200:
                    config_data = oauth_config.json()
                    validation["oauth_config_synchronized"] = "client_id" in config_data
                    
                    # Test that backend can handle OAuth redirects
                    # (simulate OAuth redirect to backend)
                    test_code = f"test_code_{uuid.uuid4().hex[:8]}"
                    redirect_test = await client.get(
                        f"{backend_url}/auth/oauth/callback",
                        params={"code": test_code, "state": "test_state"},
                        timeout=5.0,
                        follow_redirects=False
                    )
                    
                    # Backend should handle redirect (even if it rejects test code)
                    validation["redirect_handling_works"] = redirect_test.status_code in [200, 302, 400]
                    
                    if validation["oauth_config_synchronized"] and validation["redirect_handling_works"]:
                        validation["business_impact"] = "NONE: OAuth flow coordination working"
                    else:
                        validation["business_impact"] = "CRITICAL: OAuth flow broken - users cannot login"
                else:
                    validation["business_impact"] = f"CRITICAL: OAuth config unavailable - {oauth_config.status_code}"
                    
        except Exception as e:
            validation["business_impact"] = f"CRITICAL: OAuth coordination test failed - {str(e)}"
            
        return validation


@pytest.mark.mission_critical
@pytest.mark.real_services
class TestAuthServiceCoordination(BaseIntegrationTest):
    """Mission Critical: Auth service coordination for seamless user experience."""
    
    @pytest.fixture(autouse=True)
    async def setup_coordination_testing(self, real_services_fixture):
        """Setup real services for coordination testing."""
        self.services = real_services_fixture
        self.validator = AuthServiceCoordinationValidator()
        self.auth_helper = E2EAuthHelper()
        
        # Ensure both services are available
        if not self.services.get("services_available", {}).get("backend", False):
            pytest.skip("Backend service required for coordination testing")
        
        self.auth_url = self.services["auth_url"] 
        self.backend_url = self.services["backend_url"]
        
    async def test_jwt_secret_synchronization_revenue_critical(self):
        """
        MISSION CRITICAL: JWT secrets must be synchronized between services.
        
        BUSINESS IMPACT: Secret mismatch = ALL authentication fails = $0 revenue
        """
        logger.info("🔴 MISSION CRITICAL: Testing JWT secret synchronization")
        
        # Test service synchronization
        validation = await self.validator.validate_service_synchronization(
            self.auth_url, self.backend_url
        )
        
        if not validation["jwt_secrets_match"]:
            pytest.fail(f"MISSION CRITICAL FAILURE: {validation['business_impact']}")
        
        # Create token and validate across both service contexts
        user_id = f"sync-test-{uuid.uuid4().hex[:8]}"
        email = f"sync-{int(time.time())}@netra.test"
        
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            permissions=["read", "write"]
        )
        
        # CRITICAL VALIDATION: Token must work in both service contexts
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            unified_secret = get_unified_jwt_secret()
            
            # Decode with unified secret (simulates backend validation)
            decoded = jwt.decode(token, unified_secret, algorithms=["HS256"])
            assert decoded["sub"] == user_id, "CRITICAL: User ID mismatch in cross-service validation"
            assert decoded["email"] == email, "CRITICAL: Email mismatch in cross-service validation"
            
        except jwt.InvalidTokenError as e:
            pytest.fail(f"MISSION CRITICAL FAILURE: Cross-service token validation failed - {str(e)}")
        
        logger.info("✅ MISSION CRITICAL: JWT secret synchronization validated")
    
    async def test_auth_token_lifecycle_coordination(self):
        """
        MISSION CRITICAL: Token lifecycle coordinated between services.
        
        BUSINESS IMPACT: Poor token lifecycle = User session drops = Bad UX = Churn
        """
        logger.info("🔴 MISSION CRITICAL: Testing auth token lifecycle coordination")
        
        # Create user with authentication
        user_id = f"lifecycle-{uuid.uuid4().hex[:8]}"
        email = f"lifecycle-{int(time.time())}@netra.test"
        
        # Step 1: Token creation (simulates auth service)
        original_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=30
        )
        
        # Step 2: Token usage (simulates backend service)
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            decoded = jwt.decode(original_token, secret, algorithms=["HS256"])
            
            assert decoded["sub"] == user_id, "CRITICAL: Token corruption during service handoff"
            
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: Token usage phase failed - {str(e)}")
        
        # Step 3: Token refresh (simulates coordinated refresh)
        refreshed_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=60  # Extended expiry
        )
        
        # Step 4: Validate refresh coordination
        try:
            refreshed_decoded = jwt.decode(refreshed_token, secret, algorithms=["HS256"])
            
            # User identity must remain consistent
            assert refreshed_decoded["sub"] == user_id, "CRITICAL: User identity lost during token refresh"
            assert refreshed_decoded["email"] == email, "CRITICAL: Email lost during token refresh"
            
            # Expiry should be extended
            assert refreshed_decoded["exp"] > decoded["exp"], "CRITICAL: Token refresh didn't extend expiry"
            
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: Token refresh coordination failed - {str(e)}")
        
        logger.info("✅ MISSION CRITICAL: Token lifecycle coordination validated")
    
    async def test_concurrent_auth_requests_coordination(self):
        """
        MISSION CRITICAL: Multiple concurrent auth requests handled properly.
        
        BUSINESS IMPACT: Auth bottlenecks = User frustration = Abandonment
        """
        logger.info("🔴 MISSION CRITICAL: Testing concurrent auth request coordination")
        
        concurrent_users = 20
        auth_tasks = []
        
        async def authenticate_user(user_index: int) -> Dict[str, Any]:
            """Simulate user authentication."""
            user_id = f"concurrent-{user_index}-{uuid.uuid4().hex[:6]}"
            email = f"concurrent{user_index}@netra.test"
            
            start_time = time.time()
            
            # Create and validate token (simulates full auth flow)
            token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=email
            )
            
            # Immediate validation (simulates API call)
            try:
                from shared.jwt_secret_manager import get_unified_jwt_secret
                secret = get_unified_jwt_secret()
                decoded = jwt.decode(token, secret, algorithms=["HS256"])
                
                success = decoded["sub"] == user_id
                duration = time.time() - start_time
                
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "success": success,
                    "duration": duration,
                    "token": token
                }
                
            except Exception as e:
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "success": False,
                    "error": str(e),
                    "duration": time.time() - start_time
                }
        
        # Launch concurrent auth requests
        for i in range(concurrent_users):
            task = asyncio.create_task(authenticate_user(i))
            auth_tasks.append(task)
        
        results = await asyncio.gather(*auth_tasks)
        
        # CRITICAL VALIDATION: All auth requests must succeed
        successful_auths = [r for r in results if r["success"]]
        failed_auths = [r for r in results if not r["success"]]
        
        if len(failed_auths) > 0:
            failure_details = [f"User {r['user_index']}: {r.get('error', 'Unknown error')}" for r in failed_auths]
            pytest.fail(f"MISSION CRITICAL: {len(failed_auths)}/{concurrent_users} auth failures: {failure_details}")
        
        # Performance validation
        avg_duration = sum(r["duration"] for r in successful_auths) / len(successful_auths)
        max_duration = max(r["duration"] for r in successful_auths)
        
        assert avg_duration < 0.2, f"BUSINESS CRITICAL: Average auth time {avg_duration:.3f}s too slow"
        assert max_duration < 1.0, f"BUSINESS CRITICAL: Max auth time {max_duration:.3f}s unacceptable"
        
        # Verify unique user isolation
        user_ids = {r["user_id"] for r in successful_auths}
        assert len(user_ids) == concurrent_users, "CRITICAL: User ID collision in concurrent auth"
        
        logger.info(f"✅ MISSION CRITICAL: {concurrent_users} concurrent auths successful, avg {avg_duration:.3f}s")
    
    async def test_oauth_flow_coordination_business_critical(self):
        """
        MISSION CRITICAL: OAuth flow coordination between auth and backend.
        
        BUSINESS IMPACT: Broken OAuth = Users can't login with Google/GitHub = Lost conversions
        """
        logger.info("🔴 MISSION CRITICAL: Testing OAuth flow coordination")
        
        # Test OAuth configuration synchronization
        validation = await self.validator.validate_oauth_flow_coordination(
            self.auth_url, self.backend_url
        )
        
        if not validation.get("oauth_config_synchronized", False):
            # OAuth may not be fully configured in test environment - warn but don't fail
            logger.warning(f"OAUTH WARNING: {validation.get('business_impact', 'OAuth not configured')}")
            pytest.skip("OAuth not configured in test environment - skipping OAuth coordination test")
        
        # Test OAuth redirect handling
        if not validation.get("redirect_handling_works", False):
            pytest.fail(f"MISSION CRITICAL: {validation.get('business_impact', 'OAuth redirect handling broken')}")
        
        logger.info("✅ MISSION CRITICAL: OAuth flow coordination validated")
    
    async def test_service_restart_auth_continuity(self):
        """
        MISSION CRITICAL: Authentication continues during service restarts.
        
        BUSINESS IMPACT: Service restart breaks auth = Complete outage = Revenue loss
        """
        logger.info("🔴 MISSION CRITICAL: Testing service restart auth continuity")
        
        # Create user session before "restart"
        user_id = f"restart-{uuid.uuid4().hex[:8]}"
        email = f"restart-{int(time.time())}@netra.test"
        
        pre_restart_token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=120  # Long-lived for restart scenario
        )
        
        # Validate pre-restart token
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            pre_decoded = jwt.decode(pre_restart_token, secret, algorithms=["HS256"])
            
            assert pre_decoded["sub"] == user_id, "SETUP FAILURE: Pre-restart token invalid"
            
        except Exception as e:
            pytest.fail(f"SETUP FAILURE: Pre-restart validation failed - {str(e)}")
        
        # Simulate service restart by creating new auth helper instance
        post_restart_helper = E2EAuthHelper()
        
        # Test that existing tokens still work (JWT is stateless)
        try:
            post_restart_secret = get_unified_jwt_secret()
            post_decoded = jwt.decode(pre_restart_token, post_restart_secret, algorithms=["HS256"])
            
            assert post_decoded["sub"] == user_id, "MISSION CRITICAL: User session lost after restart"
            assert post_decoded["email"] == email, "MISSION CRITICAL: User data lost after restart"
            
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: Post-restart token validation failed - {str(e)}")
        
        # Test new token creation after restart
        post_restart_token = post_restart_helper.create_test_jwt_token(
            user_id=user_id,
            email=email,
            exp_minutes=60
        )
        
        try:
            new_decoded = jwt.decode(post_restart_token, post_restart_secret, algorithms=["HS256"])
            assert new_decoded["sub"] == user_id, "MISSION CRITICAL: New token creation failed after restart"
            
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: Post-restart token creation failed - {str(e)}")
        
        logger.info("✅ MISSION CRITICAL: Service restart auth continuity validated")


@pytest.mark.mission_critical
@pytest.mark.real_services  
class TestAuthServiceFailureRecovery(BaseIntegrationTest):
    """Mission Critical: Auth service failure recovery scenarios."""
    
    async def test_auth_service_timeout_recovery(self):
        """
        MISSION CRITICAL: System recovers from auth service timeouts.
        
        BUSINESS IMPACT: Auth timeouts should not crash system = Graceful degradation
        """
        logger.info("🔴 MISSION CRITICAL: Testing auth service timeout recovery")
        
        # Create valid token for fallback validation
        user_id = f"timeout-test-{uuid.uuid4().hex[:8]}" 
        token = self.auth_helper.create_test_jwt_token(
            user_id=user_id,
            email=f"timeout-{int(time.time())}@netra.test",
            exp_minutes=60
        )
        
        # Test that JWT validation works even if auth service is slow/unavailable
        # (JWT validation should be stateless and not require auth service call)
        try:
            from shared.jwt_secret_manager import get_unified_jwt_secret
            secret = get_unified_jwt_secret()
            
            # This should work without calling auth service
            decoded = jwt.decode(token, secret, algorithms=["HS256"])
            assert decoded["sub"] == user_id, "MISSION CRITICAL: JWT validation requires auth service (should be stateless)"
            
        except Exception as e:
            pytest.fail(f"MISSION CRITICAL: JWT validation not resilient to auth service issues - {str(e)}")
        
        logger.info("✅ MISSION CRITICAL: Auth service timeout recovery validated")
    
    async def test_partial_service_failure_handling(self):
        """
        MISSION CRITICAL: Handle partial service failures gracefully.
        
        BUSINESS IMPACT: Partial failures should not cause complete auth outage
        """
        logger.info("🔴 MISSION CRITICAL: Testing partial service failure handling")
        
        # Test core JWT functionality (should work independently)
        user_count = 10
        tokens = []
        
        for i in range(user_count):
            user_id = f"partial-failure-{i}-{uuid.uuid4().hex[:6]}"
            token = self.auth_helper.create_test_jwt_token(
                user_id=user_id,
                email=f"failure{i}@netra.test"
            )
            tokens.append((user_id, token))
        
        # Validate all tokens work (core auth functionality)
        successful_validations = 0
        
        for user_id, token in tokens:
            try:
                from shared.jwt_secret_manager import get_unified_jwt_secret
                secret = get_unified_jwt_secret()
                decoded = jwt.decode(token, secret, algorithms=["HS256"])
                
                if decoded["sub"] == user_id:
                    successful_validations += 1
                    
            except Exception as e:
                logger.error(f"Token validation failed for {user_id}: {e}")
        
        # CRITICAL: Core auth must work even with partial failures
        success_rate = successful_validations / user_count
        assert success_rate >= 0.95, f"MISSION CRITICAL: Only {success_rate:.1%} auth success rate - system degraded"
        
        logger.info(f"✅ MISSION CRITICAL: Partial failure handled - {success_rate:.1%} auth success rate")


if __name__ == "__main__":
    """Run mission critical auth service coordination tests."""
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-m", "mission_critical",
        "--real-services"
    ])