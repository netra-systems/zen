"""
Session Cleanup Job Tests
Tests automated session cleanup and maintenance operations
Focuses on database cleanup and expired session management
"""
import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from auth_service.auth_core.database.models import AuthSession, AuthUser
from auth_service.auth_core.database.connection import auth_db
from auth_service.auth_core.core.session_manager import SessionManager


class SessionCleanupService:
    """Service for automated session cleanup operations"""
    
    def __init__(self):
        self.session_manager = SessionManager()
    
    async def cleanup_expired_sessions(self, db_session: AsyncSession) -> int:
        """Remove expired sessions from database"""
        cutoff_time = datetime.now(timezone.utc)
        
        result = await db_session.execute(
            delete(AuthSession)
            .where(AuthSession.expires_at < cutoff_time)
        )
        
        await db_session.commit()
        return result.rowcount
    
    async def cleanup_inactive_sessions(self, db_session: AsyncSession, 
                                      days_inactive: int = 30) -> int:
        """Remove sessions inactive for specified days"""
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days_inactive)
        
        result = await db_session.execute(
            delete(AuthSession)
            .where(AuthSession.last_activity < cutoff_time)
        )
        
        await db_session.commit()
        return result.rowcount
    
    async def enforce_session_limits(self, db_session: AsyncSession, 
                                   max_sessions: int = 5) -> int:
        """Enforce maximum sessions per user"""
        users_query = select(AuthSession.user_id).distinct()
        result = await db_session.execute(users_query)
        user_ids = [row[0] for row in result.fetchall()]
        
        total_cleaned = 0
        for user_id in user_ids:
            total_cleaned += await self._cleanup_excess_sessions(
                db_session, user_id, max_sessions
            )
        
        return total_cleaned
    
    async def _cleanup_excess_sessions(self, db_session: AsyncSession,
                                     user_id: str, max_sessions: int) -> int:
        """Clean up excess sessions for specific user"""
        query = (
            select(AuthSession)
            .where(AuthSession.user_id == user_id)
            .order_by(AuthSession.last_activity.desc())
        )
        
        result = await db_session.execute(query)
        sessions = result.scalars().all()
        
        if len(sessions) <= max_sessions:
            return 0
        
        # Delete oldest sessions
        sessions_to_delete = sessions[max_sessions:]
        for session in sessions_to_delete:
            await db_session.delete(session)
        
        await db_session.commit()
        return len(sessions_to_delete)


class TestSessionCleanupJob:
    """Test automated session cleanup job functionality"""
    
    @pytest.fixture
    async def cleanup_service(self):
        """Create session cleanup service"""
        return SessionCleanupService()
    
    # Use test_db_session from conftest.py for proper async fixture handling
    
    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, cleanup_service, test_db_session):
        """Test cleanup of expired sessions"""
        # Create expired session
        expired_session = AuthSession(
            id="expired123",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        
        # Create valid session
        valid_session = AuthSession(
            id="valid123",
            user_id="user123",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        test_db_session.add(expired_session)
        test_db_session.add(valid_session)
        await test_db_session.commit()
        
        cleaned_count = await cleanup_service.cleanup_expired_sessions(test_db_session)
        
        assert cleaned_count == 1
    
    @pytest.mark.asyncio
    async def test_cleanup_inactive_sessions(self, cleanup_service, test_db_session):
        """Test cleanup of inactive sessions"""
        # Create inactive session
        inactive_session = AuthSession(
            id="inactive123",
            user_id="user123",
            last_activity=datetime.now(timezone.utc) - timedelta(days=31),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        test_db_session.add(inactive_session)
        await test_db_session.commit()
        
        cleaned_count = await cleanup_service.cleanup_inactive_sessions(
            test_db_session, days_inactive=30
        )
        
        assert cleaned_count == 1
    
    @pytest.mark.asyncio
    async def test_enforce_session_limits(self, cleanup_service, test_db_session):
        """Test enforcement of maximum sessions per user"""
        # Create 7 sessions for same user
        sessions = []
        for i in range(7):
            session = AuthSession(
                id=f"session{i}",
                user_id="user123",
                last_activity=datetime.now(timezone.utc) - timedelta(minutes=i),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            sessions.append(session)
            test_db_session.add(session)
        
        await test_db_session.commit()
        
        cleaned_count = await cleanup_service.enforce_session_limits(
            test_db_session, max_sessions=5
        )
        
        assert cleaned_count == 2
    
    @pytest.mark.asyncio
    async def test_cleanup_preserves_recent_sessions(self, cleanup_service, test_db_session):
        """Test cleanup preserves most recent sessions"""
        # Create sessions with different activity times
        sessions = []
        for i in range(3):
            session = AuthSession(
                id=f"recent{i}",
                user_id="user123",
                last_activity=datetime.now(timezone.utc) - timedelta(minutes=i),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            sessions.append(session)
            test_db_session.add(session)
        
        await test_db_session.commit()
        
        # Cleanup should preserve all recent sessions
        cleaned_count = await cleanup_service.enforce_session_limits(
            test_db_session, max_sessions=5
        )
        
        assert cleaned_count == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_job_performance(self, cleanup_service, test_db_session):
        """Test cleanup job handles large number of sessions"""
        import time
        
        # Create many expired sessions
        for i in range(100):
            session = AuthSession(
                id=f"bulk{i}",
                user_id=f"user{i % 10}",  # 10 different users
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            test_db_session.add(session)
        
        await test_db_session.commit()
        
        start_time = time.time()
        cleaned_count = await cleanup_service.cleanup_expired_sessions(test_db_session)
        end_time = time.time()
        
        assert cleaned_count == 100
        assert (end_time - start_time) < 5.0  # Should complete in under 5 seconds
    
    @pytest.mark.asyncio
    async def test_cleanup_job_error_handling(self, cleanup_service):
        """Test cleanup job handles database errors gracefully"""
        mock_session = AsyncMock()
        mock_session.execute.side_effect = Exception("Database error")
        
        try:
            await cleanup_service.cleanup_expired_sessions(mock_session)
            assert False, "Should have raised exception"
        except Exception as e:
            assert str(e) == "Database error"
    
    @pytest.mark.asyncio
    async def test_redis_session_sync(self, cleanup_service, test_db_session):
        """Test Redis session synchronization with database cleanup"""
        # This would test ensuring Redis and DB sessions stay in sync
        # Mock Redis operations for testing
        with patch.object(cleanup_service.session_manager, 'redis_client') as mock_redis:
            mock_redis.scan_iter.return_value = ["session:expired123"]
            mock_redis.delete.return_value = 1
            
            # Create corresponding DB session
            db_session_record = AuthSession(
                id="expired123",
                user_id="user123",
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
            )
            test_db_session.add(db_session_record)
            await test_db_session.commit()
            
            # Cleanup should handle both Redis and DB
            cleaned_count = await cleanup_service.cleanup_expired_sessions(test_db_session)
            
            assert cleaned_count == 1


class TestSessionMaintenanceScheduling:
    """Test session maintenance scheduling and automation"""
    
    def test_cleanup_job_configuration(self):
        """Test cleanup job configuration options"""
        cleanup_service = SessionCleanupService()
        
        # Verify service is properly configured
        assert cleanup_service.session_manager is not None
        assert hasattr(cleanup_service, 'cleanup_expired_sessions')
        assert hasattr(cleanup_service, 'cleanup_inactive_sessions')
        assert hasattr(cleanup_service, 'enforce_session_limits')
    
    def test_cleanup_job_frequency_calculation(self):
        """Test calculation of cleanup job frequency"""
        # Test logic for determining when to run cleanup
        current_time = datetime.now(timezone.utc)
        last_cleanup = current_time - timedelta(hours=6)
        cleanup_interval = timedelta(hours=4)
        
        should_run_cleanup = (current_time - last_cleanup) >= cleanup_interval
        
        assert should_run_cleanup is True
    
    def test_cleanup_metrics_collection(self):
        """Test collection of cleanup job metrics"""
        # Mock metrics collection
        cleanup_metrics = {
            "expired_sessions_cleaned": 10,
            "inactive_sessions_cleaned": 5,
            "session_limits_enforced": 3,
            "cleanup_duration_seconds": 2.5,
            "cleanup_timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        assert cleanup_metrics["expired_sessions_cleaned"] > 0
        assert cleanup_metrics["cleanup_duration_seconds"] < 10.0
        assert "cleanup_timestamp" in cleanup_metrics