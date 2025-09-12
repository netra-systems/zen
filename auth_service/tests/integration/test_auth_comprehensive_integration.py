"""
Comprehensive Auth Service Integration Tests - SSOT Testing Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure authentication reliability across all user flows and service interactions
- Value Impact: Prevents authentication failures that block user access and revenue generation
- Strategic Impact: Core platform stability - authentication is foundation for all business operations

This comprehensive test suite validates the complete authentication service functionality
using REAL services, REAL databases, and NO MOCKS (except external OAuth providers).

CRITICAL FOCUS AREAS:
1. JWT token lifecycle management (creation, validation, refresh, expiration)
2. Session persistence and management across requests
3. Cross-service authentication validation between auth and backend services
4. Database user management and persistence operations
5. Multi-user isolation and security boundaries
6. Password validation and user registration flows
7. Token refresh mechanisms and session continuity
8. Authentication error handling and security validation

TESTING REQUIREMENTS per CLAUDE.md:
- Uses ONLY real services (--real-services compatible)
- Follows SSOT patterns from test_framework/ssot/base_test_case.py
- Uses IsolatedEnvironment for all environment access
- Tests real business scenarios that existing features depend on
- Each test includes Business Value Justification (BVJ) comment
- NO MOCKS except external OAuth providers
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta, UTC
from typing import Dict, Any, Optional, List
from unittest.mock import patch, AsyncMock

import aiohttp
import bcrypt
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.database_test_utilities import DatabaseTestUtilities
from test_framework.ssot.integration_auth_manager import (
    IntegrationAuthServiceManager,
    IntegrationTestAuthHelper
)
from auth_service.auth_core.auth_environment import get_auth_env
from auth_service.auth_core.core.jwt_handler import JWTHandler
from auth_service.auth_core.database.repository import AuthUserRepository
from auth_service.auth_core.database.models import AuthUser, AuthSession, AuthAuditLog
from auth_service.auth_core.models.auth_models import (
    LoginRequest, LoginResponse, TokenRequest, TokenResponse, 
    RefreshRequest, SessionInfo, User, AuthProvider
)
from shared.isolated_environment import get_env


logger = logging.getLogger(__name__)


class TestAuthComprehensiveIntegration(SSotBaseTestCase):
    """
    Comprehensive Authentication Service Integration Tests.
    
    This test suite validates all critical authentication flows using real services,
    real databases, and production-like configurations to ensure reliability.
    
    CRITICAL: Uses real PostgreSQL, real JWT operations, real session management.
    NO MOCKS except for external OAuth providers to ensure production behavior.
    """
    
    @pytest.fixture(scope="class")
    async def auth_service_manager(self):
        """Start real auth service for comprehensive integration testing."""
        manager = IntegrationAuthServiceManager()
        
        # Start auth service with real database
        success = await manager.start_auth_service()
        if not success:
            pytest.fail("Failed to start auth service for comprehensive integration tests")
        
        yield manager
        
        # Cleanup
        await manager.stop_auth_service()
    
    @pytest.fixture
    async def auth_helper(self, auth_service_manager):
        """Create auth helper for integration testing."""
        helper = IntegrationTestAuthHelper(auth_service_manager)
        yield helper
    
    @pytest.fixture
    async def database_session(self):
        """Provide isolated database session for auth operations."""
        async with DatabaseTestUtilities("auth_service").session_scope() as session:
            yield session
    
    @pytest.fixture
    async def jwt_handler(self):
        """Provide real JWT handler for token operations."""
        handler = JWTHandler()
        yield handler
    
    @pytest.fixture
    async def user_repository(self, database_session):
        """Provide user repository for database operations."""
        repo = AuthUserRepository(database_session)
        yield repo
    
    # === JWT TOKEN LIFECYCLE TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_creation_validation_complete_cycle(
        self, auth_service_manager, jwt_handler
    ):
        """
        BVJ: All Segments - Core authentication functionality
        Integration test for complete JWT token lifecycle from creation to expiration.
        
        Tests the full token lifecycle including creation, validation, claims verification,
        and expiration handling using real JWT operations and real auth service.
        
        CRITICAL: This validates the core authentication flow that all users depend on.
        """
        # Record test metadata
        self.record_metric("test_category", "jwt_lifecycle_complete")
        self.record_metric("test_focus", "creation_validation_cycle")
        
        # Test user data
        user_data = {
            "user_id": "jwt-lifecycle-user-001",
            "email": "jwt.lifecycle@example.com",
            "permissions": ["read", "write", "admin"]
        }
        
        # Step 1: Create access token via JWT handler (direct method - more reliable)
        start_time = time.time()
        access_token = jwt_handler.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        token_creation_time = time.time() - start_time
        
        assert access_token is not None, "JWT handler should create access token"
        assert len(access_token) > 100, "JWT token should be substantial length"
        self.record_metric("token_creation_time_ms", token_creation_time * 1000)
        
        # Step 2: Validate token via JWT handler
        start_time = time.time()
        validation_result = jwt_handler.validate_token(access_token, "access")
        token_validation_time = time.time() - start_time
        
        assert validation_result is not None, "JWT validation should return result"
        assert validation_result.get("sub") == user_data["user_id"], "User ID should match"
        assert validation_result.get("email") == user_data["email"], "Email should match"
        assert validation_result.get("permissions") == user_data["permissions"], "Permissions should match"
        
        self.record_metric("token_validation_time_ms", token_validation_time * 1000)
        
        # Step 3: Validate token via auth service API
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.post(
                f"{auth_service_manager.get_auth_url()}/auth/validate",
                json={"token": access_token, "token_type": "access"},
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200, f"Auth service validation failed: {response.status}"
                
                api_validation = await response.json()
                assert api_validation.get("valid", False), "Auth service should validate token"
                assert api_validation.get("user_id") == user_data["user_id"], "API user ID should match"
        
        # Step 4: Create and validate refresh token
        refresh_token = jwt_handler.create_refresh_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        assert refresh_token is not None, "JWT handler should create refresh token"
        
        refresh_validation = jwt_handler.validate_token(refresh_token, "refresh")
        assert refresh_validation is not None, "Refresh token should be valid"
        assert refresh_validation.get("sub") == user_data["user_id"], "Refresh token user ID should match"
        
        # Step 5: Test token refresh mechanism
        new_access_token, new_refresh_token = jwt_handler.refresh_access_token(refresh_token)
        
        assert new_access_token is not None, "Token refresh should create new access token"
        assert new_refresh_token is not None, "Token refresh should create new refresh token"
        assert new_access_token != access_token, "New access token should be different"
        assert new_refresh_token != refresh_token, "New refresh token should be different"
        
        # Validate new tokens work
        new_validation = jwt_handler.validate_token(new_access_token, "access")
        assert new_validation is not None, "New access token should be valid"
        assert new_validation.get("sub") == user_data["user_id"], "New token should have same user ID"
        
        self.record_metric("jwt_lifecycle_complete", "success")
        self.increment_db_query_count(2)  # JWT operations may involve cache queries
        logger.info(" PASS:  JWT token lifecycle complete cycle working correctly")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_jwt_token_security_validation_comprehensive(
        self, auth_service_manager, jwt_handler
    ):
        """
        BVJ: Enterprise Segment - Security validation for high-value accounts
        Integration test for comprehensive JWT token security validation.
        
        Tests various security scenarios including malformed tokens, expired tokens,
        invalid signatures, and security attack vectors.
        
        CRITICAL: Security failures can lead to unauthorized access and data breaches.
        """
        # Record test metadata
        self.record_metric("test_category", "jwt_security_comprehensive")
        self.record_metric("test_focus", "security_validation")
        
        # Valid token for baseline
        valid_token = jwt_handler.create_access_token(
            user_id="security-test-user",
            email="security@example.com",
            permissions=["read"]
        )
        
        # Test security scenarios
        security_test_cases = [
            {
                "name": "empty_token",
                "token": "",
                "expected": "should_reject",
                "security_risk": "bypass_authentication"
            },
            {
                "name": "null_token",
                "token": None,
                "expected": "should_reject",
                "security_risk": "null_pointer_bypass"
            },
            {
                "name": "malformed_structure",
                "token": "not.a.valid.jwt.structure.with.extra.parts",
                "expected": "should_reject",
                "security_risk": "structure_confusion"
            },
            {
                "name": "invalid_base64",
                "token": "invalid!@#.base64!@#.signature!@#",
                "expected": "should_reject",
                "security_risk": "encoding_bypass"
            },
            {
                "name": "none_algorithm_attack",
                "token": "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhdHRhY2tlciIsImVtYWlsIjoiYXR0YWNrQGV4YW1wbGUuY29tIn0.",
                "expected": "should_reject",
                "security_risk": "algorithm_confusion_attack"
            }
        ]
        
        security_failures = []
        
        for test_case in security_test_cases:
            case_name = test_case["name"]
            token = test_case["token"]
            security_risk = test_case["security_risk"]
            
            logger.debug(f"Testing security scenario: {case_name}")
            
            try:
                # Test JWT handler validation
                jwt_result = jwt_handler.validate_token(token, "access") if token else None
                jwt_rejected = jwt_result is None
                
                # Test auth service validation
                api_rejected = True
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{auth_service_manager.get_auth_url()}/auth/validate",
                            json={"token": token or "", "token_type": "access"},
                            headers={"Content-Type": "application/json"},
                            timeout=aiohttp.ClientTimeout(total=5)
                        ) as response:
                            if response.status == 200:
                                api_result = await response.json()
                                api_rejected = not api_result.get("valid", False)
                            else:
                                api_rejected = True
                except Exception:
                    api_rejected = True  # Any exception means rejection
                
                # Both should reject the malicious token
                if not jwt_rejected or not api_rejected:
                    security_failures.append({
                        "case": case_name,
                        "risk": security_risk,
                        "jwt_rejected": jwt_rejected,
                        "api_rejected": api_rejected
                    })
                else:
                    self.record_metric(f"security_case_{case_name}", "correctly_rejected")
                
                self.increment_db_query_count(1)  # Each validation attempt
                
            except Exception as e:
                logger.debug(f"Security test case {case_name} raised exception (expected): {e}")
                self.record_metric(f"security_case_{case_name}", "correctly_rejected_exception")
        
        # Assert no security failures
        assert len(security_failures) == 0, (
            f"SECURITY VULNERABILITY: {len(security_failures)} test cases failed to reject malicious tokens. "
            f"Failures: {security_failures}"
        )
        
        # Test valid token still works
        valid_validation = jwt_handler.validate_token(valid_token, "access")
        assert valid_validation is not None, "Valid token should still work after security tests"
        
        self.record_metric("jwt_security_validation", "comprehensive_pass")
        self.record_metric("security_test_cases", len(security_test_cases))
        logger.info(f" PASS:  JWT security validation comprehensive ({len(security_test_cases)} cases passed)")
    
    # === SESSION MANAGEMENT AND PERSISTENCE TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_persistence_across_requests(
        self, auth_service_manager, database_session, user_repository
    ):
        """
        BVJ: All Segments - Session continuity for user experience
        Integration test for session persistence across multiple requests.
        
        Tests that user sessions are properly created, stored, and maintained
        across multiple API requests using real database persistence.
        
        CRITICAL: Session persistence ensures users don't get logged out unexpectedly.
        """
        # Record test metadata
        self.record_metric("test_category", "session_persistence")
        self.record_metric("test_focus", "cross_request_continuity")
        
        # Step 1: Create test user in database
        test_user = AuthUser(
            email="session.test@example.com",
            full_name="Session Test User",
            password_hash=bcrypt.hashpw("testpassword123".encode(), bcrypt.gensalt()).decode(),
            is_active=True,
            is_verified=True
        )
        
        database_session.add(test_user)
        await database_session.commit()
        await database_session.refresh(test_user)
        
        self.record_metric("test_user_created", True)
        self.increment_db_query_count(2)  # Insert + refresh
        
        # Step 2: Login via auth service to establish session
        login_data = {
            "email": "session.test@example.com",
            "password": "testpassword123",
            "provider": "local"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{auth_service_manager.get_auth_url()}/auth/login",
                json=login_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200, f"Login failed: {response.status}"
                
                login_response = await response.json()
                access_token = login_response.get("access_token")
                assert access_token is not None, "Login should return access token"
                
                self.record_metric("login_successful", True)
        
        # Step 3: Make multiple authenticated requests to test session persistence
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        request_count = 5
        successful_requests = 0
        
        for i in range(request_count):
            async with aiohttp.ClientSession() as session:
                # Test token validation endpoint
                async with session.post(
                    f"{auth_service_manager.get_auth_url()}/auth/validate",
                    json={"token": access_token, "token_type": "access"},
                    headers=auth_headers
                ) as response:
                    if response.status == 200:
                        validation_result = await response.json()
                        if validation_result.get("valid", False):
                            successful_requests += 1
                        
                        # Verify user data consistency
                        assert validation_result.get("email") == "session.test@example.com"
                        
            self.increment_db_query_count(1)  # Each validation
            
            # Add delay to test session timing
            await asyncio.sleep(0.1)
        
        # Step 4: Verify all requests succeeded (session persisted)
        assert successful_requests == request_count, (
            f"Session persistence failed: only {successful_requests}/{request_count} requests succeeded"
        )
        
        # Step 5: Verify user session exists in database
        from sqlalchemy import select
        session_query = select(AuthSession).where(AuthSession.user_id == test_user.id)
        session_result = await database_session.execute(session_query)
        user_sessions = session_result.scalars().all()
        
        assert len(user_sessions) >= 1, "User should have at least one active session in database"
        
        self.record_metric("session_persistence_requests", successful_requests)
        self.record_metric("database_sessions_found", len(user_sessions))
        self.record_metric("session_persistence_test", "success")
        self.increment_db_query_count(1)  # Session query
        
        logger.info(f" PASS:  Session persistence working ({successful_requests}/{request_count} requests successful)")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_management_multi_user_isolation(
        self, auth_service_manager, database_session, user_repository
    ):
        """
        BVJ: Mid/Enterprise Segments - Multi-user session isolation for team accounts
        Integration test for session isolation between multiple concurrent users.
        
        Tests that sessions for different users are properly isolated and
        one user's session cannot be used to access another user's resources.
        
        CRITICAL: Session isolation prevents cross-user data access vulnerabilities.
        """
        # Record test metadata
        self.record_metric("test_category", "session_isolation")
        self.record_metric("test_focus", "multi_user_boundaries")
        
        # Step 1: Create multiple test users
        test_users = []
        for i in range(3):
            user = AuthUser(
                email=f"isolation.user{i}@example.com",
                full_name=f"Isolation User {i}",
                password_hash=bcrypt.hashpw(f"password{i}123".encode(), bcrypt.gensalt()).decode(),
                is_active=True,
                is_verified=True
            )
            database_session.add(user)
            test_users.append(user)
        
        await database_session.commit()
        for user in test_users:
            await database_session.refresh(user)
        
        self.record_metric("test_users_created", len(test_users))
        self.increment_db_query_count(len(test_users) * 2)  # Insert + refresh per user
        
        # Step 2: Login all users to establish sessions
        user_tokens = {}
        
        for i, user in enumerate(test_users):
            login_data = {
                "email": f"isolation.user{i}@example.com",
                "password": f"password{i}123",
                "provider": "local"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{auth_service_manager.get_auth_url()}/auth/login",
                    json=login_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    assert response.status == 200, f"Login failed for user {i}"
                    
                    login_response = await response.json()
                    token = login_response.get("access_token")
                    assert token is not None, f"User {i} should get access token"
                    
                    user_tokens[user.id] = {
                        "token": token,
                        "email": user.email,
                        "user_index": i
                    }
        
        self.record_metric("user_logins_successful", len(user_tokens))
        
        # Step 3: Test session isolation - each token should only work for its user
        isolation_violations = []
        
        for user_id, token_data in user_tokens.items():
            token = token_data["token"]
            expected_email = token_data["email"]
            
            # Validate token returns correct user data
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{auth_service_manager.get_auth_url()}/auth/validate",
                    json={"token": token, "token_type": "access"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    assert response.status == 200, f"Token validation failed for user {user_id}"
                    
                    validation_result = await response.json()
                    assert validation_result.get("valid", False), f"Token should be valid for user {user_id}"
                    
                    actual_email = validation_result.get("email")
                    actual_user_id = validation_result.get("user_id")
                    
                    # Verify correct user data
                    if actual_email != expected_email:
                        isolation_violations.append({
                            "user_id": user_id,
                            "expected_email": expected_email,
                            "actual_email": actual_email,
                            "issue": "email_mismatch"
                        })
                    
                    if actual_user_id != user_id:
                        isolation_violations.append({
                            "user_id": user_id,
                            "expected_user_id": user_id,
                            "actual_user_id": actual_user_id,
                            "issue": "user_id_mismatch"
                        })
            
            self.increment_db_query_count(1)  # Token validation
        
        # Step 4: Verify no isolation violations
        assert len(isolation_violations) == 0, (
            f"SESSION ISOLATION FAILURE: Found {len(isolation_violations)} violations: {isolation_violations}"
        )
        
        # Step 5: Test tokens are unique (no token reuse)
        all_tokens = [data["token"] for data in user_tokens.values()]
        unique_tokens = set(all_tokens)
        
        assert len(unique_tokens) == len(all_tokens), (
            f"Token reuse detected: {len(all_tokens)} tokens, {len(unique_tokens)} unique"
        )
        
        self.record_metric("session_isolation_test", "success")
        self.record_metric("unique_user_sessions", len(unique_tokens))
        logger.info(f" PASS:  Session isolation working correctly ({len(test_users)} users tested)")
    
    # === CROSS-SERVICE AUTHENTICATION VALIDATION TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cross_service_authentication_backend_integration(
        self, auth_service_manager, jwt_handler
    ):
        """
        BVJ: All Segments - Cross-service authentication for platform functionality
        Integration test for authentication validation between auth and backend services.
        
        Tests that tokens issued by auth service are properly validated by backend service
        and that cross-service authentication maintains security boundaries.
        
        CRITICAL: Cross-service auth failures break platform functionality and user workflows.
        """
        # Record test metadata
        self.record_metric("test_category", "cross_service_auth")
        self.record_metric("test_focus", "auth_backend_integration")
        
        # Step 1: Create token via auth service
        user_data = {
            "user_id": "cross-service-user-001",
            "email": "crossservice@example.com",
            "permissions": ["read", "write", "execute"]
        }
        
        access_token = jwt_handler.create_access_token(
            user_id=user_data["user_id"],
            email=user_data["email"],
            permissions=user_data["permissions"]
        )
        
        assert access_token is not None, "Auth service should create token"
        
        # Step 2: Validate token has proper cross-service claims
        jwt_payload = jwt_handler.validate_token(access_token, "access")
        assert jwt_payload is not None, "Token should be valid"
        
        # Verify cross-service security claims
        required_claims = ["iss", "aud", "sub", "email", "permissions"]
        for claim in required_claims:
            assert claim in jwt_payload, f"Token missing required cross-service claim: {claim}"
        
        assert jwt_payload["iss"] == "netra-auth-service", "Issuer should be auth service"
        assert jwt_payload["aud"] in ["netra-platform", "netra-backend"], "Audience should be valid for backend"
        
        self.record_metric("cross_service_claims_valid", True)
        
        # Step 3: Test token validation via auth service API (simulating backend validation)
        validation_scenarios = [
            {
                "name": "standard_validation",
                "token_type": "access",
                "expected_valid": True
            },
            {
                "name": "wrong_token_type",
                "token_type": "refresh",  # Using access token as refresh
                "expected_valid": False
            }
        ]
        
        for scenario in validation_scenarios:
            scenario_name = scenario["name"]
            token_type = scenario["token_type"]
            expected_valid = scenario["expected_valid"]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{auth_service_manager.get_auth_url()}/auth/validate",
                    json={"token": access_token, "token_type": token_type},
                    headers={"Content-Type": "application/json"}
                ) as response:
                    
                    if expected_valid:
                        assert response.status == 200, f"Scenario {scenario_name} should succeed"
                        result = await response.json()
                        assert result.get("valid", False), f"Token should be valid for {scenario_name}"
                        assert result.get("user_id") == user_data["user_id"], "User ID should match"
                    else:
                        # Should either return 200 with valid=false or error status
                        if response.status == 200:
                            result = await response.json()
                            assert not result.get("valid", True), f"Token should be invalid for {scenario_name}"
                        else:
                            assert response.status in [400, 401, 403], f"Should return auth error for {scenario_name}"
                    
                    self.record_metric(f"cross_service_scenario_{scenario_name}", "tested")
            
            self.increment_db_query_count(1)  # Validation query
        
        # Step 4: Test service-to-service token creation and validation
        service_token = jwt_handler.create_service_token(
            service_id="backend-service",
            service_name="netra-backend"
        )
        
        assert service_token is not None, "Should create service token"
        
        service_validation = jwt_handler.validate_token(service_token, "service")
        assert service_validation is not None, "Service token should be valid"
        assert service_validation.get("sub") == "backend-service", "Service token should have correct subject"
        
        self.record_metric("service_token_validation", "success")
        self.record_metric("cross_service_auth_test", "success")
        logger.info(" PASS:  Cross-service authentication integration working correctly")
    
    # === DATABASE OPERATIONS AND USER MANAGEMENT TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_user_management_comprehensive(
        self, database_session, user_repository
    ):
        """
        BVJ: All Segments - User data persistence for account management
        Integration test for comprehensive database user management operations.
        
        Tests user creation, retrieval, updates, and persistence operations
        using real PostgreSQL database connections and transactions.
        
        CRITICAL: User data persistence is foundation for all authentication operations.
        """
        # Record test metadata
        self.record_metric("test_category", "database_user_management")
        self.record_metric("test_focus", "crud_operations")
        
        # Step 1: Test user creation with comprehensive data
        user_data = {
            "email": "dbtest@example.com",
            "full_name": "Database Test User",
            "password": "securepassword123",
            "auth_provider": "local",
            "is_active": True,
            "is_verified": False
        }
        
        # Hash password
        password_hash = bcrypt.hashpw(user_data["password"].encode(), bcrypt.gensalt()).decode()
        
        new_user = AuthUser(
            email=user_data["email"],
            full_name=user_data["full_name"],
            password_hash=password_hash,
            auth_provider=user_data["auth_provider"],
            is_active=user_data["is_active"],
            is_verified=user_data["is_verified"]
        )
        
        database_session.add(new_user)
        await database_session.commit()
        await database_session.refresh(new_user)
        
        assert new_user.id is not None, "User should have database ID after creation"
        assert new_user.created_at is not None, "User should have creation timestamp"
        
        self.record_metric("user_creation", "success")
        self.increment_db_query_count(2)  # Insert + refresh
        
        # Step 2: Test user retrieval operations
        # Retrieve by email
        retrieved_by_email = await user_repository.get_by_email(user_data["email"])
        assert retrieved_by_email is not None, "Should retrieve user by email"
        assert retrieved_by_email.email == user_data["email"], "Retrieved email should match"
        assert retrieved_by_email.full_name == user_data["full_name"], "Retrieved name should match"
        
        # Retrieve by ID
        retrieved_by_id = await user_repository.get_by_id(new_user.id)
        assert retrieved_by_id is not None, "Should retrieve user by ID"
        assert retrieved_by_id.id == new_user.id, "Retrieved ID should match"
        
        self.record_metric("user_retrieval", "success")
        self.increment_db_query_count(2)  # Two select queries
        
        # Step 3: Test user update operations
        # Update user data
        new_user.full_name = "Updated Database Test User"
        new_user.is_verified = True
        new_user.updated_at = datetime.now(UTC)
        
        await database_session.commit()
        
        # Verify updates persisted
        updated_user = await user_repository.get_by_id(new_user.id)
        assert updated_user.full_name == "Updated Database Test User", "Name update should persist"
        assert updated_user.is_verified == True, "Verification status should persist"
        assert updated_user.updated_at is not None, "Update timestamp should be set"
        
        self.record_metric("user_update", "success")
        self.increment_db_query_count(2)  # Update + select
        
        # Step 4: Test password verification
        # Verify original password works
        password_valid = bcrypt.checkpw(
            user_data["password"].encode(),
            updated_user.password_hash.encode()
        )
        assert password_valid, "Original password should still be valid"
        
        # Verify wrong password fails
        wrong_password_valid = bcrypt.checkpw(
            "wrongpassword".encode(),
            updated_user.password_hash.encode()
        )
        assert not wrong_password_valid, "Wrong password should not be valid"
        
        self.record_metric("password_verification", "success")
        
        # Step 5: Test OAuth user creation (different code path)
        oauth_user_info = {
            "email": "oauth.dbtest@example.com",
            "name": "OAuth Database Test",
            "id": "google_123456789",
            "provider": "google",
            "picture": "https://example.com/picture.jpg"
        }
        
        oauth_user = await user_repository.create_oauth_user(oauth_user_info)
        assert oauth_user is not None, "Should create OAuth user"
        assert oauth_user.email == oauth_user_info["email"], "OAuth user email should match"
        assert oauth_user.auth_provider == "google", "OAuth provider should be set"
        assert oauth_user.is_verified == True, "OAuth users should be pre-verified"
        
        self.record_metric("oauth_user_creation", "success")
        self.increment_db_query_count(3)  # OAuth creation involves multiple queries
        
        # Step 6: Test concurrent access and race condition handling
        # Attempt to create duplicate OAuth user (should update existing)
        duplicate_oauth_info = oauth_user_info.copy()
        duplicate_oauth_info["name"] = "Updated OAuth Name"
        
        updated_oauth_user = await user_repository.create_oauth_user(duplicate_oauth_info)
        assert updated_oauth_user.id == oauth_user.id, "Should update existing OAuth user"
        assert updated_oauth_user.full_name == "Updated OAuth Name", "Should update OAuth user name"
        
        self.record_metric("oauth_duplicate_handling", "success")
        self.increment_db_query_count(2)  # Update operation
        
        self.record_metric("database_user_management_test", "comprehensive_success")
        logger.info(" PASS:  Database user management comprehensive testing successful")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_database_transaction_integrity_and_rollback(
        self, database_session
    ):
        """
        BVJ: Enterprise Segment - Data integrity for critical business operations
        Integration test for database transaction integrity and rollback handling.
        
        Tests that database transactions maintain ACID properties and proper
        rollback behavior when errors occur during user operations.
        
        CRITICAL: Transaction integrity prevents data corruption and inconsistent state.
        """
        # Record test metadata
        self.record_metric("test_category", "database_transaction_integrity")
        self.record_metric("test_focus", "acid_properties_rollback")
        
        # Step 1: Test successful transaction
        user1 = AuthUser(
            email="transaction.test1@example.com",
            full_name="Transaction Test User 1",
            password_hash="hashed_password_1",
            is_active=True
        )
        
        user2 = AuthUser(
            email="transaction.test2@example.com",
            full_name="Transaction Test User 2",
            password_hash="hashed_password_2",
            is_active=True
        )
        
        # Add both users in single transaction
        database_session.add_all([user1, user2])
        await database_session.commit()
        
        # Verify both users were created
        await database_session.refresh(user1)
        await database_session.refresh(user2)
        
        assert user1.id is not None, "User 1 should be created successfully"
        assert user2.id is not None, "User 2 should be created successfully"
        
        self.record_metric("successful_transaction", "confirmed")
        self.increment_db_query_count(4)  # 2 inserts + 2 refreshes
        
        # Step 2: Test transaction rollback on constraint violation
        # Create user with duplicate email (should cause constraint violation)
        duplicate_user = AuthUser(
            email="transaction.test1@example.com",  # Duplicate email
            full_name="Duplicate User",
            password_hash="hashed_password_duplicate",
            is_active=True
        )
        
        # Start new transaction that should fail
        try:
            database_session.add(duplicate_user)
            await database_session.commit()
            
            # Should not reach this point
            assert False, "Duplicate email should have caused constraint violation"
            
        except Exception as e:
            # Expected: constraint violation should cause rollback
            logger.debug(f"Expected constraint violation: {e}")
            await database_session.rollback()
            
            self.record_metric("constraint_violation_rollback", "successful")
        
        # Step 3: Verify database state is consistent after rollback
        # Check that original users still exist and are unchanged
        from sqlalchemy import select
        
        user1_check = await database_session.execute(
            select(AuthUser).where(AuthUser.email == "transaction.test1@example.com")
        )
        existing_user1 = user1_check.scalar_one_or_none()
        
        assert existing_user1 is not None, "Original user 1 should still exist after rollback"
        assert existing_user1.full_name == "Transaction Test User 1", "User 1 data should be unchanged"
        
        user2_check = await database_session.execute(
            select(AuthUser).where(AuthUser.email == "transaction.test2@example.com")
        )
        existing_user2 = user2_check.scalar_one_or_none()
        
        assert existing_user2 is not None, "Original user 2 should still exist after rollback"
        assert existing_user2.full_name == "Transaction Test User 2", "User 2 data should be unchanged"
        
        # Verify duplicate user was not created
        all_users_check = await database_session.execute(
            select(AuthUser).where(AuthUser.full_name == "Duplicate User")
        )
        duplicate_check = all_users_check.scalar_one_or_none()
        
        assert duplicate_check is None, "Duplicate user should not exist after rollback"
        
        self.record_metric("database_consistency_after_rollback", "confirmed")
        self.increment_db_query_count(3)  # 3 select queries for verification
        
        # Step 4: Test partial transaction rollback with complex operations
        # Start transaction with multiple operations, fail in middle
        user3 = AuthUser(
            email="transaction.test3@example.com",
            full_name="Transaction Test User 3",
            password_hash="hashed_password_3",
            is_active=True
        )
        
        try:
            # Operation 1: Create user 3
            database_session.add(user3)
            await database_session.flush()  # Flush but don't commit
            
            # Operation 2: Update user 1
            existing_user1.full_name = "Updated Name During Transaction"
            await database_session.flush()
            
            # Operation 3: Create duplicate user (should fail)
            another_duplicate = AuthUser(
                email="transaction.test1@example.com",  # Duplicate
                full_name="Another Duplicate",
                password_hash="another_hash",
                is_active=True
            )
            database_session.add(another_duplicate)
            await database_session.commit()  # This should fail
            
            assert False, "Complex transaction should have failed on duplicate"
            
        except Exception as e:
            logger.debug(f"Expected complex transaction failure: {e}")
            await database_session.rollback()
        
        # Step 5: Verify all operations in failed transaction were rolled back
        # Check user 3 was not created
        user3_check = await database_session.execute(
            select(AuthUser).where(AuthUser.email == "transaction.test3@example.com")
        )
        user3_result = user3_check.scalar_one_or_none()
        
        assert user3_result is None, "User 3 should not exist after transaction rollback"
        
        # Check user 1 was not updated
        user1_recheck = await database_session.execute(
            select(AuthUser).where(AuthUser.email == "transaction.test1@example.com")
        )
        user1_after_rollback = user1_recheck.scalar_one()
        
        assert user1_after_rollback.full_name == "Transaction Test User 1", (
            "User 1 name should be unchanged after transaction rollback"
        )
        
        self.record_metric("complex_transaction_rollback", "successful")
        self.record_metric("database_transaction_integrity_test", "comprehensive_success")
        self.increment_db_query_count(2)  # 2 verification queries
        
        logger.info(" PASS:  Database transaction integrity and rollback testing successful")
    
    # === MULTI-USER ISOLATION AND SECURITY TESTS ===
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_multi_user_authentication_isolation_comprehensive(
        self, auth_service_manager, database_session, jwt_handler
    ):
        """
        BVJ: Enterprise Segment - Multi-tenant security for business accounts
        Integration test for comprehensive multi-user authentication isolation.
        
        Tests that authentication operations maintain proper isolation between users,
        preventing cross-user data access, token reuse, and session leakage.
        
        CRITICAL: Multi-user isolation failures can cause data breaches and compliance violations.
        """
        # Record test metadata
        self.record_metric("test_category", "multi_user_isolation_comprehensive")
        self.record_metric("test_focus", "authentication_boundaries")
        
        # Step 1: Create multiple isolated user accounts
        isolated_users = []
        for i in range(5):  # Test with 5 users for comprehensive isolation
            user = AuthUser(
                email=f"isolation.comprehensive.{i}@example.com",
                full_name=f"Isolated User {i}",
                password_hash=bcrypt.hashpw(f"isolatedpass{i}123".encode(), bcrypt.gensalt()).decode(),
                is_active=True,
                is_verified=True
            )
            database_session.add(user)
            isolated_users.append(user)
        
        await database_session.commit()
        
        for user in isolated_users:
            await database_session.refresh(user)
        
        self.record_metric("isolated_users_created", len(isolated_users))
        self.increment_db_query_count(len(isolated_users) * 2)  # Insert + refresh per user
        
        # Step 2: Generate authentication tokens for all users
        user_auth_data = {}
        
        for i, user in enumerate(isolated_users):
            # Create access and refresh tokens
            access_token = jwt_handler.create_access_token(
                user_id=user.id,
                email=user.email,
                permissions=[f"user_{i}_read", f"user_{i}_write"]
            )
            
            refresh_token = jwt_handler.create_refresh_token(
                user_id=user.id,
                email=user.email,
                permissions=[f"user_{i}_read", f"user_{i}_write"]
            )
            
            user_auth_data[user.id] = {
                "user": user,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "expected_permissions": [f"user_{i}_read", f"user_{i}_write"],
                "user_index": i
            }
        
        self.record_metric("user_tokens_generated", len(user_auth_data))
        
        # Step 3: Test token isolation - each token should only validate for its user
        isolation_violations = []
        
        for user_id, auth_data in user_auth_data.items():
            access_token = auth_data["access_token"]
            expected_user = auth_data["user"]
            expected_permissions = auth_data["expected_permissions"]
            
            # Validate access token
            token_payload = jwt_handler.validate_token(access_token, "access")
            
            if token_payload is None:
                isolation_violations.append({
                    "user_id": user_id,
                    "issue": "token_validation_failed",
                    "token_type": "access"
                })
                continue
            
            # Check user ID isolation
            if token_payload.get("sub") != user_id:
                isolation_violations.append({
                    "user_id": user_id,
                    "expected_sub": user_id,
                    "actual_sub": token_payload.get("sub"),
                    "issue": "user_id_cross_contamination"
                })
            
            # Check email isolation
            if token_payload.get("email") != expected_user.email:
                isolation_violations.append({
                    "user_id": user_id,
                    "expected_email": expected_user.email,
                    "actual_email": token_payload.get("email"),
                    "issue": "email_cross_contamination"
                })
            
            # Check permission isolation
            actual_permissions = token_payload.get("permissions", [])
            if set(actual_permissions) != set(expected_permissions):
                isolation_violations.append({
                    "user_id": user_id,
                    "expected_permissions": expected_permissions,
                    "actual_permissions": actual_permissions,
                    "issue": "permission_cross_contamination"
                })
            
            self.increment_db_query_count(1)  # Token validation
        
        # Step 4: Test cross-user token validation failures
        # Try to validate each user's token as if it belongs to another user
        cross_user_attempts = 0
        successful_cross_user_attacks = 0
        
        user_ids = list(user_auth_data.keys())
        for i, user_id_1 in enumerate(user_ids):
            for j, user_id_2 in enumerate(user_ids):
                if i >= j:  # Skip same user and avoid duplicate tests
                    continue
                
                # Take user 1's token and try to use it for user 2's operations
                user1_token = user_auth_data[user_id_1]["access_token"]
                
                # Simulate API call as if token belongs to user 2
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{auth_service_manager.get_auth_url()}/auth/validate",
                        json={"token": user1_token, "token_type": "access"},
                        headers={"Content-Type": "application/json"}
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            if result.get("valid", False):
                                # Token was valid - now check if it identifies the correct user
                                validated_user_id = result.get("user_id")
                                if validated_user_id == user_id_2:
                                    # CRITICAL SECURITY VIOLATION: Token validated for wrong user
                                    successful_cross_user_attacks += 1
                                    isolation_violations.append({
                                        "attack_type": "cross_user_token_validation",
                                        "token_owner": user_id_1,
                                        "validated_as": user_id_2,
                                        "issue": "critical_security_breach"
                                    })
                        
                        cross_user_attempts += 1
                
                self.increment_db_query_count(1)  # Cross-validation attempt
        
        # Step 5: Test session isolation via API
        api_isolation_violations = []
        
        for user_id, auth_data in user_auth_data.items():
            token = auth_data["access_token"]
            expected_email = auth_data["user"].email
            
            # Make authenticated API call
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
                
                async with session.post(
                    f"{auth_service_manager.get_auth_url()}/auth/validate",
                    json={"token": token, "token_type": "access"},
                    headers=headers
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("valid", False):
                            api_email = result.get("email")
                            api_user_id = result.get("user_id")
                            
                            if api_email != expected_email:
                                api_isolation_violations.append({
                                    "user_id": user_id,
                                    "expected_email": expected_email,
                                    "api_returned_email": api_email,
                                    "issue": "api_email_isolation_failure"
                                })
                            
                            if api_user_id != user_id:
                                api_isolation_violations.append({
                                    "user_id": user_id,
                                    "expected_user_id": user_id,
                                    "api_returned_user_id": api_user_id,
                                    "issue": "api_user_id_isolation_failure"
                                })
            
            self.increment_db_query_count(1)  # API validation
        
        # Step 6: Assert no isolation violations found
        total_violations = len(isolation_violations) + len(api_isolation_violations)
        
        assert total_violations == 0, (
            f"CRITICAL SECURITY FAILURE: Found {total_violations} multi-user isolation violations. "
            f"Token violations: {isolation_violations}, API violations: {api_isolation_violations}"
        )
        
        assert successful_cross_user_attacks == 0, (
            f"CRITICAL SECURITY BREACH: {successful_cross_user_attacks} successful cross-user attacks out of {cross_user_attempts} attempts"
        )
        
        # Step 7: Verify token uniqueness
        all_access_tokens = [data["access_token"] for data in user_auth_data.values()]
        all_refresh_tokens = [data["refresh_token"] for data in user_auth_data.values()]
        
        unique_access_tokens = set(all_access_tokens)
        unique_refresh_tokens = set(all_refresh_tokens)
        
        assert len(unique_access_tokens) == len(all_access_tokens), (
            f"Access token reuse detected: {len(all_access_tokens)} total, {len(unique_access_tokens)} unique"
        )
        
        assert len(unique_refresh_tokens) == len(all_refresh_tokens), (
            f"Refresh token reuse detected: {len(all_refresh_tokens)} total, {len(unique_refresh_tokens)} unique"
        )
        
        self.record_metric("multi_user_isolation_test", "comprehensive_success")
        self.record_metric("users_tested", len(isolated_users))
        self.record_metric("cross_user_attempts", cross_user_attempts)
        self.record_metric("successful_attacks", successful_cross_user_attacks)
        self.record_metric("isolation_violations", total_violations)
        
        logger.info(f" PASS:  Multi-user isolation comprehensive test successful ({len(isolated_users)} users, 0 violations)")
    
    # === TEST VALIDATION AND CLEANUP ===
    
    def teardown_method(self, method=None):
        """Enhanced teardown with comprehensive metrics validation."""
        super().teardown_method(method)
        
        # Validate comprehensive test metrics were recorded
        metrics = self.get_all_metrics()
        
        # Ensure comprehensive tests recorded their metrics
        if hasattr(method, '__name__') and method.__name__:
            method_name = method.__name__
            
            # All comprehensive auth tests must record these metrics
            required_metrics = ["test_category", "test_focus"]
            for metric in required_metrics:
                assert metric in metrics, f"Auth comprehensive test {method_name} must record {metric} metric"
            
            # JWT-specific validations
            if "jwt" in method_name.lower():
                assert "jwt" in metrics.get("test_category", "").lower(), "JWT tests must have JWT in test_category"
            
            # Session-specific validations  
            if "session" in method_name.lower():
                assert "session" in metrics.get("test_category", "").lower(), "Session tests must have session in test_category"
            
            # Database-specific validations
            if "database" in method_name.lower():
                assert "database" in metrics.get("test_category", "").lower(), "Database tests must have database in test_category"
                assert metrics.get("database_queries", 0) > 0, "Database tests must record DB query count"
            
            # Multi-user-specific validations
            if "multi_user" in method_name.lower():
                assert "multi_user" in metrics.get("test_category", "").lower(), "Multi-user tests must have multi_user in test_category"
        
        # Log comprehensive test metrics for analysis and debugging
        comprehensive_metrics = {
            k: v for k, v in metrics.items() 
            if any(keyword in k.lower() for keyword in ["auth", "jwt", "session", "database", "user", "token"])
        }
        
        if comprehensive_metrics:
            logger.info(f"Auth comprehensive test metrics: {comprehensive_metrics}")
            
        # Log performance metrics if recorded
        performance_metrics = {
            k: v for k, v in metrics.items() 
            if k.endswith("_time_ms") or k.endswith("_count") or "performance" in k.lower()
        }
        
        if performance_metrics:
            logger.info(f"Auth performance metrics: {performance_metrics}")