"""
Test Authentication Security Algorithms Business Logic

Business Value Justification (BVJ):
- Segment: All customer segments (security foundation)
- Business Goal: Prevent unauthorized access and protect customer data
- Value Impact: Security breaches cause customer churn and regulatory issues
- Strategic Impact: Enterprise security compliance enables high-value customers

CRITICAL REQUIREMENTS:
- Tests pure business logic for authentication security
- Validates token security and session management algorithms
- No external dependencies or infrastructure needed
- Ensures cryptographic security implementations
"""

import pytest
import jwt
import hashlib
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from unittest.mock import Mock, patch
from dataclasses import dataclass

from netra_backend.app.services.auth.token_security_validator import (
    TokenSecurityValidator,
    TokenValidationResult,
    SecurityThreat,
    TokenSecurityLevel
)
from netra_backend.app.services.auth.session_security_manager import (
    SessionSecurityManager,
    SessionSecurityResult,
    SessionAnomaly,
    ThreatLevel
)
from netra_backend.app.services.auth.cryptographic_security import (
    CryptographicSecurity,
    PasswordSecurityAnalyzer,
    EncryptionResult
)


class TestAuthenticationSecurityAlgorithmsBusinessLogic:
    """Test authentication security algorithms business logic"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.token_validator = TokenSecurityValidator()
        self.session_manager = SessionSecurityManager()
        self.crypto_security = CryptographicSecurity()
        self.password_analyzer = PasswordSecurityAnalyzer()
        
        # Test secrets and keys (for testing only)
        self.test_secret_strong = secrets.token_urlsafe(32)
        self.test_secret_weak = "weak_secret_123"
        self.test_timestamp = datetime.now(timezone.utc)
    
    def test_jwt_token_security_validation_comprehensive(self):
        """Test comprehensive JWT token security validation"""
        # Test secure JWT token
        secure_payload = {
            "user_id": "user_123",
            "email": "user@example.com",
            "role": "user",
            "iat": int(time.time()),
            "exp": int(time.time()) + 3600,  # 1 hour expiration
            "iss": "netra-auth-service",
            "aud": "netra-backend"
        }
        
        secure_token = jwt.encode(
            secure_payload,
            self.test_secret_strong,
            algorithm="HS256"
        )
        
        validation_result = self.token_validator.validate_jwt_security(
            secure_token, 
            self.test_secret_strong,
            expected_audience="netra-backend",
            expected_issuer="netra-auth-service"
        )
        
        assert validation_result.is_secure is True
        assert validation_result.security_level == TokenSecurityLevel.HIGH
        assert len(validation_result.security_warnings) == 0
        
        # Test token with security vulnerabilities
        vulnerable_payloads = [
            # No expiration
            {
                "user_id": "user_123",
                "iat": int(time.time()),
                # Missing exp
            },
            
            # Expired token
            {
                "user_id": "user_123", 
                "iat": int(time.time()) - 7200,  # 2 hours ago
                "exp": int(time.time()) - 3600   # Expired 1 hour ago
            },
            
            # Excessive permissions
            {
                "user_id": "user_123",
                "role": "admin",
                "permissions": ["read", "write", "delete", "admin", "super_admin"],
                "exp": int(time.time()) + 3600
            },
            
            # Long expiration (security risk)
            {
                "user_id": "user_123",
                "exp": int(time.time()) + (86400 * 365)  # 1 year expiration
            }
        ]
        
        for i, vuln_payload in enumerate(vulnerable_payloads):
            vuln_token = jwt.encode(vuln_payload, self.test_secret_strong, algorithm="HS256")
            
            vuln_result = self.token_validator.validate_jwt_security(
                vuln_token,
                self.test_secret_strong
            )
            
            assert vuln_result.is_secure is False, f"Failed to detect vulnerability in payload {i}"
            assert len(vuln_result.security_warnings) > 0
            
            # Check for specific vulnerabilities
            warning_types = [w.warning_type for w in vuln_result.security_warnings]
            
            if "exp" not in vuln_payload:
                assert "missing_expiration" in warning_types
            elif vuln_payload.get("exp", 0) < time.time():
                assert "token_expired" in warning_types
            elif vuln_payload.get("exp", 0) - time.time() > 86400 * 30:  # 30 days
                assert "excessive_expiration" in warning_types
            
            if len(vuln_payload.get("permissions", [])) > 3:
                assert "excessive_permissions" in warning_types
    
    def test_token_algorithm_security_validation(self):
        """Test validation of JWT algorithm security"""
        payload = {
            "user_id": "user_123",
            "exp": int(time.time()) + 3600
        }
        
        # Test insecure algorithms
        insecure_algorithms = ["none", "HS256"]  # 'none' is definitely insecure
        secure_algorithms = ["RS256", "ES256", "PS256"]
        
        # Test 'none' algorithm (critical vulnerability)
        none_token = jwt.encode(payload, "", algorithm="none")
        none_result = self.token_validator.validate_token_algorithm_security(none_token)
        
        assert none_result.is_secure is False
        assert none_result.security_level == TokenSecurityLevel.CRITICAL_VULNERABILITY
        assert "insecure_algorithm" in [w.warning_type for w in none_result.security_warnings]
        
        # Test weak secret with HS256
        weak_secret = "123"
        weak_token = jwt.encode(payload, weak_secret, algorithm="HS256")
        weak_result = self.token_validator.validate_token_algorithm_security(weak_token)
        
        # Should detect weak secret vulnerability
        secret_strength_result = self.token_validator.validate_secret_strength(weak_secret)
        assert secret_strength_result.is_strong is False
        assert secret_strength_result.entropy_bits < 128  # Minimum recommended entropy
        
        # Test strong secret with HS256
        strong_secret = secrets.token_urlsafe(32)  # 256-bit entropy
        strong_token = jwt.encode(payload, strong_secret, algorithm="HS256")
        strong_result = self.token_validator.validate_secret_strength(strong_secret)
        
        assert strong_result.is_strong is True
        assert strong_result.entropy_bits >= 128
        assert strong_result.security_level in [TokenSecurityLevel.HIGH, TokenSecurityLevel.MEDIUM]
    
    def test_session_hijacking_detection_algorithm(self):
        """Test session hijacking detection algorithms"""
        # Simulate normal session behavior
        normal_session = {
            "session_id": "session_123",
            "user_id": "user_456", 
            "ip_address": "192.168.1.100",
            "user_agent": "Mozilla/5.0 (Chrome/91.0)",
            "created_at": self.test_timestamp - timedelta(minutes=30),
            "last_activity": self.test_timestamp - timedelta(minutes=1),
            "activity_log": [
                {"timestamp": self.test_timestamp - timedelta(minutes=30), "action": "login", "ip": "192.168.1.100"},
                {"timestamp": self.test_timestamp - timedelta(minutes=25), "action": "api_call", "ip": "192.168.1.100"},
                {"timestamp": self.test_timestamp - timedelta(minutes=20), "action": "api_call", "ip": "192.168.1.100"},
                {"timestamp": self.test_timestamp - timedelta(minutes=1), "action": "api_call", "ip": "192.168.1.100"},
            ]
        }
        
        normal_result = self.session_manager.detect_session_hijacking(normal_session)
        
        assert normal_result.is_suspicious is False
        assert normal_result.threat_level == ThreatLevel.LOW
        assert len(normal_result.detected_anomalies) == 0
        
        # Simulate suspicious session behaviors
        suspicious_sessions = [
            # IP address change mid-session
            {
                **normal_session,
                "activity_log": normal_session["activity_log"] + [
                    {"timestamp": self.test_timestamp, "action": "api_call", "ip": "203.0.113.1"}  # Different IP
                ]
            },
            
            # User agent change
            {
                **normal_session,
                "user_agent": "curl/7.68.0",  # Completely different user agent
            },
            
            # Geographically impossible travel
            {
                **normal_session,
                "activity_log": [
                    {"timestamp": self.test_timestamp - timedelta(minutes=30), "action": "login", "ip": "192.168.1.100", "location": "New York"},
                    {"timestamp": self.test_timestamp - timedelta(minutes=5), "action": "api_call", "ip": "203.0.113.1", "location": "Tokyo"}  # Impossible travel time
                ]
            },
            
            # Concurrent sessions from different locations
            {
                **normal_session,
                "concurrent_sessions": [
                    {"ip": "192.168.1.100", "location": "New York", "last_activity": self.test_timestamp},
                    {"ip": "203.0.113.1", "location": "London", "last_activity": self.test_timestamp - timedelta(minutes=1)}
                ]
            }
        ]
        
        for i, suspicious_session in enumerate(suspicious_sessions):
            suspicious_result = self.session_manager.detect_session_hijacking(suspicious_session)
            
            assert suspicious_result.is_suspicious is True, f"Failed to detect suspicious session {i}"
            assert suspicious_result.threat_level in [ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
            assert len(suspicious_result.detected_anomalies) > 0
            
            # Check for specific anomaly types
            anomaly_types = [a.anomaly_type for a in suspicious_result.detected_anomalies]
            
            if i == 0:  # IP change
                assert "ip_address_change" in anomaly_types
            elif i == 1:  # User agent change
                assert "user_agent_change" in anomaly_types
            elif i == 2:  # Impossible travel
                assert "impossible_travel" in anomaly_types
            elif i == 3:  # Concurrent sessions
                assert "concurrent_sessions" in anomaly_types
    
    def test_password_security_analysis_comprehensive(self):
        """Test comprehensive password security analysis"""
        # Test weak passwords
        weak_passwords = [
            "123456",
            "password",
            "admin",
            "qwerty",
            "letmein",
            "password123",
            "admin123",
            "user@domain.com",  # Email as password
            "Password1",  # Common pattern
            "abcdefgh"  # Dictionary word
        ]
        
        for weak_password in weak_passwords:
            analysis_result = self.password_analyzer.analyze_password_security(weak_password)
            
            assert analysis_result.is_secure is False, f"Failed to identify weak password: {weak_password}"
            assert analysis_result.strength_score < 0.5  # Below 50% strength
            assert len(analysis_result.vulnerabilities) > 0
            
            # Check for specific vulnerabilities
            vulnerability_types = [v.vulnerability_type for v in analysis_result.vulnerabilities]
            
            if len(weak_password) < 8:
                assert "too_short" in vulnerability_types
            
            if weak_password.lower() in ["password", "admin", "qwerty", "letmein"]:
                assert "common_password" in vulnerability_types
            
            if weak_password.isdigit():
                assert "only_numbers" in vulnerability_types
            
            if weak_password.isalpha():
                assert "only_letters" in vulnerability_types
        
        # Test strong passwords
        strong_passwords = [
            "Tr0ub4dor&3",  # Mixed case, numbers, symbols
            "correct horse battery staple 2024!",  # Passphrase with complexity
            "MyV3ry$tr0ngP@ssw0rd2024",  # Long with all character types
            "8B#mK9$nL2@qR7&vF3!pT6",  # Random strong password
        ]
        
        for strong_password in strong_passwords:
            analysis_result = self.password_analyzer.analyze_password_security(strong_password)
            
            assert analysis_result.is_secure is True, f"Strong password incorrectly flagged as weak: {strong_password}"
            assert analysis_result.strength_score >= 0.7  # Above 70% strength
            assert len(analysis_result.vulnerabilities) == 0
            
            # Validate strength components
            assert analysis_result.entropy_bits >= 50  # Minimum entropy for strong passwords
            assert analysis_result.character_diversity_score > 0.5
            assert analysis_result.length_score >= 0.7
    
    def test_brute_force_attack_detection(self):
        """Test brute force attack detection algorithms"""
        # Normal login attempts
        normal_attempts = [
            {
                "timestamp": self.test_timestamp - timedelta(minutes=30),
                "ip_address": "192.168.1.100",
                "username": "user@example.com",
                "success": True
            }
        ]
        
        normal_result = self.session_manager.detect_brute_force_attack(normal_attempts)
        
        assert normal_result.is_brute_force_attack is False
        assert normal_result.threat_level == ThreatLevel.LOW
        
        # Brute force attack patterns
        brute_force_attempts = []
        attack_ip = "203.0.113.1"
        
        # Generate rapid failed login attempts
        for i in range(20):  # 20 failed attempts
            brute_force_attempts.append({
                "timestamp": self.test_timestamp - timedelta(minutes=10) + timedelta(seconds=i*10),
                "ip_address": attack_ip,
                "username": "admin",
                "success": False,
                "password_attempt": f"password{i:03d}"
            })
        
        brute_force_result = self.session_manager.detect_brute_force_attack(brute_force_attempts)
        
        assert brute_force_result.is_brute_force_attack is True
        assert brute_force_result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        assert brute_force_result.failed_attempts >= 20
        assert brute_force_result.attack_ip == attack_ip
        
        # Should recommend security measures
        assert len(brute_force_result.recommended_actions) > 0
        action_types = [a.action_type for a in brute_force_result.recommended_actions]
        expected_actions = ["ip_block", "account_lockout", "rate_limiting", "alert_admin"]
        assert any(action in action_types for action in expected_actions)
        
        # Test distributed brute force (multiple IPs)
        distributed_attempts = []
        attack_ips = [f"203.0.113.{i}" for i in range(1, 11)]  # 10 different IPs
        
        for ip in attack_ips:
            for j in range(3):  # 3 attempts per IP
                distributed_attempts.append({
                    "timestamp": self.test_timestamp - timedelta(minutes=5) + timedelta(seconds=j*2),
                    "ip_address": ip,
                    "username": "admin",
                    "success": False
                })
        
        distributed_result = self.session_manager.detect_distributed_brute_force(distributed_attempts)
        
        assert distributed_result.is_distributed_attack is True
        assert distributed_result.unique_ips >= 10
        assert distributed_result.total_attempts >= 30
        assert distributed_result.coordination_score >= 0.7  # High coordination indicates attack
    
    def test_multi_factor_authentication_security_validation(self):
        """Test MFA security validation algorithms"""
        # Test TOTP (Time-based One-Time Password) validation
        totp_secret = secrets.token_urlsafe(32)
        
        # Generate valid TOTP code
        import pyotp
        totp_generator = pyotp.TOTP(totp_secret)
        valid_code = totp_generator.now()
        
        totp_result = self.session_manager.validate_totp_security(
            provided_code=valid_code,
            secret=totp_secret,
            tolerance_window=1  # Allow 1 time step tolerance
        )
        
        assert totp_result.is_valid is True
        assert totp_result.security_level == TokenSecurityLevel.HIGH
        assert totp_result.time_drift_seconds < 60  # Should be within acceptable drift
        
        # Test invalid TOTP codes
        invalid_codes = [
            "000000",  # Obviously invalid
            "123456",  # Common weak code
            str(int(valid_code) + 1).zfill(6),  # Off by one
            totp_generator.at(time.time() - 300)  # Code from 5 minutes ago
        ]
        
        for invalid_code in invalid_codes:
            invalid_result = self.session_manager.validate_totp_security(
                provided_code=invalid_code,
                secret=totp_secret
            )
            
            assert invalid_result.is_valid is False
            assert len(invalid_result.security_warnings) > 0
        
        # Test backup codes validation
        backup_codes = self.session_manager.generate_backup_codes(count=10)
        
        assert len(backup_codes) == 10
        assert all(len(code) >= 8 for code in backup_codes)  # Minimum length
        assert len(set(backup_codes)) == 10  # All unique
        
        # Test backup code usage
        test_backup_code = backup_codes[0]
        backup_result = self.session_manager.validate_backup_code(
            provided_code=test_backup_code,
            valid_codes=backup_codes
        )
        
        assert backup_result.is_valid is True
        assert backup_result.remaining_codes == 9  # One code used
        assert test_backup_code not in backup_result.remaining_valid_codes  # Should be consumed
    
    def test_encryption_security_validation(self):
        """Test encryption security validation"""
        # Test data encryption with strong algorithm
        sensitive_data = "user_password_hash_and_personal_data"
        
        encryption_result = self.crypto_security.encrypt_sensitive_data(
            data=sensitive_data,
            algorithm="AES-256-GCM"
        )
        
        assert encryption_result.is_encrypted is True
        assert encryption_result.algorithm == "AES-256-GCM"
        assert encryption_result.encrypted_data != sensitive_data  # Should be encrypted
        assert len(encryption_result.encryption_key) >= 32  # 256-bit key
        assert len(encryption_result.iv) >= 12  # GCM requires minimum 12-byte IV
        
        # Test decryption
        decryption_result = self.crypto_security.decrypt_sensitive_data(
            encrypted_data=encryption_result.encrypted_data,
            key=encryption_result.encryption_key,
            iv=encryption_result.iv,
            algorithm="AES-256-GCM",
            auth_tag=encryption_result.auth_tag
        )
        
        assert decryption_result.is_successful is True
        assert decryption_result.decrypted_data == sensitive_data
        assert decryption_result.integrity_verified is True  # GCM provides authentication
        
        # Test weak encryption detection
        weak_algorithms = ["DES", "3DES", "AES-128-ECB", "RC4"]
        
        for weak_algo in weak_algorithms:
            weak_validation = self.crypto_security.validate_encryption_algorithm_security(weak_algo)
            
            assert weak_validation.is_secure is False
            assert weak_validation.security_level in [TokenSecurityLevel.LOW, TokenSecurityLevel.CRITICAL_VULNERABILITY]
            assert len(weak_validation.security_warnings) > 0
            
            warning_types = [w.warning_type for w in weak_validation.security_warnings]
            expected_warnings = ["weak_algorithm", "deprecated_algorithm", "no_authentication"]
            assert any(warning in warning_types for warning in expected_warnings)
        
        # Test strong algorithms
        strong_algorithms = ["AES-256-GCM", "AES-256-CCM", "ChaCha20-Poly1305"]
        
        for strong_algo in strong_algorithms:
            strong_validation = self.crypto_security.validate_encryption_algorithm_security(strong_algo)
            
            assert strong_validation.is_secure is True
            assert strong_validation.security_level in [TokenSecurityLevel.HIGH, TokenSecurityLevel.MEDIUM]
            assert len(strong_validation.security_warnings) == 0
    
    def test_privilege_escalation_detection(self):
        """Test privilege escalation detection algorithms"""
        # Normal privilege usage
        normal_access_log = [
            {
                "timestamp": self.test_timestamp - timedelta(minutes=30),
                "user_id": "user_123",
                "action": "read_profile",
                "resource": "user_data",
                "required_role": "user"
            },
            {
                "timestamp": self.test_timestamp - timedelta(minutes=25), 
                "user_id": "user_123",
                "action": "update_profile",
                "resource": "user_data", 
                "required_role": "user"
            }
        ]
        
        normal_result = self.session_manager.detect_privilege_escalation(normal_access_log)
        
        assert normal_result.is_suspicious is False
        assert normal_result.threat_level == ThreatLevel.LOW
        
        # Suspicious privilege escalation patterns
        escalation_attempts = [
            # Sudden admin access
            {
                "timestamp": self.test_timestamp,
                "user_id": "user_123", 
                "action": "delete_all_users",
                "resource": "admin_panel",
                "required_role": "admin",
                "user_role": "user"  # Role mismatch
            },
            
            # Multiple failed privilege attempts
            {
                "timestamp": self.test_timestamp - timedelta(minutes=1),
                "user_id": "user_123",
                "action": "access_admin_settings", 
                "resource": "admin_panel",
                "success": False,
                "error": "insufficient_privileges"
            },
            {
                "timestamp": self.test_timestamp,
                "user_id": "user_123",
                "action": "modify_user_roles",
                "resource": "admin_panel", 
                "success": False,
                "error": "insufficient_privileges"
            }
        ]
        
        escalation_log = normal_access_log + escalation_attempts
        escalation_result = self.session_manager.detect_privilege_escalation(escalation_log)
        
        assert escalation_result.is_suspicious is True
        assert escalation_result.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        assert escalation_result.escalation_attempts > 0
        
        # Should identify specific escalation patterns
        pattern_types = [p.pattern_type for p in escalation_result.detected_patterns]
        expected_patterns = ["role_mismatch", "repeated_failures", "privilege_jump"]
        assert any(pattern in pattern_types for pattern in expected_patterns)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])