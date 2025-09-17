"
E2E Tests for ConnectionHandler Issues in GCP Staging Environment.

These tests are specifically designed to catch the ConnectionHandler issues identified
in the Five WHYs analysis for user 105945141827451681156.

CRITICAL: These tests MUST fail in the current broken state to validate issue detection.

Business Value:
- Validates WebSocket connection handling in GCP Cloud Run environment
- Catches silent failure patterns in ConnectionHandler operations  
- Ensures proper resource cleanup during connection churning
- Prevents golden path chat failures for authenticated users

Test Strategy:
- All tests use REAL authentication via e2e_auth_helper.py
- Tests target GCP staging environment behavior specifically
- Focus on detecting silent failures and resource accumulation
- Use real WebSocket connections (no mocks in E2E)

Expected Test Behavior:
- CURRENT STATE: Most tests FAIL due to identified issues
- AFTER FIX: All tests PASS with proper ConnectionHandler behavior
"
import asyncio
import json
import logging
import pytest
import time
import websockets
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import patch, MagicMock
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthHelper
from test_framework.ssot.base_test_case import SSotBaseTestCase
from shared.isolated_environment import get_env
logger = logging.getLogger(__name__)
GCP_TEST_CONFIG = {'websocket_url': 'wss://netra-backend-staging-xyz.run.app/ws', 'connection_timeout': 15.0, 'test_user_id': '105945141827451681156', 'max_connections_test': 25, 'rapid_connect_delay': 0.1}

class WebSocketConnectionHandlerCloudTests(SSotBaseTestCase):
    "
    CRITICAL E2E Tests for ConnectionHandler issues in GCP Cloud environment.
    
    These tests target the specific failures identified in the Five WHYs analysis:
    1. Silent failure pattern where handler returns True but sends no response
    2. WebSocket state detection failures in GCP Cloud Run proxy environment
    3. Resource accumulation during connection churning
    4. Truncated error logging that hides root causes
"

    def setup_method(self):
        "Set up each test with proper environment and auth helper.
        super().setup_method()
        self.env = get_env()
        self.test_environment = self.env.get('TEST_ENV', 'staging')
        logger.info(f'Setting up ConnectionHandler cloud tests for environment: {self.test_environment}')
        self.auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
        self.active_connections: List[websockets.ServerConnection] = []
        self.connection_logs: List[Dict[str, Any]] = []
        staging_ws_url = self.env.get('STAGING_WEBSOCKET_URL')
        if staging_ws_url:
            GCP_TEST_CONFIG['websocket_url'] = staging_ws_url

    def teardown_method(self):
        ""Clean up connections and reset state after each test.
        if self.active_connections:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                for ws in self.active_connections:
                    if not ws.closed:
                        loop.run_until_complete(ws.close())
            except Exception as e:
                logger.warning(f'Error closing connections in teardown: {e}')
            finally:
                loop.close()
        self.active_connections.clear()
        self.connection_logs.clear()
        super().teardown_method()

    async def _connect_with_auth(self, timeout: Optional[float]=None) -> websockets.ServerConnection:
    ""
        Create authenticated WebSocket connection with proper error handling.
        
        Args:
            timeout: Connection timeout (uses config default if not provided)
            
        Returns:
            Authenticated WebSocket connection
            
        Raises:
            TimeoutError: If connection times out
            ConnectionError: If authentication or connection fails
        
        timeout = timeout or GCP_TEST_CONFIG['connection_timeout']
        try:
            websocket = await self.auth_helper.connect_authenticated_websocket(timeout=timeout)
            self.active_connections.append(websocket)
            self.connection_logs.append({'action': 'connect', 'timestamp': datetime.now(timezone.utc).isoformat(), 'success': True, 'timeout': timeout}
            return websocket
        except Exception as e:
            self.connection_logs.append({'action': 'connect', 'timestamp': datetime.now(timezone.utc).isoformat(), 'success': False, 'error': str(e), 'timeout': timeout}
            raise ConnectionError(f'Failed to create authenticated WebSocket connection: {e}')

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_connectionhandler_fails_with_invalid_websocket_state_in_gcp(self):
        "
        CRITICAL TEST: ConnectionHandler Silent Failure Detection
        
        This test MUST fail in current state due to silent failure pattern.
        
        Tests that ConnectionHandler properly fails when is_websocket_connected() 
        returns False in GCP environment, instead of silently returning True.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - Handler returns True but doesn't send response
        - AFTER FIX: PASS - Handler returns False when connection check fails
"
        logger.info('[U+1F9EA] Testing ConnectionHandler silent failure detection in GCP staging')
        websocket = await self._connect_with_auth()
        try:
            from netra_backend.app.websocket_core.handlers import ConnectionHandler
            from netra_backend.app.websocket_core.utils import is_websocket_connected
        except ImportError as e:
            pytest.skip(f'Cannot import WebSocket modules for testing: {e}')
        test_message = {'type': 'agent_execution', 'agent_name': 'test_agent', 'message': 'Test message requiring response', 'request_id': f'test-{int(time.time())}', 'user_id': GCP_TEST_CONFIG['test_user_id']}
        with patch('netra_backend.app.websocket_core.utils.is_websocket_connected') as mock_connected:
            mock_connected.return_value = False
            handler = ConnectionHandler()
            try:
                result = await handler.handle_message(websocket=websocket, user_id=GCP_TEST_CONFIG['test_user_id'], message=test_message)
                assert result is False, 'ConnectionHandler MUST return False when websocket connection check fails. Current bug: Handler returns True even when is_websocket_connected() returns False. This creates silent failures where users get no responses.'
                logger.info(' PASS:  ConnectionHandler correctly returns False for failed connection checks')
            except AssertionError:
                logger.error(' FAIL:  CRITICAL BUG DETECTED: ConnectionHandler returns True despite connection failure')
                logger.error('This causes silent failures where users receive no responses from agents')
                raise
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
            pytest.fail(f'ConnectionHandler sent response despite connection check failure: {response}. This indicates the handler is not respecting is_websocket_connected() result.')
        except asyncio.TimeoutError:
            logger.info(' PASS:  Confirmed: No response sent when connection check fails')

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_gcp_cloud_run_websocket_state_detection(self):
    ""
        Tests WebSocket state detection in GCP Cloud Run proxy environment.
        
        CRITICAL: This test targets the core issue where GCP proxy layer
        doesn't expose expected WebSocket state attributes.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - State detection fails in cloud environment
        - AFTER FIX: PASS - Proper state detection using cloud-specific logic
        
        logger.info('[U+1F9EA] Testing GCP Cloud Run WebSocket state detection')
        websocket = await self._connect_with_auth()
        try:
            from netra_backend.app.websocket_core.utils import is_websocket_connected
        except ImportError as e:
            pytest.skip(f'Cannot import WebSocket utilities for testing: {e}')
        ping_message = json.dumps({'type': 'ping', 'timestamp': datetime.now(timezone.utc).isoformat()}
        await websocket.send(ping_message)
        try:
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            logger.info(f'WebSocket ping response received: {response[:100]}...')
            connection_works_from_client = True
        except asyncio.TimeoutError:
            logger.warning('No response to WebSocket ping - connection may be problematic')
            connection_works_from_client = False
        connection_detected = is_websocket_connected(websocket)
        logger.info(f'WebSocket state detection results:')
        logger.info(f'  - Client can send/receive: {connection_works_from_client}')
        logger.info(f'  - is_websocket_connected(): {connection_detected}')
        logger.info(f  - WebSocket state: {getattr(websocket, 'state', 'NO_STATE_ATTR')})"
        logger.info(f'  - WebSocket closed: {websocket.closed}')
        if connection_works_from_client:
            assert connection_detected, f'CRITICAL BUG: is_websocket_connected() returns False but connection actually works. This causes ConnectionHandler to skip responses in GCP Cloud Run environment. Client connectivity: {connection_works_from_client}, State detection: {connection_detected}'
            logger.info(' PASS:  WebSocket state detection correctly identifies working connection')
        else:
            assert not connection_detected, f"WebSocket state detection inconsistency: Connection doesn't work but detected as connected. Client connectivity: {connection_works_from_client}, State detection: {connection_detected}
            logger.info(' PASS:  WebSocket state detection correctly identifies non-working connection')
        ws_attributes = {}
        for attr in ['state', 'client_state', '_receive', 'closed', 'close_code']:
            try:
                ws_attributes[attr] = getattr(websocket, attr, 'NOT_FOUND')
            except Exception as e:
                ws_attributes[attr] = f'ERROR_ACCESSING: {e}'
        logger.info(f'WebSocket attributes in GCP Cloud Run environment: {ws_attributes}')
        self.connection_logs.append({'test': 'gcp_state_detection', 'client_connectivity': connection_works_from_client, 'state_detection': connection_detected, 'websocket_attributes': ws_attributes, 'environment': self.test_environment}

    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.slow
    async def test_user_connection_churning_resource_cleanup(self):
        
        Tests specific user (105945141827451681156) pattern of rapid connections.
        
        Validates that connection churning doesn't cause resource accumulation
        or connection state detection failures.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - Resource accumulation causes failures after 20 connections  
        - AFTER FIX: PASS - Proper cleanup prevents resource accumulation
""
        logger.info('[U+1F9EA] Testing connection churning and resource cleanup')
        logger.info(fSimulating rapid connections for user: {GCP_TEST_CONFIG['test_user_id']})
        connection_results = []
        successful_connections = 0
        failed_connections = 0
        for cycle in range(GCP_TEST_CONFIG['max_connections_test']:
            cycle_start = time.time()
            try:
                websocket = await self._connect_with_auth(timeout=10.0)
                test_message = json.dumps({'type': 'ping', 'cycle': cycle, 'user_id': GCP_TEST_CONFIG['test_user_id'], 'timestamp': datetime.now(timezone.utc).isoformat()}
                await websocket.send(test_message)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    message_success = True
                except asyncio.TimeoutError:
                    message_success = False
                await websocket.close()
                if websocket in self.active_connections:
                    self.active_connections.remove(websocket)
                successful_connections += 1
                cycle_time = time.time() - cycle_start
                connection_results.append({'cycle': cycle, 'success': True, 'message_success': message_success, 'cycle_time': cycle_time}
                logger.info(f   PASS:  Cycle {cycle + 1}/{GCP_TEST_CONFIG['max_connections_test']}: Connection OK, Message: {('OK' if message_success else 'TIMEOUT')}, Time: {cycle_time:.2f}s)
            except Exception as e:
                failed_connections += 1
                cycle_time = time.time() - cycle_start
                connection_results.append({'cycle': cycle, 'success': False, 'error': str(e), 'cycle_time': cycle_time}
                logger.error(f"   FAIL:  Cycle {cycle + 1}/{GCP_TEST_CONFIG['max_connections_test']}: Failed - {e}, Time: {cycle_time:.2f}s)
                if 'maximum number of WebSocket managers' in str(e) or '20' in str(e):
                    logger.error(' ALERT:  CRITICAL BUG DETECTED: WebSocket manager resource limit reached')
                    logger.error('This indicates resource accumulation and improper cleanup')
                    break
            await asyncio.sleep(GCP_TEST_CONFIG['rapid_connect_delay']
        success_rate = successful_connections / len(connection_results) if connection_results else 0
        avg_time = sum((r.get('cycle_time', 0) for r in connection_results)) / len(connection_results) if connection_results else 0
        logger.info(f'Connection churning test results:')
        logger.info(f'  - Total cycles: {len(connection_results)}')
        logger.info(f'  - Successful connections: {successful_connections}')
        logger.info(f'  - Failed connections: {failed_connections}')
        logger.info(f'  - Success rate: {success_rate:.1%}')
        logger.info(f'  - Average cycle time: {avg_time:.2f}s')
        completed_cycles = len(connection_results)
        assert completed_cycles >= 20, f'Connection churning test should complete at least 20 cycles, but only completed {completed_cycles}. This indicates resource limits are being hit.'
        assert success_rate >= 0.8, f'Connection churning success rate too low: {success_rate:.1%}. Expected at least 80% success rate. This indicates resource accumulation or connection state management issues.'
        resource_errors = [r for r in connection_results if 'error' in r and ('maximum' in r['error'].lower() or '20' in r['error']]
        assert len(resource_errors) == 0, f'Found {len(resource_errors)} resource limit errors during connection churning. This indicates WebSocket manager cleanup is not working properly. Sample errors: {resource_errors[:3]}'
        logger.info(' PASS:  Connection churning test passed - proper resource management')

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_exception_logging_captures_full_details(self):
        "
        CRITICAL: Tests that exception logging captures complete error information.
        
        This test MUST fail in current state due to truncated error messages.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - Error messages truncated to empty string
        - AFTER FIX: PASS - Full exception type, message, and traceback captured
"
        logger.info('[U+1F9EA] Testing exception logging completeness in ConnectionHandler')
        websocket = await self._connect_with_auth()
        try:
            from netra_backend.app.websocket_core.handlers import ConnectionHandler
        except ImportError as e:
            pytest.skip(f'Cannot import ConnectionHandler for testing: {e}')
        exception_test_cases = [('asyncio.CancelledError', lambda: asyncio.CancelledError()), ('RuntimeError', lambda: RuntimeError('')), ('ValueError', lambda: ValueError(None)), ('TypeError', lambda: TypeError())]
        handler = ConnectionHandler()
        captured_logs = []

        def capture_log(message, *args, **kwargs):
            captured_logs.append(message)
            logger.error(message, *args, **kwargs)
        for exception_name, exception_creator in exception_test_cases:
            logger.info(f'Testing exception logging for: {exception_name}')
            test_exception = exception_creator()
            original_send_json = websocket.send_json if hasattr(websocket, 'send_json') else None

            def mock_send_json(*args, **kwargs):
                raise test_exception
            with patch.object(websocket, 'send_json', side_effect=mock_send_json):
                with patch('netra_backend.app.websocket_core.handlers.logger.error', side_effect=capture_log):
                    test_message = {'type': 'test_message', 'content': f'Testing {exception_name} logging'}
                    result = await handler.handle_message(websocket=websocket, user_id=GCP_TEST_CONFIG['test_user_id'], message=test_message)
                    assert result is False, f'Handler should return False on {exception_name}'
            relevant_logs = [log for log in captured_logs if GCP_TEST_CONFIG['test_user_id'] in str(log)]
            assert len(relevant_logs) > 0, f'No error log found for {exception_name} exception. This indicates exception logging is not working.'
            latest_log = relevant_logs[-1]
            log_str = str(latest_log)
            expected_empty_pattern = f"Error in ConnectionHandler for user {GCP_TEST_CONFIG['test_user_id']}: 
            assert log_str != expected_empty_pattern, fCRITICAL BUG: Exception logging truncated for {exception_name}. Log message: '{log_str}'. Expected more details than just user ID and empty string. Original exception: {test_exception}
            exception_type_name = type(test_exception).__name__
            assert exception_type_name in log_str, fException logging should include exception type '{exception_type_name}' but log is: '{log_str}'
            logger.info(f' PASS:  Exception logging test passed for {exception_name}: {log_str[:100]}...')
            captured_logs.clear()
        logger.info(' PASS:  All exception logging tests passed - full error details captured')

    @pytest.mark.e2e
    @pytest.mark.staging
    async def test_authenticated_user_complete_chat_flow_gcp_staging(self):
        ""
        MISSION CRITICAL: Tests complete chat flow for authenticated users in GCP staging.
        
        Uses real authentication (JWT/OAuth) to test the golden path that's currently broken.
        
        Expected Behavior:
        - CURRENT STATE: FAIL - User gets no responses due to silent failure
        - AFTER FIX: PASS - Complete chat flow works end-to-end

        logger.info('[U+1F9EA] Testing complete authenticated chat flow in GCP staging')
        logger.info(f"User ID: {GCP_TEST_CONFIG['test_user_id']})
        websocket = await self._connect_with_auth(timeout=20.0)
        agent_request = {'type': 'agent_execution', 'agent_name': 'data_analysis_agent', 'message': 'Analyze the current system status and provide recommendations', 'request_id': f'e2e-test-{int(time.time())}', 'user_id': GCP_TEST_CONFIG['test_user_id'], 'thread_id': f'thread-{int(time.time())}', 'metadata': {'test_mode': True, 'e2e_test': True, 'environment': 'staging'}}
        logger.info(fSending agent execution request: {agent_request['agent_name']}")"
        await websocket.send(json.dumps(agent_request))
        responses_received = []
        websocket_events_received = []
        timeout_seconds = 30.0
        start_time = time.time()
        try:
            while time.time() - start_time < timeout_seconds:
                try:
                    response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    try:
                        response_data = json.loads(response_text)
                        responses_received.append(response_data)
                        response_type = response_data.get('type', 'unknown')
                        if response_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed', 'agent_response']:
                            websocket_events_received.append(response_type)
                            logger.info(f'  [U+1F4E1] Received WebSocket event: {response_type}')
                        if response_type == 'agent_completed' or response_type == 'agent_response':
                            logger.info('   PASS:  Received final agent response')
                            break
                    except json.JSONDecodeError:
                        logger.warning(f'   WARNING: [U+FE0F] Received non-JSON response: {response_text[:100]}...')
                        responses_received.append({'raw': response_text}
                except asyncio.TimeoutError:
                    logger.info('  [U+23F3] Waiting for more responses...')
                    continue
        except Exception as e:
            logger.error(f'Error during response waiting: {e}')
        total_responses = len(responses_received)
        unique_event_types = set(websocket_events_received)
        logger.info(f'Chat flow test results:')
        logger.info(f'  - Total responses received: {total_responses}')
        logger.info(f'  - WebSocket events received: {sorted(unique_event_types)}')
        logger.info(f'  - Test duration: {time.time() - start_time:.1f}s')
        assert total_responses > 0, f'CRITICAL BUG: No responses received from agent execution request. This indicates ConnectionHandler silent failure where request is processed but no responses are sent back to the user. Golden path is broken.'
        expected_events = {'agent_started', 'agent_completed'}
        received_events = set(websocket_events_received)
        missing_events = expected_events - received_events
        assert len(missing_events) == 0, f'Missing critical WebSocket events: {missing_events}. Received: {received_events}. This indicates WebSocket notification system is not working properly.'
        actual_duration = time.time() - start_time
        assert actual_duration < timeout_seconds * 0.9, f'Chat flow took too long: {actual_duration:.1f}s (timeout: {timeout_seconds}s). This may indicate connection handling delays or processing issues.'
        final_responses = [r for r in responses_received if r.get('type') in ['agent_completed', 'agent_response']]
        assert len(final_responses) > 0, f"No final completion response received. Agent execution may have failed or ConnectionHandler dropped the response. All responses: {[r.get('type') for r in responses_received]}"
        logger.info(' PASS:  Complete chat flow test passed - golden path working')
        self.connection_logs.append({'test': 'complete_chat_flow', 'total_responses': total_responses, 'websocket_events': sorted(unique_event_types), 'duration': actual_duration, 'success': True}
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')