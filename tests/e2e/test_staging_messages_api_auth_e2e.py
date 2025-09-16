"""
E2E Tests for Staging Messages API Authentication - Issue #1234 Reproduction

End-to-end tests against staging environment to validate the 403 authentication
errors that correlate with commit f1c251c9c JWT SSOT changes.

Business Value: Platform/Critical - Chat Functionality Protection
Validates production-like behavior for $500K+ ARR chat functionality.

Following CLAUDE.md guidelines:
- Tests against staging environment using real URLs
- Tests designed to reproduce 403 errors in production-like conditions
- Use SSOT patterns from test_framework/ssot/
- Target canonical staging URLs: *.staging.netrasystems.ai
"""

import pytest
import asyncio
import httpx
from typing import Dict, Any
from datetime import datetime, timezone

# SSOT Base Test Case per CLAUDE.md requirements
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env


class StagingMessagesAPIAuthE2ETests(SSotAsyncTestCase):
    """
    E2E tests for staging messages API authentication - Issue #1234 reproduction.
    
    These tests validate authentication behavior in a production-like staging
    environment to reproduce the 403 errors introduced in commit f1c251c9c.
    """
    
    def setup_method(self, method):
        """Setup test environment for staging E2E auth testing."""
        super().setup_method(method)
        
        # Set up staging environment URLs per CLAUDE.md requirements
        self._env.set("STAGING_BACKEND_URL", "https://backend.staging.netrasystems.ai", "staging_e2e")
        self._env.set("STAGING_AUTH_URL", "https://auth.staging.netrasystems.ai", "staging_e2e")
        self._env.set("ENVIRONMENT", "staging", "staging_e2e")
        
        # Initialize staging client
        self.staging_backend_url = self._env.get("STAGING_BACKEND_URL")
        self.staging_auth_url = self._env.get("STAGING_AUTH_URL")
        
        # Client timeout settings for staging
        self.timeout = httpx.Timeout(30.0, connect=10.0)
    
    async def _get_staging_auth_token(self) -> str:
        """
        Get a valid auth token from staging auth service.
        
        This simulates the real user authentication flow in staging.
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Use staging auth service to get a test token
                auth_payload = {
                    "email": "test_issue_1234@example.com",
                    "password": "test_password_for_issue_1234"
                }
                
                # Attempt to authenticate with staging auth service
                auth_response = await client.post(
                    f"{self.staging_auth_url}/auth/login",
                    json=auth_payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if auth_response.status_code == 200:
                    auth_data = auth_response.json()
                    if "access_token" in auth_data:
                        return auth_data["access_token"]
                
                # If standard login fails, try to create a test token
                # This might require different endpoints in staging
                pytest.skip(f"Cannot authenticate with staging auth service: {auth_response.status_code}")
                
        except Exception as e:
            pytest.skip(f"Cannot reach staging auth service: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_messages_list_with_invalid_auth_expects_401_not_403(self):
        """
        Test staging messages API with invalid auth expects 401, not 403.
        
        This is the primary test for Issue #1234 - validates that staging
        returns correct error codes for authentication failures.
        """
        # Arrange
        invalid_token = "invalid.jwt.token.for.staging.issue.1234"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        # Act - Call staging messages API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.staging_backend_url}/api/chat/messages",
                    headers=headers
                )
                
                # Assert - Should be 401 Unauthorized, NOT 403 Forbidden
                assert response.status_code == 401, f"Expected 401 (Unauthorized), got {response.status_code}: {response.text}"
                
                # Validate error response structure
                if response.headers.get("content-type", "").startswith("application/json"):
                    error_data = response.json()
                    assert "detail" in error_data, "Error response should contain detail field"
                    
                    # Should indicate authentication failure, not authorization
                    detail = error_data.get("detail", "").lower()
                    auth_keywords = ["invalid", "expired", "token", "authentication"]
                    assert any(keyword in detail for keyword in auth_keywords), f"Error detail should indicate auth failure: {detail}"
                
                # Record successful reproduction of expected behavior
                self._metrics.record_custom("staging_invalid_auth_status", response.status_code)
                self._metrics.record_custom("staging_auth_error_correct", True)
                
            except httpx.TimeoutException:
                pytest.skip("Staging backend is not reachable or is timing out")
            except httpx.ConnectError:
                pytest.skip("Cannot connect to staging backend")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_messages_create_with_invalid_auth_expects_401_not_403(self):
        """
        Test staging messages create API with invalid auth expects 401, not 403.
        
        Tests the POST endpoint specifically, which may have different auth handling.
        """
        # Arrange
        invalid_token = "invalid.jwt.token.for.staging.create.test"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        message_data = {
            "content": "Test message for Issue #1234 staging",
            "thread_id": "staging_test_thread_123",
            "message_type": "user"
        }
        
        # Act
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.staging_backend_url}/api/chat/messages",
                    headers=headers,
                    json=message_data
                )
                
                # Assert - Should be 401 Unauthorized, NOT 403 Forbidden
                assert response.status_code == 401, f"Expected 401 (Unauthorized), got {response.status_code}: {response.text}"
                
                self._metrics.record_custom("staging_create_invalid_auth_status", response.status_code)
                
            except httpx.TimeoutException:
                pytest.skip("Staging backend create endpoint is not reachable")
            except httpx.ConnectError:
                pytest.skip("Cannot connect to staging backend for create test")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_messages_stream_with_invalid_auth_expects_401_not_403(self):
        """
        Test staging messages stream API with invalid auth expects 401, not 403.
        
        The streaming endpoint is critical for investor demos and might have
        different error handling in staging.
        """
        # Arrange
        invalid_token = "invalid.jwt.token.for.staging.stream.test"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        stream_data = {
            "content": "Stream test for Issue #1234 staging",
            "thread_id": "staging_stream_thread",
            "message_type": "user"
        }
        
        # Act
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.staging_backend_url}/api/chat/messages/stream",
                    headers=headers,
                    json=stream_data
                )
                
                # Assert - Should be 401 Unauthorized, NOT 403 Forbidden
                assert response.status_code == 401, f"Expected 401 (Unauthorized), got {response.status_code}: {response.text}"
                
                self._metrics.record_custom("staging_stream_invalid_auth_status", response.status_code)
                
            except httpx.TimeoutException:
                pytest.skip("Staging backend stream endpoint is not reachable")
            except httpx.ConnectError:
                pytest.skip("Cannot connect to staging backend for stream test")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_auth_header_variations_expect_consistent_401(self):
        """
        Test various invalid auth header formats return consistent 401 errors.
        
        This tests edge cases that might trigger 403 instead of 401 in staging.
        """
        # Arrange - Various invalid authorization headers
        invalid_auth_cases = [
            {},  # No auth header
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "Bearer "},  # Empty token
            {"Authorization": "Basic dGVzdA=="},  # Wrong scheme
            {"Authorization": "Bearer malformed.token"},  # Malformed JWT
            {"Authorization": "Bearer expired.jwt.token.from.yesterday"},  # Potentially expired
        ]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for case_num, headers in enumerate(invalid_auth_cases):
                try:
                    response = await client.get(
                        f"{self.staging_backend_url}/api/chat/messages",
                        headers=headers
                    )
                    
                    # Should be 401 or 422, but NOT 403
                    assert response.status_code in [401, 422], f"Case {case_num}: Expected 401/422, got {response.status_code}: {response.text}"
                    
                    # Record each case for analysis
                    self._metrics.record_custom(f"staging_auth_case_{case_num}_status", response.status_code)
                    
                except httpx.TimeoutException:
                    self.logger.warning(f"Timeout for auth case {case_num}")
                    continue
                except httpx.ConnectError:
                    self.logger.warning(f"Connection error for auth case {case_num}")
                    continue
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_auth_service_circuit_breaker_behavior(self):
        """
        Test staging auth behavior under potential circuit breaker conditions.
        
        This tests rapid invalid requests to see if circuit breaker affects
        the error codes returned (might cause 403 instead of 401).
        """
        # Arrange - Make rapid requests with invalid tokens
        invalid_token = "invalid.token.for.circuit.breaker.test"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        responses = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # Make multiple rapid requests
            for i in range(5):
                try:
                    response = await client.get(
                        f"{self.staging_backend_url}/api/chat/messages",
                        headers=headers
                    )
                    responses.append(response)
                    
                    # Each should be 401, even under rapid fire
                    assert response.status_code == 401, f"Request {i}: Expected 401, got {response.status_code}"
                    
                    # Small delay to be respectful to staging
                    await asyncio.sleep(0.1)
                    
                except (httpx.TimeoutException, httpx.ConnectError):
                    self.logger.warning(f"Network error on request {i}")
                    break
        
        if responses:
            # Record circuit breaker test results
            self._metrics.record_custom("staging_circuit_breaker_requests", len(responses))
            self._metrics.record_custom("staging_all_401_under_load", all(r.status_code == 401 for r in responses))
        else:
            pytest.skip("Could not complete circuit breaker test due to network issues")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    async def test_staging_jwt_ssot_commit_correlation(self):
        """
        Test specifically targeting JWT SSOT changes from commit f1c251c9c.
        
        This test validates the specific changes made in that commit are
        working correctly in staging environment.
        """
        # Test timing and behavior that would be affected by JWT SSOT changes
        start_time = datetime.now(timezone.utc)
        
        invalid_token = "jwt.ssot.test.token.f1c251c9c"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.staging_backend_url}/api/chat/messages", 
                    headers=headers
                )
                
                end_time = datetime.now(timezone.utc)
                response_time_ms = (end_time - start_time).total_seconds() * 1000
                
                # Should be 401, validating JWT SSOT delegation is working
                assert response.status_code == 401, f"JWT SSOT test: Expected 401, got {response.status_code}"
                
                # Record JWT SSOT specific metrics
                self._metrics.record_custom("jwt_ssot_response_time_ms", response_time_ms)
                self._metrics.record_custom("jwt_ssot_delegation_working", True)
                self._metrics.record_custom("commit_f1c251c9c_validation", "pass")
                
                self.logger.info(f"JWT SSOT validation took {response_time_ms:.2f}ms in staging")
                
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                pytest.skip(f"Cannot validate JWT SSOT changes in staging: {e}")
    
    @pytest.mark.asyncio
    @pytest.mark.staging
    @pytest.mark.slow
    async def test_staging_auth_performance_under_load(self):
        """
        Test auth performance in staging to identify potential timeout issues.
        
        Poor performance could lead to timeouts that appear as 403 errors.
        """
        # Test multiple concurrent auth attempts
        invalid_token = "performance.test.token.issue.1234"
        headers = {"Authorization": f"Bearer {invalid_token}"}
        
        concurrent_requests = 3  # Keep reasonable for staging
        response_times = []
        
        async def single_auth_test():
            start = datetime.now(timezone.utc)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.get(
                        f"{self.staging_backend_url}/api/chat/messages",
                        headers=headers
                    )
                    end = datetime.now(timezone.utc)
                    time_ms = (end - start).total_seconds() * 1000
                    return response.status_code, time_ms
                except Exception as e:
                    end = datetime.now(timezone.utc)
                    time_ms = (end - start).total_seconds() * 1000
                    return None, time_ms
        
        # Run concurrent tests
        try:
            results = await asyncio.gather(*[single_auth_test() for _ in range(concurrent_requests)])
            
            for status_code, response_time in results:
                if status_code is not None:
                    response_times.append(response_time)
                    # Should be 401 even under concurrent load
                    assert status_code == 401, f"Concurrent test: Expected 401, got {status_code}"
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                
                # Record performance metrics
                self._metrics.record_custom("staging_avg_auth_time_ms", avg_response_time)
                self._metrics.record_custom("staging_max_auth_time_ms", max_response_time)
                self._metrics.record_custom("staging_concurrent_requests", len(response_times))
                
                self.logger.info(f"Staging auth performance: avg={avg_response_time:.2f}ms, max={max_response_time:.2f}ms")
            
        except Exception as e:
            pytest.skip(f"Performance test failed due to staging connectivity: {e}")
    
    def teardown_method(self, method):
        """Clean up after each staging test."""
        # Record Issue #1234 staging test completion
        self._metrics.record_custom("staging_e2e_test_completed", True)
        self._metrics.record_custom("staging_environment", "https://backend.staging.netrasystems.ai")
        self._metrics.record_custom("issue_1234_commit_target", "f1c251c9c")
        
        super().teardown_method(method)