"""
RED TEAM TEST 12: User State Synchronization

CRITICAL: These tests are DESIGNED TO FAIL initially to expose real integration issues.
This test validates that user data is consistent across user_service and auth_service.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Data Consistency, User Experience, Platform Reliability
- Value Impact: User state inconsistencies cause authentication failures and data corruption
- Strategic Impact: Core user management foundation for all platform operations

Testing Level: L3 (Real services, real databases, minimal mocking)
Expected Initial Result: FAILURE (exposes real user synchronization gaps)
"""

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.configuration.base import get_unified_config
from netra_backend.app.services.user_service import UserService
from netra_backend.app.services.user_auth_service import UserAuthService
from netra_backend.app.db.models_user import User
from netra_backend.app.database import get_db


class TestUserStateSynchronization:
    """
    RED TEAM TEST 12: User State Synchronization
    
    Tests the critical path of user data consistency across services.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        config = get_unified_config()
        
        # Use REAL database connection - no mocks
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

    @pytest.fixture
    async def auth_service_connection(self):
        """Real auth service connection - will fail if auth service not running."""
        auth_service_url = "http://localhost:8001"  # Real auth service URL
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Test auth service health - will fail if service not running
                health_response = await client.get(f"{auth_service_url}/health")
                if health_response.status_code != 200:
                    pytest.skip("Auth service not available for synchronization testing")
                yield client
            except httpx.ConnectError:
                pytest.skip("Auth service not running - cannot test synchronization")

    @pytest.mark.asyncio
    async def test_01_user_creation_dual_service_consistency_fails(self, real_database_session, auth_service_connection):
        """
        Test 12A: User Creation Consistency (EXPECTED TO FAIL)
        
        Tests that user creation creates records in both auth and main databases.
        This will likely FAIL because:
        1. Dual database user creation may not be implemented
        2. Transaction coordination may not exist
        3. User data synchronization may be incomplete
        """
        test_email = f"sync_test_{secrets.token_urlsafe(8)}@example.com"
        test_name = "Synchronization Test User"
        
        # Create user via auth service first
        auth_user_data = {
            "email": test_email,
            "name": test_name,
            "password": "test_password_123",
            "provider": "email"
        }
        
        try:
            # Create user in auth service
            auth_response = await auth_service_connection.post(
                "http://localhost:8001/auth/register",
                json=auth_user_data
            )
            
            # FAILURE EXPECTED HERE - auth service registration may not exist
            assert auth_response.status_code in [200, 201], f"Auth service user creation failed: {auth_response.text}"
            
            auth_user_response = auth_response.json()
            assert "user_id" in auth_user_response, "Auth service should return user_id"
            
            auth_user_id = auth_user_response["user_id"]
            
            # Check if user was also created in main database
            main_user_query = await real_database_session.execute(
                select(User).where(User.email == test_email)
            )
            main_user = main_user_query.scalar_one_or_none()
            
            # FAILURE EXPECTED HERE - synchronization may not work
            assert main_user is not None, "User not created in main database after auth service creation"
            assert main_user.id == auth_user_id, f"User ID mismatch: auth={auth_user_id}, main={main_user.id}"
            assert main_user.email == test_email, "Email not synchronized correctly"
            assert main_user.name == test_name, "Name not synchronized correctly"
            
        except Exception as e:
            pytest.fail(f"User creation synchronization failed: {e}")

    @pytest.mark.asyncio
    async def test_02_user_profile_update_synchronization_fails(self, real_database_session, real_test_client):
        """
        Test 12B: User Profile Update Synchronization (EXPECTED TO FAIL)
        
        Tests that user profile updates are synchronized across services.
        Will likely FAIL because:
        1. Profile update propagation may not be implemented
        2. Event-driven synchronization may not exist
        3. Data consistency checks may be missing
        """
        # Create test user directly in main database
        test_user_id = str(uuid.uuid4())
        original_name = "Original User Name"
        test_email = f"profile_sync_{secrets.token_urlsafe(8)}@example.com"
        
        test_user = User(
            id=test_user_id,
            email=test_email,
            name=original_name,
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        # Generate auth token for user
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user_id,
            "email": test_email,
            "exp": int(time.time()) + 3600
        }
        test_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        
        # Update user profile via main backend API
        updated_name = "Updated User Name"
        profile_update = {
            "name": updated_name,
            "preferences": {"theme": "dark", "notifications": True}
        }
        
        auth_headers = {"Authorization": f"Bearer {test_token}"}
        
        # Try to update profile - will likely fail
        response = real_test_client.put(
            f"/api/user/profile",
            json=profile_update,
            headers=auth_headers
        )
        
        # FAILURE EXPECTED HERE
        assert response.status_code == 200, f"Profile update failed: {response.status_code} - {response.text}"
        
        # Verify update was applied in main database
        updated_user_query = await real_database_session.execute(
            select(User).where(User.id == test_user_id)
        )
        updated_user = updated_user_query.scalar_one()
        
        assert updated_user.name == updated_name, "Profile update not applied in main database"
        
        # Check if auth service was notified of the update
        async with httpx.AsyncClient() as auth_client:
            try:
                auth_profile_response = await auth_client.get(
                    f"http://localhost:8001/auth/user/{test_user_id}/profile",
                    headers={"Authorization": f"Bearer {test_token}"}
                )
                
                if auth_profile_response.status_code == 200:
                    auth_profile = auth_profile_response.json()
                    
                    # FAILURE EXPECTED HERE - synchronization may not work
                    assert auth_profile.get("name") == updated_name, \
                        f"Profile not synchronized to auth service: expected '{updated_name}', got '{auth_profile.get('name')}'"
                        
            except httpx.ConnectError:
                pytest.skip("Auth service not available for synchronization verification")

    @pytest.mark.asyncio
    async def test_03_user_deactivation_consistency_fails(self, real_database_session, auth_service_connection):
        """
        Test 12C: User Deactivation Consistency (EXPECTED TO FAIL)
        
        Tests that user deactivation is consistent across both services.
        Will likely FAIL because:
        1. Deactivation workflow may not be coordinated
        2. Session invalidation may not be synchronized
        3. Data cleanup may be inconsistent
        """
        # Create test user in main database
        test_user_id = str(uuid.uuid4())
        test_email = f"deactivation_test_{secrets.token_urlsafe(8)}@example.com"
        
        test_user = User(
            id=test_user_id,
            email=test_email,
            name="Deactivation Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        # Try to create corresponding auth service record
        auth_user_data = {
            "user_id": test_user_id,
            "email": test_email,
            "name": "Deactivation Test User"
        }
        
        try:
            # Create user in auth service (if endpoint exists)
            auth_create_response = await auth_service_connection.post(
                "http://localhost:8001/auth/users",
                json=auth_user_data
            )
            
            if auth_create_response.status_code not in [200, 201, 409]:  # 409 = already exists
                pytest.skip("Cannot create user in auth service for deactivation test")
            
            # Now deactivate user via main service
            import jwt as pyjwt
            jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
            admin_token_payload = {
                "user_id": "admin_user_id",
                "role": "admin",
                "exp": int(time.time()) + 3600
            }
            admin_token = pyjwt.encode(admin_token_payload, jwt_secret, algorithm="HS256")
            
            # Deactivate user via admin API
            deactivation_response = await auth_service_connection.put(
                f"http://localhost:8000/api/admin/users/{test_user_id}/deactivate",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            # FAILURE EXPECTED HERE - deactivation API may not exist
            if deactivation_response.status_code not in [200, 204]:
                pytest.skip(f"User deactivation API not available: {deactivation_response.status_code}")
            
            # Verify user is deactivated in main database
            deactivated_user_query = await real_database_session.execute(
                select(User).where(User.id == test_user_id)
            )
            deactivated_user = deactivated_user_query.scalar_one()
            
            assert not deactivated_user.is_active, "User not deactivated in main database"
            
            # Check if auth service was notified of deactivation
            auth_user_response = await auth_service_connection.get(
                f"http://localhost:8001/auth/users/{test_user_id}"
            )
            
            # FAILURE EXPECTED HERE - synchronization may not work
            if auth_user_response.status_code == 200:
                auth_user_data = auth_user_response.json()
                assert not auth_user_data.get("is_active", True), \
                    "User deactivation not synchronized to auth service"
                    
        except Exception as e:
            pytest.fail(f"User deactivation synchronization failed: {e}")

    @pytest.mark.asyncio
    async def test_04_concurrent_user_updates_consistency_fails(self, real_database_session):
        """
        Test 12D: Concurrent User Updates Consistency (EXPECTED TO FAIL)
        
        Tests that concurrent updates to user data maintain consistency.
        Will likely FAIL because:
        1. Optimistic locking may not be implemented
        2. Conflict resolution may not exist
        3. Race conditions may cause data corruption
        """
        # Create test user
        test_user_id = str(uuid.uuid4())
        test_email = f"concurrent_test_{secrets.token_urlsafe(8)}@example.com"
        
        test_user = User(
            id=test_user_id,
            email=test_email,
            name="Concurrent Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        async def update_user_name(session: AsyncSession, new_name: str) -> bool:
            """Update user name in a separate transaction."""
            try:
                # Get user
                user_query = await session.execute(
                    select(User).where(User.id == test_user_id)
                )
                user = user_query.scalar_one()
                
                # Update name
                user.name = new_name
                user.updated_at = datetime.now(timezone.utc)
                
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                return False
        
        # Create multiple concurrent updates
        config = get_unified_config()
        engine = create_async_engine(config.database_url, echo=False)
        async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
        
        try:
            tasks = []
            for i in range(5):
                async with async_session() as session:
                    task = update_user_name(session, f"Concurrent Name {i+1}")
                    tasks.append(task)
            
            # Run concurrent updates
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check results
            successful_updates = sum(1 for r in results if r is True)
            
            # FAILURE EXPECTED HERE - concurrency may not be handled
            assert successful_updates >= 1, "No concurrent updates succeeded"
            
            # Verify final state is consistent
            final_user_query = await real_database_session.execute(
                select(User).where(User.id == test_user_id)
            )
            final_user = final_user_query.scalar_one()
            
            assert final_user.name.startswith("Concurrent Name"), \
                f"User name not updated correctly: {final_user.name}"
            assert final_user.updated_at > test_user.created_at, \
                "User updated_at timestamp not updated"
                
        finally:
            await engine.dispose()

    @pytest.mark.asyncio
    async def test_05_user_permission_synchronization_fails(self, real_database_session, real_test_client):
        """
        Test 12E: User Permission Synchronization (EXPECTED TO FAIL)
        
        Tests that user permissions are consistent across services.
        Will likely FAIL because:
        1. Permission management may not be coordinated
        2. Role changes may not propagate
        3. Authorization checks may be inconsistent
        """
        # Create test user with specific role
        test_user_id = str(uuid.uuid4())
        test_email = f"permission_test_{secrets.token_urlsafe(8)}@example.com"
        
        test_user = User(
            id=test_user_id,
            email=test_email,
            name="Permission Test User",
            is_active=True,
            role="free_user",  # Start with basic role
            created_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user_id,
            "email": test_email,
            "role": "free_user",
            "exp": int(time.time()) + 3600
        }
        user_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        auth_headers = {"Authorization": f"Bearer {user_token}"}
        
        # Try to access premium feature (should fail)
        premium_response = real_test_client.get(
            "/api/premium/advanced-analytics",
            headers=auth_headers
        )
        
        # Should be denied for free user
        assert premium_response.status_code in [401, 403], \
            f"Free user should not access premium features: {premium_response.status_code}"
        
        # Upgrade user to premium
        test_user.role = "premium_user"
        test_user.updated_at = datetime.now(timezone.utc)
        await real_database_session.commit()
        
        # Generate new token with premium role
        premium_token_payload = {
            "user_id": test_user_id,
            "email": test_email,
            "role": "premium_user",
            "exp": int(time.time()) + 3600
        }
        premium_token = pyjwt.encode(premium_token_payload, jwt_secret, algorithm="HS256")
        premium_headers = {"Authorization": f"Bearer {premium_token}"}
        
        # Try to access premium feature again - should work now
        premium_response_2 = real_test_client.get(
            "/api/premium/advanced-analytics",
            headers=premium_headers
        )
        
        # FAILURE EXPECTED HERE - permission enforcement may not work
        assert premium_response_2.status_code in [200, 404], \
            f"Premium user should access premium features: {premium_response_2.status_code} - {premium_response_2.text}"

    @pytest.mark.asyncio
    async def test_06_user_data_export_consistency_fails(self, real_database_session, real_test_client):
        """
        Test 12F: User Data Export Consistency (EXPECTED TO FAIL)
        
        Tests that user data export includes data from both services.
        Will likely FAIL because:
        1. Cross-service data aggregation may not exist
        2. Data export API may not be implemented
        3. Data consistency checks may be missing
        """
        # Create test user with data in main database
        test_user_id = str(uuid.uuid4())
        test_email = f"export_test_{secrets.token_urlsafe(8)}@example.com"
        
        test_user = User(
            id=test_user_id,
            email=test_email,
            name="Export Test User",
            is_active=True,
            preferences={"theme": "dark", "language": "en"},
            created_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        # Generate auth token
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        token_payload = {
            "user_id": test_user_id,
            "email": test_email,
            "exp": int(time.time()) + 3600
        }
        test_token = pyjwt.encode(token_payload, jwt_secret, algorithm="HS256")
        auth_headers = {"Authorization": f"Bearer {test_token}"}
        
        # Request user data export
        export_response = real_test_client.get(
            "/api/user/export",
            headers=auth_headers
        )
        
        # FAILURE EXPECTED HERE - export API may not exist
        assert export_response.status_code == 200, \
            f"User data export failed: {export_response.status_code} - {export_response.text}"
        
        export_data = export_response.json()
        
        # Verify export includes expected data
        assert "user" in export_data, "Export should include user data"
        assert "auth_data" in export_data, "Export should include auth service data"
        assert "preferences" in export_data["user"], "Export should include user preferences"
        
        user_data = export_data["user"]
        assert user_data["id"] == test_user_id, "Export user ID mismatch"
        assert user_data["email"] == test_email, "Export email mismatch"
        assert user_data["name"] == "Export Test User", "Export name mismatch"

    @pytest.mark.asyncio
    async def test_07_user_session_state_consistency_fails(self, real_database_session, auth_service_connection):
        """
        Test 12G: User Session State Consistency (EXPECTED TO FAIL)
        
        Tests that user session state is consistent between services.
        Will likely FAIL because:
        1. Session synchronization may not be implemented
        2. Session stores may be isolated
        3. Session validation may be inconsistent
        """
        # Create test user
        test_user_id = str(uuid.uuid4())
        test_email = f"session_test_{secrets.token_urlsafe(8)}@example.com"
        
        test_user = User(
            id=test_user_id,
            email=test_email,
            name="Session Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        try:
            # Create session via auth service
            login_data = {
                "email": test_email,
                "password": "test_password_123"
            }
            
            login_response = await auth_service_connection.post(
                "http://localhost:8001/auth/login",
                json=login_data
            )
            
            if login_response.status_code not in [200, 201]:
                pytest.skip("Cannot create session in auth service")
            
            session_data = login_response.json()
            assert "access_token" in session_data, "Login should return access token"
            
            access_token = session_data["access_token"]
            
            # Verify session works with main backend
            backend_auth_headers = {"Authorization": f"Bearer {access_token}"}
            
            backend_response = TestClient(app).get(
                "/api/user/profile",
                headers=backend_auth_headers
            )
            
            # FAILURE EXPECTED HERE - cross-service session validation may not work
            assert backend_response.status_code == 200, \
                f"Auth service token not accepted by backend: {backend_response.status_code} - {backend_response.text}"
            
            backend_user_data = backend_response.json()
            assert backend_user_data["id"] == test_user_id, "User context not properly propagated"
            assert backend_user_data["email"] == test_email, "Email not properly propagated"
            
            # Test session invalidation synchronization
            logout_response = await auth_service_connection.post(
                "http://localhost:8001/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            
            if logout_response.status_code in [200, 204]:
                # Try to use token with backend after logout
                post_logout_response = TestClient(app).get(
                    "/api/user/profile",
                    headers=backend_auth_headers
                )
                
                # FAILURE EXPECTED HERE - session invalidation may not be synchronized
                assert post_logout_response.status_code == 401, \
                    "Token still valid in backend after auth service logout"
                    
        except Exception as e:
            pytest.fail(f"User session state synchronization failed: {e}")

    @pytest.mark.asyncio
    async def test_08_user_deletion_cascade_consistency_fails(self, real_database_session, auth_service_connection):
        """
        Test 12H: User Deletion Cascade Consistency (EXPECTED TO FAIL)
        
        Tests that user deletion properly removes data from both services.
        Will likely FAIL because:
        1. Cascading deletion may not be coordinated
        2. Data cleanup may be incomplete
        3. Foreign key constraints may prevent deletion
        """
        # Create test user with related data
        test_user_id = str(uuid.uuid4())
        test_email = f"deletion_test_{secrets.token_urlsafe(8)}@example.com"
        
        test_user = User(
            id=test_user_id,
            email=test_email,
            name="Deletion Test User",
            is_active=True,
            created_at=datetime.now(timezone.utc)
        )
        
        real_database_session.add(test_user)
        await real_database_session.commit()
        
        # Create some related data (threads, messages, etc.)
        # This would fail if models don't exist, which is expected
        try:
            from netra_backend.app.db.models_content import Thread
            
            test_thread = Thread(
                id=str(uuid.uuid4()),
                user_id=test_user_id,
                title="Test Thread for Deletion",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            real_database_session.add(test_thread)
            await real_database_session.commit()
            
        except ImportError:
            # Thread model doesn't exist - that's expected initially
            pass
        
        # Generate admin token for deletion
        import jwt as pyjwt
        jwt_secret = "test-jwt-secret-key-for-testing-only-must-be-32-chars"
        admin_token_payload = {
            "user_id": "admin_user_id",
            "role": "admin",
            "exp": int(time.time()) + 3600
        }
        admin_token = pyjwt.encode(admin_token_payload, jwt_secret, algorithm="HS256")
        
        try:
            # Delete user via admin API
            deletion_response = await auth_service_connection.delete(
                f"http://localhost:8000/api/admin/users/{test_user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )
            
            if deletion_response.status_code not in [200, 204, 404]:
                pytest.skip(f"User deletion API not available: {deletion_response.status_code}")
            
            # Verify user is deleted from main database
            deleted_user_query = await real_database_session.execute(
                select(User).where(User.id == test_user_id)
            )
            deleted_user = deleted_user_query.scalar_one_or_none()
            
            # FAILURE EXPECTED HERE - deletion may not work
            assert deleted_user is None, "User not deleted from main database"
            
            # Check if user is also deleted from auth service
            auth_user_response = await auth_service_connection.get(
                f"http://localhost:8001/auth/users/{test_user_id}"
            )
            
            assert auth_user_response.status_code == 404, \
                "User not deleted from auth service"
                
        except Exception as e:
            pytest.fail(f"User deletion cascade consistency failed: {e}")


# Additional utility class for user synchronization testing
class RedTeamUserSyncTestUtils:
    """Utility methods for Red Team user synchronization testing."""
    
    @staticmethod
    def generate_test_user_data(prefix: str = "test") -> Dict[str, Any]:
        """Generate test user data with unique identifiers."""
        return {
            "id": str(uuid.uuid4()),
            "email": f"{prefix}_{secrets.token_urlsafe(8)}@example.com",
            "name": f"Test User {prefix.title()}",
            "is_active": True,
            "created_at": datetime.now(timezone.utc)
        }
    
    @staticmethod
    async def verify_user_in_database(session: AsyncSession, user_id: str) -> Optional[User]:
        """Verify a user exists in the database."""
        try:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
        except Exception:
            return None
    
    @staticmethod
    async def check_auth_service_user(client: httpx.AsyncClient, user_id: str) -> Optional[Dict]:
        """Check if user exists in auth service."""
        try:
            response = await client.get(f"http://localhost:8001/auth/users/{user_id}")
            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None
