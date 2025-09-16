"""WebSocket Thread ID Integration Tests

CRITICAL PURPOSE: These tests MUST FAIL to expose integration issues between
WebSocket ID generation and thread management causing "404: Thread not found" errors.

Root Cause Being Tested:
- WebSocket factory generates IDs that cannot be used by RequestScopedSessionFactory
- Thread creation/lookup fails when WebSocket and session components use different ID formats  
- Missing integration between WebSocket connection IDs and database thread records

Error Pattern Being Exposed:
Failed to create request-scoped database session: 404: Thread not found
Thread ID mismatch: run_id contains 'websocket_factory_1757361062151'
but thread_id is 'thread_websocket_factory_1757361062151_7_90c65fe4'

Business Value: Ensuring proper multi-user WebSocket session isolation and data integrity
"""
import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Optional, Dict, Any, List
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory, get_isolated_session

class WebSocketThreadIdIntegrationTests:
    """Integration test suite to expose WebSocket-Thread ID compatibility issues.
    
    These tests are DESIGNED TO FAIL initially to demonstrate the integration
    problems between WebSocket ID generation and thread management systems.
    """

    @pytest.mark.asyncio
    async def test_websocket_connection_to_session_factory_integration(self):
        """FAILING TEST: Verify WebSocket connection IDs work with session factory
        
        EXPECTED FAILURE: This test should FAIL because WebSocket factory generates
        IDs incompatible with session factory's thread validation requirements.
        """

        def generate_websocket_connection_context():
            """Simulates WebSocket connection creating user context"""
            timestamp = int(time.time() * 1000)
            return {'connection_id': f'websocket_factory_{timestamp}', 'user_id': 'test_user_123', 'run_id': f'websocket_factory_{timestamp}', 'thread_id': None}
        websocket_context = generate_websocket_connection_context()
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)
            mock_repo_instance.create = AsyncMock(return_value=Mock())
            try:
                async with get_isolated_session(user_id=websocket_context['user_id'], request_id=None, thread_id=websocket_context['run_id']) as session:
                    pass
                integration_success = True
            except Exception as e:
                integration_success = False
                error_message = str(e)
                thread_not_found_error = '404' in error_message or 'Thread not found' in error_message
            assert integration_success, f"WEBSOCKET-SESSION INTEGRATION FAILURE: WebSocket connection context with run_id '{websocket_context['run_id']}' failed to integrate with session factory. This proves WebSocket factory generates incompatible IDs that cannot be used for database thread operations."

    @pytest.mark.asyncio
    async def test_cross_component_thread_id_consistency(self):
        """FAILING TEST: Verify thread IDs are consistent across WebSocket and session components
        
        EXPECTED FAILURE: This test should FAIL because different components
        generate different thread ID formats for the same user session.
        """
        user_id = 'test_user_456'
        operation = 'websocket_session'

        def generate_websocket_component_ids():
            """Simulates WebSocket component ID generation"""
            timestamp = int(time.time() * 1000)
            return {'connection_id': f'ws_conn_{user_id[:8]}_{timestamp}', 'thread_id': f'websocket_factory_{timestamp}', 'run_id': f'websocket_factory_{timestamp}', 'request_id': f'ws_req_{timestamp}'}

        def generate_session_factory_ids():
            """Simulates session factory ID generation"""
            return {'thread_id': UnifiedIdGenerator.generate_user_context_ids(user_id, operation)[0], 'run_id': UnifiedIdGenerator.generate_user_context_ids(user_id, operation)[1], 'request_id': UnifiedIdGenerator.generate_user_context_ids(user_id, operation)[2]}
        websocket_ids = generate_websocket_component_ids()
        session_ids = generate_session_factory_ids()

        def check_cross_component_consistency(ws_ids, session_ids) -> Dict[str, Any]:
            """Check if IDs from different components are compatible"""
            consistency_report = {'thread_id_compatible': False, 'run_id_compatible': False, 'request_id_compatible': False, 'format_analysis': {}, 'compatibility_issues': []}
            ws_thread_parsed = UnifiedIdGenerator.parse_id(ws_ids['thread_id'])
            session_thread_parsed = UnifiedIdGenerator.parse_id(session_ids['thread_id'])
            consistency_report['thread_id_compatible'] = ws_thread_parsed is not None and session_thread_parsed is not None and ws_thread_parsed.prefix.startswith('thread_') and session_thread_parsed.prefix.startswith('thread_')
            if not consistency_report['thread_id_compatible']:
                consistency_report['compatibility_issues'].append(f"Thread ID format mismatch: WebSocket='{ws_ids['thread_id']}' vs Session='{session_ids['thread_id']}'")
            ws_run_parsed = UnifiedIdGenerator.parse_id(ws_ids['run_id'])
            session_run_parsed = UnifiedIdGenerator.parse_id(session_ids['run_id'])
            consistency_report['run_id_compatible'] = ws_run_parsed is not None and session_run_parsed is not None and ws_run_parsed.prefix.startswith('run_') and session_run_parsed.prefix.startswith('run_')
            if not consistency_report['run_id_compatible']:
                consistency_report['compatibility_issues'].append(f"Run ID format mismatch: WebSocket='{ws_ids['run_id']}' vs Session='{session_ids['run_id']}'")
            return consistency_report
        consistency_result = check_cross_component_consistency(websocket_ids, session_ids)
        assert consistency_result['thread_id_compatible'], f"CROSS-COMPONENT THREAD ID INCONSISTENCY: WebSocket and session components generate incompatible thread IDs. Issues: {consistency_result['compatibility_issues']}. This causes '404: Thread not found' errors when components try to share thread references."
        assert consistency_result['run_id_compatible'], f"CROSS-COMPONENT RUN ID INCONSISTENCY: WebSocket and session components generate incompatible run IDs. Issues: {consistency_result['compatibility_issues']}. This breaks agent execution context continuity across component boundaries."

    @pytest.mark.asyncio
    async def test_websocket_thread_lifecycle_integration(self):
        """FAILING TEST: Verify complete WebSocket-to-thread lifecycle works end-to-end
        
        EXPECTED FAILURE: This test should FAIL because the lifecycle from WebSocket
        connection to thread creation to session management is broken by ID incompatibilities.
        """
        user_id = 'lifecycle_test_user'
        websocket_timestamp = int(time.time() * 1000)
        websocket_context = {'connection_id': f'ws_conn_{user_id}_{websocket_timestamp}', 'user_id': user_id, 'thread_id': f'websocket_factory_{websocket_timestamp}', 'run_id': f'websocket_factory_{websocket_timestamp}', 'timestamp': websocket_timestamp}
        lifecycle_steps = []
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance

            def mock_thread_create(*args, **kwargs):
                thread_id = kwargs.get('id', args[1] if len(args) > 1 else None)
                lifecycle_steps.append(f'Thread creation attempted with ID: {thread_id}')
                if not thread_id or not thread_id.startswith('thread_'):
                    lifecycle_steps.append(f'Thread creation FAILED: Invalid format {thread_id}')
                    raise ValueError(f'Invalid thread ID format: {thread_id}')
                lifecycle_steps.append(f'Thread creation SUCCESS: {thread_id}')
                return Mock(id=thread_id)
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)
            mock_repo_instance.create = AsyncMock(side_effect=mock_thread_create)
            session_creation_success = False
            session_error = None
            try:
                lifecycle_steps.append(f"Session creation attempted with thread_id: {websocket_context['thread_id']}")
                async with get_isolated_session(user_id=websocket_context['user_id'], request_id=None, thread_id=websocket_context['thread_id']) as session:
                    lifecycle_steps.append('Session creation SUCCESS')
                    session_creation_success = True
            except Exception as e:
                session_error = str(e)
                lifecycle_steps.append(f'Session creation FAILED: {session_error}')
            lifecycle_report = {'websocket_context': websocket_context, 'steps': lifecycle_steps, 'session_success': session_creation_success, 'session_error': session_error}
            assert session_creation_success, f'WEBSOCKET-THREAD LIFECYCLE FAILURE: Complete lifecycle from WebSocket connection to session creation failed. Lifecycle report: {lifecycle_report}. This proves the integration between WebSocket ID generation and thread management is broken.'

    @pytest.mark.asyncio
    async def test_concurrent_websocket_sessions_thread_isolation(self):
        """FAILING TEST: Verify concurrent WebSocket sessions maintain proper thread isolation
        
        EXPECTED FAILURE: This test should FAIL because ID generation inconsistencies
        cause thread isolation violations in multi-user scenarios.
        """
        user_contexts = []
        for i in range(5):
            timestamp = int(time.time() * 1000) + i
            user_contexts.append({'user_id': f'concurrent_user_{i}', 'websocket_id': f'websocket_factory_{timestamp}', 'thread_id': f'websocket_factory_{timestamp}', 'run_id': f'websocket_factory_{timestamp}', 'session_id': None})
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)
            mock_repo_instance.create = AsyncMock(return_value=Mock())
            session_results = []

            async def create_user_session(context):
                """Create session for one user context"""
                try:
                    async with get_isolated_session(user_id=context['user_id'], request_id=None, thread_id=context['thread_id']) as session:
                        return {'user_id': context['user_id'], 'success': True, 'thread_id': context['thread_id'], 'error': None}
                except Exception as e:
                    return {'user_id': context['user_id'], 'success': False, 'thread_id': context['thread_id'], 'error': str(e)}
            tasks = [create_user_session(context) for context in user_contexts]
            session_results = await asyncio.gather(*tasks, return_exceptions=True)
            successful_sessions = [r for r in session_results if isinstance(r, dict) and r.get('success', False)]
            failed_sessions = [r for r in session_results if isinstance(r, dict) and (not r.get('success', False))]
            exception_sessions = [r for r in session_results if isinstance(r, Exception)]
            isolation_report = {'total_attempts': len(user_contexts), 'successful_sessions': len(successful_sessions), 'failed_sessions': len(failed_sessions), 'exception_sessions': len(exception_sessions), 'success_rate': len(successful_sessions) / len(user_contexts), 'failure_details': failed_sessions + [str(e) for e in exception_sessions]}
            assert isolation_report['success_rate'] == 1.0, f"CONCURRENT SESSION ISOLATION FAILURE: {isolation_report['failed_sessions']} out of {isolation_report['total_attempts']} concurrent WebSocket sessions failed. Isolation report: {isolation_report}. This proves ID format inconsistencies break multi-user session isolation."

    @pytest.mark.asyncio
    async def test_websocket_thread_id_persistence_consistency(self):
        """FAILING TEST: Verify WebSocket thread IDs persist correctly in database
        
        EXPECTED FAILURE: This test should FAIL because WebSocket-generated thread IDs
        cannot be properly persisted due to format incompatibilities.
        """
        user_id = 'persistence_test_user'
        websocket_thread_id = f'websocket_factory_{int(time.time() * 1000)}'
        persistence_log = []
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance

            async def mock_get_by_id(session, thread_id):
                persistence_log.append(f'Thread lookup: {thread_id}')
                return None

            async def mock_create(session, **kwargs):
                thread_id = kwargs.get('id')
                persistence_log.append(f'Thread creation attempt: {thread_id}')
                parsed = UnifiedIdGenerator.parse_id(thread_id)
                if not parsed or not parsed.prefix.startswith('thread_'):
                    persistence_log.append(f'Thread creation FAILED: Invalid format {thread_id}')
                    raise ValueError(f'Invalid thread ID format: {thread_id}')
                persistence_log.append(f'Thread creation SUCCESS: {thread_id}')
                return Mock(id=thread_id)
            mock_repo_instance.get_by_id = mock_get_by_id
            mock_repo_instance.create = mock_create
            persistence_success = False
            persistence_error = None
            try:
                async with get_isolated_session(user_id=user_id, request_id=None, thread_id=websocket_thread_id) as session:
                    persistence_success = True
            except Exception as e:
                persistence_error = str(e)
                persistence_log.append(f'Overall persistence FAILED: {persistence_error}')
            persistence_report = {'websocket_thread_id': websocket_thread_id, 'persistence_log': persistence_log, 'persistence_success': persistence_success, 'persistence_error': persistence_error}
            assert persistence_success, f"WEBSOCKET THREAD PERSISTENCE FAILURE: WebSocket thread ID '{websocket_thread_id}' could not be persisted in database. Persistence report: {persistence_report}. This proves WebSocket factory generates thread IDs incompatible with database persistence requirements."

    @pytest.mark.asyncio
    async def test_thread_id_format_migration_integration(self):
        """FAILING TEST: Verify system can handle migration from old to new thread ID formats
        
        EXPECTED FAILURE: This test should FAIL because the system cannot handle
        mixed thread ID formats during migration scenarios.
        """
        mixed_thread_contexts = [{'format': 'legacy_websocket', 'thread_id': f'websocket_factory_{int(time.time() * 1000)}', 'user_id': 'migration_user_1', 'description': 'Legacy WebSocket factory format'}, {'format': 'legacy_manual_uuid', 'thread_id': f'req_{uuid.uuid4().hex[:12]}', 'user_id': 'migration_user_2', 'description': 'Legacy manual UUID format'}, {'format': 'ssot_compliant', 'thread_id': UnifiedIdGenerator.generate_user_context_ids('migration_user_3', 'session')[0], 'user_id': 'migration_user_3', 'description': 'New SSOT compliant format'}]
        migration_results = []
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)

            async def mock_create_with_validation(session, **kwargs):
                thread_id = kwargs.get('id')
                parsed = UnifiedIdGenerator.parse_id(thread_id)
                if not parsed or not parsed.prefix.startswith('thread_'):
                    raise ValueError(f'Invalid thread ID format: {thread_id}')
                return Mock(id=thread_id)
            mock_repo_instance.create = mock_create_with_validation
            for context in mixed_thread_contexts:
                try:
                    async with get_isolated_session(user_id=context['user_id'], request_id=None, thread_id=context['thread_id']) as session:
                        migration_results.append({'format': context['format'], 'thread_id': context['thread_id'], 'success': True, 'error': None})
                except Exception as e:
                    migration_results.append({'format': context['format'], 'thread_id': context['thread_id'], 'success': False, 'error': str(e)})
            successful_formats = [r for r in migration_results if r['success']]
            failed_formats = [r for r in migration_results if not r['success']]
            migration_report = {'total_formats_tested': len(mixed_thread_contexts), 'successful_formats': len(successful_formats), 'failed_formats': len(failed_formats), 'compatibility_rate': len(successful_formats) / len(mixed_thread_contexts), 'format_breakdown': migration_results}
            assert migration_report['compatibility_rate'] == 1.0, f"MIGRATION FORMAT COMPATIBILITY FAILURE: Only {migration_report['successful_formats']} out of {migration_report['total_formats_tested']} thread ID formats work during migration. Migration report: {migration_report}. This proves the system cannot handle mixed thread ID formats, breaking migration scenarios and backward compatibility."
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')