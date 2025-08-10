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
async def test_token_expiration():
    """Test token expiration handling"""
    data = {"sub": "test@example.com"}
    
    with patch("app.auth.auth.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime.now() - timedelta(days=2)
        mock_datetime.timedelta = timedelta
        
        token = create_access_token(data, expires_delta=timedelta(minutes=-1))
        
        with pytest.raises(jwt.ExpiredSignatureError):
            decode_token(token)

@pytest.mark.asyncio
async def test_invalid_token():
    """Test invalid token handling"""
    invalid_token = "invalid.token.here"
    
    with pytest.raises(jwt.InvalidTokenError):
        decode_token(invalid_token)

@pytest.mark.asyncio
async def test_user_registration(client, async_session):
    """Test user registration endpoint"""
    user_data = {
        "email": "newuser@example.com",
        "password": "SecurePassword123!",
        "full_name": "New User"
    }
    
    with patch("app.routes.auth.get_async_session") as mock_session:
        mock_session.return_value.__aenter__.return_value = async_session
        
        response = client.post("/api/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert "id" in data
        assert "password" not in data

@pytest.mark.asyncio
async def test_user_login_success(client, async_session):
    """Test successful user login"""
    
    test_email = "test@example.com"
    test_password = "password123"
    hashed_password = hash_password(test_password)
    
    mock_user = MagicMock()
    mock_user.id = "user-123"
    mock_user.email = test_email
    mock_user.hashed_password = hashed_password
    mock_user.is_active = True
    
    with patch("app.routes.auth.get_async_session") as mock_session:
        with patch("app.routes.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = mock_user
            mock_session.return_value.__aenter__.return_value = async_session
            
            response = client.post("/api/auth/login", data={
                "username": test_email,
                "password": test_password
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_user_login_invalid_credentials(client, async_session):
    """Test login with invalid credentials"""
    
    with patch("app.routes.auth.get_async_session") as mock_session:
        with patch("app.routes.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = None
            mock_session.return_value.__aenter__.return_value = async_session
            
            response = client.post("/api/auth/login", data={
                "username": "invalid@example.com",
                "password": "wrongpassword"
            })
            
            assert response.status_code == 401
            assert "Invalid credentials" in response.json()["detail"]

@pytest.mark.asyncio
async def test_user_login_inactive_user(client, async_session):
    """Test login with inactive user account"""
    
    mock_user = MagicMock()
    mock_user.is_active = False
    
    with patch("app.routes.auth.get_async_session") as mock_session:
        with patch("app.routes.auth.authenticate_user") as mock_auth:
            mock_auth.return_value = mock_user
            mock_session.return_value.__aenter__.return_value = async_session
            
            response = client.post("/api/auth/login", data={
                "username": "inactive@example.com",
                "password": "password123"
            })
            
            assert response.status_code == 401

@pytest.mark.asyncio
async def test_get_current_user(client, test_user, auth_headers):
    """Test getting current user information"""
    
    with patch("app.auth.auth_dependencies.get_active_user") as mock_get_user:
        mock_get_user.return_value = test_user
        
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["id"] == test_user.id

@pytest.mark.asyncio
async def test_refresh_token_endpoint(client, test_user):
    """Test token refresh endpoint"""
    
    refresh_token = create_refresh_token({"sub": test_user.email})
    
    with patch("app.routes.auth.decode_token") as mock_decode:
        with patch("app.routes.auth.get_user_by_email") as mock_get_user:
            mock_decode.return_value = {"sub": test_user.email}
            mock_get_user.return_value = test_user
            
            response = client.post("/api/auth/refresh", json={
                "refresh_token": refresh_token
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data

@pytest.mark.asyncio
async def test_logout(client, auth_headers):
    """Test user logout"""
    
    response = client.post("/api/auth/logout", headers=auth_headers)
    
    assert response.status_code == 200
    assert response.json()["message"] == "Successfully logged out"

@pytest.mark.asyncio
async def test_password_reset_request(client, async_session):
    """Test password reset request"""
    
    with patch("app.routes.auth.get_async_session") as mock_session:
        with patch("app.routes.auth.send_password_reset_email") as mock_send_email:
            mock_session.return_value.__aenter__.return_value = async_session
            mock_send_email.return_value = None
            
            response = client.post("/api/auth/password-reset-request", json={
                "email": "test@example.com"
            })
            
            assert response.status_code == 200
            assert "Password reset email sent" in response.json()["message"]

@pytest.mark.asyncio
async def test_password_reset_confirm(client, async_session):
    """Test password reset confirmation"""
    
    reset_token = create_access_token({"sub": "test@example.com", "type": "password_reset"})
    
    with patch("app.routes.auth.get_async_session") as mock_session:
        with patch("app.routes.auth.decode_token") as mock_decode:
            mock_session.return_value.__aenter__.return_value = async_session
            mock_decode.return_value = {"sub": "test@example.com", "type": "password_reset"}
            
            response = client.post("/api/auth/password-reset-confirm", json={
                "token": reset_token,
                "new_password": "NewSecurePassword123!"
            })
            
            assert response.status_code == 200
            assert "Password reset successful" in response.json()["message"]

@pytest.mark.asyncio
async def test_unauthorized_access(client):
    """Test accessing protected endpoint without authentication"""
    
    response = client.get("/api/auth/me")
    
    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]

@pytest.mark.asyncio
async def test_expired_token_access(client):
    """Test accessing protected endpoint with expired token"""
    
    expired_token = create_access_token(
        {"sub": "test@example.com"},
        expires_delta=timedelta(minutes=-1)
    )
    
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = client.get("/api/auth/me", headers=headers)
    
    assert response.status_code == 401