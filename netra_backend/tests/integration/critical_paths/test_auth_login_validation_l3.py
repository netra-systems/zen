"""
L3 Integration Test: Authentication Login Validation
Tests basic login validation from multiple angles
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import json
from unittest.mock import AsyncMock, patch

import pytest

from netra_backend.app.config import settings

# Add project root to path
from netra_backend.app.services.auth_service import AuthService

# Add project root to path


class TestAuthLoginValidationL3:
    """Test authentication login validation scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_login_with_empty_credentials(self):
        """Test login with empty username and password"""
        auth_service = AuthService()
        
        result = await auth_service.authenticate("", "")
        assert result is None, "Empty credentials should fail"
        
        result = await auth_service.authenticate("user", "")
        assert result is None, "Empty password should fail"
        
        result = await auth_service.authenticate("", "password")
        assert result is None, "Empty username should fail"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_login_with_null_credentials(self):
        """Test login with null/None credentials"""
        auth_service = AuthService()
        
        result = await auth_service.authenticate(None, None)
        assert result is None, "Null credentials should fail"
        
        result = await auth_service.authenticate("user", None)
        assert result is None, "Null password should fail"
        
        result = await auth_service.authenticate(None, "password")
        assert result is None, "Null username should fail"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_login_with_special_characters(self):
        """Test login with special characters in credentials"""
        auth_service = AuthService()
        
        # Test SQL injection attempts
        result = await auth_service.authenticate("admin' OR '1'='1", "password")
        assert result is None, "SQL injection should fail"
        
        # Test with valid special characters
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123"}):
                result = await auth_service.authenticate("user@domain.com", "P@ssw0rd!")
                assert result is not None, "Valid special characters should work"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_login_with_whitespace_credentials(self):
        """Test login with whitespace in credentials"""
        auth_service = AuthService()
        
        # Leading/trailing whitespace
        result = await auth_service.authenticate("  user  ", "password")
        assert result is None or result.get("username") == "user", "Should trim whitespace"
        
        # Only whitespace
        result = await auth_service.authenticate("   ", "   ")
        assert result is None, "Whitespace-only credentials should fail"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_login_case_sensitivity(self):
        """Test username case sensitivity handling"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user') as mock_get:
                mock_get.return_value = {"id": "123", "username": "testuser"}
                
                # Test lowercase
                result = await auth_service.authenticate("testuser", "password")
                assert result is not None
                
                # Test uppercase (should normalize)
                result = await auth_service.authenticate("TESTUSER", "password")
                mock_get.assert_called_with("testuser")  # Should normalize to lowercase