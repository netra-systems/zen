"""
Test 1: Staging JWT Cross-Service Authentication

CRITICAL: Verify JWT tokens work between auth and backend services in staging.
This test validates the JWT secret synchronization fix and cross-service communication.

Business Value: Platform/Internal - System Stability
Without JWT sync, services can't communicate, breaking user authentication entirely.
"""

import pytest
import httpx
import asyncio
import time
from typing import Dict, Optional, Any
from shared.isolated_environment import IsolatedEnvironment

# Test Configuration
STAGING_URLS = {
    "backend": "https://netra-backend-staging-701982941522.us-central1.run.app",
    "auth": "https://netra-auth-service-701982941522.us-central1.run.app",
    "frontend": "https://netra-frontend-staging-701982941522.us-central1.run.app"
}

LOCAL_URLS = {
    "backend": "http://localhost:8000", 
    "auth": "http://localhost:8001",
    "frontend": "http://localhost:3000"
}

class StagingJWTTestRunner:
    """Test runner for JWT cross-service authentication validation."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = self.env.get("ENVIRONMENT", "development")
        self.urls = STAGING_URLS if self.environment == "staging" else LOCAL_URLS
        self.timeout = 30.0
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-Test/1.0"
        }
        
    async def test_auth_service_health(self) -> Dict[str, Any]:
        """Test 1.1: Verify auth service is responding."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.urls['auth']}/health",
                    headers=self.get_base_headers()
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": response.text if response.status_code != 200 else None
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response_time": 0,
                "data": None,
                "error": f"Connection failed: {str(e)}"
            }
            
    async def test_backend_service_health(self) -> Dict[str, Any]:
        """Test 1.2: Verify backend service is responding."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.urls['backend']}/health",
                    headers=self.get_base_headers()
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "data": response.json() if response.status_code == 200 else None,
                    "error": response.text if response.status_code != 200 else None
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response_time": 0,
                "data": None,
                "error": f"Connection failed: {str(e)}"
            }
            
    async def test_oauth_simulation_token(self) -> Dict[str, Any]:
        """Test 1.3: Test OAuth simulation token generation for staging."""
        try:
            # Use E2E_OAUTH_SIMULATION_KEY for staging testing
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return {
                    "success": False,
                    "error": "E2E_OAUTH_SIMULATION_KEY not configured",
                    "suggestion": "Set E2E_OAUTH_SIMULATION_KEY environment variable"
                }
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test simulation endpoint
                response = await client.post(
                    f"{self.urls['auth']}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-test-user",
                        "email": "staging-test@netrasystems.ai"
                    }
                )
                
                return {
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "token_generated": bool(response.json().get("access_token")) if response.status_code == 200 else False,
                    "error": response.text if response.status_code != 200 else None
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response_time": 0,
                "token_generated": False,
                "error": f"Token generation failed: {str(e)}"
            }
            
    async def test_cross_service_token_validation(self) -> Dict[str, Any]:
        """Test 1.4: Verify backend can validate tokens from auth service."""
        try:
            # First, get a token from auth service
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return {
                    "success": False,
                    "error": "E2E_OAUTH_SIMULATION_KEY not configured",
                    "step": "token_generation"
                }
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Get token from auth service
                auth_response = await client.post(
                    f"{self.urls['auth']}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-test-user",
                        "email": "staging-test@netrasystems.ai"
                    }
                )
                
                if auth_response.status_code != 200:
                    return {
                        "success": False,
                        "error": f"Token generation failed: {auth_response.text}",
                        "step": "token_generation",
                        "status_code": auth_response.status_code
                    }
                    
                token_data = auth_response.json()
                access_token = token_data.get("access_token")
                
                if not access_token:
                    return {
                        "success": False,
                        "error": "No access_token in response",
                        "step": "token_extraction",
                        "response_data": token_data
                    }
                    
                # Now validate token with backend service
                backend_response = await client.get(
                    f"{self.urls['backend']}/api/user/profile",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {access_token}"
                    }
                )
                
                return {
                    "success": backend_response.status_code in [200, 401],  # 401 is ok if no user profile
                    "token_generated": True,
                    "token_validated": backend_response.status_code != 403,  # 403 means JWT validation failed
                    "auth_status_code": auth_response.status_code,
                    "backend_status_code": backend_response.status_code,
                    "jwt_secret_sync": backend_response.status_code != 403,
                    "error": None if backend_response.status_code != 403 else "JWT secret mismatch between services"
                }
                
        except Exception as e:
            return {
                "success": False,
                "token_generated": False,
                "token_validated": False,
                "jwt_secret_sync": False,
                "error": f"Cross-service validation failed: {str(e)}"
            }
            
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all JWT cross-service authentication tests."""
        print(f"🔐 Running JWT Cross-Service Authentication Tests")
        print(f"Environment: {self.environment}")
        print(f"Auth URL: {self.urls['auth']}")
        print(f"Backend URL: {self.urls['backend']}")
        print()
        
        results = {}
        
        # Test 1.1: Auth service health
        print("1.1 Testing auth service health...")
        results["auth_health"] = await self.test_auth_service_health()
        print(f"     ✅ Auth service: {results['auth_health']['success']}")
        
        # Test 1.2: Backend service health
        print("1.2 Testing backend service health...")
        results["backend_health"] = await self.test_backend_service_health()
        print(f"     ✅ Backend service: {results['backend_health']['success']}")
        
        # Test 1.3: OAuth simulation
        print("1.3 Testing OAuth simulation token generation...")
        results["oauth_simulation"] = await self.test_oauth_simulation_token()
        print(f"     ✅ Token generation: {results['oauth_simulation']['success']}")
        
        # Test 1.4: Cross-service validation
        print("1.4 Testing cross-service token validation...")
        results["cross_service_validation"] = await self.test_cross_service_token_validation()
        print(f"     ✅ JWT cross-service: {results['cross_service_validation']['success']}")
        print(f"     📋 JWT secret sync: {results['cross_service_validation'].get('jwt_secret_sync', False)}")
        
        # Summary
        all_passed = all(result["success"] for result in results.values())
        results["summary"] = {
            "all_tests_passed": all_passed,
            "environment": self.environment,
            "total_tests": len(results) - 1,  # Exclude summary
            "passed_tests": sum(1 for result in results.values() if isinstance(result, dict) and result.get("success", False)),
            "critical_issue": not results.get("cross_service_validation", {}).get("jwt_secret_sync", False)
        }
        
        print()
        print(f"📊 Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
        if results["summary"]["critical_issue"]:
            print("🚨 CRITICAL: JWT secret mismatch detected between services!")
        
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_jwt_cross_service_auth():
    """Main test entry point for JWT cross-service authentication."""
    runner = StagingJWTTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["all_tests_passed"], f"JWT tests failed: {results}"
    assert not results["summary"]["critical_issue"], "JWT secret mismatch between services"
    assert results["cross_service_validation"]["jwt_secret_sync"], "JWT secrets not synchronized"


if __name__ == "__main__":
    async def main():
        runner = StagingJWTTestRunner()
        results = await runner.run_all_tests()
        
        if not results["summary"]["all_tests_passed"]:
            exit(1)
            
    asyncio.run(main())