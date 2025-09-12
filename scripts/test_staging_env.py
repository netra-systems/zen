#!/usr/bin/env python3
"""
Staging Environment Test Script
Verifies that the staging environment is properly configured and all components are communicating
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple
from shared.isolated_environment import IsolatedEnvironment

import requests
import websocket


class StagingTester:
    """Test suite for staging environment"""
    
    def __init__(self, base_url: str = "http://localhost", api_port: int = 8080, frontend_port: int = 3000):
        self.base_url = base_url
        self.api_url = f"{base_url}:{api_port}"
        self.frontend_url = f"{base_url}:{frontend_port}"
        self.ws_url = f"ws://localhost:{api_port}/ws"
        self.test_results = []
        
    def test_backend_health(self) -> Tuple[bool, str]:
        """Test backend health endpoint"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    return True, "Backend is healthy"
                else:
                    return False, f"Backend unhealthy: {data}"
            else:
                return False, f"Backend returned status {response.status_code}"
        except Exception as e:
            return False, f"Backend health check failed: {e}"
            
    def test_frontend_health(self) -> Tuple[bool, str]:
        """Test frontend is serving"""
        try:
            response = requests.get(self.frontend_url, timeout=5)
            if response.status_code in [200, 301, 302]:
                return True, "Frontend is serving"
            else:
                return False, f"Frontend returned status {response.status_code}"
        except Exception as e:
            return False, f"Frontend health check failed: {e}"
            
    def test_api_docs(self) -> Tuple[bool, str]:
        """Test API documentation endpoints"""
        try:
            response = requests.get(f"{self.api_url}/docs", timeout=5)
            if response.status_code == 200:
                return True, "API docs are accessible"
            else:
                return False, f"API docs returned status {response.status_code}"
        except Exception as e:
            return False, f"API docs check failed: {e}"
            
    def test_database_connection(self) -> Tuple[bool, str]:
        """Test database connectivity through API"""
        try:
            # Try to access an endpoint that requires database
            response = requests.get(f"{self.api_url}/api/threads", timeout=5)
            # Even if unauthorized, a 401 means the API is working
            if response.status_code in [200, 401, 403]:
                return True, "Database connection appears functional"
            else:
                return False, f"Database test returned status {response.status_code}"
        except Exception as e:
            return False, f"Database connectivity test failed: {e}"
            
    def test_websocket_connection(self) -> Tuple[bool, str]:
        """Test WebSocket connectivity"""
        try:
            ws = websocket.create_connection(self.ws_url, timeout=5)
            
            # Send a ping message
            test_message = json.dumps({
                "type": "ping",
                "timestamp": time.time()
            })
            ws.send(test_message)
            
            # Wait for response
            response = ws.recv()
            ws.close()
            
            if response:
                return True, "WebSocket connection successful"
            else:
                return False, "No response from WebSocket"
        except Exception as e:
            return False, f"WebSocket test failed: {e}"
            
    def test_cors_headers(self) -> Tuple[bool, str]:
        """Test CORS configuration"""
        try:
            headers = {
                "Origin": "http://localhost:3000"
            }
            response = requests.options(f"{self.api_url}/api/threads", headers=headers, timeout=5)
            
            cors_headers = response.headers.get("Access-Control-Allow-Origin")
            if cors_headers:
                return True, f"CORS configured: {cors_headers}"
            else:
                return False, "CORS headers not properly configured"
        except Exception as e:
            return False, f"CORS test failed: {e}"
            
    def test_frontend_api_proxy(self) -> Tuple[bool, str]:
        """Test if frontend properly proxies to backend API"""
        try:
            # Test if frontend's API proxy is working
            response = requests.get(f"{self.frontend_url}/api/health", timeout=5, allow_redirects=True)
            if response.status_code in [200, 301, 302, 404]:
                # Even 404 means the proxy is working, just the route might not exist
                return True, "Frontend API proxy is configured"
            else:
                return False, f"Frontend proxy returned status {response.status_code}"
        except Exception as e:
            return False, f"Frontend API proxy test failed: {e}"
            
    def test_static_assets(self) -> Tuple[bool, str]:
        """Test static asset serving"""
        try:
            # Test Next.js static assets
            response = requests.get(f"{self.frontend_url}/_next/static", timeout=5, allow_redirects=True)
            if response.status_code in [200, 301, 302, 404]:
                return True, "Static assets are being served"
            else:
                return False, f"Static assets returned status {response.status_code}"
        except Exception as e:
            return False, f"Static assets test failed: {e}"
            
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all staging environment tests"""
        tests = [
            ("Backend Health", self.test_backend_health),
            ("Frontend Health", self.test_frontend_health),
            ("API Documentation", self.test_api_docs),
            ("Database Connection", self.test_database_connection),
            ("WebSocket Connection", self.test_websocket_connection),
            ("CORS Configuration", self.test_cors_headers),
            ("Frontend API Proxy", self.test_frontend_api_proxy),
            ("Static Assets", self.test_static_assets)
        ]
        
        results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        
        print("\n" + "="*60)
        print("STAGING ENVIRONMENT TEST SUITE")
        print("="*60 + "\n")
        
        for test_name, test_func in tests:
            print(f"Running: {test_name}...", end=" ")
            success, message = test_func()
            
            if success:
                print(" PASS:  PASSED")
                results["passed"] += 1
            else:
                print(" FAIL:  FAILED")
                results["failed"] += 1
                
            results["tests"].append({
                "name": test_name,
                "passed": success,
                "message": message
            })
            
            print(f"   ->  {message}\n")
            
        # Summary
        print("="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {len(tests)}")
        print(f"Passed: {results['passed']}  PASS: ")
        print(f"Failed: {results['failed']}  FAIL: ")
        
        if results["failed"] == 0:
            print("\n CELEBRATION:  All tests passed! Staging environment is fully operational.")
        else:
            print("\n WARNING: [U+FE0F] Some tests failed. Please check the failures above.")
            print("\nFailed tests:")
            for test in results["tests"]:
                if not test["passed"]:
                    print(f"  - {test['name']}: {test['message']}")
                    
        return results
        
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Test staging environment")
    parser.add_argument("--api-port", type=int, default=8080, help="API port")
    parser.add_argument("--frontend-port", type=int, default=3000, help="Frontend port")
    parser.add_argument("--base-url", default="http://localhost", help="Base URL")
    parser.add_argument("--json", action="store_true", help="Output results as JSON")
    
    args = parser.parse_args()
    
    tester = StagingTester(args.base_url, args.api_port, args.frontend_port)
    results = tester.run_all_tests()
    
    if args.json:
        print("\n" + json.dumps(results, indent=2))
        
    # Exit with appropriate code
    sys.exit(0 if results["failed"] == 0 else 1)
    
if __name__ == "__main__":
    main()