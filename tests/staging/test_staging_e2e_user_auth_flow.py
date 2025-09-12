"""
Test 3: Staging E2E User Authentication Flow

CRITICAL: Test complete user registration, login, logout flow in staging.
This validates the core user authentication pipeline that gates all platform access.

Business Value: Free/Early/Mid/Enterprise - User Onboarding & Retention
Without working auth flow, users cannot access platform features, blocking all revenue.
"""

import pytest
import httpx
import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

class StagingE2EAuthFlowTestRunner:
    """Test runner for E2E user authentication flow in staging."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()
        self.timeout = StagingConfig.TIMEOUTS["default"]
        self.test_user_id = f"staging-e2e-{uuid.uuid4().hex[:8]}"
        self.test_email = f"staging-e2e-{uuid.uuid4().hex[:8]}@netrasystems.ai"
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-E2E-Test/1.0"
        }
        
    async def test_user_registration_flow(self) -> Dict[str, Any]:
        """Test 3.1: User registration process."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test user registration
                registration_data = {
                    "email": self.test_email,
                    "password": "Staging123!Test", 
                    "first_name": "Staging",
                    "last_name": "Test",
                    "company": "Netra Staging Tests"
                }
                
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/register",
                    headers=self.get_base_headers(),
                    json=registration_data
                )
                
                response_data = response.json() if response.status_code == 200 else {}
                
                return {
                    "success": response.status_code == 201,  # 201 for created
                    "status_code": response.status_code,
                    "user_id": response_data.get("user_id"),
                    "email_verified": response_data.get("email_verified", False),
                    "requires_verification": response_data.get("requires_verification", True),
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "error": response.text if response.status_code not in [201, 200] else None
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "error": f"Registration failed: {str(e)}"
            }
            
    async def test_oauth_simulation_login(self) -> Dict[str, Any]:
        """Test 3.2: OAuth simulation login for staging testing."""
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return {
                    "success": False,
                    "error": "E2E_OAUTH_SIMULATION_KEY not configured",
                    "suggestion": "Set E2E_OAUTH_SIMULATION_KEY in staging environment"
                }
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use OAuth simulation for staging tests
                login_data = {
                    "simulation_key": simulation_key,
                    "user_id": self.test_user_id,
                    "email": self.test_email,
                    "metadata": {
                        "test_type": "e2e_auth_flow",
                        "environment": self.environment
                    }
                }
                
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json=login_data
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    access_token = token_data.get("access_token")
                    refresh_token = token_data.get("refresh_token")
                    
                    return {
                        "success": bool(access_token),
                        "status_code": response.status_code,
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "token_type": token_data.get("token_type", "bearer"),
                        "expires_in": token_data.get("expires_in"),
                        "user_data": token_data.get("user"),
                        "response_time": response.elapsed.total_seconds() if response.elapsed else 0
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "error": f"Login simulation failed: {str(e)}"
            }
            
    async def test_token_validation_and_profile(self, access_token: str) -> Dict[str, Any]:
        """Test 3.3: Token validation and user profile retrieval."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test token validation by getting user profile
                response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {access_token}"
                    }
                )
                
                if response.status_code in [200, 404]:  # 404 is ok if profile doesn't exist yet
                    profile_data = response.json() if response.status_code == 200 else {}
                    
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "token_valid": response.status_code != 401,  # 401 = invalid token
                        "profile_exists": response.status_code == 200,
                        "profile_data": profile_data,
                        "user_id": profile_data.get("id"),
                        "email": profile_data.get("email"),
                        "response_time": response.elapsed.total_seconds() if response.elapsed else 0
                    }
                else:
                    return {
                        "success": response.status_code != 403,  # 403 = JWT secret mismatch
                        "status_code": response.status_code,
                        "token_valid": response.status_code != 401,
                        "profile_exists": False,
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "token_valid": False,
                "error": f"Profile validation failed: {str(e)}"
            }
            
    async def test_token_refresh(self, refresh_token: Optional[str]) -> Dict[str, Any]:
        """Test 3.4: Token refresh functionality."""
        if not refresh_token:
            return {
                "success": False,
                "error": "No refresh token available",
                "skipped": True
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test token refresh
                refresh_data = {
                    "refresh_token": refresh_token
                }
                
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/refresh",
                    headers=self.get_base_headers(),
                    json=refresh_data
                )
                
                if response.status_code == 200:
                    token_data = response.json()
                    new_access_token = token_data.get("access_token")
                    
                    return {
                        "success": bool(new_access_token),
                        "status_code": response.status_code,
                        "new_access_token": new_access_token,
                        "new_refresh_token": token_data.get("refresh_token"),
                        "response_time": response.elapsed.total_seconds() if response.elapsed else 0
                    }
                else:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text
                    }
                    
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "error": f"Token refresh failed: {str(e)}"
            }
            
    async def test_logout_flow(self, access_token: str) -> Dict[str, Any]:
        """Test 3.5: User logout process."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test logout
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/logout",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {access_token}"
                    }
                )
                
                return {
                    "success": response.status_code in [200, 204],  # Success codes for logout
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "error": response.text if response.status_code not in [200, 204] else None
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "error": f"Logout failed: {str(e)}"
            }
            
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all E2E user authentication flow tests."""
        print(f"[U+1F464] Running E2E User Authentication Flow Tests")
        print(f"Environment: {self.environment}")
        print(f"Auth URL: {StagingConfig.get_service_url('auth')}")
        print(f"Backend URL: {StagingConfig.get_service_url('netra_backend')}")
        print(f"Test User: {self.test_email}")
        print()
        
        results = {}
        access_token = None
        refresh_token = None
        
        # Test 3.1: User registration (optional - may not be enabled in staging)
        print("3.1 Testing user registration...")
        results["user_registration"] = await self.test_user_registration_flow()
        registration_success = results["user_registration"]["success"]
        print(f"      PASS:  Registration: {registration_success} (may be disabled in staging)")
        
        # Test 3.2: OAuth simulation login (primary login method for staging)
        print("3.2 Testing OAuth simulation login...")
        results["oauth_login"] = await self.test_oauth_simulation_login()
        login_success = results["oauth_login"]["success"]
        
        if login_success:
            access_token = results["oauth_login"]["access_token"]
            refresh_token = results["oauth_login"]["refresh_token"]
            
        print(f"      PASS:  OAuth login: {login_success}")
        
        # Test 3.3: Token validation and profile
        if access_token:
            print("3.3 Testing token validation and profile...")
            results["token_profile"] = await self.test_token_validation_and_profile(access_token)
            print(f"      PASS:  Token valid: {results['token_profile']['token_valid']}")
            print(f"     [U+1F4CB] Profile access: {results['token_profile']['profile_exists']}")
        else:
            results["token_profile"] = {"success": False, "error": "No access token", "skipped": True}
            print("     [U+23ED][U+FE0F]  Skipped token validation (no access token)")
            
        # Test 3.4: Token refresh
        print("3.4 Testing token refresh...")
        results["token_refresh"] = await self.test_token_refresh(refresh_token)
        refresh_success = results["token_refresh"]["success"] or results["token_refresh"].get("skipped", False)
        print(f"      PASS:  Token refresh: {refresh_success}")
        
        # Test 3.5: Logout flow
        if access_token:
            print("3.5 Testing logout flow...")
            results["logout"] = await self.test_logout_flow(access_token)
            print(f"      PASS:  Logout: {results['logout']['success']}")
        else:
            results["logout"] = {"success": False, "error": "No access token", "skipped": True}
            print("     [U+23ED][U+FE0F]  Skipped logout (no access token)")
            
        # Summary - focus on core auth flow
        core_auth_working = (results["oauth_login"]["success"] and 
                           results.get("token_profile", {}).get("token_valid", False))
        
        all_tests_run = sum(1 for result in results.values() 
                          if isinstance(result, dict) and not result.get("skipped", False))
        passed_tests = sum(1 for result in results.values() 
                         if isinstance(result, dict) and result.get("success", False))
        
        results["summary"] = {
            "core_auth_working": core_auth_working,
            "environment": self.environment,
            "total_tests_run": all_tests_run,
            "passed_tests": passed_tests,
            "auth_flow_complete": login_success and results.get("token_profile", {}).get("token_valid", False),
            "critical_failure": not core_auth_working
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests_run']} tests passed")
        print(f"[U+1F510] Core auth flow: {' PASS:  Working' if core_auth_working else ' FAIL:  Broken'}")
        
        if results["summary"]["critical_failure"]:
            print(" ALERT:  CRITICAL: Core authentication flow is broken!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_e2e_user_auth_flow():
    """Main test entry point for E2E user authentication flow."""
    runner = StagingE2EAuthFlowTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["core_auth_working"], "Core authentication flow is broken"
    assert not results["summary"]["critical_failure"], "Critical authentication failure detected"
    assert results["oauth_login"]["success"], "OAuth simulation login failed"


if __name__ == "__main__":
    async def main():
        runner = StagingE2EAuthFlowTestRunner()
        results = await runner.run_all_tests()
        
        if results["summary"]["critical_failure"]:
            exit(1)
            
    asyncio.run(main())