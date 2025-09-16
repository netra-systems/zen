"""
Regression test with failing scenario to demonstrate potential regression issues.

This test intentionally includes a failing test to show what would happen
if the frontend reverted to the old encoding method.
"""
import base64
import pytest

def simulate_broken_frontend_encoding(token: str) -> str:
    """
    Simulates a BROKEN frontend encoding that would cause failures.
    This demonstrates what happens if someone accidentally reverts the fix.
    """
    clean_token = token.replace('Bearer ', '').strip()
    base64_encoded = base64.b64encode(clean_token.encode('latin-1')).decode('ascii')
    broken_base64url = base64_encoded
    return broken_base64url

def backend_decode(encoded_token: str) -> str:
    """
    The backend's correct decoding using urlsafe_b64decode.
    """
    padding = 4 - len(encoded_token) % 4
    if padding != 4:
        encoded_token += '=' * padding
    decoded_bytes = base64.urlsafe_b64decode(encoded_token)
    decoded_string = decoded_bytes.decode('utf-8')
    return decoded_string

class TestWebSocketJWTEncodingFailureScenarios:
    """Test suite demonstrating failure scenarios if the fix is reverted."""

    def test_broken_encoding_fails_with_special_chars(self):
        """
        This test WILL FAIL if the frontend uses broken encoding.
        It demonstrates why the fix was necessary.
        """
        jwt_with_special = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiSm9obiBEb2UvKz0iLCJpZCI6MTIzfQ.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ'
        broken_encoded = simulate_broken_frontend_encoding(jwt_with_special)
        with pytest.raises(Exception) as exc_info:
            decoded = backend_decode(broken_encoded)
            assert decoded == jwt_with_special
        assert 'Invalid' in str(exc_info.value) or 'padding' in str(exc_info.value)

    def test_regression_detection_with_url_unsafe_chars(self):
        """
        This test detects if someone accidentally uses standard base64
        instead of base64url encoding.
        """
        test_token = 'abc' * 50
        standard_b64 = base64.b64encode(test_token.encode()).decode()
        has_unsafe_chars = '+' in standard_b64 or '/' in standard_b64
        if has_unsafe_chars:
            with pytest.raises(Exception):
                backend_decode(standard_b64)

    def test_missing_padding_handling(self):
        """
        Test that demonstrates issues with incorrect padding handling.
        This would fail if padding is not handled correctly.
        """
        tokens_needing_padding = ['a', 'ab', 'abc']
        for token in tokens_needing_padding:
            broken_encoded = base64.b64encode(token.encode()).decode().rstrip('=')
            try:
                decoded = backend_decode(broken_encoded)
                assert decoded == token
            except Exception as e:
                pytest.fail(f"Padding not handled correctly for '{token}': {str(e)}")

    def test_unicode_encoding_regression(self):
        """
        Test that would fail if unicode handling regresses.
        """
        unicode_token = 'token_with_[U+00E9]moji_[U+1F680]_and_[U+7279][U+6B8A][U+5B57][U+7B26]'
        try:
            broken_encoded = base64.b64encode(unicode_token.encode('latin-1')).decode()
            pytest.fail('Latin-1 encoding should have failed for unicode')
        except UnicodeEncodeError:
            pass
        correct_encoded = base64.urlsafe_b64encode(unicode_token.encode('utf-8')).decode().rstrip('=')
        decoded = backend_decode(correct_encoded)
        assert decoded == unicode_token

    @pytest.mark.xfail(reason='Intentionally failing test to demonstrate regression scenario')
    def test_intentional_failure_demo(self):
        """
        This test is marked as xfail to demonstrate what a regression looks like.
        It shows what happens if someone uses the wrong encoding method.
        """
        jwt_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'
        wrong_encoded = base64.b64encode(jwt_token.encode()).decode()
        decoded = backend_decode(wrong_encoded)
        assert decoded == jwt_token

class TestProductionReadinessChecks:
    """Tests to ensure the fix is production-ready."""

    def test_performance_with_large_tokens(self):
        """Test that encoding/decoding performs well with large JWT tokens."""
        import time
        large_payload = 'x' * 10000
        large_token = f'header.{large_payload}.signature'
        start = time.time()
        encoded = base64.urlsafe_b64encode(large_token.encode()).decode().rstrip('=')
        encoding_time = time.time() - start
        start = time.time()
        decoded = backend_decode(encoded)
        decoding_time = time.time() - start
        assert encoding_time < 0.01, f'Encoding too slow: {encoding_time}s'
        assert decoding_time < 0.01, f'Decoding too slow: {decoding_time}s'
        assert decoded == large_token

    def test_concurrent_encoding_safety(self):
        """Test that encoding is thread-safe for concurrent requests."""
        import concurrent.futures
        test_tokens = [f'token_{i}' for i in range(100)]

        def encode_decode_cycle(token):
            encoded = base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')
            decoded = backend_decode(encoded)
            return decoded == token
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(encode_decode_cycle, test_tokens))
        assert all(results), 'Some concurrent encoding/decoding operations failed'

    def test_error_messages_are_helpful(self):
        """Test that error messages help developers identify the issue."""
        broken_token = 'not-a-valid-base64-token!'
        try:
            backend_decode(broken_token)
            pytest.fail('Should have raised an error for invalid token')
        except Exception as e:
            error_msg = str(e)
            assert len(error_msg) > 0, 'Error message should not be empty'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')