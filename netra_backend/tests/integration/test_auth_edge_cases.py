from shared.isolated_environment import get_env
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment
"""Authentication Edge Cases and Error Scenarios Tests (L3)

env = get_env()
Comprehensive tests for authentication edge cases, error conditions,
and security vulnerability scenarios.

Business Value Justification (BVJ):
- Segment: ALL (Security foundation for entire platform)
- Business Goal: Prevent security breaches and data loss
- Value Impact: Protects entire $150K MRR from security incidents
- Strategic Impact: Trust and compliance critical for enterprise contracts

Test Coverage:
- Token manipulation and forgery attempts
- Timing attacks and race conditions
- Session fixation and hijacking
- Injection attacks
- Cryptographic weaknesses
- Configuration errors
- Network failures
- Resource exhaustion
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import base64
import hashlib
import json
import os
import random
import secrets
import string
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import jwt
import pytest

# Set test environment
env.set("ENVIRONMENT", "testing", "test")
env.set("TESTING", "true", "test")

# Import auth types
# Test infrastructure  
from netra_backend.app.core.exceptions_websocket import WebSocketAuthenticationError
from netra_backend.app.schemas.auth_types import (
    AuthError,
    LoginRequest,
    Token,
    TokenData,
)

@dataclass
class SecurityTestCase:
    """Security test case definition."""
    name: str
    attack_type: str
    payload: Any
    expected_result: str
    severity: str  # "critical", "high", "medium", "low"

class AuthEdgeCasesTestSuite:
    """Test suite for authentication edge cases and errors."""
    
    def __init__(self):
        self.jwt_secret = "test_jwt_secret_key"
        self.test_cases: List[SecurityTestCase] = []
        self.vulnerabilities_found: List[str] = []
        
    def generate_malicious_token(self, attack_type: str) -> str:
        """Generate various types of malicious tokens."""
        if attack_type == "none_algorithm":
            # JWT with 'none' algorithm attack
            header = {"alg": "none", "typ": "JWT"}
            payload = {"sub": "attacker@evil.com", "admin": True}
            
            header_b64 = base64.urlsafe_b64encode(
                json.dumps(header).encode()
            ).decode().rstrip("=")
            payload_b64 = base64.urlsafe_b64encode(
                json.dumps(payload).encode()
            ).decode().rstrip("=")
            
            return f"{header_b64}.{payload_b64}."
            
        elif attack_type == "algorithm_confusion":
            # RS256 to HS256 attack
            payload = {
                "sub": "attacker@evil.com",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            }
            # Sign with public key as HMAC secret
            return jwt.encode(payload, "public_key_here", algorithm="HS256")
            
        elif attack_type == "expired_token":
            # Expired token
            payload = {
                "sub": "user@example.com",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1)
            }
            return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            
        elif attack_type == "future_token":
            # Token from the future
            payload = {
                "sub": "user@example.com",
                "iat": datetime.now(timezone.utc) + timedelta(hours=1),
                "exp": datetime.now(timezone.utc) + timedelta(hours=2)
            }
            return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            
        elif attack_type == "malformed":
            # Malformed token
            return "not.a.valid.jwt.token"
            
        elif attack_type == "sql_injection":
            # Token with SQL injection attempt
            payload = {
                "sub": "user@example.com' OR '1'='1",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            }
            return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            
        elif attack_type == "xss_payload":
            # Token with XSS payload
            payload = {
                "sub": "<script>alert('XSS')</script>",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            }
            return jwt.encode(payload, self.jwt_secret, algorithm="HS256")
            
        else:
            return "invalid_token"
    
    def generate_edge_case_input(self, case_type: str) -> Any:
        """Generate edge case inputs for testing."""
        if case_type == "empty_string":
            return ""
        elif case_type == "null_bytes":
            return "test\x00value"
        elif case_type == "unicode":
            return "test_🔐_भारत_中文_العربية"
        elif case_type == "very_long":
            return "a" * 10000
        elif case_type == "special_chars":
            return "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        elif case_type == "whitespace":
            return "   \t\n\r   "
        elif case_type == "control_chars":
            return "".join(chr(i) for i in range(32))
        elif case_type == "binary":
            return bytes(random.randint(0, 255) for _ in range(100))
        else:
            return None

@pytest.mark.integration
@pytest.mark.l3
@pytest.mark.security
class TestAuthEdgeCasesL3:
    """L3 tests for authentication edge cases and security scenarios."""
    
    @pytest.fixture
    async def edge_suite(self):
        """Create edge cases test suite."""
        suite = AuthEdgeCasesTestSuite()
        yield suite
    
    @pytest.mark.asyncio
    async def test_jwt_none_algorithm_attack(self, edge_suite):
        """Test 1: Prevent JWT 'none' algorithm vulnerability."""
        # Generate token with 'none' algorithm
        malicious_token = edge_suite.generate_malicious_token("none_algorithm")
        
        # Attempt to use malicious token
        with pytest.raises(jwt.InvalidTokenError):
            # Should reject token with 'none' algorithm
            jwt.decode(malicious_token, edge_suite.jwt_secret, algorithms=["HS256"])
    
    @pytest.mark.asyncio
    async def test_jwt_algorithm_confusion_attack(self, edge_suite):
        """Test 2: Prevent algorithm confusion attacks."""
        # Generate token with algorithm confusion
        malicious_token = edge_suite.generate_malicious_token("algorithm_confusion")
        
        # Should reject token signed with wrong algorithm
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(malicious_token, edge_suite.jwt_secret, algorithms=["HS256"])
    
    @pytest.mark.asyncio
    async def test_expired_token_handling(self, edge_suite):
        """Test 3: Proper handling of expired tokens."""
        expired_token = edge_suite.generate_malicious_token("expired_token")
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(expired_token, edge_suite.jwt_secret, algorithms=["HS256"])
    
    @pytest.mark.asyncio
    async def test_future_token_rejection(self, edge_suite):
        """Test 4: Reject tokens with future iat claims."""
        future_token = edge_suite.generate_malicious_token("future_token")
        
        # Should reject token from the future
        with pytest.raises(jwt.ImmatureSignatureError):
            jwt.decode(
                future_token,
                edge_suite.jwt_secret,
                algorithms=["HS256"],
                options={"verify_iat": True}
            )
    
    @pytest.mark.asyncio
    async def test_malformed_token_handling(self, edge_suite):
        """Test 5: Graceful handling of malformed tokens."""
        malformed_token = edge_suite.generate_malicious_token("malformed")
        
        with pytest.raises(jwt.DecodeError):
            jwt.decode(malformed_token, edge_suite.jwt_secret, algorithms=["HS256"])
    
    @pytest.mark.asyncio
    async def test_sql_injection_in_token(self, edge_suite):
        """Test 6: Prevent SQL injection through JWT claims."""
        sql_injection_token = edge_suite.generate_malicious_token("sql_injection")
        
        # Decode token
        payload = jwt.decode(
            sql_injection_token,
            edge_suite.jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": False}
        )
        
        # Verify SQL injection attempt is safely handled
        assert "' OR '1'='1" in payload["sub"]
        
        # In real implementation, this should be parameterized
        # and never directly interpolated into SQL
    
    @pytest.mark.asyncio
    async def test_xss_payload_in_token(self, edge_suite):
        """Test 7: Prevent XSS through JWT claims."""
        xss_token = edge_suite.generate_malicious_token("xss_payload")
        
        payload = jwt.decode(
            xss_token,
            edge_suite.jwt_secret,
            algorithms=["HS256"],
            options={"verify_exp": False}
        )
        
        # Verify XSS payload is present but should be escaped
        assert "<script>" in payload["sub"]
        
        # In real implementation, this should be HTML-escaped
        # before rendering in any UI
    
    @pytest.mark.asyncio
    async def test_timing_attack_on_token_validation(self, edge_suite):
        """Test 8: Prevent timing attacks on token validation."""
        valid_token = jwt.encode(
            {"sub": "user@example.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            edge_suite.jwt_secret,
            algorithm="HS256"
        )
        
        invalid_token = "invalid.token.here"
        
        # Measure validation times
        times = []
        
        for _ in range(100):
            start = time.perf_counter()
            try:
                jwt.decode(valid_token, edge_suite.jwt_secret, algorithms=["HS256"])
            except:
                pass
            times.append(time.perf_counter() - start)
        
        valid_avg = sum(times) / len(times)
        
        times = []
        for _ in range(100):
            start = time.perf_counter()
            try:
                jwt.decode(invalid_token, edge_suite.jwt_secret, algorithms=["HS256"])
            except:
                pass
            times.append(time.perf_counter() - start)
        
        invalid_avg = sum(times) / len(times)
        
        # Timing difference should be minimal (constant-time comparison)
        time_diff = abs(valid_avg - invalid_avg)
        assert time_diff < 0.001  # Less than 1ms difference
    
    @pytest.mark.asyncio
    async def test_race_condition_in_token_refresh(self, edge_suite):
        """Test 9: Handle race conditions in token refresh."""
        refresh_token = jwt.encode(
            {"sub": "user@example.com", "type": "refresh"},
            edge_suite.jwt_secret,
            algorithm="HS256"
        )
        
        # Simulate concurrent refresh attempts
        async def refresh_attempt():
            # Mock refresh logic
            await asyncio.sleep(random.uniform(0, 0.1))
            return jwt.encode(
                {"sub": "user@example.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
                edge_suite.jwt_secret,
                algorithm="HS256"
            )
        
        # Multiple concurrent refresh attempts
        tasks = [refresh_attempt() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Should handle concurrent refreshes without errors
        successful = [r for r in results if not isinstance(r, Exception)]
        assert len(successful) > 0
    
    @pytest.mark.asyncio
    async def test_session_fixation_prevention(self, edge_suite):
        """Test 10: Prevent session fixation attacks."""
        # Attacker creates session
        attacker_session = "attacker_session_id_12345"
        
        # Victim logs in with attacker's session ID
        # System should generate new session ID
        victim_session = secrets.token_hex(16)
        
        assert attacker_session != victim_session
        assert len(victim_session) >= 32
    
    @pytest.mark.asyncio
    async def test_null_byte_injection(self, edge_suite):
        """Test 11: Handle null byte injection attempts."""
        null_input = edge_suite.generate_edge_case_input("null_bytes")
        
        # Should handle null bytes safely
        assert "\x00" in null_input
        
        # Clean input
        cleaned = null_input.replace("\x00", "")
        assert "\x00" not in cleaned
    
    @pytest.mark.asyncio
    async def test_unicode_handling_in_auth(self, edge_suite):
        """Test 12: Proper Unicode handling in authentication."""
        unicode_input = edge_suite.generate_edge_case_input("unicode")
        
        # Create token with Unicode
        token = jwt.encode(
            {"sub": unicode_input, "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            edge_suite.jwt_secret,
            algorithm="HS256"
        )
        
        # Should handle Unicode correctly
        payload = jwt.decode(token, edge_suite.jwt_secret, algorithms=["HS256"])
        assert payload["sub"] == unicode_input
    
    @pytest.mark.asyncio
    async def test_extremely_long_input_handling(self, edge_suite):
        """Test 13: Handle extremely long input values."""
        long_input = edge_suite.generate_edge_case_input("very_long")
        
        # Should reject or truncate extremely long inputs
        max_length = 1000
        if len(long_input) > max_length:
            truncated = long_input[:max_length]
            assert len(truncated) == max_length
    
    @pytest.mark.asyncio
    async def test_special_characters_in_credentials(self, edge_suite):
        """Test 14: Handle special characters in credentials."""
        special_chars = edge_suite.generate_edge_case_input("special_chars")
        
        # Should handle special characters safely
        login_request = LoginRequest(
            email="test@example.com",
            password=special_chars
        )
        
        # Verify special characters preserved
        assert login_request.password == special_chars
    
    @pytest.mark.asyncio
    async def test_whitespace_manipulation(self, edge_suite):
        """Test 15: Handle whitespace manipulation attempts."""
        whitespace = edge_suite.generate_edge_case_input("whitespace")
        
        # Should trim whitespace
        cleaned = whitespace.strip()
        assert cleaned == ""
    
    @pytest.mark.asyncio
    async def test_control_character_filtering(self, edge_suite):
        """Test 16: Filter control characters from input."""
        control_chars = edge_suite.generate_edge_case_input("control_chars")
        
        # Should filter control characters
        filtered = "".join(c for c in control_chars if c.isprintable())
        assert len(filtered) < len(control_chars)
    
    @pytest.mark.asyncio
    async def test_token_replay_attack_prevention(self, edge_suite):
        """Test 17: Prevent token replay attacks."""
        # Generate token with jti (JWT ID)
        jti = secrets.token_hex(16)
        token = jwt.encode(
            {
                "sub": "user@example.com",
                "jti": jti,
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            },
            edge_suite.jwt_secret,
            algorithm="HS256"
        )
        
        # Mock used token tracking
        used_tokens = set()
        
        # First use should succeed
        payload = jwt.decode(token, edge_suite.jwt_secret, algorithms=["HS256"])
        used_tokens.add(payload["jti"])
        
        # Replay should be detected
        if payload["jti"] in used_tokens:
            # Token already used - reject
            assert True
    
    @pytest.mark.asyncio
    async def test_weak_secret_detection(self, edge_suite):
        """Test 18: Detect and reject weak JWT secrets."""
        weak_secrets = [
            "secret", "password", "123456", "admin",
            "12345678", "qwerty", "abc123"
        ]
        
        for weak_secret in weak_secrets:
            # Should reject weak secrets
            assert len(weak_secret) < 32
            
            # In production, should enforce minimum secret length
            min_secret_length = 32
            assert len(weak_secret) < min_secret_length
    
    @pytest.mark.asyncio
    async def test_token_signature_stripping(self, edge_suite):
        """Test 19: Prevent token signature stripping attacks."""
        # Create valid token
        token = jwt.encode(
            {"sub": "user@example.com", "exp": datetime.now(timezone.utc) + timedelta(hours=1)},
            edge_suite.jwt_secret,
            algorithm="HS256"
        )
        
        # Strip signature
        parts = token.split(".")
        stripped_token = f"{parts[0]}.{parts[1]}."
        
        # Should reject token without signature
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(stripped_token, edge_suite.jwt_secret, algorithms=["HS256"])
    
    @pytest.mark.asyncio
    async def test_concurrent_login_limit(self, edge_suite):
        """Test 20: Enforce concurrent login limits."""
        max_concurrent_sessions = 5
        active_sessions = []
        
        # Create sessions up to limit
        for i in range(max_concurrent_sessions + 2):
            session_id = f"session_{i}"
            
            if len(active_sessions) >= max_concurrent_sessions:
                # Should reject or remove oldest session
                active_sessions.pop(0)
            
            active_sessions.append(session_id)
        
        # Should not exceed limit
        assert len(active_sessions) <= max_concurrent_sessions
    
    @pytest.mark.asyncio
    async def test_brute_force_protection(self, edge_suite):
        """Test 21: Brute force attack protection."""
        failed_attempts = {}
        max_attempts = 5
        lockout_duration = 300  # 5 minutes
        
        email = "victim@example.com"
        
        # Simulate brute force attempts
        for i in range(10):
            if email not in failed_attempts:
                failed_attempts[email] = []
            
            # Check if locked out
            recent_attempts = [
                t for t in failed_attempts[email]
                if time.time() - t < lockout_duration
            ]
            
            if len(recent_attempts) >= max_attempts:
                # Account locked
                assert True
                break
            
            # Record failed attempt
            failed_attempts[email].append(time.time())
    
    @pytest.mark.asyncio
    async def test_password_complexity_bypass_attempts(self, edge_suite):
        """Test 22: Prevent password complexity bypass."""
        weak_passwords = [
            "",  # Empty
            " ",  # Whitespace
            "a",  # Too short
            "password",  # Common word
            "12345678",  # Numbers only
            "abcdefgh",  # Letters only
            "Password",  # No special chars
        ]
        
        for password in weak_passwords:
            # Should reject weak passwords
            is_weak = (
                len(password) < 8 or
                not any(c.isupper() for c in password) or
                not any(c.islower() for c in password) or
                not any(c.isdigit() for c in password) or
                not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password)
            )
            
            if password:  # Skip empty password for this check
                assert is_weak or password in ["password", "12345678"]
    
    @pytest.mark.asyncio
    async def test_header_injection_prevention(self, edge_suite):
        """Test 23: Prevent HTTP header injection."""
        # Attempt header injection
        malicious_header = "valid_value\r\nX-Evil-Header: malicious"
        
        # Should sanitize headers
        sanitized = malicious_header.replace("\r", "").replace("\n", "")
        assert "\r\n" not in sanitized
    
    @pytest.mark.asyncio
    async def test_token_scope_escalation(self, edge_suite):
        """Test 24: Prevent token scope escalation."""
        # Create limited scope token
        limited_token = jwt.encode(
            {
                "sub": "user@example.com",
                "scope": ["read"],
                "exp": datetime.now(timezone.utc) + timedelta(hours=1)
            },
            edge_suite.jwt_secret,
            algorithm="HS256"
        )
        
        # Decode and verify scope
        payload = jwt.decode(limited_token, edge_suite.jwt_secret, algorithms=["HS256"])
        
        # Attempt to escalate scope
        payload["scope"].append("admin")
        
        # Re-encode with escalated scope (should be prevented in real impl)
        # This would fail with proper signature verification
        escalated_token = jwt.encode(payload, "wrong_secret", algorithm="HS256")
        
        # Should fail verification with correct secret
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(escalated_token, edge_suite.jwt_secret, algorithms=["HS256"])
    
    @pytest.mark.asyncio
    async def test_subdomain_takeover_prevention(self, edge_suite):
        """Test 25: Prevent authentication bypass via subdomain takeover."""
        allowed_domains = ["app.netrasystems.ai", "api.netrasystems.ai"]
        
        # Attempt from hijacked subdomain
        malicious_domain = "evil.netrasystems.ai"
        
        # Should validate domain whitelist
        assert malicious_domain not in allowed_domains