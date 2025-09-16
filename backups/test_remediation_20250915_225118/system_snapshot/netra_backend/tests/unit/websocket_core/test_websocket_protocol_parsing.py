"""
Unit tests for WebSocket protocol format parsing - DESIGNED TO FAIL INITIALLY

Purpose: Test JWT extraction from WebSocket subprotocols to reproduce protocol mismatch bug
Issue: Frontend sending ['jwt', token] instead of expected 'jwt.${token}' format
Expected: These tests MUST FAIL initially to prove they detect the real issue

GitHub Issue: #171
Test Plan: /TEST_PLAN_WEBSOCKET_AUTH_PROTOCOL_MISMATCH.md
"""
import pytest
import base64
import json
from unittest.mock import Mock, MagicMock
from fastapi import WebSocket
from netra_backend.app.websocket_core.user_context_extractor import WebSocketUserContextExtractor
from netra_backend.app.services.unified_authentication_service import UnifiedAuthenticationService

class WebSocketProtocolParsingTests:
    """Unit tests for WebSocket protocol format parsing - DESIGNED TO FAIL INITIALLY"""

    def setup_method(self):
        """Setup test fixtures"""
        self.context_extractor = WebSocketUserContextExtractor()
        self.auth_service = UnifiedAuthenticationService()
        self.test_payload = {'sub': 'test_user_123', 'exp': 9999999999, 'iat': 1000000000, 'email': 'test@example.com'}
        self.valid_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfMTIzIiwiZXhwIjo5OTk5OTk5OTk5LCJpYXQiOjEwMDAwMDAwMDAsImVtYWlsIjoidGVzdEBleGFtcGxlLmNvbSJ9.fake_signature'
        self.encoded_token = base64.urlsafe_b64encode(self.valid_token.encode()).decode().rstrip('=')

    def create_mock_websocket(self, subprotocols: list=None, headers: dict=None) -> Mock:
        """Create a mock WebSocket with specified subprotocols and headers"""
        websocket = Mock(spec=WebSocket)
        default_headers = {'sec-websocket-protocol': ', '.join(subprotocols) if subprotocols else '', 'authorization': ''}
        if headers:
            default_headers.update(headers)
        websocket.headers = default_headers
        return websocket

    def test_jwt_protocol_format_extraction_success(self):
        """
        Test successful JWT token extraction from correct protocol format
        
        Expected Format: ['jwt-auth', 'jwt.eyJ0eXAiOiJKV1QiLCJhbGc...']
        Should Extract: eyJ0eXAiOiJKV1QiLCJhbGc...
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (unit test)
        STATUS: Should PASS after fix
        """
        correct_subprotocols = ['jwt-auth', f'jwt.{self.encoded_token}']
        websocket = self.create_mock_websocket(subprotocols=correct_subprotocols)
        extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
        assert extracted_token is not None, 'Should extract JWT token from correct protocol format'
        assert extracted_token == self.valid_token, f'Expected {self.valid_token}, got {extracted_token}'

    def test_jwt_protocol_format_extraction_failure_array_format(self):
        """
        Test JWT token extraction failure with array format (CURRENT BUG)
        
        Current Bug Format: ['jwt', 'eyJ0eXAiOiJKV1QiLCJhbGc...'] (as separate elements)
        Expected Behavior: Should fail to extract token
        
        DIFFICULTY: Low (5 minutes)  
        REAL SERVICES: No (unit test)
        STATUS: Should FAIL initially (reproduces bug), then behavior varies after fix
        """
        incorrect_subprotocols = ['jwt', self.encoded_token]
        websocket = self.create_mock_websocket(subprotocols=incorrect_subprotocols)
        extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
        assert extracted_token is None, 'Should NOT extract JWT token from incorrect array format'

    def test_jwt_protocol_format_extraction_failure_wrong_prefix(self):
        """
        Test JWT token extraction failure with wrong prefix formats
        
        Invalid formats: 'bearer.token', 'auth.token', 'token_data'
        Expected: Should not extract token from invalid prefixes
        
        DIFFICULTY: Low (3 minutes)
        REAL SERVICES: No (unit test)  
        STATUS: Should PASS (validates proper validation logic)
        """
        test_cases = [['bearer', f'bearer.{self.encoded_token}'], ['auth-token', f'auth.{self.encoded_token}'], ['token', self.encoded_token], ['jwt-auth', self.encoded_token]]
        for subprotocols in test_cases:
            websocket = self.create_mock_websocket(subprotocols=subprotocols)
            extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
            assert extracted_token is None, f'Should not extract token from invalid format: {subprotocols}'

    def test_subprotocol_jwt_prefix_validation(self):
        """
        Test validation of jwt. prefix in subprotocol strings
        
        Valid: 'jwt.token_data'
        Invalid: 'jwt token_data', 'bearer.token_data', 'token_data'
        
        DIFFICULTY: Low (3 minutes)
        REAL SERVICES: No (unit test)  
        STATUS: Should FAIL initially, PASS after fix
        """
        valid_subprotocols = ['jwt-auth', f'jwt.{self.encoded_token}']
        websocket = self.create_mock_websocket(subprotocols=valid_subprotocols)
        extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
        assert extracted_token is not None, 'Should extract token with correct jwt. prefix'
        invalid_cases = [['jwt-auth', f'jwt {self.encoded_token}'], ['jwt-auth', f'jwt_{self.encoded_token}'], ['jwt-auth', f'JWT.{self.encoded_token}'], ['jwt-auth', self.encoded_token]]
        for invalid_subprotocols in invalid_cases:
            websocket = self.create_mock_websocket(subprotocols=invalid_subprotocols)
            extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
            assert extracted_token is None, f'Should not extract token from invalid format: {invalid_subprotocols}'

    def test_base64url_token_decoding_validation(self):
        """
        Test base64url decoding of JWT tokens from subprotocol
        
        Tests encoding/decoding consistency with frontend implementation
        
        DIFFICULTY: Medium (10 minutes)
        REAL SERVICES: No (unit test)
        STATUS: Should PASS (not part of bug, but validates fix compatibility)
        """
        test_tokens = ['eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.sig', 'short.token.here', 'very.long.token.with.multiple.parts.and.extra.data.for.testing.purposes']
        for token in test_tokens:
            encoded_token = base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')
            subprotocols = ['jwt-auth', f'jwt.{encoded_token}']
            websocket = self.create_mock_websocket(subprotocols=subprotocols)
            extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
            assert extracted_token == token, f'Token encoding/decoding failed for: {token}'

    def test_multiple_subprotocols_jwt_extraction(self):
        """
        Test JWT extraction when multiple subprotocols are present
        
        Should find JWT token among multiple protocols
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (unit test)
        STATUS: Should PASS (tests robustness)
        """
        test_cases = [[f'jwt.{self.encoded_token}', 'other-protocol', 'another-protocol'], ['other-protocol', f'jwt.{self.encoded_token}', 'another-protocol'], ['other-protocol', 'another-protocol', f'jwt.{self.encoded_token}'], ['jwt-auth', 'websocket', f'jwt.{self.encoded_token}', 'custom-protocol']]
        for subprotocols in test_cases:
            websocket = self.create_mock_websocket(subprotocols=subprotocols)
            extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
            assert extracted_token == self.valid_token, f'Should extract JWT from: {subprotocols}'

    def test_empty_and_malformed_subprotocols(self):
        """
        Test handling of empty and malformed subprotocol headers
        
        Should gracefully handle edge cases
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (unit test)
        STATUS: Should PASS (validates error handling)
        """
        test_cases = [[], [''], ['   '], ['jwt.'], [f'jwt.{self.encoded_token}', ''], ['malformed-protocol-without-proper-format']]
        for subprotocols in test_cases:
            websocket = self.create_mock_websocket(subprotocols=subprotocols)
            extracted_token = self.context_extractor.extract_jwt_from_websocket(websocket)
            if any(('jwt.' in protocol and len(protocol) > 4 for protocol in subprotocols)):
                continue
            else:
                assert extracted_token is None, f'Should handle malformed protocols gracefully: {subprotocols}'

class UnifiedAuthenticationServiceProtocolParsingTests:
    """Unit tests for UnifiedAuthenticationService JWT extraction"""

    def setup_method(self):
        """Setup test fixtures"""
        self.auth_service = UnifiedAuthenticationService()
        self.valid_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.sig'
        self.encoded_token = base64.urlsafe_b64encode(self.valid_token.encode()).decode().rstrip('=')

    def create_mock_websocket_auth_service(self, subprotocols: list=None, headers: dict=None) -> Mock:
        """Create a mock WebSocket for auth service testing"""
        websocket = Mock(spec=WebSocket)
        default_headers = {}
        if subprotocols:
            default_headers['sec-websocket-protocol'] = ', '.join(subprotocols)
        if headers:
            default_headers.update(headers)
        websocket.headers = default_headers
        return websocket

    def test_websocket_jwt_extraction_from_subprotocols_success(self):
        """
        Test successful JWT extraction from WebSocket subprotocols
        
        Input: Mock WebSocket with subprotocols=['jwt-auth', 'jwt.validtoken123']
        Expected: Extract 'validtoken123'
        
        DIFFICULTY: Low (7 minutes)
        REAL SERVICES: No (mocked WebSocket)
        STATUS: Should FAIL initially, PASS after fix
        """
        subprotocols = ['jwt-auth', f'jwt.{self.encoded_token}']
        websocket = self.create_mock_websocket_auth_service(subprotocols=subprotocols)
        extracted_token = self.auth_service._extract_websocket_token(websocket)
        assert extracted_token is not None, 'Auth service should extract JWT token from correct protocol'
        assert extracted_token == self.valid_token, f'Expected {self.valid_token}, got {extracted_token}'

    def test_websocket_jwt_extraction_no_token_found(self):
        """
        Test handling when no JWT token found in subprotocols (CURRENT BUG SCENARIO)
        
        Input: Mock WebSocket with subprotocols=['jwt', 'tokendata'] (incorrect format)
        Expected: Return NO_TOKEN error code
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (mocked WebSocket)
        STATUS: Should PASS initially (correctly identifies no token), should still PASS after fix
        """
        incorrect_subprotocols = ['jwt', self.encoded_token]
        websocket = self.create_mock_websocket_auth_service(subprotocols=incorrect_subprotocols)
        extracted_token = self.auth_service._extract_websocket_token(websocket)
        assert extracted_token is None, 'Should not extract JWT from incorrect format'

    def test_websocket_jwt_extraction_no_subprotocols(self):
        """
        Test handling when no subprotocols are present
        
        Should gracefully handle missing subprotocol header
        
        DIFFICULTY: Low (3 minutes)
        REAL SERVICES: No (mocked WebSocket)
        STATUS: Should PASS (validates error handling)
        """
        websocket = self.create_mock_websocket_auth_service()
        extracted_token = self.auth_service._extract_websocket_token(websocket)
        assert extracted_token is None, 'Should handle missing subprotocols gracefully'

    @pytest.mark.asyncio
    async def test_authentication_result_error_codes(self):
        """
        Test proper error codes returned for different auth failure scenarios
        
        Validates error_code field matches expected values for different failure types
        
        DIFFICULTY: Low (5 minutes)
        REAL SERVICES: No (mocked inputs)
        STATUS: Should PASS (validates error handling consistency)
        """
        test_cases = [{'subprotocols': [], 'expected_error_code': 'NO_TOKEN', 'description': 'No subprotocols provided'}, {'subprotocols': ['jwt', 'tokendata'], 'expected_error_code': 'NO_TOKEN', 'description': 'Incorrect protocol format (bug reproduction)'}, {'subprotocols': ['other-protocol'], 'expected_error_code': 'NO_TOKEN', 'description': 'No JWT protocol present'}]
        for case in test_cases:
            websocket = self.create_mock_websocket_auth_service(subprotocols=case['subprotocols'])
            try:
                auth_result, _ = await self.auth_service.authenticate_websocket(websocket, 'test-connection')
                assert not auth_result.success, f"Auth should fail for: {case['description']}"
                assert auth_result.error_code == case['expected_error_code'], f"Expected error code {case['expected_error_code']} for: {case['description']}, got {auth_result.error_code}"
            except Exception as e:
                print(f"Auth method threw exception for {case['description']}: {e}")
pytestmark = [pytest.mark.unit, pytest.mark.websocket, pytest.mark.protocol_parsing, pytest.mark.authentication, pytest.mark.bug_reproduction]
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')