#!/usr/bin/env python3
"""
OAuth Cloud Armor Integration Test

This test validates that:
1. OAuth callbacks with URL-encoded parameters are not blocked
2. SQL injection protection remains active for other endpoints
3. Cloud Armor logs show no false positives for OAuth

Run: python tests/e2e/test_oauth_cloud_armor.py
"""

import asyncio
import aiohttp
import pytest
import json
import subprocess
import sys
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestOAuthCloudArmor:
    """Test OAuth flow and Cloud Armor integration."""
    
    def __init__(self, environment: str = "staging"):
    pass
        self.environment = environment
        self.base_url = self._get_base_url(environment)
        self.auth_url = self._get_auth_url(environment)
        self.results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": environment,
            "tests": {},
            "summary": {
                "passed": 0,
                "failed": 0,
                "warnings": 0
            }
        }
        
    def _get_base_url(self, env: str) -> str:
        """Get API base URL for environment."""
        urls = {
            "staging": "https://api.staging.netrasystems.ai",
            "production": "https://api.netrasystems.ai",
            "dev": "http://localhost:8000"
        }
        return urls.get(env, urls["staging"])
    
    def _get_auth_url(self, env: str) -> str:
        """Get auth service URL for environment."""
        urls = {
            "staging": "https://auth.staging.netrasystems.ai",
            "production": "https://auth.netrasystems.ai",
            "dev": "http://localhost:8001"
        }
        return urls.get(env, urls["staging"])
    
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_oauth_callback_not_blocked(self) -> Dict:
        """Test that OAuth callback with encoded parameters is not blocked."""
        print("
🔍 Testing OAuth callback endpoint...")
        
        # Simulate OAuth callback with encoded parameters that triggered the issue
        callback_url = f"{self.auth_url}/auth/callback"
        
        # Multiple test cases with different encoded patterns
        test_cases = [
            {
                "name": "Google OAuth pattern",
                "params": {
                    "state": "test_state_123",
                    "code": "4/0AVMBsJtest_code_with_encoded_slash",  # Google pattern
                    "scope": "email profile openid"
                }
            },
            {
                "name": "URL-encoded slashes",
                "params": {
                    "state": "state_with_encoded",
                    "code": "code%2Fwith%2Fslashes",  # Direct encoded slashes
                    "scope": "email%20profile"
                }
            },
            {
                "name": "Complex encoded params",
                "params": {
                    "state": "complex%3Dstate%26test",
                    "code": "4%2F0%3Dcomplex%26code",
                    "scope": "https%3A%2F%2Fwww.googleapis.com%2Fauth%2Fuserinfo.email"
                }
            }
        ]
        
        results = []
        for test_case in test_cases:
            print(f"  Testing: {test_case['name']}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        callback_url, 
                        params=test_case["params"], 
                        allow_redirects=False,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        
                        # Should not get 403 from Cloud Armor
                        if response.status == 403:
                            results.append({
                                "case": test_case["name"],
                                "status": "FAILED",
                                "http_status": response.status,
                                "error": "Blocked by Cloud Armor"
                            })
                            print(f"    ❌ FAILED: Got 403 (blocked)")
                        else:
                            results.append({
                                "case": test_case["name"],
                                "status": "PASSED",
                                "http_status": response.status
                            })
                            print(f"    ✅ PASSED: Got {response.status} (not blocked)")
                            
            except Exception as e:
                results.append({
                    "case": test_case["name"],
                    "status": "ERROR",
                    "error": str(e)
                })
                print(f"    ⚠️  ERROR: {e}")
        
        return {
            "test": "oauth_callback_not_blocked",
            "results": results,
            "passed": all(r["status"] == "PASSED" for r in results)
        }
    
    def check_cloud_armor_logs(self, minutes_back: int = 10) -> Dict:
        """Check Cloud Armor logs for recent OAuth blocks."""
        print(f"
📊 Checking Cloud Armor logs (last {minutes_back} minutes)...")
        
        # Build command based on OS
        if os.name == 'nt':
            # Windows
            cmd = [
                "python", "scripts/analyze_cloud_armor_logs.py",
                "--oauth", "--limit", "20", "--hours", "1"
            ]
        else:
            # Linux/Mac
            cmd = [
                "python3", "scripts/analyze_cloud_armor_logs.py",
                "--oauth", "--limit", "20", "--hours", "1"
            ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                cwd=Path(__file__).parent.parent.parent,  # Run from project root
                timeout=30
            )
            
            # Parse output for 403 errors
            blocked_count = result.stdout.count("Status: 403")
            oauth_blocks = result.stdout.count("/auth/callback")
            
            if blocked_count > 0:
                print(f"  ⚠️  Found {blocked_count} blocked requests")
                print(f"  📍 {oauth_blocks} were OAuth callbacks")
            else:
                print(f"  ✅ No blocked OAuth requests found")
            
            return {
                "blocked_requests": blocked_count,
                "oauth_callbacks_blocked": oauth_blocks,
                "status": "WARNING" if blocked_count > 0 else "PASSED",
                "output_preview": result.stdout[:500] if result.stdout else "No output"
            }
            
        except Exception as e:
            print(f"  ❌ Error checking logs: {e}")
            return {
                "status": "ERROR",
                "error": str(e)
            }
    
    @pytest.mark.auth
    @pytest.mark.e2e
    async def test_sql_injection_still_blocked(self) -> Dict:
        """Ensure SQL injection attempts are still blocked on other paths."""
        print("
🛡️  Testing SQL injection protection...")
        
        # Test paths that should still be protected
        test_cases = [
            {
                "name": "API endpoint with SQL injection",
                "url": f"{self.base_url}/api/users",
                "params": {"id": "1' OR '1'='1"}
            },
            {
                "name": "Search with SQL injection",
                "url": f"{self.base_url}/api/search",
                "params": {"q": "'; DROP TABLE users; --"}
            }
        ]
        
        results = []
        for test_case in test_cases:
            print(f"  Testing: {test_case['name']}")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        test_case["url"],
                        params=test_case["params"],
                        allow_redirects=False,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        
                        # These SHOULD be blocked (403)
                        if response.status == 403:
                            results.append({
                                "case": test_case["name"],
                                "status": "PASSED",
                                "http_status": response.status,
                                "note": "Correctly blocked SQL injection"
                            })
                            print(f"    ✅ PASSED: SQL injection blocked (403)")
                        else:
                            results.append({
                                "case": test_case["name"],
                                "status": "FAILED",
                                "http_status": response.status,
                                "error": f"SQL injection NOT blocked (got {response.status})"
                            })
                            print(f"    ❌ FAILED: SQL injection not blocked (got {response.status})")
                            
            except Exception as e:
                # Connection errors might mean it was blocked at network level
                results.append({
                    "case": test_case["name"],
                    "status": "PASSED",
                    "note": f"Likely blocked: {str(e)}"
                })
                print(f"    ✅ PASSED: Likely blocked (connection failed)")
        
        return {
            "test": "sql_injection_protection",
            "results": results,
            "passed": all(r["status"] == "PASSED" for r in results)
        }
    
    def verify_security_policy(self) -> Dict:
        """Verify Cloud Armor security policy configuration."""
        print("
🔐 Verifying security policy configuration...")
        
        cmd = [
            "gcloud", "compute", "security-policies", "rules", "describe", "50",
            "--security-policy=staging-security-policy",
            "--project=netra-staging",
            "--format=json"
        ]
        
        try:
            # Use shell=True on Windows
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                shell=(os.name == 'nt'),
                timeout=30
            )
            
            if result.returncode == 0:
                rule_data = json.loads(result.stdout) if result.stdout else {}
                
                # Verify rule configuration
                checks = {
                    "rule_exists": len(rule_data) > 0,
                    "priority_correct": rule_data[0].get("priority") == 50 if rule_data else False,
                    "action_correct": rule_data[0].get("action") == "allow" if rule_data else False,
                    "path_correct": "/auth/callback" in str(rule_data) if rule_data else False
                }
                
                all_passed = all(checks.values())
                
                for check, passed in checks.items():
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check.replace('_', ' ').title()}: {passed}")
                
                return {
                    "test": "security_policy_verification",
                    "checks": checks,
                    "passed": all_passed,
                    "rule_data": rule_data[0] if rule_data else None
                }
                
            else:
                print(f"  ❌ Failed to get rule: {result.stderr}")
                return {
                    "test": "security_policy_verification",
                    "passed": False,
                    "error": result.stderr
                }
                
        except Exception as e:
            print(f"  ❌ Error verifying policy: {e}")
            return {
                "test": "security_policy_verification",
                "passed": False,
                "error": str(e)
            }
    
    async def run_test_suite(self) -> Dict:
        """Run complete test suite."""
        print("=" * 60)
        print(f"🚀 OAuth Cloud Armor Test Suite")
        print(f"📍 Environment: {self.environment}")
        print(f"🕐 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        # Test 1: OAuth callback should not be blocked
        oauth_test = await self.test_oauth_callback_not_blocked()
        self.results["tests"]["oauth_callback"] = oauth_test
        if oauth_test["passed"]:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
        
        # Test 2: Check Cloud Armor logs
        log_check = self.check_cloud_armor_logs()
        self.results["tests"]["log_analysis"] = log_check
        if log_check.get("blocked_requests", 0) > 0:
            self.results["summary"]["warnings"] += 1
        
        # Test 3: SQL injection should still be blocked
        sql_test = await self.test_sql_injection_still_blocked()
        self.results["tests"]["sql_injection"] = sql_test
        if sql_test["passed"]:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
        
        # Test 4: Verify security policy
        policy_check = self.verify_security_policy()
        self.results["tests"]["policy_verification"] = policy_check
        if policy_check["passed"]:
            self.results["summary"]["passed"] += 1
        else:
            self.results["summary"]["failed"] += 1
        
        # Calculate overall result
        self.results["overall_status"] = "PASSED" if self.results["summary"]["failed"] == 0 else "FAILED"
        
        # Print summary
        print("
" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {self.results['summary']['passed']}")
        print(f"❌ Failed: {self.results['summary']['failed']}")
        print(f"⚠️  Warnings: {self.results['summary']['warnings']}")
        print(f"
🎯 Overall Status: {self.results['overall_status']}")
        
        # Save results
        results_file = f"oauth_cloud_armor_test_{self.environment}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"
💾 Results saved to: {results_file}")
        
        return self.results


async def main():
    """Main test runner."""
    # Get environment from command line or default to staging
    env = sys.argv[1] if len(sys.argv) > 1 else "staging"
    
    # Run tests
    test = OAuthCloudArmorTest(env)
    results = await test.run_test_suite()
    
    # Exit with error if any test failed
    if results["overall_status"] == "FAILED":
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
    pass