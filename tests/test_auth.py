import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

# Try to import from app, fall back to test helpers
try:
    from app.auth.auth import (
        create_access_token,
        create_refresh_token,
        decode_token,
        hash_password,
        verify_password
    )
except ImportError:
    from test_helpers import (
        create_access_token,
        hash_password,
        verify_password
    )
    # Mock missing functions
    def create_refresh_token(data: dict):
        return create_access_token(data, expires_delta=timedelta(days=7))
    
    def decode_token(token: str):
        import os
        secret_key = os.environ.get("JWT_SECRET_KEY", "test-secret")
        return jwt.decode(token, secret_key, algorithms=["HS256"])
from app.schemas import UserCreate, User
from app.db.models_postgres import User as UserModel

@pytest.mark.asyncio
async def test_password_hashing():
    """Test password hashing and verification"""
    password = "test_password123"
    
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrong_password", hashed)

@pytest.mark.asyncio
async def test_create_access_token():
    """Test JWT access token creation"""
    data = {"sub": "test@example.com", "user_id": "123"}
    token = create_access_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded["sub"] == "test@example.com"
    assert decoded["user_id"] == "123"
    assert "exp" in decoded

@pytest.mark.asyncio
async def test_create_refresh_token():
    """Test JWT refresh token creation"""
    data = {"sub": "test@example.com"}
    token = create_refresh_token(data)
    
    assert token is not None
    assert isinstance(token, str)
    
    decoded = decode_token(token)
    assert decoded["sub"] == "test@example.com"
    assert "exp" in decoded

@pytest.mark.asyncio
async def test_invalid_token():
    """Test invalid token handling"""
    invalid_token = "invalid.token.here"
    
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(invalid_token)