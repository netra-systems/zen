#!/usr/bin/env python3
"""
Test Auth Service Integration
Verifies that the auth service is properly integrated with backend and frontend
"""
import asyncio
import json
import logging
import sys
from typing import Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthServiceTester:
    """Test auth service integration"""
    
    def __init__(self, auth_url: str = "http://localhost:8081",
                 backend_url: str = "http://localhost:8000"):
        self.auth_url = auth_url
        self.backend_url = backend_url
        self.client = httpx.AsyncClient()
        self.test_results = []
        
    async def test_auth_service_health(self) -> bool:
        """Test auth service health endpoint"""
        try:
            response = await self.client.get(f"{self.auth_url}/health")
            success = response.status_code == 200
            self.test_results.append(("Auth Service Health", success))
            return success
        except Exception as e:
            logger.error(f"Auth service health check failed: {e}")
            self.test_results.append(("Auth Service Health", False))
            return False
    
    async def test_auth_service_endpoints(self) -> bool:
        """Test auth service API endpoints"""
        endpoints = [
            ("/", "Root"),
            ("/docs", "API Documentation"),
            ("/auth/health", "Auth Health")
        ]
        
        all_success = True
        for endpoint, name in endpoints:
            try:
                response = await self.client.get(f"{self.auth_url}{endpoint}")
                success = response.status_code in [200, 307]  # 307 for docs redirect
                self.test_results.append((f"Auth Endpoint: {name}", success))
                all_success = all_success and success
            except Exception as e:
                logger.error(f"Endpoint {endpoint} failed: {e}")
                self.test_results.append((f"Auth Endpoint: {name}", False))
                all_success = False
        
        return all_success
    
    async def test_backend_auth_client(self) -> bool:
        """Test backend auth client integration"""
        try:
            # Test if backend can reach auth service
            response = await self.client.get(f"{self.backend_url}/health")
            backend_healthy = response.status_code == 200
            self.test_results.append(("Backend Health", backend_healthy))
            
            # Test protected endpoint (should return 401 without token)
            response = await self.client.get(f"{self.backend_url}/api/user/me")
            needs_auth = response.status_code == 401
            self.test_results.append(("Backend Auth Required", needs_auth))
            
            return backend_healthy and needs_auth
            
        except Exception as e:
            logger.error(f"Backend integration test failed: {e}")
            self.test_results.append(("Backend Integration", False))
            return False
    
    async def test_token_validation_flow(self) -> bool:
        """Test token validation between services"""
        try:
            # Create a test token (in production, this would come from login)
            test_token = "test-token-123"
            
            # Test validation endpoint
            response = await self.client.post(
                f"{self.auth_url}/auth/validate",
                json={"token": test_token}
            )
            
            # Should return 401 for invalid token
            invalid_token = response.status_code == 401
            self.test_results.append(("Token Validation", invalid_token))
            
            return invalid_token
            
        except Exception as e:
            logger.error(f"Token validation test failed: {e}")
            self.test_results.append(("Token Validation", False))
            return False
    
    async def test_cors_configuration(self) -> bool:
        """Test CORS configuration"""
        try:
            headers = {
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST"
            }
            
            response = await self.client.options(
                f"{self.auth_url}/auth/login",
                headers=headers
            )
            
            cors_enabled = "access-control-allow-origin" in response.headers
            self.test_results.append(("CORS Configuration", cors_enabled))
            
            return cors_enabled
            
        except Exception as e:
            logger.error(f"CORS test failed: {e}")
            self.test_results.append(("CORS Configuration", False))
            return False
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*50)
        print("Auth Service Integration Tests")
        print("="*50 + "\n")
        
        # Run tests
        await self.test_auth_service_health()
        await self.test_auth_service_endpoints()
        await self.test_backend_auth_client()
        await self.test_token_validation_flow()
        await self.test_cors_configuration()
        
        # Print results
        print("\nTest Results:")
        print("-" * 40)
        
        passed = 0
        failed = 0
        
        for test_name, success in self.test_results:
            status = " PASS:  PASSED" if success else " FAIL:  FAILED"
            print(f"{test_name:<30} {status}")
            if success:
                passed += 1
            else:
                failed += 1
        
        print("-" * 40)
        print(f"\nTotal: {passed} passed, {failed} failed")
        
        # Close client
        await self.client.aclose()
        
        return failed == 0

async def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Auth Service Integration")
    parser.add_argument(
        "--auth-url",
        default="http://localhost:8081",
        help="Auth service URL"
    )
    parser.add_argument(
        "--backend-url",
        default="http://localhost:8000",
        help="Backend service URL"
    )
    
    args = parser.parse_args()
    
    tester = AuthServiceTester(args.auth_url, args.backend_url)
    success = await tester.run_all_tests()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))