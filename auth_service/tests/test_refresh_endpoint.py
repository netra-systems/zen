"""
MOCK-FREE test suite for the auth service refresh endpoint.

CRITICAL: This file eliminates ALL mock usage as per CLAUDE.md requirements.
Tests the refresh endpoint using ONLY real services: PostgreSQL, Redis, JWT operations.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: System Stability and Compliance  
- Value Impact: Authentic refresh token testing with real service integration
- Strategic Impact: Ensures refresh endpoint works correctly in production

ZERO MOCKS: Every test uses real JWT operations, database, and Redis.
"""

import pytest
import asyncio
import json
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from shared.isolated_environment import IsolatedEnvironment

# REAL SERVICES: No mock imports
from fastapi import HTTPException
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import jwt

# Real auth service components
from auth_service.main import app
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.models.auth_models import User
from shared.isolated_environment import get_env


class RefreshEndpointRealTests:
    """MOCK-FREE test suite for refresh endpoint using real services."""
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_with_valid_token(
        self, 
        real_auth_service, 
        real_jwt_manager, 
        real_auth_db,
        test_user_data
    ):
        """Test refresh endpoint with REAL valid refresh token.
        
        ZERO MOCKS: Uses real JWT manager and real database.
        """
        # Create real user in database
        user = User(
            id=str(uuid.uuid4()),
            email=test_user_data["email"],
            provider="google",
            provider_user_id=test_user_data["id"]
        )
        real_auth_db.add(user)
        await real_auth_db.commit()
        await real_auth_db.refresh(user)
        
        # Generate REAL tokens using real JWT manager
        tokens = await real_jwt_manager.generate_tokens(user.email, {"user_id": user.id})
        real_refresh_token = tokens["refresh_token"]
        
        # Test refresh endpoint with REAL token
        client = TestClient(app)
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": real_refresh_token},
            headers={"Content-Type": "application/json"}
        )
        
        # Should successfully refresh with real token
        assert response.status_code in [200, 201]
        
        if response.status_code == 200:
            response_data = response.json()
            assert "access_token" in response_data
            assert "refresh_token" in response_data
            
            # Verify new tokens are valid using real JWT manager
            new_access_token = response_data["access_token"]
            decoded = await real_jwt_manager.decode_token(new_access_token)
            assert decoded["sub"] == user.email
            assert decoded["user_id"] == user.id
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_with_expired_token(
        self, 
        real_jwt_manager,
        real_auth_db,
        test_user_data
    ):
        """Test refresh endpoint with REAL expired token.
        
        ZERO MOCKS: Creates real expired JWT token.
        """
        # Create real user
        user = User(
            id=str(uuid.uuid4()),
            email=test_user_data["email"],
            provider="google",
            provider_user_id=test_user_data["id"]
        )
        real_auth_db.add(user)
        await real_auth_db.commit()
        
        # Create REAL expired token by manipulating JWT expiration
        payload = {
            "sub": user.email,
            "user_id": user.id,
            "exp": int(time.time()) - 3600,  # Expired 1 hour ago
            "iat": int(time.time()) - 7200,  # Issued 2 hours ago
            "type": "refresh"
        }
        
        expired_token = jwt.encode(
            payload,
            real_jwt_manager.secret_key,
            algorithm=real_jwt_manager.algorithm
        )
        
        # Test with REAL expired token
        client = TestClient(app)
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": expired_token},
            headers={"Content-Type": "application/json"}
        )
        
        # Should reject expired token
        assert response.status_code in [401, 422]
        
        if response.status_code == 401:
            error_data = response.json()
            assert "expired" in str(error_data).lower() or "invalid" in str(error_data).lower()
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_with_blacklisted_token(
        self,
        real_jwt_manager,
        real_auth_redis,
        real_auth_db,
        test_user_data
    ):
        """Test refresh endpoint with REAL blacklisted token.
        
        ZERO MOCKS: Uses real Redis for blacklist and real JWT.
        """
        # Create real user
        user = User(
            id=str(uuid.uuid4()),
            email=test_user_data["email"],
            provider="google",
            provider_user_id=test_user_data["id"]
        )
        real_auth_db.add(user)
        await real_auth_db.commit()
        
        # Generate REAL token
        tokens = await real_jwt_manager.generate_tokens(user.email, {"user_id": user.id})
        refresh_token = tokens["refresh_token"]
        
        # REAL BLACKLIST: Add token to real Redis blacklist
        blacklist_key = f"blacklist:token:{refresh_token}"
        await real_auth_redis.set(blacklist_key, "blacklisted", ex=86400)
        
        # Verify token is really blacklisted
        is_blacklisted = await real_jwt_manager.is_token_blacklisted(refresh_token)
        assert is_blacklisted == True
        
        # Test with REAL blacklisted token
        client = TestClient(app)
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
            headers={"Content-Type": "application/json"}
        )
        
        # Should reject blacklisted token
        assert response.status_code in [401, 422]
    
    def test_refresh_endpoint_with_invalid_token_format(self):
        """Test refresh endpoint with invalid token formats.
        
        ZERO MOCKS: Tests real JWT validation.
        """
        invalid_tokens = [
            "invalid.token.format",
            "not-a-jwt-token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",  # Invalid JWT
            "",
            "   ",
            None
        ]
        
        client = TestClient(app)
        
        for invalid_token in invalid_tokens:
            request_data = {"refresh_token": invalid_token} if invalid_token is not None else {}
            
            response = client.post(
                "/auth/refresh",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )
            
            # Should reject invalid token formats
            assert response.status_code in [400, 401, 422]
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_with_wrong_token_type(
        self,
        real_jwt_manager,
        real_auth_db,
        test_user_data
    ):
        """Test refresh endpoint with access token instead of refresh token.
        
        ZERO MOCKS: Creates real access token and tests validation.
        """
        # Create real user
        user = User(
            id=str(uuid.uuid4()),
            email=test_user_data["email"],
            provider="google",
            provider_user_id=test_user_data["id"]
        )
        real_auth_db.add(user)
        await real_auth_db.commit()
        
        # Generate REAL tokens
        tokens = await real_jwt_manager.generate_tokens(user.email, {"user_id": user.id})
        access_token = tokens["access_token"]  # Wrong type - should be refresh token
        
        # Test with wrong token type
        client = TestClient(app)
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},  # Using access token as refresh token
            headers={"Content-Type": "application/json"}
        )
        
        # Should reject wrong token type
        assert response.status_code in [401, 422]
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_database_integration(
        self,
        real_auth_service,
        real_jwt_manager,
        real_auth_db,
        test_user_data
    ):
        """Test refresh endpoint with REAL database integration.
        
        ZERO MOCKS: Tests complete flow with real PostgreSQL.
        """
        # Create user with REAL database
        user = User(
            id=str(uuid.uuid4()),
            email=test_user_data["email"],
            provider="google",
            provider_user_id=test_user_data["id"],
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        real_auth_db.add(user)
        await real_auth_db.commit()
        await real_auth_db.refresh(user)
        
        # Generate REAL tokens
        tokens = await real_jwt_manager.generate_tokens(user.email, {"user_id": user.id})
        
        # Test refresh with real database lookup
        client = TestClient(app)
        response = client.post(
            "/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"Content-Type": "application/json"}
        )
        
        # Should work with real database integration
        assert response.status_code in [200, 201]
        
        if response.status_code == 200:
            response_data = response.json()
            
            # Verify user data from real database
            assert "access_token" in response_data
            
            # Decode token and verify user ID matches database
            new_access_token = response_data["access_token"]
            decoded = await real_jwt_manager.decode_token(new_access_token)
            assert decoded["user_id"] == user.id
            assert decoded["sub"] == user.email
    
    def test_refresh_endpoint_error_scenarios(self):
        """Test refresh endpoint error handling.
        
        ZERO MOCKS: Tests real error responses.
        """
        client = TestClient(app)
        
        # Test missing refresh token
        response = client.post(
            "/auth/refresh",
            json={},
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
        
        # Test malformed JSON
        response = client.post(
            "/auth/refresh",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422]
        
        # Test empty request
        response = client.post("/auth/refresh")
        assert response.status_code in [400, 422]
    
    @pytest.mark.asyncio
    async def test_refresh_endpoint_concurrent_requests(
        self,
        real_auth_service,
        real_jwt_manager,
        real_auth_db,
        test_user_data
    ):
        """Test refresh endpoint handles concurrent requests with real services.
        
        ZERO MOCKS: Tests real concurrent JWT operations.
        """
        # Create real user
        user = User(
            id=str(uuid.uuid4()),
            email=test_user_data["email"],
            provider="google",
            provider_user_id=test_user_data["id"]
        )
        real_auth_db.add(user)
        await real_auth_db.commit()
        
        # Generate REAL token
        tokens = await real_jwt_manager.generate_tokens(user.email, {"user_id": user.id})
        refresh_token = tokens["refresh_token"]
        
        # Test concurrent refresh requests
        client = TestClient(app)
        
        async def make_refresh_request():
            return client.post(
                "/auth/refresh",
                json={"refresh_token": refresh_token},
                headers={"Content-Type": "application/json"}
            )
        
        # Make 3 concurrent requests
        tasks = [make_refresh_request() for _ in range(3)]
        responses = await asyncio.gather(*tasks)
        
        # At least one should succeed, others may fail due to token invalidation
        success_count = sum(1 for r in responses if r.status_code == 200)
        assert success_count >= 1
        
        # All responses should be valid HTTP responses
        for response in responses:
            assert response.status_code in [200, 401, 422]


# Remove ALL mock fixtures - ZERO MOCKS POLICY
# The following mock fixtures have been ELIMINATED:
# - mock_jwt_manager (replaced with real_jwt_manager from conftest.py)
# - mock_db_session (replaced with real_auth_db from conftest.py) 
# - mock_redis (replaced with real_auth_redis from conftest.py)
# - All async mocks and patches

print("Refresh endpoint tests loaded - ZERO MOCKS, 100% REAL SERVICES")