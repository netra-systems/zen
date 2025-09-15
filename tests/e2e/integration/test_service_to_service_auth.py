"""
Service-to-Service Authentication Test - P0 Security
BVJ: Enterprise | Security | Inter-service auth tokens | Enables SOC2 compliance
SPEC: auth_microservice_migration_plan.xml lines 322-341
ISSUE: No validation of internal service authentication tokens
IMPACT: Services can't authenticate with each other securely
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Optional
from shared.isolated_environment import IsolatedEnvironment
import pytest
from auth_service.auth_core.models.auth_models import ServiceTokenRequest
from auth_service.auth_core.services.auth_service import AuthService
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from tests.e2e.jwt_token_helpers import JWTTokenTestHelper
from tests.e2e.test_data_factory import create_test_service_credentials
logger = logging.getLogger(__name__)

class TestServiceAuthValidator:
    """Validates service-to-service authentication patterns"""

    def __init__(self):
        self.auth_service = AuthService()
        self.auth_client = AuthServiceClient()
        self.test_timeout = 10

    async def validate_service_token_generation(self, service_id: str, service_secret: str) -> Dict:
        """Test service token generation with service credentials"""
        request = ServiceTokenRequest(service_id=service_id, service_secret=service_secret)
        try:
            response = await self.auth_service.create_service_token(request)
            assert response.token is not None, 'Service token not returned'
            assert response.expires_in == 300, 'Service token should expire in 5 minutes'
            assert response.service_name is not None, 'Service name not returned'
            return {'token': response.token, 'expires_in': response.expires_in, 'service_name': response.service_name}
        except Exception as e:
            pytest.fail(f'Service token generation failed: {e}')

    async def validate_service_token_structure(self, token: str) -> Dict:
        """Validate service token has correct structure and claims"""
        helper = JWTTokenTestHelper()
        payload = helper.decode_token_unsafe(token)
        assert payload is not None, 'Service token could not be decoded'
        assert payload.get('token_type') == 'service', "Token type should be 'service'"
        assert 'sub' in payload, 'Service ID missing from token'
        assert 'service' in payload, 'Service name missing from token'
        assert 'exp' in payload, 'Expiration missing from token'
        exp_time = datetime.fromtimestamp(payload['exp'])
        now = datetime.now()
        time_diff = (exp_time - now).total_seconds()
        assert 280 <= time_diff <= 320, f'Service token expiry incorrect: {time_diff}s'
        return payload

    async def validate_service_token_authentication(self, token: str) -> Dict:
        """Test backend authenticating with auth service using service token"""
        try:
            validation_result = await self.auth_client.validate_token_jwt(token)
            assert validation_result is not None, 'Token validation returned None'
            assert validation_result.get('valid') is True, 'Service token should be valid'
            return validation_result
        except Exception as e:
            pytest.fail(f'Service token validation failed: {e}')

    async def validate_service_vs_user_token_differences(self, service_token: str, user_token: str) -> None:
        """Test that service token validation differs from user token validation"""
        helper = JWTTokenTestHelper()
        service_payload = helper.decode_token_unsafe(service_token)
        user_payload = helper.decode_token_unsafe(user_token)
        assert service_payload.get('token_type') == 'service'
        assert user_payload.get('token_type') == 'access'
        assert 'service' in service_payload, "Service token should have 'service' field"
        assert 'service' not in user_payload, "User token should not have 'service' field"
        assert 'email' in user_payload, "User token should have 'email' field"
        assert 'email' not in service_payload, "Service token should not have 'email' field"
        service_exp = datetime.fromtimestamp(service_payload['exp'])
        user_exp = datetime.fromtimestamp(user_payload['exp'])
        assert service_exp < user_exp, 'Service tokens should expire before user tokens'

    async def validate_service_token_refresh(self, service_id: str, service_secret: str) -> None:
        """Test service token refresh mechanism"""
        token_data = await self.validate_service_token_generation(service_id, service_secret)
        original_token = token_data['token']
        await asyncio.sleep(1)
        new_token_data = await self.validate_service_token_generation(service_id, service_secret)
        new_token = new_token_data['token']
        assert original_token != new_token, 'Service tokens should be different each time'
        original_valid = await self.validate_service_token_authentication(original_token)
        new_valid = await self.validate_service_token_authentication(new_token)
        assert original_valid.get('valid') is True
        assert new_valid.get('valid') is True

    async def validate_invalid_service_credentials(self) -> None:
        """Test service token generation with invalid credentials"""
        request = ServiceTokenRequest(service_id='invalid-service', service_secret='invalid-secret')
        try:
            response = await self.auth_service.create_service_token(request)
            pytest.fail('Should have raised an exception for invalid service credentials')
        except Exception as e:
            error_msg = str(e).lower()
            assert any((keyword in error_msg for keyword in ['invalid', 'auth', 'credential', 'service'])), f'Expected auth-related error, got: {e}'

    async def validate_expired_service_token(self) -> None:
        """Test handling of expired service tokens (simulation)"""
        helper = JWTTokenTestHelper()
        expired_token = helper.create_expired_service_token('test-service')
        token_response = await self.auth_service.validate_token_jwt(expired_token)
        assert token_response.valid is False, 'Expired service token should be invalid'

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_token_generation_valid_credentials():
    """Test service token generation with valid service credentials"""
    validator = TestServiceAuthValidator()
    service_creds = create_test_service_credentials('backend')
    token_data = await validator.validate_service_token_generation(service_creds['service_id'], service_creds['service_secret'])
    assert 'token' in token_data
    assert 'service_name' in token_data
    assert token_data['service_name'] == 'netra-backend'

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_token_structure_validation():
    """Test service token has correct JWT structure and claims"""
    validator = TestServiceAuthValidator()
    service_creds = create_test_service_credentials('backend')
    token_data = await validator.validate_service_token_generation(service_creds['service_id'], service_creds['service_secret'])
    payload = await validator.validate_service_token_structure(token_data['token'])
    assert payload['sub'] == service_creds['service_id']
    assert payload['service'] == 'netra-backend'
    assert payload['token_type'] == 'service'

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_backend_auth_with_service_token():
    """Test backend authenticating with auth service using service tokens"""
    validator = TestServiceAuthValidator()
    service_creds = create_test_service_credentials('backend')
    token_data = await validator.validate_service_token_generation(service_creds['service_id'], service_creds['service_secret'])
    validation_result = await validator.validate_service_token_authentication(token_data['token'])
    assert validation_result.get('valid') is True
    user_id = validation_result.get('user_id')
    service_id = validation_result.get('service_id')
    assert user_id is not None or service_id is not None, 'No service identification returned'

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_vs_user_token_validation_differences():
    """Test service token validation differs from user token validation"""
    validator = TestServiceAuthValidator()
    helper = JWTTokenTestHelper()
    service_creds = create_test_service_credentials('backend')
    service_token_data = await validator.validate_service_token_generation(service_creds['service_id'], service_creds['service_secret'])
    user_token = helper.create_test_user_token('test-user-1', 'test@example.com')
    await validator.validate_service_vs_user_token_differences(service_token_data['token'], user_token)

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_token_refresh_mechanism():
    """Test token refresh for service accounts"""
    validator = TestServiceAuthValidator()
    service_creds = create_test_service_credentials('backend')
    await validator.validate_service_token_refresh(service_creds['service_id'], service_creds['service_secret'])

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_invalid_service_credentials_rejection():
    """Test rejection of invalid service credentials"""
    validator = TestServiceAuthValidator()
    await validator.validate_invalid_service_credentials()

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_expired_service_token_handling():
    """Test handling of expired service tokens"""
    validator = TestServiceAuthValidator()
    await validator.validate_expired_service_token()

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_service_token_performance():
    """Test service token operations complete within performance requirements"""
    validator = TestServiceAuthValidator()
    service_creds = create_test_service_credentials('backend')
    start_time = datetime.now()
    token_data = await validator.validate_service_token_generation(service_creds['service_id'], service_creds['service_secret'])
    generation_time = (datetime.now() - start_time).total_seconds()
    assert generation_time < 1.0, f'Service token generation too slow: {generation_time}s'
    start_time = datetime.now()
    await validator.validate_service_token_authentication(token_data['token'])
    validation_time = (datetime.now() - start_time).total_seconds()
    assert validation_time < 0.5, f'Service token validation too slow: {validation_time}s'

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_multiple_service_tokens_isolation():
    """Test multiple services can have independent tokens"""
    validator = TestServiceAuthValidator()
    backend_creds = create_test_service_credentials('backend')
    worker_creds = create_test_service_credentials('worker')
    backend_token_data = await validator.validate_service_token_generation(backend_creds['service_id'], backend_creds['service_secret'])
    worker_token_data = await validator.validate_service_token_generation(worker_creds['service_id'], worker_creds['service_secret'])
    assert backend_token_data['token'] != worker_token_data['token']
    backend_valid = await validator.validate_service_token_authentication(backend_token_data['token'])
    worker_valid = await validator.validate_service_token_authentication(worker_token_data['token'])
    assert backend_valid.get('valid') is True
    assert worker_valid.get('valid') is True
    assert backend_token_data['service_name'] == 'netra-backend'
    assert worker_token_data['service_name'] == 'netra-worker'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')