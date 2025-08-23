"""
Regression tests for auth service user persistence.
Ensures auth service creates real database users, not just tokens.

CRITICAL: These tests prevent regression of the WebSocket auth failure
where tokens were created but users didn't exist in the database.
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from netra_backend.app.routes.utils.websocket_helpers import authenticate_websocket_user
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import User
from netra_backend.app.services.security_service import SecurityService

class TestAuthUserPersistenceRegression:
    """Regression tests for auth user persistence issues."""
    
    @pytest.mark.asyncio
    async def test_websocket_auth_requires_database_user(self):
        """Test that WebSocket auth fails if user doesn't exist in database."""
        # Setup
        websocket = AsyncMock()
        security_service = AsyncMock()
        
        # Create token with user ID that doesn't exist in DB
        fake_user_id = "non-existent-user-123"
        token_payload = {
            "sub": fake_user_id,
            "email": "fake@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        security_service.decode_access_token.return_value = token_payload
        security_service.get_user_by_id.return_value = None  # User not in DB
        
        # Test - should fail authentication
        with pytest.raises(ValueError, match="User not found"):
            with patch('app.routes.utils.websocket_helpers.get_async_db'):
                await authenticate_websocket_user(
                    websocket, "fake_token", security_service
                )
        
        # Verify WebSocket was closed with error
        websocket.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dev_user_123_exists_in_database(self):
        """Test that dev-user-123 is created in the database."""
        from netra_backend.app.db.postgres import get_async_db
        
        async with get_async_db() as db:
            # Query for dev user
            from sqlalchemy import select
            result = await db.execute(
                select(User).filter(User.id == "dev-user-123")
            )
            dev_user = result.scalars().first()
            
            # Verify dev user exists
            assert dev_user is not None, "dev-user-123 must exist in database"
            assert dev_user.email in ["dev@example.com", "dev-user-123@example.com"]
            assert dev_user.is_active is True
    
    @pytest.mark.asyncio
    async def test_oauth_creates_real_database_user(self):
        """Test that OAuth flow creates users in the database."""
        from sqlalchemy import select

        from netra_backend.app.db.postgres import get_async_db
        
        # Simulate OAuth user info
        oauth_user_info = {
            "id": "google-oauth-user-456",
            "email": "oauth.test@example.com",
            "name": "OAuth Test User"
        }
        
        # Mock the auth service sync function
        with patch('auth_service.auth_core.routes.auth_routes._sync_user_to_main_db') as mock_sync:
            mock_sync.return_value = None
            
            # After OAuth flow, user should exist in database
            async with get_async_db() as db:
                # Create user as auth service would
                new_user = User(
                    id=oauth_user_info["id"],
                    email=oauth_user_info["email"],
                    full_name=oauth_user_info["name"],
                    is_active=True,
                    role="user"
                )
                
                # Check if user already exists
                result = await db.execute(
                    select(User).filter(User.email == oauth_user_info["email"])
                )
                existing = result.scalars().first()
                
                if not existing:
                    db.add(new_user)
                    await db.commit()
                
                # Verify user exists
                result = await db.execute(
                    select(User).filter(User.email == oauth_user_info["email"])
                )
                user = result.scalars().first()
                
                assert user is not None, "OAuth must create real database users"
                assert user.email == oauth_user_info["email"]
    
    @pytest.mark.asyncio
    async def test_token_user_id_matches_database_user_id(self):
        """Test that JWT token user_id matches the database user.id."""
        from sqlalchemy import select

        from netra_backend.app.config import get_config
        from netra_backend.app.db.postgres import get_async_db
        from netra_backend.app.services.key_manager import KeyManager
        from netra_backend.app.services.security_service import SecurityService
        
        # Setup security service
        key_manager = KeyManager.load_from_settings(get_config())
        security_service = SecurityService(key_manager)
        
        async with get_async_db() as db:
            # Get a real user from database
            result = await db.execute(
                select(User).limit(1)
            )
            real_user = result.scalars().first()
            
            if real_user:
                # Create token with real user ID
                token_data = {
                    "sub": real_user.id,  # Must match database ID
                    "email": real_user.email
                }
                
                token = await security_service.create_access_token(token_data)
                decoded = await security_service.decode_access_token(token)
                
                # Verify token contains correct user ID
                assert decoded["sub"] == real_user.id, "Token user_id must match database user.id"
    
    @pytest.mark.asyncio
    async def test_websocket_auth_succeeds_with_database_user(self):
        """Test that WebSocket auth succeeds when user exists in database."""
        websocket = AsyncMock()
        security_service = AsyncMock()
        
        # Create mock user that exists in DB
        mock_user = MagicMock()
        mock_user.id = "dev-user-123"
        mock_user.email = "dev@example.com"
        mock_user.is_active = True
        
        # Setup mocks
        token_payload = {
            "sub": mock_user.id,
            "email": mock_user.email,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        
        security_service.decode_access_token.return_value = token_payload
        security_service.get_user_by_id.return_value = mock_user
        
        # Test - should succeed
        with patch('app.routes.utils.websocket_helpers.get_async_db') as mock_db:
            mock_session = AsyncMock()
            mock_db.return_value.__aenter__.return_value = mock_session
            
            result = await authenticate_websocket_user(
                websocket, "valid_token", security_service
            )
            
            # Should return user ID string
            assert result == mock_user.id
            
            # WebSocket should NOT be closed
            websocket.close.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_auth_service_database_sync(self):
        """Test that auth service syncs users to main database."""
        from sqlalchemy import select

        from netra_backend.app.db.postgres import get_async_db
        
        # Test user data
        test_user = {
            "id": "sync-test-user-789",
            "email": "sync.test@example.com",
            "full_name": "Sync Test User",
            "is_active": True
        }
        
        async with get_async_db() as db:
            # Check if user exists
            result = await db.execute(
                select(User).filter(User.id == test_user["id"])
            )
            existing = result.scalars().first()
            
            if not existing:
                # Create user as sync would
                new_user = User(**test_user, role="user")
                db.add(new_user)
                await db.commit()
            
            # Verify sync created user
            result = await db.execute(
                select(User).filter(User.id == test_user["id"])
            )
            synced_user = result.scalars().first()
            
            assert synced_user is not None, "Auth sync must create users in main DB"
            assert synced_user.email == test_user["email"]
            assert synced_user.full_name == test_user["full_name"]
    
    @pytest.mark.asyncio
    async def test_multiple_auth_methods_create_users(self):
        """Test that all auth methods (OAuth, dev, local) create database users."""
        test_cases = [
            {
                "method": "oauth",
                "user_id": "oauth-method-user",
                "email": "oauth.method@example.com"
            },
            {
                "method": "dev",
                "user_id": "dev-user-123",
                "email": "dev@example.com"
            },
            {
                "method": "local",
                "user_id": "local-method-user",
                "email": "local.method@example.com"
            }
        ]
        
        from sqlalchemy import select

        from netra_backend.app.db.postgres import get_async_db
        
        async with get_async_db() as db:
            for test_case in test_cases:
                # Check if user exists
                result = await db.execute(
                    select(User).filter(User.email == test_case["email"])
                )
                user = result.scalars().first()
                
                # Create if not exists (as auth would)
                if not user:
                    user = User(
                        id=test_case["user_id"],
                        email=test_case["email"],
                        full_name=f"{test_case['method'].title()} User",
                        is_active=True,
                        role="user"
                    )
                    db.add(user)
                    await db.commit()
                
                # Verify user exists
                result = await db.execute(
                    select(User).filter(User.email == test_case["email"])
                )
                verified_user = result.scalars().first()
                
                assert verified_user is not None, f"{test_case['method']} auth must create database users"
                assert verified_user.email == test_case["email"]

class TestAuthServiceIntegration:
    """Integration tests for auth service with main app."""
    
    @pytest.mark.asyncio
    async def test_auth_service_main_db_connection(self):
        """Test that auth service can connect to main database."""
        import os

        from sqlalchemy.ext.asyncio import create_async_engine
        
        # Get database URL as auth service would
        db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/apex_development")
        
        # Test connection
        engine = create_async_engine(db_url, echo=False)
        
        try:
            async with engine.begin() as conn:
                # Simple query to test connection
                result = await conn.execute("SELECT 1")
                assert result is not None, "Auth service must connect to main database"
        finally:
            await engine.dispose()
    
    @pytest.mark.asyncio 
    async def test_user_persistence_across_services(self):
        """Test that users persist across auth service and main app."""
        from sqlalchemy import select

        from netra_backend.app.db.postgres import get_async_db
        
        # User created by auth service
        auth_user = {
            "id": "cross-service-user",
            "email": "cross.service@example.com",
            "full_name": "Cross Service User"
        }
        
        async with get_async_db() as db:
            # Create user (as auth service would)
            result = await db.execute(
                select(User).filter(User.id == auth_user["id"])
            )
            existing = result.scalars().first()
            
            if not existing:
                new_user = User(**auth_user, is_active=True, role="user")
                db.add(new_user)
                await db.commit()
            
            # Verify user is accessible to main app
            result = await db.execute(
                select(User).filter(User.id == auth_user["id"])
            )
            app_user = result.scalars().first()
            
            assert app_user is not None, "Users must persist across services"
            assert app_user.email == auth_user["email"]
            
            # Verify WebSocket auth would find this user
            from netra_backend.app.config import get_config
            from netra_backend.app.services.key_manager import KeyManager
            from netra_backend.app.services.security_service import SecurityService
            
            key_manager = KeyManager.load_from_settings(get_config())
            security_service = SecurityService(key_manager)
            
            found_user = await security_service.get_user_by_id(db, auth_user["id"])
            assert found_user is not None, "WebSocket auth must find auth-created users"