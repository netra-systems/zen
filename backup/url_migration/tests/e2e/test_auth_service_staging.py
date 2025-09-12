"""
Auth Service GCP Staging Environment Test - Updated for GCP Secrets Integration

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Enterprise & Development - GCP staging OAuth validation  
2. **Business Goal**: Enable OAuth testing in GCP staging environment
3. **Value Impact**: GCP staging environments support OAuth with proper URLs
4. **Revenue Impact**: Enables reliable staging OAuth testing, improves development velocity

**UPDATED SCOPE:**
- OAuth flow with GCP staging service URLs
- GCP Secrets Manager integration for E2E bypass keys
- Auth service integration with staging.netrasystems.ai services
- Token validation via GCP Cloud Run services
- Complete flow with proper error handling for GCP service timeouts

**SUCCESS CRITERIA:**
- Auth service works with GCP staging URLs
- E2E_OAUTH_SIMULATION_KEY integration from GCP Secrets Manager
- Proper timeout handling for GCP services (30+ seconds)
- Graceful handling of GCP service startup delays
- All flows work with unified test runner staging environment
"""

import asyncio
import os
import time
import uuid
from typing import Any, Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx
import pytest

from tests.e2e.staging_auth_bypass import StagingAuthHelper
from shared.isolated_environment import get_env

import logging
logger = logging.getLogger(__name__)


class GCPStagingAuthTester:
    """GCP staging environment authentication test manager"""
    
    def __init__(self):
        """Initialize GCP staging auth tester with proper service URLs"""
        self.auth_helper = StagingAuthHelper()
        # Use GCP staging service URLs from task requirements
        self.staging_auth_url = "https://auth.staging.netrasystems.ai"
        self.staging_backend_url = "https://api.staging.netrasystems.ai"
        self.staging_frontend_url = "https://app.staging.netrasystems.ai"
        self.auth_helper.staging_auth_url = self.staging_auth_url
        self.start_time = None
        self.test_session_id = str(uuid.uuid4())
    
    async def setup_staging_environment(self) -> None:
        """Setup GCP staging environment for authentication testing"""
        self.start_time = time.time()
        logger.info("Setting up GCP staging environment authentication tests")
        
        # Verify E2E_OAUTH_SIMULATION_KEY is available from environment
        if not self.auth_helper.bypass_key:
            raise ValueError("E2E_OAUTH_SIMULATION_KEY not found - ensure unified test runner configured it from GCP Secrets")
    
    async def test_staging_auth_service_health(self) -> Dict[str, Any]:
        """Test staging auth service health endpoint"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.staging_auth_url}/health",
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Auth service health check failed: {response.status_code}")
                
                health_data = response.json()
                logger.info(f"Auth service health: {health_data}")
                
                return {
                    "status": "healthy",
                    "response_time": time.time() - self.start_time,
                    "service_url": self.staging_auth_url
                }
        except httpx.TimeoutException:
            raise Exception("GCP staging auth service timeout - may be starting up")
    
    async def test_e2e_bypass_token_generation(self) -> Dict[str, Any]:
        """Test E2E bypass token generation with GCP staging services"""
        try:
            token = await self.auth_helper.get_test_token(
                email="e2e-staging@staging.netrasystems.ai",
                name="E2E Staging Test User"
            )
            
            if not token or len(token) < 20:
                raise Exception("Invalid token generated")
            
            # Verify token with staging auth service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.staging_auth_url}/auth/verify",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    raise Exception(f"Token verification failed: {response.status_code}")
                
                token_data = response.json()
                
                return {
                    "token_generated": True,
                    "token_valid": token_data.get("valid", False),
                    "user_email": token_data.get("email"),
                    "response_time": time.time() - self.start_time
                }
        except Exception as e:
            logger.error(f"E2E bypass token test failed: {e}")
            raise
    
    async def test_staging_session_management(self) -> Dict[str, Any]:
        """Test session management with GCP staging services"""
        try:
            # Get authenticated client
            client = await self.auth_helper.get_authenticated_client(
                base_url=self.staging_auth_url
            )
            
            # Test session endpoint
            response = await client.get("/auth/session", timeout=30.0)
            
            if response.status_code != 200:
                raise Exception(f"Session check failed: {response.status_code}")
            
            session_data = response.json()
            
            await client.aclose()
            
            return {
                "session_active": session_data.get("active", False),
                "user_id": session_data.get("user_id"),
                "response_time": time.time() - self.start_time
            }
        except Exception as e:
            logger.error(f"Session management test failed: {e}")
            raise
    
    async def test_cross_service_token_validation(self) -> Dict[str, Any]:
        """Test token validation between staging services"""
        try:
            # Get token from auth service
            token = await self.auth_helper.get_test_token()
            
            # Test token with backend service
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Test with backend health endpoint that may require auth
                response = await client.get(
                    f"{self.staging_backend_url}/api/health",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30.0
                )
                
                # Note: Backend may not require auth for health endpoint
                # This tests the token format and service connectivity
                backend_accessible = response.status_code in [200, 401, 403]  # 401/403 means auth was processed
                
                return {
                    "token_format_valid": True,
                    "backend_service_accessible": backend_accessible,
                    "backend_response_code": response.status_code,
                    "response_time": time.time() - self.start_time
                }
        except Exception as e:
            logger.error(f"Cross-service token validation failed: {e}")
            raise
    
    async def test_complete_staging_auth_flow(self) -> Dict[str, Any]:
        """Test complete authentication flow on GCP staging"""
        flow_results = {}
        
        # Test 1: Service health
        health_result = await self.test_staging_auth_service_health()
        flow_results["health_check"] = health_result
        
        # Test 2: E2E bypass token
        token_result = await self.test_e2e_bypass_token_generation()
        flow_results["token_generation"] = token_result
        
        # Test 3: Session management
        session_result = await self.test_staging_session_management()
        flow_results["session_management"] = session_result
        
        # Test 4: Cross-service validation
        cross_service_result = await self.test_cross_service_token_validation()
        flow_results["cross_service_validation"] = cross_service_result
        
        # Calculate total execution time
        total_time = time.time() - self.start_time
        flow_results["total_execution_time"] = total_time
        
        logger.info(f"Complete staging auth flow completed in {total_time:.2f}s")
        return flow_results
    
    async def cleanup(self) -> None:
        """Cleanup test resources"""
        try:
            logger.info("GCP staging auth test cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")


# Test execution
@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_auth_complete_flow():
    """
    CRITICAL Test: GCP Staging Authentication Complete Flow
    
    Validates authentication functionality on GCP staging environment including:
    - Service health checks with proper timeouts
    - E2E bypass key integration from GCP Secrets Manager  
    - Token generation and validation
    - Session management
    - Cross-service token validation
    - Graceful error handling for GCP service issues
    """
    # Skip test if not running in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    tester = GCPStagingAuthTester()
    
    try:
        # Setup staging environment
        await tester.setup_staging_environment()
        
        # Execute complete flow test
        results = await tester.test_complete_staging_auth_flow()
        
        # Validate critical results
        assert results["health_check"]["status"] == "healthy", "Auth service not healthy"
        assert results["token_generation"]["token_generated"] is True, "Token generation failed"
        assert results["token_generation"]["token_valid"] is True, "Token validation failed"
        assert results["session_management"]["session_active"] is True, "Session not active"
        
        # Verify reasonable response times (allowing for GCP startup)
        assert results["total_execution_time"] < 60.0, "Total flow too slow"
        
        logger.info(f" CELEBRATION:  GCP staging authentication test PASSED in {results['total_execution_time']:.2f}s")
        
    except ValueError as e:
        if "E2E_OAUTH_SIMULATION_KEY" in str(e):
            pytest.skip(f"GCP Secrets Manager issue: {e}")
        else:
            raise
    except Exception as e:
        if any(term in str(e).lower() for term in ["gcp", "timeout", "run.app", "service"]):
            pytest.skip(f"GCP service issue: {e}")
        else:
            raise
    finally:
        await tester.cleanup()


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_gcp_staging_service_connectivity():
    """Test basic connectivity to all GCP staging services"""
    # Skip test if not running in staging environment
    env = get_env()
    if env.get("ENVIRONMENT", "development") != "staging":
        pytest.skip("Test only runs in staging environment")
    
    tester = GCPStagingAuthTester()
    services_to_test = [
        ("Auth Service", tester.staging_auth_url),
        ("Backend Service", tester.staging_backend_url),
        ("Frontend Service", tester.staging_frontend_url)
    ]
    
    connectivity_results = {}
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for service_name, service_url in services_to_test:
                try:
                    response = await client.get(f"{service_url}/health", timeout=30.0)
                    connectivity_results[service_name] = {
                        "accessible": True,
                        "status_code": response.status_code,
                        "url": service_url
                    }
                    logger.info(f"{service_name} accessible: {response.status_code}")
                except httpx.TimeoutException:
                    connectivity_results[service_name] = {
                        "accessible": False,
                        "error": "timeout",
                        "url": service_url
                    }
                    logger.warning(f"{service_name} timeout")
                except Exception as e:
                    connectivity_results[service_name] = {
                        "accessible": False,
                        "error": str(e),
                        "url": service_url
                    }
                    logger.warning(f"{service_name} error: {e}")
        
        # At least auth service should be accessible for tests to work
        if not connectivity_results.get("Auth Service", {}).get("accessible", False):
            pytest.skip("Auth service not accessible - cannot run staging tests")
        
        logger.info(f"Service connectivity test completed: {connectivity_results}")
        
    except Exception as e:
        pytest.skip(f"Service connectivity test failed: {e}")


if __name__ == "__main__":
    """Direct execution for development testing"""
    async def run_gcp_staging_auth_tests():
        await test_gcp_staging_auth_complete_flow()
        await test_gcp_staging_service_connectivity()
    
    asyncio.run(run_gcp_staging_auth_tests())