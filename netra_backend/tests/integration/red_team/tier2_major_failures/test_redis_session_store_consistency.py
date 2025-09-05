"""
RED TEAM TEST 16: Redis Session Store Consistency

CRITICAL: This test is DESIGNED TO FAIL initially to expose real integration issues.
Tests consistency between Redis session data and PostgreSQL user state.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: User Experience, Data Integrity, Platform Reliability
- Value Impact: Session inconsistencies cause login failures and user frustration
- Strategic Impact: Core authentication foundation affects all user interactions

Testing Level: L3 (Real services, real databases, minimal mocking)
Expected Initial Result: FAILURE (exposes real session consistency gaps)
"""

import asyncio
import json
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from shared.isolated_environment import IsolatedEnvironment

import pytest
import redis.asyncio as redis
from fastapi.testclient import TestClient
from sqlalchemy import text, select, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Real service imports - NO MOCKS
from netra_backend.app.main import app
from netra_backend.app.core.network_constants import DatabaseConstants, ServicePorts
from netra_backend.app.database import get_db_session
from netra_backend.app.services.session_service import SessionService
from netra_backend.app.services.user_service import UserService
from netra_backend.app.models.user import User
from netra_backend.app.models.session import Session as UserSession


class TestRedisSessionStoreConsistency:
    """
    RED TEAM TEST 16: Redis Session Store Consistency
    
    Tests critical session data consistency between Redis and PostgreSQL.
    MUST use real services - NO MOCKS allowed.
    These tests WILL fail initially and that's the point.
    """

    @pytest.fixture(scope="class")
    async def real_redis_client(self):
        """Real Redis client - will fail if Redis not available."""
        try:
            redis_client = redis.Redis(
                host="localhost",
                port=ServicePorts.REDIS_DEFAULT,
                db=DatabaseConstants.REDIS_TEST_DB,
                decode_responses=True
            )
            
            # Test real connection - will fail if Redis unavailable
            await redis_client.ping()
            
            yield redis_client
        except Exception as e:
            pytest.fail(f"CRITICAL: Real Redis connection failed: {e}")
        finally:
            if 'redis_client' in locals():
                await redis_client.close()

    @pytest.fixture(scope="class")
    async def real_database_session(self):
        """Real PostgreSQL database session - will fail if DB not available."""
        try:
            # Use real database URL from constants
            database_url = DatabaseConstants.build_postgres_url(
                user="test", password="test",
                port=ServicePorts.POSTGRES_DEFAULT,
                database="netra_test"
            )
            
            engine = create_async_engine(database_url, echo=False)
            async_session = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
            
            # Test real connection - will fail if DB unavailable
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            
            async with async_session() as session:
                yield session
        except Exception as e:
            pytest.fail(f"CRITICAL: Real database connection failed: {e}")
        finally:
            if 'engine' in locals():
                await engine.dispose()

    @pytest.fixture
    def real_test_client(self):
        """Real FastAPI test client - no mocking of the application."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_01_session_creation_consistency_fails(
        self, real_redis_client, real_database_session, real_test_client
    ):
        """
        Test 16A: Session Creation Consistency (EXPECTED TO FAIL)
        
        Tests that session creation maintains consistency between Redis and PostgreSQL.
        Will likely FAIL because:
        1. Session service may not properly sync between Redis and PostgreSQL
        2. Race conditions in session creation
        3. Inconsistent session data formats
        """
        try:
            # Create test user in database
            test_user_id = str(uuid.uuid4())
            test_email = f"test_user_{secrets.token_urlsafe(8)}@example.com"
            
            # FAILURE EXPECTED HERE - user creation may not work
            user_service = UserService()
            created_user = await user_service.create_user(
                email=test_email,
                password="test_password_123",
                username=f"test_user_{secrets.token_urlsafe(6)}"
            )
            
            assert created_user is not None, "User creation failed"
            user_id = created_user.id
            
            # Create session via service
            session_service = SessionService()
            
            # FAILURE EXPECTED HERE - session creation may not sync properly
            session_data = await session_service.create_session(
                user_id=user_id,
                device_info={
                    "user_agent": "Test User Agent",
                    "ip_address": "127.0.0.1",
                    "device_type": "web"
                }
            )
            
            assert session_data is not None, "Session creation returned None"
            assert "session_id" in session_data, "Session data should contain session_id"
            assert "token" in session_data, "Session data should contain token"
            
            session_id = session_data["session_id"]
            
            # Wait for consistency (Redis/PostgreSQL sync)
            await asyncio.sleep(1)
            
            # Verify session exists in Redis
            redis_session_key = f"session:{session_id}"
            redis_session_data = await real_redis_client.hgetall(redis_session_key)
            
            assert redis_session_data, f"Session {session_id} not found in Redis"
            assert redis_session_data.get("user_id") == str(user_id), \
                f"Redis session user_id mismatch: expected {user_id}, got {redis_session_data.get('user_id')}"
            
            # Verify session exists in PostgreSQL
            pg_session_query = await real_database_session.execute(
                select(UserSession).where(UserSession.id == session_id)
            )
            pg_session = pg_session_query.scalar_one_or_none()
            
            assert pg_session is not None, f"Session {session_id} not found in PostgreSQL"
            assert str(pg_session.user_id) == str(user_id), \
                f"PostgreSQL session user_id mismatch: expected {user_id}, got {pg_session.user_id}"
            
            # Verify data consistency between Redis and PostgreSQL
            assert redis_session_data.get("created_at") is not None, \
                "Redis session should have created_at timestamp"
            
            redis_created_at = datetime.fromisoformat(redis_session_data["created_at"])
            pg_created_at = pg_session.created_at
            
            # Allow small time difference for sync latency
            time_diff = abs((redis_created_at - pg_created_at).total_seconds())
            assert time_diff < 5, \
                f"Session timestamps differ by {time_diff} seconds (Redis: {redis_created_at}, PG: {pg_created_at})"
            
        except ImportError as e:
            pytest.fail(f"Session or user services not available: {e}")
        except Exception as e:
            pytest.fail(f"Session creation consistency test failed: {e}")

    @pytest.mark.asyncio
    async def test_02_session_update_propagation_fails(
        self, real_redis_client, real_database_session
    ):
        """
        Test 16B: Session Update Propagation (EXPECTED TO FAIL)
        
        Tests that session updates propagate correctly between Redis and PostgreSQL.
        Will likely FAIL because:
        1. Update operations may not sync between stores
        2. Last accessed time may not be updated consistently
        3. Session metadata changes may not propagate
        """
        try:
            # Create test session first
            user_service = UserService()
            test_user = await user_service.create_user(
                email=f"update_test_{secrets.token_urlsafe(8)}@example.com",
                password="test_password_123",
                username=f"update_test_{secrets.token_urlsafe(6)}"
            )
            
            session_service = SessionService()
            session_data = await session_service.create_session(
                user_id=test_user.id,
                device_info={"user_agent": "Initial Agent", "ip_address": "127.0.0.1"}
            )
            
            session_id = session_data["session_id"]
            await asyncio.sleep(1)  # Wait for initial sync
            
            # Update session metadata
            updated_metadata = {
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "page_views": 5,
                "feature_flags": {"dark_mode": True, "beta_features": False}
            }
            
            # FAILURE EXPECTED HERE - session updates may not propagate
            update_result = await session_service.update_session(
                session_id=session_id,
                metadata=updated_metadata
            )
            
            assert update_result is not None, "Session update returned None"
            
            # Wait for propagation
            await asyncio.sleep(2)
            
            # Verify update in Redis
            redis_session_data = await real_redis_client.hgetall(f"session:{session_id}")
            assert redis_session_data, "Session disappeared from Redis after update"
            
            # Check if metadata was updated in Redis
            redis_metadata_str = redis_session_data.get("metadata", "{}")
            redis_metadata = json.loads(redis_metadata_str) if redis_metadata_str != "{}" else {}
            
            assert "page_views" in redis_metadata, "Redis session metadata should contain page_views"
            assert redis_metadata["page_views"] == 5, \
                f"Redis page_views should be 5, got {redis_metadata.get('page_views')}"
            
            # Verify update in PostgreSQL
            pg_session_query = await real_database_session.execute(
                select(UserSession).where(UserSession.id == session_id)
            )
            pg_session = pg_session_query.scalar_one()
            
            pg_metadata = pg_session.metadata or {}
            assert "page_views" in pg_metadata, "PostgreSQL session metadata should contain page_views"
            assert pg_metadata["page_views"] == 5, \
                f"PostgreSQL page_views should be 5, got {pg_metadata.get('page_views')}"
            
            # Verify last_accessed_at was updated
            assert pg_session.last_accessed_at is not None, \
                "PostgreSQL session should have updated last_accessed_at"
            
            # Check Redis last activity
            redis_last_activity = redis_session_data.get("last_activity")
            assert redis_last_activity is not None, \
                "Redis session should have updated last_activity"
            
        except Exception as e:
            pytest.fail(f"Session update propagation test failed: {e}")

    @pytest.mark.asyncio
    async def test_03_session_expiration_consistency_fails(
        self, real_redis_client, real_database_session
    ):
        """
        Test 16C: Session Expiration Consistency (EXPECTED TO FAIL)
        
        Tests that session expiration is handled consistently across Redis and PostgreSQL.
        Will likely FAIL because:
        1. TTL may not be set correctly in Redis
        2. Expiration cleanup may not work in PostgreSQL
        3. Expired sessions may still be accessible
        """
        try:
            # Create test session with short expiration
            user_service = UserService()
            test_user = await user_service.create_user(
                email=f"expire_test_{secrets.token_urlsafe(8)}@example.com",
                password="test_password_123",
                username=f"expire_test_{secrets.token_urlsafe(6)}"
            )
            
            session_service = SessionService()
            
            # FAILURE EXPECTED HERE - expiration configuration may not work
            session_data = await session_service.create_session(
                user_id=test_user.id,
                device_info={"user_agent": "Expiry Test Agent"},
                expires_in_seconds=5  # Very short expiration for testing
            )
            
            session_id = session_data["session_id"]
            await asyncio.sleep(1)
            
            # Verify session exists initially
            redis_session = await real_redis_client.hgetall(f"session:{session_id}")
            assert redis_session, "Session should exist initially in Redis"
            
            pg_session_query = await real_database_session.execute(
                select(UserSession).where(UserSession.id == session_id)
            )
            pg_session = pg_session_query.scalar_one_or_none()
            assert pg_session is not None, "Session should exist initially in PostgreSQL"
            
            # Check Redis TTL
            session_ttl = await real_redis_client.ttl(f"session:{session_id}")
            assert session_ttl > 0, f"Redis session should have TTL > 0, got {session_ttl}"
            assert session_ttl <= 5, f"Redis TTL should be <= 5 seconds, got {session_ttl}"
            
            # Wait for expiration
            await asyncio.sleep(7)
            
            # Verify session expired in Redis
            expired_redis_session = await real_redis_client.hgetall(f"session:{session_id}")
            assert not expired_redis_session, \
                "Session should be expired/removed from Redis"
            
            # Verify session handling in PostgreSQL
            # Session might still exist in PG but should be marked as expired or cleaned up
            await real_database_session.refresh(pg_session)
            
            # Check if session is marked as expired or if cleanup process works
            if hasattr(pg_session, 'is_expired'):
                assert pg_session.is_expired(), \
                    "PostgreSQL session should be marked as expired"
            elif hasattr(pg_session, 'expires_at'):
                assert pg_session.expires_at < datetime.now(timezone.utc), \
                    "PostgreSQL session should have passed expiration time"
            
            # Test that expired session cannot be used
            if hasattr(session_service, 'validate_session'):
                validation_result = await session_service.validate_session(session_id)
                assert not validation_result["valid"], \
                    "Expired session should not validate as valid"
                assert "expired" in validation_result.get("reason", "").lower(), \
                    "Validation failure reason should mention expiration"
                    
        except Exception as e:
            pytest.fail(f"Session expiration consistency test failed: {e}")

    @pytest.mark.asyncio
    async def test_04_concurrent_session_access_consistency_fails(
        self, real_redis_client, real_database_session
    ):
        """
        Test 16D: Concurrent Session Access Consistency (EXPECTED TO FAIL)
        
        Tests that concurrent session operations maintain consistency.
        Will likely FAIL because:
        1. Race conditions in concurrent access
        2. Locking mechanisms may not be implemented
        3. Last accessed time updates may conflict
        """
        try:
            # Create test session
            user_service = UserService()
            test_user = await user_service.create_user(
                email=f"concurrent_test_{secrets.token_urlsafe(8)}@example.com",
                password="test_password_123",
                username=f"concurrent_test_{secrets.token_urlsafe(6)}"
            )
            
            session_service = SessionService()
            session_data = await session_service.create_session(
                user_id=test_user.id,
                device_info={"user_agent": "Concurrent Test Agent"}
            )
            
            session_id = session_data["session_id"]
            await asyncio.sleep(1)
            
            # Define concurrent session access function
            async def access_session(access_id: int) -> Dict[str, Any]:
                """Simulate concurrent session access."""
                try:
                    # Update session with access info
                    update_data = {
                        f"concurrent_access_{access_id}": datetime.now(timezone.utc).isoformat(),
                        "access_count": access_id
                    }
                    
                    if hasattr(session_service, 'touch_session'):
                        result = await session_service.touch_session(session_id, update_data)
                    else:
                        result = await session_service.update_session(session_id, update_data)
                    
                    return {"access_id": access_id, "status": "success", "result": result}
                    
                except Exception as e:
                    return {"access_id": access_id, "status": "error", "error": str(e)}
            
            # FAILURE EXPECTED HERE - concurrent access may cause consistency issues
            access_tasks = [access_session(i) for i in range(5)]
            results = await asyncio.gather(*access_tasks, return_exceptions=True)
            
            # Analyze concurrent access results
            successful_accesses = 0
            failed_accesses = 0
            exceptions = []
            
            for result in results:
                if isinstance(result, Exception):
                    exceptions.append(str(result))
                    failed_accesses += 1
                elif result["status"] == "success":
                    successful_accesses += 1
                else:
                    failed_accesses += 1
            
            # At least 80% of concurrent accesses should succeed
            success_rate = successful_accesses / len(access_tasks)
            assert success_rate >= 0.8, \
                f"Concurrent session access failed: {success_rate*100:.1f}% success rate. Exceptions: {exceptions[:2]}"
            
            # Wait for all updates to propagate
            await asyncio.sleep(2)
            
            # Verify final consistency between Redis and PostgreSQL
            redis_session_data = await real_redis_client.hgetall(f"session:{session_id}")
            assert redis_session_data, "Session should still exist in Redis after concurrent access"
            
            pg_session_query = await real_database_session.execute(
                select(UserSession).where(UserSession.id == session_id)
            )
            pg_session = pg_session_query.scalar_one()
            
            # Check that last accessed times are reasonably close
            redis_last_activity = redis_session_data.get("last_activity")
            if redis_last_activity and pg_session.last_accessed_at:
                redis_time = datetime.fromisoformat(redis_last_activity)
                pg_time = pg_session.last_accessed_at
                
                time_diff = abs((redis_time - pg_time).total_seconds())
                assert time_diff < 10, \
                    f"Last access times differ by {time_diff} seconds after concurrent access"
                    
        except Exception as e:
            pytest.fail(f"Concurrent session access consistency test failed: {e}")

    @pytest.mark.asyncio
    async def test_05_session_cleanup_consistency_fails(
        self, real_redis_client, real_database_session
    ):
        """
        Test 16E: Session Cleanup Consistency (EXPECTED TO FAIL)
        
        Tests that session cleanup maintains consistency between Redis and PostgreSQL.
        Will likely FAIL because:
        1. Cleanup processes may not be synchronized
        2. Orphaned sessions may remain in one store
        3. Cleanup timing may be inconsistent
        """
        try:
            # Create multiple test sessions for cleanup testing
            user_service = UserService()
            session_service = SessionService()
            
            test_sessions = []
            
            for i in range(3):
                test_user = await user_service.create_user(
                    email=f"cleanup_test_{i}_{secrets.token_urlsafe(8)}@example.com",
                    password="test_password_123",
                    username=f"cleanup_test_{i}_{secrets.token_urlsafe(6)}"
                )
                
                session_data = await session_service.create_session(
                    user_id=test_user.id,
                    device_info={"user_agent": f"Cleanup Test Agent {i}"}
                )
                
                test_sessions.append({
                    "session_id": session_data["session_id"],
                    "user_id": test_user.id
                })
            
            await asyncio.sleep(1)  # Wait for sessions to be created
            
            # Verify all sessions exist initially
            for session_info in test_sessions:
                session_id = session_info["session_id"]
                
                redis_session = await real_redis_client.hgetall(f"session:{session_id}")
                assert redis_session, f"Session {session_id} should exist in Redis"
                
                pg_session_query = await real_database_session.execute(
                    select(UserSession).where(UserSession.id == session_id)
                )
                pg_session = pg_session_query.scalar_one_or_none()
                assert pg_session is not None, f"Session {session_id} should exist in PostgreSQL"
            
            # Perform session cleanup
            if hasattr(session_service, 'cleanup_expired_sessions'):
                # FAILURE EXPECTED HERE - cleanup may not work properly
                cleanup_result = await session_service.cleanup_expired_sessions()
                
                assert "cleaned_count" in cleanup_result, \
                    "Cleanup result should include cleaned count"
                
            elif hasattr(session_service, 'cleanup_all_sessions'):
                # Alternative cleanup method
                cleanup_result = await session_service.cleanup_all_sessions()
                
            else:
                # Manual cleanup for testing
                for session_info in test_sessions:
                    session_id = session_info["session_id"]
                    await session_service.delete_session(session_id)
                
                cleanup_result = {"cleaned_count": len(test_sessions)}
            
            # Wait for cleanup to propagate
            await asyncio.sleep(2)
            
            # Verify cleanup consistency
            remaining_redis_sessions = 0
            remaining_pg_sessions = 0
            
            for session_info in test_sessions:
                session_id = session_info["session_id"]
                
                # Check Redis
                redis_session = await real_redis_client.hgetall(f"session:{session_id}")
                if redis_session:
                    remaining_redis_sessions += 1
                
                # Check PostgreSQL
                pg_session_query = await real_database_session.execute(
                    select(UserSession).where(UserSession.id == session_id)
                )
                pg_session = pg_session_query.scalar_one_or_none()
                if pg_session is not None:
                    remaining_pg_sessions += 1
            
            # Verify cleanup consistency between stores
            assert remaining_redis_sessions == remaining_pg_sessions, \
                f"Session cleanup inconsistent: Redis has {remaining_redis_sessions} sessions, " \
                f"PostgreSQL has {remaining_pg_sessions} sessions"
            
            # If sessions remain, they should be the same ones in both stores
            if remaining_redis_sessions > 0:
                for session_info in test_sessions:
                    session_id = session_info["session_id"]
                    
                    redis_exists = bool(await real_redis_client.hgetall(f"session:{session_id}"))
                    
                    pg_session_query = await real_database_session.execute(
                        select(UserSession).where(UserSession.id == session_id)
                    )
                    pg_exists = pg_session_query.scalar_one_or_none() is not None
                    
                    assert redis_exists == pg_exists, \
                        f"Session {session_id} existence mismatch: Redis={redis_exists}, PostgreSQL={pg_exists}"
                        
        except Exception as e:
            pytest.fail(f"Session cleanup consistency test failed: {e}")


# Utility class for Redis session testing
class RedTeamRedisSessionTestUtils:
    """Utility methods for Redis session consistency testing."""
    
    @staticmethod
    async def get_session_count_redis(redis_client) -> int:
        """Get total number of sessions in Redis."""
        try:
            session_keys = await redis_client.keys("session:*")
            return len(session_keys)
        except Exception:
            return 0
    
    @staticmethod
    async def get_session_count_postgres(db_session: AsyncSession) -> int:
        """Get total number of sessions in PostgreSQL."""
        try:
            count_query = await db_session.execute(
                text("SELECT COUNT(*) FROM user_sessions")
            )
            return count_query.scalar()
        except Exception:
            return 0
    
    @staticmethod
    def create_test_session_data(user_id: str) -> Dict[str, Any]:
        """Create test session data structure."""
        return {
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_activity": datetime.now(timezone.utc).isoformat(),
            "metadata": {
                "test_session": True,
                "created_by": "red_team_test"
            }
        }
    
    @staticmethod
    async def verify_session_consistency(
        redis_client, 
        db_session: AsyncSession, 
        session_id: str
    ) -> Dict[str, Any]:
        """Verify consistency between Redis and PostgreSQL session data."""
        
        # Get Redis data
        redis_data = await redis_client.hgetall(f"session:{session_id}")
        
        # Get PostgreSQL data
        pg_query = await db_session.execute(
            select(UserSession).where(UserSession.id == session_id)
        )
        pg_session = pg_query.scalar_one_or_none()
        
        consistency_report = {
            "session_id": session_id,
            "redis_exists": bool(redis_data),
            "postgres_exists": pg_session is not None,
            "consistent": False,
            "differences": []
        }
        
        if redis_data and pg_session:
            # Compare user IDs
            redis_user_id = redis_data.get("user_id")
            pg_user_id = str(pg_session.user_id)
            
            if redis_user_id != pg_user_id:
                consistency_report["differences"].append(
                    f"User ID mismatch: Redis={redis_user_id}, PG={pg_user_id}"
                )
            
            # Compare timestamps if available
            redis_created = redis_data.get("created_at")
            if redis_created and pg_session.created_at:
                redis_time = datetime.fromisoformat(redis_created)
                time_diff = abs((redis_time - pg_session.created_at).total_seconds())
                
                if time_diff > 5:  # Allow 5 second difference
                    consistency_report["differences"].append(
                        f"Created time diff: {time_diff} seconds"
                    )
            
            consistency_report["consistent"] = len(consistency_report["differences"]) == 0
        
        elif redis_data and not pg_session:
            consistency_report["differences"].append("Session exists in Redis but not PostgreSQL")
        elif not redis_data and pg_session:
            consistency_report["differences"].append("Session exists in PostgreSQL but not Redis")
        else:
            consistency_report["consistent"] = True  # Both missing is consistent
        
        return consistency_report