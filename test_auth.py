#!/usr/bin/env python3
"""
Authentication Test Script for Netra Platform

This script tests the dev login endpoint and JWT token generation.
MISSION CRITICAL - Part of comprehensive E2E test suite.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Development Velocity & Platform Stability
- Value Impact: Prevents authentication failures that could block dev teams
- Strategic Impact: Foundation for all other API tests
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any

import httpx
import jwt

# Add project root to path

# Service URLs from running services
BACKEND_URL = "http://localhost:8000"
AUTH_SERVICE_URL = "http://localhost:8083"

class AuthenticationTester:
    """Test authentication flows for the Netra platform."""
    
    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None
        self.test_results: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "tests_passed": 0,
            "tests_failed": 0,
            "auth_token": None,
            "user_info": None,
            "errors": []
        }
    
    async def __aenter__(self):
        """Setup test environment."""
        self.session = httpx.AsyncClient(timeout=30.0)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Cleanup test environment."""
        if self.session:
            await self.session.aclose()
    
    def log_success(self, test_name: str, details: str = ""):
        """Log successful test."""
        self.test_results["tests_passed"] += 1
        print(f"✅ {test_name}: PASSED")
        if details:
            print(f"   Details: {details}")
    
    def log_failure(self, test_name: str, error: str):
        """Log failed test."""
        self.test_results["tests_failed"] += 1
        self.test_results["errors"].append({"test": test_name, "error": error})
        print(f"❌ {test_name}: FAILED")
        print(f"   Error: {error}")
    
    async def test_backend_health(self) -> bool:
        """Test that backend service is responding."""
        try:
            response = await self.session.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                self.log_success("Backend Health Check", f"Status: {response.status_code}")
                return True
            else:
                self.log_failure("Backend Health Check", f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.log_failure("Backend Health Check", f"Connection error: {str(e)}")
            return False
    
    async def test_auth_service_health(self) -> bool:
        """Test that auth service is responding."""
        try:
            response = await self.session.get(f"{AUTH_SERVICE_URL}/health")
            if response.status_code == 200:
                self.log_success("Auth Service Health Check", f"Status: {response.status_code}")
                return True
            else:
                self.log_failure("Auth Service Health Check", f"Unexpected status: {response.status_code}")
                return False
        except Exception as e:
            self.log_failure("Auth Service Health Check", f"Connection error: {str(e)}")
            return False
    
    async def test_dev_login(self) -> Optional[str]:
        """Test dev login endpoint and get JWT token."""
        try:
            # Test dev login endpoint on backend
            response = await self.session.post(
                f"{BACKEND_URL}/api/auth/dev/login",
                json={"email": "test@netra.ai"}
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                
                if token:
                    self.test_results["auth_token"] = token
                    self.test_results["user_info"] = data
                    self.log_success("Dev Login", f"Got token: {token[:20]}...")
                    return token
                else:
                    self.log_failure("Dev Login", "No access_token in response")
                    return None
            else:
                # Try auth service directly
                response = await self.session.post(
                    f"{AUTH_SERVICE_URL}/auth/dev/login",
                    json={}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token = data.get("access_token")
                    
                    if token:
                        self.test_results["auth_token"] = token
                        self.test_results["user_info"] = data
                        self.log_success("Dev Login (Auth Service)", f"Got token: {token[:20]}...")
                        return token
                    else:
                        self.log_failure("Dev Login (Auth Service)", "No access_token in response")
                        return None
                else:
                    self.log_failure("Dev Login", f"Both endpoints failed. Backend: {response.status_code}")
                    return None
        except Exception as e:
            self.log_failure("Dev Login", f"Request error: {str(e)}")
            return None
    
    async def test_token_validation(self, token: str) -> bool:
        """Test that the JWT token is valid and properly formatted."""
        try:
            # Test token format
            if not token or not token.startswith(('eyJ', 'Bearer ')):
                self.log_failure("Token Validation", "Invalid token format")
                return False
            
            # Clean token if it has Bearer prefix
            clean_token = token.replace('Bearer ', '') if token.startswith('Bearer ') else token
            
            # Decode without verification to check structure
            try:
                decoded = jwt.decode(clean_token, options={"verify_signature": False})
                self.log_success("Token Validation", f"Token decoded successfully. Subject: {decoded.get('sub', 'N/A')}")
                return True
            except jwt.InvalidTokenError as e:
                self.log_failure("Token Validation", f"Invalid JWT token: {str(e)}")
                return False
                
        except Exception as e:
            self.log_failure("Token Validation", f"Token validation error: {str(e)}")
            return False
    
    async def test_authenticated_request(self, token: str) -> bool:
        """Test making an authenticated request to the backend."""
        try:
            # Test accessing a protected endpoint
            headers = {"Authorization": f"Bearer {token}"}
            response = await self.session.get(f"{BACKEND_URL}/api/threads/", headers=headers)
            
            if response.status_code == 200:
                self.log_success("Authenticated Request", f"Successfully accessed threads endpoint")
                return True
            elif response.status_code == 401:
                self.log_failure("Authenticated Request", "Token rejected - authentication failed")
                return False
            else:
                self.log_failure("Authenticated Request", f"Unexpected status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_failure("Authenticated Request", f"Request error: {str(e)}")
            return False
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all authentication tests."""
        print("Starting Authentication Tests for Netra Platform\n")
        
        # Test service health
        backend_healthy = await self.test_backend_health()
        auth_healthy = await self.test_auth_service_health()
        
        if not backend_healthy:
            self.test_results["critical_error"] = "Backend service not available"
            return self.test_results
        
        # Test authentication flow
        token = await self.test_dev_login()
        if token:
            await self.test_token_validation(token)
            await self.test_authenticated_request(token)
        
        return self.test_results

async def main():
    """Main test execution."""
    async with AuthenticationTester() as tester:
        results = await tester.run_all_tests()
        
        print(f"\nAuthentication Test Results:")
        print(f"   Passed: {results['tests_passed']}")
        print(f"   Failed: {results['tests_failed']}")
        
        if results.get("auth_token"):
            print(f"   JWT Token: Available ({len(results['auth_token'])} chars)")
        
        if results["errors"]:
            print(f"\nErrors:")
            for error in results["errors"]:
                print(f"   - {error['test']}: {error['error']}")
        
        # Save results to file
        with open("auth_test_results.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to auth_test_results.json")
        
        # Return success if all tests passed
        success = results["tests_failed"] == 0 and results["tests_passed"] > 0
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)