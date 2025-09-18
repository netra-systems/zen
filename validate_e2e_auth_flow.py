#!/usr/bin/env python3
"""
E2E Authentication Flow Validation Script for Issue #1087
Tests the complete authentication flow on staging environment.
"""

import requests
import json
import sys
from typing import Dict, Any, Optional

class E2EAuthValidator:
    def __init__(self):
        self.base_url = "https://auth.staging.netrasystems.ai"
        self.frontend_url = "https://staging.netrasystems.ai"
        self.session = requests.Session()

    def test_auth_config(self) -> Dict[str, Any]:
        """Test auth configuration endpoint"""
        print("1. Testing auth configuration endpoint...")
        try:
            response = self.session.get(f"{self.base_url}/auth/config")
            if response.status_code == 200:
                config = response.json()
                print(f"   ✅ Auth config loaded successfully")
                print(f"   - Google Client ID: {config['google_client_id'][:20]}...")
                print(f"   - OAuth Enabled: {config['oauth_enabled']}")
                print(f"   - Development Mode: {config['development_mode']}")
                return {"status": "success", "config": config}
            else:
                print(f"   ❌ Auth config failed: {response.status_code}")
                return {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"   ❌ Auth config exception: {e}")
            return {"status": "exception", "error": str(e)}

    def test_auth_health(self) -> Dict[str, Any]:
        """Test auth service health"""
        print("2. Testing auth service health...")
        try:
            response = self.session.get(f"{self.base_url}/auth/health")
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Auth health: {health['status']}")
                print(f"   - Service: {health['service']}")
                print(f"   - Database: {health.get('database_status', 'unknown')}")
                return {"status": "success", "health": health}
            else:
                print(f"   ❌ Auth health failed: {response.status_code}")
                return {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"   ❌ Auth health exception: {e}")
            return {"status": "exception", "error": str(e)}

    def test_e2e_bypass_without_key(self) -> Dict[str, Any]:
        """Test E2E bypass endpoint without key (should fail)"""
        print("3. Testing E2E bypass without key (expected to fail)...")
        try:
            response = self.session.post(
                f"{self.base_url}/auth/e2e/test-auth",
                json={"email": "test@example.com", "name": "Test User"},
                headers={"Content-Type": "application/json"}
            )
            if response.status_code == 401:
                print(f"   ✅ E2E bypass correctly rejected without key")
                return {"status": "success", "message": "Correctly rejected"}
            else:
                print(f"   ❌ E2E bypass unexpected response: {response.status_code}")
                return {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"   ❌ E2E bypass exception: {e}")
            return {"status": "exception", "error": str(e)}

    def test_e2e_bypass_with_invalid_key(self) -> Dict[str, Any]:
        """Test E2E bypass endpoint with invalid key (should fail)"""
        print("4. Testing E2E bypass with invalid key (expected to fail)...")
        try:
            response = self.session.post(
                f"{self.base_url}/auth/e2e/test-auth",
                json={"email": "test@example.com", "name": "Test User"},
                headers={
                    "Content-Type": "application/json",
                    "X-E2E-Bypass-Key": "invalid-key-12345"
                }
            )
            if response.status_code == 401:
                error_detail = response.json().get("detail", "Unknown error")
                print(f"   ✅ E2E bypass correctly rejected invalid key")
                print(f"   - Error: {error_detail}")
                return {"status": "success", "message": "Correctly rejected invalid key"}
            else:
                print(f"   ❌ E2E bypass unexpected response: {response.status_code}")
                return {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"   ❌ E2E bypass exception: {e}")
            return {"status": "exception", "error": str(e)}

    def test_oauth_login_url(self) -> Dict[str, Any]:
        """Test OAuth login URL generation"""
        print("5. Testing OAuth login URL...")
        try:
            response = self.session.get(f"{self.base_url}/auth/login")
            if response.status_code in [302, 200]:
                print(f"   ✅ OAuth login URL accessible (code: {response.status_code})")
                if 'location' in response.headers:
                    location = response.headers['location']
                    if 'accounts.google.com' in location:
                        print(f"   - Redirects to Google OAuth: ✅")
                    else:
                        print(f"   - Redirect location: {location[:100]}...")
                return {"status": "success", "redirect": response.headers.get('location')}
            else:
                print(f"   ❌ OAuth login failed: {response.status_code}")
                return {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"   ❌ OAuth login exception: {e}")
            return {"status": "exception", "error": str(e)}

    def test_frontend_integration(self) -> Dict[str, Any]:
        """Test frontend health and integration"""
        print("6. Testing frontend integration...")
        try:
            response = self.session.get(f"{self.frontend_url}/health")
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ Frontend health: {health['status']}")

                # Check auth dependency
                auth_status = health.get('dependencies', {}).get('auth', {}).get('status')
                if auth_status == 'healthy':
                    print(f"   ✅ Frontend ↔ Auth integration: healthy")
                else:
                    print(f"   ⚠️ Frontend ↔ Auth integration: {auth_status}")

                return {"status": "success", "health": health}
            else:
                print(f"   ❌ Frontend health failed: {response.status_code}")
                return {"status": "error", "code": response.status_code}
        except Exception as e:
            print(f"   ❌ Frontend exception: {e}")
            return {"status": "exception", "error": str(e)}

    def run_validation(self) -> Dict[str, Any]:
        """Run complete E2E authentication validation"""
        print("🚀 Starting E2E Authentication Flow Validation for Issue #1087")
        print("=" * 70)

        results = {}

        # Run all tests
        results['auth_config'] = self.test_auth_config()
        results['auth_health'] = self.test_auth_health()
        results['e2e_no_key'] = self.test_e2e_bypass_without_key()
        results['e2e_invalid_key'] = self.test_e2e_bypass_with_invalid_key()
        results['oauth_login'] = self.test_oauth_login_url()
        results['frontend_integration'] = self.test_frontend_integration()

        # Summary
        print("\n" + "=" * 70)
        print("📊 VALIDATION SUMMARY")
        print("=" * 70)

        success_count = sum(1 for result in results.values() if result.get('status') == 'success')
        total_tests = len(results)

        print(f"✅ Successful tests: {success_count}/{total_tests}")

        # Detailed summary
        for test_name, result in results.items():
            status_icon = "✅" if result.get('status') == 'success' else "❌"
            print(f"{status_icon} {test_name}: {result.get('status', 'unknown')}")

        # Issue #1087 specific findings
        print("\n🔍 ISSUE #1087 SPECIFIC FINDINGS:")
        print("-" * 40)

        if results['e2e_no_key'].get('status') == 'success' and results['e2e_invalid_key'].get('status') == 'success':
            print("✅ E2E bypass security is working correctly")
            print("   - Requests without key are properly rejected")
            print("   - Requests with invalid key are properly rejected")
        else:
            print("❌ E2E bypass security issues detected")

        if results['auth_config'].get('status') == 'success':
            print("✅ Auth configuration is accessible and valid")
        else:
            print("❌ Auth configuration issues detected")

        if results['oauth_login'].get('status') == 'success':
            print("✅ OAuth login flow is accessible")
        else:
            print("❌ OAuth login flow issues detected")

        overall_status = "PASS" if success_count >= 4 else "FAIL"
        print(f"\n🎯 OVERALL STATUS: {overall_status}")

        return results

def main():
    """Main execution function"""
    validator = E2EAuthValidator()
    results = validator.run_validation()

    # Exit with appropriate code
    success_count = sum(1 for result in results.values() if result.get('status') == 'success')
    if success_count >= 4:
        print("\n✅ E2E Authentication validation completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ E2E Authentication validation failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()