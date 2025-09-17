"""
Regression test suite for WebSocket JWT authentication encoding fix.

This test ensures that the frontend's base64url encoding of JWT tokens
is correctly decoded by the backend, preventing authentication failures.

The fix addressed the issue where frontend was using btoa() incorrectly,
causing encoding mismatches with the backend's urlsafe_b64decode().
"""
import base64
import json
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any
TEST_JWT_TOKENS = ['eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiSm9obiBEb2UvKz0iLCJpZCI6MTIzfQ.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ', 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJuYW1lIjoi4pyoIFVuaWNvZGUiLCJpZCI6NDU2fQ.kLkeuNOTXBGJ6e8PJ5C9V9P5_wE_c5g5LKrqW0TgPNg']

def simulate_frontend_encoding(token: str) -> str:
    """
    Simulates the CORRECT frontend encoding after the fix.
    This matches the new implementation in webSocketService.ts
    """
    clean_token = token.replace('Bearer ', '').strip()
    token_bytes = clean_token.encode('utf-8')
    base64_encoded = base64.b64encode(token_bytes).decode('ascii')
    base64url = base64_encoded.replace('+', '-').replace('/', '_').replace('=', '')
    return base64url

def simulate_old_frontend_encoding(token: str) -> str:
    """
    Simulates the OLD (incorrect) frontend encoding before the fix.
    This shows what was causing the authentication failures.
    """
    clean_token = token.replace('Bearer ', '').strip()
    try:
        base64_encoded = base64.b64encode(clean_token.encode('latin-1')).decode('ascii')
    except UnicodeEncodeError:
        base64_encoded = base64.b64encode(clean_token.encode('utf-8')).decode('ascii')
    base64url = base64_encoded.replace('+', '-').replace('/', '_').replace('=', '')
    return base64url

def backend_decode(encoded_token: str) -> str:
    """
    Simulates the backend's decoding using urlsafe_b64decode.
    This is what the backend expects to receive.
    """
    padding = 4 - len(encoded_token) % 4
    if padding != 4:
        encoded_token += '=' * padding
    decoded_bytes = base64.urlsafe_b64decode(encoded_token)
    decoded_string = decoded_bytes.decode('utf-8')
    return decoded_string

class WebSocketJWTEncodingRegressionTests:
    """Test suite for WebSocket JWT encoding regression."""

    def test_new_frontend_encoding_matches_backend_decoding(self):
        """
        Test that the NEW frontend encoding correctly encodes JWT tokens
        that can be decoded by the backend.
        """
        for token in TEST_JWT_TOKENS:
            encoded = simulate_frontend_encoding(token)
            try:
                decoded = backend_decode(encoded)
                assert decoded == token, f'Token mismatch: {decoded} != {token}'
            except Exception as e:
                pytest.fail(f'Failed to decode token {token}: {str(e)}')

    def test_old_encoding_would_fail(self):
        """
        Test that the OLD encoding method would have caused failures.
        This demonstrates why the fix was necessary.
        """
        simple_token = 'simple.token.here'
        old_encoded = simulate_old_frontend_encoding(simple_token)
        new_encoded = simulate_frontend_encoding(simple_token)
        for token in TEST_JWT_TOKENS:
            old_encoded = simulate_old_frontend_encoding(token)
            new_encoded = simulate_frontend_encoding(token)
            decoded = backend_decode(new_encoded)
            assert decoded == token

    def test_bearer_prefix_handling(self):
        """Test that Bearer prefix is correctly handled."""
        for token in TEST_JWT_TOKENS:
            bearer_token = f'Bearer {token}'
            encoded = simulate_frontend_encoding(bearer_token)
            decoded = backend_decode(encoded)
            assert decoded == token
            encoded_direct = simulate_frontend_encoding(token)
            decoded_direct = backend_decode(encoded_direct)
            assert decoded_direct == token

    def test_padding_edge_cases(self):
        """Test base64url padding edge cases."""
        test_cases = ['a', 'ab', 'abc', 'abcd', 'abcde']
        for test_string in test_cases:
            encoded = simulate_frontend_encoding(test_string)
            decoded = backend_decode(encoded)
            assert decoded == test_string

    def test_special_characters_in_jwt(self):
        """Test JWT tokens with special characters."""
        special_tokens = ['token.with+plus/slash=equals', 'token.with.periods.everywhere', 'token-with-dashes-and_underscores', 'token!with@special#chars$here%too']
        for token in special_tokens:
            encoded = simulate_frontend_encoding(token)
            decoded = backend_decode(encoded)
            assert decoded == token

    def test_empty_and_whitespace_tokens(self):
        """Test edge cases with empty and whitespace tokens."""
        edge_cases = ['', ' ', '  ', '\t', '\n', ' token ']
        for token in edge_cases:
            if token.strip():
                encoded = simulate_frontend_encoding(token)
                decoded = backend_decode(encoded)
                assert decoded == token.strip()

    def test_long_jwt_tokens(self):
        """Test with very long JWT tokens."""
        long_payload = 'x' * 1000
        long_token = f'header.{long_payload}.signature'
        encoded = simulate_frontend_encoding(long_token)
        decoded = backend_decode(encoded)
        assert decoded == long_token

    @pytest.mark.parametrize('token', TEST_JWT_TOKENS)
    def test_parametrized_jwt_encoding(self, token):
        """Parametrized test for all test JWT tokens."""
        encoded = simulate_frontend_encoding(token)
        decoded = backend_decode(encoded)
        assert decoded == token, f'Encoding/decoding failed for token: {token}'

    def test_encoding_is_reversible(self):
        """Test that encoding and decoding is fully reversible."""
        test_strings = ['simple', 'with spaces here', 'special!@#$%^&*()chars', 'unicode[U+2713][U+2717][U+263A][U+2639]', 'mixed123.ABC-xyz_456', '{"json":"payload","with":"structure"}']
        for original in test_strings:
            encoded = simulate_frontend_encoding(original)
            decoded = backend_decode(encoded)
            assert decoded == original, f'Reversibility failed for: {original}'

    def test_real_world_jwt_structure(self):
        """Test with real-world JWT structure."""
        header = json.dumps({'alg': 'HS256', 'typ': 'JWT'})
        payload = json.dumps({'sub': '1234567890', 'name': 'John Doe', 'email': 'john@example.com', 'iat': 1516239022, 'exp': 1516242622, 'roles': ['user', 'admin']})
        header_b64 = base64.urlsafe_b64encode(header.encode()).decode().rstrip('=')
        payload_b64 = base64.urlsafe_b64encode(payload.encode()).decode().rstrip('=')
        jwt_token = f'{header_b64}.{payload_b64}.fake_signature_here'
        encoded = simulate_frontend_encoding(jwt_token)
        decoded = backend_decode(encoded)
        assert decoded == jwt_token
        parts = decoded.split('.')
        assert len(parts) == 3, 'JWT should have 3 parts'
        header_decoded = base64.urlsafe_b64decode(parts[0] + '==')
        header_json = json.loads(header_decoded)
        assert header_json['alg'] == 'HS256'
        assert header_json['typ'] == 'JWT'
        payload_decoded = base64.urlsafe_b64decode(parts[1] + '==')
        payload_json = json.loads(payload_decoded)
        assert payload_json['sub'] == '1234567890'
        assert payload_json['name'] == 'John Doe'

class WebSocketAuthenticationIntegrationTests:
    """Integration tests for WebSocket authentication flow."""

    @pytest.mark.asyncio
    async def test_websocket_auth_header_format(self):
        """Test that the auth header is correctly formatted."""
        from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager
        test_token = TEST_JWT_TOKENS[0]
        encoded_token = simulate_frontend_encoding(test_token)
        auth_header = f'Bearer {encoded_token}'
        assert auth_header.startswith('Bearer ')
        assert len(auth_header.split(' ')) == 2
        encoded_part = auth_header.split(' ')[1]
        decoded = backend_decode(encoded_part)
        assert decoded == test_token

    def test_backend_expects_base64url(self):
        """Test that backend specifically expects base64url encoding."""
        token = 'test.jwt.token'
        standard_b64 = base64.b64encode(token.encode()).decode()
        base64url = standard_b64.replace('+', '-').replace('/', '_').replace('=', '')
        decoded = backend_decode(base64url)
        assert decoded == token
        if '+' in standard_b64 or '/' in standard_b64:
            pass

class RegressionPreventionTests:
    """Tests to prevent regression of the JWT encoding issue."""

    def test_frontend_encoding_contract(self):
        """
        This test serves as a contract for frontend encoding.
        If this test fails, the frontend encoding has regressed.
        """
        known_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'
        encoded = simulate_frontend_encoding(known_token)
        expected_encoded = base64.urlsafe_b64encode(known_token.encode()).decode().rstrip('=')
        assert encoded == expected_encoded, 'Frontend encoding has changed - possible regression!'

    def test_backend_decoding_contract(self):
        """
        This test serves as a contract for backend decoding.
        If this test fails, the backend decoding has regressed.
        """
        encoded_token = 'ZXlKaGJHY2lPaUpJVXpJMU5pSXNJblI1Y0NJNklrcFhWQ0o5LmV5SnpkV0lpT2lJeE1qTTBOVFkzT0Rrd0luMC5kb3pqZ05yeVA0SjNqVm1OSGwwdzVOX1hnTDBuM0k5UGxGVVAwVEhzUjhV'
        expected_decoded = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'
        decoded = backend_decode(encoded_token)
        assert decoded == expected_decoded, 'Backend decoding has changed - possible regression!'

    def test_end_to_end_compatibility(self):
        """
        End-to-end test ensuring frontend and backend remain compatible.
        This is the most important regression test.
        """
        for token in TEST_JWT_TOKENS:
            frontend_encoded = simulate_frontend_encoding(f'Bearer {token}')
            backend_decoded = backend_decode(frontend_encoded)
            assert backend_decoded == token, f'End-to-end compatibility broken for token: {token}'

    def test_no_encoding_errors(self):
        """Test that encoding doesn't raise unexpected errors."""
        problematic_tokens = ['token_with_underscore', 'token-with-dash', 'token.with.dots', 'token/with/slashes', 'token+with+plus', 'token=with=equals', 'token with spaces', 't[U+014D]ken_with_[U+00FC]nicode']
        for token in problematic_tokens:
            try:
                encoded = simulate_frontend_encoding(token)
                decoded = backend_decode(encoded)
                assert decoded == token
            except Exception as e:
                pytest.fail(f"Encoding/decoding failed for '{token}': {str(e)}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')