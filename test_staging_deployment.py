#!/usr/bin/env python3
"""
Test staging deployment for end-to-end functionality.
Tests all critical paths in the staging environment.
"""

import requests
import json
import time
import sys
import os
from typing import Dict, Any, Tuple
from datetime import datetime

# Fix Unicode for Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')


class StagingDeploymentTester:
    """Comprehensive staging deployment tester."""
    
    def __init__(self):
        """Initialize staging URLs."""
        self.backend_url = "https://netra-backend-jmujvwwf7q-uc.a.run.app"
        self.auth_url = "https://netra-auth-jmujvwwf7q-uc.a.run.app"
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "environment": "staging",
            "tests": [],
            "summary": {}
        }
        
    def test_backend_health(self) -> Tuple[bool, str]:
        """Test backend health endpoint."""
        test_name = "Backend Health Check"
        try:
            response = requests.get(
                f"{self.backend_url}/health",
                timeout=10,
                allow_redirects=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self._record_test(test_name, True, "Backend is healthy")
                    return True, "Backend healthy"
                else:
                    self._record_test(test_name, False, f"Unhealthy status: {data}")
                    return False, f"Unhealthy: {data}"
            else:
                self._record_test(test_name, False, f"HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            self._record_test(test_name, False, str(e))
            return False, str(e)
    
    def test_auth_health(self) -> Tuple[bool, str]:
        """Test auth service health endpoint."""
        test_name = "Auth Service Health Check"
        try:
            response = requests.get(
                f"{self.auth_url}/health",
                timeout=10,
                allow_redirects=False
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self._record_test(test_name, True, "Auth service is healthy")
                    return True, "Auth healthy"
                else:
                    self._record_test(test_name, False, f"Unhealthy status: {data}")
                    return False, f"Unhealthy: {data}"
            else:
                self._record_test(test_name, False, f"HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            self._record_test(test_name, False, str(e))
            return False, str(e)
    
    def test_api_docs(self) -> Tuple[bool, str]:
        """Test API documentation endpoints."""
        test_name = "API Documentation"
        try:
            response = requests.get(
                f"{self.backend_url}/docs",
                timeout=10,
                allow_redirects=True
            )
            
            if response.status_code == 200:
                if "swagger" in response.text.lower() or "openapi" in response.text.lower():
                    self._record_test(test_name, True, "API docs accessible")
                    return True, "Docs available"
                else:
                    self._record_test(test_name, False, "Docs page invalid")
                    return False, "Invalid docs"
            else:
                self._record_test(test_name, False, f"HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            self._record_test(test_name, False, str(e))
            return False, str(e)
    
    def test_cors_headers(self) -> Tuple[bool, str]:
        """Test CORS configuration."""
        test_name = "CORS Configuration"
        try:
            # Test preflight request
            response = requests.options(
                f"{self.backend_url}/health",
                headers={
                    "Origin": "https://app.netrasystems.ai",
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization"
                },
                timeout=10
            )
            
            cors_headers = {
                "Access-Control-Allow-Origin",
                "Access-Control-Allow-Methods",
                "Access-Control-Allow-Headers"
            }
            
            missing_headers = []
            for header in cors_headers:
                if header not in response.headers:
                    missing_headers.append(header)
            
            if not missing_headers:
                self._record_test(test_name, True, "CORS properly configured")
                return True, "CORS OK"
            else:
                msg = f"Missing headers: {missing_headers}"
                self._record_test(test_name, False, msg)
                return False, msg
                
        except Exception as e:
            self._record_test(test_name, False, str(e))
            return False, str(e)
    
    def test_websocket_endpoint(self) -> Tuple[bool, str]:
        """Test WebSocket endpoint availability."""
        test_name = "WebSocket Endpoint"
        try:
            # Test WebSocket info endpoint
            response = requests.get(
                f"{self.backend_url}/ws/info",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "endpoint" in data:
                    self._record_test(test_name, True, f"WebSocket available at {data['endpoint']}")
                    return True, "WebSocket ready"
                else:
                    self._record_test(test_name, False, "Invalid WebSocket info")
                    return False, "Invalid info"
            else:
                self._record_test(test_name, False, f"HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            self._record_test(test_name, False, str(e))
            return False, str(e)
    
    def test_authentication_flow(self) -> Tuple[bool, str]:
        """Test authentication flow."""
        test_name = "Authentication Flow"
        try:
            # Test OAuth config endpoint
            response = requests.get(
                f"{self.auth_url}/auth/oauth/config",
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                if "client_id" in data:
                    self._record_test(test_name, True, "OAuth configured")
                    return True, "Auth ready"
                else:
                    self._record_test(test_name, False, "OAuth not configured")
                    return False, "OAuth missing"
            else:
                self._record_test(test_name, False, f"HTTP {response.status_code}")
                return False, f"HTTP {response.status_code}"
                
        except Exception as e:
            self._record_test(test_name, False, str(e))
            return False, str(e)
    
    def _record_test(self, name: str, passed: bool, details: str):
        """Record test result."""
        self.results["tests"].append({
            "name": name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all staging deployment tests."""
        print("\n" + "=" * 60)
        print("🚀 STAGING DEPLOYMENT TEST SUITE")
        print("=" * 60)
        print(f"Backend URL: {self.backend_url}")
        print(f"Auth URL: {self.auth_url}")
        print("-" * 60)
        
        # Run tests
        tests = [
            ("Backend Health", self.test_backend_health),
            ("Auth Health", self.test_auth_health),
            ("API Documentation", self.test_api_docs),
            ("CORS Configuration", self.test_cors_headers),
            ("WebSocket Endpoint", self.test_websocket_endpoint),
            ("Authentication Flow", self.test_authentication_flow)
        ]
        
        passed_count = 0
        failed_count = 0
        
        for test_name, test_func in tests:
            print(f"\n🧪 Testing: {test_name}")
            success, message = test_func()
            
            if success:
                print(f"   ✅ PASSED: {message}")
                passed_count += 1
            else:
                print(f"   ❌ FAILED: {message}")
                failed_count += 1
        
        # Calculate summary
        total_tests = passed_count + failed_count
        success_rate = (passed_count / total_tests * 100) if total_tests > 0 else 0
        
        self.results["summary"] = {
            "total_tests": total_tests,
            "passed": passed_count,
            "failed": failed_count,
            "success_rate": f"{success_rate:.1f}%",
            "deployment_status": "READY" if success_rate >= 80 else "NEEDS_ATTENTION"
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_count} ✅")
        print(f"Failed: {failed_count} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"\nDeployment Status: {self.results['summary']['deployment_status']}")
        
        if failed_count > 0:
            print("\n⚠️ FAILED TESTS:")
            for test in self.results["tests"]:
                if not test["passed"]:
                    print(f"  - {test['name']}: {test['details']}")
        
        # Save results
        with open("staging_deployment_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to staging_deployment_test_results.json")
        
        return self.results


def main():
    """Main test runner."""
    tester = StagingDeploymentTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if results["summary"]["deployment_status"] == "READY":
        print("\n✅ STAGING DEPLOYMENT IS READY FOR USE")
        sys.exit(0)
    else:
        print("\n⚠️ STAGING DEPLOYMENT NEEDS ATTENTION")
        sys.exit(1)


if __name__ == "__main__":
    main()