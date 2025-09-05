#!/usr/bin/env python3
"""
Direct staging deployment test script.
Tests the deployed services on GCP staging environment.
"""

import json
import sys
import time
from typing import Dict, Any
import requests
from shared.isolated_environment import IsolatedEnvironment


class StagingTester:
    def __init__(self):
        self.backend_url = "https://netra-backend-staging-701982941522.us-central1.run.app"
        self.auth_url = "https://netra-auth-service-701982941522.us-central1.run.app"
        self.results = []
        
    def log(self, message: str, level: str = "INFO"):
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        # Replace Unicode characters for Windows compatibility
        message = message.replace("✅", "[PASS]").replace("❌", "[FAIL]")
        print(f"[{timestamp}] [{level}] {message}")
        
    def test_endpoint(self, name: str, url: str, expected_status: int = 200) -> bool:
        """Test a single endpoint."""
        try:
            self.log(f"Testing {name}: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == expected_status:
                self.log(f"✅ {name} passed (status: {response.status_code})", "SUCCESS")
                self.results.append({"test": name, "url": url, "status": "PASSED", "response_code": response.status_code})
                return True
            else:
                self.log(f"❌ {name} failed (expected: {expected_status}, got: {response.status_code})", "ERROR")
                self.results.append({"test": name, "url": url, "status": "FAILED", "response_code": response.status_code, "expected": expected_status})
                return False
        except Exception as e:
            self.log(f"❌ {name} failed with exception: {str(e)}", "ERROR")
            self.results.append({"test": name, "url": url, "status": "ERROR", "error": str(e)})
            return False
    
    def test_json_endpoint(self, name: str, url: str, expected_keys: list = None) -> bool:
        """Test a JSON endpoint and validate response structure."""
        try:
            self.log(f"Testing JSON endpoint {name}: {url}")
            response = requests.get(url, timeout=10)
            
            if response.status_code != 200:
                self.log(f"❌ {name} failed (status: {response.status_code})", "ERROR")
                self.results.append({"test": name, "url": url, "status": "FAILED", "response_code": response.status_code})
                return False
            
            data = response.json()
            
            if expected_keys:
                missing_keys = [key for key in expected_keys if key not in data]
                if missing_keys:
                    self.log(f"❌ {name} missing keys: {missing_keys}", "ERROR")
                    self.results.append({"test": name, "url": url, "status": "FAILED", "missing_keys": missing_keys})
                    return False
            
            self.log(f"✅ {name} passed - Response: {json.dumps(data, indent=2)}", "SUCCESS")
            self.results.append({"test": name, "url": url, "status": "PASSED", "response": data})
            return True
            
        except Exception as e:
            self.log(f"❌ {name} failed with exception: {str(e)}", "ERROR")
            self.results.append({"test": name, "url": url, "status": "ERROR", "error": str(e)})
            return False
    
    def run_tests(self):
        """Run all staging deployment tests."""
        self.log("="*60)
        self.log("Starting Staging Deployment Tests")
        self.log("="*60)
        
        all_passed = True
        
        # Test backend health
        all_passed &= self.test_json_endpoint(
            "Backend Health",
            f"{self.backend_url}/health",
            expected_keys=["status", "service", "version"]
        )
        
        # Test auth service health
        all_passed &= self.test_json_endpoint(
            "Auth Service Health",
            f"{self.auth_url}/health",
            expected_keys=["status", "service", "version", "environment", "database_status"]
        )
        
        # Test backend API docs
        all_passed &= self.test_endpoint(
            "Backend API Docs",
            f"{self.backend_url}/docs",
            expected_status=200
        )
        
        # Test auth API docs
        all_passed &= self.test_endpoint(
            "Auth API Docs",
            f"{self.auth_url}/docs",
            expected_status=200
        )
        
        # Test backend metrics endpoint
        all_passed &= self.test_endpoint(
            "Backend Metrics",
            f"{self.backend_url}/metrics",
            expected_status=200
        )
        
        # Test auth service metrics
        all_passed &= self.test_endpoint(
            "Auth Metrics",
            f"{self.auth_url}/metrics",
            expected_status=200
        )
        
        # Test backend root endpoint
        all_passed &= self.test_json_endpoint(
            "Backend Root",
            f"{self.backend_url}/",
            expected_keys=["message", "version", "service"]
        )
        
        # Print summary
        self.log("="*60)
        self.log("Test Results Summary")
        self.log("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASSED")
        failed = sum(1 for r in self.results if r["status"] == "FAILED")
        errors = sum(1 for r in self.results if r["status"] == "ERROR")
        
        self.log(f"Total Tests: {len(self.results)}")
        self.log(f"Passed: {passed}", "SUCCESS" if passed > 0 else "INFO")
        self.log(f"Failed: {failed}", "ERROR" if failed > 0 else "INFO")
        self.log(f"Errors: {errors}", "ERROR" if errors > 0 else "INFO")
        
        if all_passed:
            self.log("✅ All tests PASSED!", "SUCCESS")
        else:
            self.log("❌ Some tests FAILED!", "ERROR")
        
        # Save results to file
        report_file = f"staging_test_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "backend_url": self.backend_url,
                "auth_url": self.auth_url,
                "summary": {
                    "total": len(self.results),
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "success": all_passed
                },
                "results": self.results
            }, f, indent=2)
        
        self.log(f"Report saved to: {report_file}")
        
        return 0 if all_passed else 1


if __name__ == "__main__":
    tester = StagingTester()
    sys.exit(tester.run_tests())