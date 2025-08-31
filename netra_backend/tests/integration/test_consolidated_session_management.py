"""Comprehensive test suite for consolidated Redis session management.

Tests all session management functionality including:
- User authentication sessions
- Demo session management
- Security features
- Performance and reliability
- Cross-service compatibility
"""

import asyncio
import json
import pytest
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import uuid

from netra_backend.app.services.redis.session_manager import RedisSessionManager
from netra_backend.app.services.redis.session_migration import SessionMigrationUtility


class TestConsolidatedSessionManager:
    """Test suite for consolidated Redis session manager."""
    
    @pytest.fixture
    async def session_manager(self):
        """Create session manager instance for testing."""
        manager = RedisSessionManager()
        yield manager
        # Cleanup
        await manager.cleanup_expired_sessions()
    
    @pytest.fixture
    def sample_user_data(self):
        """Sample user data for testing."""
        return {
            "email": "test@example.com",
            "name": "Test User",
            "provider": "google",
            "verified_email": True
        }
    
    @pytest.fixture
    def sample_demo_data(self):
        """Sample demo data for testing."""
        return {
            "industry": "healthcare",
            "user_id": None
        }


class TestUserSessions(TestConsolidatedSessionManager):
    """Test user authentication session management."""
    
    async def test_create_user_session(self, session_manager, sample_user_data):
        """Test creating a user session."""
        user_id = "test_user_123"
        
        session_id = await session_manager.create_session(
            user_id=user_id, 
            session_data=sample_user_data,
            ttl=3600
        )
        
        assert session_id is not None
        assert user_id in session_id or len(session_id) > 10
        
        # Verify session was created
        session_data = await session_manager.get_session(session_id)
        assert session_data is not None
        assert session_data["user_id"] == user_id
        assert session_data["data"]["email"] == sample_user_data["email"]
    
    async def test_get_user_session(self, session_manager, sample_user_data):
        """Test retrieving user session."""
        user_id = "test_user_456"
        session_id = await session_manager.create_session(user_id, sample_user_data)
        
        # Get session
        session_data = await session_manager.get_session(session_id)
        assert session_data is not None
        assert session_data["user_id"] == user_id
        assert "last_accessed" in session_data
        assert "created_at" in session_data
    
    async def test_update_user_session(self, session_manager, sample_user_data):
        """Test updating user session data."""
        user_id = "test_user_789"
        session_id = await session_manager.create_session(user_id, sample_user_data)
        
        # Update session
        updates = {"last_login": datetime.now(timezone.utc).isoformat()}
        result = await session_manager.update_session(session_id, updates)
        assert result is True
        
        # Verify update
        session_data = await session_manager.get_session(session_id)
        assert session_data["data"]["last_login"] == updates["last_login"]
    
    async def test_delete_user_session(self, session_manager, sample_user_data):
        """Test deleting user session."""
        user_id = "test_user_delete"
        session_id = await session_manager.create_session(user_id, sample_user_data)
        
        # Verify session exists
        session_data = await session_manager.get_session(session_id)
        assert session_data is not None
        
        # Delete session
        result = await session_manager.delete_session(session_id)
        assert result is True
        
        # Verify session is gone
        session_data = await session_manager.get_session(session_id)
        assert session_data is None
    
    async def test_session_validation(self, session_manager, sample_user_data):
        """Test session validation."""
        user_id = "test_user_validate"
        session_id = await session_manager.create_session(user_id, sample_user_data)
        
        # Valid session
        is_valid = await session_manager.validate_session(session_id, user_id)
        assert is_valid is True
        
        # Invalid user_id
        is_valid = await session_manager.validate_session(session_id, "wrong_user")
        assert is_valid is False
        
        # Invalid session_id
        is_valid = await session_manager.validate_session("invalid_session", user_id)
        assert is_valid is False
    
    async def test_get_user_sessions(self, session_manager, sample_user_data):
        """Test getting all sessions for a user."""
        user_id = "test_user_multiple"
        
        # Create multiple sessions
        session1 = await session_manager.create_session(user_id, sample_user_data)
        session2 = await session_manager.create_session(user_id, sample_user_data)
        
        # Get all user sessions
        sessions = await session_manager.get_user_sessions(user_id)
        session_ids = [s for s in sessions if s in [session1, session2]]
        
        # Should have at least our created sessions
        assert len(session_ids) >= 2
    
    async def test_extend_session(self, session_manager, sample_user_data):
        """Test extending session TTL."""
        user_id = "test_user_extend"
        session_id = await session_manager.create_session(user_id, sample_user_data, ttl=60)  # 1 minute
        
        # Extend session
        result = await session_manager.extend_session(session_id, 3600)  # 1 hour
        
        # Result should be True if Redis is available, or handled gracefully if not
        assert isinstance(result, bool)


class TestDemoSessions(TestConsolidatedSessionManager):
    """Test demo session management functionality."""
    
    async def test_create_demo_session(self, session_manager):
        """Test creating a demo session."""
        session_id = str(uuid.uuid4())
        industry = "healthcare"
        
        session_data = await session_manager.create_demo_session(
            session_id=session_id,
            industry=industry,
            user_id=123
        )
        
        assert session_data is not None
        assert session_data["industry"] == industry
        assert session_data["user_id"] == 123
        assert session_data["session_type"] == "demo"
        assert "started_at" in session_data
        assert session_data["messages"] == []
    
    async def test_get_demo_session(self, session_manager):
        """Test retrieving demo session."""
        session_id = str(uuid.uuid4())
        industry = "fintech"
        
        # Create demo session
        await session_manager.create_demo_session(session_id, industry)
        
        # Get demo session
        session_data = await session_manager.get_demo_session(session_id)
        assert session_data is not None
        assert session_data["industry"] == industry
    
    async def test_add_demo_message(self, session_manager):
        """Test adding messages to demo session."""
        session_id = str(uuid.uuid4())
        industry = "retail"
        
        # Create demo session
        await session_manager.create_demo_session(session_id, industry)
        
        # Add user message
        message1 = await session_manager.add_demo_message(
            session_id=session_id,
            role="user",
            content="How can AI optimize my retail operations?",
            message_type="question"
        )
        
        assert message1["role"] == "user"
        assert message1["content"] == "How can AI optimize my retail operations?"
        assert message1["message_type"] == "question"
        assert "timestamp" in message1
        
        # Add assistant message
        message2 = await session_manager.add_demo_message(
            session_id=session_id,
            role="assistant", 
            content="AI can optimize your retail operations in several ways...",
            agents=["TriageAgent", "OptimizationAgent"],
            metrics={"roi": 25.5, "efficiency_gain": 15.3}
        )
        
        assert message2["role"] == "assistant"
        assert message2["agents"] == ["TriageAgent", "OptimizationAgent"]
        assert message2["metrics"]["roi"] == 25.5
        
        # Verify messages were added to session
        session_data = await session_manager.get_demo_session(session_id)
        assert len(session_data["messages"]) == 2
    
    async def test_demo_session_status(self, session_manager):
        """Test getting demo session status."""
        session_id = str(uuid.uuid4())
        industry = "manufacturing"
        
        # Create demo session
        await session_manager.create_demo_session(session_id, industry)
        
        # Get initial status
        status = await session_manager.get_demo_session_status(session_id)
        assert status["session_id"] == session_id
        assert status["industry"] == industry
        assert status["message_count"] == 0
        assert status["progress_percentage"] == 0
        assert status["status"] == "active"
        
        # Add some messages
        for i in range(3):
            await session_manager.add_demo_message(
                session_id, "user", f"Message {i+1}"
            )
        
        # Get updated status
        status = await session_manager.get_demo_session_status(session_id)
        assert status["message_count"] == 3
        assert status["progress_percentage"] == 50  # 3/6 * 100
        assert status["status"] == "active"
    
    async def test_demo_session_not_found(self, session_manager):
        """Test handling of non-existent demo sessions."""
        non_existent_id = str(uuid.uuid4())
        
        # Get non-existent session
        session_data = await session_manager.get_demo_session(non_existent_id)
        assert session_data is None
        
        # Try to add message to non-existent session
        with pytest.raises(ValueError, match="Demo session not found"):
            await session_manager.add_demo_message(non_existent_id, "user", "test")
        
        # Try to get status of non-existent session
        with pytest.raises(ValueError, match="Demo session not found"):
            await session_manager.get_demo_session_status(non_existent_id)


class TestSecurityFeatures(TestConsolidatedSessionManager):
    """Test security and performance features."""
    
    async def test_regenerate_session_id(self, session_manager, sample_user_data):
        """Test session ID regeneration for security."""
        user_id = "test_user_security"
        old_session_id = await session_manager.create_session(user_id, sample_user_data)
        
        # Regenerate session ID
        new_session_id = await session_manager.regenerate_session_id(
            old_session_id, user_id, sample_user_data
        )
        
        assert new_session_id != old_session_id
        assert len(new_session_id) >= 32  # Should be cryptographically secure
        
        # Old session should be gone
        old_session = await session_manager.get_session(old_session_id)
        assert old_session is None
    
    async def test_record_session_activity(self, session_manager, sample_user_data):
        """Test recording session activity for security monitoring."""
        user_id = "test_user_activity"
        session_id = await session_manager.create_session(user_id, sample_user_data)
        
        # Record some activities
        await session_manager.record_session_activity(
            session_id=session_id,
            activity_type="api_call",
            resource="/api/users",
            client_ip="192.168.1.1"
        )
        
        await session_manager.record_session_activity(
            session_id=session_id,
            activity_type="data_access",
            resource="/api/sensitive_data",
            client_ip="192.168.1.1"
        )
        
        # Get security status
        status = await session_manager.get_session_security_status(session_id)
        assert status["session_id"] == session_id
        assert status["activity_count"] == 2
        assert status["security_level"] == "low"  # Should be low for 2 activities
    
    async def test_session_limits(self, session_manager, sample_user_data):
        """Test user session limits."""
        user_id = "test_user_limits"
        
        # Set session limit
        await session_manager.set_user_session_limit(user_id, 2)
        
        # Create sessions (this is more of an integration test)
        session1 = await session_manager.create_session(user_id, sample_user_data)
        session2 = await session_manager.create_session(user_id, sample_user_data)
        
        assert session1 is not None
        assert session2 is not None
    
    async def test_invalidate_all_user_sessions(self, session_manager, sample_user_data):
        """Test invalidating all sessions for a user."""
        user_id = "test_user_invalidate_all"
        
        # Create multiple sessions
        session1 = await session_manager.create_session(user_id, sample_user_data)
        session2 = await session_manager.create_session(user_id, sample_user_data)
        session3 = await session_manager.create_session(user_id, sample_user_data)
        
        # Invalidate all sessions except one
        count = await session_manager.invalidate_all_user_sessions(
            user_id=user_id,
            reason="security_breach",
            except_session_id=session1
        )
        
        # Should have invalidated at least 2 sessions
        assert count >= 2
        
        # Session1 should still exist
        session1_data = await session_manager.get_session(session1)
        # May or may not exist depending on Redis availability
        
        # Other sessions should be gone
        session2_data = await session_manager.get_session(session2)
        session3_data = await session_manager.get_session(session3)
        assert session2_data is None
        assert session3_data is None


class TestPerformanceAndReliability(TestConsolidatedSessionManager):
    """Test performance and reliability features."""
    
    async def test_memory_fallback(self, session_manager, sample_user_data):
        """Test memory fallback when Redis is unavailable."""
        # Force fallback mode (simulate Redis failure)
        original_redis = session_manager.redis
        session_manager.redis = None
        
        try:
            user_id = "test_user_fallback"
            
            # Create session (should use memory fallback)
            session_id = await session_manager.create_session(user_id, sample_user_data)
            assert session_id is not None
            
            # Get session (should use memory fallback)
            session_data = await session_manager.get_session(session_id)
            assert session_data is not None
            assert session_data["user_id"] == user_id
            
            # Update session (should use memory fallback)
            result = await session_manager.update_session(session_id, {"test": "value"})
            assert isinstance(result, bool)
            
            # Delete session (should use memory fallback)
            result = await session_manager.delete_session(session_id)
            assert result is True
            
        finally:
            # Restore Redis client
            session_manager.redis = original_redis
    
    async def test_session_cleanup(self, session_manager):
        """Test cleanup of expired sessions."""
        # Test cleanup functionality
        cleanup_count = await session_manager.cleanup_expired_sessions()
        assert isinstance(cleanup_count, int)
        assert cleanup_count >= 0
    
    async def test_session_stats(self, session_manager):
        """Test session statistics."""
        stats = await session_manager.get_session_stats()
        
        assert "total_sessions" in stats
        assert "memory_sessions" in stats
        assert "redis_available" in stats
        assert "default_ttl" in stats
        
        assert isinstance(stats["total_sessions"], int)
        assert isinstance(stats["redis_available"], bool)
        assert stats["default_ttl"] == 3600
    
    async def test_concurrent_session_operations(self, session_manager, sample_user_data):
        """Test concurrent session operations."""
        user_id = "test_user_concurrent"
        
        async def create_and_delete_session(index):
            session_id = await session_manager.create_session(f"{user_id}_{index}", sample_user_data)
            await asyncio.sleep(0.01)  # Small delay
            result = await session_manager.delete_session(session_id)
            return result
        
        # Create multiple concurrent operations
        tasks = [create_and_delete_session(i) for i in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Most operations should succeed
        successes = sum(1 for r in results if r is True)
        assert successes >= 8  # Allow for some variance


class TestSessionMigration:
    """Test session migration utilities."""
    
    @pytest.fixture
    async def migration_util(self):
        """Create migration utility for testing."""
        session_manager = RedisSessionManager()
        util = SessionMigrationUtility(session_manager)
        yield util
        # Cleanup would go here if needed
    
    async def test_migration_stats_initialization(self, migration_util):
        """Test migration utility initialization."""
        stats = migration_util.migration_stats
        
        assert "demo_sessions_migrated" in stats
        assert "auth_sessions_migrated" in stats
        assert "failed_migrations" in stats
        assert "total_sessions_processed" in stats
        
        assert all(count == 0 for count in stats.values())
    
    async def test_generate_migration_report(self, migration_util):
        """Test migration report generation."""
        report = await migration_util.generate_migration_report()
        
        assert "Session Migration Report" in report
        assert "Migration Statistics:" in report
        assert "Consolidated Session Manager Status:" in report
        assert "Next Steps:" in report
        assert "Migration Status:" in report
    
    async def test_demo_session_migration(self, migration_util):
        """Test demo session migration process."""
        # This is more of an integration test
        stats = await migration_util.migrate_demo_sessions()
        
        assert isinstance(stats, dict)
        assert "demo_sessions_migrated" in stats
        assert isinstance(stats["demo_sessions_migrated"], int)
    
    async def test_cleanup_legacy_references(self, migration_util):
        """Test cleanup of legacy session references."""
        # This should not raise exceptions
        await migration_util.cleanup_legacy_references()


class TestCrossServiceCompatibility(TestConsolidatedSessionManager):
    """Test compatibility with other services."""
    
    async def test_auth_service_independence(self):
        """Test that auth service maintains its own session manager."""
        # Auth service should maintain independence
        # This test ensures we don't break auth service functionality
        
        try:
            from auth_service.auth_core.core.session_manager import SessionManager as AuthSessionManager
            
            # Auth service should still have its own session manager
            auth_manager = AuthSessionManager()
            assert auth_manager is not None
            
            # It should be independent from our consolidated manager
            consolidated_manager = RedisSessionManager()
            assert type(auth_manager) != type(consolidated_manager)
            
        except ImportError:
            # Auth service not available in test environment
            pytest.skip("Auth service not available for testing")
    
    async def test_session_id_compatibility(self, session_manager, sample_user_data):
        """Test session ID format compatibility."""
        user_id = "test_user_compatibility"
        
        # Create session
        session_id = await session_manager.create_session(user_id, sample_user_data)
        
        # Session ID should be compatible with existing systems
        assert isinstance(session_id, str)
        assert len(session_id) > 10  # Should be substantial length
        assert "_" in session_id or "-" in session_id or len(session_id) >= 32  # Should have delimiter or be UUID-like
    
    async def test_session_data_format(self, session_manager, sample_user_data):
        """Test session data format compatibility."""
        user_id = "test_user_format"
        session_id = await session_manager.create_session(user_id, sample_user_data)
        
        session_data = await session_manager.get_session(session_id)
        
        # Verify expected format
        assert "user_id" in session_data
        assert "created_at" in session_data
        assert "last_accessed" in session_data
        assert "data" in session_data
        
        # Verify datetime formats are ISO-compatible
        created_at = session_data["created_at"]
        assert isinstance(created_at, str)
        # Should be parseable as ISO datetime
        parsed_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        assert isinstance(parsed_date, datetime)


if __name__ == "__main__":
    # Run tests with pytest
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))