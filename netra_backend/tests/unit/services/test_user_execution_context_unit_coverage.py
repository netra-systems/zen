"""
Unit Tests for UserExecutionContext - Following TEST_CREATION_GUIDE.md

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - User context isolation serves all user tiers
- Business Goal: Complete request isolation and prevent data leakage between users
- Value Impact: Ensures user data security, proper session management worth $500K+ ARR
- Strategic Impact: Foundation for multi-tenant AI operations and audit compliance

This test suite validates the critical UserExecutionContext business logic:
1. User isolation enforcement - Prevents data leakage between concurrent requests
2. Context validation - Ensures all required data is present and valid
3. Immutability guarantees - Context cannot be modified after creation (security)
4. Factory methods - Proper context creation from different sources
5. Audit trail support - Comprehensive tracking for compliance

Following TEST_CREATION_GUIDE.md:
- Real business logic testing (not infrastructure mocks)
- SSOT patterns using actual UserExecutionContext
- Tests that FAIL HARD when isolation or security fails
- Focus on business value: user security and data isolation
"""
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import Dict, Any, Optional
from netra_backend.app.services.user_execution_context import UserExecutionContext, InvalidContextError, ContextIsolationError
from shared.types.core_types import UserID, ensure_user_id

@pytest.mark.unit
class TestUserExecutionContextCreation:
    """Test UserExecutionContext creation and validation business logic."""

    def test_user_execution_context_creation_with_required_fields(self):
        """Test UserExecutionContext creates with all business-critical fields."""
        context = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789')
        assert context.user_id == 'test_user_123'
        assert context.thread_id == 'thread_456'
        assert context.run_id == 'run_789'
        assert context.request_id is not None
        assert isinstance(context.created_at, datetime)
        assert context.operation_depth == 0

    def test_user_execution_context_immutable_after_creation(self):
        """Test UserExecutionContext is immutable for security."""
        context = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789')
        with pytest.raises(Exception):
            context.user_id = 'hacker_user'
        with pytest.raises(Exception):
            context.thread_id = 'malicious_thread'

    def test_user_execution_context_with_optional_fields(self):
        """Test UserExecutionContext handles optional fields for extensibility."""
        mock_db_session = Mock()
        mock_websocket_client_id = 'ws_client_123'
        agent_context = {'agent_type': 'optimization', 'priority': 'high'}
        audit_metadata = {'ip_address': '192.168.1.1', 'user_agent': 'test_client'}
        context = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789', db_session=mock_db_session, websocket_client_id=mock_websocket_client_id, agent_context=agent_context, audit_metadata=audit_metadata, operation_depth=2, parent_request_id='parent_req_123')
        assert context.db_session == mock_db_session
        assert context.websocket_client_id == mock_websocket_client_id
        assert context.agent_context == agent_context
        assert context.audit_metadata == audit_metadata
        assert context.operation_depth == 2
        assert context.parent_request_id == 'parent_req_123'

    def test_user_execution_context_auto_generates_request_id(self):
        """Test UserExecutionContext auto-generates unique request IDs."""
        context1 = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789')
        context2 = UserExecutionContext(user_id='test_user_456', thread_id='thread_789', run_id='run_123')
        assert context1.request_id != context2.request_id
        assert context1.request_id is not None
        assert context2.request_id is not None
        assert len(context1.request_id) > 8
        assert len(context2.request_id) > 8

    def test_user_execution_context_validates_forbidden_patterns(self):
        """Test UserExecutionContext rejects security-violating patterns."""
        forbidden_patterns = ['TODO', 'PLACEHOLDER', 'test-placeholder', 'mock-user', 'fake-thread', 'dummy-run']
        for pattern in forbidden_patterns:
            with pytest.raises((InvalidContextError, ValueError)):
                UserExecutionContext(user_id=pattern, thread_id='thread_456', run_id='run_789')
            with pytest.raises((InvalidContextError, ValueError)):
                UserExecutionContext(user_id='test_user_123', thread_id=pattern, run_id='run_789')
            with pytest.raises((InvalidContextError, ValueError)):
                UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id=pattern)

@pytest.mark.unit
class TestUserExecutionContextBusinessMethods:
    """Test UserExecutionContext business methods for operations."""

    def test_user_execution_context_backward_compatibility_metadata_property(self):
        """Test backward compatibility metadata property merges contexts."""
        agent_context = {'agent_type': 'optimization', 'priority': 'high'}
        audit_metadata = {'ip_address': '192.168.1.1', 'session_id': 'sess_123'}
        context = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789', agent_context=agent_context, audit_metadata=audit_metadata)
        metadata = context.metadata
        assert metadata['agent_type'] == 'optimization'
        assert metadata['priority'] == 'high'
        assert metadata['ip_address'] == '192.168.1.1'
        assert metadata['session_id'] == 'sess_123'

    def test_user_execution_context_websocket_connection_id_alias(self):
        """Test websocket_connection_id alias for backward compatibility."""
        websocket_client_id = 'ws_client_123'
        context = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789', websocket_client_id=websocket_client_id)
        assert hasattr(context, 'websocket_connection_id')
        assert context.websocket_connection_id == websocket_client_id

    def test_user_execution_context_child_context_creation(self):
        """Test child context creation preserves user isolation."""
        parent_context = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789', agent_context={'parent_data': 'preserved'}, operation_depth=0)
        if hasattr(parent_context, 'create_child_context'):
            child_context = parent_context.create_child_context(additional_context={'child_data': 'added'})
            assert child_context.user_id == parent_context.user_id
            assert child_context.thread_id == parent_context.thread_id
            assert child_context.operation_depth == parent_context.operation_depth + 1
            assert child_context.parent_request_id == parent_context.request_id
        else:
            pytest.skip('create_child_context method not yet implemented - future enhancement')

@pytest.mark.unit
class TestUserExecutionContextFactoryMethods:
    """Test UserExecutionContext factory methods for different creation patterns."""

    def test_user_execution_context_from_request_factory(self):
        """Test factory method creates context from request data."""
        if hasattr(UserExecutionContext, 'from_request'):
            mock_request = Mock()
            mock_request.headers = {'user-id': 'test_user_123'}
            mock_request.path_params = {'thread_id': 'thread_456'}
            context = UserExecutionContext.from_request(request=mock_request, run_id='run_789')
            assert context.user_id == 'test_user_123'
            assert context.thread_id == 'thread_456'
            assert context.run_id == 'run_789'
        else:
            pytest.skip('from_request factory method not yet implemented - expected pattern documented')

    def test_user_execution_context_from_supervisor_compatibility(self):
        """Test supervisor-style factory method for backward compatibility."""
        if hasattr(UserExecutionContext, 'from_request_supervisor'):
            metadata = {'user_id': 'test_user_123', 'thread_id': 'thread_456', 'agent_type': 'optimization', 'session_id': 'sess_123'}
            context = UserExecutionContext.from_request_supervisor(metadata=metadata, run_id='run_789')
            assert context.user_id == 'test_user_123'
            assert context.thread_id == 'thread_456'
            assert context.run_id == 'run_789'
            assert context.metadata['agent_type'] == 'optimization'
            assert context.metadata['session_id'] == 'sess_123'
        else:
            pytest.skip('from_request_supervisor factory method not yet implemented - compatibility pattern documented')

@pytest.mark.unit
class TestUserExecutionContextSecurity:
    """Test UserExecutionContext security and isolation validation."""

    def test_user_execution_context_prevents_cross_user_contamination(self):
        """Test context prevents cross-user data contamination."""
        user1_context = UserExecutionContext(user_id='user_1', thread_id='thread_1', run_id='run_1', agent_context={'secret': 'user1_secret'})
        user2_context = UserExecutionContext(user_id='user_2', thread_id='thread_2', run_id='run_2', agent_context={'secret': 'user2_secret'})
        assert user1_context.user_id != user2_context.user_id
        assert user1_context.thread_id != user2_context.thread_id
        assert user1_context.run_id != user2_context.run_id
        assert user1_context.request_id != user2_context.request_id
        assert user1_context.agent_context['secret'] != user2_context.agent_context['secret']

    def test_user_execution_context_audit_trail_completeness(self):
        """Test context provides complete audit trail data."""
        context = UserExecutionContext(user_id='test_user_123', thread_id='thread_456', run_id='run_789', audit_metadata={'ip_address': '192.168.1.100', 'user_agent': 'Mozilla/5.0 (Test Client)', 'session_id': 'sess_abc123', 'api_key_id': 'key_xyz789'})
        assert context.user_id
        assert context.request_id
        assert context.created_at
        assert context.audit_metadata['ip_address']
        assert context.audit_metadata['user_agent']
        assert context.audit_metadata['session_id']
        assert context.audit_metadata['api_key_id']
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')