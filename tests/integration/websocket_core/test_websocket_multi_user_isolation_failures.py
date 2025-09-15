"""Integration Tests: WebSocket Multi-User Isolation Failures - Issue #965

PURPOSE: Test multi-user isolation failures caused by WebSocket Manager fragmentation

BUSINESS IMPACT:
- Priority: P0 CRITICAL
- Impact: $500K+ ARR regulatory compliance (HIPAA, SOC2, SEC)
- Root Cause: Multiple WebSocket Manager implementations break user context isolation
- Security Risk: Cross-user data contamination in concurrent sessions

TEST OBJECTIVES:
1. Reproduce user context contamination with fragmented WebSocket managers
2. Validate session isolation failures across different manager instances
3. Test concurrent user WebSocket state sharing violations
4. Demonstrate memory state pollution between user sessions
5. Prove enterprise security compliance failures

EXPECTED BEHAVIOR:
- Tests should FAIL with current fragmentation (user isolation violations)
- Tests should PASS after SSOT consolidation ensuring proper isolation

This test suite requires integration-level testing focusing on concurrent execution.
"""

import sys
import os
import asyncio
import json
import time
import threading
from typing import Dict, List, Set, Any, Optional, Tuple
from unittest.mock import Mock, patch, AsyncMock
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import unittest
from test_framework.ssot.base_test_case import SSotAsyncTestCase

@pytest.mark.integration
class TestWebSocketMultiUserIsolationFailures(SSotAsyncTestCase, unittest.TestCase):
    """Test multi-user isolation failures caused by WebSocket Manager fragmentation."""

    def setUp(self):
        """Set up test environment for multi-user isolation testing."""
        super().setUp()
        self.test_users = []
        self.mock_websockets = []
        self.cleanup_tasks = []

    def tearDown(self):
        """Clean up test resources."""
        super().tearDown()
        # Clean up mock WebSockets
        for mock_ws in self.mock_websockets:
            if hasattr(mock_ws, 'close'):
                try:
                    asyncio.run(mock_ws.close())
                except:
                    pass

        # Clean up any background tasks
        for task in self.cleanup_tasks:
            if not task.done():
                task.cancel()

    def create_test_users(self, count: int) -> List[Dict[str, Any]]:
        """Create test user contexts for isolation testing."""
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        users = []
        for i in range(count):
            user_id = f'isolation_test_user_{i}'
            user_context = UserExecutionContext(
                user_id=user_id,
                thread_id=f'thread_{i}',
                run_id=f'run_{i}',
                request_id=f'req_{i}'
            )

            # Add sensitive test data to verify isolation
            sensitive_data = {
                'user_id': user_id,
                'ssn': f'123-45-{6789 + i}',
                'account_balance': f'${100000 + i * 50000}',
                'secret_token': f'secret_token_user_{i}_{time.time()}',
                'personal_data': f'confidential_data_for_user_{i}'
            }

            users.append({
                'context': user_context,
                'sensitive_data': sensitive_data,
                'expected_isolation': True
            })

        self.test_users = users
        return users

    async def test_concurrent_user_websocket_state_contamination(self):
        """
        STATE CONTAMINATION TEST: Validate user state contamination in concurrent WebSocket sessions.

        EXPECTED TO FAIL: Fragmented managers share state between users
        EXPECTED TO PASS: SSOT manager maintains isolated state per user
        """
        users = self.create_test_users(5)
        managers_by_user = {}
        websockets_by_user = {}

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create WebSocket managers for each user
            for user in users:
                user_context = user['context']

                # Create manager for this user
                manager = await get_websocket_manager(user_context=user_context)
                managers_by_user[user_context.user_id] = manager

                # Create mock WebSocket with state tracking
                mock_ws = AsyncMock()
                mock_ws.send = AsyncMock()
                mock_ws.user_data = {}  # Track data sent to this WebSocket
                mock_ws.state_history = []  # Track state changes

                # Override send to capture user-specific data
                original_send = mock_ws.send

                async def state_tracking_send(data, user_id=user_context.user_id):
                    timestamp = time.time()
                    try:
                        if isinstance(data, str):
                            parsed_data = json.loads(data)
                            if not hasattr(mock_ws, 'user_data'):
                                mock_ws.user_data = {}
                            mock_ws.user_data[timestamp] = {
                                'user_id': user_id,
                                'data': parsed_data,
                                'timestamp': timestamp
                            }
                            mock_ws.state_history.append({
                                'action': 'send',
                                'timestamp': timestamp,
                                'data_type': type(parsed_data).__name__,
                                'user_id': user_id
                            })
                    except json.JSONDecodeError:
                        pass
                    return await original_send(data)

                mock_ws.send = state_tracking_send
                websockets_by_user[user_context.user_id] = mock_ws
                self.mock_websockets.append(mock_ws)

                # Connect WebSocket to manager
                if hasattr(manager, '_connections'):
                    manager._connections[user_context.user_id] = mock_ws
                elif hasattr(manager, 'connections'):
                    manager.connections[user_context.user_id] = mock_ws

            # Send sensitive data through each user's manager concurrently
            async def send_user_data(user):
                user_context = user['context']
                sensitive_data = user['sensitive_data']
                manager = managers_by_user[user_context.user_id]

                for i in range(3):  # Send multiple events per user
                    await manager.send_agent_event(
                        user_id=user_context.user_id,
                        event_type='agent_thinking',
                        data={
                            'user_sensitive_info': sensitive_data,
                            'iteration': i,
                            'private_message': f'Private message for {user_context.user_id} only'
                        }
                    )
                    await asyncio.sleep(0.001)  # Small delay to test concurrency

            # Execute all user data sends concurrently
            tasks = [send_user_data(user) for user in users]
            await asyncio.gather(*tasks)

            # Analyze state isolation
            self.logger.info("Analyzing user state isolation...")

            cross_contamination_detected = []

            for user in users:
                user_id = user['context'].user_id
                user_websocket = websockets_by_user[user_id]
                user_sensitive_data = user['sensitive_data']

                # Check if this user's WebSocket received data meant for other users
                if hasattr(user_websocket, 'user_data'):
                    for timestamp, data_entry in user_websocket.user_data.items():
                        data_content = data_entry.get('data', {})

                        if 'user_sensitive_info' in data_content:
                            received_sensitive = data_content['user_sensitive_info']
                            expected_user_id = received_sensitive.get('user_id')

                            if expected_user_id != user_id:
                                cross_contamination_detected.append({
                                    'receiving_user': user_id,
                                    'data_for_user': expected_user_id,
                                    'contaminated_data': received_sensitive,
                                    'timestamp': timestamp
                                })

            # Verify no cross-contamination occurred
            if cross_contamination_detected:
                self.logger.error(f"CROSS-USER CONTAMINATION DETECTED: {len(cross_contamination_detected)} violations")
                for contamination in cross_contamination_detected:
                    self.logger.error(f"  User {contamination['receiving_user']} received data for {contamination['data_for_user']}")

            self.assertEqual(
                len(cross_contamination_detected), 0,
                f"USER ISOLATION FAILURE: {len(cross_contamination_detected)} cross-user data contamination events detected. "
                f"WebSocket Manager fragmentation allows sensitive data to leak between users. "
                f"Contamination details: {cross_contamination_detected}. "
                f"This violates HIPAA, SOC2, and SEC compliance requirements."
            )

            # Additional check: Verify managers are truly isolated instances
            manager_ids = set()
            for user_id, manager in managers_by_user.items():
                manager_id = id(manager)
                if manager_id in manager_ids:
                    self.fail(f"MANAGER SHARING VIOLATION: Manager instance {manager_id} shared between users")
                manager_ids.add(manager_id)

        except Exception as e:
            self.fail(f"MULTI-USER ISOLATION FAILURE: Cannot test isolation due to manager fragmentation: {e}")

    async def test_websocket_connection_pool_isolation_violations(self):
        """
        CONNECTION POOL TEST: Validate WebSocket connection pool isolation between users.

        EXPECTED TO FAIL: Fragmented managers share connection pools
        EXPECTED TO PASS: SSOT manager maintains isolated connection pools
        """
        users = self.create_test_users(3)
        connection_pools = {}

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create managers and examine their connection pools
            for user in users:
                user_context = user['context']
                manager = await get_websocket_manager(user_context=user_context)

                # Extract connection pool reference
                connection_pool = None
                if hasattr(manager, '_connections'):
                    connection_pool = manager._connections
                elif hasattr(manager, 'connections'):
                    connection_pool = manager.connections
                elif hasattr(manager, '_websocket_connections'):
                    connection_pool = manager._websocket_connections

                if connection_pool is not None:
                    pool_id = id(connection_pool)
                    if pool_id not in connection_pools:
                        connection_pools[pool_id] = []
                    connection_pools[pool_id].append(user_context.user_id)

                self.logger.info(f"User {user_context.user_id}: Manager {type(manager).__name__}, Pool ID {pool_id}")

            # Analyze connection pool sharing
            self.logger.info(f"Connection pool analysis: {len(connection_pools)} unique pools")

            shared_pools = []
            for pool_id, users_sharing_pool in connection_pools.items():
                if len(users_sharing_pool) > 1:
                    shared_pools.append({
                        'pool_id': pool_id,
                        'sharing_users': users_sharing_pool
                    })

            if shared_pools:
                self.logger.error(f"CONNECTION POOL SHARING DETECTED: {len(shared_pools)} shared pools")
                for shared_pool in shared_pools:
                    self.logger.error(f"  Pool {shared_pool['pool_id']} shared by: {shared_pool['sharing_users']}")

            # Verify each user has isolated connection pool
            self.assertEqual(
                len(shared_pools), 0,
                f"CONNECTION POOL SHARING VIOLATION: {len(shared_pools)} connection pools shared between users. "
                f"Shared pools: {shared_pools}. "
                f"WebSocket Manager fragmentation breaks connection isolation, "
                f"allowing users to potentially access each other's WebSocket connections."
            )

        except Exception as e:
            self.fail(f"CONNECTION POOL ISOLATION FAILURE: Cannot test pool isolation due to manager fragmentation: {e}")

    async def test_memory_leak_from_fragmented_manager_instances(self):
        """
        MEMORY LEAK TEST: Validate memory leaks from fragmented manager instances.

        EXPECTED TO FAIL: Multiple manager instances cause memory leaks
        EXPECTED TO PASS: SSOT manager properly manages memory
        """
        import gc
        import psutil
        import os

        # Measure initial memory
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        managers_created = []

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            # Create many manager instances (simulating fragmentation load)
            for i in range(20):
                from netra_backend.app.services.user_execution_context import UserExecutionContext

                user_context = UserExecutionContext(
                    user_id=f'memory_test_user_{i}',
                    thread_id=f'memory_thread_{i}',
                    run_id=f'memory_run_{i}',
                    request_id=f'memory_req_{i}'
                )

                manager = await get_websocket_manager(user_context=user_context)
                managers_created.append(manager)

                # Simulate some activity
                mock_ws = AsyncMock()
                if hasattr(manager, '_connections'):
                    manager._connections[user_context.user_id] = mock_ws

            # Measure memory after manager creation
            mid_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = mid_memory - initial_memory

            self.logger.info(f"Memory usage: Initial {initial_memory:.1f}MB, After managers {mid_memory:.1f}MB (+{memory_increase:.1f}MB)")

            # Clear references to managers
            managers_created.clear()
            gc.collect()

            # Measure memory after cleanup
            await asyncio.sleep(0.1)  # Allow cleanup time
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_leaked = final_memory - initial_memory

            self.logger.info(f"Memory after cleanup: {final_memory:.1f}MB (leaked: {memory_leaked:.1f}MB)")

            # Verify reasonable memory usage
            # Allow some memory increase but flag excessive leaks
            max_acceptable_leak = 50.0  # MB

            self.assertLess(
                memory_leaked, max_acceptable_leak,
                f"MEMORY LEAK DETECTED: {memory_leaked:.1f}MB leaked after creating/destroying 20 WebSocket managers. "
                f"Maximum acceptable leak: {max_acceptable_leak}MB. "
                f"WebSocket Manager fragmentation may cause memory leaks in production. "
                f"This affects system stability and scalability."
            )

        except Exception as e:
            self.fail(f"MEMORY LEAK TEST FAILURE: Cannot test memory usage due to manager fragmentation: {e}")

@pytest.mark.integration
class TestWebSocketEnterpriseComplianceFailures(SSotAsyncTestCase, unittest.TestCase):
    """Test enterprise compliance failures caused by WebSocket Manager fragmentation."""

    async def test_hipaa_compliance_violation_simulation(self):
        """
        HIPAA COMPLIANCE TEST: Simulate HIPAA violations due to user data mixing.

        EXPECTED TO FAIL: Fragmented managers mix healthcare data between patients
        EXPECTED TO PASS: SSOT manager maintains strict patient data isolation
        """
        # Create healthcare user scenarios
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        healthcare_users = [
            {
                'context': UserExecutionContext(
                    user_id='patient_001',
                    thread_id='healthcare_thread_1',
                    run_id='medical_run_1',
                    request_id='hipaa_req_1'
                ),
                'phi_data': {
                    'patient_id': 'PATIENT_001',
                    'diagnosis': 'Diabetes Type 2',
                    'ssn': '123-45-6789',
                    'dob': '1985-03-15',
                    'treatment': 'Insulin therapy'
                }
            },
            {
                'context': UserExecutionContext(
                    user_id='patient_002',
                    thread_id='healthcare_thread_2',
                    run_id='medical_run_2',
                    request_id='hipaa_req_2'
                ),
                'phi_data': {
                    'patient_id': 'PATIENT_002',
                    'diagnosis': 'Hypertension',
                    'ssn': '987-65-4321',
                    'dob': '1978-11-22',
                    'treatment': 'Blood pressure medication'
                }
            }
        ]

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            phi_tracking = {}  # Track Protected Health Information

            for healthcare_user in healthcare_users:
                user_context = healthcare_user['context']
                phi_data = healthcare_user['phi_data']

                manager = await get_websocket_manager(user_context=user_context)

                # Mock WebSocket with PHI tracking
                mock_ws = AsyncMock()
                mock_ws.received_phi = []

                async def phi_tracking_send(data):
                    try:
                        if isinstance(data, str):
                            parsed_data = json.loads(data)
                            # Check for PHI in data
                            for patient_info in healthcare_users:
                                patient_phi = patient_info['phi_data']
                                for phi_key, phi_value in patient_phi.items():
                                    if str(phi_value) in str(data):
                                        mock_ws.received_phi.append({
                                            'phi_type': phi_key,
                                            'phi_value': phi_value,
                                            'intended_patient': patient_info['context'].user_id,
                                            'receiving_patient': user_context.user_id,
                                            'timestamp': time.time()
                                        })
                    except:
                        pass

                mock_ws.send = phi_tracking_send

                if hasattr(manager, '_connections'):
                    manager._connections[user_context.user_id] = mock_ws

                phi_tracking[user_context.user_id] = mock_ws

                # Send PHI data through manager
                await manager.send_agent_event(
                    user_id=user_context.user_id,
                    event_type='agent_thinking',
                    data={
                        'medical_analysis': phi_data,
                        'confidential': True,
                        'hipaa_protected': True
                    }
                )

            # Analyze PHI violations
            hipaa_violations = []

            for user_id, mock_ws in phi_tracking.items():
                for phi_event in mock_ws.received_phi:
                    if phi_event['intended_patient'] != phi_event['receiving_patient']:
                        hipaa_violations.append(phi_event)

            if hipaa_violations:
                self.logger.error(f"HIPAA VIOLATIONS DETECTED: {len(hipaa_violations)} PHI leaks")
                for violation in hipaa_violations:
                    self.logger.error(f"  Patient {violation['receiving_patient']} received PHI for {violation['intended_patient']}")

            self.assertEqual(
                len(hipaa_violations), 0,
                f"HIPAA COMPLIANCE FAILURE: {len(hipaa_violations)} Protected Health Information violations detected. "
                f"WebSocket Manager fragmentation allows patient data to leak between users. "
                f"Violations: {hipaa_violations}. "
                f"This violates HIPAA regulations and exposes organization to $1.5M+ fines."
            )

        except Exception as e:
            self.fail(f"HIPAA COMPLIANCE TEST FAILURE: Cannot test compliance due to manager fragmentation: {e}")

    async def test_financial_data_isolation_sec_compliance(self):
        """
        SEC COMPLIANCE TEST: Validate financial data isolation per SEC requirements.

        EXPECTED TO FAIL: Fragmented managers leak financial data between users
        EXPECTED TO PASS: SSOT manager maintains SEC-compliant data isolation
        """
        from netra_backend.app.services.user_execution_context import UserExecutionContext

        # Create financial user scenarios
        financial_users = [
            {
                'context': UserExecutionContext(
                    user_id='trader_001',
                    thread_id='trading_thread_1',
                    run_id='trading_run_1',
                    request_id='sec_req_1'
                ),
                'financial_data': {
                    'account_id': 'ACC_001',
                    'portfolio_value': '$2,500,000',
                    'insider_positions': ['AAPL', 'MSFT'],
                    'trading_strategy': 'High-frequency arbitrage',
                    'sec_regulated': True
                }
            },
            {
                'context': UserExecutionContext(
                    user_id='trader_002',
                    thread_id='trading_thread_2',
                    run_id='trading_run_2',
                    request_id='sec_req_2'
                ),
                'financial_data': {
                    'account_id': 'ACC_002',
                    'portfolio_value': '$5,800,000',
                    'insider_positions': ['GOOGL', 'AMZN'],
                    'trading_strategy': 'Value investing',
                    'sec_regulated': True
                }
            }
        ]

        try:
            from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

            financial_tracking = {}

            for financial_user in financial_users:
                user_context = financial_user['context']
                financial_data = financial_user['financial_data']

                manager = await get_websocket_manager(user_context=user_context)

                # Mock WebSocket with financial data tracking
                mock_ws = AsyncMock()
                mock_ws.financial_exposures = []

                async def financial_tracking_send(data):
                    try:
                        if isinstance(data, str):
                            parsed_data = json.loads(data)
                            # Check for financial data cross-contamination
                            for other_user in financial_users:
                                other_data = other_user['financial_data']
                                if other_user['context'].user_id != user_context.user_id:
                                    for key, value in other_data.items():
                                        if str(value) in str(data):
                                            mock_ws.financial_exposures.append({
                                                'exposed_data': f'{key}: {value}',
                                                'data_owner': other_user['context'].user_id,
                                                'exposed_to': user_context.user_id,
                                                'timestamp': time.time()
                                            })
                    except:
                        pass

                mock_ws.send = financial_tracking_send

                if hasattr(manager, '_connections'):
                    manager._connections[user_context.user_id] = mock_ws

                financial_tracking[user_context.user_id] = mock_ws

                # Send financial data through manager
                await manager.send_agent_event(
                    user_id=user_context.user_id,
                    event_type='agent_completed',
                    data={
                        'trading_analysis': financial_data,
                        'sec_confidential': True,
                        'material_information': True
                    }
                )

            # Analyze financial data exposures
            sec_violations = []

            for user_id, mock_ws in financial_tracking.items():
                sec_violations.extend(mock_ws.financial_exposures)

            if sec_violations:
                self.logger.error(f"SEC VIOLATIONS DETECTED: {len(sec_violations)} financial data exposures")
                for violation in sec_violations:
                    self.logger.error(f"  {violation['exposed_to']} exposed to {violation['data_owner']}'s data: {violation['exposed_data']}")

            self.assertEqual(
                len(sec_violations), 0,
                f"SEC COMPLIANCE FAILURE: {len(sec_violations)} financial data exposure violations detected. "
                f"WebSocket Manager fragmentation allows material financial information to leak between users. "
                f"Violations: {sec_violations}. "
                f"This violates SEC regulations on material information handling and insider trading protections."
            )

        except Exception as e:
            self.fail(f"SEC COMPLIANCE TEST FAILURE: Cannot test compliance due to manager fragmentation: {e}")

if __name__ == '__main__':
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category integration')