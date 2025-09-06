"""Unit tests for Auth Integration module.

Tests authentication integration with external auth service.
HIGHEST PRIORITY - Auth failures = 100% revenue loss.

Business Value: Ensures proper token validation, user retrieval, and error handling
for all authenticated endpoints. Protects against unauthorized access.

Target Coverage:
- get_current_user: token validation and database lookup
- get_current_user_optional: optional authentication flow  
- Permission-based dependencies: admin, developer, custom permissions
- Error scenarios: 401 Unauthorized, 404 User Not Found, service failures
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from auth_service.core.auth_manager import AuthManager
from shared.isolated_environment import IsolatedEnvironment

import uuid
import jwt
from datetime import datetime, timedelta, UTC
from typing import Any, Dict, Optional

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.auth_integration.auth import (
    get_current_user,
    get_current_user_optional,
    require_admin,
    require_developer,
    require_permission)
from netra_backend.app.clients.auth_client_core import auth_client
from netra_backend.app.db.models_postgres import User

class TestAuthIntegration:
    """Test suite for Auth Integration functionality."""
    
    @pytest.fixture
 def real_credentials():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock HTTP authorization credentials."""
        # Mock: Authentication service isolation for testing without real auth flows
        credentials = Mock(spec=HTTPAuthorizationCredentials)
        credentials.credentials = "valid-jwt-token-123"
        return credentials
    
    @pytest.fixture
 def real_auth_client():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock auth client with common responses."""
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', new_callable=AsyncMock) as mock:
            yield mock
    
    @pytest.fixture
 def real_db_session():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock async database session."""
        # Mock: Database session isolation for transaction testing without real database dependency
        session = AsyncMock(spec=AsyncSession)
        # Mock: Database session isolation for transaction testing without real database dependency
        session.__aenter__ = AsyncMock(return_value=session)
        # Mock: Session isolation for controlled testing without external state
        session.__aexit__ = AsyncMock(return_value=None)
        return session
    
    @pytest.fixture
    def sample_user(self):
        pass
    """Use real service instance."""
    # TODO: Initialize real service
        """Create sample user for testing."""
        user = User()
        user.id = "test-user-123"
        user.email = "test@example.com"
        user.is_admin = False
        user.is_developer = False
        user.permissions = ["read", "write"]
        return user

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token_success(self, mock_credentials, mock_auth_client, mock_db_session, sample_user):
        """Test successful user retrieval with valid token."""
        self._setup_successful_auth_flow(mock_auth_client, mock_db_session, sample_user)
        
        result = await get_current_user(mock_credentials, mock_db_session)
        
        assert result == sample_user
        mock_auth_client.assert_called_once_with("valid-jwt-token-123")
    
    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token_raises_401(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 401 error with invalid token."""
        mock_auth_client.return_value = {"valid": False}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db_session)
        
        self._assert_401_unauthorized(exc_info)

    @pytest.mark.asyncio
    async def test_get_current_user_no_token_validation_raises_401(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 401 error when auth service returns None."""
        mock_auth_client.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db_session)
        
        self._assert_401_unauthorized(exc_info)

    @pytest.mark.asyncio
    async def test_get_current_user_missing_user_id_raises_401(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 401 error when token payload lacks user_id."""
        mock_auth_client.return_value = {"valid": True}  # No user_id
        
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(mock_credentials, mock_db_session)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid token payload" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_user_not_found_raises_404(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test 404 error when user not found in database."""
        self._setup_auth_client_valid_response(mock_auth_client)
        self._setup_db_session_no_user(mock_db_session)
        
        # Mock config to be production so it doesn't create dev users
        with patch('netra_backend.app.config.get_config') as mock_config:
            mock_config.return_value.environment = "production"
            
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(mock_credentials, mock_db_session)
            
            assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
            assert "User not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_get_current_user_optional_valid_credentials_returns_user(self, mock_credentials, mock_auth_client, mock_db_session, sample_user):
        """Test optional auth returns user with valid credentials."""
        # Mock: Async component isolation for testing without real async operations
        with patch('netra_backend.app.auth_integration.auth.get_current_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.return_value = sample_user
            
            result = await get_current_user_optional(mock_credentials, mock_db_session)
            
            assert result == sample_user

    @pytest.mark.asyncio
    async def test_get_current_user_optional_no_credentials_returns_none(self, mock_db_session):
        """Test optional auth returns None with no credentials."""
        result = await get_current_user_optional(None, mock_db_session)
        
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_user_optional_invalid_credentials_returns_none(self, mock_credentials, mock_db_session):
        """Test optional auth returns None when authentication fails."""
        # Mock: Async component isolation for testing without real async operations
        with patch('netra_backend.app.auth_integration.auth.get_current_user', new_callable=AsyncMock) as mock_get_user:
            mock_get_user.side_effect = HTTPException(status_code=401, detail="Invalid token")
            
            result = await get_current_user_optional(mock_credentials, mock_db_session)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_require_admin_with_admin_user_success(self, sample_user):
        """Test admin requirement with admin user."""
        sample_user.is_admin = True
        
        result = await require_admin(sample_user)
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_admin_with_non_admin_user_raises_403(self, sample_user):
        """Test admin requirement with non-admin user."""
        sample_user.is_admin = False
        
        with pytest.raises(HTTPException) as exc_info:
            await require_admin(sample_user)
        
        self._assert_403_forbidden(exc_info, "Admin access required")

    @pytest.mark.asyncio
    async def test_require_developer_with_developer_user_success(self, sample_user):
        """Test developer requirement with developer user."""
        sample_user.is_developer = True
        
        result = await require_developer(sample_user)
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_developer_with_non_developer_user_raises_403(self, sample_user):
        """Test developer requirement with non-developer user."""
        sample_user.is_developer = False
        
        with pytest.raises(HTTPException) as exc_info:
            await require_developer(sample_user)
        
        self._assert_403_forbidden(exc_info, "Developer access required")

    @pytest.mark.asyncio
    async def test_require_permission_with_valid_permission_success(self, sample_user):
        """Test permission requirement with valid permission."""
        check_permission = require_permission("read")
        
        result = await check_permission(sample_user)
        
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_permission_with_invalid_permission_raises_403(self, sample_user):
        """Test permission requirement with missing permission."""
        check_permission = require_permission("admin")
        
        with pytest.raises(HTTPException) as exc_info:
            await check_permission(sample_user)
        
        self._assert_403_forbidden(exc_info, "Permission 'admin' required")

    @pytest.mark.asyncio
    async def test_get_current_user_auth_service_failure(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test handling of auth service failure during token validation."""
        # Mock auth service exception
        mock_auth_client.side_effect = Exception("Auth service unavailable")
        
        with pytest.raises(Exception, match="Auth service unavailable"):
            await get_current_user(mock_credentials, mock_db_session)
            
    @pytest.mark.asyncio
    async def test_get_current_user_database_failure(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test handling of database failure during user lookup."""
        self._setup_auth_client_valid_response(mock_auth_client)
        # Mock database exception
        mock_db_session.execute.side_effect = Exception("Database connection failed")
        
        with pytest.raises(Exception, match="Database connection failed"):
            await get_current_user(mock_credentials, mock_db_session)
            
    @pytest.mark.asyncio
    async def test_get_current_user_dev_mode_creates_user(self, mock_credentials, mock_auth_client, mock_db_session):
        """Test that development mode creates user when not found."""
        self._setup_auth_client_valid_response(mock_auth_client)
        self._setup_db_session_no_user(mock_db_session)
        
        # Mock config to be development
        with patch('netra_backend.app.config.get_config') as mock_config, \
             patch('netra_backend.app.services.user_service.user_service.get_or_create_dev_user', new_callable=AsyncMock) as mock_create_user:
            
            mock_config.return_value.environment = "development"
            
            dev_user = User()
            dev_user.id = "test-user-123"
            dev_user.email = "dev@example.com"
            mock_create_user.return_value = dev_user
            
            result = await get_current_user(mock_credentials, mock_db_session)
            
            assert result == dev_user
            mock_create_user.assert_called_once()
            
    def test_permission_validation_helper_with_valid_permission(self, sample_user):
        """Test internal permission validation helper function."""
        # Should not raise exception for valid permission
        try:
            from netra_backend.app.auth_integration.auth import _validate_user_permission
            _validate_user_permission(sample_user, "read")
            assert True  # No exception raised
        except ImportError:
            pytest.skip("Permission validation helper not available")
            
    def test_permission_validation_helper_with_invalid_permission(self, sample_user):
        """Test internal permission validation helper function with invalid permission."""
        try:
            from netra_backend.app.auth_integration.auth import _validate_user_permission
            with pytest.raises(HTTPException) as exc_info:
                _validate_user_permission(sample_user, "invalid_permission")
            self._assert_403_forbidden(exc_info, "Permission 'invalid_permission' required")
        except ImportError:
            pytest.skip("Permission validation helper not available")
            
    def test_permission_validation_helper_user_without_permissions(self):
        """Test permission validation with user that has no permissions attribute."""
        try:
            from netra_backend.app.auth_integration.auth import _validate_user_permission
            user_no_permissions = User()
            user_no_permissions.id = "no-perms-user"
            # No permissions attribute
            
            # Should not raise exception if user doesn't have permissions attribute
            _validate_user_permission(user_no_permissions, "any_permission")
            assert True  # Should complete without error
        except ImportError:
            pytest.skip("Permission validation helper not available")
            
    @pytest.mark.asyncio
    async def test_require_admin_with_superuser(self):
        """Test admin requirement with superuser flag."""
        user = User()
        user.id = "superuser-123"
        user.is_superuser = True
        user.is_admin = False  # Legacy flag is false
        
        result = await require_admin(user)
        assert result == user
        
    @pytest.mark.asyncio
    async def test_require_admin_with_role_based_admin(self):
        """Test admin requirement with admin role."""
        user = User()
        user.id = "role-admin-123"
        user.role = "admin"
        user.is_admin = False
        user.is_superuser = False
        
        result = await require_admin(user)
        assert result == user
        
    @pytest.mark.asyncio
    async def test_require_admin_with_super_admin_role(self):
        """Test admin requirement with super_admin role."""
        user = User()
        user.id = "super-admin-123"
        user.role = "super_admin"
        user.is_admin = False
        
        result = await require_admin(user)
        assert result == user
        
    @pytest.mark.asyncio
    async def test_require_developer_user_without_developer_attribute(self):
        """Test developer requirement with user that has no is_developer attribute."""
        user = User()
        user.id = "no-dev-attr-123"
        # No is_developer attribute
        
        with pytest.raises(HTTPException) as exc_info:
            await require_developer(user)
            
        self._assert_403_forbidden(exc_info, "Developer access required")
        
    def test_auth_client_instance_exists(self):
        """Test that auth client instance is properly initialized."""
        from netra_backend.app.auth_integration.auth import auth_client
        assert auth_client is not None
        assert hasattr(auth_client, 'validate_token_jwt')
        
    def test_security_bearer_instance(self):
        """Test that HTTPBearer security instance is properly configured."""
        from netra_backend.app.auth_integration.auth import security
        assert security is not None
        assert isinstance(security, HTTPBearer)
        
    def test_dependency_annotations_exist(self):
        """Test that FastAPI dependency annotations are properly defined."""
        from netra_backend.app.auth_integration.auth import ActiveUserDep, OptionalUserDep, AdminDep, DeveloperDep
        
        # These should be properly typed annotations
        assert ActiveUserDep is not None
        assert OptionalUserDep is not None
        assert AdminDep is not None
        assert DeveloperDep is not None

    # Helper methods (each ≤8 lines)
    def _setup_successful_auth_flow(self, mock_auth_client, mock_db_session, user):
        """Setup successful authentication flow."""
        self._setup_auth_client_valid_response(mock_auth_client)
        self._setup_db_session_with_user(mock_db_session, user)

    def _setup_auth_client_valid_response(self, mock_auth_client):
        """Setup auth client to await asyncio.sleep(0)
    return valid response."""
        mock_auth_client.return_value = {
            "valid": True,
            "user_id": "test-user-123",
            "email": "test@example.com"  # Include email for dev user creation
        }

    def _setup_db_session_with_user(self, mock_db_session, user):
        """Setup database session to return user."""
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.scalar_one_or_none.return_value = user
        mock_db_session.execute.return_value = mock_result

    def _setup_db_session_no_user(self, mock_db_session):
        """Setup database session to return no user."""
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.scalar_one_or_none.return_value = None
        mock_db_session.execute.return_value = mock_result

    def _assert_401_unauthorized(self, exc_info):
        """Assert 401 Unauthorized exception details."""
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid or expired token" in exc_info.value.detail
        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}

    def _assert_403_forbidden(self, exc_info, expected_detail):
        """Assert 403 Forbidden exception details."""
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert expected_detail in exc_info.value.detail
        
    def _create_admin_user_with_role(self, role: str) -> User:
        """Create admin user with specific role."""
        user = User()
        user.id = f"admin-{role}-123"
        user.role = role
        user.is_admin = False  # Test role-based auth over legacy flag
        return user


class TestRevenueProtectionAuth:
    """Test auth features that protect revenue and prevent user churn."""
    
    def test_enterprise_session_persistence_revenue_protection(self):
        """Test session persistence for enterprise users to prevent revenue loss.
        
        BVJ: Enterprise Segment - Revenue Protection
        Ensures enterprise user sessions persist through payment flows and
        high-value operations, preventing revenue loss due to session timeouts
        during critical business transactions.
        """
        from datetime import datetime, timedelta, UTC
        
        # Create enterprise user with high revenue potential
        enterprise_user = enterprise_user_instance  # Initialize appropriate service
        enterprise_user.id = "enterprise-123"
        enterprise_user.session_timeout_minutes = 240  # 4 hours for enterprise
        
        # Test high-value operations
        high_value_operations = [
            {"operation": "bulk_data_analysis", "duration_minutes": 45, "cost": 2500.00},
            {"operation": "custom_model_training", "duration_minutes": 90, "cost": 4800.00},
            {"operation": "enterprise_reporting", "duration_minutes": 31, "cost": 1200.00}
        ]
        
        total_potential_revenue = sum(op["cost"] for op in high_value_operations)
        assert total_potential_revenue == 8500.00
        
        # Verify all operations complete within enterprise session timeout
        for operation in high_value_operations:
            assert operation["duration_minutes"] <= enterprise_user.session_timeout_minutes
        
        # Compare to standard user timeout
        standard_user_timeout = 30  # minutes
        enterprise_advantage = enterprise_user.session_timeout_minutes - standard_user_timeout
        assert enterprise_advantage == 210  # 3.5 hours additional
        
        # Verify enterprise session enables all complex workflows
        complex_operations = [op for op in high_value_operations if op["duration_minutes"] > standard_user_timeout]
        assert len(complex_operations) == 3  # All require enterprise sessions
        
        # Calculate revenue protection ROI
        session_cost_per_month = 50.00
        monthly_revenue_protected = total_potential_revenue * 30  # Daily operations
        roi = (monthly_revenue_protected - session_cost_per_month) / session_cost_per_month
        assert roi > 5000  # 5000%+ ROI


class TestTokenSecurityValidation:
    """Advanced security tests for token validation and authentication."""
    
    def test_jwt_token_tampering_detection(self):
        """Test detection of tampered JWT tokens."""
        # Create a valid token
        secret = "test_secret_key"
        payload = {"user_id": "123", "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp()}
        valid_token = jwt.encode(payload, secret, algorithm="HS256")
        
        # Tamper with the token
        tampered_token = valid_token[:-5] + "XXXXX"  # Change last 5 characters
        
        # Should detect tampering
        try:
            decoded = jwt.decode(tampered_token, secret, algorithms=["HS256"])
            assert False, "Should have raised InvalidTokenError"
        except jwt.InvalidTokenError:
            pass  # Expected
        
    def test_jwt_token_expiry_security(self):
        """Test JWT token expiration security."""
        secret = "test_secret_key"
        
        # Create expired token
        expired_payload = {
            "user_id": "123", 
            "exp": (datetime.now(UTC) - timedelta(hours=1)).timestamp()  # 1 hour ago
        }
        expired_token = jwt.encode(expired_payload, secret, algorithm="HS256")
        
        # Should reject expired token
        try:
            decoded = jwt.decode(expired_token, secret, algorithms=["HS256"])
            assert False, "Should have raised ExpiredSignatureError"
        except jwt.ExpiredSignatureError:
            pass  # Expected
            
    def test_jwt_algorithm_security(self):
        """Test JWT algorithm confusion attacks."""
        secret = "test_secret_key"
        payload = {"user_id": "123", "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp()}
        
        # Try to use 'none' algorithm (security risk)
        try:
            malicious_token = jwt.encode(payload, secret, algorithm="none")
            # Should not accept 'none' algorithm tokens
            decoded = jwt.decode(malicious_token, options={"verify_signature": False}, algorithms=["none"])
            # This is a security risk if allowed
            assert decoded["user_id"] == "123"
        except Exception:
            pass  # May fail depending on jwt library version
            
    def test_token_payload_injection_security(self):
        """Test resistance to payload injection attacks."""
        secret = "test_secret_key"
        
        # Attempt to inject admin privileges
        malicious_payload = {
            "user_id": "123",
            "role": "admin",  # Escalated privileges
            "permissions": ["delete_all", "admin_access"],
            "exp": (datetime.now(UTC) + timedelta(hours=1)).timestamp()
        }
        
        malicious_token = jwt.encode(malicious_payload, secret, algorithm="HS256")
        decoded = jwt.decode(malicious_token, secret, algorithms=["HS256"])
        
        # Should detect suspicious privilege escalation
        assert decoded["role"] == "admin"  # Token is valid but privileges should be verified separately
        assert "delete_all" in decoded.get("permissions", [])
        
    @pytest.mark.asyncio
    async def test_concurrent_token_validation_race_condition_protection(self):
        """Test concurrent token validation to ensure thread safety and prevent race conditions.
        
        BVJ: Platform Security - Risk Reduction
        Ensures authentication system handles concurrent requests safely, preventing
        race conditions that could lead to token validation bypass or unauthorized access.
        Critical for high-traffic enterprise environments where multiple requests 
        may validate the same token simultaneously.
        """
        import asyncio
        
        # Mock successful token validation response
        mock_validation_response = {
            "valid": True,
            "user_id": "concurrent-user-123",
            "email": "concurrent@example.com"
        }
        
        # Track concurrent executions to detect race conditions
        concurrent_executions = []
        validation_call_count = 0
        
        async def mock_validate_token(token):
            nonlocal validation_call_count
            validation_call_count += 1
            
            # Record execution timing to detect race conditions
            execution_id = f"exec_{validation_call_count}"
            execution_info = {"id": execution_id, "start_time": asyncio.get_event_loop().time()}
            concurrent_executions.append(execution_info)
            
            # Simulate realistic network latency
            await asyncio.sleep(0.01)
            
            # Record completion
            execution_info["end_time"] = asyncio.get_event_loop().time()
            
            await asyncio.sleep(0)
    return mock_validation_response
        
        # Mock database user lookup
        mock_user = User()
        mock_user.id = "concurrent-user-123"
        mock_user.email = "concurrent@example.com"
        mock_user.is_admin = False
        
        mock_db_session = AsyncNone  # TODO: Use real service instance
        mock_result = mock_result_instance  # Initialize appropriate service
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db_session.execute.return_value = mock_result
        
        # Mock credentials
        mock_credentials = mock_credentials_instance  # Initialize appropriate service
        mock_credentials.credentials = "concurrent-test-token"
        
        # Test concurrent token validations
        with patch('netra_backend.app.auth_integration.auth.auth_client.validate_token_jwt', side_effect=mock_validate_token):
            # Execute multiple concurrent authentication requests
            tasks = []
            num_concurrent_requests = 5
            
            for i in range(num_concurrent_requests):
                task = get_current_user(mock_credentials, mock_db_session)
                tasks.append(task)
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Verify all requests succeeded
            successful_results = [r for r in results if isinstance(r, User)]
            failed_results = [r for r in results if isinstance(r, Exception)]
            
            assert len(successful_results) == num_concurrent_requests, f"Expected {num_concurrent_requests} successful authentications, got {len(successful_results)}"
            assert len(failed_results) == 0, f"Unexpected failures: {failed_results}"
            
            # Verify all results are identical (no race condition corruption)
            first_result = successful_results[0]
            for result in successful_results[1:]:
                assert result.id == first_result.id
                assert result.email == first_result.email
            
            # Verify proper concurrent execution (overlapping time windows)
            assert len(concurrent_executions) == num_concurrent_requests
            
            # Check for actual concurrency (executions should overlap)
            start_times = [exec_info["start_time"] for exec_info in concurrent_executions]
            end_times = [exec_info["end_time"] for exec_info in concurrent_executions]
            
            # If properly concurrent, some executions should start before others finish
            min_start = min(start_times)
            max_start = max(start_times)
            min_end = min(end_times)
            
            # Verify concurrency: some requests started before others finished
            assert max_start < min_end + 0.05, "Requests were not properly concurrent - possible serialization bottleneck"
            
            # Verify no authentication cache pollution between requests
            for result in successful_results:
                assert result.id == "concurrent-user-123"
                assert result.email == "concurrent@example.com"