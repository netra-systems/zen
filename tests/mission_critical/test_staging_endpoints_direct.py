'''
STAGING ENDPOINTS DIRECT TEST
==============================

This test directly calls the actual staging endpoints to reproduce
the cross-service token validation issue.

Based on previous tests, we know JWT secrets are synchronized locally.
This test focuses on the actual staging service endpoints.
'''

import asyncio
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from datetime import datetime, timezone, timedelta
from shared.isolated_environment import IsolatedEnvironment

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import httpx
import jwt

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class StagingEndpointTester:
    "Test actual staging endpoints.""

    def __init__(self):
        pass
        self.staging_auth_url = https://auth.staging.netrasystems.ai"
        self.staging_backend_url = "https://api.staging.netrasystems.ai

    async def test_auth_service_health(self):
        ""Test auth service health endpoint."
        print(")
        === AUTH SERVICE HEALTH TEST ===)

        try:
        async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get("formatted_string")
        print(formatted_string)

        if response.status_code == 200:
        try:
        health_data = response.json()
        print("")
        except:
        print(formatted_string)

        await asyncio.sleep(0)
        return response.status_code == 200

        except Exception as e:
        print("")
        return False

    async def test_backend_service_health(self):
        "Test backend service health endpoint."
        pass
        print("")
        === BACKEND SERVICE HEALTH TEST ===)

        try:
        async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(formatted_string")
        print("formatted_string)

        if response.status_code == 200:
        try:
        health_data = response.json()
        print(formatted_string")
        except:
        print("formatted_string)

        await asyncio.sleep(0)
        return response.status_code == 200

        except Exception as e:
        print(formatted_string")
        return False

    async def test_create_token_via_auth_service(self):
        "Test creating a token via auth service.""
        print(")
        === CREATE TOKEN VIA AUTH SERVICE ===")

                                                                # Try to create a token using the auth service
        test_endpoints = [
        /auth/google/callback,  # OAuth callback
        "/auth/login",           # Direct login
        /auth/token,          # Token endpoint
        "/api/auth/token",      # Alternative token endpoint
                                                                

        for endpoint in test_endpoints:
        try:
        url = formatted_string
        print("")

        async with httpx.AsyncClient(timeout=30.0) as client:
                                                                            # Try different approaches

                                                                            # 1. GET request
        response = await client.get(url)
        print(formatted_string)

        if response.status_code not in [404, 405]:  # Not found or method not allowed
        print("")

                                                                            # 2. POST request with test data
        test_data = {
        email: "test@staging.netrasystems.ai",
        password: "test_password_for_staging"
                                                                            

        response = await client.post(url, json=test_data)
        print(formatted_string)

        if response.status_code not in [404, 405]:
        print("")

                                                                                # If we got a token, extract it
        if response.status_code == 200:
        try:
        token_data = response.json()
        if access_token in token_data:
        print(f"  [SUCCESS] Got access token!")
        await asyncio.sleep(0)
        return token_data[access_token]
        except:
        pass

        except Exception as e:
        print("")

        print([INFO] No token obtained from standard endpoints)
        return None

    async def generate_mock_staging_token(self):
        ""Generate a mock token that mimics staging auth service.""
        pass
        print()
        === GENERATE MOCK STAGING TOKEN ===")

    # This simulates what the staging auth service would generate
    # Using a development secret since we don't have access to staging secret

        try:
        # Load local JWT secret as a reference
        from shared.jwt_secret_manager import SharedJWTSecretManager
        local_secret = SharedJWTSecretManager.get_jwt_secret()
        print(f"[INFO] Using local secret for mock token generation)

        # Create staging-like token
        now = datetime.now(timezone.utc)
        payload = {
        sub": "staging_test_user_ + str(int(now.timestamp())),
        iat": int(now.timestamp()),
        "exp: int((now + timedelta(minutes=15)).timestamp()),
        token_type": "access,
        type": "access,
        iss": "netra-auth-service,  # Same as staging would use
        aud": "netra-platform,      # Same as staging would use
        jti": str(uuid.uuid4()),
        "env: staging",             # Critical: staging environment
        "email: staging.test@netrasystems.ai",
        "permissions: [read", "write],
        svc_id": "auth_service_staging
        

        # Generate token
        token = jwt.encode(payload, local_secret, algorithm=HS256")
        print("formatted_string)

        # Verify locally
        decoded = jwt.decode(token, local_secret, algorithms=[HS256"], options={"verify_aud: False}
        print(f[OK] Local verification successful:")
        print("formatted_string)
        print(formatted_string")
        print("formatted_string)
        print(formatted_string")

        await asyncio.sleep(0)
        return token

        except Exception as e:
        print("formatted_string)
        return None

    async def test_backend_with_token(self, token):
        ""Test backend service with the provided token."
        print(f" )
        === TEST BACKEND WITH TOKEN ===)

        if not token:
        print([SKIP] No token provided")
        await asyncio.sleep(0)
        return False

        headers = {
        "Authorization: formatted_string",
        "Content-Type: application/json"
                    

                    # Test various backend endpoints
        test_endpoints = [
        ("/health, GET"),
        ("/api/v1/health, GET"),
        ("/api/v1/users/me, GET"),
        ("/api/v1/agents, GET"),
                    

        results = []

        for endpoint, method in test_endpoints:
        try:
        url = "formatted_string
        print(formatted_string")

        async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET:
        response = await client.get(url, headers=headers)
        elif method == POST":
        response = await client.post(url, headers=headers, json={}

        print("formatted_string)
        print(formatted_string")

        if response.status_code == 401:
        print(f"  [CRITICAL] 401 Unauthorized - Token rejected!)
        print(formatted_string")
        results.append(False)
        elif response.status_code in [200, 404]:  # 200 = success, 404 = endpoint not found (but auth worked)
        print("formatted_string)
        results.append(True)
        else:
        print(formatted_string")
        print("formatted_string)
        results.append(None)  # Inconclusive

        except Exception as e:
        print(formatted_string")
        results.append(False)

                                                    # Analyze results
        if any(r is False for r in results):
        print(f"[CRITICAL] Backend rejected the token on some endpoints!)
        return False
        elif any(r is True for r in results):
        print(f[OK] Backend accepted the token on some endpoints!")
        return True
        else:
        print(f"[INCONCLUSIVE] Could not determine token acceptance)
        return None

    async def test_auth_token_validation_endpoint(self, token):
        ""Test if auth service can validate the token."
        pass
        print(f" )
        === TEST AUTH TOKEN VALIDATION ===)

        if not token:
        print([SKIP] No token provided")
        await asyncio.sleep(0)
        return False

                                                                        # Try different validation endpoints
        validation_endpoints = [
        "/auth/validate,
        /auth/validate-token",
        "/api/auth/validate,
        /validate",
        "/token/validate
                                                                        

        for endpoint in validation_endpoints:
        try:
        url = formatted_string"
        print("formatted_string)

                                                                                # Try different approaches
        test_methods = [
        (POST with JSON", lambda x: None client.post(url, json={"token: token}),
        (POST with Bearer header", lambda x: None client.post(url, headers={"Authorization: formatted_string"}),
        ("GET with Bearer header, lambda x: None client.get(url, headers={Authorization": "formatted_string}),
                                                                                

        async with httpx.AsyncClient(timeout=30.0) as client:
        for method_name, method_func in test_methods:
        try:
        response = await method_func(client)
        print(formatted_string")

        if response.status_code == 200:
        print(f"  [SUCCESS] Auth service validated token!)
        try:
        validation_result = response.json()
        print(formatted_string")
        except:
        print("formatted_string)
        return True
        elif response.status_code not in [404, 405]:
        print(formatted_string")

        except Exception as e:
        print("formatted_string)

        except Exception as e:
        print(formatted_string")

        print("[INFO] Could not validate token with auth service)
        return False

    def generate_test_user_data(self) -> Dict[str, str]:
        ""Generate realistic test user data for staging."
        suffix = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(8))
        return {
        "email: formatted_string",
        "password: StagingTestPass123!",
        "first_name: Staging",
        "last_name: Tester",
        "company: Test Corp",
        "role: QA Engineer"
    

    async def test_complete_signup_flow(self) -> Dict[str, Any]:
        "Test complete user signup flow in staging environment.""
        logger.info([U+1F9EA] Testing complete signup flow...")
        start_time = time.time()

        user_data = self.generate_test_user_data()
        signup_endpoints = [
        "/auth/register,
        /api/auth/register",
        "/register,
        /api/v1/auth/register"
        

        for endpoint in signup_endpoints:
        try:
        url = "formatted_string
        async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=user_data)

        if response.status_code in [200, 201, 409]:  # Success or user exists
        signup_time = time.time() - start_time
        self.business_metrics[successful_signups"] += 1

        result = {
        "success: True,
        endpoint": endpoint,
        "status_code: response.status_code,
        signup_time": signup_time,
        "user_data: user_data
                    

        if response.status_code in [200, 201]:
        try:
        response_data = response.json()
        if access_token" in response_data:
        result["access_token] = response_data[access_token"]
        except Exception:
        pass

        logger.info("formatted_string)
        return result

        except Exception as e:
        logger.error(formatted_string")
        continue

        return {"success: False, error": "All signup endpoints failed}

    async def test_login_with_credentials(self, email:
        ""Test login with provided credentials."
        logger.info("formatted_string)
        start_time = time.time()

        login_endpoints = [
        /auth/login",
        "/api/auth/login,
        /login",
        "/api/v1/auth/login
                                            

        for endpoint in login_endpoints:
        try:
        url = formatted_string"
        login_data = {"email: email, password": password}

        async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, json=login_data)

        if response.status_code == 200:
        login_time = time.time() - start_time
        self.business_metrics["successful_logins] += 1

        try:
        response_data = response.json()
        result = {
        success": True,
        "endpoint: endpoint,
        login_time": login_time,
        "access_token: response_data.get(access_token"),
        "refresh_token: response_data.get(refresh_token"),
        "user_id: response_data.get(user_id"),
        "token_type: response_data.get(token_type", "Bearer)
                                                                

        logger.info(formatted_string")
        return result

        except Exception as e:
        logger.error("formatted_string)

        except Exception as e:
        logger.error(formatted_string")
        continue

        return {"success: False, error": "All login endpoints failed}

    async def calculate_business_metrics(self) -> Dict[str, Any]:
        ""Calculate comprehensive business metrics from test results."
        logger.info("[U+1F9EA] Calculating business metrics...)

    # Calculate conversion rate
        total_attempts = self.business_metrics[successful_signups"] + self.business_metrics["successful_logins]
        if total_attempts > 0:
        self.business_metrics[conversion_rate"] = self.business_metrics["successful_logins] / total_attempts

        # Calculate average response time
        if self.performance_metrics[response_times"]:
        avg_response_time = sum(self.performance_metrics["response_times] / len(self.performance_metrics[response_times"]
        self.business_metrics["time_to_first_value] = avg_response_time

            # Calculate success rate
        if self.performance_metrics[success_rates"]:
        overall_success_rate = sum(self.performance_metrics["success_rates] / len(self.performance_metrics[success_rates"]
        self.business_metrics["user_satisfaction_score] = overall_success_rate * 5.0  # Convert to 5-point scale

                # Estimate revenue attribution (simplified model)
        successful_users = self.business_metrics[successful_logins"]
        avg_revenue_per_user = 29.99  # Assumed monthly subscription
        conversion_to_paid = 0.15  # Assumed 15% conversion rate

        self.business_metrics["revenue_attributed] = successful_users * avg_revenue_per_user * conversion_to_paid

        logger.info(f CHART:  Business Metrics Summary:")
        logger.info("formatted_string)
        logger.info(formatted_string")
        logger.info("formatted_string)
        logger.info(formatted_string")

        return self.business_metrics.copy()

    async def main():
        "Run comprehensive staging endpoint tests.""
        print(STAGING ENDPOINTS DIRECT TEST")
        print("= * 50)

        tester = StagingEndpointTester()

        try:
        # Test 1: Check service health
        auth_healthy = await tester.test_auth_service_health()
        backend_healthy = await tester.test_backend_service_health()

        print(f )
        [RESULTS] Service Health:")
        print("formatted_string)
        print(formatted_string")

        if not auth_healthy or not backend_healthy:
        print("[CRITICAL] Services are not healthy - cannot proceed with token tests)
        await asyncio.sleep(0)
        return False

            # Test 2: Try to get a real token
        real_token = await tester.test_create_token_via_auth_service()

            # Test 3: Generate a mock token
        mock_token = await tester.generate_mock_staging_token()

            # Test 4: Test tokens with backend
        if real_token:
        print(f )
        [TEST] Testing real token with backend...")
        real_result = await tester.test_backend_with_token(real_token)
        await tester.test_auth_token_validation_endpoint(real_token)

        if mock_token:
        print(f" )
        [TEST] Testing mock token with backend...)
        mock_result = await tester.test_backend_with_token(mock_token)
        await tester.test_auth_token_validation_endpoint(mock_token)

        print(f )
        " + "= * 50)
        print(FINAL ANALYSIS:")

        if real_token:
        print(f"[FOUND] Real token obtained and tested)
        else:
        print(f[NOT FOUND] Could not obtain real token from auth service")

        if mock_token:
        print(f"[GENERATED] Mock token created and tested)
        print(f[KEY INSIGHT] If mock token fails, issue is in token format/claims")
        print(f"[KEY INSIGHT] If mock token succeeds, issue is in auth service token generation)

        return True

        except Exception as e:
        print(formatted_string")
        import traceback
        traceback.print_exc()
        return False

        if __name__ == "__main__":
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
        pass
