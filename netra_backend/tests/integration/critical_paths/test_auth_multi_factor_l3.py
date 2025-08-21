"""
L3 Integration Test: Multi-Factor Authentication
Tests MFA flows including TOTP, SMS, and backup codes
"""

import pytest
import asyncio
import pyotp
from unittest.mock import patch, AsyncMock, MagicMock
from netra_backend.app.services.auth_service import AuthService
from netra_backend.app.core.config import settings
import time


class TestAuthMultiFactorL3:
    """Test multi-factor authentication scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_enrollment_flow(self):
        """Test MFA enrollment process"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                # Initial login
                result = await auth_service.authenticate("testuser", "password")
                
                # Enroll in MFA
                mfa_secret = await auth_service.enroll_mfa(result["user_id"])
                
                assert mfa_secret is not None
                assert "secret" in mfa_secret
                assert "qr_code" in mfa_secret
                assert "backup_codes" in mfa_secret
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_totp_verification(self):
        """Test TOTP code verification"""
        auth_service = AuthService()
        
        # Generate TOTP secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)
        
        with patch.object(auth_service, '_get_user_mfa_secret', return_value=secret):
            # Valid code
            valid_code = totp.now()
            result = await auth_service.verify_mfa("123", valid_code)
            assert result is True, "Valid TOTP code should verify"
            
            # Invalid code
            result = await auth_service.verify_mfa("123", "000000")
            assert result is False, "Invalid TOTP code should fail"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_backup_code_usage(self):
        """Test backup code usage and invalidation"""
        auth_service = AuthService()
        
        backup_codes = ["CODE1", "CODE2", "CODE3"]
        
        with patch.object(auth_service, '_get_backup_codes', return_value=backup_codes):
            # Use backup code
            result = await auth_service.verify_backup_code("123", "CODE1")
            assert result is True, "Valid backup code should work"
            
            # Try to reuse same code
            result = await auth_service.verify_backup_code("123", "CODE1")
            assert result is False, "Used backup code should be invalid"
            
            # Use different code
            result = await auth_service.verify_backup_code("123", "CODE2")
            assert result is True, "Unused backup code should work"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_rate_limiting(self):
        """Test MFA attempt rate limiting"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_get_user_mfa_secret', return_value="SECRET"):
            # Multiple failed attempts
            for i in range(5):
                await auth_service.verify_mfa("123", "000000")
            
            # Should be rate limited
            with pytest.raises(Exception) as exc_info:
                await auth_service.verify_mfa("123", "000000")
            
            assert "rate limit" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_mfa_bypass_for_trusted_device(self):
        """Test MFA bypass for trusted devices"""
        auth_service = AuthService()
        
        device_id = "trusted-device-123"
        
        with patch.object(auth_service, '_is_trusted_device', return_value=True):
            # Should bypass MFA for trusted device
            result = await auth_service.check_mfa_required("123", device_id)
            assert result is False, "Trusted device should bypass MFA"
        
        with patch.object(auth_service, '_is_trusted_device', return_value=False):
            # Should require MFA for untrusted device
            result = await auth_service.check_mfa_required("123", "untrusted-device")
            assert result is True, "Untrusted device should require MFA"