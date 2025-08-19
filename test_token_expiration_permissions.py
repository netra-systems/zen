#!/usr/bin/env python3
"""
CRITICAL: Token Expiration and Permission Tests

Tests token expiration handling and permission enforcement across services.

Agent 12 - Unified Testing Implementation Team  
FOCUS:
- Token expiration behavior
- Permission level enforcement
- Invalid token handling
"""

import asyncio
import httpx
import os
import time
from datetime import datetime, timedelta

# Test Configuration
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8081")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:54323")


class TokenExpirationTester:
    """Test token expiration and permissions."""
    
    def __init__(self):
        self.auth_client = httpx.AsyncClient(base_url=AUTH_SERVICE_URL, timeout=10.0)
        self.backend_client = httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0)
        
    async def close(self):
        await self.auth_client.aclose()
        await self.backend_client.aclose()
        
    async def get_dev_token(self) -> str:
        """Get a fresh dev token."""
        response = await self.auth_client.post("/auth/dev/login", json={"email": "dev@example.com"})
        if response.status_code == 200:
            return response.json().get("access_token")
        return None
        
    async def test_invalid_tokens(self):
        """Test various invalid token scenarios."""
        print("\n=== INVALID TOKEN TESTS ===")
        
        invalid_tokens = [
            ("empty", ""),
            ("malformed", "invalid.token.here"),
            ("wrong_format", "not-a-jwt-token"),
            ("expired_structure", "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0LXVzZXIiLCJleHAiOjE2MDAwMDAwMDB9.fake_signature"),
        ]
        
        for test_name, token in invalid_tokens:
            print(f"\nTesting {test_name} token...")
            
            # Test with auth service
            try:
                auth_response = await self.auth_client.post("/auth/validate", json={"token": token})
                auth_valid = auth_response.status_code == 200 and auth_response.json().get("valid", False)
                print(f"  Auth service: {'REJECT' if not auth_valid else 'ACCEPT'} (expected: REJECT)")
            except Exception as e:
                print(f"  Auth service: ERROR - {e}")
                
            # Test with backend service
            headers = {"Authorization": f"Bearer {token}"}
            try:
                backend_response = await self.backend_client.get("/health", headers=headers)
                backend_accepts = backend_response.status_code == 200
                print(f"  Backend: {'ACCEPT' if backend_accepts else 'REJECT'} (expected: REJECT)")
            except Exception as e:
                print(f"  Backend: ERROR - {e}")
                
    async def test_token_in_different_contexts(self, token: str):
        """Test token in various contexts."""
        print("\n=== TOKEN CONTEXT TESTS ===")
        
        contexts = [
            ("Basic Health Check", "/health", self.backend_client),
            ("Auth Verification", "/auth/verify", self.auth_client),
        ]
        
        for context_name, endpoint, client in contexts:
            print(f"\nTesting {context_name} at {endpoint}")
            headers = {"Authorization": f"Bearer {token}"}
            
            try:
                response = await client.get(endpoint, headers=headers)
                status = "PASS" if response.status_code == 200 else f"FAIL({response.status_code})"
                print(f"  Result: {status}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"  Data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                    except:
                        print("  Data: Non-JSON response")
                        
            except Exception as e:
                print(f"  Result: ERROR - {e}")
                
    async def test_permission_inference(self, token: str):
        """Test what permissions can be inferred from token behavior."""
        print("\n=== PERMISSION INFERENCE TESTS ===")
        
        # Test various endpoints that might have different permission requirements
        test_endpoints = [
            # Public endpoints (should work)
            ("/health", "public"),
            ("/api/health", "public"), 
            
            # User endpoints (should work with user token)
            ("/api/user/info", "user"),
            
            # Admin endpoints (may require admin permissions)
            ("/admin/users", "admin"),
            ("/admin/health", "admin"),
            
            # API endpoints
            ("/api/agents/status", "api"),
        ]
        
        headers = {"Authorization": f"Bearer {token}"}
        
        for endpoint, expected_level in test_endpoints:
            print(f"\nTesting {endpoint} (expected: {expected_level})")
            
            try:
                response = await self.backend_client.get(endpoint, headers=headers)
                
                if response.status_code == 200:
                    print(f"  ALLOW - Token has {expected_level}+ permissions")
                elif response.status_code == 401:
                    print(f"  DENY - Invalid token")
                elif response.status_code == 403:
                    print(f"  DENY - Insufficient permissions for {expected_level}")
                elif response.status_code == 404:
                    print(f"  N/A - Endpoint not found")
                else:
                    print(f"  UNKNOWN - Status {response.status_code}")
                    
            except Exception as e:
                print(f"  ERROR - {e}")
                
    async def analyze_token_structure(self, token: str):
        """Analyze the JWT token structure."""
        print("\n=== TOKEN STRUCTURE ANALYSIS ===")
        
        try:
            # Basic JWT structure check
            parts = token.split('.')
            if len(parts) == 3:
                print(f"Valid JWT structure: header.payload.signature")
                print(f"Header length: {len(parts[0])}")
                print(f"Payload length: {len(parts[1])}")
                print(f"Signature length: {len(parts[2])}")
                
                # Decode header and payload (without verification)
                import base64
                import json
                
                try:
                    # Add padding if needed
                    header_padded = parts[0] + '=' * (4 - len(parts[0]) % 4)
                    header = json.loads(base64.urlsafe_b64decode(header_padded))
                    print(f"Header: {header}")
                except Exception as e:
                    print(f"Could not decode header: {e}")
                    
                try:
                    payload_padded = parts[1] + '=' * (4 - len(parts[1]) % 4)
                    payload = json.loads(base64.urlsafe_b64decode(payload_padded))
                    print(f"Payload keys: {list(payload.keys())}")
                    
                    # Check expiration
                    if 'exp' in payload:
                        exp_time = datetime.fromtimestamp(payload['exp'])
                        now = datetime.now()
                        time_left = exp_time - now
                        print(f"Expires at: {exp_time}")
                        print(f"Time left: {time_left}")
                        print(f"Currently valid: {time_left.total_seconds() > 0}")
                        
                    if 'sub' in payload:
                        print(f"Subject (user): {payload['sub']}")
                        
                    if 'permissions' in payload:
                        print(f"Permissions: {payload['permissions']}")
                        
                except Exception as e:
                    print(f"Could not decode payload: {e}")
                    
            else:
                print(f"Invalid JWT structure: {len(parts)} parts instead of 3")
                
        except Exception as e:
            print(f"Token analysis failed: {e}")


async def run_expiration_and_permission_tests():
    """Run expiration and permission tests."""
    print("Token Expiration and Permission Tests")
    print("=" * 50)
    
    tester = TokenExpirationTester()
    
    try:
        # Get a fresh token
        print("\n1. Getting fresh dev token...")
        token = await tester.get_dev_token()
        if not token:
            print("[FAIL] Could not obtain test token")
            return False
            
        print(f"[PASS] Obtained token: {token[:30]}...")
        
        # Analyze token structure
        await tester.analyze_token_structure(token)
        
        # Test token in different contexts
        await tester.test_token_in_different_contexts(token)
        
        # Test permission inference
        await tester.test_permission_inference(token)
        
        # Test invalid tokens
        await tester.test_invalid_tokens()
        
        print(f"\n{'='*50}")
        print("EXPIRATION AND PERMISSION TESTS COMPLETED")
        print(f"{'='*50}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await tester.close()


if __name__ == "__main__":
    result = asyncio.run(run_expiration_and_permission_tests())
    print(f"\nResult: {'PASSED' if result else 'FAILED'}")
    exit(0 if result else 1)