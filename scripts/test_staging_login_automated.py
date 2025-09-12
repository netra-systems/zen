from shared.isolated_environment import get_env
#!/usr/bin/env python3
"""
env = get_env()
Automated staging login test script for agent testing.
This script provides multiple methods for testing staging login without manual OAuth flow.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
import requests
from datetime import datetime, timezone
import argparse
import io

# Set UTF-8 encoding for output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Simple environment configuration
class IsolatedEnvironment:
    def get(self, key, default=None):
        return env.get(key, default)


class StagingLoginTester:
    """Test staging login functionality with automated methods"""
    
    def __init__(self, method: str = "mock"):
        self.env = IsolatedEnvironment()
        self.method = method
        self.base_url = "https://app.staging.netrasystems.ai"
        self.api_url = "https://api.staging.netrasystems.ai"
        self.auth_url = "https://auth.staging.netrasystems.ai"
        self.session = requests.Session()
        self.test_results = []
        
    def test_mock_login(self) -> Dict[str, Any]:
        """
        Test login using mock authentication.
        This simulates a logged-in user without actual OAuth.
        """
        print("\n[Mock Login Test]")
        print("-" * 40)
        
        # Step 1: Create mock session
        mock_user = {
            "id": "mock-user-001",
            "email": "test.agent@staging.netrasystems.ai",
            "name": "Test Agent",
            "picture": "https://ui-avatars.com/api/?name=Test+Agent"
        }
        
        # Step 2: Test health endpoint first
        print("Testing health endpoint...")
        try:
            response = self.session.get(f"{self.api_url}/health", timeout=10)
            health_status = response.json() if response.status_code == 200 else {"error": response.text}
            print(f"  Health: {health_status}")
        except Exception as e:
            print(f"  Health check failed: {e}")
            health_status = {"error": str(e)}
        
        # Step 3: Create mock authentication header
        mock_token = "mock-token-" + str(int(time.time()))
        self.session.headers.update({
            "Authorization": f"Bearer {mock_token}",
            "X-Mock-User": json.dumps(mock_user),
            "X-Test-Mode": "true"
        })
        
        # Step 4: Test authenticated endpoints
        test_endpoints = [
            ("/api/user/me", "User Profile"),
            ("/api/threads", "Threads List"),
            ("/api/settings", "User Settings")
        ]
        
        results = {
            "method": "mock_login",
            "user": mock_user,
            "endpoints": {}
        }
        
        for endpoint, name in test_endpoints:
            print(f"Testing {name}...")
            try:
                url = f"{self.api_url}{endpoint}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"  [U+2713] {name}: Success")
                    results["endpoints"][endpoint] = {"status": "success", "code": 200}
                elif response.status_code == 401:
                    print(f"   WARNING:  {name}: Unauthorized (mock auth not enabled)")
                    results["endpoints"][endpoint] = {"status": "unauthorized", "code": 401}
                else:
                    print(f"  [U+2717] {name}: Failed ({response.status_code})")
                    results["endpoints"][endpoint] = {"status": "failed", "code": response.status_code}
                    
            except Exception as e:
                print(f"  [U+2717] {name}: Error - {e}")
                results["endpoints"][endpoint] = {"status": "error", "error": str(e)}
        
        return results
    
    def test_direct_api_access(self) -> Dict[str, Any]:
        """
        Test direct API access using service account or API key.
        """
        print("\n[Direct API Access Test]")
        print("-" * 40)
        
        # Try to load staging service account credentials
        service_account_file = Path("config/netra-staging-service-account.json")
        api_key_file = Path("staging_test_credentials.json")
        
        results = {
            "method": "direct_api",
            "authenticated": False,
            "endpoints": {}
        }
        
        # Check for API key file
        if api_key_file.exists():
            print("Found test credentials file...")
            with open(api_key_file) as f:
                creds = json.load(f)
                
            if "accounts" in creds and "api_key" in creds["accounts"]:
                api_key = creds["accounts"]["api_key"]["api_key"]
                self.session.headers["X-API-Key"] = api_key
                results["authenticated"] = True
                print(f"  Using API Key: {api_key[:20]}...")
        
        # Test public endpoints first
        public_endpoints = [
            ("/health", "Health Check"),
            ("/api/version", "API Version"),
            ("/api/status", "API Status")
        ]
        
        print("\nTesting public endpoints...")
        for endpoint, name in public_endpoints:
            try:
                url = f"{self.api_url}{endpoint}"
                response = self.session.get(url, timeout=10)
                
                if response.status_code == 200:
                    print(f"  [U+2713] {name}: Available")
                    results["endpoints"][endpoint] = {
                        "status": "available",
                        "data": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text[:100]
                    }
                else:
                    print(f"  [U+2717] {name}: Status {response.status_code}")
                    results["endpoints"][endpoint] = {"status": "unavailable", "code": response.status_code}
                    
            except Exception as e:
                print(f"  [U+2717] {name}: {e}")
                results["endpoints"][endpoint] = {"status": "error", "error": str(e)}
        
        return results
    
    def test_health_and_readiness(self) -> Dict[str, Any]:
        """
        Test health and readiness endpoints for all services.
        """
        print("\n[Service Health Check]")
        print("-" * 40)
        
        services = [
            ("Frontend", f"{self.base_url}/health"),
            ("Backend API", f"{self.api_url}/health"),
            ("Auth Service", f"{self.auth_url}/health"),
            ("WebSocket", f"{self.api_url}/ws/health")
        ]
        
        results = {
            "method": "health_check",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "services": {}
        }
        
        for service_name, url in services:
            print(f"Checking {service_name}...")
            try:
                response = requests.get(url, timeout=10)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        status = data.get("status", "unknown")
                        print(f"  [U+2713] {service_name}: {status}")
                    except:
                        print(f"  [U+2713] {service_name}: OK (non-JSON response)")
                        status = "ok"
                    
                    results["services"][service_name] = {
                        "url": url,
                        "status": status,
                        "code": 200
                    }
                else:
                    print(f"  [U+2717] {service_name}: HTTP {response.status_code}")
                    results["services"][service_name] = {
                        "url": url,
                        "status": "unhealthy",
                        "code": response.status_code
                    }
                    
            except requests.exceptions.Timeout:
                print(f"  [U+2717] {service_name}: Timeout")
                results["services"][service_name] = {
                    "url": url,
                    "status": "timeout",
                    "error": "Request timed out"
                }
            except Exception as e:
                print(f"  [U+2717] {service_name}: Error - {e}")
                results["services"][service_name] = {
                    "url": url,
                    "status": "error",
                    "error": str(e)
                }
        
        # Overall health assessment
        healthy_count = sum(1 for s in results["services"].values() if s.get("status") in ["healthy", "ok"])
        total_count = len(results["services"])
        results["overall_health"] = "healthy" if healthy_count == total_count else "degraded"
        
        return results
    
    def test_oauth_redirect(self) -> Dict[str, Any]:
        """
        Test OAuth redirect flow without completing authentication.
        """
        print("\n[OAuth Redirect Test]")
        print("-" * 40)
        
        results = {
            "method": "oauth_redirect",
            "providers": {}
        }
        
        providers = ["google", "github"]
        
        for provider in providers:
            print(f"Testing {provider.capitalize()} OAuth...")
            
            try:
                # Test OAuth initiation
                oauth_url = f"{self.auth_url}/auth/{provider}"
                response = requests.get(oauth_url, allow_redirects=False, timeout=10)
                
                if response.status_code in [302, 303]:
                    location = response.headers.get("Location", "")
                    
                    if provider == "google" and "accounts.google.com" in location:
                        print(f"  [U+2713] Google OAuth: Redirects correctly")
                        results["providers"]["google"] = {
                            "status": "configured",
                            "redirect_url": location[:100] + "..."
                        }
                    elif provider == "github" and "github.com" in location:
                        print(f"  [U+2713] GitHub OAuth: Redirects correctly")
                        results["providers"]["github"] = {
                            "status": "configured",
                            "redirect_url": location[:100] + "..."
                        }
                    else:
                        print(f"   WARNING:  {provider.capitalize()}: Unexpected redirect")
                        results["providers"][provider] = {
                            "status": "misconfigured",
                            "redirect_url": location[:100] + "..."
                        }
                else:
                    print(f"  [U+2717] {provider.capitalize()}: No redirect ({response.status_code})")
                    results["providers"][provider] = {
                        "status": "not_configured",
                        "code": response.status_code
                    }
                    
            except Exception as e:
                print(f"  [U+2717] {provider.capitalize()}: Error - {e}")
                results["providers"][provider] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """
        Run all test methods and generate comprehensive report.
        """
        print("=" * 60)
        print("STAGING LOGIN TEST SUITE")
        print("=" * 60)
        print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
        print(f"Environment: Staging")
        
        all_results = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "staging",
            "tests": {}
        }
        
        # Run each test method
        test_methods = [
            ("health", self.test_health_and_readiness),
            ("oauth_redirect", self.test_oauth_redirect),
            ("direct_api", self.test_direct_api_access),
            ("mock_login", self.test_mock_login)
        ]
        
        for test_name, test_method in test_methods:
            try:
                result = test_method()
                all_results["tests"][test_name] = result
                self.test_results.append(result)
            except Exception as e:
                print(f"\n[U+2717] Test '{test_name}' failed: {e}")
                all_results["tests"][test_name] = {"error": str(e)}
        
        # Generate summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        # Check service health
        health_test = all_results["tests"].get("health", {})
        if health_test.get("overall_health") == "healthy":
            print("[U+2713] All services are healthy")
        else:
            print(" WARNING:  Some services are degraded")
            for service, status in health_test.get("services", {}).items():
                if status.get("status") not in ["healthy", "ok"]:
                    print(f"  - {service}: {status.get('status', 'unknown')}")
        
        # Check OAuth configuration
        oauth_test = all_results["tests"].get("oauth_redirect", {})
        configured_providers = [
            p for p, s in oauth_test.get("providers", {}).items()
            if s.get("status") == "configured"
        ]
        
        if configured_providers:
            print(f"[U+2713] OAuth configured for: {', '.join(configured_providers)}")
        else:
            print("[U+2717] No OAuth providers configured")
        
        # Provide recommendations
        print("\n" + "-" * 60)
        print("RECOMMENDATIONS FOR AGENT TESTING")
        print("-" * 60)
        
        recommendations = []
        
        if health_test.get("overall_health") != "healthy":
            recommendations.append("Fix service health issues before testing login flows")
        
        if not configured_providers:
            recommendations.append("OAuth is not properly configured - use mock or API key authentication")
        else:
            recommendations.append("OAuth is configured but requires real Google/GitHub account for testing")
        
        recommendations.append("Use the setup_staging_test_account.py script to generate test credentials")
        recommendations.append("For automated testing, use mock authentication or API keys instead of OAuth")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"{i}. {rec}")
        
        # Save report
        report_file = Path("staging_login_test_report.json")
        with open(report_file, 'w') as f:
            json.dump(all_results, f, indent=2)
        
        print(f"\nFull report saved to: {report_file.absolute()}")
        
        return all_results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Test staging login functionality")
    parser.add_argument(
        "--method",
        choices=["mock", "api", "oauth", "all"],
        default="all",
        help="Test method to use"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file for test report (JSON)"
    )
    
    args = parser.parse_args()
    
    tester = StagingLoginTester(method=args.method)
    
    if args.method == "all":
        results = tester.run_comprehensive_test()
    elif args.method == "mock":
        results = tester.test_mock_login()
    elif args.method == "api":
        results = tester.test_direct_api_access()
    elif args.method == "oauth":
        results = tester.test_oauth_redirect()
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    # Exit code based on results
    if args.method == "all":
        health_ok = results.get("tests", {}).get("health", {}).get("overall_health") == "healthy"
        return 0 if health_ok else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())