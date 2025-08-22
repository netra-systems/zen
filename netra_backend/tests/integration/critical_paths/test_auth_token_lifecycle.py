"""
L3 Integration Test: Authentication Token Lifecycle
Tests complete token lifecycle from creation to expiration
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import jwt
import pytest

from netra_backend.app.config import get_config

from netra_backend.app.services.auth_service import AuthService

class TestAuthTokenLifecycleL3:
    """Test authentication token lifecycle scenarios"""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_creation_with_valid_user(self):
        """Test token creation for valid authenticated user"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                result = await auth_service.authenticate("testuser", "password")
                
                assert result is not None
                assert "access_token" in result
                assert "refresh_token" in result
                assert "token_type" in result
                assert result["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_expiration_handling(self):
        """Test token expiration and validation"""
        auth_service = AuthService()
        
        # Create expired token
        expired_token = jwt.encode(
            {"sub": "123", "exp": datetime.utcnow() - timedelta(hours=1)},
            settings.SECRET_KEY,
            algorithm="HS256"
        )
        
        result = await auth_service.validate_token_jwt(expired_token)
        assert result is None, "Expired token should be invalid"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_refresh_flow(self):
        """Test refresh token flow"""
        auth_service = AuthService()
        
        # Create initial tokens
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                initial = await auth_service.authenticate("testuser", "password")
                
                # Use refresh token
                refreshed = await auth_service.refresh_token(initial["refresh_token"])
                
                assert refreshed is not None
                assert refreshed["access_token"] != initial["access_token"]
                assert "refresh_token" in refreshed
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_token_revocation(self):
        """Test token revocation mechanism"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                result = await auth_service.authenticate("testuser", "password")
                token = result["access_token"]
                
                # Revoke token
                await auth_service.revoke_token(token)
                
                # Validate revoked token
                validation = await auth_service.validate_token_jwt(token)
                assert validation is None, "Revoked token should be invalid"
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.l3
    async def test_concurrent_token_validation(self):
        """Test concurrent token validation requests"""
        auth_service = AuthService()
        
        with patch.object(auth_service, '_verify_password', return_value=True):
            with patch.object(auth_service, '_get_user', return_value={"id": "123", "username": "testuser"}):
                result = await auth_service.authenticate("testuser", "password")
                token = result["access_token"]
                
                # Validate token concurrently
                tasks = [auth_service.validate_token_jwt(token) for _ in range(10)]
                results = await asyncio.gather(*tasks)
                
                assert all(r is not None for r in results), "All validations should succeed"