"""Phase 2 Integration Tests: Execution Engine Factory WebSocket Coordination (Issue #1123)

CRITICAL BUSINESS VALUE: These tests reproduce WebSocket coordination issues that
cause WebSocket 1011 errors, blocking the Golden Path user flow and $500K+ ARR.

EXPECTED BEHAVIOR: All tests in this file should INITIALLY FAIL to demonstrate
the WebSocket coordination problems. They will pass after fixes are implemented.

Business Value Justification (BVJ):
- Segment: All (Free -> Enterprise)
- Business Goal: Ensure reliable service coordination for chat functionality
- Value Impact: Prevents Golden Path initialization failures and WebSocket 1011 errors
- Strategic Impact: Essential for $500K+ ARR chat reliability and real-time communication

Infrastructure Requirements:
- Local PostgreSQL (port 5434) - NO DOCKER
- Local Redis (port 6381) - NO DOCKER
- Real WebSocket connections
- Real service integration testing

Test Philosophy:
- FAILING TESTS FIRST: These tests reproduce real WebSocket coordination issues
- REAL SERVICES ONLY: No mocks - use actual database, Redis, WebSocket connections
- RACE CONDITION REPRODUCTION: Tests demonstrate timing-sensitive failures
- GOLDEN PATH PROTECTION: Tests validate end-to-end service coordination
"""
import pytest
import asyncio
import gc
import inspect
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Any, Optional
from unittest.mock import patch, MagicMock
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.fixtures.real_services_fixtures import RealServicesFixtureMixin
from netra_backend.app.services.user_execution_context import UserExecutionContext

@pytest.mark.integration
class ExecutionEngineFactoryWebSocketCoordination1123Tests(SSotAsyncTestCase, RealServicesFixtureMixin):
    """Phase 2 Integration Tests: Factory WebSocket Coordination Issues

    These tests are designed to FAIL initially to demonstrate the WebSocket
    coordination issues that cause 1011 errors and block the Golden Path.
    They will pass after coordination fixes are implemented.
    """

    def setUp(self):
        """Set up test environment with real services."""
        super().setUp()
        self.test_users = []
        self.factory_instances = []
        self.created_contexts = []
        self.websocket_bridges = []
        self.coordination_metrics = []
        self.received_events = []
        self.websocket_errors = []
        self.coordination_failures = []
        self.max_coordination_delay = 5.0
        self.websocket_timeout = 10.0

    async def asyncSetUp(self):
        """Set up real services for integration testing."""
        await super().asyncSetUp()
        await self.setup_real_services()

    async def asyncTearDown(self):
        """Clean up test resources and real services."""
        for context in self.created_contexts:
            try:
                if hasattr(context, 'cleanup'):
                    await context.cleanup()
            except Exception:
                pass
        for factory in self.factory_instances:
            try:
                if hasattr(factory, 'shutdown'):
                    await factory.shutdown()
            except Exception:
                pass
        for bridge in self.websocket_bridges:
            try:
                if hasattr(bridge, 'cleanup'):
                    await bridge.cleanup()
            except Exception:
                pass
        await self.cleanup_real_services()
        gc.collect()
        await super().asyncTearDown()

    async def test_factory_service_dependency_resolution_failures(self):
        """FAILING TEST: Reproduce service dependency resolution issues

        BVJ: All Segments - Ensures factory resolves service dependencies correctly
        EXPECTED: FAIL - Factory fails to coordinate with database and Redis properly
        ISSUE: Service dependency resolution race conditions cause initialization failures
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        except ImportError as e:
            self.fail(f'Cannot import required classes: {e}')
        coordination_results = []

        async def test_service_coordination(test_scenario: str, delay_before_factory: float):
            """Test factory creation with service dependency timing."""
            start_time = time.time()
            try:
                if delay_before_factory > 0:
                    await asyncio.sleep(delay_before_factory)
                db_session = await self.get_real_database_session()
                redis_client = await self.get_real_redis_client()
                if not db_session or not redis_client:
                    raise Exception('Real services not available')
                websocket_bridge = AgentWebSocketBridge(database_session_manager=db_session, redis_manager=redis_client)
                self.websocket_bridges.append(websocket_bridge)
                factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge, database_session_manager=db_session, redis_manager=redis_client)
                self.factory_instances.append(factory)
                context = UserExecutionContext(user_id=f'coord_test_user_{test_scenario}', run_id=f'coord_test_run_{test_scenario}_{int(time.time() * 1000)}', session_id=f'coord_test_session_{test_scenario}', request_id=f'coord_test_request_{test_scenario}')
                self.created_contexts.append(context)
                engine = await factory.create_for_user(context)
                coordination_time = time.time() - start_time
                await factory.cleanup_engine(engine)
                return {'scenario': test_scenario, 'success': True, 'coordination_time': coordination_time, 'error': None}
            except Exception as e:
                coordination_time = time.time() - start_time
                return {'scenario': test_scenario, 'success': False, 'coordination_time': coordination_time, 'error': str(e)}
        coordination_scenarios = [('immediate_factory_creation', 0.0), ('delayed_factory_creation', 0.1), ('slow_service_startup', 0.5)]
        tasks = [test_service_coordination(scenario, delay) for scenario, delay in coordination_scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_coordinations = 0
        failed_coordinations = 0
        for result in results:
            if isinstance(result, dict):
                coordination_results.append(result)
                if result['success']:
                    successful_coordinations += 1
                else:
                    failed_coordinations += 1
                    self.coordination_failures.append(result)
            else:
                failed_coordinations += 1
                self.coordination_failures.append({'scenario': 'exception', 'success': False, 'error': str(result)})
        self.assertEqual(failed_coordinations, 0, f"SERVICE COORDINATION FAILURES: {failed_coordinations} out of {len(coordination_scenarios)} coordination tests failed. Factory cannot properly coordinate with real services. Failures: {[f['error'] for f in self.coordination_failures]}")
        for result in coordination_results:
            if result['success']:
                self.assertLess(result['coordination_time'], self.max_coordination_delay, f"SERVICE COORDINATION TOO SLOW: {result['scenario']} took {result['coordination_time']:.2f}s (limit: {self.max_coordination_delay}s). Factory service coordination is too slow for production use.")

    async def test_factory_startup_sequence_coordination_race_conditions(self):
        """FAILING TEST: Reproduce startup sequence coordination race conditions

        BVJ: Platform - Ensures proper startup sequence prevents race conditions
        EXPECTED: FAIL - Startup sequence coordination causes race conditions
        ISSUE: Service startup timing dependencies cause factory initialization failures
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory, configure_execution_engine_factory
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        except ImportError as e:
            self.fail(f'Cannot import required classes: {e}')
        startup_sequence_results = []

        async def test_startup_sequence(sequence_name: str, service_order: List[str]):
            """Test different service startup sequences."""
            start_time = time.time()
            sequence_services = {}
            try:
                for service in service_order:
                    if service == 'database':
                        sequence_services['database'] = await self.get_real_database_session()
                        await asyncio.sleep(0.05)
                    elif service == 'redis':
                        sequence_services['redis'] = await self.get_real_redis_client()
                        await asyncio.sleep(0.03)
                    elif service == 'websocket':
                        sequence_services['websocket'] = AgentWebSocketBridge(database_session_manager=sequence_services.get('database'), redis_manager=sequence_services.get('redis'))
                        self.websocket_bridges.append(sequence_services['websocket'])
                        await asyncio.sleep(0.02)
                    elif service == 'factory':
                        sequence_services['factory'] = ExecutionEngineFactory(websocket_bridge=sequence_services.get('websocket'), database_session_manager=sequence_services.get('database'), redis_manager=sequence_services.get('redis'))
                        self.factory_instances.append(sequence_services['factory'])
                required_services = ['database', 'redis', 'websocket', 'factory']
                missing_services = [svc for svc in required_services if svc not in sequence_services or sequence_services[svc] is None]
                if missing_services:
                    raise Exception(f'Failed to initialize services: {missing_services}')
                context = UserExecutionContext(user_id=f'startup_test_user_{sequence_name}', run_id=f'startup_test_run_{sequence_name}_{int(time.time() * 1000)}', session_id=f'startup_test_session_{sequence_name}', request_id=f'startup_test_request_{sequence_name}')
                self.created_contexts.append(context)
                factory = sequence_services['factory']
                engine = await factory.create_for_user(context)
                startup_time = time.time() - start_time
                await factory.cleanup_engine(engine)
                return {'sequence': sequence_name, 'order': service_order, 'success': True, 'startup_time': startup_time, 'error': None}
            except Exception as e:
                startup_time = time.time() - start_time
                return {'sequence': sequence_name, 'order': service_order, 'success': False, 'startup_time': startup_time, 'error': str(e)}
        startup_sequences = [('correct_sequence', ['database', 'redis', 'websocket', 'factory']), ('reverse_sequence', ['factory', 'websocket', 'redis', 'database']), ('random_sequence', ['redis', 'factory', 'database', 'websocket']), ('websocket_first', ['websocket', 'database', 'redis', 'factory'])]
        tasks = [test_startup_sequence(seq_name, order) for seq_name, order in startup_sequences]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_sequences = 0
        failed_sequences = 0
        sequence_failures = []
        for result in results:
            if isinstance(result, dict):
                startup_sequence_results.append(result)
                if result['success']:
                    successful_sequences += 1
                else:
                    failed_sequences += 1
                    sequence_failures.append(result)
            else:
                failed_sequences += 1
                sequence_failures.append({'sequence': 'exception', 'error': str(result), 'success': False})
        correct_sequence_result = next((r for r in startup_sequence_results if r['sequence'] == 'correct_sequence'), None)
        if correct_sequence_result:
            self.assertTrue(correct_sequence_result['success'], f"STARTUP SEQUENCE FAILURE: Even the correct startup sequence failed. Error: {correct_sequence_result['error']}. Factory startup coordination is fundamentally broken.")
        for result in startup_sequence_results:
            if not result['success'] and result['sequence'] != 'correct_sequence':
                error_msg = result['error'].lower()
                crash_indicators = ['segmentation', 'core dumped', 'signal', 'abort']
                has_crash = any((indicator in error_msg for indicator in crash_indicators))
                self.assertFalse(has_crash, f"STARTUP SEQUENCE CRASH: {result['sequence']} caused a crash. Error: {result['error']}. Wrong startup sequences should fail gracefully, not crash.")

    async def test_factory_websocket_bridge_initialization_1011_errors(self):
        """FAILING TEST: Reproduce WebSocket 1011 errors from factory/bridge coordination

        BVJ: All Segments - Ensures WebSocket functionality works for chat
        EXPECTED: FAIL - Factory/WebSocket coordination causes 1011 errors
        ISSUE: Factory initialization timing conflicts with WebSocket handshake
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
            from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
        except ImportError as e:
            self.fail(f'Cannot import required classes: {e}')
        websocket_test_results = []

        async def test_websocket_coordination(test_name: str, coordination_delay: float):
            """Test WebSocket bridge coordination with factory."""
            start_time = time.time()
            try:
                db_session = await self.get_real_database_session()
                redis_client = await self.get_real_redis_client()
                websocket_bridge = AgentWebSocketBridge(database_session_manager=db_session, redis_manager=redis_client)
                self.websocket_bridges.append(websocket_bridge)
                if coordination_delay > 0:
                    await asyncio.sleep(coordination_delay)
                factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge, database_session_manager=db_session, redis_manager=redis_client)
                self.factory_instances.append(factory)
                context = UserExecutionContext(user_id=f'ws_test_user_{test_name}', run_id=f'ws_test_run_{test_name}_{int(time.time() * 1000)}', session_id=f'ws_test_session_{test_name}', request_id=f'ws_test_request_{test_name}')
                self.created_contexts.append(context)
                engine = await factory.create_for_user(context)
                if hasattr(engine, 'websocket_emitter') and engine.websocket_emitter:
                    await engine.websocket_emitter.send_agent_started('Test agent started')
                    await asyncio.sleep(0.1)
                    await engine.websocket_emitter.send_agent_thinking('Test thinking')
                    await asyncio.sleep(0.1)
                    await engine.websocket_emitter.send_agent_completed('Test completed')
                coordination_time = time.time() - start_time
                await factory.cleanup_engine(engine)
                return {'test': test_name, 'success': True, 'coordination_time': coordination_time, 'websocket_events_sent': 3, 'error': None}
            except Exception as e:
                coordination_time = time.time() - start_time
                error_str = str(e).lower()
                is_1011_error = '1011' in error_str or 'websocket' in error_str
                return {'test': test_name, 'success': False, 'coordination_time': coordination_time, 'websocket_events_sent': 0, 'error': str(e), 'is_1011_error': is_1011_error}
        websocket_scenarios = [('immediate_websocket', 0.0), ('delayed_websocket', 0.1), ('slow_websocket_startup', 0.3), ('race_condition_timing', 0.05)]
        tasks = [test_websocket_coordination(test_name, delay) for test_name, delay in websocket_scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_websocket_tests = 0
        failed_websocket_tests = 0
        websocket_1011_errors = []
        for result in results:
            if isinstance(result, dict):
                websocket_test_results.append(result)
                if result['success']:
                    successful_websocket_tests += 1
                else:
                    failed_websocket_tests += 1
                    if result.get('is_1011_error', False):
                        websocket_1011_errors.append(result)
                        self.websocket_errors.append(result)
            else:
                failed_websocket_tests += 1
                error_str = str(result).lower()
                if '1011' in error_str or 'websocket' in error_str:
                    websocket_1011_errors.append({'test': 'exception', 'error': str(result), 'is_1011_error': True})
                    self.websocket_errors.append({'test': 'exception', 'error': str(result)})
        self.assertEqual(len(websocket_1011_errors), 0, f"WEBSOCKET 1011 ERRORS DETECTED: {len(websocket_1011_errors)} tests failed with WebSocket 1011 errors. Errors: {[err['error'] for err in websocket_1011_errors]}. Factory/WebSocket coordination is causing Golden Path blocking issues.")
        self.assertEqual(failed_websocket_tests, 0, f'WEBSOCKET COORDINATION FAILURES: {failed_websocket_tests} out of {len(websocket_scenarios)} WebSocket tests failed. Factory cannot properly coordinate with WebSocket bridge.')

    async def test_factory_agent_execution_chain_coordination(self):
        """FAILING TEST: Reproduce execution chain coordination failures

        BVJ: All Segments - Ensures complete execution chain works for AI responses
        EXPECTED: FAIL - Execution engine -> WebSocket -> agent chain coordination fails
        ISSUE: Chain coordination issues prevent Golden Path completion
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        except ImportError as e:
            self.fail(f'Cannot import required classes: {e}')
        chain_test_results = []

        async def test_execution_chain(chain_name: str, simulate_load: bool):
            """Test complete execution chain coordination."""
            start_time = time.time()
            try:
                db_session = await self.get_real_database_session()
                redis_client = await self.get_real_redis_client()
                websocket_bridge = AgentWebSocketBridge(database_session_manager=db_session, redis_manager=redis_client)
                self.websocket_bridges.append(websocket_bridge)
                factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge, database_session_manager=db_session, redis_manager=redis_client)
                self.factory_instances.append(factory)
                context = UserExecutionContext(user_id=f'chain_test_user_{chain_name}', run_id=f'chain_test_run_{chain_name}_{int(time.time() * 1000)}', session_id=f'chain_test_session_{chain_name}', request_id=f'chain_test_request_{chain_name}')
                self.created_contexts.append(context)
                engine = await factory.create_for_user(context)
                if simulate_load:

                    async def simulate_agent_operation(op_id: int):
                        if hasattr(engine, 'websocket_emitter'):
                            await engine.websocket_emitter.send_agent_started(f'Agent {op_id} started')
                            await asyncio.sleep(0.1)
                            await engine.websocket_emitter.send_tool_executing(f'Agent {op_id} executing')
                            await asyncio.sleep(0.1)
                            await engine.websocket_emitter.send_agent_completed(f'Agent {op_id} completed')
                    load_tasks = [simulate_agent_operation(i) for i in range(3)]
                    await asyncio.gather(*load_tasks)
                elif hasattr(engine, 'websocket_emitter'):
                    await engine.websocket_emitter.send_agent_started('Simple agent started')
                    await engine.websocket_emitter.send_agent_completed('Simple agent completed')
                chain_time = time.time() - start_time
                await factory.cleanup_engine(engine)
                return {'chain': chain_name, 'success': True, 'chain_time': chain_time, 'load_simulation': simulate_load, 'error': None}
            except Exception as e:
                chain_time = time.time() - start_time
                return {'chain': chain_name, 'success': False, 'chain_time': chain_time, 'load_simulation': simulate_load, 'error': str(e)}
        chain_scenarios = [('simple_chain', False), ('loaded_chain', True)]
        tasks = [test_execution_chain(chain_name, simulate_load) for chain_name, simulate_load in chain_scenarios]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        successful_chains = 0
        failed_chains = 0
        chain_failures = []
        for result in results:
            if isinstance(result, dict):
                chain_test_results.append(result)
                if result['success']:
                    successful_chains += 1
                else:
                    failed_chains += 1
                    chain_failures.append(result)
            else:
                failed_chains += 1
                chain_failures.append({'chain': 'exception', 'error': str(result), 'success': False})
        self.assertEqual(failed_chains, 0, f"EXECUTION CHAIN FAILURES: {failed_chains} out of {len(chain_scenarios)} execution chain tests failed. Factory -> Engine -> WebSocket -> Agent chain is broken. Failures: {[f['error'] for f in chain_failures]}")
        for result in chain_test_results:
            if result['success']:
                max_chain_time = 2.0 if not result['load_simulation'] else 5.0
                self.assertLess(result['chain_time'], max_chain_time, f"EXECUTION CHAIN TOO SLOW: {result['chain']} took {result['chain_time']:.2f}s (limit: {max_chain_time}s). Execution chain coordination is too slow for real-time chat.")

    async def test_concurrent_multi_user_factory_operations_isolation_failures(self):
        """FAILING TEST: Reproduce multi-user concurrent operation isolation failures

        BVJ: All Segments - Ensures multi-user isolation for enterprise security
        EXPECTED: FAIL - Concurrent multi-user operations cause isolation failures
        ISSUE: Factory user isolation breaks under concurrent load
        """
        try:
            from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
            from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        except ImportError as e:
            self.fail(f'Cannot import required classes: {e}')
        num_concurrent_users = 5
        concurrent_test_results = []
        db_session = await self.get_real_database_session()
        redis_client = await self.get_real_redis_client()
        websocket_bridge = AgentWebSocketBridge(database_session_manager=db_session, redis_manager=redis_client)
        self.websocket_bridges.append(websocket_bridge)
        factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge, database_session_manager=db_session, redis_manager=redis_client)
        self.factory_instances.append(factory)

        async def test_concurrent_user_operation(user_id: int):
            """Test concurrent operations for a specific user."""
            start_time = time.time()
            try:
                context = UserExecutionContext(user_id=f'concurrent_user_{user_id}', run_id=f'concurrent_run_{user_id}_{int(time.time() * 1000)}', session_id=f'concurrent_session_{user_id}', request_id=f'concurrent_request_{user_id}')
                self.created_contexts.append(context)
                engine = await factory.create_for_user(context)
                user_operations = []
                for op in range(3):
                    if hasattr(engine, 'websocket_emitter'):
                        await engine.websocket_emitter.send_agent_started(f'User {user_id} operation {op}')
                        await asyncio.sleep(0.05)
                        user_operations.append(f'operation_{op}')
                operation_time = time.time() - start_time
                engine_context = engine.get_user_context()
                isolation_valid = engine_context.user_id == f'concurrent_user_{user_id}' and context.user_id in engine_context.user_id
                await factory.cleanup_engine(engine)
                return {'user_id': user_id, 'success': True, 'operation_time': operation_time, 'operations_completed': len(user_operations), 'isolation_valid': isolation_valid, 'error': None}
            except Exception as e:
                operation_time = time.time() - start_time
                return {'user_id': user_id, 'success': False, 'operation_time': operation_time, 'operations_completed': 0, 'isolation_valid': False, 'error': str(e)}
        user_tasks = [test_concurrent_user_operation(user_id) for user_id in range(num_concurrent_users)]
        results = await asyncio.gather(*user_tasks, return_exceptions=True)
        successful_users = 0
        failed_users = 0
        isolation_failures = []
        for result in results:
            if isinstance(result, dict):
                concurrent_test_results.append(result)
                if result['success']:
                    successful_users += 1
                    if not result['isolation_valid']:
                        isolation_failures.append(result)
                else:
                    failed_users += 1
            else:
                failed_users += 1
                concurrent_test_results.append({'user_id': 'exception', 'success': False, 'error': str(result), 'isolation_valid': False})
        self.assertEqual(failed_users, 0, f'CONCURRENT USER OPERATION FAILURES: {failed_users} out of {num_concurrent_users} concurrent user operations failed. Factory cannot handle concurrent multi-user load.')
        self.assertEqual(len(isolation_failures), 0, f"USER ISOLATION FAILURES: {len(isolation_failures)} users had isolation validation failures. Multi-user concurrent operations break user isolation. Failed users: {[f['user_id'] for f in isolation_failures]}")
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')