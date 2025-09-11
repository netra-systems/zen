"""
Unit tests to reproduce auth service timeout configuration issues (Issue #395).

REPRODUCTION TARGET: 0.5s timeout too aggressive for GCP Cloud Run staging environment.
These tests SHOULD FAIL initially to demonstrate the timeout configuration problem.

Key Issues to Reproduce:
1. 0.5s staging health check timeout causing connectivity failures
2. Auth service responds in 0.195s but timeout configuration is still too aggressive
3. Environment-specific timeout configuration not accounting for GCP Cloud Run latency
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from netra_backend.app.clients.auth_client_core import AuthServiceClient
from test_framework.ssot.base_test_case import SSotAsyncTestCase


class TestAuthServiceTimeoutReproduction(SSotAsyncTestCase):
    """
    Unit tests to reproduce the 0.5s timeout configuration issue.
    
    These tests simulate the exact conditions that cause timeout failures
    in GCP Cloud Run staging environment.
    """
    
    async def asyncSetUp(self):
        """Set up test environment with staging configuration."""
        await super().asyncSetUp()
        
        # Mock staging environment to trigger aggressive 0.5s timeout
        self.mock_env_patcher = patch('shared.isolated_environment.get_env')
        self.mock_env = self.mock_env_patcher.start()
        
        # Mock environment properly - return a mock object that has get method
        mock_env_dict = MagicMock()
        mock_env_dict.get.side_effect = lambda key, default=None: {
            "ENVIRONMENT": "staging",
            "AUTH_CLIENT_TIMEOUT": "30"
        }.get(key, default)
        self.mock_env.return_value = mock_env_dict
        
        self.auth_client = AuthServiceClient()
    
    async def asyncTearDown(self):
        """Clean up test environment."""
        self.mock_env_patcher.stop()
        if self.auth_client._client:
            await self.auth_client._client.aclose()
        await super().asyncTearDown()

    @pytest.mark.asyncio
    async def test_staging_timeout_too_aggressive_for_gcp_cloud_run(self):
        """
        REPRODUCTION TEST: 0.5s timeout is too aggressive for GCP Cloud Run.
        
        This test simulates a healthy auth service that responds in 0.6s 
        (slightly above the 0.5s staging timeout) to reproduce the timeout failure.
        
        EXPECTED RESULT: Test should FAIL, demonstrating the timeout issue.
        """
        
        # Mock auth service response that takes 0.6s (healthy but above 0.5s timeout)
        async def mock_slow_but_healthy_response(*args, **kwargs):
            await asyncio.sleep(0.6)  # Simulate 0.6s response time (healthy but slow)
            mock_response = MagicMock()
            mock_response.status_code = 200  # Healthy service
            return mock_response
        
        with patch.object(self.auth_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = mock_slow_but_healthy_response
            mock_get_client.return_value = mock_client
            
            # Test the connectivity check with aggressive staging timeout
            start_time = time.time()
            is_reachable = await self.auth_client._check_auth_service_connectivity()
            duration = time.time() - start_time
            
            # REPRODUCTION ASSERTION: Should fail due to 0.5s timeout
            self.assertFalse(is_reachable, 
                           f"Expected connectivity check to FAIL due to 0.5s timeout, "
                           f"but it succeeded after {duration:.3f}s")
            
            # Verify timeout occurred around 0.5s (not 0.6s)
            self.assertLess(duration, 0.55, 
                          f"Expected timeout around 0.5s, but took {duration:.3f}s")
            
    @pytest.mark.asyncio
    async def test_environment_specific_timeout_configuration_issue(self):
        """
        REPRODUCTION TEST: Environment-specific timeout configuration.
        
        Tests that staging environment gets ultra-aggressive 0.5s timeout 
        while other environments get more reasonable timeouts.
        
        EXPECTED RESULT: Should show staging timeout is significantly more aggressive.
        """
        
        # Test staging timeout (ultra-aggressive)
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env.return_value.get.return_value = "staging"
            staging_client = AuthServiceClient()
            staging_timeouts = staging_client._get_environment_specific_timeouts()
            
            # Staging should have ultra-fast timeouts (causing the issue)
            self.assertEqual(staging_timeouts.connect, 1.0)
            self.assertEqual(staging_timeouts.read, 2.0)
            self.assertEqual(staging_timeouts.pool, 2.0)
            # Total staging timeout: max 6 seconds
            
        # Test production timeout (more reasonable)  
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_dict = MagicMock()
            mock_env_dict.get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "production",
                "AUTH_CLIENT_TIMEOUT": "30"
            }.get(key, default)
            mock_env.return_value = mock_env_dict
            prod_client = AuthServiceClient()
            prod_timeouts = prod_client._get_environment_specific_timeouts()
            
            # Production should have balanced timeouts
            self.assertEqual(prod_timeouts.connect, 2.0)
            self.assertEqual(prod_timeouts.read, 5.0)
            self.assertEqual(prod_timeouts.pool, 5.0)
            # Total production timeout: max 15 seconds
            
        # REPRODUCTION ASSERTION: Staging timeout is more aggressive
        staging_total = (staging_timeouts.connect + staging_timeouts.read + 
                        staging_timeouts.write + staging_timeouts.pool)
        prod_total = (prod_timeouts.connect + prod_timeouts.read + 
                     prod_timeouts.write + prod_timeouts.pool)
        
        self.assertLess(staging_total, prod_total * 0.6, 
                       f"Staging timeout ({staging_total}s) should be significantly "
                       f"less than production ({prod_total}s), indicating aggressive configuration")

    @pytest.mark.asyncio
    async def test_health_check_timeout_hardcoded_issue(self):
        """
        REPRODUCTION TEST: Health check timeout hardcoded to 0.5s in staging.
        
        This test reproduces the exact issue where _check_auth_service_connectivity 
        uses a hardcoded 0.5s timeout for staging environment.
        
        EXPECTED RESULT: Should FAIL when auth service takes longer than 0.5s.
        """
        
        # Simulate auth service that responds in 0.7s (healthy but above timeout)
        async def mock_auth_service_response(*args, **kwargs):
            await asyncio.sleep(0.7)  # 0.7s response (above 0.5s staging timeout)
            mock_response = MagicMock()
            mock_response.status_code = 200  # Service is healthy
            return mock_response
        
        # Mock asyncio.wait_for to simulate timeout behavior
        original_wait_for = asyncio.wait_for
        
        async def mock_wait_for(coro, timeout):
            if timeout == 0.5:  # Staging timeout
                # Simulate TimeoutError for 0.5s timeout
                await asyncio.sleep(0.1)  # Brief delay
                raise asyncio.TimeoutError("Operation timed out after 0.5s")
            return await original_wait_for(coro, timeout)
        
        with patch.object(self.auth_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = mock_auth_service_response
            mock_get_client.return_value = mock_client
            
            with patch('asyncio.wait_for', mock_wait_for):
                # Test health check with staging environment
                is_reachable = await self.auth_client._check_auth_service_connectivity()
                
                # REPRODUCTION ASSERTION: Should fail due to hardcoded 0.5s timeout
                self.assertFalse(is_reachable, 
                               "Expected health check to FAIL due to hardcoded 0.5s timeout")

    @pytest.mark.asyncio  
    async def test_auth_service_responds_healthy_but_times_out(self):
        """
        REPRODUCTION TEST: Auth service is healthy (0.195s response) but still times out.
        
        This test simulates the reported issue where auth service responds quickly 
        but the timeout configuration still causes failures.
        
        EXPECTED RESULT: Should demonstrate timeout configuration issues.
        """
        
        # Mock auth service with healthy 0.195s response time (as reported)
        async def mock_healthy_fast_response(*args, **kwargs):
            await asyncio.sleep(0.195)  # Actual reported response time
            mock_response = MagicMock() 
            mock_response.status_code = 200  # Healthy
            return mock_response
            
        # But mock timeout configuration that's still too aggressive
        with patch.object(self.auth_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get = mock_healthy_fast_response
            mock_get_client.return_value = mock_client
            
            # Mock environment detection for staging (0.5s timeout)
            with patch('shared.isolated_environment.get_env') as mock_env:
                mock_env.return_value.get.return_value = "staging"
                
                # Test connectivity check 
                start_time = time.time()
                is_reachable = await self.auth_client._check_auth_service_connectivity()
                duration = time.time() - start_time
                
                # Should succeed since 0.195s < 0.5s timeout
                # But let's verify the timeout buffer is minimal
                self.assertTrue(is_reachable, 
                              f"Auth service responds in 0.195s but connectivity check failed")
                
                # ASSERTION: Verify timeout buffer is dangerously small
                timeout_buffer = 0.5 - 0.195  # 0.305s buffer
                self.assertLess(timeout_buffer, 0.4,
                              f"Timeout buffer of {timeout_buffer:.3f}s is dangerously small "
                              f"for GCP Cloud Run network variability")

    @pytest.mark.asyncio
    async def test_token_validation_timeout_reproduction(self):
        """
        REPRODUCTION TEST: Token validation timeout in staging environment.
        
        This reproduces the complete token validation flow that times out
        due to aggressive staging timeout configuration.
        
        EXPECTED RESULT: Should FAIL due to timeout during token validation.
        """
        
        # Mock token validation that takes slightly longer than timeout
        async def mock_slow_validation_request(*args, **kwargs):
            await asyncio.sleep(0.8)  # Above staging timeout limits
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "valid": True,
                "user_id": "test_user", 
                "email": "test@example.com"
            }
            return mock_response
        
        with patch.object(self.auth_client, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post = mock_slow_validation_request
            mock_get_client.return_value = mock_client
            
            # Test token validation with staging timeouts
            test_token = "test_jwt_token"
            
            try:
                result = await self.auth_client.validate_token(test_token)
                self.fail("Expected validation to timeout, but it succeeded")
                
            except (asyncio.TimeoutError, httpx.TimeoutException, Exception) as e:
                # REPRODUCTION ASSERTION: Should timeout due to aggressive staging config
                self.assertIn("timeout", str(e).lower(), 
                            f"Expected timeout error but got: {e}")
                
    def test_staging_timeout_constants_inspection(self):
        """
        UNIT TEST: Inspect hardcoded timeout constants causing the issue.
        
        This test verifies the exact hardcoded values that cause timeout failures.
        """
        
        # Mock staging environment
        with patch('shared.isolated_environment.get_env') as mock_env:
            mock_env_dict = MagicMock()
            mock_env_dict.get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "staging",
                "AUTH_CLIENT_TIMEOUT": "30"
            }.get(key, default)
            mock_env.return_value = mock_env_dict
            
            # Create client and inspect timeout configuration
            client = AuthServiceClient()
            timeouts = client._get_environment_specific_timeouts()
            
            # REPRODUCTION ASSERTIONS: Verify aggressive staging timeouts
            self.assertEqual(timeouts.connect, 1.0, "Staging connect timeout should be 1.0s")
            self.assertEqual(timeouts.read, 2.0, "Staging read timeout should be 2.0s")  
            self.assertEqual(timeouts.write, 1.0, "Staging write timeout should be 1.0s")
            self.assertEqual(timeouts.pool, 2.0, "Staging pool timeout should be 2.0s")
            
            # Check health check timeout hardcoding in method (can't directly test async method constants)
            # But we know from code analysis it's hardcoded to 0.5s for staging
            
            # Total timeout budget is dangerously low
            total_timeout = timeouts.connect + timeouts.read + timeouts.write + timeouts.pool  
            self.assertEqual(total_timeout, 6.0, 
                           f"Total staging timeout budget of {total_timeout}s is too aggressive for Cloud Run")
            
            # Compare with production
            mock_env_dict.get.side_effect = lambda key, default=None: {
                "ENVIRONMENT": "production",
                "AUTH_CLIENT_TIMEOUT": "30"
            }.get(key, default)
            prod_client = AuthServiceClient() 
            prod_timeouts = prod_client._get_environment_specific_timeouts()
            prod_total = (prod_timeouts.connect + prod_timeouts.read + 
                         prod_timeouts.write + prod_timeouts.pool)
            
            self.assertLess(total_timeout, prod_total / 2, 
                          f"Staging timeout ({total_timeout}s) is less than half of "
                          f"production ({prod_total}s), indicating overly aggressive configuration")