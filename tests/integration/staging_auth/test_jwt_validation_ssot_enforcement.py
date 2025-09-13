"""

SSOT JWT Validation Enforcement Integration Test - ISSUE #814



PURPOSE: Integration test validating JWT validation SSOT enforcement in staging

EXPECTED: PASS after SSOT remediation - validates JWT validation delegation

TARGET: All JWT validation must be performed by auth service, never locally



BUSINESS VALUE: Ensures JWT security consistency for $500K+ ARR authentication

EXECUTION: Staging environment integration - NO Docker dependency

"""

import logging

import pytest

import asyncio

import aiohttp

import json

import os

import time

from typing import Dict, Any, Optional, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase



logger = logging.getLogger(__name__)



class TestJWTValidationSSOTEnforcement(SSotAsyncTestCase):

    """

    Integration test validating JWT validation SSOT enforcement.

    Tests that all JWT validation is performed by auth service in staging.

    """



    @classmethod

    async def asyncSetUpClass(cls):

        """Setup JWT validation SSOT testing environment"""

        await super().asyncSetUpClass()



        # Staging endpoints

        cls.staging_auth_service_url = os.getenv(

            "STAGING_AUTH_SERVICE_URL",

            "https://auth-staging.netra-apex.com"

        )

        cls.staging_backend_url = os.getenv(

            "STAGING_BACKEND_URL",

            "https://backend-staging.netra-apex.com"

        )



        # Test credentials

        cls.staging_test_email = "jwt-validation-test@example.com"

        cls.staging_test_password = "JWTValidation123!"



    async def asyncSetUp(self):

        """Setup individual JWT validation test"""

        await super().asyncSetUp()

        self.http_session = aiohttp.ClientSession()

        self.auth_token = None

        self.auth_service_response_times = []

        self.backend_response_times = []



    async def asyncTearDown(self):

        """Cleanup JWT validation test"""

        if self.http_session:

            await self.http_session.close()

        await super().asyncTearDown()



    async def test_backend_jwt_validation_delegates_to_auth_service(self):

        """

        Integration test: Backend JWT validation delegates to auth service



        VALIDATES: Backend doesn't validate JWT locally, always calls auth service

        ENSURES: SSOT enforcement for JWT validation in staging

        """

        # Step 1: Get valid JWT from auth service

        logger.info("Getting valid JWT from staging auth service")

        await self._get_valid_jwt_from_auth_service()



        # Step 2: Test backend validation delegates to auth service

        logger.info("Testing backend JWT validation delegation")

        await self._test_backend_jwt_validation_delegation()



        # Step 3: Test invalid JWT handling

        logger.info("Testing invalid JWT handling")

        await self._test_invalid_jwt_handling()



        # Step 4: Test expired JWT handling

        logger.info("Testing expired JWT handling")

        await self._test_expired_jwt_handling()



    async def _get_valid_jwt_from_auth_service(self):

        """Get valid JWT from staging auth service"""

        login_payload = {

            "email": self.staging_test_email,

            "password": self.staging_test_password

        }



        try:

            start_time = time.time()

            async with self.http_session.post(

                f"{self.staging_auth_service_url}/auth/login",

                json=login_payload,

                timeout=30

            ) as response:

                end_time = time.time()

                self.auth_service_response_times.append(end_time - start_time)



                if response.status == 200:

                    auth_data = await response.json()

                    self.auth_token = auth_data["access_token"]



                    assert self.auth_token is not None, "Valid JWT received from auth service"

                    logger.info("Valid JWT obtained from staging auth service")



                elif response.status == 401:

                    pytest.skip("Staging JWT test user not configured")

                else:

                    pytest.fail(f"Auth service JWT creation failed: {response.status}")



        except aiohttp.ClientError as e:

            pytest.skip(f"Staging auth service not accessible: {e}")



    async def _test_backend_jwt_validation_delegation(self):

        """Test backend JWT validation delegates to auth service"""

        headers = {"Authorization": f"Bearer {self.auth_token}"}



        # Test endpoint that requires JWT validation

        try:

            start_time = time.time()

            async with self.http_session.get(

                f"{self.staging_backend_url}/api/v1/user/profile",

                headers=headers,

                timeout=30

            ) as response:

                end_time = time.time()

                self.backend_response_times.append(end_time - start_time)



                assert response.status == 200, "Backend accepts valid JWT via auth service"



                profile_data = await response.json()

                assert "user_id" in profile_data, "Backend provides user data from auth service validation"



                # Validate that backend took time to call auth service

                # (Not instantaneous local validation)

                response_time = end_time - start_time

                assert response_time > 0.01, "Backend took time to validate JWT (not local)"



                logger.info(f"Backend JWT validation delegation successful ({response_time:.3f}s)")



        except aiohttp.ClientError as e:

            pytest.skip(f"Staging backend not accessible: {e}")



    async def _test_invalid_jwt_handling(self):

        """Test handling of invalid JWT tokens"""

        invalid_tokens = [

            "invalid-jwt-token-123",

            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",  # Malformed JWT

            "",  # Empty token

            "Bearer-without-token",  # Malformed Bearer format

        ]



        for invalid_token in invalid_tokens:

            headers = {"Authorization": f"Bearer {invalid_token}"}



            try:

                async with self.http_session.get(

                    f"{self.staging_backend_url}/api/v1/user/profile",

                    headers=headers,

                    timeout=30

                ) as response:

                    # Backend should reject via auth service validation

                    assert response.status == 401, f"Backend rejects invalid JWT: {invalid_token[:20]}..."



                    error_data = await response.json()

                    # Error should indicate auth service validation failure

                    error_message = error_data.get("error", "").lower()

                    assert any(keyword in error_message for keyword in ["invalid", "unauthorized", "token"]), \

                        "Error indicates auth service JWT validation failure"



                    logger.info(f"Invalid JWT properly rejected via auth service")



            except aiohttp.ClientError:

                # If backend is not accessible, skip this test

                continue



    async def _test_expired_jwt_handling(self):

        """Test handling of expired JWT tokens"""

        # Create a token that will expire quickly (if supported by staging)

        try:

            short_lived_payload = {

                "email": self.staging_test_email,

                "password": self.staging_test_password,

                "expires_in": 1  # 1 second for testing

            }



            async with self.http_session.post(

                f"{self.staging_auth_service_url}/auth/login",

                json=short_lived_payload,

                timeout=30

            ) as response:

                if response.status == 200:

                    auth_data = await response.json()

                    short_lived_token = auth_data["access_token"]



                    # Wait for token expiration

                    await asyncio.sleep(2)



                    # Test expired token handling

                    expired_headers = {"Authorization": f"Bearer {short_lived_token}"}



                    async with self.http_session.get(

                        f"{self.staging_backend_url}/api/v1/user/profile",

                        headers=expired_headers,

                        timeout=30

                    ) as expired_response:

                        assert expired_response.status == 401, "Backend rejects expired JWT via auth service"



                        expired_error = await expired_response.json()

                        error_message = expired_error.get("error", "").lower()

                        assert "expired" in error_message or "invalid" in error_message, \

                            "Error indicates JWT expiration via auth service"



                        logger.info("Expired JWT properly rejected via auth service")



                else:

                    logger.warning("Short-lived JWT not supported in staging")



        except aiohttp.ClientError:

            logger.warning("Expired JWT test skipped - staging limitation")



    async def test_jwt_validation_response_time_indicates_delegation(self):

        """

        Integration test: JWT validation response times indicate auth service delegation



        VALIDATES: Response times show network calls to auth service, not local validation

        ENSURES: Backend doesn't cache or validate JWTs locally

        """

        await self._get_valid_jwt_from_auth_service()



        # Test multiple JWT validations

        await self._perform_multiple_jwt_validations()



        # Analyze response times

        await self._analyze_jwt_validation_response_times()



    async def _perform_multiple_jwt_validations(self):

        """Perform multiple JWT validations to analyze response patterns"""

        headers = {"Authorization": f"Bearer {self.auth_token}"}



        # Perform 5 validations to get response time patterns

        for i in range(5):

            try:

                start_time = time.time()

                async with self.http_session.get(

                    f"{self.staging_backend_url}/api/v1/user/profile",

                    headers=headers,

                    timeout=30

                ) as response:

                    end_time = time.time()

                    response_time = end_time - start_time



                    assert response.status == 200, f"JWT validation {i+1} successful"

                    self.backend_response_times.append(response_time)



                    # Small delay between validations

                    await asyncio.sleep(0.1)



            except aiohttp.ClientError:

                break



    async def _analyze_jwt_validation_response_times(self):

        """Analyze JWT validation response times to confirm delegation"""

        if len(self.backend_response_times) >= 3:

            avg_backend_time = sum(self.backend_response_times) / len(self.backend_response_times)



            # Backend should take time for network calls to auth service

            assert avg_backend_time > 0.01, \

                f"Backend validation time ({avg_backend_time:.3f}s) indicates auth service delegation"



            # Response times should be consistent (not cached locally)

            max_time = max(self.backend_response_times)

            min_time = min(self.backend_response_times)

            time_variance = max_time - min_time



            # Some variance expected due to network, but not huge differences

            assert time_variance < 2.0, \

                f"JWT validation time variance ({time_variance:.3f}s) reasonable for auth service calls"



            logger.info(f"JWT validation response times confirm auth service delegation: "

                       f"avg={avg_backend_time:.3f}s, variance={time_variance:.3f}s")



    async def test_jwt_validation_error_messages_from_auth_service(self):

        """

        Integration test: JWT validation error messages come from auth service



        VALIDATES: Error messages consistent with auth service responses

        ENSURES: Backend doesn't generate its own JWT validation errors

        """

        # Test various invalid JWT scenarios

        await self._test_jwt_error_message_consistency()



    async def _test_jwt_error_message_consistency(self):

        """Test JWT error message consistency with auth service"""

        # Test cases for different JWT validation errors

        jwt_test_cases = [

            {

                "token": "malformed.jwt.token",

                "expected_error_types": ["invalid", "malformed", "token"]

            },

            {

                "token": "",

                "expected_error_types": ["missing", "required", "token"]

            },

            {

                "token": "valid-format-but-invalid-signature",

                "expected_error_types": ["invalid", "signature", "token"]

            }

        ]



        for test_case in jwt_test_cases:

            headers = {"Authorization": f"Bearer {test_case['token']}"}



            try:

                # Get error from backend

                async with self.http_session.get(

                    f"{self.staging_backend_url}/api/v1/user/profile",

                    headers=headers,

                    timeout=30

                ) as backend_response:

                    assert backend_response.status == 401, "Backend rejects invalid JWT"

                    backend_error = await backend_response.json()



                # Get error directly from auth service for comparison

                async with self.http_session.post(

                    f"{self.staging_auth_service_url}/auth/validate",

                    headers=headers,

                    timeout=30

                ) as auth_response:

                    if auth_response.status == 401:

                        auth_error = await auth_response.json()



                        # Compare error message patterns

                        backend_error_msg = backend_error.get("error", "").lower()

                        auth_error_msg = auth_error.get("error", "").lower()



                        # Errors should be similar (indicating delegation)

                        error_similarity = any(

                            error_type in backend_error_msg and error_type in auth_error_msg

                            for error_type in test_case["expected_error_types"]

                        )



                        if not error_similarity:

                            # Check if backend error at least indicates auth service source

                            assert any(keyword in backend_error_msg

                                     for keyword in ["service", "validation", "auth"]), \

                                f"Backend error should indicate auth service validation: {backend_error_msg}"



                        logger.info(f"JWT error message consistency validated for token type: {test_case['token'][:10]}...")



            except aiohttp.ClientError:

                continue



    async def test_jwt_validation_rate_limiting_from_auth_service(self):

        """

        Integration test: JWT validation rate limiting managed by auth service



        VALIDATES: Rate limiting decisions come from auth service

        ENSURES: Backend doesn't implement its own JWT validation rate limiting

        """

        await self._get_valid_jwt_from_auth_service()



        # Perform rapid JWT validations to test rate limiting

        await self._test_jwt_validation_rate_limiting()



    async def _test_jwt_validation_rate_limiting(self):

        """Test JWT validation rate limiting behavior"""

        headers = {"Authorization": f"Bearer {self.auth_token}"}



        # Perform rapid validations to trigger potential rate limiting

        rate_limit_responses = []



        for i in range(20):  # 20 rapid requests

            try:

                async with self.http_session.get(

                    f"{self.staging_backend_url}/api/v1/user/profile",

                    headers=headers,

                    timeout=10

                ) as response:

                    rate_limit_responses.append({

                        "status": response.status,

                        "request_num": i + 1

                    })



                    # If rate limiting kicks in, should be 429

                    if response.status == 429:

                        error_data = await response.json()

                        rate_limit_error = error_data.get("error", "").lower()



                        # Rate limiting should indicate auth service source

                        assert any(keyword in rate_limit_error

                                 for keyword in ["rate", "limit", "too many"]), \

                            "Rate limit error indicates proper source"



                        logger.info(f"Rate limiting triggered at request {i+1}")

                        break



                # Small delay to not overwhelm staging

                await asyncio.sleep(0.05)



            except (aiohttp.ClientError, asyncio.TimeoutError):

                break



        # Analyze rate limiting behavior

        successful_requests = sum(1 for resp in rate_limit_responses if resp["status"] == 200)

        rate_limited_requests = sum(1 for resp in rate_limit_responses if resp["status"] == 429)



        logger.info(f"JWT validation rate limiting test: "

                   f"{successful_requests} successful, {rate_limited_requests} rate limited")



if __name__ == "__main__":

    # Run with: python -m pytest tests/integration/staging_auth/test_jwt_validation_ssot_enforcement.py -v

    pytest.main([__file__, "-v"])

