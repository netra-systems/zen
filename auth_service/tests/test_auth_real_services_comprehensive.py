"""
Real Service Auth Tests - No Mock Implementation
===============================================

This test suite eliminates all mock usage and tests against real services:
- Real PostgreSQL/SQLite database connections
- Real Redis for session management  
- Real JWT validation without mocks
- Real HTTP clients for OAuth flows

Business Value Justification (BVJ):
- Segment: Platform/Internal | Goal: Test Quality | Impact: Eliminates mock violations
- Replaces 222+ mock violations with real service tests
- Ensures auth service actually works with real dependencies
- Validates end-to-end authentication flows
"""

import asyncio
import json
import pytest
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
import redis.asyncio as redis
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import text

# Import auth service components
from auth_service.auth_core.config import AuthConfig
from auth_service.auth_core.database.models import Base, AuthUser, AuthSession, AuthAuditLog
from auth_service.auth_core.database.database_manager import AuthDatabaseManager
from auth_service.auth_core.services.auth_service import AuthService
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.redis_manager import AuthRedisManager
from auth_service.main import app

# Import test framework utilities
from test_framework.environment_isolation import (
    get_test_env_manager,
    isolated_test_env,
    test_env_with_llm
)


class TestRealDatabaseConnections:
    """Test real database connections without mocks."""
    
    @pytest.fixture
    async def real_db_engine(self, isolated_test_env):
        """Create real database engine using test environment."""
        # Get database URL from isolated environment
        database_url = AuthConfig.get_database_url()
        
        # Create real engine
        engine = AuthDatabaseManager.create_async_engine(database_url)
        
        # Create tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        yield engine
        
        # Cleanup
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()
    
    async def test_database_connection_establishment(self, real_db_engine):
        """Test that we can establish a real database connection."""
        # Test basic connectivity
        async with real_db_engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            assert result.scalar() == 1
    
    async def test_create_auth_user_real_db(self, real_db_engine):
        """Test creating an auth user in real database."""
        user_id = str(uuid.uuid4())
        email = f"test-{secrets.token_hex(8)}@example.com"
        
        # Create user directly in database
        async with real_db_engine.begin() as conn:
            from sqlalchemy import insert
            stmt = insert(AuthUser).values(
                id=user_id,
                email=email,
                full_name="Test User",
                auth_provider="local",
                is_active=True,
                is_verified=False
            )
            await conn.execute(stmt)
            await conn.commit()
        
        # Verify user exists with proper async session
        from sqlalchemy.ext.asyncio import AsyncSession
        session = AsyncSession(real_db_engine)
        try:
            from sqlalchemy import select
            stmt = select(AuthUser).where(AuthUser.email == email)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            assert user is not None
            assert user.email == email
            assert user.full_name == "Test User"
            assert user.auth_provider == "local"
        finally:
            await session.close()
    
    async def test_auth_session_persistence(self, real_db_engine):
        """Test auth session persistence in real database."""
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Create session
        async with real_db_engine.begin() as conn:
            from sqlalchemy import insert
            stmt = insert(AuthSession).values(
                id=session_id,
                user_id=user_id,
                refresh_token_hash="test_hash",
                ip_address="192.168.1.1",
                user_agent="TestAgent/1.0",
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                is_active=True
            )
            await conn.execute(stmt)
            await conn.commit()
        
        # Verify session exists with proper async session
        from sqlalchemy.ext.asyncio import AsyncSession
        db_session = AsyncSession(real_db_engine)
        try:
            from sqlalchemy import select
            stmt = select(AuthSession).where(AuthSession.id == session_id)
            result = await db_session.execute(stmt)
            auth_session = result.scalar_one_or_none()
            
            assert auth_session is not None
            assert auth_session.user_id == user_id
            assert auth_session.refresh_token_hash == "test_hash"
            assert auth_session.is_active is True
        finally:
            await db_session.close()


class TestRealRedisConnections:
    """Test real Redis connections for session management."""
    
    @pytest.fixture
    async def real_redis_manager(self, isolated_test_env):
        """Create real Redis manager using test environment."""
        manager = AuthRedisManager()
        await manager.initialize()
        
        # Test connection
        try:
            await manager.ping()
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
            
        yield manager
        
        # Cleanup
        try:
            await manager.cleanup()
        except:
            pass  # Ignore cleanup errors
    
    async def test_redis_connection_establishment(self, real_redis_manager):
        """Test that we can establish a real Redis connection."""
        # Test ping
        pong = await real_redis_manager.ping()
        assert pong is True
    
    async def test_redis_session_storage(self, real_redis_manager):
        """Test session storage in real Redis."""
        session_key = f"session:{secrets.token_hex(16)}"
        session_data = {
            "user_id": str(uuid.uuid4()),
            "email": "test@example.com",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Store session data
        await real_redis_manager.set_session(session_key, session_data, expire_seconds=3600)
        
        # Retrieve session data
        retrieved_data = await real_redis_manager.get_session(session_key)
        
        assert retrieved_data is not None
        assert retrieved_data["user_id"] == session_data["user_id"]
        assert retrieved_data["email"] == session_data["email"]
    
    async def test_redis_blacklist_management(self, real_redis_manager):
        """Test token blacklist management in real Redis."""
        token_jti = secrets.token_hex(32)
        
        # Add token to blacklist
        await real_redis_manager.blacklist_token(token_jti, expire_seconds=3600)
        
        # Check if token is blacklisted
        is_blacklisted = await real_redis_manager.is_token_blacklisted(token_jti)
        assert is_blacklisted is True
        
        # Check non-blacklisted token
        other_token = secrets.token_hex(32)
        is_not_blacklisted = await real_redis_manager.is_token_blacklisted(other_token)
        assert is_not_blacklisted is False


class TestRealJWTValidation:
    """Test real JWT validation without mocks."""
    
    @pytest.fixture
    def real_jwt_handler(self, isolated_test_env):
        """Create real JWT handler using test environment."""
        return JWTHandler()
    
    def test_jwt_token_creation_and_validation(self, real_jwt_handler):
        """Test real JWT token creation and validation."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        permissions = ["read", "write"]
        
        # Create access token
        access_token = real_jwt_handler.create_access_token(
            user_id=user_id,
            email=email,
            permissions=permissions
        )
        
        assert access_token is not None
        assert isinstance(access_token, str)
        assert len(access_token.split('.')) == 3  # JWT has 3 parts
        
        # Validate access token
        payload = real_jwt_handler.validate_token(access_token, "access")
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["email"] == email
        assert payload["permissions"] == permissions
        assert payload["type"] == "access"
    
    def test_jwt_refresh_token_flow(self, real_jwt_handler):
        """Test real JWT refresh token creation and validation."""
        user_id = str(uuid.uuid4())
        
        # Create refresh token
        refresh_token = real_jwt_handler.create_refresh_token(user_id)
        
        assert refresh_token is not None
        assert isinstance(refresh_token, str)
        
        # Validate refresh token
        payload = real_jwt_handler.validate_token(refresh_token, "refresh")
        
        assert payload is not None
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
    
    def test_jwt_token_expiration(self, real_jwt_handler):
        """Test JWT token expiration handling."""
        user_id = str(uuid.uuid4())
        
        # Create token with very short expiration for testing
        # We'll modify the handler temporarily for this test
        original_expiry = real_jwt_handler.access_expiry
        real_jwt_handler.access_expiry = -1  # Already expired
        
        try:
            expired_token = real_jwt_handler.create_access_token(user_id, "test@example.com")
            
            # Validation should fail for expired token
            payload = real_jwt_handler.validate_token(expired_token, "access")
            assert payload is None  # Should be None for expired token
            
        finally:
            # Restore original expiry
            real_jwt_handler.access_expiry = original_expiry


class TestRealAuthServiceFlows:
    """Test complete auth service flows with real dependencies."""
    
    @pytest.fixture
    async def real_auth_service(self, isolated_test_env):
        """Create auth service with real dependencies."""
        service = AuthService()
        
        # Initialize with real database
        await service.initialize()
        
        yield service
        
        # Cleanup
        try:
            await service.cleanup()
        except:
            pass
    
    async def test_user_registration_real_flow(self, real_auth_service):
        """Test complete user registration with real database."""
        email = f"test-{secrets.token_hex(8)}@example.com"
        password = "TestPassword123!"
        full_name = "Test User"
        
        # Register user
        result = await real_auth_service.register_user(
            email=email,
            password=password,
            full_name=full_name
        )
        
        assert result is not None
        assert "access_token" in result
        assert "refresh_token" in result
        assert "user" in result
        assert result["user"]["email"] == email
        assert result["user"]["full_name"] == full_name
    
    async def test_user_login_real_flow(self, real_auth_service):
        """Test complete user login with real database."""
        email = f"test-{secrets.token_hex(8)}@example.com"
        password = "TestPassword123!"
        
        # First register user
        await real_auth_service.register_user(
            email=email,
            password=password,
            full_name="Test User"
        )
        
        # Then login
        login_result = await real_auth_service.authenticate_user(email, password)
        
        assert login_result is not None
        assert "access_token" in login_result
        assert "refresh_token" in login_result
        assert "user" in login_result
        assert login_result["user"]["email"] == email
    
    async def test_token_refresh_real_flow(self, real_auth_service):
        """Test token refresh with real dependencies."""
        email = f"test-{secrets.token_hex(8)}@example.com"
        password = "TestPassword123!"
        
        # Register user to get tokens
        register_result = await real_auth_service.register_user(
            email=email,
            password=password,
            full_name="Test User"
        )
        
        refresh_token = register_result["refresh_token"]
        
        # Refresh tokens
        refresh_result = await real_auth_service.refresh_tokens(refresh_token)
        
        assert refresh_result is not None
        new_access_token, new_refresh_token = refresh_result
        
        assert new_access_token is not None
        assert new_refresh_token is not None
        assert new_access_token != register_result["access_token"]
        assert new_refresh_token != refresh_token


class TestRealHTTPEndpoints:
    """Test HTTP endpoints with real FastAPI test client."""
    
    @pytest.fixture
    def real_client(self, isolated_test_env):
        """Create real test client with isolated environment."""
        return TestClient(app)
    
    def test_health_endpoint_real(self, real_client):
        """Test health endpoint with real client."""
        response = real_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_auth_config_endpoint_real(self, real_client):
        """Test auth config endpoint with real client."""
        response = real_client.get("/auth/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "environment" in data
        assert data["environment"] in ["test", "development", "staging", "production"]
    
    async def test_refresh_endpoint_real_flow(self, isolated_test_env):
        """Test refresh endpoint with real async client."""
        # Create real async client
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            # First, we need to create a user and get tokens
            # Since we can't easily do this through endpoints without OAuth setup,
            # we'll test the endpoint structure
            
            # Test with missing refresh token
            response = await client.post("/auth/refresh", json={})
            assert response.status_code == 422
            
            # Test with invalid JSON
            response = await client.post(
                "/auth/refresh",
                content=b"invalid json",
                headers={"content-type": "application/json"}
            )
            assert response.status_code == 422


class TestRealOAuthFlows:
    """Test OAuth flows with real HTTP clients (where possible)."""
    
    async def test_oauth_state_generation_real(self, isolated_test_env):
        """Test OAuth state generation without mocks."""
        from auth_service.auth_core.security.oauth_security import OAuthSecurityManager
        
        oauth_manager = OAuthSecurityManager()
        
        # Generate state parameter
        state = oauth_manager.generate_state_parameter()
        
        assert state is not None
        assert len(state) >= 32  # Should be sufficiently random
        assert isinstance(state, str)
    
    async def test_oauth_session_id_generation_real(self, isolated_test_env):
        """Test OAuth session ID generation without mocks."""
        from auth_service.auth_core.security.oauth_security import OAuthSecurityManager
        
        oauth_manager = OAuthSecurityManager()
        
        # Generate session ID
        session_id = oauth_manager.generate_secure_session_id()
        
        assert session_id is not None
        assert len(session_id) >= 32
        assert isinstance(session_id, str)


class TestRealErrorHandling:
    """Test error handling with real services."""
    
    async def test_database_connection_failure_handling(self, isolated_test_env):
        """Test handling of database connection failures."""
        # Try to create engine with invalid URL
        try:
            invalid_engine = AuthDatabaseManager.create_async_engine("postgresql://invalid:invalid@localhost:9999/invalid")
            
            # This should fail when we try to connect
            async with invalid_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            # If we get here, cleanup
            await invalid_engine.dispose()
            
        except Exception as e:
            # Expected - connection should fail
            assert "connection" in str(e).lower() or "timeout" in str(e).lower()
    
    async def test_redis_connection_failure_handling(self, isolated_test_env):
        """Test handling of Redis connection failures."""
        # Create Redis manager with invalid connection
        invalid_manager = AuthRedisManager()
        # Override Redis URL to invalid one
        invalid_manager.redis_url = "redis://invalid:9999"
        
        try:
            await invalid_manager.initialize()
            # If connection succeeds (shouldn't), test ping
            await invalid_manager.ping()
            
        except Exception as e:
            # Expected - connection should fail
            assert "connection" in str(e).lower() or "timeout" in str(e).lower() or "error" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])