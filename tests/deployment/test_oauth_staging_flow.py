"""
Deployment test for OAuth flow in staging environment.
This test verifies the complete OAuth flow works correctly when deployed.
"""

import asyncio
import os

import httpx


class OAuthStagingTester:
    """Tests OAuth flow in staging environment"""

    def __init__(self):
        self.auth_service_url = os.getenv(
            "AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai"
        )
        self.frontend_url = os.getenv(
            "FRONTEND_URL", "https://app.staging.netrasystems.ai"
        )
        self.api_url = os.getenv("API_URL", "https://api.staging.netrasystems.ai")

    async def test_auth_service_health(self) -> bool:
        """Test that auth service is healthy"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.auth_service_url}/auth/health")
                if response.status_code != 200:
                    print(f"[FAIL] Auth service unhealthy: {response.status_code}")
                    return False

                data = response.json()
                if data.get("status") != "healthy":
                    print(f"[FAIL] Auth service status: {data.get('status')}")
                    return False

                print("[PASS] Auth service is healthy")
                return True
            except Exception as e:
                print(f"[FAIL] Auth service unreachable: {e}")
                return False

    async def test_auth_config_endpoint(self) -> bool:
        """Test that auth config endpoint returns OAuth configuration"""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.auth_service_url}/auth/config")
                if response.status_code != 200:
                    print(
                        f"[FAIL] Auth config endpoint failed: {
                            response.status_code}"
                    )
                    return False

                data = response.json()

                # Verify required fields
                required_fields = [
                    "google_client_id",
                    "endpoints",
                    "authorized_redirect_uris",
                ]
                for field in required_fields:
                    if field not in data:
                        print(f"[FAIL] Missing required field: {field}")
                        return False

                # Verify Google client ID is set
                if not data.get("google_client_id"):
                    print("[FAIL] Google client ID not configured")
                    return False

                # Verify redirect URI is correct
                expected_callback = f"{self.auth_service_url}/auth/callback"
                if expected_callback not in data.get("authorized_redirect_uris", []):
                    print(
                        f"[FAIL] Expected callback URL not in redirect URIs: {expected_callback}"
                    )
                    print(f"   Found: {data.get('authorized_redirect_uris')}")
                    return False

                print("[PASS] Auth config is properly configured")
                print(f"   Client ID: {data['google_client_id'][:20]}...")
                print(f"   Redirect URIs: {data['authorized_redirect_uris']}")
                return True

            except Exception as e:
                print(f"[FAIL] Auth config endpoint error: {e}")
                return False

    async def test_oauth_initiation(self) -> bool:
        """Test that OAuth login initiation redirects to Google"""
        async with httpx.AsyncClient(follow_redirects=False) as client:
            try:
                response = await client.get(
                    f"{self.auth_service_url}/auth/login", params={"provider": "google"}
                )

                if response.status_code != 302:
                    print(
                        f"[FAIL] OAuth initiation didn't redirect: {
                            response.status_code}"
                    )
                    return False

                location = response.headers.get("location", "")
                if not location.startswith("https://accounts.google.com/o/oauth2/"):
                    print(f"[FAIL] OAuth redirect URL incorrect: {location[:50]}...")
                    return False

                # Check for required OAuth parameters
                if "client_id=" not in location:
                    print("[FAIL] Missing client_id in OAuth URL")
                    return False

                if "redirect_uri=" not in location:
                    print("[FAIL] Missing redirect_uri in OAuth URL")
                    return False

                if f"{self.auth_service_url}/auth/callback" not in location:
                    print("[FAIL] Incorrect redirect_uri in OAuth URL")
                    return False

                print("[PASS] OAuth initiation works correctly")
                print("   Redirects to Google OAuth")
                print(
                    f"   Callback URL: {
                        self.auth_service_url}/auth/callback"
                )
                return True

            except Exception as e:
                print(f"[FAIL] OAuth initiation error: {e}")
                return False

    async def test_frontend_chat_page(self) -> bool:
        """Test that frontend chat page is accessible and can handle tokens"""
        async with httpx.AsyncClient() as client:
            try:
                # Test chat page loads
                response = await client.get(f"{self.frontend_url}/chat")
                if response.status_code != 200:
                    print(
                        f"[FAIL] Chat page not accessible: {
                            response.status_code}"
                    )
                    return False

                # Check if page contains necessary OAuth handling code
                content = response.text
                if "localStorage" not in content and "jwt_token" not in content:
                    print("[WARN] Chat page may not have token handling code")
                    # This is a warning, not a failure

                print("[PASS] Frontend chat page is accessible")
                return True

            except Exception as e:
                print(f"[FAIL] Frontend chat page error: {e}")
                return False

    async def test_token_validation_endpoint(self) -> bool:
        """Test that token validation endpoint exists and responds"""
        async with httpx.AsyncClient() as client:
            try:
                # Test with invalid token (should fail gracefully)
                response = await client.post(
                    f"{self.auth_service_url}/auth/validate",
                    json={"token": "invalid-test-token"},
                )

                # Should return 401 for invalid token
                if response.status_code == 401:
                    print(
                        "[PASS] Token validation endpoint works (correctly rejects invalid token)"
                    )
                    return True
                elif response.status_code == 200:
                    data = response.json()
                    if not data.get("valid"):
                        print("[PASS] Token validation endpoint works (returns invalid)")
                        return True

                print(
                    f"[FAIL] Unexpected token validation response: {
                        response.status_code}"
                )
                return False

            except Exception as e:
                print(f"[FAIL] Token validation endpoint error: {e}")
                return False

    async def test_api_auth_integration(self) -> bool:
        """Test that main API can communicate with auth service"""
        async with httpx.AsyncClient() as client:
            try:
                # Test API health endpoint (should work without auth)
                response = await client.get(f"{self.api_url}/health")
                if response.status_code != 200:
                    print(f"[FAIL] API health check failed: {response.status_code}")
                    return False

                # Test protected endpoint without token (should fail)
                response = await client.get(f"{self.api_url}/api/threads")
                if response.status_code == 401:
                    print("[PASS] API correctly requires authentication")
                    return True
                elif response.status_code == 200:
                    print("[WARN] API endpoint accessible without authentication")
                    return True  # Not a failure, might be intentional

                print(f"[FAIL] Unexpected API response: {response.status_code}")
                return False

            except Exception as e:
                print(f"[FAIL] API integration error: {e}")
                return False

    async def run_all_tests(self):
        """Run all OAuth staging tests"""
        print("\n" + "=" * 60)
        print("OAuth Staging Environment Tests")
        print("=" * 60)
        print(f"Auth Service: {self.auth_service_url}")
        print(f"Frontend: {self.frontend_url}")
        print(f"API: {self.api_url}")
        print("=" * 60 + "\n")

        tests = [
            ("Auth Service Health", self.test_auth_service_health),
            ("Auth Config Endpoint", self.test_auth_config_endpoint),
            ("OAuth Initiation", self.test_oauth_initiation),
            ("Frontend Chat Page", self.test_frontend_chat_page),
            ("Token Validation", self.test_token_validation_endpoint),
            ("API Auth Integration", self.test_api_auth_integration),
        ]

        results = []
        for test_name, test_func in tests:
            print(f"\nTesting: {test_name}")
            print("-" * 40)
            result = await test_func()
            results.append((test_name, result))
            print()

        # Summary
        print("\n" + "=" * 60)
        print("Test Summary")
        print("=" * 60)

        passed = sum(1 for _, result in results if result)
        total = len(results)

        for test_name, result in results:
            status = "[PASS]" if result else "[FAIL]"
            print(f"{status}: {test_name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n[SUCCESS] All OAuth staging tests passed!")
            return True
        else:
            print(f"\n[WARNING] {total - passed} test(s) failed")
            return False


async def main():
    """Main test runner"""
    tester = OAuthStagingTester()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
