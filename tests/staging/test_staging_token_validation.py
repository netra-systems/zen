"""
Test 7: Staging Token Validation

CRITICAL: Verify token generation and validation across all staging services.
This ensures the JWT authentication system works correctly for all user requests.

Business Value: Platform/Internal - Security & User Authentication  
Token validation failures block user access to all platform features.
"""

import pytest
import httpx
import asyncio
import time
import jwt
import uuid
from typing import Dict, Any, Optional, List
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

class StagingTokenValidationTestRunner:
    """Test runner for token validation in staging environment."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()
        self.timeout = StagingConfig.TIMEOUTS["default"]
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-Token-Test/1.0"
        }
        
    async def test_token_generation(self) -> Dict[str, Any]:
        """Test 7.1: Token generation via OAuth simulation."""
        print("7.1 Testing token generation...")
        
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return {
                    "success": False,
                    "error": "E2E_OAUTH_SIMULATION_KEY not configured",
                    "suggestion": "Set E2E_OAUTH_SIMULATION_KEY environment variable"
                }
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Generate token
                test_user_id = f"staging-token-test-{uuid.uuid4().hex[:8]}"
                test_email = f"token-test-{uuid.uuid4().hex[:8]}@netrasystems.ai"
                
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": test_user_id,
                        "email": test_email
                    }
                )
                
                if response.status_code != 200:
                    return {
                        "success": False,
                        "status_code": response.status_code,
                        "error": response.text,
                        "test_user": test_user_id
                    }
                    
                token_data = response.json()
                access_token = token_data.get("access_token")
                refresh_token = token_data.get("refresh_token")
                
                # Validate token structure
                token_valid_structure = bool(access_token and len(access_token) > 100)
                
                # Try to decode token (without validation for inspection)
                token_payload = None
                token_header = None
                
                try:
                    # Decode without verification to inspect structure
                    token_header = jwt.get_unverified_header(access_token)
                    token_payload = jwt.decode(access_token, options={"verify_signature": False})
                except Exception as e:
                    token_payload = {"decode_error": str(e)}
                    
                return {
                    "success": token_valid_structure,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "access_token_length": len(access_token) if access_token else 0,
                    "refresh_token_present": bool(refresh_token),
                    "token_type": token_data.get("token_type", "unknown"),
                    "expires_in": token_data.get("expires_in"),
                    "token_header": token_header,
                    "token_payload": token_payload,
                    "user_data": token_data.get("user", {}),
                    "test_user": test_user_id,
                    "tokens": {
                        "access_token": access_token,
                        "refresh_token": refresh_token
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Token generation test failed: {str(e)}"
            }
            
    async def test_token_validation_backend(self, access_token: str) -> Dict[str, Any]:
        """Test 7.2: Token validation by backend service."""
        print("7.2 Testing token validation by backend...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test authenticated endpoint
                response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {access_token}"
                    }
                )
                
                # Status codes interpretation:
                # 200 = token valid, user profile found
                # 404 = token valid, user profile not found (still valid token)
                # 401 = token invalid/expired
                # 403 = token validation failed (JWT secret mismatch)
                
                token_accepted = response.status_code not in [401, 403]
                jwt_secret_sync = response.status_code != 403
                
                return {
                    "success": token_accepted,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "token_accepted": token_accepted,
                    "jwt_secret_sync": jwt_secret_sync,
                    "profile_found": response.status_code == 200,
                    "validation_error": None if token_accepted else response.text,
                    "service": "backend"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Backend token validation failed: {str(e)}",
                "service": "backend"
            }
            
    async def test_token_validation_auth(self, access_token: str) -> Dict[str, Any]:
        """Test 7.3: Token validation by auth service.""" 
        print("7.3 Testing token validation by auth service...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test token info endpoint
                response = await client.get(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/token/info",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": f"Bearer {access_token}"
                    }
                )
                
                token_valid = response.status_code == 200
                token_info = {}
                
                if token_valid:
                    try:
                        token_info = response.json()
                    except:
                        pass
                        
                return {
                    "success": token_valid,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "token_valid": token_valid,
                    "token_info": token_info,
                    "user_id": token_info.get("user_id") if isinstance(token_info, dict) else None,
                    "expires_at": token_info.get("exp") if isinstance(token_info, dict) else None,
                    "validation_error": None if token_valid else response.text,
                    "service": "auth"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Auth token validation failed: {str(e)}",
                "service": "auth"
            }
            
    async def test_token_refresh(self, refresh_token: Optional[str]) -> Dict[str, Any]:
        """Test 7.4: Token refresh functionality."""
        print("7.4 Testing token refresh...")
        
        if not refresh_token:
            return {
                "success": False,
                "error": "No refresh token available",
                "skipped": True
            }
            
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test token refresh
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/refresh",
                    headers=self.get_base_headers(),
                    json={"refresh_token": refresh_token}
                )
                
                refresh_success = response.status_code == 200
                new_tokens = {}
                
                if refresh_success:
                    try:
                        new_tokens = response.json()
                    except:
                        pass
                        
                new_access_token = new_tokens.get("access_token")
                new_refresh_token = new_tokens.get("refresh_token")
                
                return {
                    "success": refresh_success,
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0,
                    "new_access_token_generated": bool(new_access_token),
                    "new_refresh_token_generated": bool(new_refresh_token),
                    "new_access_token_length": len(new_access_token) if new_access_token else 0,
                    "refresh_error": None if refresh_success else response.text,
                    "new_tokens": {
                        "access_token": new_access_token,
                        "refresh_token": new_refresh_token
                    }
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Token refresh test failed: {str(e)}"
            }
            
    async def test_token_expiry_handling(self) -> Dict[str, Any]:
        """Test 7.5: Token expiry and error handling."""
        print("7.5 Testing token expiry handling...")
        
        results = {}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Test with no token
                no_token_response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                    headers=self.get_base_headers()
                )
                
                results["no_token"] = {
                    "success": no_token_response.status_code == 401,  # Should be unauthorized
                    "status_code": no_token_response.status_code,
                    "correctly_rejected": no_token_response.status_code == 401
                }
                
                # Test with invalid token
                invalid_token_response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": "Bearer invalid-token-12345"
                    }
                )
                
                results["invalid_token"] = {
                    "success": invalid_token_response.status_code in [401, 403],  # Should be rejected
                    "status_code": invalid_token_response.status_code,
                    "correctly_rejected": invalid_token_response.status_code in [401, 403]
                }
                
                # Test with malformed token
                malformed_token_response = await client.get(
                    f"{StagingConfig.get_service_url('netra_backend')}/api/user/profile",
                    headers={
                        **self.get_base_headers(),
                        "Authorization": "Bearer malformed.token.here"
                    }
                )
                
                results["malformed_token"] = {
                    "success": malformed_token_response.status_code in [401, 403],  # Should be rejected
                    "status_code": malformed_token_response.status_code,
                    "correctly_rejected": malformed_token_response.status_code in [401, 403]
                }
                
        except Exception as e:
            results["error"] = {
                "success": False,
                "error": f"Token expiry handling test failed: {str(e)}"
            }
            
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all token validation tests."""
        print(f"[U+1F510] Running Token Validation Tests")
        print(f"Environment: {self.environment}")
        print(f"Auth URL: {StagingConfig.get_service_url('auth')}")
        print(f"Backend URL: {StagingConfig.get_service_url('netra_backend')}")
        print()
        
        results = {}
        access_token = None
        refresh_token = None
        
        # Test 7.1: Token generation
        token_gen_result = await self.test_token_generation()
        results["token_generation"] = token_gen_result
        
        if token_gen_result["success"]:
            access_token = token_gen_result["tokens"]["access_token"]
            refresh_token = token_gen_result["tokens"]["refresh_token"]
            print(f"      PASS:  Token generated: {len(access_token) if access_token else 0} chars")
            
            # Test 7.2: Backend token validation
            backend_validation = await self.test_token_validation_backend(access_token)
            results["backend_validation"] = backend_validation
            print(f"      PASS:  Backend validation: {backend_validation['token_accepted']}")
            print(f"     [U+1F4CB] JWT secret sync: {backend_validation['jwt_secret_sync']}")
            
            # Test 7.3: Auth service token validation
            auth_validation = await self.test_token_validation_auth(access_token)
            results["auth_validation"] = auth_validation
            print(f"      PASS:  Auth validation: {auth_validation['token_valid']}")
            
        else:
            print(f"      FAIL:  Token generation failed: {token_gen_result.get('error', 'Unknown error')}")
            
        # Test 7.4: Token refresh
        refresh_result = await self.test_token_refresh(refresh_token)
        results["token_refresh"] = refresh_result
        refresh_working = refresh_result["success"] or refresh_result.get("skipped", False)
        print(f"      PASS:  Token refresh: {refresh_working}")
        
        # Test 7.5: Token expiry handling
        expiry_results = await self.test_token_expiry_handling()
        results.update({f"expiry_{k}": v for k, v in expiry_results.items()})
        
        expiry_handling_correct = all(
            result.get("correctly_rejected", False) 
            for key, result in expiry_results.items() 
            if key != "error"
        )
        print(f"      PASS:  Expiry handling: {expiry_handling_correct}")
        
        # Calculate summary
        core_token_functions = [
            results.get("token_generation", {}).get("success", False),
            results.get("backend_validation", {}).get("token_accepted", False),
            results.get("auth_validation", {}).get("token_valid", False)
        ]
        
        jwt_secret_synchronized = results.get("backend_validation", {}).get("jwt_secret_sync", False)
        
        all_tests = {k: v for k, v in results.items() if isinstance(v, dict) and "success" in v}
        total_tests = len(all_tests)
        passed_tests = sum(1 for result in all_tests.values() if result["success"])
        
        results["summary"] = {
            "core_token_system_working": all(core_token_functions),
            "jwt_secret_synchronized": jwt_secret_synchronized,
            "token_generation_working": results.get("token_generation", {}).get("success", False),
            "cross_service_validation_working": jwt_secret_synchronized,
            "environment": self.environment,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "critical_token_failure": not all(core_token_functions) or not jwt_secret_synchronized
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
        print(f"[U+1F510] Token system: {' PASS:  Working' if results['summary']['core_token_system_working'] else ' FAIL:  Broken'}")
        print(f" CYCLE:  JWT secret sync: {' PASS:  Synchronized' if jwt_secret_synchronized else ' FAIL:  Mismatch'}")
        
        if results["summary"]["critical_token_failure"]:
            print(" ALERT:  CRITICAL: Token validation system failure detected!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_token_validation():
    """Main test entry point for token validation."""
    runner = StagingTokenValidationTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["core_token_system_working"], "Core token system is not working"
    assert results["summary"]["jwt_secret_synchronized"], "JWT secrets not synchronized between services"  
    assert not results["summary"]["critical_token_failure"], "Critical token validation failure"


if __name__ == "__main__":
    async def main():
        runner = StagingTokenValidationTestRunner()
        results = await runner.run_all_tests()
        
        if results["summary"]["critical_token_failure"]:
            exit(1)
            
    asyncio.run(main())