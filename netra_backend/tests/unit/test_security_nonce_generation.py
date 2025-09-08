"""
Test Security Nonce Generation Business Logic - Core Unit Tests

Business Value Justification (BVJ):
- Segment: All (Security affects all user tiers)
- Business Goal: Security compliance and XSS attack prevention
- Value Impact: Prevents malicious script injection attacks that could compromise user data
- Strategic Impact: CRITICAL - Security vulnerabilities could result in data breaches and loss of customer trust

This test suite validates the core business logic for Content Security Policy (CSP) 
nonce generation that protects users from cross-site scripting attacks.
"""

import pytest
import re
from test_framework.base import BaseTestCase
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.middleware.nonce_generator import NonceGenerator


class TestSecurityNonceGeneration(BaseTestCase):
    """Test nonce generation delivers secure CSP protection for business security."""
    
    def setup_method(self):
        """Setup test environment with isolated configuration."""
        super().setup_method()
        self.env = IsolatedEnvironment()
        
    def teardown_method(self):
        """Clean up test environment."""
        super().teardown_method()
        
    @pytest.mark.unit
    def test_nonce_generation_cryptographic_security(self):
        """Test that generated nonces are cryptographically secure and unpredictable."""
        # Generate multiple nonces to test randomness
        nonces = []
        for _ in range(100):
            nonce = NonceGenerator.generate_nonce()
            nonces.append(nonce)
            
            # Each nonce should be URL-safe base64 encoded
            assert re.match(r'^[A-Za-z0-9_-]+$', nonce), f"Nonce {nonce} contains invalid characters"
            
            # Should be reasonable length for security (16 bytes -> ~22 chars base64)
            assert len(nonce) >= 20, f"Nonce {nonce} too short for security"
            assert len(nonce) <= 30, f"Nonce {nonce} unnecessarily long"
        
        # All nonces should be unique (cryptographic randomness)
        unique_nonces = set(nonces)
        assert len(unique_nonces) == len(nonces), "Nonces should be unique - possible weak randomness"
        
    @pytest.mark.unit
    def test_nonce_generation_consistency(self):
        """Test that nonce generation consistently produces valid outputs."""
        for i in range(50):
            nonce = NonceGenerator.generate_nonce()
            
            # Should always be string
            assert isinstance(nonce, str), f"Iteration {i}: Nonce should be string"
            
            # Should not be empty
            assert len(nonce) > 0, f"Iteration {i}: Nonce should not be empty"
            
            # Should not contain spaces or special characters that break CSP
            assert ' ' not in nonce, f"Iteration {i}: Nonce should not contain spaces"
            assert '"' not in nonce, f"Iteration {i}: Nonce should not contain quotes"
            assert "'" not in nonce, f"Iteration {i}: Nonce should not contain single quotes"
            assert ';' not in nonce, f"Iteration {i}: Nonce should not contain semicolons"
            
    @pytest.mark.unit
    def test_csp_nonce_injection_protection(self):
        """Test that CSP nonce addition protects against script injection attacks."""
        # Test basic CSP policy
        original_csp = "default-src 'self'"
        nonce = NonceGenerator.generate_nonce()
        
        updated_csp = NonceGenerator.add_nonce_to_csp(original_csp, nonce)
        
        # Should add nonce to script-src and style-src
        expected_nonce_directive = f"'nonce-{nonce}'"
        assert expected_nonce_directive in updated_csp
        assert "script-src 'self'" in updated_csp or f"script-src {expected_nonce_directive}" in updated_csp
        assert "style-src 'self'" in updated_csp or f"style-src {expected_nonce_directive}" in updated_csp
        
        # Original policy should be preserved
        assert "default-src 'self'" in updated_csp
        
    @pytest.mark.unit
    def test_csp_directive_enhancement_business_logic(self):
        """Test that CSP directive enhancement maintains security while adding nonce support."""
        test_cases = [
            # Existing script-src should be enhanced
            {
                "input": "script-src 'self' https://trusted.com",
                "should_contain": ["script-src", "'self'", "https://trusted.com", "'nonce-"]
            },
            # No existing script-src should add new directive
            {
                "input": "default-src 'self'",
                "should_contain": ["default-src 'self'", "script-src 'self' 'nonce-", "style-src 'self' 'nonce-"]
            },
            # Complex CSP should be preserved
            {
                "input": "default-src 'none'; script-src 'self'; style-src 'unsafe-inline'",
                "should_contain": ["default-src 'none'", "script-src", "style-src", "'nonce-"]
            }
        ]
        
        for i, test_case in enumerate(test_cases):
            nonce = NonceGenerator.generate_nonce()
            result = NonceGenerator.add_nonce_to_csp(test_case["input"], nonce)
            
            for expected_content in test_case["should_contain"]:
                assert expected_content in result, \
                    f"Test case {i}: '{expected_content}' not found in result: {result}"
                    
            # Nonce should be properly formatted
            nonce_pattern = f"'nonce-{re.escape(nonce)}'"
            assert re.search(nonce_pattern, result), \
                f"Test case {i}: Properly formatted nonce not found in: {result}"
                
    @pytest.mark.unit
    def test_csp_directive_addition_security(self):
        """Test that CSP directive addition maintains security best practices."""
        nonce = NonceGenerator.generate_nonce()
        
        # Test with various CSP scenarios
        test_scenarios = [
            ("", "script-src 'self'"),  # Empty CSP
            ("default-src 'self'", "script-src 'self'"),  # Basic CSP
            ("script-src 'none'", "script-src 'none'"),  # Restrictive CSP
        ]
        
        for original_csp, expected_base in test_scenarios:
            result = NonceGenerator.add_nonce_to_csp(original_csp, nonce)
            
            # Should always include self as safe source
            if "script-src" in result:
                # Extract script-src directive
                script_src_match = re.search(r"script-src[^;]*", result)
                assert script_src_match, f"script-src directive malformed in: {result}"
                script_src_directive = script_src_match.group()
                
                # Should include nonce
                assert f"'nonce-{nonce}'" in script_src_directive
                
            # Should never allow unsafe-eval or unsafe-inline without explicit intent
            assert "'unsafe-eval'" not in result, "CSP should not introduce unsafe-eval"
            # Note: unsafe-inline might be present in original CSP, we don't add it
            
    @pytest.mark.unit  
    def test_nonce_format_validation_business_requirements(self):
        """Test that nonce format meets business security requirements."""
        nonce = NonceGenerator.generate_nonce()
        
        # Business requirement: Must be suitable for HTML attributes
        html_safe_pattern = r'^[A-Za-z0-9_-]+$'
        assert re.match(html_safe_pattern, nonce), \
            f"Nonce {nonce} not safe for HTML attributes"
            
        # Business requirement: Must not contain CSP breaking characters
        csp_breaking_chars = ['"', "'", ';', '(', ')', ' ', '\t', '\n', '\r']
        for char in csp_breaking_chars:
            assert char not in nonce, \
                f"Nonce {nonce} contains CSP-breaking character: {char}"
                
        # Business requirement: Should be base64url format (no padding)
        assert not nonce.endswith('='), \
            f"Nonce {nonce} should not have base64 padding for URL safety"
            
    @pytest.mark.unit
    def test_multiple_directive_enhancement(self):
        """Test that both script-src and style-src directives are enhanced for complete protection."""
        nonce = NonceGenerator.generate_nonce()
        
        # Test with existing script-src but no style-src
        csp_with_script = "script-src 'self' https://cdn.example.com"
        result = NonceGenerator.add_nonce_to_csp(csp_with_script, nonce)
        
        # Both directives should be present
        assert "script-src" in result
        assert "style-src" in result
        
        # Both should have the nonce
        nonce_directive = f"'nonce-{nonce}'"
        
        # Count occurrences - should appear at least twice (script-src and style-src)
        nonce_count = result.count(nonce_directive)
        assert nonce_count >= 2, \
            f"Nonce should appear in both script-src and style-src: {result}"
            
        # Original script-src content should be preserved
        assert "https://cdn.example.com" in result
        assert "'self'" in result
        
    @pytest.mark.unit
    def test_csp_malformation_prevention(self):
        """Test that CSP processing prevents malformed CSP policies that could break security."""
        nonce = NonceGenerator.generate_nonce()
        
        # Test edge cases that could break CSP
        edge_cases = [
            "script-src",  # Incomplete directive
            "script-src ;",  # Malformed with semicolon
            "default-src 'self'; script-src",  # Incomplete in complex CSP
        ]
        
        for edge_case in edge_cases:
            result = NonceGenerator.add_nonce_to_csp(edge_case, nonce)
            
            # Result should be valid CSP (no hanging directives)
            assert not re.search(r';\s*;', result), \
                f"Double semicolons found in: {result}"
            assert not result.endswith(';'), \
                f"CSP should not end with semicolon: {result}"
            assert not re.search(r'\s+;', result), \
                f"Spaces before semicolons found in: {result}"
                
            # Should contain valid nonce
            assert f"'nonce-{nonce}'" in result
            
    @pytest.mark.unit
    def test_nonce_entropy_validation(self):
        """Test that generated nonces have sufficient entropy for security."""
        # Generate many nonces to test entropy
        nonces = [NonceGenerator.generate_nonce() for _ in range(1000)]
        
        # Test character distribution
        all_chars = ''.join(nonces)
        unique_chars = set(all_chars)
        
        # Should use most of the base64url character set
        expected_chars = set('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_')
        chars_used_ratio = len(unique_chars) / len(expected_chars)
        
        assert chars_used_ratio > 0.8, \
            f"Character distribution too low: {chars_used_ratio:.2f} - possible weak randomness"
            
        # Test that we're not seeing obvious patterns
        for i in range(len(nonces) - 1):
            current_nonce = nonces[i] 
            next_nonce = nonces[i + 1]
            
            # Nonces should not share long common prefixes (>4 chars)
            common_prefix_len = 0
            for j in range(min(len(current_nonce), len(next_nonce))):
                if current_nonce[j] == next_nonce[j]:
                    common_prefix_len += 1
                else:
                    break
                    
            assert common_prefix_len <= 4, \
                f"Consecutive nonces share too long prefix: {current_nonce[:common_prefix_len]}"