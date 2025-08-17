"""
Enhanced Authentication Tests
Tests enhanced authentication security functionality
"""

import pytest
from app.auth.enhanced_auth_security import EnhancedAuthSecurity, AuthenticationResult


class TestEnhancedAuthentication:
    """Test enhanced authentication security."""
    
    @pytest.fixture
    def auth_security(self):
        """Create authentication security for testing."""
        return EnhancedAuthSecurity()
    
    def test_successful_authentication(self, auth_security):
        """Test successful authentication flow."""
        result, session_id = auth_security.authenticate_user(
            "test_user", 
            "valid_password123", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        assert result == AuthenticationResult.SUCCESS
        assert session_id is not None
        assert len(session_id) > 20  # Should be sufficiently long
    
    def test_failed_authentication(self, auth_security):
        """Test failed authentication handling."""
        result, session_id = auth_security.authenticate_user(
            "test_user", 
            "wrong_password", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        assert result == AuthenticationResult.FAILED
        assert session_id is None
    
    def test_rate_limiting_by_ip(self, auth_security):
        """Test IP-based rate limiting."""
        ip_address = "192.168.1.100"
        
        # Make multiple failed attempts
        for i in range(11):  # Exceed rate limit
            result, _ = auth_security.authenticate_user(
                f"user_{i}", 
                "wrong_password", 
                ip_address, 
                "Mozilla/5.0 Test Agent"
            )
            
            if i < 10:
                assert result == AuthenticationResult.FAILED
            else:
                assert result == AuthenticationResult.BLOCKED
    
    def test_user_lockout(self, auth_security):
        """Test user lockout after max failed attempts."""
        user_id = "lockout_test_user"
        
        # Make multiple failed attempts for same user
        for i in range(6):  # Exceed max failed attempts (5)
            result, _ = auth_security.authenticate_user(
                user_id, 
                "wrong_password", 
                f"192.168.1.{i}", 
                "Mozilla/5.0 Test Agent"
            )
            
            if i < 5:
                assert result == AuthenticationResult.FAILED
            else:
                assert result == AuthenticationResult.BLOCKED
    
    def test_session_validation(self, auth_security):
        """Test session validation with security checks."""
        # Create session
        result, session_id = auth_security.authenticate_user(
            "session_test_user", 
            "valid_password123", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        assert result == AuthenticationResult.SUCCESS
        
        # Validate session with same IP/UA
        valid, error = auth_security.validate_session(
            session_id, 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        assert valid
        assert error is None
        
        # Validate session with different IP (should be suspicious)
        valid, error = auth_security.validate_session(
            session_id, 
            "10.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        # Session might still be valid but flagged as suspicious
        session = auth_security.active_sessions.get(session_id)
        if session:
            assert "ip_mismatch" in session.security_flags.get("security_issues", [])
    
    def test_concurrent_session_limits(self, auth_security):
        """Test concurrent session limits."""
        user_id = "concurrent_test_user"
        sessions = []
        
        # Create multiple sessions (should be limited)
        for i in range(5):  # Try to exceed max concurrent sessions (3)
            result, session_id = auth_security.authenticate_user(
                user_id, 
                "valid_password123", 
                f"192.168.1.{i}", 
                f"Mozilla/5.0 Test Agent {i}"
            )
            
            if result == AuthenticationResult.SUCCESS:
                sessions.append(session_id)
        
        # Should not have more than max concurrent sessions
        active_user_sessions = [
            s for s in auth_security.active_sessions.values() 
            if s.user_id == user_id and s.status.value == "active"
        ]
        assert len(active_user_sessions) <= auth_security.max_concurrent_sessions
    
    def test_security_metrics(self, auth_security):
        """Test security metrics collection."""
        # Generate some activity
        auth_security.authenticate_user("user1", "password", "127.0.0.1", "agent")
        auth_security.authenticate_user("user2", "wrong", "127.0.0.1", "agent")
        
        metrics = auth_security.get_security_status()
        
        assert "active_sessions" in metrics
        assert "blocked_ips" in metrics
        assert "metrics" in metrics
        assert "security_score" in metrics["metrics"]
    
    def test_password_strength_validation(self, auth_security):
        """Test password strength validation."""
        weak_passwords = [
            "123456",
            "password",
            "abc123",
            "qwerty"
        ]
        
        for weak_password in weak_passwords:
            is_strong = auth_security.validate_password_strength(weak_password)
            assert not is_strong
        
        strong_passwords = [
            "MyStr0ngP@ssw0rd!",
            "C0mpl3x_P@ssw0rd_2023",
            "S3cur3#Passw0rd$"
        ]
        
        for strong_password in strong_passwords:
            is_strong = auth_security.validate_password_strength(strong_password)
            assert is_strong
    
    def test_session_hijacking_protection(self, auth_security):
        """Test protection against session hijacking."""
        # Create session
        result, session_id = auth_security.authenticate_user(
            "hijack_test_user", 
            "valid_password123", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        assert result == AuthenticationResult.SUCCESS
        
        # Try to use session from different browser
        valid, error = auth_security.validate_session(
            session_id, 
            "127.0.0.1", 
            "Chrome/90.0 Different Agent"
        )
        
        # Should detect potential hijacking
        assert not valid or "suspicious" in error.lower()
    
    def test_multi_factor_authentication(self, auth_security):
        """Test multi-factor authentication flow."""
        # Enable MFA for user
        user_id = "mfa_test_user"
        auth_security.enable_mfa(user_id)
        
        # First factor authentication
        result, session_id = auth_security.authenticate_user(
            user_id, 
            "valid_password123", 
            "127.0.0.1", 
            "Mozilla/5.0 Test Agent"
        )
        
        # Should require second factor
        assert result == AuthenticationResult.MFA_REQUIRED
        
        # Provide second factor
        mfa_result = auth_security.verify_mfa_token(session_id, "123456")
        assert mfa_result == AuthenticationResult.SUCCESS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])