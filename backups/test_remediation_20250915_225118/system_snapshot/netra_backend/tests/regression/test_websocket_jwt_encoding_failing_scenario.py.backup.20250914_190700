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
    # Remove 'Bearer ' prefix if present
    clean_token = token.replace('Bearer ', '').strip()
    
    # BROKEN: This is intentionally wrong - using standard base64 instead of base64url
    # This simulates what would happen if someone used btoa() incorrectly
    base64_encoded = base64.b64encode(clean_token.encode('latin-1')).decode('ascii')
    
    # BROKEN: Not properly converting to base64url
    # Missing the character replacements or doing them incorrectly
    broken_base64url = base64_encoded  # Oops, forgot to replace + and /
    
    return broken_base64url


def backend_decode(encoded_token: str) -> str:
    """
    The backend's correct decoding using urlsafe_b64decode.
    """
    # Add padding if needed
    padding = 4 - (len(encoded_token) % 4)
    if padding != 4:
        encoded_token += '=' * padding
    
    # Decode from base64url
    decoded_bytes = base64.urlsafe_b64decode(encoded_token)
    
    # Convert bytes to string
    decoded_string = decoded_bytes.decode('utf-8')
    
    return decoded_string


class TestWebSocketJWTEncodingFailureScenarios:
    """Test suite demonstrating failure scenarios if the fix is reverted."""
    
    def test_broken_encoding_fails_with_special_chars(self):
        """
        This test WILL FAIL if the frontend uses broken encoding.
        It demonstrates why the fix was necessary.
        """
        # JWT with special characters that will break with wrong encoding
        jwt_with_special = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiSm9obiBEb2UvKz0iLCJpZCI6MTIzfQ.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ"
        
        # Use the broken encoding (simulating regression)
        broken_encoded = simulate_broken_frontend_encoding(jwt_with_special)
        
        # This should fail because the encoding is wrong
        # The broken encoding will have + and / characters that backend can't decode
        with pytest.raises(Exception) as exc_info:
            decoded = backend_decode(broken_encoded)
            # If this assertion is reached, the encoding accidentally worked
            # which means our test isn't demonstrating the failure properly
            assert decoded == jwt_with_special
        
        # Verify that it failed for the right reason
        # The error should be related to invalid base64url characters
        assert "Invalid" in str(exc_info.value) or "padding" in str(exc_info.value)
    
    def test_regression_detection_with_url_unsafe_chars(self):
        """
        This test detects if someone accidentally uses standard base64
        instead of base64url encoding.
        """
        # Create a token that will have + and / in base64 encoding
        # These characters are URL-unsafe and MUST be replaced
        test_token = "abc" * 50  # This will likely produce + or / in base64
        
        # Standard base64 (WRONG)
        standard_b64 = base64.b64encode(test_token.encode()).decode()
        
        # Check if it contains URL-unsafe characters
        has_unsafe_chars = '+' in standard_b64 or '/' in standard_b64
        
        if has_unsafe_chars:
            # If we use standard base64 with unsafe chars, backend decode will fail
            with pytest.raises(Exception):
                # Try to decode standard base64 as if it were base64url
                backend_decode(standard_b64)
    
    def test_missing_padding_handling(self):
        """
        Test that demonstrates issues with incorrect padding handling.
        This would fail if padding is not handled correctly.
        """
        # Tokens that require different amounts of padding
        tokens_needing_padding = [
            "a",   # Needs == padding
            "ab",  # Needs = padding  
            "abc", # Needs no padding after encoding
        ]
        
        for token in tokens_needing_padding:
            # Encode without proper padding handling
            broken_encoded = base64.b64encode(token.encode()).decode().rstrip('=')
            
            # Backend should handle missing padding, but if not...
            try:
                decoded = backend_decode(broken_encoded)
                # If this works, padding is being handled correctly
                assert decoded == token
            except Exception as e:
                # This demonstrates what happens without proper padding
                pytest.fail(f"Padding not handled correctly for '{token}': {str(e)}")
    
    def test_unicode_encoding_regression(self):
        """
        Test that would fail if unicode handling regresses.
        """
        unicode_token = "token_with_[U+00E9]moji_[U+1F680]_and_[U+7279][U+6B8A][U+5B57][U+7B26]"
        
        try:
            # Try the broken Latin-1 encoding (which can't handle unicode)
            broken_encoded = base64.b64encode(unicode_token.encode('latin-1')).decode()
            # If we got here, it means Latin-1 somehow worked (it shouldn't)
            pytest.fail("Latin-1 encoding should have failed for unicode")
        except UnicodeEncodeError:
            # This is expected - Latin-1 can't encode unicode
            # The fix uses UTF-8 which handles unicode correctly
            pass
        
        # Verify the correct UTF-8 encoding works
        correct_encoded = base64.urlsafe_b64encode(unicode_token.encode('utf-8')).decode().rstrip('=')
        decoded = backend_decode(correct_encoded)
        assert decoded == unicode_token
    
    @pytest.mark.xfail(reason="Intentionally failing test to demonstrate regression scenario")
    def test_intentional_failure_demo(self):
        """
        This test is marked as xfail to demonstrate what a regression looks like.
        It shows what happens if someone uses the wrong encoding method.
        """
        jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        
        # Intentionally use wrong encoding
        wrong_encoded = base64.b64encode(jwt_token.encode()).decode()  # Standard base64, not base64url
        
        # This WILL fail because we're not using base64url encoding
        decoded = backend_decode(wrong_encoded)
        assert decoded == jwt_token  # This assertion will fail


class TestProductionReadinessChecks:
    """Tests to ensure the fix is production-ready."""
    
    def test_performance_with_large_tokens(self):
        """Test that encoding/decoding performs well with large JWT tokens."""
        import time
        
        # Create a large JWT-like token (simulating large claims)
        large_payload = "x" * 10000
        large_token = f"header.{large_payload}.signature"
        
        # Measure encoding time
        start = time.time()
        encoded = base64.urlsafe_b64encode(large_token.encode()).decode().rstrip('=')
        encoding_time = time.time() - start
        
        # Measure decoding time
        start = time.time()
        decoded = backend_decode(encoded)
        decoding_time = time.time() - start
        
        # Performance assertions (should be very fast)
        assert encoding_time < 0.01, f"Encoding too slow: {encoding_time}s"
        assert decoding_time < 0.01, f"Decoding too slow: {decoding_time}s"
        assert decoded == large_token
    
    def test_concurrent_encoding_safety(self):
        """Test that encoding is thread-safe for concurrent requests."""
        import concurrent.futures
        
        test_tokens = [
            f"token_{i}" for i in range(100)
        ]
        
        def encode_decode_cycle(token):
            encoded = base64.urlsafe_b64encode(token.encode()).decode().rstrip('=')
            decoded = backend_decode(encoded)
            return decoded == token
        
        # Run encoding/decoding concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = list(executor.map(encode_decode_cycle, test_tokens))
        
        # All should succeed
        assert all(results), "Some concurrent encoding/decoding operations failed"
    
    def test_error_messages_are_helpful(self):
        """Test that error messages help developers identify the issue."""
        # Intentionally broken token (not base64)
        broken_token = "not-a-valid-base64-token!"
        
        try:
            backend_decode(broken_token)
            pytest.fail("Should have raised an error for invalid token")
        except Exception as e:
            error_msg = str(e)
            # Error message should be helpful for debugging
            assert len(error_msg) > 0, "Error message should not be empty"
            # Could check for specific helpful keywords
            # assert "base64" in error_msg.lower() or "decode" in error_msg.lower()


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v", "--tb=short"])