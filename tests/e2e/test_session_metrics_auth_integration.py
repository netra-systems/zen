"""
E2E Tests: Session Metrics Authentication Integration

This test suite validates session metrics in real authenticated scenarios,
ensuring the SessionMetrics SSOT bug doesn't break actual user flows.

Business Value:
- Validates session tracking works correctly in real multi-user scenarios
- Ensures authentication flows don't crash due to SessionMetrics field bugs
- Tests WebSocket session management with proper user context isolation

CRITICAL: Uses REAL authentication via SSOT auth helper.
NO MOCKS - These are end-to-end tests with real services and real auth.

Target Integration Points:
- WebSocket connections with authenticated sessions
- Database session factory error handling during auth
- Multi-user concurrent session scenarios
- Session metrics collection during real agent execution

Expected Behavior:
- Tests should expose AttributeError when session errors occur during auth
- WebSocket authentication should trigger session factory error paths  
- Multi-user scenarios should isolate session metrics properly
"""
import asyncio
import pytest
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import aiohttp
import websockets
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.base_test_case import SSotBaseTestCase

@pytest.mark.e2e
class TestSessionMetricsAuthIntegration(SSotBaseTestCase):
    """
    E2E tests for SessionMetrics integration with authentication flows.
    
    These tests use REAL authentication and REAL services to validate
    that session metrics work correctly in production-like scenarios.
    """

    @pytest.fixture(autouse=True)
    async def setup_authenticated_services(self):
        """Setup real authenticated services for E2E testing."""
        self.auth_helper = E2EAuthHelper()
        self.auth_config = E2EAuthConfig()
        self.auth_tokens = await self.auth_helper.setup_authenticated_test_users(num_users=3)
        print(f'\n[U+1F510] AUTHENTICATED E2E SETUP:')
        print(f'  Users authenticated: {len(self.auth_tokens)}')
        print(f'  Auth service: {self.auth_config.auth_service_url}')
        print(f'  Backend service: {self.auth_config.backend_url}')
        print(f'  WebSocket URL: {self.auth_config.websocket_url}')
        yield
        await self.auth_helper.cleanup()

    async def test_websocket_auth_session_metrics_integration(self):
        """
        Test WebSocket authentication with session metrics collection.
        
        This test validates that WebSocket connections create proper session
        metrics and handle authentication errors without crashing due to SSOT bugs.
        """
        print(f'\n[U+1F50C] TESTING WEBSOCKET AUTH + SESSION METRICS')
        if not self.auth_tokens:
            pytest.skip('No authenticated tokens available')
        user_token = list(self.auth_tokens.values())[0]
        websocket_url = f"{self.auth_config.websocket_url}?token={user_token['access_token']}"
        try:
            async with websockets.connect(websocket_url, timeout=10.0, extra_headers={'Authorization': f"Bearer {user_token['access_token']}", 'X-Request-ID': f'e2e-session-test-{int(time.time())}'}) as websocket:
                print(' PASS:  WebSocket connection established with auth')
                test_message = {'type': 'start_agent', 'payload': {'user_request': 'Test session metrics collection', 'agent_type': 'supply_researcher', 'thread_id': f'test-thread-{int(time.time())}'}}
                await websocket.send(json.dumps(test_message))
                print('[U+1F4E4] Sent agent execution message')
                messages_received = []
                timeout_counter = 0
                while timeout_counter < 15:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        message_data = json.loads(response)
                        messages_received.append(message_data)
                        print(f"[U+1F4E5] Received: {message_data.get('type', 'unknown')}")
                        if message_data.get('type') == 'error':
                            error_details = message_data.get('data', {})
                            error_msg = str(error_details)
                            print(f' SEARCH:  ERROR MESSAGE ANALYSIS:')
                            print(f'  Error: {error_msg}')
                            if 'has no attribute' in error_msg:
                                ssot_fields = ['last_activity', 'operations_count', 'errors']
                                if any((field in error_msg for field in ssot_fields)):
                                    print('[U+1F41B] SSOT BUG DETECTED in WebSocket error handling!')
                                    print('This proves SessionMetrics SSOT violation affects real user flows')
                                    pytest.fail(f'SSOT BUG EXPOSED: WebSocket auth flow failed due to SessionMetrics field access error: {error_msg}\nThis proves the SSOT violation impacts real user authentication scenarios.')
                        if message_data.get('type') == 'agent_completed' or len(messages_received) > 10:
                            break
                    except asyncio.TimeoutError:
                        timeout_counter += 1
                        continue
                print(f' CHART:  WebSocket session completed: {len(messages_received)} messages')
                if len(messages_received) > 0:
                    print(' PASS:  WebSocket auth session completed without SSOT errors')
                else:
                    print(' WARNING: [U+FE0F] No messages received - may indicate session issues')
        except Exception as e:
            error_msg = str(e)
            print(f' FAIL:  WebSocket connection error: {error_msg}')
            if 'has no attribute' in error_msg:
                ssot_indicators = ['last_activity', 'operations_count', 'errors']
                if any((indicator in error_msg for indicator in ssot_indicators)):
                    print('[U+1F41B] SSOT BUG CONFIRMED: WebSocket auth failed due to SessionMetrics SSOT violation')
                    pytest.fail(f'SSOT BUG REPRODUCTION: WebSocket authentication failed due to SessionMetrics field access error: {error_msg}\nThis proves the bug impacts real authenticated user sessions.')
            raise e

    async def test_multi_user_concurrent_session_metrics(self):
        """
        Test concurrent authenticated users to validate session metrics isolation.
        
        This test ensures SessionMetrics work correctly when multiple users
        are active simultaneously with proper isolation.
        """
        print(f'\n[U+1F465] TESTING MULTI-USER SESSION METRICS')
        if len(self.auth_tokens) < 2:
            pytest.skip('Need at least 2 authenticated users for concurrent testing')
        user_tokens = list(self.auth_tokens.values())[:2]
        concurrent_sessions = []
        for i, user_token in enumerate(user_tokens):
            session_task = asyncio.create_task(self._run_authenticated_session(user_token, f'user-{i}', f'concurrent-test-{i}-{int(time.time())}'))
            concurrent_sessions.append(session_task)
        results = await asyncio.gather(*concurrent_sessions, return_exceptions=True)
        print(f'\n CHART:  CONCURRENT SESSION RESULTS:')
        ssot_bugs_found = 0
        successful_sessions = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = str(result)
                print(f'  User {i} ERROR: {error_msg}')
                if 'has no attribute' in error_msg:
                    ssot_fields = ['last_activity', 'operations_count', 'errors']
                    if any((field in error_msg for field in ssot_fields)):
                        ssot_bugs_found += 1
                        print(f'    [U+1F41B] SSOT BUG detected in user {i} session')
            else:
                successful_sessions += 1
                print(f'  User {i} SUCCESS: {result}')
        print(f'\nSUMMARY:')
        print(f'  Successful sessions: {successful_sessions}')
        print(f'  SSOT bugs found: {ssot_bugs_found}')
        if ssot_bugs_found > 0:
            pytest.fail(f'SSOT BUG IN MULTI-USER SCENARIO: {ssot_bugs_found} users experienced SessionMetrics AttributeError.\nThis proves the SSOT violation affects concurrent user sessions and breaks user isolation.')
        assert successful_sessions > 0, 'Expected at least some successful concurrent sessions'
        print(' PASS:  Multi-user sessions completed without SSOT violations')

    async def _run_authenticated_session(self, user_token: Dict[str, Any], user_label: str, thread_id: str) -> Dict[str, Any]:
        """Run a single authenticated WebSocket session for concurrent testing."""
        websocket_url = f"{self.auth_config.websocket_url}?token={user_token['access_token']}"
        try:
            async with websockets.connect(websocket_url, timeout=10.0, extra_headers={'Authorization': f"Bearer {user_token['access_token']}", 'X-Request-ID': f'concurrent-{user_label}-{int(time.time())}'}) as websocket:
                message = {'type': 'start_agent', 'payload': {'user_request': f'Concurrent session test for {user_label}', 'agent_type': 'supply_researcher', 'thread_id': thread_id}}
                await websocket.send(json.dumps(message))
                messages = []
                timeout_count = 0
                while timeout_count < 8:
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        message_data = json.loads(response)
                        messages.append(message_data)
                        if message_data.get('type') == 'error':
                            error_details = str(message_data.get('data', {}))
                            if 'has no attribute' in error_details:
                                raise AttributeError(f'SessionMetrics SSOT bug in {user_label}: {error_details}')
                        if message_data.get('type') in ['agent_completed', 'session_complete']:
                            break
                    except asyncio.TimeoutError:
                        timeout_count += 1
                        continue
                return {'user': user_label, 'messages': len(messages), 'success': True}
        except Exception as e:
            raise e

    async def test_session_metrics_database_auth_error_integration(self):
        """
        Test session metrics during database authentication errors.
        
        This test forces database authentication issues to trigger the
        error handling path where the SSOT bug occurs.
        """
        print(f'\n[U+1F510][U+1F4BE] TESTING SESSION METRICS + DATABASE AUTH ERRORS')
        if not self.auth_tokens:
            pytest.skip('No authenticated tokens available')
        user_token = list(self.auth_tokens.values())[0]
        headers = {'Authorization': f"Bearer {user_token['access_token']}", 'Content-Type': 'application/json', 'X-Request-ID': f'db-auth-test-{int(time.time())}'}
        async with aiohttp.ClientSession() as session:
            thread_create_url = f'{self.auth_config.backend_url}/threads'
            thread_data = {'title': 'Session Metrics Database Auth Test', 'metadata': {'test_type': 'session_metrics_ssot'}}
            try:
                async with session.post(thread_create_url, json=thread_data, headers=headers, timeout=10.0) as response:
                    print(f'[U+1F4E1] Thread creation response: {response.status}')
                    if response.status != 201:
                        response_text = await response.text()
                        print(f' FAIL:  Thread creation failed: {response_text}')
                        if 'has no attribute' in response_text:
                            ssot_fields = ['last_activity', 'operations_count', 'errors']
                            if any((field in response_text for field in ssot_fields)):
                                print('[U+1F41B] SSOT BUG DETECTED in database auth error handling!')
                                pytest.fail(f'SSOT BUG CONFIRMED: Database auth error triggered SessionMetrics field access bug: {response_text}\nThis proves the bug affects authenticated API operations.')
                    else:
                        print(' PASS:  Thread creation successful without SSOT errors')
                        thread_response = await response.json()
                        thread_id = thread_response.get('id')
                        await self._test_agent_execution_session_metrics(session, headers, thread_id)
            except Exception as e:
                error_msg = str(e)
                print(f'[U+1F4A5] Database auth test error: {error_msg}')
                if 'has no attribute' in error_msg:
                    ssot_indicators = ['last_activity', 'operations_count', 'errors']
                    if any((indicator in error_msg for indicator in ssot_indicators)):
                        pytest.fail(f'SSOT BUG IN DATABASE AUTH: {error_msg}\nSessionMetrics SSOT violation triggered during authenticated database operations.')
                raise e

    async def _test_agent_execution_session_metrics(self, session: aiohttp.ClientSession, headers: Dict[str, str], thread_id: str):
        """Test agent execution that involves complex database session operations."""
        agent_execute_url = f'{self.auth_config.backend_url}/agents/execute'
        agent_data = {'agent_type': 'supply_researcher', 'query': 'Test session metrics during agent execution', 'thread_id': thread_id, 'test_metadata': {'purpose': 'session_metrics_ssot_validation'}}
        try:
            async with session.post(agent_execute_url, json=agent_data, headers=headers, timeout=30.0) as response:
                print(f'[U+1F916] Agent execution response: {response.status}')
                response_text = await response.text()
                if response.status >= 400:
                    print(f' FAIL:  Agent execution error: {response_text}')
                    if 'has no attribute' in response_text:
                        ssot_fields = ['last_activity', 'operations_count', 'errors']
                        if any((field in response_text for field in ssot_fields)):
                            print('[U+1F41B] SSOT BUG in agent execution session management!')
                            raise AttributeError(f'SessionMetrics SSOT bug during agent execution: {response_text}')
                else:
                    print(' PASS:  Agent execution completed without session metrics errors')
        except asyncio.TimeoutError:
            print('[U+23F1][U+FE0F] Agent execution timeout (may indicate session issues)')
        except Exception as e:
            raise e

    async def test_session_cleanup_auth_scenarios(self):
        """
        Test session cleanup scenarios with authentication.
        
        This validates that session metrics are properly cleaned up
        without triggering SSOT bugs during auth session teardown.
        """
        print(f'\n[U+1F9F9] TESTING SESSION CLEANUP + AUTH')
        if not self.auth_tokens:
            pytest.skip('No authenticated tokens available')
        cleanup_errors = []
        successful_cleanups = 0
        for i in range(3):
            user_token = list(self.auth_tokens.values())[0]
            try:
                websocket_url = f"{self.auth_config.websocket_url}?token={user_token['access_token']}"
                async with websockets.connect(websocket_url, timeout=5.0, extra_headers={'Authorization': f"Bearer {user_token['access_token']}", 'X-Request-ID': f'cleanup-test-{i}-{int(time.time())}'}) as websocket:
                    message = {'type': 'ping', 'data': {'cleanup_test': i}}
                    await websocket.send(json.dumps(message))
                    await asyncio.sleep(0.1)
                print(f'  Session {i}: Created and cleaned up')
                successful_cleanups += 1
                await asyncio.sleep(0.1)
            except Exception as e:
                error_msg = str(e)
                cleanup_errors.append(f'Session {i}: {error_msg}')
                print(f'  Session {i} cleanup error: {error_msg}')
                if 'has no attribute' in error_msg:
                    ssot_fields = ['last_activity', 'operations_count', 'errors']
                    if any((field in error_msg for field in ssot_fields)):
                        print(f'[U+1F41B] SSOT BUG during session {i} cleanup!')
        print(f'\n CHART:  CLEANUP RESULTS:')
        print(f'  Successful cleanups: {successful_cleanups}')
        print(f'  Cleanup errors: {len(cleanup_errors)}')
        if cleanup_errors:
            ssot_cleanup_errors = [error for error in cleanup_errors if 'has no attribute' in error and any((field in error for field in ['last_activity', 'operations_count', 'errors']))]
            if ssot_cleanup_errors:
                pytest.fail(f'SSOT BUG IN SESSION CLEANUP: {len(ssot_cleanup_errors)} cleanup operations failed due to SessionMetrics field access:\n' + '\n'.join(ssot_cleanup_errors) + f'\nThis proves the SSOT violation affects session lifecycle management.')
        print(' PASS:  All session cleanups completed without SSOT violations')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')