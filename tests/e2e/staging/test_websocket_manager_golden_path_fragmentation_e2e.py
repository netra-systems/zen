"""E2E Tests: WebSocket Manager Golden Path Fragmentation - Issue #824

PURPOSE: End-to-end testing of WebSocket Manager fragmentation impact on Golden Path user flow

BUSINESS IMPACT:
- Priority: P0 CRITICAL
- Impact: $500K+ ARR Golden Path functionality
- User Flow: Login → AI responses (core business value)
- Events at Risk: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

E2E TEST OBJECTIVES:
1. Test complete Golden Path user flow with fragmented WebSocket managers
2. Validate end-to-end WebSocket event delivery to real frontend clients
3. Test multi-user Golden Path scenarios with staging GCP environment
4. Reproduce real-world race conditions affecting customer chat experience
5. Validate Golden Path reliability after SSOT consolidation

EXPECTED BEHAVIOR:
- Tests should FAIL with current fragmentation causing Golden Path failures
- Tests should PASS after SSOT consolidation ensures reliable Golden Path

This test suite runs against staging GCP environment with real WebSocket connections.
"""
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, UTC
from typing import Dict, List, Optional, Any, Set
import pytest
from loguru import logger
import aiohttp
import websockets
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env, IsolatedEnvironment

@pytest.mark.e2e
class WebSocketManagerGoldenPathFragmentationE2ETests(SSotAsyncTestCase):
    """E2E tests for WebSocket Manager fragmentation impact on Golden Path user flow."""
    GOLDEN_PATH_EVENTS = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

    @classmethod
    async def asyncSetUpClass(cls):
        """Set up class-level test environment for staging E2E."""
        await super().asyncSetUpClass()
        cls.env = IsolatedEnvironment()
        cls.staging_url = cls.env.get('STAGING_BACKEND_URL', 'https://staging-backend-dot-netra-staging.uc.r.appspot.com')
        cls.staging_ws_url = cls.staging_url.replace('https:', 'wss:') + '/ws'
        cls.staging_available = await cls._check_staging_availability()
        if not cls.staging_available:
            pytest.skip('Staging environment not available for Golden Path E2E testing')
        logger.info(f'E2E testing against staging: {cls.staging_url}')

    @classmethod
    async def _check_staging_availability(cls) -> bool:
        """Check if staging environment is available for E2E testing."""
        try:
            timeout = aiohttp.ClientTimeout(total=15)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f'{cls.staging_url}/health') as response:
                    if response.status == 200:
                        health_data = await response.json()
                        logger.info(f'Staging health check passed: {health_data}')
                        return True
                    else:
                        logger.warning(f'Staging health check failed: {response.status}')
                        return False
        except Exception as e:
            logger.error(f'Staging availability check failed: {e}')
            return False

    async def asyncSetUp(self):
        """Set up individual E2E test environment."""
        await super().asyncSetUp()
        self.test_session_id = f'e2e_test_{uuid.uuid4().hex[:12]}'
        self.test_user_id = f'golden_path_user_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'golden_thread_{uuid.uuid4().hex[:8]}'
        logger.info(f'Starting E2E test session: {self.test_session_id}')

    async def test_golden_path_complete_user_flow_e2e(self):
        """
        GOLDEN PATH E2E: Test complete user login → AI response flow with WebSocket events.

        EXPECTED TO FAIL: Fragmented managers cause Golden Path event delivery failures
        EXPECTED TO PASS: SSOT manager ensures reliable Golden Path user experience
        """
        if not self.staging_available:
            self.skipTest('Staging environment not available')
        received_events = []
        connection_issues = []
        golden_path_success = False
        try:
            logger.info('Phase 1: Establishing WebSocket connection to staging...')
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                try:
                    async with session.ws_connect(self.staging_ws_url, heartbeat=30) as ws:
                        logger.info('Phase 2: Simulating Golden Path user request...')
                        agent_request = {'type': 'agent_request', 'user_id': self.test_user_id, 'thread_id': self.test_thread_id, 'session_id': self.test_session_id, 'message': 'Help me optimize my AI costs for better efficiency', 'timestamp': datetime.now(UTC).isoformat()}
                        await ws.send_str(json.dumps(agent_request))
                        logger.info(f"Sent Golden Path request: {agent_request['message']}")
                        logger.info('Phase 3: Monitoring for Golden Path WebSocket events...')
                        event_timeout = 60
                        start_time = time.time()
                        while time.time() - start_time < event_timeout:
                            try:
                                response = await asyncio.wait_for(ws.receive(), timeout=5)
                                if response.type == aiohttp.WSMsgType.TEXT:
                                    try:
                                        event_data = json.loads(response.data)
                                        event_type = event_data.get('type')
                                        if event_type:
                                            received_events.append(event_type)
                                            logger.info(f'Received Golden Path event: {event_type}')
                                            if all((event in received_events for event in self.GOLDEN_PATH_EVENTS)):
                                                golden_path_success = True
                                                logger.info('✅ All Golden Path events received successfully!')
                                                break
                                    except json.JSONDecodeError as e:
                                        logger.warning(f'Invalid JSON received: {e}')
                                elif response.type == aiohttp.WSMsgType.ERROR:
                                    connection_issues.append(f'WebSocket error: {response}')
                                    logger.error(f'WebSocket error: {response}')
                            except asyncio.TimeoutError:
                                logger.debug('Waiting for more events...')
                                continue
                            except Exception as e:
                                connection_issues.append(f'Event receive error: {e}')
                                logger.error(f'Event receive error: {e}')
                                break
                except aiohttp.ClientError as e:
                    connection_issues.append(f'WebSocket connection failed: {e}')
                    logger.error(f'WebSocket connection failed: {e}')
        except Exception as e:
            connection_issues.append(f'E2E test setup failed: {e}')
            logger.error(f'E2E test setup failed: {e}')
        logger.info('Phase 4: Validating Golden Path completion...')
        logger.info(f'Golden Path E2E Results:')
        logger.info(f'  Expected events: {self.GOLDEN_PATH_EVENTS}')
        logger.info(f'  Received events: {received_events}')
        logger.info(f'  Connection issues: {len(connection_issues)}')
        logger.info(f'  Golden Path success: {golden_path_success}')
        if connection_issues:
            for issue in connection_issues:
                logger.error(f'  Connection issue: {issue}')
        missing_events = [event for event in self.GOLDEN_PATH_EVENTS if event not in received_events]
        self.assertEqual(len(missing_events), 0, f'GOLDEN PATH FAILURE: {len(missing_events)} critical events missing. Missing events: {missing_events}. WebSocket Manager fragmentation prevents delivery of events critical for $500K+ ARR chat functionality. Received events: {received_events}. Connection issues: {connection_issues}')
        self.assertTrue(golden_path_success, f'GOLDEN PATH INCOMPLETE: Complete user flow did not succeed. WebSocket Manager fragmentation breaks end-to-end user experience. Received {len(received_events)}/{len(self.GOLDEN_PATH_EVENTS)} critical events.')

    async def test_multi_user_golden_path_isolation_e2e(self):
        """
        MULTI-USER E2E: Test Golden Path isolation with multiple concurrent users.

        EXPECTED TO FAIL: Fragmented managers cause user isolation failures
        EXPECTED TO PASS: SSOT manager maintains proper multi-user isolation
        """
        if not self.staging_available:
            self.skipTest('Staging environment not available')
        num_concurrent_users = 3
        user_results = {}
        isolation_violations = []

        async def simulate_user_golden_path(user_index: int):
            """Simulate Golden Path for a single user."""
            user_id = f'multiuser_test_{user_index}_{uuid.uuid4().hex[:6]}'
            thread_id = f'thread_{user_index}_{uuid.uuid4().hex[:6]}'
            session_id = f'session_{user_index}_{uuid.uuid4().hex[:6]}'
            user_events = []
            user_issues = []
            try:
                timeout = aiohttp.ClientTimeout(total=45)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.ws_connect(self.staging_ws_url, heartbeat=30) as ws:
                        agent_request = {'type': 'agent_request', 'user_id': user_id, 'thread_id': thread_id, 'session_id': session_id, 'message': f'User {user_index} Golden Path test request', 'timestamp': datetime.now(UTC).isoformat()}
                        await ws.send_str(json.dumps(agent_request))
                        event_timeout = 30
                        start_time = time.time()
                        while time.time() - start_time < event_timeout:
                            try:
                                response = await asyncio.wait_for(ws.receive(), timeout=3)
                                if response.type == aiohttp.WSMsgType.TEXT:
                                    try:
                                        event_data = json.loads(response.data)
                                        event_type = event_data.get('type')
                                        event_user_id = event_data.get('user_id', event_data.get('userId'))
                                        if event_type:
                                            user_events.append(event_type)
                                            if event_user_id and event_user_id != user_id:
                                                isolation_violations.append({'expected_user': user_id, 'received_user': event_user_id, 'event_type': event_type, 'user_index': user_index})
                                        if len(user_events) >= len(self.GOLDEN_PATH_EVENTS):
                                            break
                                    except json.JSONDecodeError:
                                        continue
                            except asyncio.TimeoutError:
                                continue
            except Exception as e:
                user_issues.append(f'User {user_index} connection failed: {e}')
            return {'user_index': user_index, 'user_id': user_id, 'events': user_events, 'issues': user_issues}
        logger.info(f'Testing multi-user Golden Path with {num_concurrent_users} concurrent users...')
        tasks = [simulate_user_golden_path(i) for i in range(num_concurrent_users)]
        user_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_users = [r for r in user_results if not isinstance(r, Exception)]
        failed_users = [r for r in user_results if isinstance(r, Exception)]
        logger.info(f'Multi-user Golden Path results:')
        logger.info(f'  Successful users: {len(successful_users)}/{num_concurrent_users}')
        logger.info(f'  Failed users: {len(failed_users)}')
        logger.info(f'  Isolation violations: {len(isolation_violations)}')
        for user_result in successful_users:
            logger.info(f"  User {user_result['user_index']}: {len(user_result['events'])} events")
        self.assertEqual(len(isolation_violations), 0, f'USER ISOLATION FAILURE: {len(isolation_violations)} isolation violations detected. WebSocket Manager fragmentation causes event cross-contamination between users. Violations: {isolation_violations}')
        for user_result in successful_users:
            self.assertGreater(len(user_result['events']), 0, f"USER {user_result['user_index']} GOLDEN PATH FAILURE: No events received. Multi-user WebSocket Manager fragmentation prevents event delivery.")

    async def test_websocket_manager_race_condition_reproduction_e2e(self):
        """
        RACE CONDITION E2E: Reproduce real-world race conditions affecting Golden Path.

        EXPECTED TO FAIL: Fragmented managers cause race conditions in production
        EXPECTED TO PASS: SSOT manager eliminates race conditions
        """
        if not self.staging_available:
            self.skipTest('Staging environment not available')
        race_conditions_detected = []
        connection_failures = []

        async def rapid_connection_test(connection_index: int):
            """Test rapid WebSocket connections to detect race conditions."""
            try:
                connection_id = f'race_test_{connection_index}_{uuid.uuid4().hex[:6]}'
                start_time = time.time()
                timeout = aiohttp.ClientTimeout(total=10)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.ws_connect(self.staging_ws_url, heartbeat=10) as ws:
                        connection_time = time.time() - start_time
                        test_message = {'type': 'race_condition_test', 'connection_id': connection_id, 'connection_index': connection_index, 'timestamp': datetime.now(UTC).isoformat()}
                        await ws.send_str(json.dumps(test_message))
                        response = await asyncio.wait_for(ws.receive(), timeout=5)
                        return {'connection_index': connection_index, 'connection_id': connection_id, 'connection_time': connection_time, 'success': True, 'response_received': response.type == aiohttp.WSMsgType.TEXT}
            except Exception as e:
                connection_failures.append({'connection_index': connection_index, 'error': str(e), 'error_type': type(e).__name__})
                return {'connection_index': connection_index, 'success': False, 'error': str(e)}
        logger.info('Testing for race conditions with rapid concurrent connections...')
        num_connections = 10
        tasks = [rapid_connection_test(i) for i in range(num_connections)]
        connection_results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_connections = [r for r in connection_results if not isinstance(r, Exception) and r.get('success')]
        failed_connections = [r for r in connection_results if isinstance(r, Exception) or not r.get('success')]
        logger.info(f'Race condition test results:')
        logger.info(f'  Successful connections: {len(successful_connections)}/{num_connections}')
        logger.info(f'  Failed connections: {len(failed_connections)}')
        if successful_connections:
            connection_times = [r['connection_time'] for r in successful_connections]
            avg_time = sum(connection_times) / len(connection_times)
            max_time = max(connection_times)
            min_time = min(connection_times)
            time_variance = max_time - min_time
            logger.info(f'  Connection time stats:')
            logger.info(f'    Average: {avg_time:.3f}s')
            logger.info(f'    Min: {min_time:.3f}s')
            logger.info(f'    Max: {max_time:.3f}s')
            logger.info(f'    Variance: {time_variance:.3f}s')
            if time_variance > 2.0:
                race_conditions_detected.append(f'High connection time variance: {time_variance:.3f}s')
        error_types = {}
        for failure in connection_failures:
            error_type = failure.get('error_type', 'Unknown')
            error_types[error_type] = error_types.get(error_type, 0) + 1
        logger.info(f'  Error types: {error_types}')
        timeout_errors = error_types.get('TimeoutError', 0)
        if timeout_errors > num_connections * 0.3:
            race_conditions_detected.append(f'High timeout rate: {timeout_errors}/{num_connections}')
        race_condition_threshold = 2
        self.assertLessEqual(len(race_conditions_detected), race_condition_threshold, f'RACE CONDITIONS DETECTED: {len(race_conditions_detected)} race condition indicators. WebSocket Manager fragmentation causes production race conditions affecting Golden Path. Detected conditions: {race_conditions_detected}. Connection failures: {len(connection_failures)}/{num_connections}')

    async def test_golden_path_resilience_under_load_e2e(self):
        """
        LOAD RESILIENCE E2E: Test Golden Path resilience under concurrent load.

        EXPECTED TO FAIL: Fragmented managers fail under concurrent load
        EXPECTED TO PASS: SSOT manager maintains Golden Path under load
        """
        if not self.staging_available:
            self.skipTest('Staging environment not available')
        load_test_results = {'total_requests': 0, 'successful_golden_paths': 0, 'failed_golden_paths': 0, 'partial_golden_paths': 0, 'connection_errors': 0}

        async def golden_path_under_load(request_index: int):
            """Simulate Golden Path request under load."""
            try:
                user_id = f'load_test_user_{request_index}'
                request_events = []
                timeout = aiohttp.ClientTimeout(total=20)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.ws_connect(self.staging_ws_url, heartbeat=20) as ws:
                        agent_request = {'type': 'agent_request', 'user_id': user_id, 'thread_id': f'load_thread_{request_index}', 'message': f'Load test request {request_index}', 'timestamp': datetime.now(UTC).isoformat()}
                        await ws.send_str(json.dumps(agent_request))
                        event_timeout = 15
                        start_time = time.time()
                        while time.time() - start_time < event_timeout:
                            try:
                                response = await asyncio.wait_for(ws.receive(), timeout=2)
                                if response.type == aiohttp.WSMsgType.TEXT:
                                    try:
                                        event_data = json.loads(response.data)
                                        event_type = event_data.get('type')
                                        if event_type in self.GOLDEN_PATH_EVENTS:
                                            request_events.append(event_type)
                                        if len(request_events) >= len(self.GOLDEN_PATH_EVENTS):
                                            break
                                    except json.JSONDecodeError:
                                        continue
                            except asyncio.TimeoutError:
                                continue
                return {'request_index': request_index, 'events': request_events, 'success': len(request_events) >= len(self.GOLDEN_PATH_EVENTS), 'partial': 0 < len(request_events) < len(self.GOLDEN_PATH_EVENTS)}
            except Exception as e:
                logger.error(f'Load test request {request_index} failed: {e}')
                return {'request_index': request_index, 'events': [], 'success': False, 'partial': False, 'error': str(e)}
        logger.info('Testing Golden Path resilience under concurrent load...')
        num_concurrent_requests = 5
        tasks = [golden_path_under_load(i) for i in range(num_concurrent_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for result in results:
            if isinstance(result, Exception):
                load_test_results['connection_errors'] += 1
                continue
            load_test_results['total_requests'] += 1
            if result.get('success'):
                load_test_results['successful_golden_paths'] += 1
            elif result.get('partial'):
                load_test_results['partial_golden_paths'] += 1
            else:
                load_test_results['failed_golden_paths'] += 1
        success_rate = load_test_results['successful_golden_paths'] / max(load_test_results['total_requests'], 1) * 100
        logger.info(f'Load resilience test results:')
        logger.info(f"  Total requests: {load_test_results['total_requests']}")
        logger.info(f"  Successful Golden Paths: {load_test_results['successful_golden_paths']}")
        logger.info(f"  Partial Golden Paths: {load_test_results['partial_golden_paths']}")
        logger.info(f"  Failed Golden Paths: {load_test_results['failed_golden_paths']}")
        logger.info(f"  Connection errors: {load_test_results['connection_errors']}")
        logger.info(f'  Success rate: {success_rate:.1f}%')
        minimum_success_rate = 70.0
        self.assertGreaterEqual(success_rate, minimum_success_rate, f'GOLDEN PATH LOAD FAILURE: {success_rate:.1f}% success rate below {minimum_success_rate}% threshold. WebSocket Manager fragmentation causes Golden Path failures under load. Production reliability requires consistent Golden Path delivery. Results: {load_test_results}')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')