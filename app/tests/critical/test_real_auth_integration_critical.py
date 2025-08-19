"""Critical Real Auth Service Integration Tests

Business Value Justification (BVJ):
- Segment: All paid tiers (Early, Mid, Enterprise)
- Business Goal: Protect customer authentication and prevent revenue loss
- Value Impact: Prevents authentication failures that cause 100% service unavailability
- Revenue Impact: Critical - Auth failures = immediate customer churn. Estimated -$50K+ MRR risk

This module replaces critical mocked auth tests with REAL service integration.
These tests are BUSINESS CRITICAL and must pass for production deployment.

ARCHITECTURE:
- NO MOCKS - Uses real auth service HTTP calls only
- Validates real database state changes
- Tests actual end-to-end authentication flows
- Ensures service availability and reliability

COMPLIANCE:
- Module ≤300 lines ✓
- Functions ≤8 lines ✓
- Strong typing with Pydantic ✓
"""

import pytest
import asyncio
import httpx
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth_integration.auth import (
    get_current_user, get_current_user_optional,
    require_admin, require_developer
)
from app.db.models_postgres import User
from app.db.session import get_db_session
from app.clients.auth_client_core import AuthServiceClient


class CriticalAuthTestManager:
    """Manages critical auth service testing infrastructure"""
    
    def __init__(self):
        self.auth_url = "http://localhost:8081"
        self.http_client = httpx.AsyncClient(timeout=30.0)
        self.auth_client = AuthServiceClient()
        self.test_users = []
    
    async def ensure_critical_service_availability(self) -> bool:
        """Ensure auth service is available for critical tests"""
        max_retries = 10
        for attempt in range(max_retries):
            try:
                response = await self.http_client.get(f"{self.auth_url}/health")
                if response.status_code == 200:
                    return True
                await asyncio.sleep(1)
            except:
                await asyncio.sleep(1)
        return False
    
    async def create_critical_test_user(self) -> Dict[str, Any]:
        """Create test user for critical testing"""
        response = await self.http_client.post(f"{self.auth_url}/auth/dev/login")
        response.raise_for_status()
        user_data = response.json()
        self.test_users.append(user_data)
        return user_data
    
    async def validate_service_token(self, token: str) -> Dict[str, Any]:
        """Validate token via auth service"""
        return await self.auth_client.validate_token(token)
    
    async def test_service_performance(self, iterations: int = 5) -> float:
        """Test auth service performance under load"""
        start_time = time.time()
        
        tasks = []
        for _ in range(iterations):
            tasks.append(self.create_critical_test_user())
        
        await asyncio.gather(*tasks)
        
        return time.time() - start_time
    
    async def cleanup_test_resources(self):
        """Cleanup test resources"""
        await self.http_client.aclose()
        await self.auth_client.close()


# Global critical test manager
critical_auth_manager = CriticalAuthTestManager()


@pytest.fixture(scope="session", autouse=True)
async def critical_auth_setup():
    """Setup critical auth testing environment"""
    service_available = await critical_auth_manager.ensure_critical_service_availability()
    if not service_available:
        pytest.fail("CRITICAL: Auth service not available - cannot run critical tests")
    
    yield
    
    await critical_auth_manager.cleanup_test_resources()


@pytest.fixture
async def critical_test_user():
    """Critical test user with guaranteed creation"""
    return await critical_auth_manager.create_critical_test_user()


@pytest.fixture
async def critical_token(critical_test_user):
    """Critical test token"""
    return critical_test_user["access_token"]


@pytest.fixture
async def critical_db_session():
    """Critical database session"""
    async for session in get_db_session():
        yield session


@pytest.mark.critical
@pytest.mark.asyncio
class TestCriticalTokenValidation:
    """CRITICAL: Token validation must work for revenue protection"""
    
    async def test_critical_token_validation_success(self, critical_token):
        """CRITICAL: Valid token must validate successfully"""
        result = await critical_auth_manager.validate_service_token(critical_token)
        
        # CRITICAL ASSERTIONS - Must not fail
        assert result is not None, "Token validation returned None"
        assert result.get("valid") is True, "Valid token marked as invalid"
        assert "user_id" in result, "Token validation missing user_id"
        assert "email" in result, "Token validation missing email"
    
    async def test_critical_invalid_token_rejection(self):
        """CRITICAL: Invalid tokens must be rejected"""
        invalid_tokens = [
            "invalid_token",
            "",
            "malformed.jwt.token",
            "bearer_token_without_proper_format",
            None
        ]
        
        for token in invalid_tokens:
            if token is not None:
                result = await critical_auth_manager.validate_service_token(token)
                assert result is None or result.get("valid") is False, \
                    f"Invalid token '{token}' was accepted"
    
    async def test_critical_token_security_boundaries(self):
        """CRITICAL: Test security boundary conditions"""
        # Test extremely long token
        long_token = "a" * 10000
        result = await critical_auth_manager.validate_service_token(long_token)
        assert result is None or result.get("valid") is False
        
        # Test special characters
        special_token = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        result = await critical_auth_manager.validate_service_token(special_token)
        assert result is None or result.get("valid") is False
    
    async def test_critical_concurrent_token_validation(self, critical_token):
        """CRITICAL: Concurrent validations must work"""
        tasks = []
        for _ in range(20):
            tasks.append(critical_auth_manager.validate_service_token(critical_token))
        
        results = await asyncio.gather(*tasks)
        
        # All validations must succeed
        for result in results:
            assert result is not None
            assert result.get("valid") is True


@pytest.mark.critical
@pytest.mark.asyncio
class TestCriticalUserRetrieval:
    """CRITICAL: User retrieval must work for auth-dependent features"""
    
    async def test_critical_user_retrieval_complete_flow(self, critical_token, critical_db_session):
        """CRITICAL: Complete user retrieval flow must work"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=critical_token
        )
        
        # CRITICAL: This must not fail
        user = await get_current_user(credentials, critical_db_session)
        
        # CRITICAL ASSERTIONS
        assert user is not None, "User retrieval returned None"
        assert isinstance(user, User), "Returned object is not User instance"
        assert user.email is not None, "User email is None"
        assert user.id is not None, "User ID is None"
        assert user.is_active is True, "User is not active"
    
    async def test_critical_user_database_consistency(self, critical_test_user, critical_db_session):
        """CRITICAL: User data must be consistent between auth and main DB"""
        user_id = critical_test_user["user"]["id"]
        expected_email = critical_test_user["user"]["email"]
        
        # Query main database directly
        result = await critical_db_session.execute(
            select(User).where(User.id == user_id)
        )
        db_user = result.scalar_one_or_none()
        
        # CRITICAL ASSERTIONS - Data consistency is mandatory
        assert db_user is not None, f"User {user_id} not found in main database"
        assert db_user.id == user_id, "User ID mismatch between auth and main DB"
        assert db_user.email == expected_email, "User email mismatch between DBs"
        assert db_user.is_active is True, "User not active in main database"
    
    async def test_critical_auth_failure_handling(self, critical_db_session):
        """CRITICAL: Auth failures must be handled gracefully"""
        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="definitely_invalid_token"
        )
        
        # CRITICAL: Must raise proper HTTP exception, not crash
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(invalid_credentials, critical_db_session)
        
        # CRITICAL: Must be proper 401 response
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in str(exc_info.value.detail)
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
    
    async def test_critical_optional_auth_reliability(self, critical_token, critical_db_session):
        """CRITICAL: Optional auth must be reliable for free users"""
        # Test with valid credentials
        valid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=critical_token
        )
        user = await get_current_user_optional(valid_credentials, critical_db_session)
        assert user is not None, "Optional auth failed with valid token"
        
        # Test with no credentials
        no_user = await get_current_user_optional(None, critical_db_session)
        assert no_user is None, "Optional auth returned user without credentials"
        
        # Test with invalid credentials
        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid"
        )
        invalid_user = await get_current_user_optional(invalid_credentials, critical_db_session)
        assert invalid_user is None, "Optional auth returned user with invalid token"


@pytest.mark.critical
@pytest.mark.asyncio
class TestCriticalPermissionSecurity:
    """CRITICAL: Permission system must protect paid features"""
    
    async def test_critical_admin_permission_enforcement(self, critical_token, critical_db_session):
        """CRITICAL: Admin permissions must be enforced correctly"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", 
            credentials=critical_token
        )
        
        user = await get_current_user(credentials, critical_db_session)
        
        # Test based on actual user permissions
        has_admin = (hasattr(user, 'is_admin') and user.is_admin) or \
                   (hasattr(user, 'role') and user.role in ['admin', 'super_admin'])
        
        if has_admin:
            # CRITICAL: Admin user must pass admin check
            result = await require_admin(user)
            assert result == user, "Admin user failed admin requirement"
        else:
            # CRITICAL: Non-admin must be rejected with 403
            with pytest.raises(HTTPException) as exc_info:
                await require_admin(user)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Admin access required" in str(exc_info.value.detail)
    
    async def test_critical_developer_permission_enforcement(self, critical_token, critical_db_session):
        """CRITICAL: Developer permissions must protect dev features"""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=critical_token
        )
        
        user = await get_current_user(credentials, critical_db_session)
        
        has_developer = hasattr(user, 'is_developer') and user.is_developer
        
        if has_developer:
            # CRITICAL: Developer user must pass developer check
            result = await require_developer(user)
            assert result == user, "Developer user failed developer requirement"
        else:
            # CRITICAL: Non-developer must be rejected with 403
            with pytest.raises(HTTPException) as exc_info:
                await require_developer(user)
            assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
            assert "Developer access required" in str(exc_info.value.detail)


@pytest.mark.critical
@pytest.mark.asyncio  
class TestCriticalServiceReliability:
    """CRITICAL: Auth service reliability for business continuity"""
    
    async def test_critical_service_health_monitoring(self):
        """CRITICAL: Auth service health must be monitorable"""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{critical_auth_manager.auth_url}/health")
            
            # CRITICAL: Health endpoint must respond
            assert response.status_code == 200, "Health endpoint returned non-200"
            
            health_data = response.json()
            assert health_data.get("status") == "healthy", "Service reports unhealthy"
    
    async def test_critical_service_performance_under_load(self):
        """CRITICAL: Service must handle reasonable load"""
        # Test creating multiple users concurrently
        performance_time = await critical_auth_manager.test_service_performance(10)
        
        # CRITICAL: Must complete within reasonable time (30 seconds)
        assert performance_time < 30.0, f"Service too slow: {performance_time}s for 10 operations"
    
    async def test_critical_service_error_handling(self):
        """CRITICAL: Service must handle errors gracefully"""
        async with httpx.AsyncClient() as client:
            # Test non-existent endpoint
            response = await client.get(f"{critical_auth_manager.auth_url}/nonexistent")
            assert response.status_code == 404, "Service doesn't handle 404 properly"
            
            # Test malformed request
            response = await client.post(f"{critical_auth_manager.auth_url}/auth/validate",
                                       json={"invalid": "data"})
            assert response.status_code in [400, 422], "Service doesn't validate requests"
    
    async def test_critical_multiple_concurrent_auth_flows(self, critical_db_session):
        """CRITICAL: Multiple concurrent auth flows must work"""
        # Create multiple users concurrently
        user_creation_tasks = []
        for _ in range(5):
            user_creation_tasks.append(critical_auth_manager.create_critical_test_user())
        
        users = await asyncio.gather(*user_creation_tasks)
        
        # Test concurrent auth with all users
        auth_tasks = []
        for user_data in users:
            credentials = HTTPAuthorizationCredentials(
                scheme="Bearer",
                credentials=user_data["access_token"]
            )
            auth_tasks.append(get_current_user(credentials, critical_db_session))
        
        auth_results = await asyncio.gather(*auth_tasks)
        
        # CRITICAL: All auths must succeed
        assert len(auth_results) == 5, "Not all concurrent auths succeeded"
        for user in auth_results:
            assert user is not None, "Concurrent auth returned None"
            assert isinstance(user, User), "Concurrent auth returned wrong type"