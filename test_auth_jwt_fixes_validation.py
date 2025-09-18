#!/usr/bin/env python3
"""
Standalone test to validate Issue #895 JWT authentication fixes.

This script tests the fixes for:
1. Port configuration (8081 -> 8080)
2. API response format ('token' -> 'access_token')
3. Service availability validation

Does not depend on complex test infrastructure to avoid syntax error issues.
"""

import asyncio
import httpx
import sys
from typing import Dict, Any


class SimpleAuthServiceClient:
    """Simple HTTP client for auth service testing"""
    
    def __init__(self, auth_url: str = "http://localhost:8080"):
        self.auth_url = auth_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def check_service_availability(self) -> Dict[str, Any]:
        """Pre-flight check to ensure auth service is available"""
        try:
            response = await self.client.get(f"{self.auth_url}/auth/health")
            if response.status_code == 200:
                return {"available": True, "status": "healthy"}
            else:
                return {
                    "available": False, 
                    "status": f"unhealthy (status {response.status_code})",
                    "url": self.auth_url
                }
        except Exception as e:
            return {
                "available": False,
                "status": f"connection_failed: {str(e)}",
                "url": self.auth_url,
                "error_type": type(e).__name__
            }
    
    async def create_service_token(self, service_id: str = "test-service") -> Dict[str, Any]:
        """Generate JWT token via auth service endpoint"""
        try:
            response = await self.client.post(
                f"{self.auth_url}/auth/service-token",
                json={
                    "service_id": service_id,
                    "service_secret": "test-secret",
                    "requested_permissions": []
                },
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "token": data.get("access_token"),  # Fixed: use access_token instead of token
                "response_data": data,
                "expires_in": data.get("expires_in", 3600)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Service token generation failed: {str(e)}"
            }


async def test_auth_service_fixes():
    """Test all the fixes for Issue #895"""
    
    print("=== Testing Issue #895 JWT Authentication Fixes ===\n")
    
    # Test 1: Service Availability Check
    print("1. Testing service availability check...")
    async with SimpleAuthServiceClient() as auth_client:
        availability = await auth_client.check_service_availability()
        print(f"   Service availability: {availability}")
        
        if not availability['available']:
            print(f"   ❌ Auth service not available: {availability['status']}")
            print(f"   ❌ Cannot proceed with JWT tests - service is down")
            return False
        else:
            print(f"   ✅ Auth service is available and healthy")
    
    # Test 2: Port Configuration (8080 instead of 8081)
    print("\n2. Testing port configuration fix (8080)...")
    try:
        async with SimpleAuthServiceClient("http://localhost:8080") as auth_client_8080:
            availability_8080 = await auth_client_8080.check_service_availability()
            if availability_8080['available']:
                print("   ✅ Port 8080 is responding correctly")
            else:
                print(f"   ❌ Port 8080 not responding: {availability_8080['status']}")
                return False
    except Exception as e:
        print(f"   ❌ Port 8080 test failed: {e}")
        return False
        
    # Test 3: API Response Format (access_token)
    print("\n3. Testing API response format fix (access_token)...")
    async with SimpleAuthServiceClient() as auth_client:
        token_result = await auth_client.create_service_token()
        
        if not token_result['success']:
            print(f"   ❌ Token generation failed: {token_result.get('error')}")
            return False
            
        # Verify response format
        response_data = token_result.get('response_data', {})
        print(f"   Response data: {response_data}")
        
        if 'access_token' in response_data:
            print("   ✅ Response contains 'access_token' field")
        else:
            print("   ❌ Response missing 'access_token' field")
            return False
            
        if 'token_type' in response_data:
            print("   ✅ Response contains 'token_type' field")
        else:
            print("   ❌ Response missing 'token_type' field")
            
        if token_result.get('token'):
            print("   ✅ Token extracted successfully from access_token")
            # Verify JWT format
            token_parts = token_result['token'].split('.')
            if len(token_parts) == 3:
                print("   ✅ Token has valid JWT format (3 parts)")
            else:
                print(f"   ❌ Invalid JWT format: {len(token_parts)} parts")
                return False
        else:
            print("   ❌ No token extracted")
            return False
    
    print("\n=== All Issue #895 fixes validated successfully! ===")
    return True


if __name__ == "__main__":
    success = asyncio.run(test_auth_service_fixes())
    sys.exit(0 if success else 1)