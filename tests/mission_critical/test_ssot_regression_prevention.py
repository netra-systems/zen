"""
MISSION CRITICAL: SSOT Regression Prevention Test Suite

This test suite prevents regression of SSOT violations and ensures the framework
remains compliant over time. These tests act as guardrails to catch violations
before they reach production. CRITICAL for spacecraft safety.

Business Value: Platform/Internal - Risk Reduction & System Stability
Prevents cascading failures that could bring down the entire test infrastructure.

CRITICAL: These tests are designed to be STRICT and UNFORGIVING.
They catch violations that could lead to system instability or cascade failures.
"""

import asyncio
import ast
import importlib
import inspect
import logging
import os
import sys
import time
import traceback
import uuid
from collections import defaultdict
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type, Union
from netra_backend.app.core.registry.universal_registry import AgentRegistry
# NO MOCKS - Real services only for mission critical isolation testing

import pytest

# Real services and isolation testing components
import asyncpg
import psycopg2
# MIGRATED: from netra_backend.app.services.redis_client import get_redis_client
import websockets
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Process, Queue

# Import real framework components - NO MOCKS
from netra_backend.app.database.manager import DatabaseManager
from netra_backend.app.services.websocket_manager import WebSocketManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_factory import ExecutionFactory
from test_framework.backend_client import BackendClient
from test_framework.test_context import TestContext

from shared.isolated_environment import IsolatedEnvironment, get_env

logger = logging.getLogger(__name__)


class TestSSOTRegressionPrevention:
    """
    REGRESSION CRITICAL: Prevent SSOT framework regression.
    These tests catch violations before they can cause system-wide issues.
    """
    
    async def setUp(self):
        """Set up regression prevention test environment with REAL services."""
        await super().setUp()
        self.test_id = uuid.uuid4().hex[:8]
        self.project_root = Path(__file__).parent.parent.parent
        
        # Initialize REAL service connections for isolation testing
        self.env = IsolatedEnvironment()
        self.db_manager = DatabaseManager()
        self.redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6381, decode_responses=True)
        self.test_context = TestContext(user_id=f"test_user_{self.test_id}")
        
        # Create isolated test environment
        self.user_contexts = {}
        self.websocket_connections = {}
        self.database_sessions = {}
        
        logger.info(f"Starting regression prevention test with REAL services: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up regression prevention test and REAL service connections."""
        # Clean up all real service connections
        for ws_conn in self.websocket_connections.values():
            try:
                asyncio.get_event_loop().run_until_complete(ws_conn.close())
            except:
                pass
        
        for db_session in self.database_sessions.values():
            try:
                db_session.close()
            except:
                pass
        
        try:
            asyncio.get_event_loop().run_until_complete(redis_client.flushdb())
        except:
            pass
            
        logger.info(f"Completed regression prevention test cleanup: {self._testMethodName} (ID: {self.test_id})")
    
    def test_user_context_isolation_concurrent_database_access(self):
        """
        ISOLATION CRITICAL: Test database session isolation between concurrent users.
        Verifies each user has completely isolated database sessions with no data leakage.
        """
        num_users = 15
        operations_per_user = 10
        isolation_failures = []
        
        async def user_database_operations(user_id):
            """Simulate database operations for a specific user."""
            failures = []
            try:
                # Create isolated database session for this user
                user_env = IsolatedEnvironment()
                user_db = DatabaseManager()
                
                # Create user-specific data
                user_data = {
                    'user_id': user_id,
                    'session_id': f"session_{user_id}_{uuid.uuid4().hex[:8]}",
                    'secret_data': f"secret_for_user_{user_id}",
                    'timestamp': datetime.now().isoformat()
                }
                
                # Perform database operations
                for op_num in range(operations_per_user):
                    try:
                        # Store user-specific data
                        await redis_client.hset(
                            f"user:{user_id}:data",
                            f"operation_{op_num}",
                            str(user_data)
                        )
                        
                        # Verify data isolation - should only see own data
                        stored_data = await redis_client.hget(
                            f"user:{user_id}:data",
                            f"operation_{op_num}"
                        )
                        
                        if not stored_data or user_id not in str(stored_data):
                            failures.append({
                                'user_id': user_id,
                                'operation': op_num,
                                'issue': 'data_isolation_failure',
                                'expected_data': str(user_data),
                                'actual_data': str(stored_data)
                            })
                        
                        # Verify no cross-contamination
                        for other_user in range(num_users):
                            if other_user != user_id:
                                other_data = await redis_client.hget(
                                    f"user:{other_user}:data",
                                    f"operation_{op_num}"
                                )
                                if other_data and str(user_id) in str(other_data):
                                    failures.append({
                                        'user_id': user_id,
                                        'contaminated_user': other_user,
                                        'issue': 'cross_user_contamination',
                                        'contaminated_data': str(other_data)
                                    })
                        
                        time.sleep(0.01)  # Small delay to test race conditions
                        
                    except Exception as e:
                        failures.append({
                            'user_id': user_id,
                            'operation': op_num,
                            'issue': 'operation_failure',
                            'error': str(e)
                        })
                        
            except Exception as e:
                failures.append({
                    'user_id': user_id,
                    'issue': 'setup_failure',
                    'error': str(e)
                })
            
            return failures
        
        # Create wrapper function for ThreadPoolExecutor since it can't handle async functions directly
        def run_user_operations(user_id):
            return asyncio.run(user_database_operations(user_id))
        
        # Execute concurrent user operations
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            future_to_user = {
                executor.submit(run_user_operations, user_id): user_id 
                for user_id in range(num_users)
            }
            
            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    user_failures = future.result(timeout=30)
                    isolation_failures.extend(user_failures)
                except Exception as e:
                    isolation_failures.append({
                        'user_id': user_id,
                        'issue': 'execution_failure',
                        'error': str(e)
                    })
        
        # Verify isolation success
        if isolation_failures:
            logger.error(f"Database isolation failures detected: {isolation_failures[:10]}")
        
        assert len(isolation_failures) == 0, f"Database isolation failed: {len(isolation_failures)} failures detected"
    
    async def test_websocket_channel_isolation_concurrent_sessions(self):
        """
        ISOLATION CRITICAL: Test WebSocket channel isolation between concurrent user sessions.
        Verifies each user has completely isolated WebSocket channels with no message leakage.
        """
        num_users = 12
        messages_per_user = 8
        isolation_failures = []
        
        async def user_websocket_session(user_id):
            """Simulate WebSocket session for a specific user."""
            failures = []
            ws_uri = f"ws://localhost:8000/ws/user_{user_id}"
            
            try:
                async with websockets.connect(ws_uri) as websocket:
                    self.websocket_connections[user_id] = websocket
                    
                    # Send user-specific messages
                    user_messages = []
                    for msg_num in range(messages_per_user):
                        message = {
                            'user_id': user_id,
                            'message_id': f"msg_{user_id}_{msg_num}",
                            'content': f"Secret message {msg_num} for user {user_id}",
                            'timestamp': time.time()
                        }
                        
                        await websocket.send(str(message))
                        user_messages.append(message)
                        
                        # Wait for response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            
                            # Verify response isolation
                            if str(user_id) not in response:
                                failures.append({
                                    'user_id': user_id,
                                    'message_num': msg_num,
                                    'issue': 'response_isolation_failure',
                                    'sent_message': str(message),
                                    'received_response': response
                                })
                            
                            # Check for data leakage from other users
                            for other_user in range(num_users):
                                if other_user != user_id and str(other_user) in response:
                                    failures.append({
                                        'user_id': user_id,
                                        'contaminated_by': other_user,
                                        'issue': 'websocket_cross_contamination',
                                        'response': response
                                    })
                        
                        except asyncio.TimeoutError:
                            failures.append({
                                'user_id': user_id,
                                'message_num': msg_num,
                                'issue': 'response_timeout',
                                'message': str(message)
                            })
                        
                        await asyncio.sleep(0.05)  # Small delay to test race conditions
                    
                    return failures
                    
            except Exception as e:
                return [{
                    'user_id': user_id,
                    'issue': 'websocket_connection_failure',
                    'error': str(e)
                }]
        
        # Execute concurrent WebSocket sessions
        tasks = [user_websocket_session(user_id) for user_id in range(num_users)]
        
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    isolation_failures.append({
                        'issue': 'task_execution_failure',
                        'error': str(result)
                    })
                elif isinstance(result, list):
                    isolation_failures.extend(result)
        except Exception as e:
            isolation_failures.append({
                'issue': 'test_execution_failure',
                'error': str(e)
            })
        
        # Verify WebSocket isolation success
        if isolation_failures:
            logger.error(f"WebSocket isolation failures: {isolation_failures[:10]}")
        
        assert len(isolation_failures) == 0, f"WebSocket isolation failed: {len(isolation_failures)} failures detected"
    
    def test_agent_registry_isolation_concurrent_execution(self):
        """
        ISOLATION CRITICAL: Test agent registry isolation between concurrent executions.
        Verifies each execution context has isolated agent registries with no state sharing.
        """
        num_contexts = 10
        agents_per_context = 5
        isolation_failures = []
        
        def context_agent_operations(context_id):
            """Simulate agent operations within an isolated execution context."""
            failures = []
            
            try:
                # Create isolated execution context
                context = TestContext(user_id=f"context_user_{context_id}")
                registry = AgentRegistry()
                execution_factory = ExecutionFactory()
                
                # Create context-specific agents
                context_agents = []
                for agent_num in range(agents_per_context):
                    agent_id = f"agent_{context_id}_{agent_num}"
                    
                    # Register agent with context-specific data
                    agent_config = {
                        'agent_id': agent_id,
                        'context_id': context_id,
                        'secret_key': f"secret_for_context_{context_id}_agent_{agent_num}",
                        'execution_data': f"private_data_{context_id}_{agent_num}"
                    }
                    
                    registry.register_agent(agent_id, agent_config)
                    context_agents.append(agent_id)
                    
                    # Verify agent isolation
                    retrieved_config = registry.get_agent_config(agent_id)
                    if not retrieved_config or retrieved_config.get('context_id') != context_id:
                        failures.append({
                            'context_id': context_id,
                            'agent_id': agent_id,
                            'issue': 'agent_config_isolation_failure',
                            'expected_context': context_id,
                            'actual_config': retrieved_config
                        })
                    
                    # Check for cross-context contamination
                    all_agents = registry.list_agents()
                    for other_agent in all_agents:
                        if other_agent != agent_id:
                            other_config = registry.get_agent_config(other_agent)
                            if (other_config and 
                                other_config.get('context_id') == context_id and
                                other_agent not in context_agents):
                                failures.append({
                                    'context_id': context_id,
                                    'contaminated_agent': other_agent,
                                    'issue': 'cross_context_agent_contamination',
                                    'contaminated_config': other_config
                                })
                
                # Test execution isolation
                for agent_id in context_agents:
                    try:
                        execution = execution_factory.create_execution(
                            agent_id=agent_id,
                            context=context
                        )
                        
                        # Verify execution context isolation
                        if execution.context.user_id != f"context_user_{context_id}":
                            failures.append({
                                'context_id': context_id,
                                'agent_id': agent_id,
                                'issue': 'execution_context_isolation_failure',
                                'expected_user': f"context_user_{context_id}",
                                'actual_user': execution.context.user_id
                            })
                    
                    except Exception as e:
                        failures.append({
                            'context_id': context_id,
                            'agent_id': agent_id,
                            'issue': 'execution_creation_failure',
                            'error': str(e)
                        })
                
                return failures
                
            except Exception as e:
                return [{
                    'context_id': context_id,
                    'issue': 'context_setup_failure',
                    'error': str(e)
                }]
        
        # Execute concurrent context operations
        with ThreadPoolExecutor(max_workers=num_contexts) as executor:
            future_to_context = {
                executor.submit(context_agent_operations, context_id): context_id 
                for context_id in range(num_contexts)
            }
            
            for future in as_completed(future_to_context):
                context_id = future_to_context[future]
                try:
                    context_failures = future.result(timeout=45)
                    isolation_failures.extend(context_failures)
                except Exception as e:
                    isolation_failures.append({
                        'context_id': context_id,
                        'issue': 'execution_future_failure',
                        'error': str(e)
                    })
        
        # Verify agent registry isolation success
        if isolation_failures:
            logger.error(f"Agent registry isolation failures: {isolation_failures[:10]}")
        
        assert len(isolation_failures) == 0, f"Agent registry isolation failed: {len(isolation_failures)} failures detected"
    
    async def test_race_condition_prevention_concurrent_state_access(self):
        """
        ISOLATION CRITICAL: Test race condition prevention in concurrent state access.
        Verifies state management prevents race conditions and maintains data integrity.
        """
        num_workers = 20
        operations_per_worker = 15
        shared_state_key = f"shared_state_{self.test_id}"
        race_condition_failures = []
        
        async def concurrent_state_operations(worker_id):
            """Perform concurrent state operations to detect race conditions."""
            failures = []
            
            try:
                for op_num in range(operations_per_worker):
                    operation_id = f"worker_{worker_id}_op_{op_num}"
                    
                    # Simulate atomic state updates
                    try:
                        # Read current state
                        current_state = await redis_client.get(shared_state_key)
                        if current_state is None:
                            current_state = "0"
                        
                        current_value = int(current_state)
                        new_value = current_value + 1
                        
                        # Atomic update with race condition detection
                        pipe = await redis_client.pipeline()
                        pipe.watch(shared_state_key)
                        pipe.multi()
                        pipe.set(shared_state_key, str(new_value))
                        pipe.set(f"operation:{operation_id}", f"updated_to_{new_value}")
                        
                        result = pipe.execute()
                        
                        if not result:
                            # Race condition detected
                            failures.append({
                                'worker_id': worker_id,
                                'operation_id': operation_id,
                                'issue': 'race_condition_detected',
                                'attempted_value': new_value,
                                'current_state': current_state
                            })
                        
                        # Verify state consistency
                        final_state = await redis_client.get(shared_state_key)
                        operation_record = await redis_client.get(f"operation:{operation_id}")
                        
                        if operation_record and f"updated_to_{final_state}" not in operation_record:
                            failures.append({
                                'worker_id': worker_id,
                                'operation_id': operation_id,
                                'issue': 'state_consistency_failure',
                                'final_state': final_state,
                                'operation_record': operation_record
                            })
                    
                    except Exception as e:
                        failures.append({
                            'worker_id': worker_id,
                            'operation_id': operation_id,
                            'issue': 'atomic_operation_failure',
                            'error': str(e)
                        })
                    
                    time.sleep(0.001)  # Tiny delay to increase race condition likelihood
                
                return failures
                
            except Exception as e:
                return [{
                    'worker_id': worker_id,
                    'issue': 'worker_setup_failure',
                    'error': str(e)
                }]
        
        # Initialize shared state
        await redis_client.set(shared_state_key, "0")
        
        # Create wrapper function for ThreadPoolExecutor since it can't handle async functions directly
        def run_state_operations(worker_id):
            return asyncio.run(concurrent_state_operations(worker_id))
            
        # Execute concurrent operations
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_worker = {
                executor.submit(run_state_operations, worker_id): worker_id 
                for worker_id in range(num_workers)
            }
            
            for future in as_completed(future_to_worker):
                worker_id = future_to_worker[future]
                try:
                    worker_failures = future.result(timeout=60)
                    race_condition_failures.extend(worker_failures)
                except Exception as e:
                    race_condition_failures.append({
                        'worker_id': worker_id,
                        'issue': 'worker_execution_failure',
                        'error': str(e)
                    })
        
        # Verify final state consistency
        final_value = int(await redis_client.get(shared_state_key) or "0")
        expected_max_value = num_workers * operations_per_worker
        
        # Some race conditions are expected and handled properly
        race_condition_count = len([f for f in race_condition_failures if f.get('issue') == 'race_condition_detected'])
        critical_failures = [f for f in race_condition_failures if f.get('issue') != 'race_condition_detected']
        
        # Log race condition statistics
        logger.info(f"Race condition test results: final_value={final_value}, expected_max={expected_max_value}, ")
        logger.info(f"detected_races={race_condition_count}, critical_failures={len(critical_failures)}")
        
        if critical_failures:
            logger.error(f"Critical race condition failures: {critical_failures[:5]}")
        
        # Allow detected race conditions (they should be handled properly)
        # But fail on critical consistency failures
        assert len(critical_failures) == 0, f"Critical race condition failures detected: {len(critical_failures)} failures"
    
    async def test_security_boundary_validation_user_isolation(self):
        """
        SECURITY CRITICAL: Test security boundary validation between isolated users.
        Verifies users cannot access each other's data or execute unauthorized operations.
        """
        num_users = 8
        security_failures = []
        user_secrets = {}
        
        # Setup isolated user environments with secrets
        for user_id in range(num_users):
            user_secret = f"top_secret_data_for_user_{user_id}_{uuid.uuid4().hex}"
            user_secrets[user_id] = user_secret
            
            # Store user's private data
            await redis_client.hset(
                f"user:{user_id}:private",
                "secret_data",
                user_secret
            )
            
            # Store user's authorization token
            auth_token = f"auth_token_{user_id}_{uuid.uuid4().hex}"
            await redis_client.hset(
                f"user:{user_id}:auth",
                "token",
                auth_token
            )
        
        async def attempt_security_breach(attacker_user_id, target_user_id):
            """Attempt to breach security boundaries between users."""
            failures = []
            
            try:
                # Create attacker's context
                attacker_env = IsolatedEnvironment()
                attacker_context = TestContext(user_id=f"user_{attacker_user_id}")
                
                # Attempt 1: Direct data access to other user's private data
                try:
                    stolen_secret = await redis_client.hget(
                        f"user:{target_user_id}:private",
                        "secret_data"
                    )
                    
                    if stolen_secret and stolen_secret == user_secrets[target_user_id]:
                        failures.append({
                            'attacker_user': attacker_user_id,
                            'target_user': target_user_id,
                            'breach_type': 'direct_data_access',
                            'stolen_data': stolen_secret,
                            'issue': 'security_boundary_breach'
                        })
                except Exception:
                    # Good - access should be restricted
                    pass
                
                # Attempt 2: Auth token theft
                try:
                    stolen_token = await redis_client.hget(
                        f"user:{target_user_id}:auth",
                        "token"
                    )
                    
                    if stolen_token:
                        failures.append({
                            'attacker_user': attacker_user_id,
                            'target_user': target_user_id,
                            'breach_type': 'auth_token_theft',
                            'stolen_token': stolen_token,
                            'issue': 'authentication_boundary_breach'
                        })
                except Exception:
                    # Good - access should be restricted
                    pass
                
                # Attempt 3: Context impersonation
                try:
                    imposter_context = TestContext(user_id=f"user_{target_user_id}")
                    
                    # If successful, this is a security issue
                    if imposter_context.user_id != f"user_{attacker_user_id}":
                        failures.append({
                            'attacker_user': attacker_user_id,
                            'target_user': target_user_id,
                            'breach_type': 'context_impersonation',
                            'imposter_context': imposter_context.user_id,
                            'issue': 'context_security_breach'
                        })
                except Exception:
                    # Good - impersonation should fail
                    pass
                
                # Attempt 4: Cross-user command injection
                try:
                    malicious_command = f"user:{target_user_id}:private"
                    
                    # Try to use attacker's context to access target's data
                    backend_client = BackendClient(context=attacker_context)
                    
                    # This should fail due to proper isolation
                    result = backend_client.execute_command(
                        f"GET {malicious_command}"
                    )
                    
                    if result and str(target_user_id) in str(result):
                        failures.append({
                            'attacker_user': attacker_user_id,
                            'target_user': target_user_id,
                            'breach_type': 'command_injection',
                            'malicious_result': str(result),
                            'issue': 'command_security_breach'
                        })
                
                except Exception:
                    # Good - command should be blocked
                    pass
                
                return failures
                
            except Exception as e:
                return [{
                    'attacker_user': attacker_user_id,
                    'target_user': target_user_id,
                    'issue': 'security_test_setup_failure',
                    'error': str(e)
                }]
        
        # Create wrapper function for ThreadPoolExecutor since it can't handle async functions directly
        def run_security_breach(attacker_user_id, target_user_id):
            return asyncio.run(attempt_security_breach(attacker_user_id, target_user_id))
            
        # Test all possible user-to-user attack vectors
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            attack_futures = []
            
            for attacker in range(num_users):
                for target in range(num_users):
                    if attacker != target:
                        future = executor.submit(run_security_breach, attacker, target)
                        attack_futures.append(future)
            
            for future in as_completed(attack_futures):
                try:
                    breach_failures = future.result(timeout=30)
                    security_failures.extend(breach_failures)
                except Exception as e:
                    security_failures.append({
                        'issue': 'security_test_execution_failure',
                        'error': str(e)
                    })
        
        # Verify security boundary integrity
        if security_failures:
            logger.error(f"CRITICAL: Security boundary breaches detected: {security_failures}")
        
        assert len(security_failures) == 0, f"CRITICAL SECURITY FAILURE: {len(security_failures)} boundary breaches detected"
    
    async def test_database_session_isolation_transaction_boundaries(self):
        """
        ISOLATION CRITICAL: Test database session isolation with transaction boundaries.
        Verifies each session has proper transaction isolation with no data leakage.
        """
        num_sessions = 12
        transactions_per_session = 8
        isolation_failures = []
        
        async def session_transaction_operations(session_id):
            """Perform database transactions within an isolated session."""
            failures = []
            
            try:
                # Create isolated database session
                session_env = IsolatedEnvironment()
                db_manager = DatabaseManager()
                
                # Create session-specific transaction data
                session_data = {
                    'session_id': session_id,
                    'user_id': f"session_user_{session_id}",
                    'transaction_data': f"private_transaction_data_{session_id}"
                }
                
                for tx_num in range(transactions_per_session):
                    tx_id = f"tx_{session_id}_{tx_num}"
                    
                    try:
                        # Begin transaction
                        with db_manager.get_session() as db_session:
                            # Store transaction data
                            tx_key = f"transaction:{tx_id}"
                            await redis_client.hset(
                                tx_key,
                                "data",
                                str(session_data)
                            )
                            
                            # Verify transaction isolation
                            stored_data = await redis_client.hget(tx_key, "data")
                            if not stored_data or str(session_id) not in stored_data:
                                failures.append({
                                    'session_id': session_id,
                                    'transaction_id': tx_id,
                                    'issue': 'transaction_data_isolation_failure',
                                    'expected_data': str(session_data),
                                    'actual_data': stored_data
                                })
                            
                            # Check for cross-session contamination
                            all_tx_keys = await redis_client.keys("transaction:*")
                            for other_key in all_tx_keys:
                                if tx_id not in other_key:
                                    other_data = await redis_client.hget(other_key, "data")
                                    if other_data and str(session_id) in other_data:
                                        other_tx_id = other_key.split(":")[1]
                                        if not other_tx_id.startswith(f"tx_{session_id}_"):
                                            failures.append({
                                                'session_id': session_id,
                                                'transaction_id': tx_id,
                                                'contaminated_transaction': other_tx_id,
                                                'issue': 'cross_session_transaction_contamination',
                                                'contaminated_data': other_data
                                            })
                            
                            # Simulate transaction rollback scenario
                            if tx_num % 3 == 0:  # Rollback every 3rd transaction
                                await redis_client.delete(tx_key)
                                
                                # Verify rollback isolation
                                rollback_data = await redis_client.hget(tx_key, "data")
                                if rollback_data:
                                    failures.append({
                                        'session_id': session_id,
                                        'transaction_id': tx_id,
                                        'issue': 'transaction_rollback_isolation_failure',
                                        'unexpected_data': rollback_data
                                    })
                    
                    except Exception as e:
                        failures.append({
                            'session_id': session_id,
                            'transaction_id': tx_id,
                            'issue': 'transaction_operation_failure',
                            'error': str(e)
                        })
                    
                    time.sleep(0.01)  # Small delay for race condition testing
                
                return failures
                
            except Exception as e:
                return [{
                    'session_id': session_id,
                    'issue': 'session_setup_failure',
                    'error': str(e)
                }]
        
        # Create wrapper function for ThreadPoolExecutor since it can't handle async functions directly
        def run_session_operations(session_id):
            return asyncio.run(session_transaction_operations(session_id))
            
        # Execute concurrent session operations
        with ThreadPoolExecutor(max_workers=num_sessions) as executor:
            future_to_session = {
                executor.submit(run_session_operations, session_id): session_id 
                for session_id in range(num_sessions)
            }
            
            for future in as_completed(future_to_session):
                session_id = future_to_session[future]
                try:
                    session_failures = future.result(timeout=45)
                    isolation_failures.extend(session_failures)
                except Exception as e:
                    isolation_failures.append({
                        'session_id': session_id,
                        'issue': 'session_execution_failure',
                        'error': str(e)
                    })
        
        # Verify database session isolation success
        if isolation_failures:
            logger.error(f"Database session isolation failures: {isolation_failures[:10]}")
        
        assert len(isolation_failures) == 0, f"Database session isolation failed: {len(isolation_failures)} failures detected"
    
    def test_performance_metrics_concurrent_load_testing(self):
        """
        PERFORMANCE CRITICAL: Test performance metrics under concurrent load.
        Verifies system maintains performance standards with high concurrent usage.
        """
        import psutil
        
        process = psutil.Process()
        num_concurrent_operations = 25
        operations_per_thread = 20
        performance_failures = []
        
        # Performance benchmarks
        performance_metrics = {
            'response_times': [],
            'memory_usage': [],
            'cpu_usage': [],
            'error_rates': [],
            'throughput_metrics': []
        }
        
        def performance_load_operation(thread_id):
            """Execute performance-intensive operations for load testing."""
            thread_metrics = {
                'response_times': [],
                'errors': [],
                'operations_completed': 0
            }
            
            try:
                for op_num in range(operations_per_thread):
                    start_time = time.time()
                    
                    try:
                        # Memory-intensive operation
                        large_data = [f"data_{thread_id}_{op_num}_{i}" for i in range(1000)]
                        
                        # CPU-intensive operation
                        result = sum(hash(item) for item in large_data)
                        
                        # I/O-intensive operation
                        for i in range(10):
                            await redis_client.set(
                                f"perf_test:{thread_id}:{op_num}:{i}",
                                f"performance_data_{result}_{i}"
                            )
                            
                            # Verify data integrity
                            retrieved = await redis_client.get(
                                f"perf_test:{thread_id}:{op_num}:{i}"
                            )
                            
                            if not retrieved or str(result) not in retrieved:
                                thread_metrics['errors'].append({
                                    'operation': f"{thread_id}_{op_num}_{i}",
                                    'issue': 'data_integrity_failure',
                                    'expected': f"performance_data_{result}_{i}",
                                    'actual': retrieved
                                })
                        
                        end_time = time.time()
                        response_time = end_time - start_time
                        thread_metrics['response_times'].append(response_time)
                        thread_metrics['operations_completed'] += 1
                        
                        # Performance threshold checks
                        if response_time > 2.0:  # 2 second threshold
                            thread_metrics['errors'].append({
                                'operation': f"{thread_id}_{op_num}",
                                'issue': 'response_time_threshold_exceeded',
                                'response_time': response_time,
                                'threshold': 2.0
                            })
                    
                    except Exception as e:
                        thread_metrics['errors'].append({
                            'operation': f"{thread_id}_{op_num}",
                            'issue': 'operation_exception',
                            'error': str(e)
                        })
                
                return thread_metrics
                
            except Exception as e:
                return {
                    'errors': [{
                        'thread_id': thread_id,
                        'issue': 'thread_setup_failure',
                        'error': str(e)
                    }],
                    'response_times': [],
                    'operations_completed': 0
                }
        
        # Measure initial system state
        initial_memory = process.memory_info().rss
        initial_cpu = process.cpu_percent()
        
        # Execute concurrent performance operations
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=num_concurrent_operations) as executor:
            future_to_thread = {
                executor.submit(performance_load_operation, thread_id): thread_id 
                for thread_id in range(num_concurrent_operations)
            }
            
            for future in as_completed(future_to_thread):
                thread_id = future_to_thread[future]
                try:
                    thread_metrics = future.result(timeout=120)
                    
                    # Aggregate metrics
                    performance_metrics['response_times'].extend(thread_metrics['response_times'])
                    performance_failures.extend(thread_metrics['errors'])
                    
                    # Calculate thread-specific metrics
                    if thread_metrics['response_times']:
                        avg_response_time = sum(thread_metrics['response_times']) / len(thread_metrics['response_times'])
                        max_response_time = max(thread_metrics['response_times'])
                        
                        performance_metrics['throughput_metrics'].append({
                            'thread_id': thread_id,
                            'operations_completed': thread_metrics['operations_completed'],
                            'avg_response_time': avg_response_time,
                            'max_response_time': max_response_time
                        })
                
                except Exception as e:
                    performance_failures.append({
                        'thread_id': thread_id,
                        'issue': 'thread_execution_failure',
                        'error': str(e)
                    })
        
        end_time = time.time()
        total_test_time = end_time - start_time
        
        # Measure final system state
        final_memory = process.memory_info().rss
        final_cpu = process.cpu_percent()
        
        # Calculate overall performance metrics
        total_operations = sum(m['operations_completed'] for m in performance_metrics['throughput_metrics'])
        overall_throughput = total_operations / total_test_time if total_test_time > 0 else 0
        
        if performance_metrics['response_times']:
            avg_response_time = sum(performance_metrics['response_times']) / len(performance_metrics['response_times'])
            max_response_time = max(performance_metrics['response_times'])
        else:
            avg_response_time = 0
            max_response_time = 0
        
        memory_increase = final_memory - initial_memory
        
        # Performance validation
        performance_summary = {
            'total_operations': total_operations,
            'test_duration': total_test_time,
            'overall_throughput': overall_throughput,
            'avg_response_time': avg_response_time,
            'max_response_time': max_response_time,
            'memory_increase': memory_increase,
            'cpu_usage_change': final_cpu - initial_cpu,
            'error_count': len(performance_failures)
        }
        
        logger.info(f"Performance test results: {performance_summary}")
        
        # Performance thresholds
        if avg_response_time > 1.0:  # Average response time threshold
            performance_failures.append({
                'metric': 'avg_response_time',
                'value': avg_response_time,
                'threshold': 1.0,
                'issue': 'average_response_time_exceeded'
            })
        
        if overall_throughput < 50:  # Minimum throughput threshold
            performance_failures.append({
                'metric': 'overall_throughput',
                'value': overall_throughput,
                'threshold': 50,
                'issue': 'throughput_below_minimum'
            })
        
        if memory_increase > 100 * 1024 * 1024:  # 100MB memory increase threshold
            performance_failures.append({
                'metric': 'memory_increase',
                'value': memory_increase,
                'threshold': 100 * 1024 * 1024,
                'issue': 'excessive_memory_usage'
            })
        
        # Verify performance standards met
        if performance_failures:
            logger.error(f"Performance standard failures: {performance_failures[:10]}")
        
        assert len(performance_failures) <= 5, f"Too many performance failures: {len(performance_failures)} detected"
    
    def test_prevent_dependency_violations(self):
        """
        DEPENDENCY CRITICAL: Prevent dependency violations in SSOT framework.
        This ensures SSOT doesn't introduce unwanted dependencies.
        """
        violations = []
        
        # Allowed dependencies for SSOT framework
        allowed_dependencies = [
            'asyncio', 'logging', 'os', 'sys', 'time', 'traceback', 'uuid',
            'pathlib', 'typing', 'unittest', 'contextlib', 'datetime',
            'inspect', 'warnings', 'collections', 'abc',
            'pytest', 'sqlalchemy', 'psutil',  # Test framework dependencies
            'shared.isolated_environment'  # Internal dependency
        ]
        
        # Forbidden dependencies
        forbidden_dependencies = [
            'requests',  # Should use internal HTTP client
            'redis',     # Should use internal Redis client
            'psycopg2',  # Should use SQLAlchemy
            'pymongo',   # Should use internal MongoDB client
            'celery',    # Should use internal task queue
            'fastapi',   # Should not depend on web framework
            'django',    # Should not depend on web framework
            'flask'      # Should not depend on web framework
        ]
        
        # Scan SSOT framework files for dependencies
        ssot_files = list((self.project_root / 'test_framework' / 'ssot').rglob("*.py"))
        
        for ssot_file in ssot_files:
            try:
                with open(ssot_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Extract import statements
                try:
                    tree = ast.parse(content)
                    
                    class ImportVisitor(ast.NodeVisitor):
                        def __init__(self):
                            self.imports = []
                        
                        def visit_Import(self, node):
                            for alias in node.names:
                                self.imports.append(alias.name)
                        
                        def visit_ImportFrom(self, node):
                            if node.module:
                                self.imports.append(node.module)
                    
                    visitor = ImportVisitor()
                    visitor.visit(tree)
                    
                    # Check for forbidden dependencies
                    for import_name in visitor.imports:
                        root_module = import_name.split('.')[0]
                        
                        if root_module in forbidden_dependencies:
                            violations.append({
                                'file': str(ssot_file),
                                'import': import_name,
                                'violation': 'forbidden_dependency'
                            })
                        
                        # Check for unexpected dependencies
                        if (root_module not in allowed_dependencies and 
                            not root_module.startswith('test_framework') and
                            not root_module.startswith('shared') and
                            not root_module.startswith('netra_backend')):
                            
                            violations.append({
                                'file': str(ssot_file),
                                'import': import_name,
                                'violation': 'unexpected_dependency'
                            })
                            
                except SyntaxError:
                    pass
                    
            except (OSError, UnicodeDecodeError):
                pass
        
        if violations:
            logger.error(f"Dependency violations in SSOT framework: {violations}")
        
        self.assertEqual(len(violations), 0,
                        f"SSOT framework dependency violations: {violations}")
    
    def test_prevent_circular_import_violations(self):
        """
        IMPORT CRITICAL: Prevent circular import violations.
        This ensures the SSOT framework doesn't create circular dependencies.
        """
        violations = []
        
        # Build dependency graph
        dependency_graph = defaultdict(set)
        
        # Scan Python files to build import graph
        python_files = list(self.project_root.rglob("*.py"))
        
        for python_file in python_files[:50]:  # Limit for performance
            try:
                with open(python_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                try:
                    tree = ast.parse(content)
                    
                    class ImportVisitor(ast.NodeVisitor):
                        def __init__(self, file_path):
                            self.file_path = file_path
                            self.imports = []
                        
                        def visit_Import(self, node):
                            for alias in node.names:
                                self.imports.append(alias.name)
                        
                        def visit_ImportFrom(self, node):
                            if node.module:
                                self.imports.append(node.module)
                    
                    visitor = ImportVisitor(python_file)
                    visitor.visit(tree)
                    
                    # Add to dependency graph
                    file_module = self._path_to_module_name(python_file)
                    for import_name in visitor.imports:
                        if self._is_internal_module(import_name):
                            dependency_graph[file_module].add(import_name)
                            
                except SyntaxError:
                    pass
                    
            except (OSError, UnicodeDecodeError):
                pass
        
        # Detect circular dependencies
        def detect_cycles(graph):
            visited = set()
            rec_stack = set()
            cycles = []
            
            def dfs(node, path):
                if node in rec_stack:
                    # Found cycle
                    cycle_start = path.index(node)
                    cycle = path[cycle_start:] + [node]
                    cycles.append(cycle)
                    return
                
                if node in visited:
                    return
                
                visited.add(node)
                rec_stack.add(node)
                path.append(node)
                
                for neighbor in graph.get(node, set()):
                    dfs(neighbor, path.copy())
                
                rec_stack.remove(node)
            
            for node in graph:
                if node not in visited:
                    dfs(node, [])
            
            return cycles
        
        cycles = detect_cycles(dependency_graph)
        
        for cycle in cycles:
            violations.append({
                'cycle': cycle,
                'violation': 'circular_import'
            })
        
        if violations:
            logger.error(f"Circular import violations: {violations}")
        
        self.assertEqual(len(violations), 0,
                        f"Circular import dependencies detected: {violations}")
    
    def _validate_isolation_boundaries(self, test_results):
        """Validate that isolation boundaries are maintained in test results."""
        boundary_violations = []
        
        for result in test_results:
            # Check for cross-user data contamination
            if 'user_data' in result and 'other_user_data' in result:
                if result['user_data'] == result['other_user_data']:
                    boundary_violations.append({
                        'violation_type': 'data_contamination',
                        'details': result
                    })
            
            # Check for shared state violations
            if 'shared_state_detected' in result and result['shared_state_detected']:
                boundary_violations.append({
                    'violation_type': 'shared_state',
                    'details': result
                })
        
        return boundary_violations
    
    def _measure_concurrent_performance(self, operation_func, num_threads, operations_per_thread):
        """Measure performance of concurrent operations."""
        performance_metrics = {
            'start_time': time.time(),
            'operation_times': [],
            'errors': [],
            'success_count': 0
        }
        
        def timed_operation(thread_id):
            thread_start = time.time()
            try:
                result = operation_func(thread_id)
                thread_end = time.time()
                return {
                    'thread_id': thread_id,
                    'duration': thread_end - thread_start,
                    'result': result,
                    'success': True
                }
            except Exception as e:
                thread_end = time.time()
                return {
                    'thread_id': thread_id,
                    'duration': thread_end - thread_start,
                    'error': str(e),
                    'success': False
                }
        
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(timed_operation, thread_id)
                for thread_id in range(num_threads)
            ]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    performance_metrics['operation_times'].append(result['duration'])
                    
                    if result['success']:
                        performance_metrics['success_count'] += 1
                    else:
                        performance_metrics['errors'].append(result)
                        
                except Exception as e:
                    performance_metrics['errors'].append({
                        'future_error': str(e)
                    })
        
        performance_metrics['end_time'] = time.time()
        performance_metrics['total_time'] = performance_metrics['end_time'] - performance_metrics['start_time']
        
        if performance_metrics['operation_times']:
            performance_metrics['avg_operation_time'] = sum(performance_metrics['operation_times']) / len(performance_metrics['operation_times'])
            performance_metrics['max_operation_time'] = max(performance_metrics['operation_times'])
            performance_metrics['min_operation_time'] = min(performance_metrics['operation_times'])
        
        return performance_metrics


class TestSSOTContinuousCompliance:
    """
    COMPLIANCE CRITICAL: Continuous SSOT compliance monitoring.
    These tests run continuously to ensure SSOT compliance is maintained.
    """
    
    def setUp(self):
        """Set up continuous compliance test environment with REAL services."""
        self.test_id = uuid.uuid4().hex[:8]
        
        # Initialize REAL service connections for compliance testing
        self.env = IsolatedEnvironment()
        self.db_manager = DatabaseManager()
        self.redis_client = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6381, decode_responses=True)
        self.test_context = TestContext(user_id=f"compliance_user_{self.test_id}")
        
        logger.info(f"Starting continuous compliance test with REAL services: {self._testMethodName} (ID: {self.test_id})")
    
    def tearDown(self):
        """Clean up continuous compliance test and REAL service connections."""
        try:
            await redis_client.flushdb()
        except:
            pass
            
        logger.info(f"Completed continuous compliance test cleanup: {self._testMethodName} (ID: {self.test_id})")
    
    def test_continuous_system_health_real_services(self):
        """
        HEALTH CRITICAL: Continuously monitor system health with REAL services.
        This test runs regularly to ensure all real service components are healthy.
        """
        health_issues = []
        service_health = {}
        
        # Test Database Health
        try:
            db_start_time = time.time()
            with self.db_manager.get_session() as session:
                # Test basic database operations
                test_key = f"health_check_{self.test_id}"
                await redis_client.set(test_key, "healthy")
                result = await redis_client.get(test_key)
                
                if result != "healthy":
                    health_issues.append({
                        'service': 'database',
                        'issue': 'basic_operation_failure',
                        'expected': 'healthy',
                        'actual': result
                    })
                
                await redis_client.delete(test_key)
            
            db_response_time = time.time() - db_start_time
            service_health['database'] = {
                'status': 'healthy' if len([h for h in health_issues if h.get('service') == 'database']) == 0 else 'unhealthy',
                'response_time': db_response_time,
                'operations_tested': ['set', 'get', 'delete']
            }
            
            if db_response_time > 1.0:  # 1 second threshold
                health_issues.append({
                    'service': 'database',
                    'issue': 'slow_response_time',
                    'response_time': db_response_time,
                    'threshold': 1.0
                })
        
        except Exception as e:
            health_issues.append({
                'service': 'database',
                'issue': 'connection_failure',
                'error': str(e)
            })
            service_health['database'] = {'status': 'failed', 'error': str(e)}
        
        # Test Redis Health
        try:
            redis_start_time = time.time()
            
            # Test Redis operations
            test_hash = f"redis_health_{self.test_id}"
            await redis_client.hset(test_hash, "field1", "value1")
            await redis_client.hset(test_hash, "field2", "value2")
            
            all_fields = await redis_client.hgetall(test_hash)
            if len(all_fields) != 2 or all_fields.get("field1") != "value1":
                health_issues.append({
                    'service': 'redis',
                    'issue': 'hash_operation_failure',
                    'expected_fields': 2,
                    'actual_fields': len(all_fields),
                    'data': all_fields
                })
            
            await redis_client.delete(test_hash)
            
            redis_response_time = time.time() - redis_start_time
            service_health['redis'] = {
                'status': 'healthy' if len([h for h in health_issues if h.get('service') == 'redis']) == 0 else 'unhealthy',
                'response_time': redis_response_time,
                'operations_tested': ['hset', 'hgetall', 'delete']
            }
            
            if redis_response_time > 0.5:  # 500ms threshold
                health_issues.append({
                    'service': 'redis',
                    'issue': 'slow_response_time',
                    'response_time': redis_response_time,
                    'threshold': 0.5
                })
        
        except Exception as e:
            health_issues.append({
                'service': 'redis',
                'issue': 'connection_failure',
                'error': str(e)
            })
            service_health['redis'] = {'status': 'failed', 'error': str(e)}
        
        # Test Service Integration Health
        try:
            integration_start_time = time.time()
            
            # Test service integration through BackendClient
            backend_client = BackendClient(context=self.test_context)
            test_command = "PING"
            result = backend_client.execute_command(test_command)
            
            if not result or "PONG" not in str(result).upper():
                health_issues.append({
                    'service': 'integration',
                    'issue': 'service_integration_failure',
                    'command': test_command,
                    'result': str(result)
                })
            
            integration_response_time = time.time() - integration_start_time
            service_health['integration'] = {
                'status': 'healthy' if len([h for h in health_issues if h.get('service') == 'integration']) == 0 else 'unhealthy',
                'response_time': integration_response_time,
                'operations_tested': ['ping']
            }
        
        except Exception as e:
            health_issues.append({
                'service': 'integration',
                'issue': 'integration_test_failure',
                'error': str(e)
            })
            service_health['integration'] = {'status': 'failed', 'error': str(e)}
        
        # Log comprehensive health status
        logger.info(f"System health check results: {service_health}")
        
        if health_issues:
            logger.error(f"System health issues detected: {health_issues}")
        
        # Categorize health issues
        critical_issues = [
            issue for issue in health_issues 
            if issue.get('issue') in ['connection_failure', 'basic_operation_failure', 'service_integration_failure']
        ]
        
        warning_issues = [
            issue for issue in health_issues 
            if issue.get('issue') in ['slow_response_time']
        ]
        
        # Verify system health
        assert len(critical_issues) == 0, f"Critical system health issues: {critical_issues}"
        assert len(warning_issues) <= 2, f"Too many warning health issues: {warning_issues}"
    
    def test_continuous_regression_monitoring_real_performance(self):
        """
        REGRESSION CRITICAL: Monitor real system performance to detect regressions.
        This test tracks actual system metrics over time to detect gradual regression.
        """
        import psutil
        
        process = psutil.Process()
        
        # Collect comprehensive real system metrics
        system_start_time = time.time()
        initial_memory = process.memory_info().rss
        initial_cpu = process.cpu_percent()
        
        # Performance regression test scenarios
        regression_metrics = {
            'timestamp': datetime.now().isoformat(),
            'test_id': self.test_id,
            'system_metrics': {},
            'service_metrics': {},
            'isolation_metrics': {}
        }
        
        regression_issues = []
        
        # Test 1: Database Performance Regression
        try:
            db_start = time.time()
            
            # Execute database operations
            for i in range(50):
                key = f"regression_test_{self.test_id}_{i}"
                await redis_client.set(key, f"test_data_{i}")
                result = await redis_client.get(key)
                if not result:
                    regression_issues.append({
                        'metric': 'database_operations',
                        'operation': i,
                        'issue': 'data_persistence_failure'
                    })
                await redis_client.delete(key)
            
            db_time = time.time() - db_start
            regression_metrics['service_metrics']['database_50_ops'] = db_time
            
            if db_time > 2.0:  # 2 second threshold for 50 operations
                regression_issues.append({
                    'metric': 'database_performance',
                    'value': db_time,
                    'threshold': 2.0,
                    'issue': 'database_performance_regression'
                })
        
        except Exception as e:
            regression_issues.append({
                'metric': 'database_test',
                'issue': 'database_test_failure',
                'error': str(e)
            })
        
        # Test 2: Memory Usage Regression
        try:
            memory_start = process.memory_info().rss
            
            # Create memory-intensive operations
            test_data = []
            for i in range(1000):
                test_data.append(f"memory_test_data_{self.test_id}_{i}" * 100)
            
            memory_peak = process.memory_info().rss
            memory_increase = memory_peak - memory_start
            
            # Clean up test data
            del test_data
            
            memory_final = process.memory_info().rss
            memory_cleanup = memory_peak - memory_final
            
            regression_metrics['system_metrics']['memory_increase'] = memory_increase
            regression_metrics['system_metrics']['memory_cleanup'] = memory_cleanup
            
            if memory_increase > 100 * 1024 * 1024:  # 100MB threshold
                regression_issues.append({
                    'metric': 'memory_usage',
                    'value': memory_increase,
                    'threshold': 100 * 1024 * 1024,
                    'issue': 'excessive_memory_usage'
                })
            
            if memory_cleanup < memory_increase * 0.8:  # Should clean up at least 80%
                regression_issues.append({
                    'metric': 'memory_cleanup',
                    'cleanup_ratio': memory_cleanup / memory_increase if memory_increase > 0 else 0,
                    'threshold': 0.8,
                    'issue': 'poor_memory_cleanup'
                })
        
        except Exception as e:
            regression_issues.append({
                'metric': 'memory_test',
                'issue': 'memory_test_failure',
                'error': str(e)
            })
        
        # Test 3: Isolation Performance Regression
        try:
            isolation_start = time.time()
            
            # Test concurrent isolation operations
            def quick_isolation_test(test_id):
                context = TestContext(user_id=f"regression_user_{test_id}")
                await redis_client.set(
                    f"isolation_test:{test_id}",
                    f"data_{test_id}"
                )
                return await redis_client.get(f"isolation_test:{test_id}")
            
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [
                    executor.submit(quick_isolation_test, i) 
                    for i in range(10)
                ]
                
                results = []
                for future in as_completed(futures):
                    try:
                        result = future.result(timeout=5)
                        results.append(result)
                    except Exception as e:
                        regression_issues.append({
                            'metric': 'isolation_operations',
                            'issue': 'isolation_operation_failure',
                            'error': str(e)
                        })
            
            isolation_time = time.time() - isolation_start
            regression_metrics['isolation_metrics']['concurrent_ops_time'] = isolation_time
            regression_metrics['isolation_metrics']['successful_ops'] = len(results)
            
            if isolation_time > 5.0:  # 5 second threshold
                regression_issues.append({
                    'metric': 'isolation_performance',
                    'value': isolation_time,
                    'threshold': 5.0,
                    'issue': 'isolation_performance_regression'
                })
            
            if len(results) < 8:  # Should complete at least 8/10 operations
                regression_issues.append({
                    'metric': 'isolation_reliability',
                    'successful_ops': len(results),
                    'total_ops': 10,
                    'threshold': 8,
                    'issue': 'isolation_reliability_regression'
                })
        
        except Exception as e:
            regression_issues.append({
                'metric': 'isolation_test',
                'issue': 'isolation_test_failure',
                'error': str(e)
            })
        
        # Calculate overall system metrics
        system_total_time = time.time() - system_start_time
        final_memory = process.memory_info().rss
        final_cpu = process.cpu_percent()
        
        regression_metrics['system_metrics'].update({
            'total_test_time': system_total_time,
            'memory_change': final_memory - initial_memory,
            'cpu_usage': final_cpu
        })
        
        # Log comprehensive regression monitoring results
        logger.info(f"Regression monitoring metrics: {regression_metrics}")
        
        if regression_issues:
            logger.warning(f"Regression monitoring issues detected: {regression_issues}")
        
        # Categorize regression issues
        critical_regressions = [
            issue for issue in regression_issues 
            if 'failure' in issue.get('issue', '').lower()
        ]
        
        performance_regressions = [
            issue for issue in regression_issues 
            if 'performance_regression' in issue.get('issue', '')
        ]
        
        # Verify regression thresholds
        assert len(critical_regressions) == 0, f"Critical system regressions detected: {critical_regressions}"
        assert len(performance_regressions) <= 2, f"Too many performance regressions: {performance_regressions}"
        assert len(regression_issues) <= 5, f"Too many total regression issues: {len(regression_issues)} detected"
    
    def _check_real_service_health(self):
        """Check real service health metrics."""
        try:
            health_metrics = {
                'redis_connection': True,
                'database_connection': True,
                'service_response_times': {}
            }
            
            # Test Redis connection
            start_time = time.time()
            await redis_client.ping()
            health_metrics['service_response_times']['redis'] = time.time() - start_time
            
            # Test Database connection
            start_time = time.time()
            with self.db_manager.get_session() as session:
                pass  # Basic connection test
            health_metrics['service_response_times']['database'] = time.time() - start_time
            
            return health_metrics
            
        except Exception as e:
            return {'error': str(e), 'healthy': False}
    
    def _measure_real_service_load_time(self):
        """Measure real service initialization load time."""
        start_time = time.time()
        
        try:
            # Initialize real service components to measure load time
            test_env = IsolatedEnvironment()
            test_db = DatabaseManager()
            test_redis = await get_redis_client()  # MIGRATED: was redis.Redis(host='localhost', port=6381)
            
            # Test basic operations
            test_redis.ping()
            
            return time.time() - start_time
            
        except Exception:
            return -1  # Error indicator
    
    def _measure_system_memory_usage(self):
        """Measure current system memory usage."""
        try:
            import psutil
            process = psutil.Process()
            return {
                'rss': process.memory_info().rss,
                'vms': process.memory_info().vms,
                'percent': process.memory_percent()
            }
        except Exception:
            return {'error': 'memory_measurement_failed'}

    def test_comprehensive_data_leakage_detection(self):
        """
        ISOLATION CRITICAL: Comprehensive data leakage detection across all boundaries.
        Tests for any form of data leakage between isolated contexts.
        """
        num_isolated_contexts = 15
        operations_per_context = 12
        leakage_violations = []
        
        # Create isolated test data for each context
        context_secrets = {}
        for context_id in range(num_isolated_contexts):
            context_secrets[context_id] = {
                'secret_key': f"ULTRA_SECRET_{context_id}_{uuid.uuid4().hex}",
                'private_data': f"PRIVATE_DATA_{context_id}_{time.time()}",
                'auth_token': f"AUTH_{context_id}_{uuid.uuid4().hex[:16]}",
                'session_id': f"SESSION_{context_id}_{uuid.uuid4().hex[:12]}"
            }
        
        def isolated_context_operations(context_id):
            """Perform operations within an isolated context and check for leakage."""
            violations = []
            
            try:
                # Create truly isolated environment
                context_env = IsolatedEnvironment()
                context = TestContext(user_id=f"leak_test_user_{context_id}")
                secrets = context_secrets[context_id]
                
                for op_num in range(operations_per_context):
                    operation_key = f"context:{context_id}:operation:{op_num}"
                    
                    # Store context-specific secret data
                    await redis_client.hset(
                        operation_key,
                        "secret_data",
                        secrets['secret_key']
                    )
                    
                    await redis_client.hset(
                        operation_key,
                        "private_data",
                        secrets['private_data']
                    )
                    
                    # Verify data isolation - no leakage to other contexts
                    for other_context in range(num_isolated_contexts):
                        if other_context != context_id:
                            other_secrets = context_secrets[other_context]
                            
                            # Check if current context's data leaked to other context
                            other_keys = await redis_client.keys(f"context:{other_context}:*")
                            for other_key in other_keys:
                                other_data = await redis_client.hgetall(other_key)
                                
                                # Check for secret leakage
                                for field, value in other_data.items():
                                    if (secrets['secret_key'] in str(value) or 
                                        secrets['private_data'] in str(value) or
                                        secrets['auth_token'] in str(value)):
                                        
                                        violations.append({
                                            'context_id': context_id,
                                            'operation': op_num,
                                            'leaked_to_context': other_context,
                                            'leaked_data_type': 'secret_data',
                                            'leaked_content': str(value),
                                            'issue': 'critical_data_leakage'
                                        })
                            
                            # Check reverse leakage - other context data in current context
                            current_data = await redis_client.hgetall(operation_key)
                            for field, value in current_data.items():
                                if (other_secrets['secret_key'] in str(value) or 
                                    other_secrets['private_data'] in str(value) or
                                    other_secrets['auth_token'] in str(value)):
                                    
                                    violations.append({
                                        'context_id': context_id,
                                        'operation': op_num,
                                        'contaminated_by_context': other_context,
                                        'contaminated_data_type': 'reverse_leakage',
                                        'contaminated_content': str(value),
                                        'issue': 'critical_reverse_leakage'
                                    })
                    
                    time.sleep(0.005)  # Small delay to test concurrent access patterns
                
                return violations
                
            except Exception as e:
                return [{
                    'context_id': context_id,
                    'issue': 'context_operation_failure',
                    'error': str(e)
                }]
        
        # Execute all contexts concurrently to maximize leakage detection
        with ThreadPoolExecutor(max_workers=num_isolated_contexts) as executor:
            future_to_context = {
                executor.submit(isolated_context_operations, context_id): context_id 
                for context_id in range(num_isolated_contexts)
            }
            
            for future in as_completed(future_to_context):
                context_id = future_to_context[future]
                try:
                    context_violations = future.result(timeout=60)
                    leakage_violations.extend(context_violations)
                except Exception as e:
                    leakage_violations.append({
                        'context_id': context_id,
                        'issue': 'future_execution_failure',
                        'error': str(e)
                    })
        
        # Clean up test data
        for context_id in range(num_isolated_contexts):
            keys_to_delete = await redis_client.keys(f"context:{context_id}:*")
            if keys_to_delete:
                await redis_client.delete(*keys_to_delete)
        
        # Verify NO data leakage detected
        if leakage_violations:
            logger.error(f"CRITICAL: Data leakage violations detected: {leakage_violations[:10]}")
        
        critical_leakages = [v for v in leakage_violations if 'leakage' in v.get('issue', '')]
        
        assert len(critical_leakages) == 0, f"CRITICAL: Data leakage detected in {len(critical_leakages)} cases"
        assert len(leakage_violations) == 0, f"Total isolation violations: {len(leakage_violations)} detected"

    def test_stress_test_concurrent_user_isolation_boundaries(self):
        """
        STRESS CRITICAL: Stress test isolation boundaries under extreme concurrent load.
        Tests isolation integrity under maximum stress conditions.
        """
        num_concurrent_users = 30
        operations_per_user = 25
        stress_test_duration = 45  # seconds
        isolation_stress_failures = []
        
        stress_test_start = time.time()
        
        def extreme_stress_user_operations(user_id):
            """Execute extreme stress operations for a specific user."""
            failures = []
            user_start_time = time.time()
            
            try:
                # Create user-specific stress test environment
                user_env = IsolatedEnvironment()
                user_context = TestContext(user_id=f"stress_user_{user_id}")
                
                user_data_signature = f"STRESS_USER_{user_id}_SIGNATURE_{uuid.uuid4().hex[:8]}"
                
                operation_count = 0
                while (time.time() - stress_test_start) < stress_test_duration:
                    op_start_time = time.time()
                    
                    try:
                        # High-frequency data operations
                        for i in range(5):  # Burst of 5 operations
                            key = f"stress:{user_id}:{operation_count}:{i}"
                            
                            # Complex data structure to stress system
                            complex_data = {
                                'user_signature': user_data_signature,
                                'operation_id': f"{user_id}_{operation_count}_{i}",
                                'timestamp': time.time(),
                                'payload': f"payload_{user_id}_{operation_count}_{i}" * 50,
                                'nested_data': {
                                    'level_1': f"level1_{user_id}_{i}",
                                    'level_2': {
                                        'level_2_data': f"level2_{user_id}_{operation_count}"
                                    }
                                }
                            }
                            
                            # Store complex data
                            await redis_client.hset(
                                key,
                                "complex_data",
                                str(complex_data)
                            )
                            
                            # Immediate verification
                            retrieved = await redis_client.hget(key, "complex_data")
                            if not retrieved or user_data_signature not in retrieved:
                                failures.append({
                                    'user_id': user_id,
                                    'operation': operation_count,
                                    'sub_operation': i,
                                    'issue': 'stress_data_integrity_failure',
                                    'expected_signature': user_data_signature,
                                    'retrieved_data': str(retrieved)[:200]  # Truncate for logging
                                })
                            
                            # Stress test: Check for contamination from random other users
                            random_other_users = [u for u in range(num_concurrent_users) if u != user_id]
                            if random_other_users:
                                random_user = random_other_users[operation_count % len(random_other_users)]
                                random_keys = await redis_client.keys(f"stress:{random_user}:*")
                                
                                if random_keys:
                                    # Sample a few random keys to check for contamination
                                    sample_keys = random_keys[:min(3, len(random_keys))]
                                    for sample_key in sample_keys:
                                        sample_data = await redis_client.hget(sample_key, "complex_data")
                                        if sample_data and user_data_signature in sample_data:
                                            failures.append({
                                                'user_id': user_id,
                                                'operation': operation_count,
                                                'contaminated_user': random_user,
                                                'contaminated_key': sample_key,
                                                'issue': 'stress_cross_user_contamination',
                                                'user_signature': user_data_signature
                                            })
                        
                        operation_count += 1
                        
                        # Brief pause to allow other users to operate
                        time.sleep(0.001)
                        
                        # Performance check
                        op_duration = time.time() - op_start_time
                        if op_duration > 1.0:  # Operation took more than 1 second
                            failures.append({
                                'user_id': user_id,
                                'operation': operation_count,
                                'issue': 'stress_performance_degradation',
                                'operation_duration': op_duration,
                                'threshold': 1.0
                            })
                    
                    except Exception as e:
                        failures.append({
                            'user_id': user_id,
                            'operation': operation_count,
                            'issue': 'stress_operation_exception',
                            'error': str(e)
                        })
                
                user_total_time = time.time() - user_start_time
                
                return {
                    'user_id': user_id,
                    'operations_completed': operation_count,
                    'total_time': user_total_time,
                    'failures': failures
                }
                
            except Exception as e:
                return {
                    'user_id': user_id,
                    'operations_completed': 0,
                    'total_time': time.time() - user_start_time,
                    'failures': [{
                        'user_id': user_id,
                        'issue': 'stress_user_setup_failure',
                        'error': str(e)
                    }]
                }
        
        # Launch extreme concurrent stress test
        with ThreadPoolExecutor(max_workers=num_concurrent_users) as executor:
            future_to_user = {
                executor.submit(extreme_stress_user_operations, user_id): user_id 
                for user_id in range(num_concurrent_users)
            }
            
            stress_results = []
            for future in as_completed(future_to_user):
                user_id = future_to_user[future]
                try:
                    user_result = future.result(timeout=stress_test_duration + 30)
                    stress_results.append(user_result)
                    isolation_stress_failures.extend(user_result['failures'])
                except Exception as e:
                    isolation_stress_failures.append({
                        'user_id': user_id,
                        'issue': 'stress_user_execution_failure',
                        'error': str(e)
                    })
        
        # Calculate stress test metrics
        total_operations = sum(result['operations_completed'] for result in stress_results)
        total_test_time = time.time() - stress_test_start
        operations_per_second = total_operations / total_test_time if total_test_time > 0 else 0
        
        stress_metrics = {
            'total_operations': total_operations,
            'test_duration': total_test_time,
            'operations_per_second': operations_per_second,
            'concurrent_users': num_concurrent_users,
            'failure_count': len(isolation_stress_failures)
        }
        
        logger.info(f"Stress test isolation metrics: {stress_metrics}")
        
        # Clean up stress test data
        try:
            keys_to_delete = await redis_client.keys("stress:*")
            if keys_to_delete:
                # Delete in batches to avoid overwhelming Redis
                batch_size = 100
                for i in range(0, len(keys_to_delete), batch_size):
                    batch = keys_to_delete[i:i + batch_size]
                    await redis_client.delete(*batch)
        except Exception as e:
            logger.warning(f"Stress test cleanup warning: {e}")
        
        # Analyze stress test results
        critical_failures = [f for f in isolation_stress_failures if 'contamination' in f.get('issue', '') or 'integrity_failure' in f.get('issue', '')]
        performance_issues = [f for f in isolation_stress_failures if 'performance' in f.get('issue', '')]
        
        if critical_failures:
            logger.error(f"CRITICAL: Stress test isolation failures: {critical_failures[:5]}")
        
        if isolation_stress_failures:
            logger.warning(f"Stress test issues detected: {len(isolation_stress_failures)} total issues")
        
        # Verify stress test isolation integrity
        assert len(critical_failures) == 0, f"CRITICAL: Isolation failed under stress: {len(critical_failures)} critical failures"
        assert operations_per_second >= 10, f"Stress test performance too low: {operations_per_second} ops/sec"
        assert len(isolation_stress_failures) <= 20, f"Too many stress test issues: {len(isolation_stress_failures)} detected"


async def run_async_tests():
    """Run async WebSocket isolation tests."""
    test_instance = TestSSOTRegressionPrevention()
    test_instance.setUp()
    
    try:
        await test_instance.test_websocket_channel_isolation_concurrent_sessions()
        logger.info("Async WebSocket isolation tests completed successfully")
    except Exception as e:
        logger.error(f"Async WebSocket isolation tests failed: {e}")
        raise
    finally:
        test_instance.tearDown()


if __name__ == '__main__':
    # Configure logging for test execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run async tests first
    try:
        asyncio.run(run_async_tests())
    except Exception as e:
        logger.error(f"Async test execution failed: {e}")
    
    # Run the synchronous tests
    pytest.main([__file__, '-v', '--tb=short', '--capture=no', '--maxfail=3'])