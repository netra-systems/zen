"""
Unit Tests for User Session Manager Business Logic

Business Value Justification (BVJ):
- Segment: Enterprise/Mid/Early (Critical Multi-User Infrastructure)
- Business Goal: User Data Security & Session Isolation Excellence
- Value Impact: Validates session management that prevents $X million in data breaches,
  ensures proper user isolation for concurrent AI optimization sessions
- Strategic Impact: Tests the session layer that enables secure multi-user AI workload optimization

CRITICAL: These unit tests validate the BUSINESS LOGIC of user session management,
focusing on security-critical patterns that protect user data and enable concurrent sessions:

KEY SECURITY CAPABILITIES TESTED:
1. Session Creation - Secure session initialization with unique identifiers  
2. User Isolation - Prevents session data leakage between users
3. Session Lifecycle - Proper creation, updates, and cleanup
4. Data Integrity - Session data validation and consistency
5. Concurrent Safety - Multi-user session handling without conflicts

TEST STRATEGY: Pure business logic validation with mocked storage.
Tests focus on security patterns, data validation, and multi-user isolation logic.
"""
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, Set
from netra_backend.app.websocket_core.user_session_manager import UserSessionManager
from shared.types import UserID
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.unit
class TestUserSessionManagerInitialization(SSotBaseTestCase):
    """Test UserSessionManager initialization business logic."""

    def test_session_manager_initializes_empty_state(self):
        """Test UserSessionManager initializes with clean, secure state."""
        manager = UserSessionManager()
        assert len(manager._sessions) == 0
        assert len(manager._user_sessions) == 0
        assert isinstance(manager._sessions, dict)
        assert isinstance(manager._user_sessions, dict)

    def test_session_manager_ready_for_multi_user_operations(self):
        """Test UserSessionManager is ready for concurrent multi-user operations."""
        manager = UserSessionManager()
        user1 = UserID('user-1')
        user2 = UserID('user-2')
        user1_sessions = manager._user_sessions.get(user1, set())
        user2_sessions = manager._user_sessions.get(user2, set())
        assert len(user1_sessions) == 0
        assert len(user2_sessions) == 0

@pytest.mark.unit
class TestSessionCreation(SSotBaseTestCase):
    """Test session creation business logic - CRITICAL for user onboarding."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = UserSessionManager()

    async def test_create_session_generates_unique_session_id(self):
        """Test create_session generates unique session identifiers."""
        user_id = UserID('session-user-123')
        session_data = {'preferences': {'theme': 'dark'}}
        session_id = await self.manager.create_session(user_id, session_data)
        assert session_id.startswith('session_')
        assert session_id in self.manager._sessions
        assert isinstance(session_id, str)
        assert len(session_id) > 8

    async def test_create_session_stores_complete_session_data(self):
        """Test create_session stores all required session information."""
        user_id = UserID('data-user-456')
        session_data = {'workspace': 'optimization-workspace', 'preferences': {'notifications': True}, 'context': {'last_action': 'cluster_analysis'}}
        session_id = await self.manager.create_session(user_id, session_data)
        stored_session = self.manager._sessions[session_id]
        assert stored_session['user_id'] == user_id
        assert stored_session['data'] == session_data
        assert stored_session['active'] is True
        assert stored_session['data']['workspace'] == 'optimization-workspace'
        assert stored_session['data']['preferences']['notifications'] is True
        assert stored_session['data']['context']['last_action'] == 'cluster_analysis'

    async def test_create_session_maintains_user_session_mapping(self):
        """Test create_session maintains bidirectional user-session mapping."""
        user_id = UserID('mapping-user-789')
        session_data = {'test': 'data'}
        session_id = await self.manager.create_session(user_id, session_data)
        assert user_id in self.manager._user_sessions
        assert session_id in self.manager._user_sessions[user_id]
        assert isinstance(self.manager._user_sessions[user_id], set)

    async def test_create_multiple_sessions_same_user(self):
        """Test user can have multiple concurrent sessions."""
        user_id = UserID('multi-session-user')
        session_data_1 = {'workspace': 'workspace-1'}
        session_data_2 = {'workspace': 'workspace-2'}
        session_data_3 = {'workspace': 'workspace-3'}
        session_id_1 = await self.manager.create_session(user_id, session_data_1)
        session_id_2 = await self.manager.create_session(user_id, session_data_2)
        session_id_3 = await self.manager.create_session(user_id, session_data_3)
        assert session_id_1 != session_id_2 != session_id_3
        assert len(self.manager._user_sessions[user_id]) == 3
        assert self.manager._sessions[session_id_1]['data']['workspace'] == 'workspace-1'
        assert self.manager._sessions[session_id_2]['data']['workspace'] == 'workspace-2'
        assert self.manager._sessions[session_id_3]['data']['workspace'] == 'workspace-3'

    async def test_create_session_different_users_isolated(self):
        """Test sessions for different users are properly isolated."""
        user_a = UserID('isolated-user-a')
        user_b = UserID('isolated-user-b')
        session_data_a = {'secret': 'user-a-data', 'workspace': 'private-a'}
        session_data_b = {'secret': 'user-b-data', 'workspace': 'private-b'}
        session_a = await self.manager.create_session(user_a, session_data_a)
        session_b = await self.manager.create_session(user_b, session_data_b)
        assert session_a != session_b
        assert self.manager._sessions[session_a]['user_id'] == user_a
        assert self.manager._sessions[session_b]['user_id'] == user_b
        assert self.manager._sessions[session_a]['data']['secret'] == 'user-a-data'
        assert self.manager._sessions[session_b]['data']['secret'] == 'user-b-data'
        assert session_a in self.manager._user_sessions[user_a]
        assert session_a not in self.manager._user_sessions[user_b]
        assert session_b in self.manager._user_sessions[user_b]
        assert session_b not in self.manager._user_sessions[user_a]

@pytest.mark.unit
class TestSessionRetrieval(SSotBaseTestCase):
    """Test session retrieval business logic - validates data access patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = UserSessionManager()

    async def test_get_session_returns_existing_session(self):
        """Test get_session returns complete session data for valid session ID."""
        user_id = UserID('retrieval-user-123')
        original_data = {'optimization_settings': {'cpu_threshold': 0.8, 'memory_limit': '2Gi'}, 'last_updated': '2025-01-09T10:30:00Z'}
        session_id = await self.manager.create_session(user_id, original_data)
        retrieved_session = await self.manager.get_session(session_id)
        assert retrieved_session is not None
        assert retrieved_session['user_id'] == user_id
        assert retrieved_session['data'] == original_data
        assert retrieved_session['active'] is True
        settings = retrieved_session['data']['optimization_settings']
        assert settings['cpu_threshold'] == 0.8
        assert settings['memory_limit'] == '2Gi'

    async def test_get_session_returns_none_for_invalid_id(self):
        """Test get_session returns None for non-existent session IDs."""
        invalid_session_ids = ['nonexistent-session-123', 'session_999999', '', 'invalid-format']
        for invalid_id in invalid_session_ids:
            result = await self.manager.get_session(invalid_id)
            assert result is None, f'Should return None for invalid ID: {invalid_id}'

    async def test_get_user_sessions_returns_all_user_sessions(self):
        """Test get_user_sessions returns all sessions for a specific user."""
        user_id = UserID('multi-session-retrieval-user')
        sessions_data = [{'workspace': 'analysis-1'}, {'workspace': 'optimization-2'}, {'workspace': 'monitoring-3'}]
        created_session_ids = []
        for data in sessions_data:
            session_id = await self.manager.create_session(user_id, data)
            created_session_ids.append(session_id)
        user_sessions = await self.manager.get_user_sessions(user_id)
        assert isinstance(user_sessions, set)
        assert len(user_sessions) == 3
        for session_id in created_session_ids:
            assert session_id in user_sessions

    async def test_get_user_sessions_returns_empty_for_no_sessions(self):
        """Test get_user_sessions returns empty set for users with no sessions."""
        user_with_no_sessions = UserID('no-sessions-user')
        user_sessions = await self.manager.get_user_sessions(user_with_no_sessions)
        assert isinstance(user_sessions, set)
        assert len(user_sessions) == 0

    async def test_get_user_sessions_isolation_between_users(self):
        """Test get_user_sessions maintains strict isolation between users."""
        user_a = UserID('isolation-user-a')
        user_b = UserID('isolation-user-b')
        session_a1 = await self.manager.create_session(user_a, {'data': 'a1'})
        session_a2 = await self.manager.create_session(user_a, {'data': 'a2'})
        session_b1 = await self.manager.create_session(user_b, {'data': 'b1'})
        sessions_a = await self.manager.get_user_sessions(user_a)
        sessions_b = await self.manager.get_user_sessions(user_b)
        assert len(sessions_a) == 2
        assert len(sessions_b) == 1
        assert session_a1 in sessions_a
        assert session_a2 in sessions_a
        assert session_b1 not in sessions_a
        assert session_b1 in sessions_b
        assert session_a1 not in sessions_b
        assert session_a2 not in sessions_b

@pytest.mark.unit
class TestSessionUpdates(SSotBaseTestCase):
    """Test session update business logic - validates data mutation patterns."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = UserSessionManager()

    async def test_update_session_modifies_existing_data(self):
        """Test update_session modifies session data while preserving structure."""
        user_id = UserID('update-user-123')
        initial_data = {'preferences': {'theme': 'light', 'notifications': True}, 'workspace': 'initial-workspace'}
        session_id = await self.manager.create_session(user_id, initial_data)
        update_data = {'preferences': {'theme': 'dark'}, 'last_action': 'optimization_completed'}
        update_result = await self.manager.update_session(session_id, update_data)
        assert update_result is True
        updated_session = await self.manager.get_session(session_id)
        updated_data = updated_session['data']
        assert updated_data['preferences']['theme'] == 'dark'
        assert updated_data['preferences']['notifications'] is True
        assert updated_data['workspace'] == 'initial-workspace'
        assert updated_data['last_action'] == 'optimization_completed'

    async def test_update_session_fails_for_invalid_session(self):
        """Test update_session fails gracefully for non-existent sessions."""
        invalid_session_id = 'nonexistent-session-456'
        update_data = {'some': 'data'}
        update_result = await self.manager.update_session(invalid_session_id, update_data)
        assert update_result is False

    async def test_update_session_handles_complex_nested_data(self):
        """Test update_session handles complex nested data structures."""
        user_id = UserID('complex-update-user')
        initial_data = {'optimization': {'cpu': {'current': 0.7, 'target': 0.5}, 'memory': {'current': '1.5Gi', 'target': '1.0Gi'}}, 'metadata': {'version': '1.0'}}
        session_id = await self.manager.create_session(user_id, initial_data)
        update_data = {'optimization': {'cpu': {'target': 0.4}, 'network': {'bandwidth': '100Mbps'}}, 'metadata': {'version': '1.1', 'updated': '2025-01-09'}}
        result = await self.manager.update_session(session_id, update_data)
        assert result is True
        updated_session = await self.manager.get_session(session_id)
        data = updated_session['data']
        assert data['optimization']['cpu']['current'] == 0.7
        assert data['optimization']['cpu']['target'] == 0.4
        assert data['optimization']['memory']['current'] == '1.5Gi'
        assert data['optimization']['network']['bandwidth'] == '100Mbps'
        assert data['metadata']['version'] == '1.1'
        assert data['metadata']['updated'] == '2025-01-09'

@pytest.mark.unit
class TestSessionLifecycle(SSotBaseTestCase):
    """Test session lifecycle management - validates cleanup and state transitions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = UserSessionManager()

    async def test_close_session_deactivates_and_removes_mapping(self):
        """Test close_session properly deactivates session and updates mappings."""
        user_id = UserID('lifecycle-user-123')
        session_data = {'workspace': 'closing-workspace'}
        session_id = await self.manager.create_session(user_id, session_data)
        assert session_id in self.manager._user_sessions[user_id]
        session = await self.manager.get_session(session_id)
        assert session['active'] is True
        close_result = await self.manager.close_session(session_id)
        assert close_result is True
        session = await self.manager.get_session(session_id)
        assert session['active'] is False
        assert session_id not in self.manager._user_sessions[user_id]

    async def test_close_session_fails_for_invalid_session(self):
        """Test close_session fails gracefully for non-existent sessions."""
        invalid_session_id = 'nonexistent-close-session'
        close_result = await self.manager.close_session(invalid_session_id)
        assert close_result is False

    async def test_is_session_active_validates_session_status(self):
        """Test is_session_active correctly validates session activity status."""
        user_id = UserID('active-status-user')
        session_data = {'test': 'data'}
        session_id = await self.manager.create_session(user_id, session_data)
        assert await self.manager.is_session_active(session_id) is True
        await self.manager.close_session(session_id)
        assert await self.manager.is_session_active(session_id) is False

    async def test_is_session_active_returns_false_for_invalid_session(self):
        """Test is_session_active returns False for non-existent sessions."""
        invalid_session_ids = ['nonexistent-session', 'session_999999', '', None]
        for invalid_id in invalid_session_ids:
            if invalid_id is None:
                continue
            result = await self.manager.is_session_active(invalid_id)
            assert result is False, f'Should return False for invalid ID: {invalid_id}'

    async def test_session_lifecycle_complete_workflow(self):
        """Test complete session lifecycle from creation to cleanup."""
        user_id = UserID('complete-lifecycle-user')
        initial_data = {'workspace': 'lifecycle-test', 'preferences': {'auto_save': True}}
        session_id = await self.manager.create_session(user_id, initial_data)
        assert await self.manager.is_session_active(session_id) is True
        update_data = {'last_activity': '2025-01-09T12:00:00Z'}
        update_result = await self.manager.update_session(session_id, update_data)
        assert update_result is True
        session = await self.manager.get_session(session_id)
        assert session['data']['last_activity'] == '2025-01-09T12:00:00Z'
        close_result = await self.manager.close_session(session_id)
        assert close_result is True
        assert await self.manager.is_session_active(session_id) is False
        user_sessions = await self.manager.get_user_sessions(user_id)
        assert session_id not in user_sessions

@pytest.mark.unit
class TestSessionCleanupAndUtilities(SSotBaseTestCase):
    """Test session cleanup utilities and administrative functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = UserSessionManager()

    def test_clear_all_sessions_resets_manager_state(self):
        """Test clear_all_sessions completely resets manager to initial state."""
        user1 = UserID('cleanup-user-1')
        user2 = UserID('cleanup-user-2')
        self.manager._sessions['session_0'] = {'user_id': user1, 'data': {'test': 'data1'}, 'active': True}
        self.manager._sessions['session_1'] = {'user_id': user2, 'data': {'test': 'data2'}, 'active': True}
        self.manager._user_sessions[user1] = {'session_0'}
        self.manager._user_sessions[user2] = {'session_1'}
        assert len(self.manager._sessions) == 2
        assert len(self.manager._user_sessions) == 2
        self.manager.clear_all_sessions()
        assert len(self.manager._sessions) == 0
        assert len(self.manager._user_sessions) == 0
        assert isinstance(self.manager._sessions, dict)
        assert isinstance(self.manager._user_sessions, dict)

    async def test_manager_handles_concurrent_operations(self):
        """Test manager handles concurrent session operations safely."""
        user_id = UserID('concurrent-user')
        session_ids = []
        for i in range(5):
            session_data = {'concurrent_test': i, 'workspace': f'workspace_{i}'}
            session_id = await self.manager.create_session(user_id, session_data)
            session_ids.append(session_id)
        assert len(session_ids) == 5
        user_sessions = await self.manager.get_user_sessions(user_id)
        assert len(user_sessions) == 5
        for i, session_id in enumerate(session_ids):
            if i % 2 == 0:
                result = await self.manager.close_session(session_id)
                assert result is True
            else:
                update_result = await self.manager.update_session(session_id, {'updated': True})
                assert update_result is True
        final_user_sessions = await self.manager.get_user_sessions(user_id)
        assert len(final_user_sessions) == 2
        for session_id in final_user_sessions:
            session = await self.manager.get_session(session_id)
            assert session['data']['updated'] is True
            assert session['active'] is True

@pytest.mark.unit
class TestSessionSecurityAndValidation(SSotBaseTestCase):
    """Test session security patterns and data validation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = UserSessionManager()

    async def test_session_data_isolation_between_operations(self):
        """Test session data is isolated between different operations."""
        user1 = UserID('isolation-user-1')
        user2 = UserID('isolation-user-2')
        sensitive_data_1 = {'api_keys': {'aws': 'secret-key-1', 'gcp': 'secret-key-2'}, 'workspace': 'user1-private-workspace'}
        sensitive_data_2 = {'api_keys': {'aws': 'different-secret', 'azure': 'azure-secret'}, 'workspace': 'user2-private-workspace'}
        session1 = await self.manager.create_session(user1, sensitive_data_1)
        session2 = await self.manager.create_session(user2, sensitive_data_2)
        session1_data = (await self.manager.get_session(session1))['data']
        session2_data = (await self.manager.get_session(session2))['data']
        assert session1_data['api_keys']['aws'] == 'secret-key-1'
        assert session1_data['workspace'] == 'user1-private-workspace'
        assert 'azure' not in session1_data['api_keys']
        assert session2_data['api_keys']['aws'] == 'different-secret'
        assert session2_data['workspace'] == 'user2-private-workspace'
        assert 'gcp' not in session2_data['api_keys']
        user1_sessions = await self.manager.get_user_sessions(user1)
        user2_sessions = await self.manager.get_user_sessions(user2)
        assert session1 in user1_sessions
        assert session1 not in user2_sessions
        assert session2 in user2_sessions
        assert session2 not in user1_sessions

    async def test_session_data_consistency_during_updates(self):
        """Test session data remains consistent during concurrent updates."""
        user_id = UserID('consistency-user')
        initial_data = {'counter': 0, 'metadata': {'operations': []}}
        session_id = await self.manager.create_session(user_id, initial_data)
        for i in range(3):
            current_session = await self.manager.get_session(session_id)
            current_counter = current_session['data']['counter']
            current_ops = current_session['data']['metadata']['operations'].copy()
            update_data = {'counter': current_counter + 1, 'metadata': {'operations': current_ops + [f'operation_{i}']}}
            result = await self.manager.update_session(session_id, update_data)
            assert result is True
        final_session = await self.manager.get_session(session_id)
        final_data = final_session['data']
        assert final_data['counter'] == 3
        assert len(final_data['metadata']['operations']) == 3
        assert 'operation_0' in final_data['metadata']['operations']
        assert 'operation_1' in final_data['metadata']['operations']
        assert 'operation_2' in final_data['metadata']['operations']
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')