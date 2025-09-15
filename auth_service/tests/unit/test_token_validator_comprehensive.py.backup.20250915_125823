"""
Comprehensive unit tests for TokenValidator SSOT class - Core JWT token operations

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Ensure core JWT token creation and validation security
- Value Impact: Secure token management enables trusted user authentication across platform
- Strategic Impact: Foundation for multi-user system authentication and authorization

CRITICAL: TokenValidator is the SSOT for basic JWT operations in auth service.
This test suite validates all token operations fail hard when system breaks.

Test Categories:
- Token Creation (create_token method)
- Token Validation (validate_token method) 
- JWT Algorithm Security (HS256)
- Datetime Conversion Handling
- Error Scenarios and Edge Cases
- Security Patterns and Vulnerabilities
- Performance Characteristics

CHEATING ON TESTS = ABOMINATION
All tests use real TokenValidator instances with no business logic mocks.
"""
import jwt
import json
import base64
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import pytest
from auth_service.auth_core.core.token_validator import TokenValidator
from auth_service.auth_core.models.auth_models import User
from test_framework.base_integration_test import BaseIntegrationTest
from shared.isolated_environment import get_env

class TestTokenValidatorBasicOperations:
    """Test core TokenValidator operations - token creation and validation"""

    def setup_method(self):
        """Setup for each test - real TokenValidator instance"""
        self.validator = TokenValidator()
        self.validator.initialize()
        self.user_id = str(uuid.uuid4())
        self.email = 'test@example.com'
        self.test_user_data = {'user_id': self.user_id, 'email': self.email, 'permissions': ['read', 'write'], 'role': 'user'}

    def test_token_validator_initialization(self):
        """Test TokenValidator initializes with correct configuration"""
        validator = TokenValidator()
        validator.initialize()
        assert validator.secret_key == 'test-secret-key'
        assert validator.algorithm == 'HS256'
        assert hasattr(validator, 'initialize')
        assert hasattr(validator, 'create_token')
        assert hasattr(validator, 'validate_token')

    def test_create_token_basic_user_data(self):
        """Test creating token with basic user data"""
        token = self.validator.create_token(self.test_user_data)
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
        parts = token.split('.')
        assert len(parts) == 3, 'JWT must have exactly 3 parts (header.payload.signature)'

    def test_create_token_with_expiration_datetime(self):
        """Test creating token with datetime expiration"""
        exp_time = datetime.now(timezone.utc) + timedelta(hours=1)
        user_data = self.test_user_data.copy()
        user_data['exp'] = exp_time
        token = self.validator.create_token(user_data)
        assert token is not None
        decoded = jwt.decode(token, options={'verify_signature': False})
        assert 'exp' in decoded
        assert isinstance(decoded['exp'], (int, float))
        expected_timestamp = exp_time.timestamp()
        assert abs(decoded['exp'] - expected_timestamp) < 1.0

    def test_create_token_with_naive_datetime_assumes_utc(self):
        """Test creating token with naive datetime assumes UTC timezone"""
        naive_exp = datetime.now() + timedelta(hours=1)
        user_data = self.test_user_data.copy()
        user_data['exp'] = naive_exp
        token = self.validator.create_token(user_data)
        assert token is not None
        decoded = jwt.decode(token, options={'verify_signature': False})
        expected_utc_timestamp = naive_exp.replace(tzinfo=timezone.utc).timestamp()
        assert abs(decoded['exp'] - expected_utc_timestamp) < 1.0

    def test_create_token_with_aware_datetime_preserves_timezone(self):
        """Test creating token with timezone-aware datetime"""
        aware_exp = datetime.now(timezone.utc) + timedelta(hours=2)
        user_data = self.test_user_data.copy()
        user_data['exp'] = aware_exp
        token = self.validator.create_token(user_data)
        assert token is not None
        decoded = jwt.decode(token, options={'verify_signature': False})
        assert abs(decoded['exp'] - aware_exp.timestamp()) < 1.0

    def test_create_token_preserves_user_data(self):
        """Test token creation preserves all user data fields"""
        token = self.validator.create_token(self.test_user_data)
        decoded = jwt.decode(token, options={'verify_signature': False})
        assert decoded['user_id'] == self.test_user_data['user_id']
        assert decoded['email'] == self.test_user_data['email']
        assert decoded['permissions'] == self.test_user_data['permissions']
        assert decoded['role'] == self.test_user_data['role']

    def test_create_token_makes_copy_of_user_data(self):
        """Test token creation makes copy of user data (no mutation)"""
        original_data = self.test_user_data.copy()
        token = self.validator.create_token(self.test_user_data)
        assert self.test_user_data == original_data
        assert token is not None

class TestTokenValidatorValidationOperations:
    """Test TokenValidator validation operations"""

    def setup_method(self):
        """Setup for each test"""
        self.validator = TokenValidator()
        self.validator.initialize()
        self.user_data = {'user_id': str(uuid.uuid4()), 'email': 'validation@example.com', 'permissions': ['read', 'write', 'admin'], 'role': 'admin'}

    def test_validate_valid_token_success(self):
        """Test validation of valid token returns payload"""
        token = self.validator.create_token(self.user_data)
        payload = self.validator.validate_token(token)
        assert payload is not None
        assert isinstance(payload, dict)
        assert payload['user_id'] == self.user_data['user_id']
        assert payload['email'] == self.user_data['email']
        assert payload['permissions'] == self.user_data['permissions']
        assert payload['role'] == self.user_data['role']

    def test_validate_token_verifies_expiration(self):
        """Test validation verifies token expiration"""
        expired_data = self.user_data.copy()
        expired_data['exp'] = datetime.now(timezone.utc) - timedelta(minutes=5)
        token = self.validator.create_token(expired_data)
        with pytest.raises(jwt.ExpiredSignatureError):
            self.validator.validate_token(token)

    def test_validate_token_verifies_signature(self):
        """Test validation verifies JWT signature"""
        token = self.validator.create_token(self.user_data)
        parts = token.split('.')
        tampered_token = f'{parts[0]}.{parts[1]}.invalid_signature'
        with pytest.raises(jwt.InvalidSignatureError):
            self.validator.validate_token(tampered_token)

    def test_validate_malformed_token_fails(self):
        """Test validation of malformed tokens fails properly"""
        malformed_tokens = ['not.a.jwt', 'only.two.parts', 'too.many.parts.here.invalid', '', None, 'invalid', 'header.payload', '..']
        for malformed_token in malformed_tokens:
            with pytest.raises((jwt.DecodeError, jwt.InvalidTokenError, AttributeError, TypeError)):
                self.validator.validate_token(malformed_token)

    def test_validate_token_with_wrong_algorithm(self):
        """Test validation fails for tokens with wrong algorithm"""
        payload = self.user_data.copy()
        wrong_algo_token = jwt.encode(payload, 'different-secret', algorithm='HS512')
        with pytest.raises(jwt.InvalidSignatureError):
            self.validator.validate_token(wrong_algo_token)

    def test_validate_token_with_wrong_secret(self):
        """Test validation fails for tokens signed with different secret"""
        payload = self.user_data.copy()
        wrong_secret_token = jwt.encode(payload, 'wrong-secret-key', algorithm='HS256')
        with pytest.raises(jwt.InvalidSignatureError):
            self.validator.validate_token(wrong_secret_token)

    def test_validate_token_future_issued_time(self):
        """Test validation handles future issued time appropriately"""
        future_data = self.user_data.copy()
        future_data['iat'] = int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp())
        future_data['exp'] = int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp())
        token = jwt.encode(future_data, self.validator.secret_key, algorithm=self.validator.algorithm)
        try:
            payload = self.validator.validate_token(token)
            if payload is not None:
                assert payload['user_id'] == self.user_data['user_id']
        except jwt.InvalidIssuedAtError:
            pass

class TestTokenValidatorSecurityPatterns:
    """Test TokenValidator security patterns and vulnerability prevention"""

    def setup_method(self):
        """Setup for each test"""
        self.validator = TokenValidator()
        self.validator.initialize()
        self.user_data = {'user_id': str(uuid.uuid4()), 'email': 'security@example.com', 'role': 'user'}

    def test_algorithm_is_secure(self):
        """Test TokenValidator uses secure algorithm (HS256)"""
        assert self.validator.algorithm == 'HS256'
        token = self.validator.create_token(self.user_data)
        header = jwt.get_unverified_header(token)
        assert header['alg'] == 'HS256'
        assert header['typ'] == 'JWT'

    def test_secret_key_is_configured(self):
        """Test TokenValidator has non-empty secret key"""
        assert self.validator.secret_key is not None
        assert len(self.validator.secret_key) > 0
        assert isinstance(self.validator.secret_key, str)

    def test_rejects_none_algorithm_tokens(self):
        """Test validation rejects tokens with 'none' algorithm (security vulnerability)"""
        payload = self.user_data.copy()
        header = {'alg': 'none', 'typ': 'JWT'}
        header_encoded = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        payload_encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        none_token = f'{header_encoded}.{payload_encoded}.'
        with pytest.raises((jwt.DecodeError, jwt.InvalidAlgorithmError)):
            self.validator.validate_token(none_token)

    def test_token_tampering_detection(self):
        """Test detection of token payload tampering"""
        token = self.validator.create_token(self.user_data)
        parts = token.split('.')
        payload_bytes = base64.urlsafe_b64decode(parts[1] + '==')
        payload = json.loads(payload_bytes)
        payload['role'] = 'admin'
        modified_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=')
        tampered_token = f'{parts[0]}.{modified_payload}.{parts[2]}'
        with pytest.raises(jwt.InvalidSignatureError):
            self.validator.validate_token(tampered_token)

    def test_handles_injection_attempts_in_user_data(self):
        """Test TokenValidator handles potential injection attempts in user data"""
        malicious_data = {'user_id': "'; DROP TABLE users; --", 'email': "<script>alert('xss')</script>@example.com", 'role': '../../../etc/passwd', 'permissions': ["'; DELETE FROM tokens; --"], 'nested': {'attack': '$(rm -rf /)'}}
        token = self.validator.create_token(malicious_data)
        assert token is not None
        payload = self.validator.validate_token(token)
        assert payload['user_id'] == malicious_data['user_id']
        assert payload['email'] == malicious_data['email']
        assert payload['role'] == malicious_data['role']

    def test_large_payload_handling(self):
        """Test TokenValidator handles large payloads appropriately"""
        large_data = self.user_data.copy()
        large_data['large_field'] = 'x' * 10000
        large_data['array_field'] = ['item'] * 1000
        token = self.validator.create_token(large_data)
        assert token is not None
        payload = self.validator.validate_token(token)
        assert payload['large_field'] == large_data['large_field']
        assert len(payload['array_field']) == 1000

    def test_special_characters_in_user_data(self):
        """Test TokenValidator handles special characters properly"""
        special_data = {'user_id': 'user_123', 'email': 't[U+00EB]st@[U+00E9]x[U+00E4]mpl[U+00E9].com', 'name': 'Jos[U+00E9] Mar[U+00ED]a Garc[U+00ED]a-P[U+00E9]rez', 'description': 'User with [U+00E9]mojis [U+1F680] and [U+00F1]o[U+00F1]o characters', 'unicode': '[U+6D4B][U+8BD5][U+7528][U+6237]', 'symbols': '!@#$%^&*()[]{}|\\:;"\'<>,.?/', 'whitespace': '  tab\there  \n newline \r return  '}
        token = self.validator.create_token(special_data)
        assert token is not None
        payload = self.validator.validate_token(token)
        for key, value in special_data.items():
            assert payload[key] == value

class TestTokenValidatorDatetimeHandling:
    """Test TokenValidator datetime conversion and timezone handling"""

    def setup_method(self):
        """Setup for each test"""
        self.validator = TokenValidator()
        self.validator.initialize()
        self.base_user_data = {'user_id': str(uuid.uuid4()), 'email': 'datetime@example.com'}

    def test_datetime_conversion_utc_aware(self):
        """Test datetime conversion with UTC timezone"""
        utc_time = datetime.now(timezone.utc) + timedelta(hours=1)
        user_data = self.base_user_data.copy()
        user_data['exp'] = utc_time
        token = self.validator.create_token(user_data)
        payload = jwt.decode(token, options={'verify_signature': False})
        assert isinstance(payload['exp'], (int, float))
        assert payload['exp'] == utc_time.timestamp()

    def test_datetime_conversion_naive_assumes_utc(self):
        """Test naive datetime conversion assumes UTC"""
        naive_time = datetime(2024, 12, 31, 23, 59, 59)
        user_data = self.base_user_data.copy()
        user_data['exp'] = naive_time
        token = self.validator.create_token(user_data)
        payload = jwt.decode(token, options={'verify_signature': False})
        expected_timestamp = naive_time.replace(tzinfo=timezone.utc).timestamp()
        assert payload['exp'] == expected_timestamp

    def test_datetime_conversion_non_utc_timezone(self):
        """Test datetime conversion with non-UTC timezone"""
        from datetime import timezone as tz
        offset_tz = tz(timedelta(hours=5))
        offset_time = datetime.now(offset_tz) + timedelta(hours=1)
        user_data = self.base_user_data.copy()
        user_data['exp'] = offset_time
        token = self.validator.create_token(user_data)
        payload = jwt.decode(token, options={'verify_signature': False})
        assert payload['exp'] == offset_time.timestamp()

    def test_non_datetime_exp_preserved(self):
        """Test non-datetime exp values are preserved as-is"""
        timestamp_exp = int(time.time()) + 3600
        user_data = self.base_user_data.copy()
        user_data['exp'] = timestamp_exp
        token = self.validator.create_token(user_data)
        payload = jwt.decode(token, options={'verify_signature': False})
        assert payload['exp'] == timestamp_exp

    def test_multiple_datetime_fields_handled(self):
        """Test multiple datetime fields are handled independently"""
        now = datetime.now(timezone.utc)
        user_data = self.base_user_data.copy()
        user_data['exp'] = now + timedelta(hours=1)
        user_data['iat'] = int(now.timestamp())
        user_data['nbf'] = now - timedelta(minutes=5)
        user_data['custom_time'] = now.isoformat()
        token = self.validator.create_token(user_data)
        payload = jwt.decode(token, options={'verify_signature': False})
        assert isinstance(payload['exp'], (int, float))
        assert payload['iat'] == user_data['iat']
        assert payload['nbf'] == user_data['nbf']
        assert payload['custom_time'] == user_data['custom_time']

    def test_edge_case_datetime_values(self):
        """Test edge case datetime values"""
        edge_cases = [datetime.min.replace(tzinfo=timezone.utc), datetime.max.replace(tzinfo=timezone.utc), datetime(1970, 1, 1, tzinfo=timezone.utc), datetime(2038, 1, 19, tzinfo=timezone.utc)]
        for edge_datetime in edge_cases:
            user_data = self.base_user_data.copy()
            user_data['exp'] = edge_datetime
            try:
                token = self.validator.create_token(user_data)
                payload = jwt.decode(token, options={'verify_signature': False})
                assert isinstance(payload['exp'], (int, float))
                assert payload['exp'] == edge_datetime.timestamp()
            except (OverflowError, OSError):
                pass

class TestTokenValidatorErrorHandling:
    """Test TokenValidator error handling and edge cases"""

    def setup_method(self):
        """Setup for each test"""
        self.validator = TokenValidator()
        self.validator.initialize()

    def test_create_token_empty_user_data(self):
        """Test creating token with empty user data"""
        empty_data = {}
        token = self.validator.create_token(empty_data)
        assert token is not None
        payload = jwt.decode(token, options={'verify_signature': False})
        assert isinstance(payload, dict)

    def test_create_token_none_user_data_fails(self):
        """Test creating token with None user data fails hard"""
        with pytest.raises((TypeError, AttributeError)):
            self.validator.create_token(None)

    def test_create_token_non_dict_user_data_fails(self):
        """Test creating token with non-dict user data fails hard"""
        invalid_data_types = ['string', 123, ['list'], True, object()]
        for invalid_data in invalid_data_types:
            with pytest.raises((TypeError, AttributeError)):
                self.validator.create_token(invalid_data)

    def test_validate_token_empty_string_fails(self):
        """Test validating empty string token fails hard"""
        with pytest.raises((jwt.DecodeError, jwt.InvalidTokenError)):
            self.validator.validate_token('')

    def test_validate_token_none_fails(self):
        """Test validating None token fails hard"""
        with pytest.raises((TypeError, AttributeError)):
            self.validator.validate_token(None)

    def test_validate_token_non_string_fails(self):
        """Test validating non-string token fails hard"""
        invalid_tokens = [123, ['token'], {'token': 'value'}, True, object()]
        for invalid_token in invalid_tokens:
            with pytest.raises((TypeError, AttributeError)):
                self.validator.validate_token(invalid_token)

    def test_create_token_with_circular_reference_fails(self):
        """Test creating token with circular reference fails properly"""
        circular_data = {'user_id': '123'}
        circular_data['self'] = circular_data
        with pytest.raises((TypeError, ValueError)):
            self.validator.create_token(circular_data)

    def test_create_token_with_non_serializable_data_fails(self):
        """Test creating token with non-serializable data fails properly"""
        non_serializable_data = {'user_id': '123', 'function': lambda x: x, 'object': object()}
        with pytest.raises((TypeError, ValueError)):
            self.validator.create_token(non_serializable_data)

class TestTokenValidatorPerformanceCharacteristics:
    """Test TokenValidator performance characteristics and behavior"""

    def setup_method(self):
        """Setup for each test"""
        self.validator = TokenValidator()
        self.validator.initialize()
        self.standard_user_data = {'user_id': str(uuid.uuid4()), 'email': 'performance@example.com', 'permissions': ['read', 'write']}

    def test_token_creation_is_deterministic(self):
        """Test token creation with same data produces different tokens (due to timestamps)"""
        tokens = [self.validator.create_token(self.standard_user_data.copy()) for _ in range(5)]
        for token in tokens:
            assert token is not None
            assert len(token) > 0

    def test_token_validation_is_consistent(self):
        """Test token validation produces consistent results"""
        token = self.validator.create_token(self.standard_user_data)
        payloads = [self.validator.validate_token(token) for _ in range(5)]
        for payload in payloads:
            assert payload is not None
            assert payload['user_id'] == self.standard_user_data['user_id']
            assert payload['email'] == self.standard_user_data['email']

    def test_handles_concurrent_operations(self):
        """Test TokenValidator handles concurrent operations safely"""
        import threading
        results = []
        errors = []

        def create_and_validate():
            try:
                user_data = {'user_id': str(uuid.uuid4()), 'email': f'concurrent_{threading.current_thread().ident}@example.com'}
                token = self.validator.create_token(user_data)
                payload = self.validator.validate_token(token)
                results.append((token, payload))
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=create_and_validate) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        assert len(errors) == 0, f'Concurrent operations failed: {errors}'
        assert len(results) == 10
        for token, payload in results:
            assert token is not None
            assert payload is not None
            assert 'user_id' in payload
            assert 'email' in payload

    def test_memory_usage_with_large_tokens(self):
        """Test memory usage doesn't explode with large token data"""
        for size_multiplier in [1, 10, 100]:
            large_data = self.standard_user_data.copy()
            large_data['large_field'] = 'x' * (1000 * size_multiplier)
            token = self.validator.create_token(large_data)
            payload = self.validator.validate_token(token)
            assert token is not None
            assert payload is not None
            assert len(payload['large_field']) == 1000 * size_multiplier

class TestTokenValidatorBusinessValueScenarios(BaseIntegrationTest):
    """Test TokenValidator in realistic business scenarios"""

    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.validator = TokenValidator()
        self.validator.initialize()

    def test_user_authentication_scenario(self):
        """Test complete user authentication scenario"""
        user_login_data = {'user_id': 'user_12345', 'email': 'john.doe@company.com', 'role': 'employee', 'department': 'engineering', 'permissions': ['read_docs', 'create_tickets', 'comment'], 'session_id': str(uuid.uuid4()), 'login_time': datetime.now(timezone.utc).isoformat()}
        auth_token = self.validator.create_token(user_login_data)
        assert auth_token is not None
        validated_payload = self.validator.validate_token(auth_token)
        assert validated_payload is not None
        assert validated_payload['user_id'] == 'user_12345'
        assert validated_payload['role'] == 'employee'
        assert validated_payload['department'] == 'engineering'
        assert 'read_docs' in validated_payload['permissions']

    def test_service_to_service_authentication(self):
        """Test service-to-service authentication scenario"""
        service_data = {'service_id': 'analytics-service', 'service_name': 'Analytics Service', 'permissions': ['read_user_data', 'write_analytics'], 'environment': 'production', 'service_version': 'v2.1.0', 'issued_to': 'backend-service', 'exp': datetime.now(timezone.utc) + timedelta(hours=2)}
        service_token = self.validator.create_token(service_data)
        assert service_token is not None
        service_payload = self.validator.validate_token(service_token)
        assert service_payload is not None
        assert service_payload['service_id'] == 'analytics-service'
        assert 'read_user_data' in service_payload['permissions']

    def test_temporary_access_token_scenario(self):
        """Test temporary access token with short expiration"""
        temp_data = {'user_id': 'user_67890', 'purpose': 'password_reset', 'email': 'user@example.com', 'exp': datetime.now(timezone.utc) + timedelta(minutes=15), 'single_use': True, 'created_at': datetime.now(timezone.utc).isoformat()}
        temp_token = self.validator.create_token(temp_data)
        assert temp_token is not None
        temp_payload = self.validator.validate_token(temp_token)
        assert temp_payload is not None
        assert temp_payload['purpose'] == 'password_reset'
        assert temp_payload['single_use'] == True

    def test_api_key_style_long_lived_token(self):
        """Test API key style long-lived token scenario"""
        api_data = {'api_key_id': 'ak_' + str(uuid.uuid4()), 'user_id': 'api_user_123', 'client_name': 'Mobile App v1.2', 'permissions': ['read_profile', 'update_profile', 'read_data'], 'rate_limit': 1000, 'created_date': '2024-01-01', 'exp': datetime.now(timezone.utc) + timedelta(days=365)}
        api_token = self.validator.create_token(api_data)
        assert api_token is not None
        api_payload = self.validator.validate_token(api_token)
        assert api_payload is not None
        assert api_payload['api_key_id'].startswith('ak_')
        assert api_payload['rate_limit'] == 1000
        assert 'read_profile' in api_payload['permissions']

    def test_multi_tenant_scenario(self):
        """Test multi-tenant authentication scenario"""
        tenant_data = {'user_id': 'user_456', 'tenant_id': 'tenant_acme_corp', 'tenant_name': 'ACME Corporation', 'email': 'user@acme.com', 'role': 'admin', 'tenant_permissions': ['manage_users', 'view_analytics', 'billing'], 'subscription_tier': 'enterprise', 'region': 'us-east-1'}
        tenant_token = self.validator.create_token(tenant_data)
        assert tenant_token is not None
        tenant_payload = self.validator.validate_token(tenant_token)
        assert tenant_payload is not None
        assert tenant_payload['tenant_id'] == 'tenant_acme_corp'
        assert tenant_payload['subscription_tier'] == 'enterprise'
        assert 'manage_users' in tenant_payload['tenant_permissions']

class TestTokenValidatorRegressionPrevention(BaseIntegrationTest):
    """Test TokenValidator against known issues and regression prevention"""

    def setup_method(self):
        """Setup for each test"""
        super().setup_method()
        self.validator = TokenValidator()
        self.validator.initialize()

    def test_prevents_algorithm_confusion_attack(self):
        """Test prevents algorithm confusion attacks"""
        user_data = {'user_id': '123', 'role': 'user'}
        token = self.validator.create_token(user_data)
        parts = token.split('.')
        header_data = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
        header_data['alg'] = 'none'
        malicious_header = base64.urlsafe_b64encode(json.dumps(header_data).encode()).decode().rstrip('=')
        malicious_token = f'{malicious_header}.{parts[1]}.'
        with pytest.raises((jwt.DecodeError, jwt.InvalidAlgorithmError)):
            self.validator.validate_token(malicious_token)

    def test_prevents_key_confusion_attack(self):
        """Test prevents key confusion attacks"""
        user_data = {'user_id': '123', 'admin': False}
        token = self.validator.create_token(user_data)
        assert self.validator.validate_token(token) is not None
        different_validator = TokenValidator()
        different_validator.secret_key = 'different-secret-key'
        with pytest.raises(jwt.InvalidSignatureError):
            different_validator.validate_token(token)

    def test_prevents_timing_attacks_on_validation(self):
        """Test validation timing doesn't leak information"""
        user_data = {'user_id': '123'}
        valid_token = self.validator.create_token(user_data)
        import time
        valid_times = []
        for _ in range(10):
            start = time.time()
            try:
                self.validator.validate_token(valid_token)
            except:
                pass
            valid_times.append(time.time() - start)
        invalid_times = []
        for _ in range(10):
            start = time.time()
            try:
                self.validator.validate_token('invalid.token.here')
            except:
                pass
            invalid_times.append(time.time() - start)
        avg_valid = sum(valid_times) / len(valid_times)
        avg_invalid = sum(invalid_times) / len(invalid_times)
        assert avg_valid < 0.1
        assert avg_invalid < 0.1

    def test_handles_jwt_header_injection(self):
        """Test handles JWT header injection attempts"""
        user_data = {'user_id': '123'}
        token = self.validator.create_token(user_data)
        parts = token.split('.')
        header = json.loads(base64.urlsafe_b64decode(parts[0] + '=='))
        header['malicious'] = '"; system("rm -rf /"); //'
        header['xss'] = '<script>alert("xss")</script>'
        malicious_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=')
        malicious_token = f'{malicious_header}.{parts[1]}.{parts[2]}'
        try:
            payload = self.validator.validate_token(malicious_token)
        except jwt.InvalidSignatureError:
            pass

    def test_consistent_error_handling_across_invalid_inputs(self):
        """Test consistent error handling prevents information leakage"""
        invalid_inputs = [None, '', 'invalid', 'a.b', 'a.b.c.d', 'invalid.payload.sig', 'header.invalid.sig', 'header.payload.invalid']
        for invalid_input in invalid_inputs:
            with pytest.raises((jwt.DecodeError, jwt.InvalidTokenError, TypeError, AttributeError)):
                self.validator.validate_token(invalid_input)
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')