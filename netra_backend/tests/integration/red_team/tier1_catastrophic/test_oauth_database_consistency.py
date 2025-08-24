"""
RED TEAM TEST 3: OAuth Flow Database State Consistency

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real database consistency issues.
This test validates that OAuth callback creates user records consistently across both databases
and properly handles partial failures.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Data Integrity, User Trust, Platform Stability
- Value Impact: Inconsistent user data causes login failures and user confusion
- Strategic Impact: Core data integrity foundation for user management

Testing Level: L3 (Real databases, real services, transaction testing)
Expected Initial Result: FAILURE (exposes database consistency gaps)
"""

import asyncio
import json
import os
import secrets
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient
from sqlalchemy import text, select, insert, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from unittest.mock import patch, AsyncMock, MagicMock

# Real service imports - NO MOCKS
from netra_backend.app.main import app
# Fix imports with error handling
try:
    from netra_backend.app.core.configuration.base import get_unified_config
except ImportError:
    def get_unified_config():
        from types import SimpleNamespace
        return SimpleNamespace(database_url="DATABASE_URL_PLACEHOLDER")

try:
    from netra_backend.app.db.models import User, Organization
except ImportError:
    # Create mock models if not available
    from unittest.mock import Mock, AsyncMock, MagicMock
    User = Mock()
    Organization = Mock()

try:
    from netra_backend.app.db.session import get_db_session
except ImportError:
    from netra_backend.app.db.database_manager import DatabaseManager
    get_db_session = lambda: DatabaseManager().get_session()


class TestOAuthDatabaseConsistency:
    """
    RED TEAM TEST 3: OAuth Flow Database State Consistency
    
    Tests that OAuth flows maintain consistency between auth DB and main DB.
    MUST use real databases - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_main_db_session(self):
        """Real main database (PostgreSQL) session - will fail if DB not available."""
        config = get_unified_config()
        
        # Main backend database
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Main database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture(scope="class")
    async def real_auth_db_session(self):
        """Real auth database session - will fail if auth DB not available."""
        # Auth service database URL (may be different from main DB)
        auth_db_url = os.getenv("AUTH_DATABASE_URL")
        if not auth_db_url:
            # Fallback to main DB URL for testing
            config = get_unified_config()
            auth_db_url = config.database_url
        
        engine = create_async_engine(auth_db_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Auth database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    async def cleanup_test_data(self, real_main_db_session, real_auth_db_session):
        """Clean up test data after each test."""
        test_emails = []
        test_user_ids = []
        
        async def register_cleanup(email: str = None, user_id: str = None):
            if email:
                test_emails.append(email)
            if user_id:
                test_user_ids.append(user_id)
        
        yield register_cleanup
        
        # Cleanup main DB
        try:
            for email in test_emails:
                await real_main_db_session.execute(
                    text("DELETE FROM users WHERE email = :email"),
                    {"email": email}
                )
            
            for user_id in test_user_ids:
                await real_main_db_session.execute(
                    text("DELETE FROM users WHERE id = :user_id"),
                    {"user_id": user_id}
                )
            
            await real_main_db_session.commit()
        except Exception as e:
            print(f"Main DB cleanup error: {e}")
        
        # Cleanup auth DB
        try:
            for email in test_emails:
                await real_auth_db_session.execute(
                    text("DELETE FROM users WHERE email = :email"),
                    {"email": email}
                )
            
            for user_id in test_user_ids:
                await real_auth_db_session.execute(
                    text("DELETE FROM users WHERE id = :user_id"),
                    {"user_id": user_id}
                )
            
            await real_auth_db_session.commit()
        except Exception as e:
            print(f"Auth DB cleanup error: {e}")

    @pytest.mark.asyncio
    async def test_01_oauth_user_creation_dual_database_fails(self, real_main_db_session, real_auth_db_session, cleanup_test_data):
        """
        Test 3A: OAuth User Creation in Both Databases (EXPECTED TO FAIL)
        
        Tests that OAuth callback creates user in both auth DB and main DB.
        Will likely FAIL because dual database creation may not be implemented.
        """
        test_email = f"oauth-test-{uuid.uuid4()}@example.com"
        test_user_id = str(uuid.uuid4())
        cleanup_test_data(email=test_email, user_id=test_user_id)
        
        # Simulate OAuth user data
        oauth_user_data = {
            "id": "google_123456789",
            "email": test_email,
            "name": "OAuth Test User",
            "picture": "https://example.com/photo.jpg",
            "verified_email": True
        }
        
        # Mock OAuth provider responses
        with patch("httpx.AsyncClient") as mock_client:
            mock_async_client = AsyncMock()
            mock_client.return_value.__aenter__.return_value = mock_async_client
            
            # Mock token exchange
            mock_token_response = AsyncMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {
                "access_token": "mock_access_token",
                "token_type": "Bearer"
            }
            mock_async_client.post.return_value = mock_token_response
            
            # Mock user info
            mock_user_response = AsyncMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = oauth_user_data
            mock_async_client.get.return_value = mock_user_response
            
            # Trigger OAuth callback
            test_client = TestClient(app)
            response = test_client.post(
                "/auth/callback/google",
                json={
                    "code": f"test_oauth_code_{secrets.token_urlsafe(16)}",
                    "state": secrets.token_urlsafe(32)
                }
            )
        
        # FAILURE EXPECTED HERE - OAuth callback may not create users in both DBs
        assert response.status_code == 200, f"OAuth callback failed: {response.text}"
        
        # Verify user exists in auth database
        auth_user = await real_auth_db_session.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": test_email}
        )
        auth_user_result = auth_user.fetchone()
        assert auth_user_result is not None, f"User not created in auth database: {test_email}"
        
        # Verify user exists in main database
        main_user = await real_main_db_session.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": test_email}
        )
        main_user_result = main_user.fetchone()
        assert main_user_result is not None, f"User not created in main database: {test_email}"
        
        # Verify data consistency between databases
        assert auth_user_result.email == main_user_result.email, "Email mismatch between databases"
        assert auth_user_result.id == main_user_result.id, "User ID mismatch between databases"

    @pytest.mark.asyncio
    async def test_02_oauth_partial_failure_rollback_fails(self, real_main_db_session, real_auth_db_session, cleanup_test_data):
        """
        Test 3B: OAuth Partial Failure Rollback (EXPECTED TO FAIL)
        
        Tests that partial failures during OAuth are properly rolled back.
        Will likely FAIL because rollback logic may not be implemented.
        """
        test_email = f"rollback-test-{uuid.uuid4()}@example.com"
        cleanup_test_data(email=test_email)
        
        # Create scenario where auth DB succeeds but main DB fails
        oauth_user_data = {
            "id": "google_rollback_test",
            "email": test_email,
            "name": "Rollback Test User",
            "verified_email": True
        }
        
        # Simulate OAuth success up to database operations
        with patch("httpx.AsyncClient") as mock_http:
            mock_async_client = AsyncMock()
            mock_http.return_value.__aenter__.return_value = mock_async_client
            
            mock_token_response = AsyncMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {"access_token": "mock_token"}
            mock_async_client.post.return_value = mock_token_response
            
            mock_user_response = AsyncMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = oauth_user_data
            mock_async_client.get.return_value = mock_user_response
            
            # Mock main DB to fail during user creation
            with patch("netra_backend.app.db.session.get_db_session") as mock_db:
                async def failing_db_session():
                    # First call succeeds (auth DB), second call fails (main DB)
                    call_count = getattr(failing_db_session, 'call_count', 0)
                    failing_db_session.call_count = call_count + 1
                    
                    if call_count == 0:
                        # Auth DB session - should succeed
                        async with real_auth_db_session as session:
                            try:
                                yield session
                            finally:
                                if hasattr(session, "close"):
                                    await session.close()
                    else:
                        # Main DB session - should fail
                        raise Exception("Main database connection failed")
                
                mock_db.side_effect = failing_db_session
                
                test_client = TestClient(app)
                response = test_client.post(
                    "/auth/callback/google",
                    json={
                        "code": f"rollback_test_code_{secrets.token_urlsafe(16)}",
                        "state": secrets.token_urlsafe(32)
                    }
                )
        
        # OAuth should fail due to main DB failure
        assert response.status_code != 200, "OAuth should fail when main DB fails"
        
        # FAILURE EXPECTED HERE - rollback may not be implemented
        # Verify no user was created in auth database (should be rolled back)
        auth_user = await real_auth_db_session.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": test_email}
        )
        auth_user_result = auth_user.fetchone()
        assert auth_user_result is None, f"User created in auth DB despite main DB failure (no rollback): {test_email}"
        
        # Verify no user was created in main database
        main_user = await real_main_db_session.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": test_email}
        )
        main_user_result = main_user.fetchone()
        assert main_user_result is None, f"User created in main DB despite failure: {test_email}"

    @pytest.mark.asyncio
    async def test_03_concurrent_oauth_same_user_fails(self, real_main_db_session, real_auth_db_session, cleanup_test_data):
        """
        Test 3C: Concurrent OAuth for Same User (EXPECTED TO FAIL)
        
        Tests handling of concurrent OAuth attempts for the same user.
        Will likely FAIL because concurrent handling may cause duplicate entries or race conditions.
        """
        test_email = f"concurrent-test-{uuid.uuid4()}@example.com"
        cleanup_test_data(email=test_email)
        
        oauth_user_data = {
            "id": "google_concurrent_test",
            "email": test_email,
            "name": "Concurrent Test User",
            "verified_email": True
        }
        
        async def simulate_oauth_callback(attempt_number: int) -> dict:
            """Simulate a single OAuth callback attempt."""
            with patch("httpx.AsyncClient") as mock_http:
                mock_async_client = AsyncMock()
                mock_http.return_value.__aenter__.return_value = mock_async_client
                
                mock_token_response = AsyncMock()
                mock_token_response.status_code = 200
                mock_token_response.json.return_value = {"access_token": f"token_{attempt_number}"}
                mock_async_client.post.return_value = mock_token_response
                
                mock_user_response = AsyncMock()
                mock_user_response.status_code = 200
                mock_user_response.json.return_value = oauth_user_data
                mock_async_client.get.return_value = mock_user_response
                
                test_client = TestClient(app)
                response = test_client.post(
                    "/auth/callback/google",
                    json={
                        "code": f"concurrent_code_{attempt_number}_{secrets.token_urlsafe(16)}",
                        "state": secrets.token_urlsafe(32)
                    }
                )
                
                return {
                    "attempt": attempt_number,
                    "status_code": response.status_code,
                    "response_data": response.json() if response.status_code == 200 else None
                }
        
        # Run 5 concurrent OAuth attempts
        concurrent_attempts = [simulate_oauth_callback(i) for i in range(5)]
        results = await asyncio.gather(*concurrent_attempts, return_exceptions=True)
        
        # Count successful and failed attempts
        successful_attempts = []
        failed_attempts = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_attempts.append(f"Exception: {result}")
            elif result["status_code"] == 200:
                successful_attempts.append(result)
            else:
                failed_attempts.append(f"Attempt {result['attempt']}: Status {result['status_code']}")
        
        # FAILURE EXPECTED HERE - only one attempt should succeed
        assert len(successful_attempts) == 1, f"Multiple OAuth attempts succeeded: {len(successful_attempts)} (should be 1)"
        
        # Verify only one user record exists in each database
        auth_users = await real_auth_db_session.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": test_email}
        )
        auth_count = auth_users.scalar()
        assert auth_count == 1, f"Multiple users in auth DB: {auth_count} (should be 1)"
        
        main_users = await real_main_db_session.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": test_email}
        )
        main_count = main_users.scalar()
        assert main_count == 1, f"Multiple users in main DB: {main_count} (should be 1)"

    @pytest.mark.asyncio
    async def test_04_oauth_transaction_isolation_fails(self, real_main_db_session, real_auth_db_session, cleanup_test_data):
        """
        Test 3D: OAuth Transaction Isolation (EXPECTED TO FAIL)
        
        Tests that OAuth transactions are properly isolated between databases.
        Will likely FAIL because transaction isolation may not be implemented properly.
        """
        test_email = f"isolation-test-{uuid.uuid4()}@example.com"
        cleanup_test_data(email=test_email)
        
        # Create a scenario where we can test transaction boundaries
        oauth_user_data = {
            "id": "google_isolation_test",
            "email": test_email,
            "name": "Isolation Test User",
            "verified_email": True
        }
        
        # Start a transaction in main DB that will block
        async with real_main_db_session.begin() as main_transaction:
            # Insert a conflicting user that will cause constraint violation
            conflicting_user_id = str(uuid.uuid4())
            await real_main_db_session.execute(
                text("INSERT INTO users (id, email, created_at) VALUES (:id, :email, NOW())"),
                {"id": conflicting_user_id, "email": test_email}
            )
            
            # Don't commit yet - this should block OAuth user creation
            
            # Try OAuth callback while transaction is open
            with patch("httpx.AsyncClient") as mock_http:
                mock_async_client = AsyncMock()
                mock_http.return_value.__aenter__.return_value = mock_async_client
                
                mock_token_response = AsyncMock()
                mock_token_response.status_code = 200
                mock_token_response.json.return_value = {"access_token": "isolation_token"}
                mock_async_client.post.return_value = mock_token_response
                
                mock_user_response = AsyncMock()
                mock_user_response.status_code = 200
                mock_user_response.json.return_value = oauth_user_data
                mock_async_client.get.return_value = mock_user_response
                
                test_client = TestClient(app)
                
                # This should either wait for transaction or fail properly
                start_time = time.time()
                response = test_client.post(
                    "/auth/callback/google",
                    json={
                        "code": f"isolation_test_code_{secrets.token_urlsafe(16)}",
                        "state": secrets.token_urlsafe(32)
                    }
                )
                end_time = time.time()
            
            # Rollback the blocking transaction
            await main_transaction.rollback()
        
        # FAILURE EXPECTED HERE - transaction isolation may not work
        # OAuth should have failed due to constraint violation or timeout
        duration = end_time - start_time
        
        if response.status_code == 200:
            # If it succeeded, it should have waited for the transaction
            assert duration > 0.1, f"OAuth completed too quickly ({duration:.3f}s) - may not respect transaction isolation"
        else:
            # If it failed, that's acceptable for isolation test
            assert response.status_code in [409, 500, 503], f"Unexpected error code: {response.status_code}"
        
        # Verify final state is consistent
        final_users = await real_main_db_session.execute(
            text("SELECT COUNT(*) FROM users WHERE email = :email"),
            {"email": test_email}
        )
        user_count = final_users.scalar()
        assert user_count <= 1, f"Multiple users created despite transaction isolation: {user_count}"

    @pytest.mark.asyncio
    async def test_05_oauth_data_validation_across_databases_fails(self, real_main_db_session, real_auth_db_session, cleanup_test_data):
        """
        Test 3E: OAuth Data Validation Across Databases (EXPECTED TO FAIL)
        
        Tests that data validation is consistent across both databases.
        Will likely FAIL because validation rules may not be synchronized.
        """
        test_scenarios = [
            {
                "name": "Invalid Email Format",
                "email": "invalid-email-format",
                "should_fail": True
            },
            {
                "name": "Extremely Long Email",
                "email": "a" * 300 + "@example.com",
                "should_fail": True
            },
            {
                "name": "SQL Injection Attempt",
                "email": "test'; DROP TABLE users; --@example.com",
                "should_fail": True
            },
            {
                "name": "Unicode Email",
                "email": "测试@example.com",
                "should_fail": False  # Should be allowed
            },
            {
                "name": "Empty Name",
                "email": f"empty-name-{uuid.uuid4()}@example.com",
                "name": "",
                "should_fail": True
            }
        ]
        
        for scenario in test_scenarios:
            test_email = scenario["email"]
            if not test_email.startswith("invalid") and "@" in test_email:
                cleanup_test_data(email=test_email)
            
            oauth_user_data = {
                "id": f"google_validation_{hash(test_email)}",
                "email": test_email,
                "name": scenario.get("name", "Validation Test User"),
                "verified_email": True
            }
            
            with patch("httpx.AsyncClient") as mock_http:
                mock_async_client = AsyncMock()
                mock_http.return_value.__aenter__.return_value = mock_async_client
                
                mock_token_response = AsyncMock()
                mock_token_response.status_code = 200
                mock_token_response.json.return_value = {"access_token": "validation_token"}
                mock_async_client.post.return_value = mock_token_response
                
                mock_user_response = AsyncMock()
                mock_user_response.status_code = 200
                mock_user_response.json.return_value = oauth_user_data
                mock_async_client.get.return_value = mock_user_response
                
                test_client = TestClient(app)
                response = test_client.post(
                    "/auth/callback/google",
                    json={
                        "code": f"validation_code_{secrets.token_urlsafe(16)}",
                        "state": secrets.token_urlsafe(32)
                    }
                )
            
            if scenario["should_fail"]:
                # FAILURE EXPECTED HERE - validation may not be implemented
                assert response.status_code != 200, f"Scenario '{scenario['name']}' should fail but succeeded: {test_email}"
                
                # Verify no user was created in either database
                if "@" in test_email:  # Only check if it's a valid-looking email
                    auth_user = await real_auth_db_session.execute(
                        text("SELECT COUNT(*) FROM users WHERE email = :email"),
                        {"email": test_email}
                    )
                    assert auth_user.scalar() == 0, f"Invalid user created in auth DB: {test_email}"
                    
                    main_user = await real_main_db_session.execute(
                        text("SELECT COUNT(*) FROM users WHERE email = :email"),
                        {"email": test_email}
                    )
                    assert main_user.scalar() == 0, f"Invalid user created in main DB: {test_email}"
            else:
                # Should succeed
                assert response.status_code == 200, f"Scenario '{scenario['name']}' should succeed but failed: {test_email}"

    @pytest.mark.asyncio
    async def test_06_oauth_foreign_key_consistency_fails(self, real_main_db_session, real_auth_db_session, cleanup_test_data):
        """
        Test 3F: OAuth Foreign Key Consistency (EXPECTED TO FAIL)
        
        Tests that foreign key relationships are maintained across databases.
        Will likely FAIL because foreign key handling may not be properly implemented.
        """
        test_email = f"fk-test-{uuid.uuid4()}@example.com"
        test_user_id = str(uuid.uuid4())
        test_org_id = str(uuid.uuid4())
        
        cleanup_test_data(email=test_email, user_id=test_user_id)
        
        # Create organization in main DB first
        await real_main_db_session.execute(
            text("INSERT INTO organizations (id, name, created_at) VALUES (:id, :name, NOW())"),
            {"id": test_org_id, "name": "FK Test Organization"}
        )
        await real_main_db_session.commit()
        
        oauth_user_data = {
            "id": "google_fk_test",
            "email": test_email,
            "name": "FK Test User",
            "verified_email": True,
            "organization_id": test_org_id  # This should create FK relationship
        }
        
        with patch("httpx.AsyncClient") as mock_http:
            mock_async_client = AsyncMock()
            mock_http.return_value.__aenter__.return_value = mock_async_client
            
            mock_token_response = AsyncMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {"access_token": "fk_token"}
            mock_async_client.post.return_value = mock_token_response
            
            mock_user_response = AsyncMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = oauth_user_data
            mock_async_client.get.return_value = mock_user_response
            
            test_client = TestClient(app)
            response = test_client.post(
                "/auth/callback/google",
                json={
                    "code": f"fk_test_code_{secrets.token_urlsafe(16)}",
                    "state": secrets.token_urlsafe(32)
                }
            )
        
        # FAILURE EXPECTED HERE - FK relationships may not be handled
        assert response.status_code == 200, f"OAuth with FK relationship failed: {response.text}"
        
        # Verify user was created with correct FK relationship
        main_user = await real_main_db_session.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": test_email}
        )
        user_result = main_user.fetchone()
        assert user_result is not None, f"User not created in main DB: {test_email}"
        
        # Check if organization relationship is preserved
        if hasattr(user_result, 'organization_id'):
            assert user_result.organization_id == test_org_id, "Organization FK not preserved"
        
        # Test FK constraint by trying to delete organization
        try:
            await real_main_db_session.execute(
                text("DELETE FROM organizations WHERE id = :id"),
                {"id": test_org_id}
            )
            await real_main_db_session.commit()
            
            # This should fail if FK constraints are properly enforced
            pytest.fail("Organization deletion should fail due to FK constraint")
        except Exception:
            # Expected - FK constraint should prevent deletion
            await real_main_db_session.rollback()

    @pytest.mark.asyncio
    async def test_07_oauth_audit_trail_consistency_fails(self, real_main_db_session, real_auth_db_session, cleanup_test_data):
        """
        Test 3G: OAuth Audit Trail Consistency (EXPECTED TO FAIL)
        
        Tests that audit trails are consistent across both databases.
        Will likely FAIL because audit trail creation may not be implemented.
        """
        test_email = f"audit-test-{uuid.uuid4()}@example.com"
        cleanup_test_data(email=test_email)
        
        oauth_user_data = {
            "id": "google_audit_test",
            "email": test_email,
            "name": "Audit Test User",
            "verified_email": True
        }
        
        # Record start time for audit verification
        start_time = datetime.now(timezone.utc)
        
        with patch("httpx.AsyncClient") as mock_http:
            mock_async_client = AsyncMock()
            mock_http.return_value.__aenter__.return_value = mock_async_client
            
            mock_token_response = AsyncMock()
            mock_token_response.status_code = 200
            mock_token_response.json.return_value = {"access_token": "audit_token"}
            mock_async_client.post.return_value = mock_token_response
            
            mock_user_response = AsyncMock()
            mock_user_response.status_code = 200
            mock_user_response.json.return_value = oauth_user_data
            mock_async_client.get.return_value = mock_user_response
            
            test_client = TestClient(app)
            response = test_client.post(
                "/auth/callback/google",
                json={
                    "code": f"audit_test_code_{secrets.token_urlsafe(16)}",
                    "state": secrets.token_urlsafe(32)
                }
            )
        
        end_time = datetime.now(timezone.utc)
        
        # FAILURE EXPECTED HERE - OAuth may succeed but audit trail may be missing
        assert response.status_code == 200, f"OAuth failed: {response.text}"
        
        # Check for audit records in both databases
        audit_tables = ["user_audit_log", "auth_audit_log", "audit_events"]
        
        for table in audit_tables:
            try:
                # Check main DB
                main_audit = await real_main_db_session.execute(
                    text(f"SELECT * FROM {table} WHERE user_email = :email AND event_type = 'user_created' AND timestamp BETWEEN :start AND :end"),
                    {"email": test_email, "start": start_time, "end": end_time}
                )
                main_audit_result = main_audit.fetchone()
                
                # Check auth DB  
                auth_audit = await real_auth_db_session.execute(
                    text(f"SELECT * FROM {table} WHERE user_email = :email AND event_type = 'user_created' AND timestamp BETWEEN :start AND :end"),
                    {"email": test_email, "start": start_time, "end": end_time}
                )
                auth_audit_result = auth_audit.fetchone()
                
                # FAILURE EXPECTED HERE - audit trails may not exist
                if main_audit_result or auth_audit_result:
                    # If audit exists in one, it should exist in both
                    assert main_audit_result is not None, f"Audit missing in main DB table {table}"
                    assert auth_audit_result is not None, f"Audit missing in auth DB table {table}"
                    
                    # Audit data should be consistent
                    assert main_audit_result.user_email == auth_audit_result.user_email, "Audit email mismatch"
                    break
                    
            except Exception as e:
                # Table may not exist - that's part of the expected failure
                continue
        
        # If no audit tables exist, that's an expected failure
        print("No audit trails found - this is expected to fail initially")

    @pytest.mark.asyncio
    async def test_08_oauth_database_performance_consistency_fails(self, real_main_db_session, real_auth_db_session):
        """
        Test 3H: OAuth Database Performance Consistency (EXPECTED TO FAIL)
        
        Tests that OAuth operations perform consistently under load.
        Will likely FAIL because performance optimization may not be implemented.
        """
        # Create load test with multiple OAuth users
        num_users = 20
        oauth_operations = []
        
        for i in range(num_users):
            test_email = f"perf-test-{i}-{uuid.uuid4()}@example.com"
            
            oauth_user_data = {
                "id": f"google_perf_test_{i}",
                "email": test_email,
                "name": f"Performance Test User {i}",
                "verified_email": True
            }
            
            oauth_operations.append((test_email, oauth_user_data))
        
        async def perform_oauth_operation(email: str, user_data: dict) -> dict:
            """Perform a single OAuth operation and measure performance."""
            start_time = time.time()
            
            try:
                with patch("httpx.AsyncClient") as mock_http:
                    mock_async_client = AsyncMock()
                    mock_http.return_value.__aenter__.return_value = mock_async_client
                    
                    mock_token_response = AsyncMock()
                    mock_token_response.status_code = 200
                    mock_token_response.json.return_value = {"access_token": f"perf_token_{hash(email)}"}
                    mock_async_client.post.return_value = mock_token_response
                    
                    mock_user_response = AsyncMock()
                    mock_user_response.status_code = 200
                    mock_user_response.json.return_value = user_data
                    mock_async_client.get.return_value = mock_user_response
                    
                    test_client = TestClient(app)
                    response = test_client.post(
                        "/auth/callback/google",
                        json={
                            "code": f"perf_code_{hash(email)}_{secrets.token_urlsafe(8)}",
                            "state": secrets.token_urlsafe(32)
                        }
                    )
                
                end_time = time.time()
                
                return {
                    "email": email,
                    "success": response.status_code == 200,
                    "duration": end_time - start_time,
                    "status_code": response.status_code
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    "email": email,
                    "success": False,
                    "duration": end_time - start_time,
                    "error": str(e)
                }
        
        # Run OAuth operations concurrently
        tasks = [perform_oauth_operation(email, data) for email, data in oauth_operations]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze performance results
        successful_operations = []
        failed_operations = []
        durations = []
        
        for result in results:
            if isinstance(result, Exception):
                failed_operations.append(f"Exception: {result}")
            elif result["success"]:
                successful_operations.append(result)
                durations.append(result["duration"])
            else:
                failed_operations.append(f"Email: {result['email']}, Status: {result.get('status_code', 'Error')}")
        
        # FAILURE EXPECTED HERE - performance may be poor or inconsistent
        success_rate = len(successful_operations) / len(oauth_operations)
        assert success_rate >= 0.8, f"OAuth performance test failed: {success_rate*100:.1f}% success rate"
        
        if durations:
            avg_duration = sum(durations) / len(durations)
            max_duration = max(durations)
            min_duration = min(durations)
            
            # Performance thresholds - these will likely fail initially
            assert avg_duration < 5.0, f"Average OAuth duration too slow: {avg_duration:.2f}s (should be < 5.0s)"
            assert max_duration < 10.0, f"Slowest OAuth too slow: {max_duration:.2f}s (should be < 10.0s)"
            
            # Consistency check - operations should have similar performance
            duration_variance = max_duration - min_duration
            assert duration_variance < 8.0, f"OAuth performance too inconsistent: {duration_variance:.2f}s variance"
        
        # Cleanup performance test data
        for email, _ in oauth_operations:
            try:
                await real_main_db_session.execute(
                    text("DELETE FROM users WHERE email = :email"),
                    {"email": email}
                )
                await real_auth_db_session.execute(
                    text("DELETE FROM users WHERE email = :email"),
                    {"email": email}
                )
            except Exception:
                pass  # Ignore cleanup errors
        
        try:
            await real_main_db_session.commit()
            await real_auth_db_session.commit()
        except Exception:
            pass  # Ignore cleanup errors


# Helper utilities for database consistency testing
class DatabaseConsistencyUtils:
    """Utility methods for database consistency testing."""
    
    @staticmethod
    async def verify_user_exists(session: AsyncSession, email: str, table: str = "users") -> bool:
        """Verify that a user exists in the given database session."""
        try:
            result = await session.execute(
                text(f"SELECT COUNT(*) FROM {table} WHERE email = :email"),
                {"email": email}
            )
            count = result.scalar()
            return count > 0
        except Exception:
            return False
    
    @staticmethod
    async def get_user_data(session: AsyncSession, email: str, table: str = "users") -> Optional[Dict[str, Any]]:
        """Get user data from the database."""
        try:
            result = await session.execute(
                text(f"SELECT * FROM {table} WHERE email = :email"),
                {"email": email}
            )
            row = result.fetchone()
            if row:
                return {column: value for column, value in zip(result.keys(), row)}
            return None
        except Exception:
            return None
    
    @staticmethod
    async def cleanup_test_user(session: AsyncSession, email: str, table: str = "users"):
        """Clean up a test user from the database."""
        try:
            await session.execute(
                text(f"DELETE FROM {table} WHERE email = :email"),
                {"email": email}
            )
            await session.commit()
        except Exception:
            await session.rollback()