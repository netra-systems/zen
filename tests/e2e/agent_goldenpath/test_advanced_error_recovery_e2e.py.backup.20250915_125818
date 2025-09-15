"""
E2E Tests for Advanced Error Recovery Scenarios - Golden Path Resilience

MISSION CRITICAL: Tests advanced error recovery scenarios to validate system resilience
and graceful degradation in the Golden Path agent workflow. These tests ensure that
various failure modes are handled properly without breaking the user experience.

Business Value Justification (BVJ):
- Segment: All Users (System Reliability affects all segments)
- Business Goal: Platform Reliability & User Trust through Robust Error Handling
- Value Impact: Validates system resilience critical for maintaining user confidence
- Strategic Impact: Poor error recovery = user frustration = churn = $500K+ ARR loss

Test Strategy:
- REAL SERVICES: Staging GCP Cloud Run environment only (NO Docker)
- REALISTIC FAILURES: Simulate real-world failure scenarios (timeouts, invalid requests, etc.)
- GRACEFUL DEGRADATION: System should handle errors without complete failure
- USER EXPERIENCE: Error messages should be helpful and recovery should be seamless
- BUSINESS CONTINUITY: Critical functionality should remain available during errors

CRITICAL: These tests must demonstrate actual error scenarios with proper recovery.
No mocking of error conditions that don't represent real-world failures.

GitHub Issue: #861 Agent Golden Path Messages Test Creation - Gap Area 2
Coverage Target: Complex error recovery paths (identified gap)
"""
import asyncio
import pytest
import time
import json
import logging
import websockets
import ssl
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
import uuid
import httpx
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from tests.e2e.staging_config import get_staging_config, is_staging_available
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.ssot.websocket_test_utility import WebSocketTestHelper

@pytest.mark.e2e
@pytest.mark.gcp_staging
@pytest.mark.error_recovery
@pytest.mark.mission_critical
class TestAdvancedErrorRecoveryE2E(SSotAsyncTestCase):
    """
    E2E tests for validating advanced error recovery scenarios in staging GCP.

    Tests system resilience, graceful degradation, and error recovery
    under various realistic failure conditions.
    """

    @classmethod
    def setup_class(cls):
        """Setup staging environment for error recovery testing."""
        cls.staging_config = get_staging_config()
        cls.logger = logging.getLogger(__name__)
        if not is_staging_available():
            pytest.skip('Staging environment not available')
        cls.auth_helper = E2EAuthHelper(environment='staging')
        cls.websocket_helper = WebSocketTestHelper(base_url=cls.staging_config.urls.websocket_url, environment='staging')
        cls.CRITICAL_EVENTS = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        cls.logger.info(f'Advanced error recovery E2E tests initialized for staging')

    def setup_method(self, method):
        """Setup for each test method."""
        super().setup_method(method)
        self.error_test_session = f'error_recovery_{int(time.time())}'
        self.thread_id = f'error_test_{self.error_test_session}'
        self.run_id = f'run_{self.thread_id}'
        self.test_user_id = f'error_test_user_{int(time.time())}'
        self.test_user_email = f'error_test_{int(time.time())}@netra-testing.ai'
        self.access_token = self.__class__.auth_helper.create_test_jwt_token(user_id=self.test_user_id, email=self.test_user_email, exp_minutes=60)
        self.logger.info(f'Error recovery test setup - session: {self.error_test_session}')

    async def _establish_websocket_connection(self, headers_override: Dict[str, str]=None) -> websockets.ServerConnection:
        """Establish WebSocket connection with optional header overrides for error testing."""
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        headers = {'Authorization': f'Bearer {self.access_token}', 'X-Environment': 'staging', 'X-Test-Suite': 'advanced-error-recovery', 'X-Session-Id': self.error_test_session}
        if headers_override:
            headers.update(headers_override)
        websocket = await asyncio.wait_for(websockets.connect(self.__class__.staging_config.urls.websocket_url, additional_headers=headers, ssl=ssl_context, ping_interval=30, ping_timeout=10), timeout=20.0)
        return websocket

    async def _send_request_and_collect_events(self, websocket, message_data: Dict[str, Any], timeout: float=60.0) -> Dict[str, Any]:
        """Send request and collect events with comprehensive error handling."""
        start_time = time.time()
        try:
            await websocket.send(json.dumps(message_data))
            message_sent_time = time.time()
            events = []
            event_types = set()
            error_events = []
            success = False
            while time.time() - message_sent_time < timeout:
                try:
                    event_data = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    event = json.loads(event_data)
                    events.append(event)
                    event_type = event.get('type', 'unknown')
                    event_types.add(event_type)
                    if 'error' in event_type.lower() or event.get('error'):
                        error_events.append(event)
                    if event_type == 'agent_completed':
                        success = True
                        break
                    elif event_type in ['agent_error', 'fatal_error']:
                        break
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError as e:
                    error_events.append({'error': 'json_decode', 'details': str(e)})
                    continue
            total_time = time.time() - start_time
            return {'success': success, 'total_time': total_time, 'events': events, 'event_types': event_types, 'error_events': error_events, 'events_count': len(events), 'critical_events': event_types.intersection(self.__class__.CRITICAL_EVENTS)}
        except Exception as e:
            total_time = time.time() - start_time
            return {'success': False, 'total_time': total_time, 'events': [], 'event_types': set(), 'error_events': [{'error': 'exception', 'details': str(e)}], 'events_count': 0, 'critical_events': set(), 'exception': e}

    async def test_invalid_agent_type_error_recovery(self):
        """
        Test error recovery when requesting non-existent agent type.

        ERROR RECOVERY: System should gracefully handle invalid agent requests
        with helpful error messages and maintain connection stability.

        Scenario:
        1. Send request with invalid agent type
        2. Validate system returns appropriate error
        3. Verify connection remains stable
        4. Send valid follow-up request to confirm recovery
        5. Ensure no system instability from invalid request

        DIFFICULTY: Medium (25 minutes)
        REAL SERVICES: Yes - Invalid agent handling in staging
        STATUS: Should PASS - Graceful error handling essential for UX
        """
        self.logger.info('🚨 Testing invalid agent type error recovery')
        websocket = await self._establish_websocket_connection()
        try:
            invalid_request = {'type': 'agent_request', 'agent': 'nonexistent_quantum_ai_agent', 'message': 'Test invalid agent error recovery', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': self.test_user_id, 'context': {'error_test': 'invalid_agent_type', 'expected_error': True}}
            invalid_result = await self._send_request_and_collect_events(websocket, invalid_request, timeout=30.0)
            self.logger.info(f'📊 Invalid Agent Request Result:')
            self.logger.info(f"   Success: {invalid_result['success']}")
            self.logger.info(f"   Events: {invalid_result['events_count']}")
            self.logger.info(f"   Error Events: {len(invalid_result['error_events'])}")
            self.logger.info(f"   Time: {invalid_result['total_time']:.1f}s")
            assert not invalid_result['success'], f'Invalid agent request should not succeed'
            has_error_indication = len(invalid_result['error_events']) > 0 or 'error' in invalid_result['event_types'] or any(('error' in str(event).lower() for event in invalid_result['events']))
            assert has_error_indication, f"Should receive error indication for invalid agent type. Events: {invalid_result['event_types']}, Error events: {invalid_result['error_events']}"
            assert invalid_result['total_time'] < 15.0, f"Error response should be quick: {invalid_result['total_time']:.1f}s (max 15s)"
            await asyncio.sleep(2)
            recovery_request = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Recovery test after invalid agent request', 'thread_id': f'{self.thread_id}_recovery', 'run_id': f'{self.run_id}_recovery', 'user_id': self.test_user_id, 'context': {'error_test': 'recovery_after_invalid_agent', 'recovery_validation': True}}
            recovery_result = await self._send_request_and_collect_events(websocket, recovery_request, timeout=45.0)
            self.logger.info(f'📊 Recovery Request Result:')
            self.logger.info(f"   Success: {recovery_result['success']}")
            self.logger.info(f"   Events: {recovery_result['events_count']}")
            self.logger.info(f"   Critical Events: {len(recovery_result['critical_events'])}")
            assert recovery_result['success'], f"Recovery request should succeed after error. Error events: {recovery_result['error_events']}"
            assert len(recovery_result['critical_events']) >= 2, f"Recovery should deliver critical events. Got: {recovery_result['critical_events']}"
            assert recovery_result['events_count'] >= 3, f"Recovery should generate adequate events: {recovery_result['events_count']}"
            self.logger.info('✅ Invalid agent type error recovery validated')
        finally:
            await websocket.close()

    async def test_malformed_request_error_recovery(self):
        """
        Test error recovery when sending malformed WebSocket messages.

        ERROR RECOVERY: System should handle malformed JSON and invalid message
        structures without crashing or corrupting the connection.

        Scenario:
        1. Send malformed JSON message
        2. Send message with missing required fields
        3. Send message with invalid data types
        4. Verify system handles each gracefully
        5. Confirm connection remains functional after errors

        DIFFICULTY: High (30 minutes)
        REAL SERVICES: Yes - Message parsing resilience in staging
        STATUS: Should PASS - Robust message handling critical for reliability
        """
        self.logger.info('🔧 Testing malformed request error recovery')
        websocket = await self._establish_websocket_connection()
        try:
            error_scenarios = []
            self.logger.info('Testing malformed JSON handling...')
            try:
                malformed_json = '{"type": "agent_request", "incomplete": true, "missing_quote": test}'
                await websocket.send(malformed_json)
                try:
                    error_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    error_scenarios.append({'scenario': 'malformed_json', 'response_received': True, 'response': error_response})
                except asyncio.TimeoutError:
                    error_scenarios.append({'scenario': 'malformed_json', 'response_received': False, 'status': 'timeout'})
            except Exception as e:
                error_scenarios.append({'scenario': 'malformed_json', 'exception': str(e)})
            self.logger.info('Testing missing required fields...')
            missing_fields_request = {'type': 'agent_request', 'partial': True}
            missing_result = await self._send_request_and_collect_events(websocket, missing_fields_request, timeout=15.0)
            error_scenarios.append({'scenario': 'missing_fields', 'result': missing_result})
            self.logger.info('Testing invalid data types...')
            invalid_types_request = {'type': 'agent_request', 'agent': 12345, 'message': ['invalid', 'array'], 'user_id': {'invalid': 'object'}, 'thread_id': True, 'context': 'should_be_object'}
            invalid_types_result = await self._send_request_and_collect_events(websocket, invalid_types_request, timeout=15.0)
            error_scenarios.append({'scenario': 'invalid_types', 'result': invalid_types_result})
            self.logger.info(f'📊 Malformed Request Handling Results:')
            for scenario in error_scenarios:
                scenario_name = scenario['scenario']
                self.logger.info(f'   {scenario_name}: {scenario}')
            connection_stable = True
            stability_request = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Connection stability test after malformed requests', 'thread_id': f'{self.thread_id}_stability', 'run_id': f'{self.run_id}_stability', 'user_id': self.test_user_id, 'context': {'stability_test': True, 'after_malformed_requests': True}}
            stability_result = await self._send_request_and_collect_events(websocket, stability_request, timeout=45.0)
            self.logger.info(f'📊 Connection Stability Result:')
            self.logger.info(f"   Success: {stability_result['success']}")
            self.logger.info(f"   Events: {stability_result['events_count']}")
            self.logger.info(f"   Time: {stability_result['total_time']:.1f}s")
            assert stability_result['success'], f"Connection should remain stable after malformed requests. Stability test failed: {stability_result['error_events']}"
            assert len(stability_result['critical_events']) >= 2, f"Should receive critical events after error recovery. Got: {stability_result['critical_events']}"
            for scenario in error_scenarios[1:]:
                if 'result' in scenario:
                    result = scenario['result']
                    assert result['total_time'] < 20.0, f"Malformed request handling should be quick for {scenario['scenario']}: {result['total_time']:.1f}s"
            self.logger.info('✅ Malformed request error recovery validated')
        finally:
            await websocket.close()

    async def test_network_interruption_recovery(self):
        """
        Test recovery from simulated network interruptions.

        ERROR RECOVERY: System should handle connection drops and allow
        graceful reconnection without losing critical functionality.

        Scenario:
        1. Establish connection and start agent request
        2. Forcibly close connection during processing
        3. Reconnect and attempt to continue or restart
        4. Validate system handles interruption gracefully
        5. Ensure no data corruption or hanging processes

        DIFFICULTY: Very High (40 minutes)
        REAL SERVICES: Yes - Connection resilience testing in staging
        STATUS: Should PASS - Network resilience critical for production
        """
        self.logger.info('🌐 Testing network interruption recovery')
        websocket1 = await self._establish_websocket_connection()
        try:
            initial_request = {'type': 'agent_request', 'agent': 'apex_optimizer_agent', 'message': 'Please provide comprehensive AI cost optimization analysis with detailed market research and implementation recommendations. Include specific calculations and step-by-step guidance.', 'thread_id': self.thread_id, 'run_id': self.run_id, 'user_id': self.test_user_id, 'context': {'interruption_test': True, 'expects_lengthy_processing': True}}
            await websocket1.send(json.dumps(initial_request))
            initial_events = []
            interruption_time = 15.0
            start_time = time.time()
            while time.time() - start_time < interruption_time:
                try:
                    event_data = await asyncio.wait_for(websocket1.recv(), timeout=5.0)
                    event = json.loads(event_data)
                    initial_events.append(event)
                    if event.get('type') == 'agent_completed':
                        break
                except asyncio.TimeoutError:
                    continue
                except json.JSONDecodeError:
                    continue
            self.logger.info(f'Collected {len(initial_events)} events before interruption')
            await websocket1.close()
            await asyncio.sleep(2)
            self.logger.info('Connection interrupted - attempting recovery...')
            websocket2 = await self._establish_websocket_connection({'X-Connection-Type': 'recovery', 'X-Previous-Session': self.error_test_session})
            recovery_request = {'type': 'agent_request', 'agent': 'triage_agent', 'message': 'Recovery test: system should respond normally after interruption', 'thread_id': f'{self.thread_id}_recovery', 'run_id': f'{self.run_id}_recovery', 'user_id': self.test_user_id, 'context': {'recovery_after_interruption': True, 'connection_recovery_test': True}}
            recovery_result = await self._send_request_and_collect_events(websocket2, recovery_request, timeout=45.0)
            self.logger.info(f'📊 Network Interruption Recovery Results:')
            self.logger.info(f'   Initial Events: {len(initial_events)}')
            self.logger.info(f"   Recovery Success: {recovery_result['success']}")
            self.logger.info(f"   Recovery Events: {recovery_result['events_count']}")
            self.logger.info(f"   Recovery Time: {recovery_result['total_time']:.1f}s")
            assert recovery_result['success'], f"Recovery after network interruption should succeed. Error events: {recovery_result['error_events']}"
            assert len(recovery_result['critical_events']) >= 2, f"Recovery should deliver critical events. Got: {recovery_result['critical_events']}"
            assert recovery_result['total_time'] < 60.0, f"Recovery should not be excessively slow: {recovery_result['total_time']:.1f}s"
            recovery_events = recovery_result['events']
            has_meaningful_response = any((len(str(event.get('data', {}))) > 50 for event in recovery_events if event.get('type') == 'agent_completed'))
            assert has_meaningful_response, f'Recovery should deliver meaningful response content'
            self.logger.info('✅ Network interruption recovery validated')
        finally:
            try:
                await websocket2.close()
            except:
                pass

    async def test_concurrent_error_scenarios(self):
        """
        Test error handling under concurrent conditions.

        ERROR RECOVERY: System should handle multiple simultaneous errors
        without system-wide instability or cascading failures.

        Scenario:
        1. Create multiple concurrent connections
        2. Send mix of valid and invalid requests simultaneously
        3. Validate system handles errors independently
        4. Ensure no cross-contamination of error states
        5. Confirm overall system stability

        DIFFICULTY: Very High (45 minutes)
        REAL SERVICES: Yes - Concurrent error resilience in staging
        STATUS: Should PASS - Concurrent error handling critical for multi-user stability
        """
        self.logger.info('⚡ Testing concurrent error scenarios')
        concurrent_scenarios = [{'type': 'valid', 'request': {'type': 'agent_request', 'agent': 'triage_agent', 'message': f'Valid request 1: AI cost optimization help. ID: VALID1-{int(time.time())}', 'user_id': f'valid_user_1_{int(time.time())}'}}, {'type': 'invalid_agent', 'request': {'type': 'agent_request', 'agent': 'nonexistent_agent', 'message': f'Invalid agent request. ID: INVALID1-{int(time.time())}', 'user_id': f'invalid_user_1_{int(time.time())}'}}, {'type': 'valid', 'request': {'type': 'agent_request', 'agent': 'apex_optimizer_agent', 'message': f'Valid request 2: Comprehensive optimization analysis. ID: VALID2-{int(time.time())}', 'user_id': f'valid_user_2_{int(time.time())}'}}, {'type': 'missing_fields', 'request': {'type': 'agent_request', 'partial': True}}, {'type': 'valid', 'request': {'type': 'agent_request', 'agent': 'data_helper_agent', 'message': f'Valid request 3: Data analysis help. ID: VALID3-{int(time.time())}', 'user_id': f'valid_user_3_{int(time.time())}'}}]

        async def execute_concurrent_scenario(scenario_index: int, scenario: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a single concurrent scenario."""
            try:
                user_context = await self._create_isolated_user_context(scenario_index)
                headers = {'X-Scenario-Index': str(scenario_index), 'X-Scenario-Type': scenario['type']}
                websocket = await self._establish_websocket_connection(headers)
                request = scenario['request'].copy()
                if scenario['type'] != 'missing_fields':
                    request.update({'thread_id': f'concurrent_{scenario_index}_{int(time.time())}', 'run_id': f'run_concurrent_{scenario_index}_{int(time.time())}'})
                    if 'user_id' not in request:
                        request['user_id'] = user_context['user_id']
                result = await self._send_request_and_collect_events(websocket, request, timeout=30.0)
                await websocket.close()
                return {'scenario_index': scenario_index, 'scenario_type': scenario['type'], 'result': result, 'expected_success': scenario['type'] == 'valid'}
            except Exception as e:
                return {'scenario_index': scenario_index, 'scenario_type': scenario['type'], 'exception': str(e), 'expected_success': scenario['type'] == 'valid'}

        async def _create_isolated_user_context(self, user_index: int) -> Dict[str, Any]:
            """Create isolated user context for concurrent error testing."""
            user_context = {'user_id': f'concurrent_error_user_{user_index}_{int(time.time())}', 'email': f'concurrent_error_{user_index}_{int(time.time())}@netra-testing.ai'}
            user_context['access_token'] = self.__class__.auth_helper.create_test_jwt_token(user_id=user_context['user_id'], email=user_context['email'], exp_minutes=30)
            return user_context
        concurrent_tasks = [execute_concurrent_scenario(i, scenario) for i, scenario in enumerate(concurrent_scenarios)]
        start_time = time.time()
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        valid_scenarios = [r for r in results if isinstance(r, dict) and r.get('expected_success')]
        invalid_scenarios = [r for r in results if isinstance(r, dict) and (not r.get('expected_success'))]
        exception_scenarios = [r for r in results if isinstance(r, Exception)]
        self.logger.info(f'📊 Concurrent Error Scenarios Results:')
        self.logger.info(f'   Total Scenarios: {len(concurrent_scenarios)}')
        self.logger.info(f'   Valid Scenarios: {len(valid_scenarios)}')
        self.logger.info(f'   Invalid Scenarios: {len(invalid_scenarios)}')
        self.logger.info(f'   Exceptions: {len(exception_scenarios)}')
        self.logger.info(f'   Total Time: {total_time:.2f}s')
        valid_successes = [r for r in valid_scenarios if r.get('result', {}).get('success')]
        valid_success_rate = len(valid_successes) / len(valid_scenarios) if valid_scenarios else 0
        assert valid_success_rate >= 0.8, f'Valid requests should succeed despite concurrent errors. Success rate: {valid_success_rate:.1%} ({len(valid_successes)}/{len(valid_scenarios)})'
        for invalid_result in invalid_scenarios:
            if 'result' in invalid_result:
                result = invalid_result['result']
                assert not result.get('success'), f"Invalid scenario should not succeed: {invalid_result['scenario_type']}"
                assert result.get('total_time', 0) < 25.0, f"Error handling should be quick for {invalid_result['scenario_type']}: {result.get('total_time', 0):.1f}s"
        assert len(exception_scenarios) == 0, f'Should not have connection exceptions during concurrent errors: {exception_scenarios}'
        assert total_time < 60.0, f'Concurrent error handling should complete in reasonable time: {total_time:.2f}s'
        self.logger.info(f'✅ Concurrent error scenarios validated:')
        self.logger.info(f'   Valid Success Rate: {valid_success_rate:.1%}')
        self.logger.info(f'   System Stability: No exceptions')
        self.logger.info(f'   Performance: {total_time:.1f}s')
        self.logger.info('⚡ Concurrent error scenarios test complete')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')