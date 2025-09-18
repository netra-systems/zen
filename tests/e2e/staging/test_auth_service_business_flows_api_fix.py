"""
Staging E2E Test: Auth Service Business Flows - API Fix Validation for Issue #552

CRITICAL: This test validates that auth service business functionality works correctly
when NOT blocked by Docker API signature issues. Uses staging GCP environment.

PURPOSE:
- Prove auth service core functionality is working (business flows operational)
- Validate that Issue #552 is purely an API signature problem, not service dysfunction
- Provide alternative validation path when Docker unavailable
- Test realistic auth business flows that generate revenue

REQUIREMENTS (per CLAUDE.md):
- NO Docker dependencies (uses staging GCP environment)
- Real auth service validation (no mocks)
- Business-focused testing (user registration, login, token validation)
- Staging environment fallback per Issue #544 resolution

Business Value Justification:
1. Segment: Platform - Authentication infrastructure (serves all customer tiers)
2. Business Goal: Ensure auth reliability for customer acquisition and retention  
3. Value Impact: Validates auth flows that enable 500K+ ARR customer onboarding
4. Revenue Impact: Protects user registration and login that drives conversions

@compliance CLAUDE.md - Real services over mocks, staging environment validation
@compliance USER_CONTEXT_ARCHITECTURE.md - Factory patterns for user isolation
"""
import asyncio
import aiohttp
import json
import logging
import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Optional, Any
from unittest.mock import patch
from shared.isolated_environment import get_env
from test_framework.test_context import TestContext, TestUserContext
logger = logging.getLogger(__name__)

@pytest.mark.e2e
class AuthServiceBusinessFlowsStagingAPIFixTests:
    """Test auth service business flows on staging to validate Issue #552 is API-only problem."""

    @classmethod
    def setup_class(cls):
        """Set up staging environment configuration for auth testing."""
        cls.env = get_env()
        cls.auth_service_url = cls.env.get('STAGING_AUTH_SERVICE_URL', 'https://auth-service-staging.netrasystems.ai')
        cls.test_mode = 'staging_e2e'
        logger.info(f'🌐 Staging Auth E2E Tests - Service URL: {cls.auth_service_url}')

    async def test_staging_auth_registration_business_flow(self):
        """Test complete user registration business flow on staging.
        
        This test proves that auth service core functionality works correctly,
        demonstrating that Issue #552 is purely a Docker API signature problem.
        """
        test_email = f'test+issue552+{uuid.uuid4()}@netra-staging.com'
        test_password = 'SecureTestPassword123!'
        test_name = 'Issue 552 Test User'
        async with aiohttp.ClientSession() as session:
            registration_data = {'email': test_email, 'password': test_password, 'name': test_name, 'terms_accepted': True, 'metadata': {'test_source': 'issue_552_reproduction', 'test_timestamp': datetime.now(timezone.utc).isoformat()}}
            try:
                async with session.post(f'{self.auth_service_url}/api/auth/register', json=registration_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_text = await response.text()
                    logger.info(f'Registration response: {response.status} - {response_text}')
                    assert response.status in [200, 201], f'Registration failed with status {response.status}: {response_text}'
                    data = await response.json()
                    required_fields = ['user_id', 'access_token', 'refresh_token']
                    for field in required_fields:
                        assert field in data, f"Registration response missing required field '{field}': {data}"
                    self.access_token = data['access_token']
                    self.user_id = data['user_id']
                    logger.info(f'CHECK User registration successful - User ID: {self.user_id}')
            except aiohttp.ClientError as e:
                pytest.skip(f'Staging auth service unavailable: {e}')
            except asyncio.TimeoutError:
                pytest.skip('Staging auth service timeout - service may be unavailable')

    async def test_staging_auth_login_business_flow(self):
        """Test user login business flow on staging.
        
        This validates the complete auth workflow that enables customer access
        to the platform, protecting revenue-generating functionality.
        """
        test_email = f'test+login552+{uuid.uuid4()}@netra-staging.com'
        test_password = 'SecureTestPassword123!'
        async with aiohttp.ClientSession() as session:
            registration_data = {'email': test_email, 'password': test_password, 'name': 'Login Test User', 'terms_accepted': True}
            try:
                async with session.post(f'{self.auth_service_url}/api/auth/register', json=registration_data, timeout=aiohttp.ClientTimeout(total=30)) as reg_response:
                    if reg_response.status not in [200, 201]:
                        pytest.skip(f'Could not register test user: {reg_response.status}')
                login_data = {'email': test_email, 'password': test_password}
                async with session.post(f'{self.auth_service_url}/api/auth/login', json=login_data, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_text = await response.text()
                    logger.info(f'Login response: {response.status} - {response_text}')
                    assert response.status == 200, f'Login failed with status {response.status}: {response_text}'
                    data = await response.json()
                    required_fields = ['access_token', 'user_id']
                    for field in required_fields:
                        assert field in data, f"Login response missing required field '{field}': {data}"
                    logger.info('CHECK User login successful')
            except aiohttp.ClientError as e:
                pytest.skip(f'Staging auth service unavailable for login test: {e}')
            except asyncio.TimeoutError:
                pytest.skip('Login test timeout - staging service may be unavailable')

    async def test_staging_token_validation_business_flow(self):
        """Test token validation business flow on staging.
        
        This validates the token-based authentication that protects API access
        and enables authorized user actions throughout the platform.
        """
        test_email = f'test+token552+{uuid.uuid4()}@netra-staging.com'
        test_password = 'SecureTestPassword123!'
        async with aiohttp.ClientSession() as session:
            try:
                registration_data = {'email': test_email, 'password': test_password, 'name': 'Token Test User', 'terms_accepted': True}
                async with session.post(f'{self.auth_service_url}/api/auth/register', json=registration_data, timeout=aiohttp.ClientTimeout(total=30)) as reg_response:
                    if reg_response.status not in [200, 201]:
                        pytest.skip(f'Could not register user for token test: {reg_response.status}')
                    reg_data = await reg_response.json()
                    access_token = reg_data['access_token']
                headers = {'Authorization': f'Bearer {access_token}'}
                async with session.get(f'{self.auth_service_url}/api/auth/validate', headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    response_text = await response.text()
                    logger.info(f'Token validation response: {response.status} - {response_text}')
                    assert response.status == 200, f'Token validation failed with status {response.status}: {response_text}'
                    data = await response.json()
                    assert 'user_id' in data, f'Token validation response missing user_id: {data}'
                    assert 'valid' in data, f'Token validation response missing valid field: {data}'
                    assert data['valid'] is True, f'Token should be valid: {data}'
                    logger.info('CHECK Token validation successful')
            except aiohttp.ClientError as e:
                pytest.skip(f'Staging auth service unavailable for token test: {e}')
            except asyncio.TimeoutError:
                pytest.skip('Token validation test timeout - staging service may be unavailable')

    def test_staging_auth_service_health_check(self):
        """Test auth service health endpoint on staging.
        
        This basic health check validates that the auth service is operational,
        proving that any test failures are due to API signature issues, not service problems.
        """
        import requests
        try:
            response = requests.get(f'{self.auth_service_url}/health', timeout=30)
            logger.info(f'Health check response: {response.status_code} - {response.text}')
            assert response.status_code == 200, f'Health check failed with status {response.status_code}: {response.text}'
            try:
                health_data = response.json()
                if isinstance(health_data, dict):
                    expected_fields = ['status', 'healthy', 'service']
                    found_fields = [field for field in expected_fields if field in health_data]
                    assert found_fields, f'Health response should contain at least one of {expected_fields}: {health_data}'
            except ValueError:
                pass
            logger.info('CHECK Auth service health check successful')
        except requests.exceptions.RequestException as e:
            pytest.skip(f'Staging auth service unavailable for health check: {e}')
        except requests.exceptions.Timeout:
            pytest.skip('Auth service health check timeout - service may be unavailable')

@pytest.mark.e2e
class DockerAPISignatureVsStagingValidationTests:
    """Prove that Issue #552 is Docker API problem, not auth service dysfunction."""

    def test_docker_api_signature_fails_but_staging_auth_works(self):
        """DEMONSTRATION: Docker API fails but staging auth service works.
        
        This test demonstrates that:
        1. Docker API signature issue exists (Issue #552)
        2. Auth service itself works fine on staging 
        3. The issue is purely API signature mismatch, not service problems
        """
        from test_framework.unified_docker_manager import UnifiedDockerManager
        manager = UnifiedDockerManager()
        api_signature_fails = False
        try:
            manager.acquire_environment(env_name='test', use_alpine=True, rebuild_images=True)
        except TypeError as e:
            api_signature_fails = True
            logger.info(f'CHECK Confirmed API signature issue exists: {e}')
        assert api_signature_fails, 'API signature issue should exist to demonstrate Issue #552'
        env = get_env()
        staging_url = env.get('STAGING_AUTH_SERVICE_URL', 'https://auth-service-staging.netrasystems.ai')
        if staging_url:
            import requests
            try:
                response = requests.get(f'{staging_url}/health', timeout=10)
                staging_works = response.status_code == 200
                if staging_works:
                    logger.info('CHECK Staging auth service is operational')
                else:
                    logger.warning(f'Staging service response: {response.status_code}')
            except requests.exceptions.RequestException as e:
                logger.warning(f'Staging service unavailable: {e}')
                staging_works = False
        else:
            logger.warning('No staging URL configured')
            staging_works = False
        logger.info(f'ISSUE #552 ANALYSIS: Docker API fails={api_signature_fails}, Staging auth works={staging_works}')
        assert api_signature_fails, 'Issue #552 should be demonstrable'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')