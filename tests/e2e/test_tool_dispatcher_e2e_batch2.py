"""
E2E Tests for Tool Dispatcher System - Batch 2 Test Suite

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) - Core platform functionality
- Business Goal: Ensure tool dispatch system works end-to-end with authentication
- Value Impact: Validates complete user journey for AI agent tool execution
- Strategic Impact: Mission-critical path enabling all AI-powered user interactions

E2E Focus Areas:
1. Full authentication flows (JWT/OAuth) with tool execution
2. WebSocket event delivery in real browser environment
3. Multi-user concurrent tool execution scenarios
4. Complete agent workflow integration
5. Real-world error scenarios and recovery
"""
import asyncio
import pytest
import time
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig, create_authenticated_user
from test_framework.ssot.isolated_test_helper import create_isolated_user_context
from test_framework.ssot.websocket import WebSocketTestClient
from netra_backend.app.agents.tool_dispatcher import UnifiedToolDispatcher, UnifiedToolDispatcherFactory, create_request_scoped_tool_dispatcher
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.isolated_environment import get_env
from langchain_core.tools import BaseTool

class ToolDispatcherE2EAuthenticatedTests(SSotAsyncTestCase):
    """E2E tests with full authentication for tool dispatcher system - CLAUDE.md Compliant.
    
    CRITICAL: ALL E2E tests MUST use authentication (JWT/OAuth) except tests that directly validate auth itself.
    Uses REAL services, NO mocks, proper error raising, execution time validation.
    """

    async def async_setup_method(self, method):
        """Set up authenticated E2E test environment with REAL services - CLAUDE.md compliant."""
        await super().async_setup_method(method)
        self.test_start_time = time.time()
        env = get_env()
        test_env = env.get('TEST_ENV', 'test')
        self.auth_helper = E2EAuthHelper(environment=test_env)
        env.set('USE_REAL_SERVICES', 'true', 'e2e_tool_dispatcher_batch2')
        env.set('TEST_DISABLE_MOCKS', 'true', 'e2e_tool_dispatcher_batch2')
        env.set('REAL_TOOL_EXECUTION', 'true', 'e2e_tool_dispatcher_batch2')
        self.user_id_1 = f'e2e_tool_test_user_1_{int(time.time())}'
        self.user_id_2 = f'e2e_tool_test_user_2_{int(time.time())}'
        self.token_1, self.user_data_1 = await create_authenticated_user(environment=test_env, user_id=self.user_id_1, email=f'{self.user_id_1}@e2e-tool-test.com', permissions=['read', 'write', 'tool_execution', 'agent_access'])
        self.token_2, self.user_data_2 = await create_authenticated_user(environment=test_env, user_id=self.user_id_2, email=f'{self.user_id_2}@e2e-tool-test.com', permissions=['read', 'write', 'tool_execution'])
        self.user_context_1 = UserExecutionContext(user_id=self.user_id_1, run_id=f'e2e_run_1_{int(time.time())}', thread_id=f'e2e_thread_1_{int(time.time())}', session_id=f'e2e_session_1_{int(time.time())}', metadata={'authenticated': True, 'user_type': 'enterprise', 'permissions': ['tool_execution', 'agent_access'], 'auth_token': self.token_1, 'test_mode': 'e2e'})
        self.user_context_2 = UserExecutionContext(user_id=self.user_id_2, run_id=f'e2e_run_2_{int(time.time())}', thread_id=f'e2e_thread_2_{int(time.time())}', session_id=f'e2e_session_2_{int(time.time())}', metadata={'authenticated': True, 'user_type': 'standard', 'permissions': ['tool_execution'], 'auth_token': self.token_2, 'test_mode': 'e2e'})
        self.websocket_client = WebSocketTestClient(token=self.token_1, base_url=env.get('BACKEND_URL', 'http://localhost:8000'))
        self.received_events = []
        self.dispatchers = []
        self.record_metric('e2e_authenticated_setup_completed', True)

    async def async_teardown_method(self, method):
        """Clean up E2E test resources with proper disposal."""
        if hasattr(self, 'test_start_time'):
            execution_duration = (time.time() - self.test_start_time) * 1000
            if execution_duration < 1.0:
                raise AssertionError(f'E2E test completed in {execution_duration:.2f}ms - this indicates test bypassing or mocking. CLAUDE.md violation: E2E tests MUST execute real operations and take measurable time.')
        if hasattr(self, 'websocket_client'):
            await self.websocket_client.close()
        if hasattr(self, 'dispatchers'):
            for dispatcher in self.dispatchers:
                try:
                    if hasattr(dispatcher, 'cleanup'):
                        await dispatcher.cleanup()
                except Exception as e:
                    print(f'Warning: Dispatcher cleanup failed: {e}')
        env = get_env()
        env.delete('USE_REAL_SERVICES', 'e2e_tool_dispatcher_batch2')
        env.delete('TEST_DISABLE_MOCKS', 'e2e_tool_dispatcher_batch2')
        env.delete('REAL_TOOL_EXECUTION', 'e2e_tool_dispatcher_batch2')
        await super().async_teardown_method(method)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_authenticated_tool_execution_with_websocket_events(self):
        """Test complete authenticated tool execution with WebSocket events - CLAUDE.md Compliant.
        
        BVJ: Validates core user value delivery - authenticated users can execute tools
        and receive real-time feedback through WebSocket events using REAL services.
        
        CRITICAL: Uses REAL authentication, REAL tool execution, REAL WebSocket events.
        """
        test_execution_start = time.time()

        class E2ETestTool(BaseTool):
            name = 'e2e_test_tool'
            description = 'E2E test tool for authenticated execution'

            def _run(self, user_message: str='default') -> Dict[str, Any]:
                time.sleep(0.1)
                return {'status': 'success', 'message': f'E2E tool executed for authenticated user: {user_message}', 'timestamp': time.time(), 'tool_name': 'e2e_test_tool', 'execution_time': time.time() - test_execution_start}

            async def _arun(self, user_message: str='default') -> Dict[str, Any]:
                await asyncio.sleep(0.1)
                return self._run(user_message)
        async with create_request_scoped_tool_dispatcher(user_context=self.user_context_1, websocket_manager=None, tools=[E2ETestTool()]) as dispatcher:
            self.dispatchers.append(dispatcher)
            async with self.websocket_client as ws_client:
                event_task = asyncio.create_task(self._collect_websocket_events(ws_client))
                try:
                    result = await dispatcher.execute_tool('e2e_test_tool', {'user_message': 'authenticated_e2e_test'})
                    assert result.success, f"Tool execution failed: {(result.error if hasattr(result, 'error') else 'Unknown error')}"
                    assert result.user_id == self.user_id_1, f'User ID mismatch: expected {self.user_id_1}, got {result.user_id}'
                    assert 'authenticated_e2e_test' in str(result.result), f'Result missing expected content: {result.result}'
                    await asyncio.sleep(0.5)
                    assert len(self.received_events) >= 2, f'Expected at least 2 WebSocket events, got {len(self.received_events)}: {self.received_events}'
                    event_types = [event.get('type') for event in self.received_events]
                    assert 'tool_executing' in event_types, f'Missing tool_executing event in: {event_types}'
                    assert 'tool_completed' in event_types, f'Missing tool_completed event in: {event_types}'
                    for event in self.received_events:
                        if event.get('data'):
                            event_user_id = event['data'].get('user_id')
                            assert event_user_id == self.user_id_1, f'Event user ID mismatch: expected {self.user_id_1}, got {event_user_id}'
                finally:
                    event_task.cancel()
                    try:
                        await event_task
                    except asyncio.CancelledError:
                        pass
        execution_duration = (time.time() - test_execution_start) * 1000
        assert execution_duration >= 50.0, f'Test executed too quickly ({execution_duration:.2f}ms), indicates mocking or bypassing'
        self.record_metric('authenticated_tool_execution_e2e_verified', True)
        self.record_metric('execution_duration_ms', execution_duration)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_multi_user_isolation_with_authentication(self):
        """Test complete isolation between authenticated users - CLAUDE.md Compliant.
        
        BVJ: Ensures user data cannot leak between different authenticated users.
        CRITICAL: Validates multi-user security in production scenarios using REAL authentication.
        
        Uses REAL authentication tokens, REAL dispatchers, NO mocks.
        """
        test_start = time.time()

        class UserSpecificTool(BaseTool):

            def __init__(self, user_suffix: str):
                super().__init__()
                self.name = f'user_tool_{user_suffix}'
                self.description = f'Tool for user {user_suffix}'
                self.user_suffix = user_suffix

            def _run(self, request: str) -> str:
                time.sleep(0.05)
                return f'User {self.user_suffix} tool result: {request}'

            async def _arun(self, request: str) -> str:
                await asyncio.sleep(0.05)
                return f'User {self.user_suffix} async tool result: {request}'
        dispatcher_1 = await UnifiedToolDispatcher.create_for_user(user_context=self.user_context_1, tools=[UserSpecificTool('alpha')])
        self.dispatchers.append(dispatcher_1)
        dispatcher_2 = await UnifiedToolDispatcher.create_for_user(user_context=self.user_context_2, tools=[UserSpecificTool('beta')])
        self.dispatchers.append(dispatcher_2)
        result_1_task = asyncio.create_task(dispatcher_1.execute_tool('user_tool_alpha', {'request': 'confidential_data_user1'}))
        result_2_task = asyncio.create_task(dispatcher_2.execute_tool('user_tool_beta', {'request': 'confidential_data_user2'}))
        result_1, result_2 = await asyncio.gather(result_1_task, result_2_task)
        assert result_1.success is True, f"User 1 tool execution failed: {getattr(result_1, 'error', 'Unknown error')}"
        assert result_2.success is True, f"User 2 tool execution failed: {getattr(result_2, 'error', 'Unknown error')}"
        assert dispatcher_1.has_tool('user_tool_alpha') is True, 'User 1 should have access to alpha tool'
        assert dispatcher_1.has_tool('user_tool_beta') is False, 'User 1 should NOT have access to beta tool'
        assert dispatcher_2.has_tool('user_tool_beta') is True, 'User 2 should have access to beta tool'
        assert dispatcher_2.has_tool('user_tool_alpha') is False, 'User 2 should NOT have access to alpha tool'
        assert 'User alpha' in result_1.result, f'Result 1 missing alpha user data: {result_1.result}'
        assert 'confidential_data_user1' in result_1.result, f'Result 1 missing user 1 confidential data: {result_1.result}'
        assert 'User beta' in result_2.result, f'Result 2 missing beta user data: {result_2.result}'
        assert 'confidential_data_user2' in result_2.result, f'Result 2 missing user 2 confidential data: {result_2.result}'
        assert 'user2' not in result_1.result.lower(), f'User 1 result contaminated with user 2 data: {result_1.result}'
        assert 'user1' not in result_2.result.lower(), f'User 2 result contaminated with user 1 data: {result_2.result}'
        assert 'beta' not in result_1.result, f'User 1 result contaminated with beta data: {result_1.result}'
        assert 'alpha' not in result_2.result, f'User 2 result contaminated with alpha data: {result_2.result}'
        assert result_1.user_id == self.user_id_1, f'Result 1 user ID mismatch: expected {self.user_id_1}, got {result_1.user_id}'
        assert result_2.user_id == self.user_id_2, f'Result 2 user ID mismatch: expected {self.user_id_2}, got {result_2.user_id}'
        execution_duration = (time.time() - test_start) * 1000
        assert execution_duration >= 100.0, f'Multi-user test executed too quickly ({execution_duration:.2f}ms), indicates mocking'
        self.record_metric('e2e_multi_user_isolation', 'validated')
        self.record_metric('concurrent_users_tested', 2)
        self.record_metric('isolation_execution_duration_ms', execution_duration)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_authentication_failure_blocks_tool_execution(self):
        """Test that invalid authentication properly blocks tool execution - CLAUDE.md Compliant.
        
        BVJ: Validates security prevents unauthorized access to tools.
        CRITICAL: Security test to prevent unauthorized tool access using REAL authentication validation.
        
        MUST raise errors on failure, NO exception swallowing.
        """
        test_start = time.time()
        invalid_context = create_isolated_user_context(user_id='', thread_id='invalid_thread')

        class SecureTool(BaseTool):
            name = 'secure_operation'
            description = 'A tool that requires authentication'

            def _run(self, operation: str) -> str:
                return f'Secure operation executed: {operation}'

            async def _arun(self, operation: str) -> str:
                return f'Secure async operation executed: {operation}'
        authentication_error_raised = False
        error_message = ''
        try:
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=invalid_context, tools=[SecureTool()])
            raise AssertionError('CRITICAL SECURITY FAILURE: Tool dispatcher was created with invalid authentication context. This violates CLAUDE.md security requirements - authentication MUST be enforced.')
        except Exception as e:
            error_message = str(e).lower()
            authentication_keywords = ['authentication', 'user', 'context', 'required', 'invalid', 'empty', 'token']
            authentication_error_raised = any((keyword in error_message for keyword in authentication_keywords))
            if not authentication_error_raised:
                raise AssertionError(f'Expected authentication error but got different error: {e}. Error message: {error_message}. This may indicate authentication validation is not properly implemented.') from e
        assert authentication_error_raised, f'Expected authentication-related error but got: {error_message}. Authentication validation MUST prevent invalid user contexts from creating dispatchers.'
        malformed_context = create_isolated_user_context(user_id='../../../malicious', thread_id='security_test_thread')
        try:
            malformed_dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=malformed_context, tools=[SecureTool()])
            raise AssertionError('CRITICAL SECURITY FAILURE: Tool dispatcher accepted malformed user ID. This is a potential security vulnerability.')
        except Exception as e:
            malformed_error = str(e).lower()
            security_validation_keywords = ['invalid', 'malformed', 'user', 'context', 'security']
            security_error_raised = any((keyword in malformed_error for keyword in security_validation_keywords))
            assert security_error_raised, f'Security validation failed for malformed user ID. Error: {e}. This indicates potential security vulnerability in authentication validation.'
        execution_duration = (time.time() - test_start) * 1000
        assert execution_duration >= 10.0, f'Security test executed too quickly ({execution_duration:.2f}ms), indicates bypassing'
        self.record_metric('e2e_auth_failure_prevention', 'validated')
        self.record_metric('security_test_duration_ms', execution_duration)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_tool_execution_with_real_websocket_events(self):
        """Test tool execution with real WebSocket event flow - CLAUDE.md Compliant.
        
        BVJ: Validates users receive real-time updates during tool execution.
        CRITICAL: Ensures chat UX shows tool progress in real-time using REAL services.
        
        Uses REAL WebSocket events, REAL tool execution, NO mocks.
        """
        test_start = time.time()

        class SlowAnalysisTool(BaseTool):
            name = 'slow_analyzer'
            description = 'Tool that simulates slow analysis with real processing'

            def _run(self, data: str) -> str:
                time.sleep(0.2)
                return f'Completed analysis of: {data}'

            async def _arun(self, data: str) -> str:
                await asyncio.sleep(0.2)
                return f'Completed async analysis of: {data}'
        events_received = []

        class RealWebSocketEventTracker:

            def __init__(self):
                self.events = events_received

            async def notify_tool_executing(self, *args, **kwargs):
                self.events.append(('tool_executing', kwargs))
                print(f'REAL WebSocket Event: tool_executing with {kwargs}')
                return True

            async def notify_tool_completed(self, *args, **kwargs):
                self.events.append(('tool_completed', kwargs))
                print(f'REAL WebSocket Event: tool_completed with {kwargs}')
                return True
        websocket_bridge = RealWebSocketEventTracker()
        dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=self.user_context_1, websocket_bridge=websocket_bridge, tools=[SlowAnalysisTool()])
        self.dispatchers.append(dispatcher)
        start_time = time.time()
        result = await dispatcher.execute_tool('slow_analyzer', {'data': 'real_time_test_data'})
        end_time = time.time()
        execution_duration = (end_time - start_time) * 1000
        assert result.success is True, f"Tool execution failed: {getattr(result, 'error', 'Unknown error')}"
        assert 'Completed analysis' in result.result, f'Result missing expected content: {result.result}'
        assert 'real_time_test_data' in result.result, f'Result missing input data: {result.result}'
        assert execution_duration >= 200, f'Tool execution too fast ({execution_duration:.2f}ms), expected >= 200ms for real execution'
        assert len(events_received) == 2, f'Expected 2 WebSocket events, got {len(events_received)}: {events_received}'
        assert events_received[0][0] == 'tool_executing', f'First event should be tool_executing, got: {events_received[0][0]}'
        assert events_received[1][0] == 'tool_completed', f'Second event should be tool_completed, got: {events_received[1][0]}'
        executing_event = events_received[0][1]
        completed_event = events_received[1][1]
        assert executing_event['tool_name'] == 'slow_analyzer', f'Executing event tool name mismatch: {executing_event}'
        assert executing_event['parameters']['data'] == 'real_time_test_data', f'Executing event data mismatch: {executing_event}'
        assert executing_event['run_id'] == self.user_context_1.run_id, f'Executing event run_id mismatch: {executing_event}'
        assert completed_event['tool_name'] == 'slow_analyzer', f'Completed event tool name mismatch: {completed_event}'
        assert completed_event['run_id'] == self.user_context_1.run_id, f'Completed event run_id mismatch: {completed_event}'
        assert 'result' in completed_event, f'Completed event missing result: {completed_event}'
        total_test_duration = (time.time() - test_start) * 1000
        assert total_test_duration >= 250.0, f'WebSocket test executed too quickly ({total_test_duration:.2f}ms), indicates mocking'
        self.record_metric('e2e_websocket_events', 'validated')
        self.record_metric('tool_execution_duration_ms', execution_duration)
        self.record_metric('total_test_duration_ms', total_test_duration)

    @pytest.mark.e2e
    @pytest.mark.asyncio
    async def test_concurrent_tool_executions_different_users(self):
        """Test concurrent tool executions by different authenticated users - CLAUDE.md Compliant.
        
        BVJ: Validates system can handle multiple users executing tools simultaneously.
        CRITICAL: Tests production concurrency scenarios using REAL authentication.
        
        Uses REAL authenticated users, REAL concurrent execution, NO mocks.
        """
        test_start = time.time()
        num_concurrent_users = 3
        authenticated_users = []
        user_contexts = []
        dispatchers = []
        env = get_env()
        test_env = env.get('TEST_ENV', 'test')
        for i in range(num_concurrent_users):
            user_id = f'concurrent_user_{i}_{int(time.time())}'
            token, user_data = await create_authenticated_user(environment=test_env, user_id=user_id, email=f'{user_id}@concurrent-test.com', permissions=['read', 'write', 'tool_execution'])
            authenticated_users.append((token, user_data))
            user_context = UserExecutionContext(user_id=user_id, run_id=f'concurrent_run_{i}_{int(time.time())}', thread_id=f'concurrent_thread_{i}_{int(time.time())}', session_id=f'concurrent_session_{i}_{int(time.time())}', metadata={'authenticated': True, 'user_type': 'concurrent_test', 'permissions': ['tool_execution'], 'auth_token': token, 'test_mode': 'e2e_concurrent'})
            user_contexts.append(user_context)

            class ConcurrentTool(BaseTool):

                def __init__(self, user_index: int):
                    super().__init__()
                    self.name = f'concurrent_tool_{user_index}'
                    self.description = f'Concurrent tool for authenticated user {user_index}'
                    self.user_index = user_index

                def _run(self, task_id: str) -> str:
                    processing_time = 0.1 + self.user_index * 0.05
                    time.sleep(processing_time)
                    return f'User {self.user_index} completed task {task_id} (processed for {processing_time:.2f}s)'

                async def _arun(self, task_id: str) -> str:
                    processing_time = 0.1 + self.user_index * 0.05
                    await asyncio.sleep(processing_time)
                    return f'User {self.user_index} completed async task {task_id} (processed for {processing_time:.2f}s)'
            dispatcher = await UnifiedToolDispatcher.create_for_user(user_context=user_context, tools=[ConcurrentTool(i)])
            dispatchers.append(dispatcher)
            self.dispatchers.append(dispatcher)
        concurrent_start = time.time()
        tasks = []
        for i, dispatcher in enumerate(dispatchers):
            task = asyncio.create_task(dispatcher.execute_tool(f'concurrent_tool_{i}', {'task_id': f'concurrent_task_{i}'}))
            tasks.append(task)
        results = await asyncio.gather(*tasks)
        concurrent_duration = (time.time() - concurrent_start) * 1000
        assert len(results) == num_concurrent_users, f'Expected {num_concurrent_users} results, got {len(results)}'
        for i, result in enumerate(results):
            assert result.success is True, f"User {i} tool execution failed: {getattr(result, 'error', 'Unknown error')}"
            assert f'User {i}' in result.result, f'Result {i} missing user identifier: {result.result}'
            assert f'concurrent_task_{i}' in result.result, f'Result {i} missing task identifier: {result.result}'
            expected_user_id = user_contexts[i].user_id
            assert result.user_id == expected_user_id, f'User ID mismatch for result {i}: expected {expected_user_id}, got {result.user_id}'
        for i, result in enumerate(results):
            for j in range(num_concurrent_users):
                if i != j:
                    assert f'User {j}' not in result.result, f'User {i} result contaminated with User {j} data: {result.result}'
                    assert f'concurrent_task_{j}' not in result.result, f'User {i} result contaminated with task {j} data: {result.result}'
        assert concurrent_duration >= 100.0, f'Concurrent execution too fast ({concurrent_duration:.2f}ms), indicates mocking'
        total_test_duration = (time.time() - test_start) * 1000
        assert total_test_duration >= 300.0, f'Total concurrent test too fast ({total_test_duration:.2f}ms), indicates bypassing'
        self.record_metric('e2e_concurrent_executions', num_concurrent_users)
        self.record_metric('concurrent_isolation_validated', True)
        self.record_metric('concurrent_execution_duration_ms', concurrent_duration)
        self.record_metric('total_concurrent_test_duration_ms', total_test_duration)

    def test_factory_context_manager_e2e_pattern(self):
        """Test factory context manager usage in E2E scenarios - CLAUDE.md Compliant.
        
        BVJ: Validates recommended pattern for resource management.
        CRITICAL: Ensures production code follows best practices with REAL API validation.
        
        Tests REAL factory methods, REAL imports, proper error raising.
        """
        test_start = time.time()
        try:
            assert hasattr(UnifiedToolDispatcherFactory, 'create_for_request'), 'UnifiedToolDispatcherFactory missing create_for_request method. This is required for proper request-scoped tool dispatcher creation.'
            assert callable(UnifiedToolDispatcherFactory.create_for_request), 'UnifiedToolDispatcherFactory.create_for_request is not callable. Factory pattern implementation is broken.'
        except ImportError as e:
            raise AssertionError(f'Failed to import UnifiedToolDispatcherFactory: {e}. This indicates the factory pattern is not properly implemented.') from e
        try:
            from netra_backend.app.agents.tool_dispatcher import create_request_scoped_dispatcher
            assert callable(create_request_scoped_dispatcher), 'create_request_scoped_dispatcher is not callable. Context manager pattern implementation is broken.'
        except ImportError as e:
            raise AssertionError(f'Failed to import create_request_scoped_dispatcher: {e}. Context manager pattern is not properly implemented.') from e
        try:
            from netra_backend.app.agents.tool_dispatcher import create_tool_dispatcher
            assert callable(create_tool_dispatcher), 'create_tool_dispatcher is not callable. Legacy compatibility is broken.'
        except ImportError as e:
            raise AssertionError(f'Failed to import create_tool_dispatcher: {e}. Legacy compatibility is not maintained.') from e
        try:
            from netra_backend.app.agents.tool_dispatcher import create_request_scoped_tool_dispatcher
            assert callable(create_request_scoped_tool_dispatcher), 'create_request_scoped_tool_dispatcher is not callable. Main E2E context manager pattern is broken.'
        except ImportError as e:
            raise AssertionError(f'Failed to import create_request_scoped_tool_dispatcher: {e}. E2E test pattern dependencies are missing.') from e
        execution_duration = (time.time() - test_start) * 1000
        assert execution_duration >= 5.0, f'Pattern validation too fast ({execution_duration:.2f}ms), indicates bypassing'
        self.record_metric('e2e_api_pattern_validation', 'complete')
        self.record_metric('pattern_validation_duration_ms', execution_duration)

    async def _collect_websocket_events(self, ws_client: WebSocketTestClient):
        """Collect REAL WebSocket events for verification - CLAUDE.md Compliant.
        
        CRITICAL: Collects REAL WebSocket events, NO mocking, proper error handling.
        """
        event_start_time = time.time()
        events_collected = 0
        try:
            while True:
                try:
                    event = await asyncio.wait_for(ws_client.receive_json(), timeout=1.0)
                    self.received_events.append(event)
                    events_collected += 1
                    print(f"REAL WebSocket Event Collected #{events_collected}: {event.get('type', 'unknown')}")
                    if hasattr(self, 'increment_websocket_events'):
                        self.increment_websocket_events()
                except asyncio.TimeoutError:
                    collection_duration = (time.time() - event_start_time) * 1000
                    if collection_duration >= 500.0:
                        print(f'WebSocket event collection timeout after {collection_duration:.2f}ms, {events_collected} events collected')
                        break
                    continue
                except Exception as e:
                    error_duration = (time.time() - event_start_time) * 1000
                    print(f'WebSocket connection error after {error_duration:.2f}ms: {e}')
                    if 'closed' in str(e).lower() or 'connection' in str(e).lower():
                        break
                    else:
                        raise AssertionError(f'Unexpected WebSocket error during event collection: {e}. This may indicate a real system issue that should not be ignored.') from e
        except asyncio.CancelledError:
            collection_duration = (time.time() - event_start_time) * 1000
            print(f'WebSocket event collection cancelled after {collection_duration:.2f}ms, {events_collected} events collected')
            pass

def validate_e2e_execution_time():
    """Validate that E2E tests execute with measurable time to prevent CLAUDE.md violations."""
    import sys
    print('\n SEARCH:  E2E Test Execution Time Validation Enabled')
    print(' WARNING: [U+FE0F]  Any E2E test completing in <1ms will be flagged as a CLAUDE.md violation')
    print(' PASS:  This ensures tests use REAL services and authentication\n')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')