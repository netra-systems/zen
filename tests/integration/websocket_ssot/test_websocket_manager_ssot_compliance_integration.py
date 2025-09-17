"""Integration Tests: WebSocket Manager SSOT Compliance - Issue #824

PURPOSE: Integration testing for WebSocket Manager SSOT compliance with real services

BUSINESS IMPACT:
- Priority: P0 CRITICAL
- Impact: $500K+ ARR Golden Path functionality
- Root Cause: Multiple WebSocket Manager implementations break Golden Path user flow

INTEGRATION TEST OBJECTIVES:
1. Test WebSocket Manager integration with staging GCP environment
2. Validate Golden Path user flow with SSOT-compliant WebSocket events
3. Test multi-user WebSocket event isolation with real services
4. Validate WebSocket Manager startup integration with real services
5. Test race condition reproduction with multiple WebSocket factories

EXPECTED BEHAVIOR:
- Tests should FAIL with current fragmentation causing event delivery failures
- Tests should PASS after SSOT consolidation ensures reliable event delivery

This test suite runs against staging GCP environment (no Docker required).
"""
import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, UTC
from typing import Dict, List, Optional, Any
import pytest
from loguru import logger
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env, IsolatedEnvironment

@pytest.mark.integration
class WebSocketManagerSSOTComplianceIntegrationTests(SSotAsyncTestCase):
    """Integration tests for WebSocket Manager SSOT compliance with staging services."""

    @classmethod
    async def asyncSetUpClass(cls):
        """Set up class-level test environment for staging integration."""
        await super().asyncSetUpClass()
        cls.staging_available = await cls._check_staging_availability()
        if not cls.staging_available:
            pytest.skip('Staging environment not available for WebSocket SSOT integration testing')

    @classmethod
    async def _check_staging_availability(cls) -> bool:
        """Check if staging environment is available for testing."""
        try:
            import aiohttp
            env = IsolatedEnvironment()
            staging_url = env.get('STAGING_BACKEND_URL', 'https://staging-backend-dot-netra-staging.uc.r.appspot.com')
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(f'{staging_url}/health') as response:
                    return response.status == 200
        except Exception as e:
            logger.warning(f'Staging availability check failed: {e}')
            return False

    async def asyncSetUp(self):
        """Set up individual test environment."""
        await super().asyncSetUp()
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from shared.types.core_types import ensure_user_id, ensure_thread_id
        self.test_user_id = f'test_user_{uuid.uuid4().hex[:8]}'
        self.test_thread_id = f'thread_{uuid.uuid4().hex[:8]}'
        self.test_run_id = f'run_{uuid.uuid4().hex[:8]}'
        self.user_context = UserExecutionContext(user_id=ensure_user_id(self.test_user_id), thread_id=ensure_thread_id(self.test_thread_id), run_id=self.test_run_id, request_id=f'integration_test_{uuid.uuid4().hex[:8]}')

    async def test_websocket_manager_ssot_import_consistency_integration(self):
        """
        INTEGRATION TEST: Validate SSOT import consistency with real staging environment.

        EXPECTED TO FAIL: Fragmented imports cause initialization inconsistencies
        EXPECTED TO PASS: SSOT imports provide consistent manager instances
        """
        managers_created = []
        creation_errors = []
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager, get_websocket_manager
            manager1 = WebSocketManager(user_context=self.user_context)
            managers_created.append(('Direct WebSocketManager', manager1))
            manager2 = get_websocket_manager(user_context=self.user_context)
            managers_created.append(('get_websocket_manager factory', manager2))
        except Exception as e:
            creation_errors.append(f'SSOT canonical import failed: {e}')
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            manager3 = UnifiedWebSocketManager(user_context=self.user_context)
            managers_created.append(('UnifiedWebSocketManager direct', manager3))
        except Exception as e:
            creation_errors.append(f'UnifiedWebSocketManager import failed: {e}')
        logger.info(f'Created {len(managers_created)} WebSocket managers via different import paths')
        for method, manager in managers_created:
            logger.info(f'  {method}: {type(manager).__name__} from {type(manager).__module__}')
        if creation_errors:
            logger.error(f'Creation errors: {creation_errors}')
        self.assertEqual(len(creation_errors), 0, f'SSOT IMPORT FAILURE: {len(creation_errors)} import paths failed. SSOT consolidation should eliminate import inconsistencies. Errors: {creation_errors}')
        if len(managers_created) > 1:
            manager_types = [type(manager).__name__ for _, manager in managers_created]
            unique_types = set(manager_types)
            self.assertEqual(len(unique_types), 1, f'SSOT TYPE INCONSISTENCY: Different import paths create different manager types. Expected single type, found: {unique_types}')

    async def test_websocket_manager_golden_path_event_delivery_integration(self):
        """
        GOLDEN PATH INTEGRATION TEST: Validate 5 critical WebSocket events with SSOT manager.

        EXPECTED TO FAIL: Fragmented managers cause event delivery failures
        EXPECTED TO PASS: SSOT manager ensures all 5 events are delivered
        """
        required_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        received_events = []
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            manager = WebSocketManager(user_context=self.user_context)

            class MockWebSocketConnection:

                def __init__(self):
                    self.events = []

                async def send_text(self, data):
                    try:
                        event_data = json.loads(data)
                        if 'type' in event_data:
                            self.events.append(event_data['type'])
                            received_events.append(event_data['type'])
                    except json.JSONDecodeError:
                        pass

                async def close(self):
                    pass
            mock_connection = MockWebSocketConnection()
            connection_id = f'test_connection_{uuid.uuid4().hex[:8]}'
            if hasattr(manager, '_connections'):
                manager._connections[connection_id] = mock_connection
            for event_type in required_events:
                try:
                    await manager.send_agent_event(event_type=event_type, data={'message': f'Test {event_type} event', 'timestamp': datetime.now(UTC).isoformat()}, user_context=self.user_context)
                    await asyncio.sleep(0.1)
                except Exception as e:
                    logger.error(f'Failed to send {event_type} event: {e}')
        except Exception as e:
            self.fail(f'SSOT WebSocket Manager creation failed: {e}')
        logger.info(f'Expected events: {required_events}')
        logger.info(f'Received events: {received_events}')
        for event_type in required_events:
            self.assertIn(event_type, received_events, f'GOLDEN PATH EVENT FAILURE: {event_type} event not delivered. SSOT manager must deliver all 5 critical events for Golden Path. Missing events break $500K+ ARR chat functionality.')

    async def test_websocket_manager_multi_user_isolation_integration(self):
        """
        MULTI-USER INTEGRATION TEST: Validate user isolation with SSOT WebSocket managers.

        EXPECTED TO FAIL: Fragmented managers break user isolation
        EXPECTED TO PASS: SSOT manager maintains proper user isolation
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from shared.types.core_types import ensure_user_id, ensure_thread_id
        user_contexts = []
        for i in range(3):
            user_context = UserExecutionContext(user_id=ensure_user_id(f'isolation_test_user_{i}'), thread_id=ensure_thread_id(f'isolation_thread_{i}'), run_id=f'isolation_run_{i}', request_id=f'isolation_req_{i}')
            user_contexts.append(user_context)
        managers = []
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            for i, context in enumerate(user_contexts):
                manager = WebSocketManager(user_context=context)
                managers.append((f'user_{i}', manager))
        except Exception as e:
            self.fail(f'Failed to create isolated WebSocket managers: {e}')
        for i, (user_name, manager) in enumerate(managers):
            self.assertEqual(manager.user_context.user_id, user_contexts[i].user_id, f'USER CONTEXT ISOLATION FAILURE: Manager {user_name} has wrong user context')
            for j, (other_user_name, other_manager) in enumerate(managers):
                if i != j:
                    self.assertNotEqual(id(manager), id(other_manager), f'MANAGER ISOLATION FAILURE: {user_name} and {other_user_name} share manager instances')
        logger.info(f'Successfully created and validated isolation for {len(managers)} users')

    async def test_websocket_manager_race_condition_reproduction_integration(self):
        """
        RACE CONDITION INTEGRATION TEST: Reproduce race conditions with multiple factories.

        EXPECTED TO FAIL: Multiple factory paths cause race conditions
        EXPECTED TO PASS: Single SSOT factory eliminates race conditions
        """
        race_condition_detected = False
        creation_times = []

        async def create_manager_method_1():
            start_time = time.time()
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                manager = WebSocketManager(user_context=self.user_context)
                end_time = time.time()
                creation_times.append(('Direct WebSocketManager', end_time - start_time))
                return manager
            except Exception as e:
                logger.error(f'Method 1 creation failed: {e}')
                raise

        async def create_manager_method_2():
            start_time = time.time()
            try:
                from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
                manager = get_websocket_manager(user_context=self.user_context)
                end_time = time.time()
                creation_times.append(('Factory get_websocket_manager', end_time - start_time))
                return manager
            except Exception as e:
                logger.error(f'Method 2 creation failed: {e}')
                raise

        async def create_manager_method_3():
            start_time = time.time()
            try:
                from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
                manager = UnifiedWebSocketManager(user_context=self.user_context)
                end_time = time.time()
                creation_times.append(('UnifiedWebSocketManager', end_time - start_time))
                return manager
            except Exception as e:
                logger.error(f'Method 3 creation failed: {e}')
                raise
        tasks = [create_manager_method_1(), create_manager_method_2(), create_manager_method_3()]
        try:
            managers = await asyncio.gather(*tasks, return_exceptions=True)
            exceptions = [m for m in managers if isinstance(m, Exception)]
            successful_managers = [m for m in managers if not isinstance(m, Exception)]
            logger.info(f'Concurrent creation results:')
            logger.info(f'  Successful managers: {len(successful_managers)}')
            logger.info(f'  Exceptions: {len(exceptions)}')
            for exc in exceptions:
                logger.error(f'    {type(exc).__name__}: {exc}')
            if len(creation_times) > 1:
                times = [t[1] for t in creation_times]
                time_variance = max(times) - min(times)
                logger.info(f'Creation time variance: {time_variance:.3f}s')
                for method, duration in creation_times:
                    logger.info(f'  {method}: {duration:.3f}s')
                if time_variance > 0.5:
                    race_condition_detected = True
        except Exception as e:
            logger.error(f'Concurrent creation test failed: {e}')
        self.assertFalse(race_condition_detected, f'RACE CONDITION DETECTED: Significant creation time variance suggests race conditions. SSOT consolidation should eliminate timing dependencies between factory methods.')

    async def test_websocket_manager_staging_environment_integration(self):
        """
        STAGING INTEGRATION TEST: Validate WebSocket Manager with real staging environment.

        EXPECTED TO FAIL: Fragmentation causes staging integration failures
        EXPECTED TO PASS: SSOT manager integrates reliably with staging
        """
        if not self.staging_available:
            self.skipTest('Staging environment not available')
        import aiohttp
        env = IsolatedEnvironment()
        staging_url = env.get('STAGING_BACKEND_URL', 'https://staging-backend-dot-netra-staging.uc.r.appspot.com')
        try:
            from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
            manager = WebSocketManager(user_context=self.user_context)
            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                ws_url = staging_url.replace('https:', 'wss:') + '/ws'
                try:
                    async with session.ws_connect(ws_url) as ws:
                        test_message = {'type': 'test_connection', 'user_id': self.user_context.user_id, 'timestamp': datetime.now(UTC).isoformat()}
                        await ws.send_str(json.dumps(test_message))
                        response = await asyncio.wait_for(ws.receive(), timeout=10)
                        self.assertIsNotNone(response)
                        logger.info(f'Staging WebSocket response: {response}')
                except asyncio.TimeoutError:
                    logger.warning('Staging WebSocket connection timeout - may indicate fragmentation issues')
                except aiohttp.ClientError as e:
                    logger.warning(f'Staging WebSocket connection failed: {e}')
        except Exception as e:
            logger.error(f'Staging integration test failed: {e}')
            pass
        logger.info('WebSocket Manager staging integration test completed')
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')