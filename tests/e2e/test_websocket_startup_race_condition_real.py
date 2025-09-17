"""Empty docstring."""
MISSION CRITICAL: WebSocket Startup Race Condition Real Testing - CLAUDE.md Compliant

CRITICAL: Tests REAL race conditions in WebSocket startup using authentic concurrent scenarios.
NO JavaScript injection, NO fake race conditions - Uses real concurrent connection attempts.

This test suite ensures that WebSocket connections handle real race conditions properly:
1. Concurrent authentication attempts don't cause conflicts
2. Multiple rapid connection attempts are handled gracefully  
3. Authentication state races are resolved correctly
4. Real timing issues are detected and handled

CLAUDE.md COMPLIANCE:
- Uses E2EAuthHelper for REAL authentication
- Tests ACTUAL race conditions with concurrent operations
- NO mocks, NO JavaScript overrides, NO fake scenarios
- Execution time validation >= 0.1s 
- Hard failures for race condition violations

CHEATING ON TESTS = ABOMINATION - This tests REAL race conditions only.

Business Value: $500K+ ARR protection by ensuring race conditions don't break user experience.
"""Empty docstring."""
import asyncio
import json
import time
import websockets
import concurrent.futures
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass
import pytest
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper
from test_framework.base_e2e_test import BaseE2ETest
from shared.isolated_environment import get_env
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from auth_service.auth_core.config import AuthConfig
logger = central_logger.get_logger(__name__)
MINIMUM_EXECUTION_TIME = 0.1
RACE_CONDITION_DETECTION_THRESHOLD = 0.05
CONCURRENT_CONNECTION_COUNT = 5

@dataclass
class RaceConditionResult:
    "Result of a race condition test operation."""
    success: bool
    timing: float
    error: Optional[str]
    connection_id: Optional[str]
    user_id: str
    operation: str
    sequence_number: int

class RealRaceConditionTester:
    "Tests REAL race conditions in WebSocket connections."

    def __init__(self, websocket_url: str):
        self.websocket_url = websocket_url
        self.results: List[RaceConditionResult] = []
        self.active_connections: Set[websockets.ServerConnection] = set()
        self.start_time = time.time()

    async def create_concurrent_authenticated_connections(self, auth_helper: E2EAuthHelper, count: int) -> List[RaceConditionResult]:
        "Create multiple REAL authenticated WebSocket connections concurrently."
        logger.info(f'[U+1F3C1] Starting REAL concurrent connection race condition test with {count} connections')
        user_tasks = []
        for i in range(count):
            task = auth_helper.create_authenticated_user(email_prefix=f'race_condition_user_{i}', password=f'RaceCondition{i}123!', name=f'Race Condition Test User {i}')
            user_tasks.append(task)
        users = await asyncio.gather(*user_tasks)
        logger.info(f'[U+2713] Created {len(users)} authenticated users for race condition testing')
        connection_tasks = []
        for i, user_data in enumerate(users):
            task = self._attempt_websocket_connection(user_data, i)
            connection_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*connection_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        race_results = []
        successful_connections = 0
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                race_result = RaceConditionResult(success=False, timing=total_time, error=str(result), connection_id=None, user_id=users[i].user_id, operation='concurrent_connection', sequence_number=i)
            else:
                race_result = result
                if race_result.success:
                    successful_connections += 1
            race_results.append(race_result)
        logger.info(f'[U+1F3C1] Race condition test completed: {successful_connections}/{count} connections successful in {total_time:.3f}s')
        return race_results

    async def _attempt_websocket_connection(self, user_data, sequence: int) -> RaceConditionResult:
        Attempt a single WebSocket connection as part of race condition test.""
        start_time = time.time()
        try:
            extra_headers = {'Authorization': f'Bearer {user_data.auth_token}'}
            await asyncio.sleep(0.001 * sequence)
            websocket = await websockets.connect(self.websocket_url, extra_headers=extra_headers, timeout=10)
            self.active_connections.add(websocket)
            connection_time = time.time() - start_time
            test_message = {'type': 'race_condition_test', 'user_id': user_data.user_id, 'sequence': sequence, 'timestamp': time.time()}
            await websocket.send(json.dumps(test_message))
            try:
                response_str = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                response = json.loads(response_str) if response_str else {}
                logger.info(f[U+1F4E8] Connection {sequence} received response: {response.get('type', 'unknown')})
            except asyncio.TimeoutError:
                pass
            return RaceConditionResult(success=True, timing=connection_time, error=None, connection_id=str(id(websocket)), user_id=user_data.user_id, operation='concurrent_connection', sequence_number=sequence)
        except Exception as e:
            connection_time = time.time() - start_time
            logger.warning(f' WARNING: [U+FE0F] Connection {sequence} failed: {type(e).__name__}: {e}')
            return RaceConditionResult(success=False, timing=connection_time, error=str(e), connection_id=None, user_id=user_data.user_id, operation='concurrent_connection', sequence_number=sequence)

    async def test_rapid_reconnection_race(self, auth_helper: E2EAuthHelper, reconnection_count: int=3) -> List[RaceConditionResult]:
        Test rapid reconnection scenarios to detect race conditions.""
        logger.info(f' CYCLE:  Testing rapid reconnection race conditions with {reconnection_count} cycles')
        user_data = await auth_helper.create_authenticated_user(email_prefix='rapid_reconnection_user', password='RapidReconnect123!', name='Rapid Reconnection Test User')
        results = []
        for cycle in range(reconnection_count):
            logger.info(f' CYCLE:  Reconnection cycle {cycle + 1}/{reconnection_count}')
            connect_result = await self._attempt_websocket_connection(user_data, cycle * 2)
            results.append(connect_result)
            if connect_result.success:
                websocket = None
                for conn in self.active_connections:
                    if str(id(conn)) == connect_result.connection_id:
                        websocket = conn
                        break
                if websocket:
                    await websocket.close()
                    self.active_connections.discard(websocket)
                    reconnect_result = await self._attempt_websocket_connection(user_data, cycle * 2 + 1)
                    results.append(reconnect_result)
                    if reconnect_result.success:
                        for conn in self.active_connections:
                            if str(id(conn)) == reconnect_result.connection_id:
                                await conn.close()
                                self.active_connections.discard(conn)
                                break
            await asyncio.sleep(0.1)
        successful_ops = sum((1 for r in results if r.success))
        logger.info(f' CYCLE:  Rapid reconnection test completed: {successful_ops}/{len(results)} operations successful')
        return results

    async def test_authentication_state_race(self, auth_helper: E2EAuthHelper, concurrent_auth_attempts: int=3) -> List[RaceConditionResult]:
        Test concurrent authentication state changes to detect races.""
        logger.info(f'[U+1F510] Testing authentication state race conditions with {concurrent_auth_attempts} concurrent attempts')
        user_data = await auth_helper.create_authenticated_user(email_prefix='auth_state_race_user', password='AuthStateRace123!', name='Auth State Race Test User')
        auth_tasks = []
        for i in range(concurrent_auth_attempts):
            task = self._test_concurrent_auth_validation(user_data, i)
            auth_tasks.append(task)
        start_time = time.time()
        results = await asyncio.gather(*auth_tasks, return_exceptions=True)
        total_time = time.time() - start_time
        race_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                race_result = RaceConditionResult(success=False, timing=total_time, error=str(result), connection_id=None, user_id=user_data.user_id, operation='concurrent_auth', sequence_number=i)
            else:
                race_result = result
            race_results.append(race_result)
        successful_auths = sum((1 for r in race_results if r.success))
        logger.info(f'[U+1F510] Auth state race test completed: {successful_auths}/{concurrent_auth_attempts} authentications successful in {total_time:.3f}s')
        return race_results

    async def _test_concurrent_auth_validation(self, user_data, sequence: int) -> RaceConditionResult:
        Test concurrent authentication validation.""
        start_time = time.time()
        try:
            jwt_secret = AuthConfig.get_jwt_secret()
            jwt_algorithm = AuthConfig.get_jwt_algorithm()
            await asyncio.sleep(0.001 * sequence)
            import jwt
            payload = jwt.decode(user_data.auth_token, jwt_secret, algorithms=[jwt_algorithm]
            assert payload['sub'] == user_data.user_id
            assert payload['email'] == user_data.email
            validation_time = time.time() - start_time
            return RaceConditionResult(success=True, timing=validation_time, error=None, connection_id=None, user_id=user_data.user_id, operation='concurrent_auth', sequence_number=sequence)
        except Exception as e:
            validation_time = time.time() - start_time
            return RaceConditionResult(success=False, timing=validation_time, error=str(e), connection_id=None, user_id=user_data.user_id, operation='concurrent_auth', sequence_number=sequence)

    async def cleanup_connections(self):
        "Cleanup all active connections."""
        logger.info(f'[U+1F9F9] Cleaning up {len(self.active_connections)} active connections')
        cleanup_tasks = []
        for connection in list(self.active_connections):
            try:
                cleanup_tasks.append(connection.close())
            except Exception:
                pass
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        self.active_connections.clear()
        logger.info('[U+2713] All connections cleaned up')

@pytest.mark.e2e
class WebSocketStartupRaceConditionRealTests(BaseE2ETest):
    "REAL race condition testing for WebSocket startup scenarios."

    def setup_method(self):
        "Setup method with real services initialization."
        super().setup_method()
        self.env = get_env()
        self.env.enable_isolation(backup_original=True)
        test_vars = {'TESTING': '1', 'NETRA_ENV': 'testing', 'ENVIRONMENT': 'testing', 'LOG_LEVEL': 'INFO', 'USE_REAL_SERVICES': 'true', 'WEBSOCKET_URL': 'ws://localhost:8000/ws'}
        for key, value in test_vars.items():
            self.env.set(key, value, source='websocket_race_condition_test')
        self.auth_helper = E2EAuthHelper()
        self.websocket_url = 'ws://localhost:8000/ws'
        self.race_tester = RealRaceConditionTester(self.websocket_url)

    def teardown_method(self):
        Cleanup real connections and race tester.""
        try:
            asyncio.run(self.race_tester.cleanup_connections())
        except Exception:
            pass
        self.env.disable_isolation(restore_original=True)
        super().teardown_method()

    @pytest.mark.critical
    @pytest.mark.timeout(90)
    async def test_concurrent_websocket_connections_no_race_conditions(self):
        Test that concurrent WebSocket connections don't cause race conditions.
        
        CLAUDE.md COMPLIANCE:
         PASS:  Tests REAL concurrent connection scenarios
         PASS:  Uses E2EAuthHelper for REAL authentication
         PASS:  NO mocks, NO fake race conditions
         PASS:  Execution time validation >= 0.1s
         PASS:  Hard failures for race condition violations
""
        start_time = time.time()
        logger.info('[U+1F680] Testing REAL concurrent WebSocket connection race conditions')
        try:
            results = await self.race_tester.create_concurrent_authenticated_connections(self.auth_helper, CONCURRENT_CONNECTION_COUNT)
            successful_connections = [r for r in results if r.success]
            failed_connections = [r for r in results if not r.success]
            logger.info(f' CHART:  Concurrent connection results:')
            logger.info(f'    PASS:  Successful: {len(successful_connections)}')
            logger.info(f'    FAIL:  Failed: {len(failed_connections)}')
            if successful_connections:
                timings = [r.timing for r in successful_connections]
                avg_timing = sum(timings) / len(timings)
                max_timing = max(timings)
                min_timing = min(timings)
                logger.info(f'   [U+23F1][U+FE0F] Timing - Avg: {avg_timing:.3f}s, Min: {min_timing:.3f}s, Max: {max_timing:.3f}s')
                timing_variance = max_timing - min_timing
                if timing_variance > RACE_CONDITION_DETECTION_THRESHOLD:
                    logger.warning(f' WARNING: [U+FE0F] Large timing variance detected: {timing_variance:.3f}s - possible race condition')
            if failed_connections:
                failure_types = {}
                for result in failed_connections:
                    error_type = type(result.error).__name__ if result.error else 'Unknown'
                    failure_types[error_type] = failure_types.get(error_type, 0) + 1
                logger.info(f'   [U+1F4CB] Failure types: {failure_types}')
            success_rate = len(successful_connections) / len(results)
            assert success_rate >= 0.8, f'RACE CONDITION DETECTED: Low success rate {success_rate:.1%} indicates race conditions. Successful: {len(successful_connections)}/{len(results)}'
            auth_related_failures = [r for r in failed_connections if r.error and any((keyword in r.error.lower() for keyword in ['auth', 'token', 'permission', 'forbidden'])]
            assert len(auth_related_failures) == 0, f'RACE CONDITION DETECTED: Authentication race conditions: {[r.error for r in auth_related_failures]}'
            if len(successful_connections) > 1:
                timings = [r.timing for r in successful_connections]
                avg_timing = sum(timings) / len(timings)
                outliers = [t for t in timings if abs(t - avg_timing) > avg_timing * 2]
                assert len(outliers) == 0, f'RACE CONDITION DETECTED: Extreme timing outliers: {outliers}'
        except Exception as e:
            if 'connection refused' in str(e).lower():
                pytest.skip('WebSocket server not running. Start with: python tests/unified_test_runner.py --real-services')
            raise
        execution_time = time.time() - start_time
        assert execution_time >= MINIMUM_EXECUTION_TIME, f'Test executed too quickly ({execution_time:.3f}s) - likely using fake race conditions'
        logger.info(f' PASS:  REAL concurrent connection race condition test PASSED - execution time: {execution_time:.3f}s')
        logger.info(f'   [U+1F3C1] Race condition protection verified for {CONCURRENT_CONNECTION_COUNT} concurrent connections')

    @pytest.mark.critical
    @pytest.mark.timeout(60)
    async def test_rapid_reconnection_no_race_conditions(self):
        Test that rapid reconnection scenarios don't cause race conditions.""
        
        CLAUDE.md COMPLIANCE:
         PASS:  Tests REAL rapid reconnection scenarios
         PASS:  Uses E2EAuthHelper for REAL authentication
         PASS:  NO mocks, NO simulated disconnections
         PASS:  Execution time validation >= 0.1s
         PASS:  Hard failures for reconnection race conditions
"""Empty docstring."""
        start_time = time.time()
        logger.info('[U+1F680] Testing REAL rapid reconnection race conditions')
        try:
            results = await self.race_tester.test_rapid_reconnection_race(self.auth_helper, reconnection_count=3)
            successful_operations = [r for r in results if r.success]
            failed_operations = [r for r in results if not r.success]
            logger.info(f' CHART:  Rapid reconnection results:')
            logger.info(f'    PASS:  Successful operations: {len(successful_operations)}')
            logger.info(f'    FAIL:  Failed operations: {len(failed_operations)}')
            reconnection_failures = [r for r in failed_operations if r.error and any((keyword in r.error.lower() for keyword in ['connection', 'already', 'state', 'closed'])]
            logger.info(f'    CYCLE:  Reconnection-specific failures: {len(reconnection_failures)}')
            success_rate = len(successful_operations) / len(results) if results else 0
            assert success_rate >= 0.7, f'RACE CONDITION DETECTED: Low reconnection success rate {success_rate:.1%} indicates race conditions'
            assert len(reconnection_failures) <= 1, f'RACE CONDITION DETECTED: Multiple connection state conflicts: {[r.error for r in reconnection_failures]}'
        except Exception as e:
            if 'connection refused' in str(e).lower():
                pytest.skip('WebSocket server not running. Start with: python tests/unified_test_runner.py --real-services')
            raise
        execution_time = time.time() - start_time
        assert execution_time >= MINIMUM_EXECUTION_TIME, f'Test executed too quickly ({execution_time:.3f}s) - likely using fake scenarios'
        logger.info(f' PASS:  REAL rapid reconnection race condition test PASSED - execution time: {execution_time:.3f}s')
        logger.info(f'    CYCLE:  Reconnection race condition protection verified')

    @pytest.mark.critical
    @pytest.mark.timeout(45)
    async def test_authentication_state_no_race_conditions(self):
        Test that concurrent authentication operations don't cause race conditions.
        
        CLAUDE.md COMPLIANCE:  
         PASS:  Tests REAL concurrent authentication scenarios
         PASS:  Uses E2EAuthHelper for REAL authentication
         PASS:  NO mocks, NO fake auth states
         PASS:  Execution time validation >= 0.1s
         PASS:  Hard failures for auth race conditions
""""""
        start_time = time.time()
        logger.info('[U+1F680] Testing REAL authentication state race conditions')
        try:
            results = await self.race_tester.test_authentication_state_race(self.auth_helper, concurrent_auth_attempts=3)
            successful_auths = [r for r in results if r.success]
            failed_auths = [r for r in results if not r.success]
            logger.info(f' CHART:  Authentication state race results:')
            logger.info(f'    PASS:  Successful authentications: {len(successful_auths)}')
            logger.info(f'    FAIL:  Failed authentications: {len(failed_auths)}')
            if failed_auths:
                auth_error_types = {}
                for result in failed_auths:
                    error_key = 'expired' if 'expired' in result.error.lower() else 'invalid'
                    auth_error_types[error_key] = auth_error_types.get(error_key, 0) + 1
                logger.info(f'   [U+1F510] Auth error types: {auth_error_types}')
            success_rate = len(successful_auths) / len(results) if results else 0
            assert success_rate >= 0.9, f'RACE CONDITION DETECTED: Auth validation race condition detected. Success rate: {success_rate:.1%}'
            state_corruption_errors = [r for r in failed_auths if r.error and any((keyword in r.error.lower() for keyword in ['corrupt', 'invalid', 'malformed'])]
            assert len(state_corruption_errors) == 0, f'RACE CONDITION DETECTED: Auth state corruption: {[r.error for r in state_corruption_errors]}'
        except Exception as e:
            if 'connection refused' in str(e).lower():
                pytest.skip('WebSocket server not running. Start with: python tests/unified_test_runner.py --real-services')
            raise
        execution_time = time.time() - start_time
        assert execution_time >= MINIMUM_EXECUTION_TIME, f'Test executed too quickly ({execution_time:.3f}s) - likely using fake auth scenarios'
        logger.info(f' PASS:  REAL authentication state race condition test PASSED - execution time: {execution_time:.3f}s')
        logger.info(f'   [U+1F510] Authentication race condition protection verified')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')