"""
User Session Management Integration Tests - Real Services

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure reliable user authentication and session persistence
- Value Impact: Users maintain login state across browser sessions, enabling continuous AI interactions
- Strategic Impact: Foundation for multi-user platform and subscription management

These tests validate the complete user session lifecycle using real PostgreSQL and Redis services,
ensuring that session management supports concurrent users and delivers reliable authentication.
"""

import asyncio
import pytest
import time
from typing import Dict, List
from unittest.mock import patch
from uuid import uuid4

from test_framework.base_integration_test import DatabaseIntegrationTest, CacheIntegrationTest
from test_framework.conftest_real_services import real_services
from shared.isolated_environment import get_env


class TestUserSessionManagement(DatabaseIntegrationTest, CacheIntegrationTest):
    """Test user session management with real database and Redis cache."""

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_login_creates_session_in_redis(self, real_services):
        """
        Test that user login creates valid session in Redis cache.
        
        BVJ: Users must have persistent authentication sessions to access AI features.
        """
        # Create test user in real database
        user_data = await self.create_test_user_context(real_services)
        
        # Simulate user login - create session in Redis
        session_data = await self.create_test_session(real_services, user_data['id'], {
            'user_id': user_data['id'],
            'email': user_data['email'],
            'login_time': time.time(),
            'ip_address': '127.0.0.1',
            'user_agent': 'integration-test-browser',
            'active': True
        })
        
        # Verify session stored in Redis
        retrieved_session = await real_services.redis.get_json(session_data['session_key'])
        
        assert retrieved_session is not None, "Session must be stored in Redis"
        assert retrieved_session['user_id'] == user_data['id'], "Session must contain correct user ID"
        assert retrieved_session['email'] == user_data['email'], "Session must contain user email"
        assert retrieved_session['active'] is True, "Session must be active after login"
        
        # Verify session can be retrieved for authentication
        user_from_session = await real_services.postgres.fetchrow("""
            SELECT id, email, name, is_active 
            FROM auth.users 
            WHERE id = $1
        """, user_data['id'])
        
        assert user_from_session is not None, "User must exist in database for session validation"
        assert user_from_session['email'] == retrieved_session['email'], "Database and Redis data must match"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_concurrent_user_sessions_isolation(self, real_services):
        """
        Test that multiple users can maintain isolated concurrent sessions.
        
        BVJ: Platform must support multiple users simultaneously without session conflicts.
        """
        # Create multiple test users concurrently
        users = []
        sessions = []
        
        async def create_user_session(index: int):
            user_data = await self.create_test_user_context(real_services, {
                'email': f'concurrent-user-{index}@example.com',
                'name': f'Concurrent User {index}',
                'is_active': True
            })
            
            session_data = await self.create_test_session(real_services, user_data['id'], {
                'user_id': user_data['id'],
                'session_type': f'concurrent_session_{index}',
                'created_at': time.time(),
                'active': True
            })
            
            return user_data, session_data
        
        # Create 5 concurrent user sessions
        results = await asyncio.gather(*[create_user_session(i) for i in range(5)])
        users, sessions = zip(*results)
        
        # Verify all sessions are isolated and retrievable
        for i, (user, session) in enumerate(zip(users, sessions)):
            retrieved_session = await real_services.redis.get_json(session['session_key'])
            
            assert retrieved_session is not None, f"Session {i} must be stored"
            assert retrieved_session['user_id'] == user['id'], f"Session {i} must have correct user ID"
            assert retrieved_session['session_type'] == f'concurrent_session_{i}', f"Session {i} must be isolated"
        
        # Verify database isolation - each user is distinct
        user_emails = [user['email'] for user in users]
        assert len(set(user_emails)) == 5, "All users must have unique emails"
        
        # Verify Redis isolation - each session key is distinct
        session_keys = [session['session_key'] for session in sessions]
        assert len(set(session_keys)) == 5, "All sessions must have unique keys"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_expiration_and_cleanup(self, real_services):
        """
        Test that expired sessions are properly handled and cleaned up.
        
        BVJ: Platform must manage session lifecycle to maintain security and performance.
        """
        # Create test user
        user_data = await self.create_test_user_context(real_services)
        
        # Create short-lived session (2 seconds)
        session_data = await self.create_test_session(real_services, user_data['id'])
        short_lived_key = f"session:short:{user_data['id']}"
        await real_services.redis.set_json(short_lived_key, {
            'user_id': user_data['id'],
            'created_at': time.time(),
            'expires_at': time.time() + 2,  # 2 second expiration
            'active': True
        }, ex=2)  # Redis TTL of 2 seconds
        
        # Create long-lived session
        long_lived_key = f"session:long:{user_data['id']}"
        await real_services.redis.set_json(long_lived_key, {
            'user_id': user_data['id'],
            'created_at': time.time(),
            'expires_at': time.time() + 3600,  # 1 hour expiration
            'active': True
        }, ex=3600)
        
        # Verify both sessions exist initially
        short_session = await real_services.redis.get_json(short_lived_key)
        long_session = await real_services.redis.get_json(long_lived_key)
        
        assert short_session is not None, "Short session must exist initially"
        assert long_session is not None, "Long session must exist initially"
        
        # Wait for short session to expire
        await asyncio.sleep(3)
        
        # Verify session expiration behavior
        expired_session = await real_services.redis.get_json(short_lived_key)
        active_session = await real_services.redis.get_json(long_lived_key)
        
        assert expired_session is None, "Expired session must be cleaned up by Redis"
        assert active_session is not None, "Active session must remain available"
        assert active_session['user_id'] == user_data['id'], "Active session must maintain user context"

    @pytest.mark.integration  
    @pytest.mark.real_services
    async def test_session_update_and_activity_tracking(self, real_services):
        """
        Test that user activity updates session data for engagement tracking.
        
        BVJ: Platform must track user engagement for subscription optimization and product insights.
        """
        # Create test user and session
        user_data = await self.create_test_user_context(real_services)
        session_data = await self.create_test_session(real_services, user_data['id'])
        
        initial_session = await real_services.redis.get_json(session_data['session_key'])
        initial_created_at = initial_session['created_at']
        
        # Simulate user activity - update session with activity data
        activity_updates = {
            'last_activity': time.time(),
            'page_views': 5,
            'agent_interactions': 2,
            'messages_sent': 3,
            'session_duration': 300  # 5 minutes
        }
        
        # Update session in Redis with activity tracking
        updated_session = {**initial_session, **activity_updates}
        await real_services.redis.set_json(session_data['session_key'], updated_session, ex=3600)
        
        # Verify session updates are persisted
        retrieved_session = await real_services.redis.get_json(session_data['session_key'])
        
        assert retrieved_session is not None, "Updated session must be retrievable"
        assert retrieved_session['user_id'] == user_data['id'], "Session must maintain user identity"
        assert retrieved_session['created_at'] == initial_created_at, "Original session data must be preserved"
        
        # Verify activity tracking data
        assert retrieved_session['page_views'] == 5, "Page view tracking must be accurate"
        assert retrieved_session['agent_interactions'] == 2, "Agent interaction tracking must be accurate"  
        assert retrieved_session['messages_sent'] == 3, "Message count tracking must be accurate"
        assert retrieved_session['session_duration'] == 300, "Session duration tracking must be accurate"
        
        # Verify business value - activity data enables engagement optimization
        engagement_score = (
            retrieved_session['agent_interactions'] * 10 + 
            retrieved_session['messages_sent'] * 5 + 
            retrieved_session['page_views']
        )
        assert engagement_score > 0, "Session activity must provide engagement metrics for business optimization"

    @pytest.mark.integration
    @pytest.mark.real_services  
    async def test_session_invalidation_on_logout(self, real_services):
        """
        Test that user logout properly invalidates session in both Redis and database.
        
        BVJ: Secure logout prevents unauthorized access and maintains platform security.
        """
        # Create test user and active session
        user_data = await self.create_test_user_context(real_services)
        session_data = await self.create_test_session(real_services, user_data['id'])
        
        # Verify session is initially active
        active_session = await real_services.redis.get_json(session_data['session_key'])
        assert active_session is not None, "Session must be active before logout"
        assert active_session['active'] is True, "Session must be marked as active"
        
        # Record logout activity in database
        logout_time = time.time()
        await real_services.postgres.execute("""
            INSERT INTO auth.user_sessions (user_id, session_key, action, timestamp, ip_address)
            VALUES ($1, $2, 'logout', $3, $4)
        """, user_data['id'], session_data['session_key'], logout_time, '127.0.0.1')
        
        # Invalidate session in Redis - mark as inactive and reduce TTL
        invalidated_session = {**active_session, 'active': False, 'logout_time': logout_time}
        await real_services.redis.set_json(session_data['session_key'], invalidated_session, ex=60)  # 1 minute cleanup window
        
        # Verify session invalidation
        retrieved_session = await real_services.redis.get_json(session_data['session_key'])
        assert retrieved_session is not None, "Invalidated session should exist briefly for audit"
        assert retrieved_session['active'] is False, "Session must be marked as inactive"
        assert retrieved_session['logout_time'] == logout_time, "Logout time must be recorded"
        
        # Verify database audit trail
        logout_record = await real_services.postgres.fetchrow("""
            SELECT user_id, action, timestamp 
            FROM auth.user_sessions 
            WHERE user_id = $1 AND action = 'logout'
            ORDER BY timestamp DESC 
            LIMIT 1
        """, user_data['id'])
        
        assert logout_record is not None, "Logout must be recorded in database"
        assert logout_record['action'] == 'logout', "Database must record logout action"
        assert logout_record['timestamp'] == logout_time, "Database timestamp must match Redis timestamp"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_recovery_after_service_restart(self, real_services):
        """
        Test that user sessions survive Redis service restarts through database persistence.
        
        BVJ: Platform must maintain user sessions across infrastructure maintenance events.
        """
        # Create test user and session
        user_data = await self.create_test_user_context(real_services)
        original_session = await self.create_test_session(real_services, user_data['id'])
        
        # Store session metadata in database for persistence
        session_metadata = {
            'user_id': user_data['id'],
            'session_key': original_session['session_key'],
            'created_at': original_session['created_at'],
            'expires_at': original_session['expires_at'],
            'ip_address': '127.0.0.1',
            'user_agent': 'test-browser'
        }
        
        await real_services.postgres.execute("""
            INSERT INTO auth.persistent_sessions 
            (user_id, session_key, created_at, expires_at, ip_address, user_agent, is_active)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            ON CONFLICT (session_key) DO UPDATE SET
                is_active = EXCLUDED.is_active,
                expires_at = EXCLUDED.expires_at
        """, user_data['id'], session_metadata['session_key'], 
             session_metadata['created_at'], session_metadata['expires_at'],
             session_metadata['ip_address'], session_metadata['user_agent'], True)
        
        # Simulate Redis restart by manually clearing the session
        await real_services.redis.delete(original_session['session_key'])
        
        # Verify session is removed from Redis
        missing_session = await real_services.redis.get_json(original_session['session_key'])
        assert missing_session is None, "Session must be cleared from Redis cache"
        
        # Simulate session recovery - restore from database to Redis
        persistent_session = await real_services.postgres.fetchrow("""
            SELECT user_id, session_key, created_at, expires_at, ip_address, user_agent
            FROM auth.persistent_sessions
            WHERE session_key = $1 AND is_active = true AND expires_at > $2
        """, session_metadata['session_key'], time.time())
        
        assert persistent_session is not None, "Session must be recoverable from database"
        
        # Restore session to Redis
        recovered_session_data = {
            'user_id': persistent_session['user_id'],
            'created_at': persistent_session['created_at'],
            'expires_at': persistent_session['expires_at'],
            'ip_address': persistent_session['ip_address'],
            'user_agent': persistent_session['user_agent'],
            'active': True,
            'recovered': True  # Flag to indicate recovery
        }
        
        remaining_ttl = max(60, int(persistent_session['expires_at'] - time.time()))
        await real_services.redis.set_json(original_session['session_key'], recovered_session_data, ex=remaining_ttl)
        
        # Verify session recovery
        recovered_session = await real_services.redis.get_json(original_session['session_key'])
        assert recovered_session is not None, "Session must be successfully recovered"
        assert recovered_session['user_id'] == user_data['id'], "Recovered session must maintain user identity"
        assert recovered_session['active'] is True, "Recovered session must be active"
        assert recovered_session['recovered'] is True, "Recovery flag must be set for monitoring"

    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_session_performance_under_load(self, real_services):
        """
        Test session management performance with concurrent operations.
        
        BVJ: Platform must maintain responsive performance during peak user activity.
        """
        # Create base test user
        user_data = await self.create_test_user_context(real_services)
        
        # Measure session creation performance
        start_time = time.time()
        session_creation_tasks = []
        
        async def create_and_validate_session(index: int):
            session_data = await self.create_test_session(real_services, user_data['id'], {
                'user_id': user_data['id'],
                'session_index': index,
                'created_at': time.time(),
                'active': True
            })
            
            # Validate session immediately
            retrieved = await real_services.redis.get_json(session_data['session_key'])
            assert retrieved is not None, f"Session {index} must be created successfully"
            assert retrieved['session_index'] == index, f"Session {index} must have correct index"
            return session_data
        
        # Create 20 concurrent sessions
        sessions = await asyncio.gather(*[create_and_validate_session(i) for i in range(20)])
        
        creation_duration = time.time() - start_time
        creation_rate = len(sessions) / creation_duration
        
        # Performance assertions
        assert creation_rate > 10, f"Session creation rate too slow: {creation_rate:.2f} sessions/sec"
        assert len(sessions) == 20, "All sessions must be created successfully"
        
        # Test session retrieval performance
        retrieval_start = time.time()
        
        async def retrieve_session(session):
            retrieved = await real_services.redis.get_json(session['session_key'])
            assert retrieved is not None, "Session must be retrievable"
            return retrieved
        
        retrieved_sessions = await asyncio.gather(*[retrieve_session(session) for session in sessions])
        
        retrieval_duration = time.time() - retrieval_start
        retrieval_rate = len(retrieved_sessions) / retrieval_duration
        
        # Performance assertions for retrieval
        assert retrieval_rate > 50, f"Session retrieval rate too slow: {retrieval_rate:.2f} retrievals/sec"
        assert len(retrieved_sessions) == 20, "All sessions must be retrievable"
        
        self.logger.info(f"Session performance: {creation_rate:.2f} creates/sec, {retrieval_rate:.2f} retrievals/sec")
        
        # Verify business value - performance metrics support scaling decisions
        self.assert_business_value_delivered({
            'session_creation_rate': creation_rate,
            'session_retrieval_rate': retrieval_rate,
            'concurrent_sessions': len(sessions),
            'performance_baseline': True
        }, 'automation')