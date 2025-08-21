"""
L4 Integration Test: Login Edge Cases Complete
Tests all edge cases in login flow including rate limiting, account states, and errors
"""

import pytest
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.services.user_service import UserService
from netra_backend.app.services.rate_limit_service import RateLimitService
from netra_backend.app.services.session_service import SessionService
from netra_backend.app.models.user import User, UserStatus
from netra_backend.app.config import settings
from netra_backend.app.core.exceptions import (

# Add project root to path
    AuthenticationError,
    RateLimitExceeded,
    AccountLocked,
    AccountSuspended
)


class TestLoginEdgeCasesCompleteL4:
    """Complete login edge case testing"""
    
    @pytest.fixture
    async def auth_system(self):
        """Complete auth system setup"""
        return {
            'auth_service': AuthService(),
            'user_service': UserService(),
            'rate_limiter': RateLimitService(),
            'session_service': SessionService(),
            'failed_attempts': {},
            'locked_accounts': set(),
            'suspicious_ips': set()
        }
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_rate_limiting(self, auth_system):
        """Test login rate limiting per IP and per account"""
        email = "ratelimit@test.com"
        password = "Test123!"
        ip_address = "192.168.1.100"
        
        # Attempt rapid logins from same IP
        login_attempts = []
        for i in range(10):
            try:
                result = await auth_system['auth_service'].login(
                    email=email,
                    password=password,
                    ip_address=ip_address
                )
                login_attempts.append(result)
            except RateLimitExceeded:
                login_attempts.append("rate_limited")
        
        # Should hit rate limit after 5 attempts
        successful = [a for a in login_attempts if a != "rate_limited"]
        rate_limited = [a for a in login_attempts if a == "rate_limited"]
        
        assert len(successful) <= 5
        assert len(rate_limited) >= 5
        
        # Test per-account rate limiting
        different_ips = [f"192.168.1.{i}" for i in range(200, 210)]
        account_attempts = []
        
        for ip in different_ips:
            try:
                result = await auth_system['auth_service'].login(
                    email=email,
                    password=password,
                    ip_address=ip
                )
                account_attempts.append(result)
            except RateLimitExceeded:
                account_attempts.append("rate_limited")
        
        # Account should also be rate limited
        assert "rate_limited" in account_attempts
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_invalid_credentials_lockout(self, auth_system):
        """Test account lockout after multiple failed attempts"""
        email = "lockout@test.com"
        correct_password = "Correct123!"
        wrong_password = "Wrong456!"
        ip_address = "192.168.1.101"
        
        # Create user
        user = await auth_system['user_service'].create_user(
            email=email,
            password=correct_password
        )
        
        # Attempt login with wrong password multiple times
        failed_attempts = 0
        locked = False
        
        for i in range(10):
            try:
                result = await auth_system['auth_service'].login(
                    email=email,
                    password=wrong_password,
                    ip_address=ip_address
                )
            except AuthenticationError:
                failed_attempts += 1
            except AccountLocked:
                locked = True
                break
        
        # Account should be locked after 5 failed attempts
        assert failed_attempts >= 5
        assert locked
        
        # Even correct password should fail when locked
        with pytest.raises(AccountLocked):
            await auth_system['auth_service'].login(
                email=email,
                password=correct_password,
                ip_address=ip_address
            )
        
        # Verify lockout duration
        lockout_info = await auth_system['user_service'].get_lockout_info(user.id)
        assert lockout_info['is_locked']
        assert lockout_info['lockout_until'] > datetime.utcnow()
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_suspended_account(self, auth_system):
        """Test login attempts with suspended account"""
        email = "suspended@test.com"
        password = "Test123!"
        
        # Create and suspend user
        user = await auth_system['user_service'].create_user(
            email=email,
            password=password
        )
        
        await auth_system['user_service'].suspend_user(
            user_id=user.id,
            reason="Terms violation",
            duration_hours=24
        )
        
        # Login should fail with specific error
        with pytest.raises(AccountSuspended) as exc_info:
            await auth_system['auth_service'].login(
                email=email,
                password=password,
                ip_address="192.168.1.102"
            )
        
        assert "suspended" in str(exc_info.value).lower()
        assert exc_info.value.suspension_reason == "Terms violation"
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_unverified_email(self, auth_system):
        """Test login with unverified email address"""
        email = "unverified@test.com"
        password = "Test123!"
        
        # Create user without email verification
        user = await auth_system['user_service'].create_user(
            email=email,
            password=password,
            email_verified=False
        )
        
        # Login should succeed but with limited access flag
        result = await auth_system['auth_service'].login(
            email=email,
            password=password,
            ip_address="192.168.1.103"
        )
        
        assert result['login_successful']
        assert result['limited_access']
        assert result['email_verification_required']
        
        # Session should have restricted permissions
        session = await auth_system['session_service'].get_session(result['session_id'])
        assert session['permissions']['restricted_mode']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_expired_password(self, auth_system):
        """Test login with expired password"""
        email = "expired_pass@test.com"
        password = "OldPassword123!"
        
        # Create user with expired password
        user = await auth_system['user_service'].create_user(
            email=email,
            password=password,
            password_expires_at=datetime.utcnow() - timedelta(days=1)
        )
        
        # Login should succeed but require password change
        result = await auth_system['auth_service'].login(
            email=email,
            password=password,
            ip_address="192.168.1.104"
        )
        
        assert result['login_successful']
        assert result['password_change_required']
        assert result['session_type'] == 'temporary'
        
        # Session should only allow password change endpoint
        session = await auth_system['session_service'].get_session(result['session_id'])
        assert session['allowed_endpoints'] == ['/api/auth/change-password']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_2fa_enabled(self, auth_system):
        """Test login flow with 2FA enabled"""
        email = "2fa@test.com"
        password = "Test123!"
        
        # Create user with 2FA
        user = await auth_system['user_service'].create_user(
            email=email,
            password=password,
            two_factor_enabled=True,
            two_factor_secret="JBSWY3DPEHPK3PXP"
        )
        
        # First login step
        result = await auth_system['auth_service'].login(
            email=email,
            password=password,
            ip_address="192.168.1.105"
        )
        
        assert result['login_successful'] == False
        assert result['two_factor_required']
        assert 'challenge_token' in result
        
        # Attempt with wrong 2FA code
        with pytest.raises(AuthenticationError):
            await auth_system['auth_service'].verify_2fa(
                challenge_token=result['challenge_token'],
                two_factor_code="000000"
            )
        
        # Attempt with correct 2FA code
        correct_code = "123456"  # Would be generated from secret
        with patch.object(auth_system['auth_service'], 'verify_totp') as mock_totp:
            mock_totp.return_value = True
            
            final_result = await auth_system['auth_service'].verify_2fa(
                challenge_token=result['challenge_token'],
                two_factor_code=correct_code
            )
            
            assert final_result['login_successful']
            assert 'session_id' in final_result
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_from_new_device(self, auth_system):
        """Test login from unrecognized device"""
        email = "device@test.com"
        password = "Test123!"
        
        # Create user with device tracking
        user = await auth_system['user_service'].create_user(
            email=email,
            password=password,
            track_devices=True
        )
        
        # Register known device
        await auth_system['user_service'].register_device(
            user_id=user.id,
            device_id="known_device_1",
            device_info={"type": "desktop", "browser": "chrome"}
        )
        
        # Login from new device
        result = await auth_system['auth_service'].login(
            email=email,
            password=password,
            ip_address="192.168.1.106",
            device_id="new_device_1",
            device_info={"type": "mobile", "browser": "safari"}
        )
        
        assert result['login_successful']
        assert result['new_device_detected']
        assert result['verification_email_sent']
        
        # Check security alert was created
        alerts = await auth_system['user_service'].get_security_alerts(user.id)
        assert len(alerts) > 0
        assert alerts[0]['type'] == 'new_device_login'
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_from_suspicious_location(self, auth_system):
        """Test login from suspicious geographic location"""
        email = "location@test.com"
        password = "Test123!"
        
        # Create user with typical location
        user = await auth_system['user_service'].create_user(
            email=email,
            password=password,
            typical_location="US"
        )
        
        # Record normal login pattern
        for _ in range(5):
            await auth_system['auth_service'].login(
                email=email,
                password=password,
                ip_address="8.8.8.8",  # US IP
                geo_location={"country": "US", "city": "Mountain View"}
            )
        
        # Attempt login from suspicious location
        result = await auth_system['auth_service'].login(
            email=email,
            password=password,
            ip_address="1.2.3.4",  # Different country IP
            geo_location={"country": "CN", "city": "Beijing"}
        )
        
        assert result['login_successful']
        assert result['suspicious_location']
        assert result['additional_verification_required']
        
        # Session should have limited permissions until verified
        session = await auth_system['session_service'].get_session(result['session_id'])
        assert session['requires_location_verification']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_during_maintenance_mode(self, auth_system):
        """Test login behavior during maintenance mode"""
        email_regular = "regular@test.com"
        email_admin = "admin@test.com"
        password = "Test123!"
        
        # Create regular and admin users
        regular_user = await auth_system['user_service'].create_user(
            email=email_regular,
            password=password,
            role="user"
        )
        
        admin_user = await auth_system['user_service'].create_user(
            email=email_admin,
            password=password,
            role="admin"
        )
        
        # Enable maintenance mode
        with patch.object(settings, 'MAINTENANCE_MODE', True):
            # Regular user login should fail
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_system['auth_service'].login(
                    email=email_regular,
                    password=password,
                    ip_address="192.168.1.107"
                )
            assert "maintenance" in str(exc_info.value).lower()
            
            # Admin user should still login
            admin_result = await auth_system['auth_service'].login(
                email=email_admin,
                password=password,
                ip_address="192.168.1.108"
            )
            assert admin_result['login_successful']
            assert admin_result['maintenance_mode_active']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_concurrent_login_session_management(self, auth_system):
        """Test concurrent login session limits"""
        email = "concurrent@test.com"
        password = "Test123!"
        
        # Create user with session limit
        user = await auth_system['user_service'].create_user(
            email=email,
            password=password,
            max_concurrent_sessions=3
        )
        
        # Create multiple sessions
        sessions = []
        for i in range(5):
            try:
                result = await auth_system['auth_service'].login(
                    email=email,
                    password=password,
                    ip_address=f"192.168.1.{110 + i}",
                    device_id=f"device_{i}"
                )
                sessions.append(result)
            except Exception as e:
                sessions.append({"error": str(e)})
        
        # Only 3 should succeed
        successful_sessions = [s for s in sessions if 'session_id' in s]
        assert len(successful_sessions) == 3
        
        # Oldest session should be terminated when limit exceeded
        first_session_valid = await auth_system['session_service'].validate_session(
            sessions[0].get('session_id')
        )
        assert not first_session_valid['valid']  # Should be terminated
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_sql_injection_attempt(self, auth_system):
        """Test login security against SQL injection"""
        malicious_emails = [
            "admin'--",
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "admin@test.com' UNION SELECT * FROM users--"
        ]
        
        for evil_email in malicious_emails:
            # Should safely handle without executing injection
            with pytest.raises((AuthenticationError, ValueError)):
                await auth_system['auth_service'].login(
                    email=evil_email,
                    password="password",
                    ip_address="192.168.1.200"
                )
            
            # Verify no database corruption
            db_healthy = await auth_system['auth_service'].health_check()
            assert db_healthy['database_connection']
    
    @pytest.mark.asyncio
    @pytest.mark.timeout(30)
    async def test_login_with_password_history_check(self, auth_system):
        """Test login after password change with history validation"""
        email = "history@test.com"
        passwords = ["FirstPass123!", "SecondPass456!", "ThirdPass789!"]
        
        # Create user
        user = await auth_system['user_service'].create_user(
            email=email,
            password=passwords[0]
        )
        
        # Change password multiple times
        for i in range(1, len(passwords)):
            await auth_system['auth_service'].change_password(
                user_id=user.id,
                old_password=passwords[i-1],
                new_password=passwords[i]
            )
        
        # Old passwords should not work
        for old_pass in passwords[:-1]:
            with pytest.raises(AuthenticationError):
                await auth_system['auth_service'].login(
                    email=email,
                    password=old_pass,
                    ip_address="192.168.1.201"
                )
        
        # Current password should work
        result = await auth_system['auth_service'].login(
            email=email,
            password=passwords[-1],
            ip_address="192.168.1.201"
        )
        assert result['login_successful']