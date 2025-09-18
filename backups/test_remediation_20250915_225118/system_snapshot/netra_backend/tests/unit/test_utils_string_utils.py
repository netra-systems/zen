"""
Unit Test for String Utilities Module

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Security and Data Integrity
- Value Impact: Prevents XSS attacks, SQL injection, and path traversal vulnerabilities
- Strategic Impact: Protects $500K+ ARR by securing user data and preventing security breaches

CRITICAL: NO MOCKS except for external dependencies. Tests use real business logic.
Tests essential security functions that protect Golden Path user interactions.
"""

import pytest
from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.utils.string_utils import StringUtils


class StringUtilsTests(SSotBaseTestCase):
    """Test suite for StringUtils following SSOT patterns."""
    
    def setup_method(self, method):
        """Setup using SSOT test infrastructure."""
        super().setup_method(method)
        self.string_utils = StringUtils()
        self.record_metric("test_category", "string_utils_security")
    
    def test_sanitize_html_removes_script_tags(self):
        """
        Test HTML sanitization removes dangerous script tags.
        
        BVJ: Prevents XSS attacks that could compromise Golden Path user sessions
        """
        # Test dangerous script tag removal
        dangerous_html = '<script>alert("xss")</script><p>Safe content</p>'
        result = self.string_utils.sanitize_html(dangerous_html)
        
        assert '<script>' not in result
        assert 'alert("xss")' not in result
        assert 'Safe content' in result
        self.record_metric("xss_prevention_test", "passed")
    
    def test_sanitize_html_removes_event_handlers(self):
        """
        Test HTML sanitization removes event handlers.
        
        BVJ: Blocks event-based XSS attacks protecting user chat interactions
        """
        dangerous_html = '<div onclick="malicious()">Content</div>'
        result = self.string_utils.sanitize_html(dangerous_html)
        
        assert 'onclick' not in result
        assert 'malicious()' not in result
        self.record_metric("event_handler_removal", "passed")
    
    def test_escape_sql_prevents_injection(self):
        """
        Test SQL escaping prevents injection attacks.
        
        BVJ: Protects database integrity for business-critical agent and user data
        """
        malicious_input = "'; DROP TABLE users; --"
        result = self.string_utils.escape_sql(malicious_input)
        
        assert "''" in result  # Single quotes escaped
        assert "\\--" in result  # Comment markers escaped
        assert "DROP TABLE" in result  # Content preserved but safe
        self.record_metric("sql_injection_prevention", "passed")
    
    def test_sanitize_path_prevents_traversal(self):
        """
        Test path sanitization prevents directory traversal.
        
        BVJ: Secures file operations in Golden Path document processing
        """
        malicious_path = "../../../etc/passwd"
        result = self.string_utils.sanitize_path(malicious_path)
        
        assert ".." not in result
        assert result == "etc/passwd"
        self.record_metric("path_traversal_prevention", "passed")
    
    def test_email_validation_accuracy(self):
        """
        Test email validation for user authentication.
        
        BVJ: Ensures valid user emails for Golden Path authentication flow
        """
        # Valid emails
        assert self.string_utils.is_valid_email("user@example.com")
        assert self.string_utils.is_valid_email("test.user+123@domain.co.uk")
        
        # Invalid emails
        assert not self.string_utils.is_valid_email("invalid.email")
        assert not self.string_utils.is_valid_email("@example.com")
        assert not self.string_utils.is_valid_email("user@")
        
        self.record_metric("email_validation_accuracy", "passed")
    
    def test_url_validation_security(self):
        """
        Test URL validation blocks dangerous protocols.
        
        BVJ: Prevents malicious redirects in Golden Path user flows
        """
        # Valid URLs
        assert self.string_utils.is_valid_url("https://example.com")
        assert self.string_utils.is_valid_url("http://localhost:3000")
        
        # Dangerous URLs
        assert not self.string_utils.is_valid_url("javascript:alert('xss')")
        assert not self.string_utils.is_valid_url("data:text/html,<script>alert('xss')</script>")
        assert not self.string_utils.is_valid_url("vbscript:malicious")
        
        self.record_metric("url_security_validation", "passed")