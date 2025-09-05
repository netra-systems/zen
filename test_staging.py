#!/usr/bin/env python3
"""Test script for staging environment"""

import asyncio
import httpx
import json
import sys
from datetime import datetime
from typing import Dict, List, Any
from shared.isolated_environment import IsolatedEnvironment

# Staging URLs
BACKEND_URL = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
AUTH_URL = "https://auth.staging.netrasystems.ai"
FRONTEND_URL = "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app"

class StagingTester:
    def __init__(self):
        self.results = []
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def test_health_endpoints(self):
        """Test health endpoints for all services"""
        print("\n[HEALTH] Testing Health Endpoints...")
        
        # Test backend health
        try:
            response = await self.client.get(f"{BACKEND_URL}/health")
            if response.status_code == 200:
                self.results.append(("Backend Health", "PASS", response.json()))
            else:
                self.results.append(("Backend Health", "FAIL", f"Status: {response.status_code}"))
        except Exception as e:
            self.results.append(("Backend Health", "FAIL", str(e)))
            
        # Test auth health  
        try:
            response = await self.client.get(f"{AUTH_URL}/health")
            if response.status_code == 200:
                self.results.append(("Auth Health", "PASS", response.json()))
            else:
                self.results.append(("Auth Health", "FAIL", f"Status: {response.status_code}"))
        except Exception as e:
            self.results.append(("Auth Health", "FAIL", str(e)))
            
        # Test frontend
        try:
            response = await self.client.get(FRONTEND_URL)
            if response.status_code == 200:
                self.results.append(("Frontend", "PASS", "HTML served successfully"))
            else:
                self.results.append(("Frontend", "FAIL", f"Status: {response.status_code}"))
        except Exception as e:
            self.results.append(("Frontend", "FAIL", str(e)))
            
    async def test_api_endpoints(self):
        """Test basic API endpoints"""
        print("\n[API] Testing API Endpoints...")
        
        # Test backend API docs
        try:
            response = await self.client.get(f"{BACKEND_URL}/docs")
            if response.status_code == 200:
                self.results.append(("Backend API Docs", "PASS", "Swagger UI available"))
            else:
                self.results.append(("Backend API Docs", "FAIL", f"Status: {response.status_code}"))
        except Exception as e:
            self.results.append(("Backend API Docs", "FAIL", str(e)))
            
        # Test auth API docs
        try:
            response = await self.client.get(f"{AUTH_URL}/docs")
            if response.status_code == 200:
                self.results.append(("Auth API Docs", "PASS", "Swagger UI available"))
            else:
                self.results.append(("Auth API Docs", "FAIL", f"Status: {response.status_code}"))
        except Exception as e:
            self.results.append(("Auth API Docs", "FAIL", str(e)))
            
    async def test_authentication_flow(self):
        """Test authentication endpoints"""
        print("\n[AUTH] Testing Authentication Flow...")
        
        # Test login endpoint exists
        try:
            response = await self.client.post(
                f"{AUTH_URL}/api/auth/login",
                json={"email": "test@example.com", "password": "testpass"}
            )
            # We expect 401 for invalid credentials
            if response.status_code in [401, 403, 400]:
                self.results.append(("Login Endpoint", "PASS", "Endpoint responds correctly"))
            else:
                self.results.append(("Login Endpoint", "WARN", f"Unexpected status: {response.status_code}"))
        except Exception as e:
            self.results.append(("Login Endpoint", "FAIL", str(e)))
            
        # Test register endpoint exists
        try:
            response = await self.client.post(
                f"{AUTH_URL}/api/auth/register",
                json={
                    "email": f"test_{datetime.now().timestamp()}@example.com",
                    "password": "TestPass123!",
                    "name": "Test User"
                }
            )
            if response.status_code in [200, 201, 400, 409]:
                self.results.append(("Register Endpoint", "PASS", "Endpoint responds correctly"))
            else:
                self.results.append(("Register Endpoint", "WARN", f"Status: {response.status_code}"))
        except Exception as e:
            self.results.append(("Register Endpoint", "FAIL", str(e)))
            
    async def test_websocket_endpoint(self):
        """Test WebSocket endpoint availability"""
        print("\n[WS] Testing WebSocket Endpoint...")
        
        # Just test that the endpoint exists (not full WS connection)
        try:
            response = await self.client.get(f"{BACKEND_URL}/ws")
            # WebSocket endpoint should return 426 Upgrade Required for regular GET
            if response.status_code == 426:
                self.results.append(("WebSocket Endpoint", "PASS", "Endpoint available"))
            else:
                self.results.append(("WebSocket Endpoint", "WARN", f"Status: {response.status_code}"))
        except Exception as e:
            self.results.append(("WebSocket Endpoint", "FAIL", str(e)))
            
    async def test_cors_headers(self):
        """Test CORS configuration"""
        print("\n[CORS] Testing CORS Headers...")
        
        try:
            response = await self.client.options(
                f"{BACKEND_URL}/health",
                headers={"Origin": "https://netra-frontend-staging-pnovr5vsba-uc.a.run.app"}
            )
            cors_headers = response.headers.get("access-control-allow-origin")
            if cors_headers:
                self.results.append(("CORS Headers", "PASS", f"Allow-Origin: {cors_headers}"))
            else:
                self.results.append(("CORS Headers", "WARN", "No CORS headers found"))
        except Exception as e:
            self.results.append(("CORS Headers", "FAIL", str(e)))
            
    async def run_all_tests(self):
        """Run all staging tests"""
        print("=" * 60)
        print("STAGING ENVIRONMENT TEST SUITE")
        print("=" * 60)
        print(f"Backend URL: {BACKEND_URL}")
        print(f"Auth URL: {AUTH_URL}")
        print(f"Frontend URL: {FRONTEND_URL}")
        print("=" * 60)
        
        await self.test_health_endpoints()
        await self.test_api_endpoints()
        await self.test_authentication_flow()
        await self.test_websocket_endpoint()
        await self.test_cors_headers()
        
        await self.client.aclose()
        
        # Print results
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)
        
        passed = 0
        failed = 0
        warned = 0
        
        for test_name, status, details in self.results:
            print(f"[{status}] {test_name}")
            if isinstance(details, dict):
                print(f"    {json.dumps(details, indent=2)}")
            else:
                print(f"    {details}")
            
            if status == "PASS":
                passed += 1
            elif status == "FAIL":
                failed += 1
            else:
                warned += 1
                
        print("\n" + "=" * 60)
        print(f"SUMMARY: {passed} passed, {failed} failed, {warned} warnings")
        print("=" * 60)
        
        return failed == 0

async def main():
    tester = StagingTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())