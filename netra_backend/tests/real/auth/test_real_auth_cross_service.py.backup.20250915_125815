"""
Real Cross-Service Authentication Testing

Tests authentication communication between services using real Docker services.
Validates service-to-service authentication, token propagation, and security boundaries.

Business Value: Ensures secure service communication and prevents authentication bypass attacks.
Coverage Target: 95%+ for cross-service authentication flows
"""

import pytest
import asyncio
import jwt
import time
from typing import Dict, Any, Optional
from unittest.mock import patch
import httpx
import redis.asyncio as redis
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from netra_backend.app.core.auth_constants import (
    JWT_SECRET_KEY,
    JWT_ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from shared.isolated_environment import IsolatedEnvironment
from test_framework.docker_test_manager import UnifiedDockerManager
from test_framework.helpers.auth_helpers import create_test_user_data, create_test_jwt_token
from test_framework.database_helpers import get_test_db_session
from netra_backend.app.db.models_user import User
from netra_backend.app.core.database import get_database_session


class TestRealAuthCrossService:
    """Test cross-service authentication with real services"""

    @pytest.fixture(autouse=True)
    async def setup_docker_services(self):
        """Setup Docker services for cross-service testing"""
        self.docker_manager = UnifiedDockerManager()
        await self.docker_manager.ensure_services_ready()
        
        # Get service URLs
        self.env = IsolatedEnvironment()
        self.backend_url = f"http://localhost:{self.env.get('BACKEND_PORT', '8000')}"
        self.auth_url = f"http://localhost:{self.env.get('AUTH_PORT', '8081')}"
        self.redis_url = f"redis://localhost:{self.env.get('REDIS_PORT', '6381')}"
        
        # Setup Redis client
        self.redis_client = redis.from_url(self.redis_url)
        
        yield
        
        # Cleanup
        await self.redis_client.close()
        await self.docker_manager.cleanup()

    @pytest.fixture
    async def test_user_token(self):
        """Create test user and generate valid token"""
        async with get_test_db_session() as db_session:
            user = await create_test_user(db_session, "crossservice@test.com", "CrossService User")
            token = generate_test_token(user.id)
            return {"user": user, "token": token}

    async def test_backend_to_auth_service_token_validation(self, test_user_token):
        """Test backend service validating tokens with auth service"""
        user_data = test_user_token
        token = user_data["token"]
        
        async with httpx.AsyncClient() as client:
            # Backend calls auth service to validate token
            auth_response = await client.post(
                f"{self.auth_url}/api/v1/auth/validate",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            
            assert auth_response.status_code == 200
            validated_user = auth_response.json()
            assert validated_user["user_id"] == user_data["user"].id
            assert validated_user["email"] == user_data["user"].email

    async def test_service_to_service_internal_auth(self):
        """Test internal service authentication using service keys"""
        # Generate service token for backend -> auth communication
        service_payload = {
            "service": "netra-backend",
            "iat": int(time.time()),
            "exp": int(time.time()) + 300,  # 5 minutes
            "scope": "internal"
        }
        
        service_token = jwt.encode(
            service_payload,
            self.env.get("SERVICE_JWT_SECRET", "test-service-secret"),
            algorithm="HS256"
        )
        
        async with httpx.AsyncClient() as client:
            # Use service token for internal API call
            response = await client.get(
                f"{self.auth_url}/api/v1/internal/health",
                headers={"Authorization": f"Bearer {service_token}"},
                timeout=30.0
            )
            
            assert response.status_code == 200
            health_data = response.json()
            assert health_data["service"] == "auth-service"
            assert health_data["status"] == "healthy"

    async def test_cross_service_user_session_sharing(self, test_user_token):
        """Test user session sharing between services via Redis"""
        user_data = test_user_token
        token = user_data["token"]
        
        # Create session in auth service
        async with httpx.AsyncClient() as client:
            login_response = await client.post(
                f"{self.auth_url}/api/v1/auth/session",
                headers={"Authorization": f"Bearer {token}"},
                json={"create_session": True},
                timeout=30.0
            )
            
            assert login_response.status_code == 200
            session_data = login_response.json()
            session_id = session_data["session_id"]
            
            # Verify session exists in Redis
            session_key = f"session:{session_id}"
            cached_session = await self.redis_client.get(session_key)
            assert cached_session is not None
            
            # Backend service reads session from Redis
            backend_response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers={"X-Session-ID": session_id},
                timeout=30.0
            )
            
            assert backend_response.status_code == 200
            profile_data = backend_response.json()
            assert profile_data["user_id"] == user_data["user"].id

    async def test_token_propagation_across_services(self, test_user_token):
        """Test JWT token propagation through service chain"""
        user_data = test_user_token
        token = user_data["token"]
        
        async with httpx.AsyncClient() as client:
            # Frontend -> Backend -> Auth service chain
            response = await client.post(
                f"{self.backend_url}/api/v1/auth/verify-chain",
                headers={"Authorization": f"Bearer {token}"},
                json={"validate_with_auth": True},
                timeout=30.0
            )
            
            # Should successfully validate through the chain
            assert response.status_code == 200
            chain_data = response.json()
            assert chain_data["backend_validation"] is True
            assert chain_data["auth_service_validation"] is True
            assert chain_data["user_id"] == user_data["user"].id

    async def test_cross_service_permission_enforcement(self, test_user_token):
        """Test permission enforcement across service boundaries"""
        user_data = test_user_token
        token = user_data["token"]
        
        async with httpx.AsyncClient() as client:
            # Try to access admin endpoint with regular user token
            admin_response = await client.get(
                f"{self.backend_url}/api/v1/admin/users",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            
            assert admin_response.status_code == 403
            error_data = admin_response.json()
            assert "insufficient_permissions" in error_data["detail"]
            
            # Verify permission check was validated with auth service
            assert "auth_service_verified" in error_data

    async def test_service_authentication_failure_handling(self):
        """Test handling of authentication failures between services"""
        invalid_token = "invalid.jwt.token"
        
        async with httpx.AsyncClient() as client:
            # Backend should handle auth service validation failure gracefully
            response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers={"Authorization": f"Bearer {invalid_token}"},
                timeout=30.0
            )
            
            assert response.status_code == 401
            error_data = response.json()
            assert error_data["error"] == "invalid_token"
            assert "auth_service_rejection" in error_data["details"]

    async def test_cross_service_rate_limiting_coordination(self, test_user_token):
        """Test rate limiting coordination between services"""
        user_data = test_user_token
        token = user_data["token"]
        
        async with httpx.AsyncClient() as client:
            # Make multiple requests to trigger rate limiting
            responses = []
            for i in range(15):  # Exceed typical rate limit
                response = await client.get(
                    f"{self.backend_url}/api/v1/user/profile",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                responses.append(response.status_code)
                
                if response.status_code == 429:
                    break
                    
                await asyncio.sleep(0.1)
            
            # Should eventually get rate limited
            assert 429 in responses
            
            # Verify rate limit info is shared between services
            rate_limit_key = f"rate_limit:user:{user_data['user'].id}"
            limit_data = await self.redis_client.get(rate_limit_key)
            assert limit_data is not None

    async def test_service_health_check_chain(self):
        """Test health check propagation through service dependencies"""
        async with httpx.AsyncClient() as client:
            # Backend health check should verify auth service dependency
            health_response = await client.get(
                f"{self.backend_url}/api/v1/health/detailed",
                timeout=30.0
            )
            
            assert health_response.status_code == 200
            health_data = health_response.json()
            assert health_data["status"] == "healthy"
            assert "dependencies" in health_data
            assert "auth_service" in health_data["dependencies"]
            assert health_data["dependencies"]["auth_service"]["status"] == "healthy"

    async def test_cross_service_token_refresh_coordination(self, test_user_token):
        """Test token refresh coordination between services"""
        user_data = test_user_token
        
        # Create a token that's about to expire
        near_expired_payload = {
            "user_id": user_data["user"].id,
            "email": user_data["user"].email,
            "iat": int(time.time()),
            "exp": int(time.time()) + 60,  # 1 minute expiry
        }
        
        near_expired_token = jwt.encode(
            near_expired_payload,
            self.env.get(JWT_SECRET_KEY, "test-secret"),
            algorithm=JWT_ALGORITHM
        )
        
        async with httpx.AsyncClient() as client:
            # Backend should coordinate with auth service for token refresh
            refresh_response = await client.post(
                f"{self.backend_url}/api/v1/auth/refresh",
                headers={"Authorization": f"Bearer {near_expired_token}"},
                json={"auto_refresh": True},
                timeout=30.0
            )
            
            assert refresh_response.status_code == 200
            refresh_data = refresh_response.json()
            assert "new_access_token" in refresh_data
            assert "refresh_token" in refresh_data
            
            # Verify new token works across services
            new_token = refresh_data["new_access_token"]
            profile_response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers={"Authorization": f"Bearer {new_token}"},
                timeout=30.0
            )
            
            assert profile_response.status_code == 200

    async def test_service_isolation_boundary_enforcement(self, test_user_token):
        """Test that service isolation boundaries are properly enforced"""
        user_data = test_user_token
        token = user_data["token"]
        
        async with httpx.AsyncClient() as client:
            # Try to directly access internal auth service endpoints
            internal_response = await client.get(
                f"{self.auth_url}/api/v1/internal/user-secrets",
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0
            )
            
            # Should be blocked - internal endpoints not accessible with user tokens
            assert internal_response.status_code in [403, 404]
            
            # Verify proper service boundary is maintained
            if internal_response.status_code == 403:
                error_data = internal_response.json()
                assert "service_boundary_violation" in error_data.get("detail", "")

    async def test_distributed_session_invalidation(self, test_user_token):
        """Test session invalidation propagation across services"""
        user_data = test_user_token
        token = user_data["token"]
        
        async with httpx.AsyncClient() as client:
            # Create active session across services
            session_response = await client.post(
                f"{self.auth_url}/api/v1/auth/session",
                headers={"Authorization": f"Bearer {token}"},
                json={"create_session": True},
                timeout=30.0
            )
            
            session_id = session_response.json()["session_id"]
            
            # Verify session works in backend
            profile_response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers={"X-Session-ID": session_id},
                timeout=30.0
            )
            assert profile_response.status_code == 200
            
            # Invalidate session from auth service
            logout_response = await client.post(
                f"{self.auth_url}/api/v1/auth/logout",
                headers={"X-Session-ID": session_id},
                timeout=30.0
            )
            assert logout_response.status_code == 200
            
            # Verify session is invalidated in backend
            await asyncio.sleep(1)  # Allow propagation
            invalid_response = await client.get(
                f"{self.backend_url}/api/v1/user/profile",
                headers={"X-Session-ID": session_id},
                timeout=30.0
            )
            assert invalid_response.status_code == 401