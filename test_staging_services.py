#!/usr/bin/env python3
"""
Quick staging services test script
Tests the deployed staging services directly via HTTP
"""

import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any


class StagingTester:
    def __init__(self):
        self.backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
        self.auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
        self.frontend_url = "https://netra-frontend-staging-701982941522.us-central1.run.app"
        self.results = []
        
    async def test_backend_health(self) -> bool:
        """Test backend health endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.backend_url}/health", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.results.append(("✅", "Backend Health", f"Status: {data.get('status', 'unknown')}"))
                        return True
                    else:
                        self.results.append(("❌", "Backend Health", f"HTTP {response.status}"))
                        return False
        except Exception as e:
            self.results.append(("❌", "Backend Health", str(e)))
            return False
            
    async def test_auth_health(self) -> bool:
        """Test auth service health endpoint"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.auth_url}/health", timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        self.results.append(("✅", "Auth Health", f"Status: {data.get('status', 'unknown')}"))
                        return True
                    else:
                        self.results.append(("❌", "Auth Health", f"HTTP {response.status}"))
                        return False
        except Exception as e:
            self.results.append(("❌", "Auth Health", str(e)))
            return False
            
    async def test_frontend(self) -> bool:
        """Test frontend is accessible"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.frontend_url, timeout=10) as response:
                    if response.status == 200:
                        self.results.append(("✅", "Frontend", "Accessible"))
                        return True
                    else:
                        self.results.append(("❌", "Frontend", f"HTTP {response.status}"))
                        return False
        except Exception as e:
            self.results.append(("❌", "Frontend", str(e)))
            return False
            
    async def test_backend_api(self) -> bool:
        """Test backend API endpoints"""
        try:
            async with aiohttp.ClientSession() as session:
                # Test docs endpoint
                async with session.get(f"{self.backend_url}/docs", timeout=10, allow_redirects=True) as response:
                    if response.status == 200:
                        self.results.append(("✅", "Backend API Docs", "Accessible"))
                        return True
                    else:
                        self.results.append(("⚠️", "Backend API Docs", f"HTTP {response.status}"))
                        return False
        except Exception as e:
            self.results.append(("⚠️", "Backend API Docs", str(e)))
            return False
            
    async def test_websocket_endpoint(self) -> bool:
        """Test WebSocket endpoint availability"""
        try:
            # Just check if the WebSocket endpoint responds
            ws_url = self.backend_url.replace("https://", "wss://") + "/ws"
            async with aiohttp.ClientSession() as session:
                # Try to connect to WebSocket (it may reject without auth, but that's ok)
                try:
                    async with session.ws_connect(ws_url, timeout=5) as ws:
                        self.results.append(("✅", "WebSocket Endpoint", "Connectable"))
                        await ws.close()
                        return True
                except aiohttp.WSServerHandshakeError as e:
                    # 401/403 means endpoint exists but needs auth
                    if e.status in [401, 403]:
                        self.results.append(("✅", "WebSocket Endpoint", "Available (auth required)"))
                        return True
                    else:
                        self.results.append(("❌", "WebSocket Endpoint", f"HTTP {e.status}"))
                        return False
        except Exception as e:
            self.results.append(("⚠️", "WebSocket Endpoint", f"Connection failed: {str(e)[:50]}"))
            return False
            
    async def test_cors_headers(self) -> bool:
        """Test CORS configuration"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Origin": "https://app.staging.netrasystems.ai",
                    "Access-Control-Request-Method": "GET"
                }
                async with session.options(f"{self.backend_url}/health", headers=headers, timeout=10) as response:
                    cors_headers = response.headers.get("Access-Control-Allow-Origin")
                    if cors_headers:
                        self.results.append(("✅", "CORS Headers", f"Configured: {cors_headers}"))
                        return True
                    else:
                        # Try a regular GET to see if CORS is on response
                        async with session.get(f"{self.backend_url}/health", headers={"Origin": "https://app.staging.netrasystems.ai"}, timeout=10) as get_response:
                            cors_on_get = get_response.headers.get("Access-Control-Allow-Origin")
                            if cors_on_get:
                                self.results.append(("✅", "CORS Headers", f"Present: {cors_on_get}"))
                                return True
                            else:
                                self.results.append(("⚠️", "CORS Headers", "Not configured"))
                                return False
        except Exception as e:
            self.results.append(("⚠️", "CORS Headers", str(e)[:50]))
            return False
            
    async def run_all_tests(self):
        """Run all staging tests"""
        print("\n" + "="*60)
        print("STAGING ENVIRONMENT TESTS")
        print("="*60)
        print(f"Backend URL: {self.backend_url}")
        print(f"Auth URL: {self.auth_url}")
        print(f"Frontend URL: {self.frontend_url}")
        print("="*60 + "\n")
        
        tests = [
            self.test_backend_health(),
            self.test_auth_health(),
            self.test_frontend(),
            self.test_backend_api(),
            self.test_websocket_endpoint(),
            self.test_cors_headers()
        ]
        
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        # Print results
        print("\nTEST RESULTS:")
        print("-" * 60)
        for status, test_name, details in self.results:
            # Use text labels instead of emojis for Windows compatibility
            status_text = "PASS" if status == "✅" else "FAIL" if status == "❌" else "WARN"
            print(f"[{status_text}] {test_name}: {details}")
        
        # Summary
        passed = sum(1 for r in self.results if r[0] == "✅")
        failed = sum(1 for r in self.results if r[0] == "❌")
        warnings = sum(1 for r in self.results if r[0] == "⚠️")
        
        print("\n" + "="*60)
        print(f"SUMMARY: {passed} passed, {failed} failed, {warnings} warnings")
        
        if failed == 0:
            print("[SUCCESS] All critical tests passed! Staging services are operational.")
        else:
            print("[FAILURE] Some tests failed. Check the services and configurations.")
        print("="*60)
        
        return failed == 0


async def main():
    tester = StagingTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())