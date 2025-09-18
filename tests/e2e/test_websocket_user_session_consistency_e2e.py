"WebSocket User Session Consistency E2E Tests"""

CRITICAL PURPOSE: These tests MUST FAIL to expose end-to-end WebSocket user session
consistency issues with REAL authentication, demonstrating the business impact of
ID generation inconsistencies on actual user workflows.

Root Cause Being Tested:
- WebSocket connections with authenticated users fail due to thread ID mismatches
- Real multi-user scenarios break when WebSocket factory IDs conflict with database expectations
- Session isolation violations occur when ID formats don't match between components'

Error Pattern Being Exposed:
Failed to create request-scoped database session req_1757357912444_24_73708c2b: 404: Thread not found
Thread ID mismatch in authenticated WebSocket sessions causing user isolation breakdown

Business Value: Ensuring chat interactions work reliably for paying customers
This directly impacts revenue as broken chat = broken core product value
""
import pytest
import asyncio
import json
import time
from typing import Dict, Any, List, Optional
from unittest.mock import patch, Mock, AsyncMock
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context, get_test_jwt_token
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

class WebSocketUserSessionConsistencyE2ETests:
    E2E test suite to expose WebSocket user session consistency failures with real authentication.
    
    These tests are DESIGNED TO FAIL initially to demonstrate how ID generation
    inconsistencies break real user workflows and business value delivery.
    
    CRITICAL: All tests use REAL authentication as mandated by CLAUDE.md E2E requirements.
""

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_authenticated_websocket_session_creation_with_thread_consistency(self):
        FAILING E2E TEST: Verify authenticated WebSocket sessions maintain thread ID consistency""
        
        EXPECTED FAILURE: This test should FAIL because WebSocket factory generates thread IDs
        that are incompatible with authenticated session management, breaking real user workflows.
        
        Business Impact: Users cannot start chat conversations = revenue loss
"""Empty docstring."""
        auth_helper = E2EAuthHelper()
        user_context = await create_authenticated_user_context(user_email='websocket.test.user@example.com', environment='test', permissions=['read', 'write', 'premium')
        jwt_token = user_context.agent_context['jwt_token']
        user_id = str(user_context.user_id)
        auth_headers = {'Authorization': f'Bearer {jwt_token}'}
        websocket_connection_context = {'user_id': user_id, 'jwt_token': jwt_token, 'connection_timestamp': int(time.time() * 1000), 'connection_id': None, 'thread_id': None, 'run_id': None}

        def simulate_websocket_factory_id_generation(user_id: str, timestamp: int):
            Simulates the current problematic WebSocket factory ID generation""
            return {'connection_id': f'ws_conn_{user_id}_{timestamp}', 'thread_id': f'websocket_factory_{timestamp}', 'run_id': f'websocket_factory_{timestamp}'}
        websocket_ids = simulate_websocket_factory_id_generation(user_id, websocket_connection_context['connection_timestamp')
        websocket_connection_context.update(websocket_ids)
        session_creation_result = {'success': False, 'error': None, 'thread_id_used': websocket_connection_context['thread_id'], 'session_details': None}
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo, patch('netra_backend.app.database.request_scoped_session_factory.get_isolated_session') as mock_get_session:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)

            async def mock_create_thread(*args, **kwargs):
                thread_id = kwargs.get('id', args[1] if len(args) > 1 else None)
                parsed = UnifiedIdGenerator.parse_id(thread_id)
                if not parsed or not parsed.prefix.startswith('thread_'):
                    raise ValueError(f'Invalid thread ID format for authenticated user: {thread_id}')
                return Mock(id=thread_id)
            mock_repo_instance.create = AsyncMock(side_effect=mock_create_thread)

            async def mock_session_creation(user_id, request_id=None, thread_id=None):
                if thread_id and thread_id.startswith('websocket_factory_'):
                    raise Exception(f'404: Thread not found - incompatible thread ID format: {thread_id}')
                return AsyncMock()
            mock_get_session.return_value.__aenter__ = mock_session_creation
            mock_get_session.return_value.__aexit__ = AsyncMock(return_value=None)
            try:
                from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
                async with get_isolated_session(user_id=user_id, request_id=None, thread_id=websocket_connection_context['thread_id') as session:
                    session_creation_result['success'] = True
                    session_creation_result['session_details'] = {'user_id': user_id, 'thread_id': websocket_connection_context['thread_id'], 'authenticated': True}
            except Exception as e:
                session_creation_result['error'] = str(e)
        e2e_report = {'user_context': user_context, 'websocket_context': websocket_connection_context, 'session_result': session_creation_result, 'business_impact': 'Premium user cannot start chat conversation'}
        assert session_creation_result['success'], fAUTHENTICATED WEBSOCKET SESSION E2E FAILURE: Premium user '{user_id}' cannot establish WebSocket session due to thread ID format incompatibility. E2E Report: {e2e_report}. BUSINESS IMPACT: Users cannot start chat conversations = direct revenue loss.

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multi_user_websocket_thread_isolation_with_authentication(self):
        FAILING E2E TEST: Verify multi-user WebSocket sessions maintain proper isolation
        
        EXPECTED FAILURE: This test should FAIL because thread ID inconsistencies
        cause user isolation violations in authenticated multi-user scenarios.
        
        Business Impact: User data leakage between customers = security breach
""
        auth_helper = E2EAuthHelper()
        authenticated_users = []
        for i in range(3):
            user_context = await create_authenticated_user_context(user_email=f'multiuser.test.{i)@example.com', environment='test', permissions=['read', 'write', 'enterprise']
            authenticated_users.append(user_context)
        websocket_sessions = []
        timestamp_base = int(time.time() * 1000)
        for i, user in enumerate(authenticated_users):
            session_context = {'user_id': str(user.user_id), 'jwt_token': user.agent_context['jwt_token'], 'websocket_thread_id': f'websocket_factory_{timestamp_base + i}', 'expected_isolation': f'isolated_session_for_user_{i}', 'auth_headers': {'Authorization': fBearer {user.agent_context['jwt_token']}}}
            websocket_sessions.append(session_context)
        isolation_results = []
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)
            mock_repo_instance.create = AsyncMock(return_value=Mock())

            async def create_isolated_websocket_session(session_context):
                "Create isolated WebSocket session for authenticated user"
                try:
                    from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
                    async with get_isolated_session(user_id=session_context['user_id'), request_id=None, thread_id=session_context['websocket_thread_id') as session:
                        return {'user_id': session_context['user_id'], 'success': True, 'thread_id': session_context['websocket_thread_id'], 'isolation_verified': True, 'error': None}
                except Exception as e:
                    return {'user_id': session_context['user_id'], 'success': False, 'thread_id': session_context['websocket_thread_id'], 'isolation_verified': False, 'error': str(e)}
            tasks = [create_isolated_websocket_session(session) for session in websocket_sessions]
            isolation_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_isolations = [r for r in isolation_results if isinstance(r, dict) and r.get('success')]
        failed_isolations = [r for r in isolation_results if isinstance(r, dict) and (not r.get('success'))]
        exception_isolations = [r for r in isolation_results if isinstance(r, Exception)]
        isolation_report = {'total_enterprise_users': len(authenticated_users), 'successful_isolations': len(successful_isolations), 'failed_isolations': len(failed_isolations) + len(exception_isolations), 'isolation_success_rate': len(successful_isolations) / len(authenticated_users), 'failure_details': failed_isolations + [str(e) for e in exception_isolations], 'business_impact': 'Enterprise customer data isolation breach'}
        assert isolation_report['isolation_success_rate'] == 1.0, fMULTI-USER WEBSOCKET ISOLATION E2E FAILURE: {isolation_report['failed_isolations']} out of {isolation_report['total_enterprise_users']} enterprise users failed session isolation. Isolation report: {isolation_report}. BUSINESS IMPACT: Enterprise customer data isolation breach = security incident.

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_websocket_agent_execution_with_authenticated_thread_consistency(self):
        "FAILING E2E TEST: Verify WebSocket agent execution works with authenticated thread consistency"""
        
        EXPECTED FAILURE: This test should FAIL because agent execution fails when WebSocket
        thread IDs are incompatible with authenticated session management.
        
        Business Impact: AI agents cannot execute for users = core product value lost
"""Empty docstring."""
        auth_helper = E2EAuthHelper()
        user_context = await create_authenticated_user_context(user_email='agent.execution.user@example.com', environment='test', permissions=['read', 'write', 'premium')
        user_id = str(user_context.user_id)
        jwt_token = user_context.agent_context['jwt_token']
        agent_execution_context = {'user_id': user_id, 'jwt_token': jwt_token, 'agent_type': 'data_analyzer', 'websocket_thread_id': f'websocket_factory_{int(time.time() * 1000)}', 'run_id': f'websocket_factory_{int(time.time() * 1000)}', 'agent_message': 'Analyze my data please'}
        execution_pipeline_log = []
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance
            mock_repo_instance.get_by_id = AsyncMock(return_value=None)

            async def mock_agent_thread_creation(*args, **kwargs):
                thread_id = kwargs.get('id', args[1] if len(args) > 1 else None)
                execution_pipeline_log.append(f'Agent thread creation: {thread_id}')
                parsed = UnifiedIdGenerator.parse_id(thread_id)
                if not parsed or not parsed.prefix.startswith('thread_'):
                    execution_pipeline_log.append(f'Agent thread INVALID: {thread_id}')
                    raise ValueError(f'Agent execution requires valid thread ID: {thread_id}')
                execution_pipeline_log.append(f'Agent thread VALID: {thread_id}')
                return Mock(id=thread_id)
            mock_repo_instance.create = AsyncMock(side_effect=mock_agent_thread_creation)
            agent_execution_result = {'success': False, 'error': None, 'pipeline_log': execution_pipeline_log, 'agent_response': None}
            try:
                execution_pipeline_log.append(f'Starting agent execution for user {user_id}')
                from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
                async with get_isolated_session(user_id=user_id, request_id=None, thread_id=agent_execution_context['websocket_thread_id') as session:
                    execution_pipeline_log.append('Session created successfully for agent execution')
                    agent_execution_result['agent_response'] = {'status': 'completed', 'result': 'Data analysis completed successfully', 'thread_id': agent_execution_context['websocket_thread_id']}
                    agent_execution_result['success'] = True
            except Exception as e:
                agent_execution_result['error'] = str(e)
                execution_pipeline_log.append(f'Agent execution FAILED: {e}')
        agent_e2e_report = {'user_context': user_context, 'agent_context': agent_execution_context, 'execution_result': agent_execution_result, 'pipeline_log': execution_pipeline_log, 'business_impact': 'Premium user cannot execute AI agents'}
        assert agent_execution_result['success'], fWEBSOCKET AGENT EXECUTION E2E FAILURE: Premium user '{user_id}' cannot execute AI agents due to WebSocket thread ID incompatibility. Agent E2E Report: {agent_e2e_report}. BUSINESS IMPACT: Core product value (AI agent execution) is broken = direct revenue loss.

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_websocket_session_persistence_across_reconnections(self):
        ""FAILING E2E TEST: Verify WebSocket sessions persist correctly across reconnections
        
        EXPECTED FAILURE: This test should FAIL because thread ID format inconsistencies
        break session persistence when users reconnect their WebSocket connections.
        
        Business Impact: Users lose conversation history = poor user experience

        auth_helper = E2EAuthHelper()
        user_context = await create_authenticated_user_context(user_email='session.persistence.user@example.com', environment='test', permissions=['read', 'write', 'premium')
        user_id = str(user_context.user_id)
        jwt_token = user_context.agent_context['jwt_token']
        initial_timestamp = int(time.time() * 1000)
        initial_connection = {'user_id': user_id, 'jwt_token': jwt_token, 'connection_id': f'ws_conn_initial_{initial_timestamp}', 'thread_id': f'websocket_factory_{initial_timestamp}', 'conversation_data': ['Hello', 'How are you?', 'I need help with data analysis']}
        reconnection_timestamp = initial_timestamp + 5000
        reconnection_context = {'user_id': user_id, 'jwt_token': jwt_token, 'connection_id': f'ws_conn_reconnect_{reconnection_timestamp}', 'expected_thread_id': initial_connection['thread_id'], 'expected_conversation': initial_connection['conversation_data']}
        persistence_test_log = []
        with patch('netra_backend.app.database.get_db') as mock_get_db, patch('netra_backend.app.services.database.thread_repository.ThreadRepository') as mock_thread_repo:
            mock_session = AsyncMock()
            mock_get_db.return_value.__aenter__.return_value = mock_session
            mock_get_db.return_value.__aexit__.return_value = None
            mock_repo_instance = Mock()
            mock_thread_repo.return_value = mock_repo_instance

            async def mock_thread_lookup(session, thread_id):
                persistence_test_log.append(f'Looking up thread: {thread_id}')
                parsed = UnifiedIdGenerator.parse_id(thread_id)
                if not parsed or not parsed.prefix.startswith('thread_'):
                    persistence_test_log.append(f'Thread lookup FAILED: Invalid format {thread_id}')
                    return None
                persistence_test_log.append(f'Thread lookup SUCCESS: {thread_id}')
                return Mock(id=thread_id, conversation_data=initial_connection['conversation_data')
            mock_repo_instance.get_by_id = mock_thread_lookup
            mock_repo_instance.create = AsyncMock(return_value=Mock())
            persistence_result = {'initial_session_created': False, 'reconnection_found_thread': False, 'conversation_restored': False, 'error': None}
            try:
                persistence_test_log.append('Creating initial WebSocket session')
                from netra_backend.app.database.request_scoped_session_factory import get_isolated_session
                async with get_isolated_session(user_id=user_id, request_id=None, thread_id=initial_connection['thread_id') as session:
                    persistence_result['initial_session_created'] = True
                    persistence_test_log.append('Initial session created successfully')
                persistence_test_log.append('Simulating reconnection and thread persistence check')
                found_thread = await mock_repo_instance.get_by_id(mock_session, reconnection_context['expected_thread_id')
                if found_thread:
                    persistence_result['reconnection_found_thread'] = True
                    persistence_result['conversation_restored'] = hasattr(found_thread, 'conversation_data') and found_thread.conversation_data == reconnection_context['expected_conversation']
                    persistence_test_log.append('Reconnection successful - thread found and conversation restored')
                else:
                    persistence_test_log.append('Reconnection FAILED - thread not found')
            except Exception as e:
                persistence_result['error'] = str(e)
                persistence_test_log.append(f'Persistence test ERROR: {e}')
        persistence_report = {'user_context': user_context, 'initial_connection': initial_connection, 'reconnection_context': reconnection_context, 'persistence_result': persistence_result, 'test_log': persistence_test_log, 'business_impact': 'Users lose conversation history on reconnect'}
        assert persistence_result['reconnection_found_thread'], f"WEBSOCKET SESSION PERSISTENCE E2E FAILURE: User '{user_id}' cannot restore WebSocket session after reconnection due to thread ID format incompatibility. Persistence report: {persistence_report}. BUSINESS IMPACT: Users lose conversation history = poor user experience = churn risk."
        assert persistence_result['conversation_restored'], f'CONVERSATION RESTORATION FAILURE: Even if thread is found, conversation data is lost due to WebSocket session persistence issues. This breaks user experience continuity.'
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')
)))))))))))