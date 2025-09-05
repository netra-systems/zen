#!/usr/bin/env python3
"""
End-to-end test for staging authentication flow.
Tests login, token refresh, and session persistence.
"""
import asyncio
import json
import time
import httpx
from datetime import datetime
from typing import Optional, Dict, Tuple
from shared.isolated_environment import IsolatedEnvironment


class StagingAuthE2ETest:
    """End-to-end authentication test for staging environment"""
    
    def __init__(self):
        self.frontend_url = "https://netra-frontend-staging-701982941522.us-central1.run.app"
        self.backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
        self.auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
        
        # Alternative URLs
        self.auth_alt_url = "https://auth.staging.netrasystems.ai"
        
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[str] = None
        
    async def test_health_checks(self) -> bool:
        """Test that all services are healthy"""
        print("\n1. Testing service health checks...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            services = [
                ("Auth Service", f"{self.auth_url}/health"),
                ("Backend Service", f"{self.backend_url}/health"),
                ("Frontend Service", f"{self.frontend_url}/api/health")
            ]
            
            all_healthy = True
            for name, url in services:
                try:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        status = data.get('status', 'unknown')
                        print(f"  [OK] {name}: {status}")
                    else:
                        print(f"  [FAIL] {name}: HTTP {response.status_code}")
                        all_healthy = False
                except Exception as e:
                    print(f"  [FAIL] {name}: {str(e)[:50]}")
                    all_healthy = False
                    
        return all_healthy
    
    async def test_dev_login(self) -> bool:
        """Test dev login to get initial tokens"""
        print("\n2. Testing dev login...")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Try dev login endpoint
                response = await client.post(
                    f"{self.auth_url}/auth/dev/login",
                    json={
                        "email": "dev@example.com",
                        "password": "dev123"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    self.user_id = data.get('user_id')
                    
                    print(f"  [OK] Login successful")
                    print(f"  [OK] Access token: ...{self.access_token[-20:] if self.access_token else 'None'}")
                    print(f"  [OK] Refresh token: ...{self.refresh_token[-20:] if self.refresh_token else 'None'}")
                    print(f"  [OK] User ID: {self.user_id}")
                    return True
                else:
                    print(f"  [FAIL] Login failed: HTTP {response.status_code}")
                    if response.text:
                        print(f"    Response: {response.text[:200]}")
                    return False
                    
            except Exception as e:
                print(f"  [FAIL] Login error: {str(e)}")
                return False
    
    async def test_token_validation(self) -> bool:
        """Test that the access token is valid"""
        print("\n3. Testing token validation...")
        
        if not self.access_token:
            print("  [FAIL] No access token available")
            return False
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.auth_url}/auth/validate",
                    json={"token": self.access_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  [OK] Token is valid")
                    print(f"    User ID: {data.get('user_id')}")
                    print(f"    Expires in: {data.get('expires_in')} seconds")
                    return True
                else:
                    print(f"  [FAIL] Token validation failed: HTTP {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"  [FAIL] Validation error: {str(e)}")
                return False
    
    async def test_token_refresh_snake_case(self) -> bool:
        """Test token refresh with snake_case format"""
        print("\n4. Testing token refresh (snake_case)...")
        
        if not self.refresh_token:
            print("  [FAIL] No refresh token available")
            return False
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.auth_url}/auth/refresh",
                    json={"refresh_token": self.refresh_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    old_access = self.access_token
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    
                    print(f"  [OK] Token refreshed successfully (snake_case)")
                    print(f"    New access token: ...{self.access_token[-20:] if self.access_token else 'None'}")
                    print(f"    Tokens changed: {old_access != self.access_token}")
                    return True
                else:
                    print(f"  [FAIL] Refresh failed: HTTP {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    return False
                    
            except Exception as e:
                print(f"  [FAIL] Refresh error: {str(e)}")
                return False
    
    async def test_token_refresh_camel_case(self) -> bool:
        """Test token refresh with camelCase format (frontend format)"""
        print("\n5. Testing token refresh (camelCase - frontend format)...")
        
        if not self.refresh_token:
            print("  [FAIL] No refresh token available")
            return False
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Use camelCase like the frontend does
                response = await client.post(
                    f"{self.auth_url}/auth/refresh",
                    json={"refreshToken": self.refresh_token}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    old_access = self.access_token
                    self.access_token = data.get('access_token')
                    self.refresh_token = data.get('refresh_token')
                    
                    print(f"  [OK] Token refreshed successfully (camelCase)")
                    print(f"    New access token: ...{self.access_token[-20:] if self.access_token else 'None'}")
                    print(f"    Tokens changed: {old_access != self.access_token}")
                    return True
                else:
                    print(f"  [FAIL] Refresh failed: HTTP {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    return False
                    
            except Exception as e:
                print(f"  [FAIL] Refresh error: {str(e)}")
                return False
    
    async def test_authenticated_api_call(self) -> bool:
        """Test making an authenticated API call to the backend"""
        print("\n6. Testing authenticated backend API call...")
        
        if not self.access_token:
            print("  [FAIL] No access token available")
            return False
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Try to access threads endpoint
                response = await client.get(
                    f"{self.backend_url}/api/threads",
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  [OK] Authenticated API call successful")
                    print(f"    Threads count: {len(data.get('threads', []))}")
                    return True
                elif response.status_code == 403:
                    print(f"  [FAIL] Authentication failed: HTTP 403 Forbidden")
                    print(f"    The backend is rejecting the token")
                    return False
                else:
                    print(f"  [FAIL] API call failed: HTTP {response.status_code}")
                    print(f"    Response: {response.text[:200]}")
                    return False
                    
            except Exception as e:
                print(f"  [FAIL] API call error: {str(e)}")
                return False
    
    async def test_session_persistence(self) -> bool:
        """Test that session persists across multiple refreshes"""
        print("\n7. Testing session persistence...")
        
        if not self.refresh_token:
            print("  [FAIL] No refresh token available")
            return False
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            tokens_list = []
            
            for i in range(3):
                print(f"\n  Refresh cycle {i+1}/3:")
                
                # Wait a bit between refreshes
                if i > 0:
                    await asyncio.sleep(1)
                
                # Alternate between snake_case and camelCase
                field_name = "refresh_token" if i % 2 == 0 else "refreshToken"
                
                try:
                    response = await client.post(
                        f"{self.auth_url}/auth/refresh",
                        json={field_name: self.refresh_token}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        self.access_token = data.get('access_token')
                        self.refresh_token = data.get('refresh_token')
                        tokens_list.append(self.access_token)
                        
                        # Validate the new token
                        val_response = await client.post(
                            f"{self.auth_url}/auth/validate",
                            json={"token": self.access_token}
                        )
                        
                        if val_response.status_code == 200:
                            val_data = val_response.json()
                            print(f"    [OK] Token refreshed and valid")
                            print(f"      User ID consistent: {val_data.get('user_id') == self.user_id}")
                        else:
                            print(f"    [FAIL] New token validation failed")
                            return False
                    else:
                        print(f"    [FAIL] Refresh failed: HTTP {response.status_code}")
                        return False
                        
                except Exception as e:
                    print(f"    [FAIL] Error: {str(e)}")
                    return False
            
            # Check that all tokens are different (no reuse)
            unique_tokens = len(set(tokens_list))
            print(f"\n  [OK] Session persisted across {len(tokens_list)} refreshes")
            print(f"    All tokens unique: {unique_tokens == len(tokens_list)}")
            
            return True
    
    async def test_logout(self) -> bool:
        """Test logout functionality"""
        print("\n8. Testing logout...")
        
        if not self.access_token:
            print("  [FAIL] No access token available")
            return False
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{self.auth_url}/auth/logout",
                    headers={
                        "Authorization": f"Bearer {self.access_token}"
                    }
                )
                
                if response.status_code in [200, 204]:
                    print(f"  [OK] Logout successful")
                    
                    # Verify token is now invalid
                    val_response = await client.post(
                        f"{self.auth_url}/auth/validate",
                        json={"token": self.access_token}
                    )
                    
                    if val_response.status_code != 200:
                        print(f"    [OK] Token properly invalidated after logout")
                        return True
                    else:
                        print(f"    [FAIL] Token still valid after logout!")
                        return False
                else:
                    print(f"  [FAIL] Logout failed: HTTP {response.status_code}")
                    return False
                    
            except Exception as e:
                print(f"  [FAIL] Logout error: {str(e)}")
                return False
    
    async def run_all_tests(self):
        """Run all E2E tests"""
        print("=" * 60)
        print("STAGING AUTHENTICATION E2E TEST")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Auth Service: {self.auth_url}")
        print(f"Backend Service: {self.backend_url}")
        print(f"Frontend Service: {self.frontend_url}")
        
        results = []
        
        # Run tests in sequence
        tests = [
            ("Health Checks", self.test_health_checks),
            ("Dev Login", self.test_dev_login),
            ("Token Validation", self.test_token_validation),
            ("Token Refresh (snake_case)", self.test_token_refresh_snake_case),
            ("Token Refresh (camelCase)", self.test_token_refresh_camel_case),
            ("Authenticated API Call", self.test_authenticated_api_call),
            ("Session Persistence", self.test_session_persistence),
            ("Logout", self.test_logout)
        ]
        
        for name, test_func in tests:
            try:
                result = await test_func()
                results.append((name, result))
            except Exception as e:
                print(f"\nTest '{name}' crashed: {str(e)}")
                results.append((name, False))
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for _, result in results if result)
        total = len(results)
        
        for name, result in results:
            status = "[OK] PASS" if result else "[FAIL] FAIL"
            print(f"{status}: {name}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        if passed == total:
            print("\n[SUCCESS] ALL TESTS PASSED! Authentication is working correctly.")
        else:
            print("\n[WARNING]  Some tests failed. Review the output above for details.")
        
        return passed == total


async def main():
    """Main entry point"""
    tester = StagingAuthE2ETest()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)