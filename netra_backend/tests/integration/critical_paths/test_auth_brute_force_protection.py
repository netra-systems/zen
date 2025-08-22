"""
L3 Integration Test: Brute Force Protection
Tests authentication brute force protection mechanisms
"""

# Add project root to path
import sys
from pathlib import Path

from test_framework import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from netra_backend.app.config import get_config

# Add project root to path
from netra_backend.app.services.auth_service import AuthService

# Add project root to path


class TestAuthBruteForceProtectionL3:
    """Test brute force protection scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_failed_login_tracking(self):
        """Test tracking of failed login attempts"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=False):
            # Multiple failed attempts
            for i in range(3):
                result = await auth_service.authenticate("testuser", "wrong_password")
                assert result is None
            
            # Check failed attempt count
            count = await auth_service.get_failed_attempts("testuser")
            assert count == 3
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_account_lockout_after_threshold(self):
        """Test account lockout after exceeding attempt threshold"""
        auth_service = AuthService()
        max_attempts = 5
        
        with patch.object(auth_service, 'MAX_FAILED_ATTEMPTS', max_attempts):
            with patch.object(auth_service, '_verify_password', return_value=False):
                # Exceed threshold
                for i in range(max_attempts + 1):
                    await auth_service.authenticate("testuser", "wrong_password")
                
                # Account should be locked
                with patch.object(auth_service, '_verify_password', return_value=True):
                    result = await auth_service.authenticate("testuser", "correct_password")
                    assert result is None, "Account should be locked"
                    
                    # Check lock status
                    is_locked = await auth_service.is_account_locked("testuser")
                    assert is_locked is True
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_lockout_duration_expiry(self):
        """Test automatic unlock after lockout duration"""
        auth_service = AuthService()
        lockout_duration = 1  # 1 second for testing
        
        with patch.object(auth_service, 'LOCKOUT_DURATION', lockout_duration):
            # Lock account
            await auth_service.lock_account("testuser")
            
            # Should be locked immediately
            is_locked = await auth_service.is_account_locked("testuser")
            assert is_locked is True
            
            # Wait for lockout to expire
            await asyncio.sleep(lockout_duration + 0.1)
            
            # Should be unlocked
            is_locked = await auth_service.is_account_locked("testuser")
            assert is_locked is False
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_ip_based_rate_limiting(self):
        """Test IP-based login rate limiting"""
        auth_service = AuthService()
        ip_address = "192.168.1.100"
        
        # Multiple rapid attempts from same IP
        attempts = []
        for i in range(10):
            start = time.time()
            result = await auth_service.authenticate(
                f"user{i}", "password", ip=ip_address
            )
            duration = time.time() - start
            attempts.append(duration)
        
        # Later attempts should be rate limited (slower)
        assert attempts[-1] > attempts[0], "Should be rate limited"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_captcha_requirement_after_failures(self):
        """Test CAPTCHA requirement after multiple failures"""
        auth_service = AuthService()
        captcha_threshold = 3
        
        with patch.object(auth_service, 'CAPTCHA_THRESHOLD', captcha_threshold):
            with patch.object(auth_service, '_verify_password', return_value=False):
                # Failed attempts
                for i in range(captcha_threshold):
                    await auth_service.authenticate("testuser", "wrong")
                
                # Next attempt should require CAPTCHA
                requires_captcha = await auth_service.requires_captcha("testuser")
                assert requires_captcha is True
                
                # Without CAPTCHA should fail
                with patch.object(auth_service, '_verify_password', return_value=True):
                    result = await auth_service.authenticate("testuser", "correct")
                    assert result is None, "Should require CAPTCHA"