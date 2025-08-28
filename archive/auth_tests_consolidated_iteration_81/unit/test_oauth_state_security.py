"""
OAuth State Parameter Security Tests
Testing Level: Unit (L1)
Focus: OAuth state parameter security implementation

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Security, Compliance, Trust
- Value Impact: Prevents CSRF attacks and OAuth hijacking
- Strategic Impact: Critical for platform security compliance and user trust

OAuth Basics Coverage:
- State parameter generation (cryptographically secure)
- State parameter validation (timing-safe comparison)
- State parameter expiration handling
- State parameter uniqueness enforcement
- CSRF protection through state binding
"""

import secrets
import time
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
import pytest

from auth_service.auth_core.security.oauth_security import OAuthSecurityManager
from auth_service.auth_core.models.auth_models import AuthProvider


class TestOAuthStateParameterSecurity:
    """Test OAuth state parameter security basics"""

    def test_state_parameter_cryptographic_strength(self):
        """Test that OAuth state parameters meet cryptographic strength requirements"""
        security_manager = OAuthSecurityManager()
        
        # Generate multiple state parameters
        states = [security_manager.generate_state_parameter() for _ in range(100)]
        
        # Test entropy - all states should be unique
        assert len(set(states)) == 100, "State parameters must be cryptographically unique"
        
        # Test length - should be at least 32 characters for security
        for state in states:
            assert len(state) >= 32, f"State parameter too short: {len(state)} chars"
            
        # Test character set - should be URL-safe base64
        import string
        valid_chars = set(string.ascii_letters + string.digits + '-_')
        for state in states:
            state_chars = set(state.rstrip('='))  # Remove padding
            assert state_chars.issubset(valid_chars), f"Invalid characters in state: {state}"

    def test_state_parameter_timing_safe_validation(self):
        """Test that state validation is timing-safe to prevent timing attacks"""
        security_manager = OAuthSecurityManager()
        
        valid_state = security_manager.generate_state_parameter()
        
        # Create a state that differs by one character
        invalid_state = valid_state[:-1] + ('A' if valid_state[-1] != 'A' else 'B')
        
        # Store the valid state
        security_manager.store_state_parameter(valid_state, "test_session")
        
        # Time the validation operations
        import time
        
        # Valid state validation timing
        start_time = time.perf_counter()
        result_valid = security_manager.validate_state_parameter(valid_state, "test_session")
        valid_duration = time.perf_counter() - start_time
        
        # Invalid state validation timing  
        start_time = time.perf_counter()
        result_invalid = security_manager.validate_state_parameter(invalid_state, "test_session")
        invalid_duration = time.perf_counter() - start_time
        
        # Results should be correct
        assert result_valid is True, "Valid state should pass validation"
        assert result_invalid is False, "Invalid state should fail validation"
        
        # Timing should be similar (within reasonable bounds)
        # This is a basic check - in production, use constant-time comparison
        time_ratio = max(valid_duration, invalid_duration) / min(valid_duration, invalid_duration)
        assert time_ratio < 10.0, f"Timing difference too large: {time_ratio}x"

    def test_state_parameter_expiration_enforcement(self):
        """Test that expired state parameters are rejected"""
        security_manager = OAuthSecurityManager()
        
        state = security_manager.generate_state_parameter()
        
        # Mock time to simulate expiration
        with patch('auth_service.auth_core.security.oauth_security.datetime') as mock_datetime:
            # Store state at current time
            mock_datetime.now.return_value = datetime.now(timezone.utc)
            mock_datetime.utcnow.return_value = datetime.now(timezone.utc)
            security_manager.store_state_parameter(state, "test_session")
            
            # Validate immediately - should work
            assert security_manager.validate_state_parameter(state, "test_session") is True
            
            # Move time forward past expiration (default 10 minutes)
            expired_time = datetime.now(timezone.utc) + timedelta(minutes=15)
            mock_datetime.now.return_value = expired_time
            mock_datetime.utcnow.return_value = expired_time.replace(tzinfo=None)
            
            # Should now be expired
            assert security_manager.validate_state_parameter(state, "test_session") is False

    def test_state_parameter_single_use_enforcement(self):
        """Test that state parameters can only be used once"""
        security_manager = OAuthSecurityManager()
        
        state = security_manager.generate_state_parameter()
        security_manager.store_state_parameter(state, "test_session")
        
        # First use should succeed
        assert security_manager.validate_state_parameter(state, "test_session") is True
        
        # Second use should fail (state should be consumed)
        assert security_manager.validate_state_parameter(state, "test_session") is False

    def test_state_parameter_session_binding(self):
        """Test that state parameters are bound to specific sessions"""
        security_manager = OAuthSecurityManager()
        
        state = security_manager.generate_state_parameter()
        
        # Store state for session A
        security_manager.store_state_parameter(state, "session_a")
        
        # Should validate for correct session
        assert security_manager.validate_state_parameter(state, "session_a") is True
        
        # Should NOT validate for different session  
        security_manager.store_state_parameter(state, "session_a")  # Re-store for test
        assert security_manager.validate_state_parameter(state, "session_b") is False

    def test_state_parameter_hmac_integrity(self):
        """Test that state parameters include HMAC for integrity protection"""
        security_manager = OAuthSecurityManager()
        
        # Generate state with known session
        session_id = "test_session_123"
        state = security_manager.generate_state_parameter_with_hmac(session_id)
        
        # State should contain HMAC signature
        assert '.' in state, "State should contain HMAC separator"
        
        state_data, signature = state.split('.', 1)
        
        # Verify HMAC signature
        expected_signature = hmac.new(
            security_manager.hmac_secret.encode(),
            f"{state_data}:{session_id}".encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Use timing-safe comparison for validation
        assert hmac.compare_digest(signature, expected_signature), "HMAC signature verification failed"

    def test_state_parameter_collision_resistance(self):
        """Test resistance to state parameter collisions"""
        security_manager = OAuthSecurityManager()
        
        # Generate many states and check for collisions
        state_count = 10000
        states = set()
        
        for _ in range(state_count):
            state = security_manager.generate_state_parameter()
            assert state not in states, f"State collision detected: {state}"
            states.add(state)
        
        # All states should be unique
        assert len(states) == state_count, "Not all states were unique"

    def test_oauth_provider_state_isolation(self):
        """Test that different OAuth providers maintain separate state spaces"""
        security_manager = OAuthSecurityManager()
        
        # Generate states for different providers
        google_state = security_manager.generate_provider_state(AuthProvider.GOOGLE, "session_1")
        github_state = security_manager.generate_provider_state(AuthProvider.GITHUB, "session_1") 
        
        # States should be different even for same session
        assert google_state != github_state, "Provider states should be isolated"
        
        # Store both states
        security_manager.store_provider_state(AuthProvider.GOOGLE, google_state, "session_1")
        security_manager.store_provider_state(AuthProvider.GITHUB, github_state, "session_1")
        
        # Validation should be provider-specific
        assert security_manager.validate_provider_state(AuthProvider.GOOGLE, google_state, "session_1") is True
        assert security_manager.validate_provider_state(AuthProvider.GITHUB, github_state, "session_1") is True
        
        # Cross-provider validation should fail
        assert security_manager.validate_provider_state(AuthProvider.GITHUB, google_state, "session_1") is False
        assert security_manager.validate_provider_state(AuthProvider.GOOGLE, github_state, "session_1") is False

    def test_state_parameter_cleanup_on_failure(self):
        """Test that failed OAuth attempts clean up state parameters"""
        security_manager = OAuthSecurityManager()
        
        state = security_manager.generate_state_parameter()
        security_manager.store_state_parameter(state, "test_session")
        
        # Simulate OAuth failure
        security_manager.handle_oauth_failure(state, "test_session", "invalid_code")
        
        # State should be cleaned up and no longer valid
        assert security_manager.validate_state_parameter(state, "test_session") is False

    def test_state_parameter_entropy_distribution(self):
        """Test that state parameters have good entropy distribution"""
        security_manager = OAuthSecurityManager()
        
        # Generate states and analyze entropy
        states = [security_manager.generate_state_parameter() for _ in range(1000)]
        
        # Check character frequency distribution
        char_counts = {}
        for state in states:
            for char in state:
                char_counts[char] = char_counts.get(char, 0) + 1
        
        # Basic entropy check - no character should be overwhelmingly frequent
        total_chars = sum(char_counts.values())
        for char, count in char_counts.items():
            frequency = count / total_chars
            assert frequency < 0.1, f"Character '{char}' appears too frequently: {frequency:.3f}"