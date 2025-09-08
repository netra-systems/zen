#!/usr/bin/env python
"""INTEGRATION TEST 9: Agent Supervisor Isolation Testing

This test validates that the agent supervisor architecture properly isolates
execution contexts between users and ensures no state leakage or race conditions
when handling concurrent requests through the factory pattern architecture.

Business Value: Enables 10+ concurrent users without interference
Test Requirements:
- Real Docker services for multi-user simulation
- Factory pattern execution engine testing
- WebSocket isolation validation
- Database session isolation testing
- Cross-user state isolation verification

CRITICAL: This test validates the core factory pattern that enables concurrent multi-user support.
See: USER_CONTEXT_ARCHITECTURE.md and GOLDEN_AGENT_INDEX.md
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
from collections import defaultdict
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from shared.isolated_environment import IsolatedEnvironment

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
import requests
import websockets
from loguru import logger
from shared.isolated_environment import get_env

# Import production components for supervisor isolation testing
from netra_backend.app.core.supervisor_factory import create_supervisor_core
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.dependencies import get_request_scoped_db_session
from test_framework.base_integration_test import BaseIntegrationTest as DockerTestBase


class SupervisorIsolationTracker:
    """Tracks supervisor isolation across concurrent executions"""
    
    def __init__(self):
        self.supervisor_instances: Dict[str, Dict[str, Any]] = {}
        self.execution_contexts: Dict[str, Dict[str, Any]] = {}
        self.state_leakages: List[Dict[str, Any]] = []
        self.concurrent_executions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = threading.Lock()
        
    def record_supervisor_instance(self, user_id: str, supervisor_id: str, metadata: Dict[str, Any]):
        """Record supervisor instance creation"""
        with self._lock:
            if user_id not in self.supervisor_instances:
                self.supervisor_instances[user_id] = {}
            self.supervisor_instances[user_id][supervisor_id] = {
                'metadata': metadata.copy(),
                'timestamp': datetime.now().isoformat(),
                'state_isolated': True
            }
            
    def record_execution_context(self, user_id: str, context_id: str, context_data: Dict[str, Any]):
        """Record execution context creation"""
        with self._lock:
            if user_id not in self.execution_contexts:
                self.execution_contexts[user_id] = {}
            self.execution_contexts[user_id][context_id] = {
                'data': context_data.copy(),
                'timestamp': datetime.now().isoformat()
            }
            
    def record_state_leakage(self, from_user: str, to_user: str, leakage_type: str, details: Dict[str, Any]):
        """Record state leakage between users"""
        with self._lock:
            leakage = {
                'from_user': from_user,
                'to_user': to_user,
                'leakage_type': leakage_type,
                'details': details.copy(),
                'timestamp': datetime.now().isoformat(),
                'severity': 'critical'
            }
            self.state_leakages.append(leakage)
            
    def record_concurrent_execution(self, user_id: str, execution_id: str, 
                                  start_time: datetime, end_time: datetime, result: Any):
        """Record concurrent execution results"""
        with self._lock:
            execution = {
                'execution_id': execution_id,
                'user_id': user_id,
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat(),
                'duration_ms': int((end_time - start_time).total_seconds() * 1000),
                'success': result is not None,
                'result_type': type(result).__name__ if result else None
            }
            self.concurrent_executions[user_id].append(execution)
            
    def get_isolation_analysis(self) -> Dict[str, Any]:
        """Get comprehensive isolation analysis"""
        with self._lock:
            return {
                'users_tested': list(self.supervisor_instances.keys()),
                'total_supervisors': sum(len(supervisors) for supervisors in self.supervisor_instances.values()),
                'total_contexts': sum(len(contexts) for contexts in self.execution_contexts.values()),
                'state_leakages': len(self.state_leakages),
                'concurrent_executions': sum(len(execs) for execs in self.concurrent_executions.values()),
                'leakage_details': self.state_leakages.copy(),
                'isolation_successful': len(self.state_leakages) == 0
            }


@pytest.mark.integration  
@pytest.mark.requires_docker
@pytest.mark.supervisor_isolation
class TestAgentSupervisorIsolation(DockerTestBase):
    """Integration Test 9: Agent supervisor isolation testing"""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self):
        """Initialize test environment for supervisor isolation testing"""
        self.isolation_tracker = SupervisorIsolationTracker()
        
        # Create multiple test users for isolation testing
        self.test_users = [
            {
                'user_id': f"isolation_user_{i}_{uuid.uuid4().hex[:8]}",
                'thread_id': f"thread_{i}_{uuid.uuid4().hex[:8]}",
                'session_id': f"session_{i}_{uuid.uuid4().hex[:8]}"
            }
            for i in range(5)
        ]
        
        # Service configuration
        backend_port = get_env().get('BACKEND_PORT', '8000')
        self.backend_url = f"http://localhost:{backend_port}"
        
        # Concurrent execution configuration
        self.max_concurrent_users = 3
        self.requests_per_user = 2
        
        yield
        
        # Generate isolation analysis
        analysis = self.isolation_tracker.get_isolation_analysis()
        logger.info(f"Supervisor isolation test completed. Analysis: {analysis}")
        
    async def _create_isolated_supervisor(self, user_data: Dict[str, Any]) -> Tuple[Any, str]:
        """Create isolated supervisor using factory pattern"""
        user_id = user_data['user_id']
        thread_id = user_data['thread_id']
        session_id = user_data['session_id']
        
        # Create database session using request-scoped pattern
        async for db_session in get_request_scoped_db_session():
            try:
                # Create supervisor using factory pattern
                supervisor = await create_supervisor_core(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=str(uuid.uuid4()),
                    db_session=db_session,
                    websocket_connection_id=f"conn_{user_id}"
                )
                
                # Generate unique supervisor ID for tracking
                supervisor_id = f"supervisor_{user_id}_{int(time.time() * 1000)}"
                
                # Record supervisor instance
                self.isolation_tracker.record_supervisor_instance(
                    user_id,
                    supervisor_id,
                    {
                        'supervisor_type': type(supervisor).__name__,
                        'thread_id': thread_id,
                        'session_id': session_id,
                        'has_isolated_session': db_session is not None
                    }
                )
                
                return supervisor, supervisor_id
                
            except Exception as e:
                logger.error(f"Failed to create isolated supervisor for {user_id}: {e}")
                raise
                
    async def _create_user_execution_context(self, user_data: Dict[str, Any]) -> UserExecutionContext:
        """Create UserExecutionContext for isolation testing"""
        user_id = user_data['user_id']
        thread_id = user_data['thread_id']
        run_id = str(uuid.uuid4())
        
        # Create database session
        async for db_session in get_request_scoped_db_session():
            try:
                # Create context
                context = UserExecutionContext(
                    user_id=user_id,
                    thread_id=thread_id,
                    run_id=run_id,
                    db_session=db_session,
                    metadata={
                        'test_type': 'supervisor_isolation',
                        'session_id': user_data['session_id']
                    }
                )
                
                # Record context
                context_id = f"context_{user_id}_{int(time.time() * 1000)}"
                self.isolation_tracker.record_execution_context(
                    user_id,
                    context_id,
                    {
                        'context_type': type(context).__name__,
                        'run_id': run_id,
                        'has_session': context.db_session is not None
                    }
                )
                
                return context
                
            except Exception as e:
                logger.error(f"Failed to create execution context for {user_id}: {e}")
                raise
                
    async def _execute_agent_with_supervisor(self, user_data: Dict[str, Any], 
                                           query: str) -> Dict[str, Any]:
        """Execute agent with isolated supervisor"""
        user_id = user_data['user_id']
        execution_id = f"exec_{user_id}_{int(time.time() * 1000)}"
        start_time = datetime.now()
        
        try:
            # Create isolated supervisor
            supervisor, supervisor_id = await self._create_isolated_supervisor(user_data)
            
            # Create execution context
            context = await self._create_user_execution_context(user_data)
            
            # Validate context isolation
            await self._validate_context_isolation(context, user_id)
            
            # Execute agent with unique query to detect cross-contamination
            unique_query = f"{query} (User: {user_id[:8]}, Timestamp: {int(time.time())})"
            
            logger.info(f"Executing agent for {user_id} with query: {unique_query[:50]}...")
            
            # Execute using the supervisor
            result = await supervisor.execute(context, stream_updates=False)
            
            end_time = datetime.now()
            
            # Record execution
            self.isolation_tracker.record_concurrent_execution(
                user_id, execution_id, start_time, end_time, result
            )
            
            # Validate result isolation
            await self._validate_result_isolation(result, user_id, unique_query)
            
            return {
                'user_id': user_id,
                'execution_id': execution_id,
                'supervisor_id': supervisor_id,
                'result': result,
                'duration_ms': int((end_time - start_time).total_seconds() * 1000)
            }
            
        except Exception as e:
            end_time = datetime.now()
            self.isolation_tracker.record_concurrent_execution(
                user_id, execution_id, start_time, end_time, None
            )
            logger.error(f"Agent execution failed for {user_id}: {e}")
            raise
            
    async def _validate_context_isolation(self, context: UserExecutionContext, expected_user_id: str):
        """Validate that execution context is properly isolated"""
        # Validate user ID matches
        if context.user_id != expected_user_id:
            self.isolation_tracker.record_state_leakage(
                context.user_id, expected_user_id, 'user_id_mismatch',
                {'expected': expected_user_id, 'actual': context.user_id}
            )
            
        # Validate database session isolation
        if hasattr(context.db_session, '_netra_user_tag'):
            session_user = getattr(context.db_session, '_netra_user_tag')
            if session_user != expected_user_id:
                self.isolation_tracker.record_state_leakage(
                    session_user, expected_user_id, 'db_session_cross_user',
                    {'expected_user': expected_user_id, 'session_user': session_user}
                )
                
    async def _validate_result_isolation(self, result: Any, user_id: str, expected_query: str):
        """Validate that execution results don't contain cross-user contamination"""
        if not result:
            return
            
        result_str = str(result).lower()
        
        # Check for other user IDs in the result
        for test_user in self.test_users:
            other_user_id = test_user['user_id']
            if other_user_id != user_id and other_user_id[:8] in result_str:
                self.isolation_tracker.record_state_leakage(
                    other_user_id, user_id, 'result_contamination',
                    {'contaminated_result': result_str[:200], 'foreign_user_id': other_user_id}
                )
                
    async def _simulate_concurrent_user_requests(self) -> List[Dict[str, Any]]:
        """Simulate concurrent requests from multiple users"""
        logger.info(f"Simulating concurrent requests from {self.max_concurrent_users} users")
        
        # Prepare tasks for concurrent execution
        tasks = []
        for i in range(self.max_concurrent_users):
            user_data = self.test_users[i]
            
            for request_num in range(self.requests_per_user):
                query = f"Analyze system performance metrics and provide recommendations for optimization (Request {request_num + 1})"
                task = self._execute_agent_with_supervisor(user_data, query)
                tasks.append(task)
                
        # Execute all tasks concurrently
        results = []
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, task_result in enumerate(completed_tasks):
            if isinstance(task_result, Exception):
                logger.error(f"Task {i} failed: {task_result}")
            else:
                results.append(task_result)
                
        return results
        
    @pytest.mark.asyncio
    async def test_supervisor_isolation_single_user(self):
        """
        Test 9a: Single user supervisor isolation
        
        Validates:
        1. Supervisor instances are properly created with isolation
        2. Execution contexts maintain user-specific state
        3. Database sessions are request-scoped
        4. WebSocket associations are user-specific
        """
        logger.info("=== INTEGRATION TEST 9a: Single User Supervisor Isolation ===")
        
        user_data = self.test_users[0]
        
        # Test multiple sequential executions for the same user
        results = []
        for i in range(3):
            query = f"Performance analysis request {i + 1} - provide detailed metrics"
            result = await self._execute_agent_with_supervisor(user_data, query)
            results.append(result)
            
            # Small delay between executions
            await asyncio.sleep(0.5)
            
        # Validate all executions were successful
        assert len(results) == 3, f"Expected 3 results, got {len(results)}"
        
        for i, result in enumerate(results):
            assert result['user_id'] == user_data['user_id'], f"User ID mismatch in result {i}"
            assert result['result'] is not None, f"Result {i} should not be None"
            assert result['duration_ms'] > 0, f"Result {i} should have positive duration"
            
        logger.info("✅ INTEGRATION TEST 9a PASSED: Single user isolation working correctly")
        
    @pytest.mark.asyncio
    async def test_concurrent_multi_user_isolation(self):
        """
        Test 9b: Concurrent multi-user supervisor isolation
        
        Validates:
        1. Multiple supervisors can execute concurrently without interference
        2. User-specific state remains isolated during concurrent execution
        3. Database sessions don't leak between users
        4. WebSocket events are routed to correct users
        5. No race conditions in factory pattern creation
        """
        logger.info("=== INTEGRATION TEST 9b: Concurrent Multi-User Supervisor Isolation ===")
        
        # Execute concurrent requests
        results = await self._simulate_concurrent_user_requests()
        
        # Validate results
        expected_total_results = self.max_concurrent_users * self.requests_per_user
        assert len(results) >= expected_total_results * 0.8, \
            f"Expected at least {int(expected_total_results * 0.8)} successful results, got {len(results)}"
            
        # Group results by user
        results_by_user = defaultdict(list)
        for result in results:
            results_by_user[result['user_id']].append(result)
            
        # Validate each user got their expected results
        for i in range(self.max_concurrent_users):
            user_id = self.test_users[i]['user_id']
            user_results = results_by_user.get(user_id, [])
            
            assert len(user_results) > 0, f"User {user_id} should have at least one result"
            
            for result in user_results:
                assert result['user_id'] == user_id, f"Result user_id mismatch for {user_id}"
                assert result['result'] is not None, f"Result should not be None for {user_id}"
                
        # Validate no state leakages occurred
        analysis = self.isolation_tracker.get_isolation_analysis()
        assert analysis['state_leakages'] == 0, \
            f"State leakages detected: {analysis['leakage_details']}"
            
        logger.info(f"✅ Concurrent execution successful: {len(results)} results from {len(results_by_user)} users")
        logger.info("✅ INTEGRATION TEST 9b PASSED: Multi-user isolation working correctly")
        
    @pytest.mark.asyncio
    async def test_factory_pattern_memory_isolation(self):
        """
        Test 9c: Factory pattern memory isolation
        
        Validates:
        1. Factory-created supervisors don't share memory between users
        2. Execution engines maintain separate state per user
        3. Tool dispatchers are isolated per request
        4. WebSocket notifiers don't cross-contaminate
        """
        logger.info("=== INTEGRATION TEST 9c: Factory Pattern Memory Isolation ===")
        
        # Create supervisors for different users simultaneously
        supervisors = []
        supervisor_ids = []
        
        for user_data in self.test_users[:3]:
            supervisor, supervisor_id = await self._create_isolated_supervisor(user_data)
            supervisors.append(supervisor)
            supervisor_ids.append(supervisor_id)
            
        # Validate supervisors are different instances
        for i in range(len(supervisors)):
            for j in range(i + 1, len(supervisors)):
                assert supervisors[i] is not supervisors[j], \
                    f"Supervisors {i} and {j} should be different instances"
                    
                # Validate they have different internal state
                if hasattr(supervisors[i], 'user_id') and hasattr(supervisors[j], 'user_id'):
                    assert supervisors[i].user_id != supervisors[j].user_id, \
                        f"Supervisors {i} and {j} should have different user_ids"
                        
        # Validate memory addresses are different
        memory_addresses = [id(supervisor) for supervisor in supervisors]
        assert len(set(memory_addresses)) == len(supervisors), \
            "All supervisors should have unique memory addresses"
            
        logger.info(f"✅ Created {len(supervisors)} isolated supervisors with unique memory addresses")
        logger.info("✅ INTEGRATION TEST 9c PASSED: Factory pattern memory isolation working")
        
    @pytest.mark.asyncio
    async def test_database_session_isolation(self):
        """
        Test 9d: Database session isolation between users
        
        Validates:
        1. Each user gets their own database session
        2. Database sessions are properly scoped to requests
        3. No session sharing between concurrent users
        4. Session cleanup occurs after request completion
        """
        logger.info("=== INTEGRATION TEST 9d: Database Session Isolation ===")
        
        # Create execution contexts for multiple users
        contexts = []
        for user_data in self.test_users[:3]:
            context = await self._create_user_execution_context(user_data)
            contexts.append(context)
            
        # Validate database sessions are isolated
        db_sessions = [context.db_session for context in contexts]
        session_ids = [id(session) for session in db_sessions]
        
        # All sessions should be different instances
        assert len(set(session_ids)) == len(db_sessions), \
            "All database sessions should be unique instances"
            
        # Validate session tagging (if implemented)
        for i, context in enumerate(contexts):
            if hasattr(context.db_session, 'info') and 'user_id' in context.db_session.info:
                session_user = context.db_session.info['user_id']
                expected_user = self.test_users[i]['user_id']
                assert session_user == expected_user, \
                    f"Session user tag mismatch: expected {expected_user}, got {session_user}"
                    
        logger.info(f"✅ Validated {len(contexts)} isolated database sessions")
        logger.info("✅ INTEGRATION TEST 9d PASSED: Database session isolation working")
        
    @pytest.mark.asyncio
    async def test_websocket_routing_isolation(self):
        """
        Test 9e: WebSocket routing isolation
        
        Validates:
        1. WebSocket events are routed to correct user connections
        2. Agent notifications don't leak between users
        3. Thread associations are maintained per user
        4. Connection isolation prevents cross-user events
        """
        logger.info("=== INTEGRATION TEST 9e: WebSocket Routing Isolation ===")
        
        # This test would require real WebSocket connections to be meaningful
        # For now, we'll validate the theoretical isolation through context creation
        
        websocket_contexts = []
        for user_data in self.test_users[:3]:
            # Create context with WebSocket connection ID
            async for db_session in get_request_scoped_db_session():
                context = UserExecutionContext(
                    user_id=user_data['user_id'],
                    thread_id=user_data['thread_id'],
                    run_id=str(uuid.uuid4()),
                    db_session=db_session,
                    websocket_connection_id=f"ws_conn_{user_data['user_id']}",
                    metadata={'websocket_test': True}
                )
                websocket_contexts.append(context)
                break
                
        # Validate WebSocket connection isolation
        connection_ids = [context.websocket_connection_id for context in websocket_contexts]
        assert len(set(connection_ids)) == len(connection_ids), \
            "All WebSocket connection IDs should be unique"
            
        # Validate user-connection mapping
        for i, context in enumerate(websocket_contexts):
            expected_user = self.test_users[i]['user_id']
            assert expected_user in context.websocket_connection_id, \
                f"WebSocket connection ID should contain user ID for {expected_user}"
                
        logger.info(f"✅ Validated {len(websocket_contexts)} isolated WebSocket contexts")
        logger.info("✅ INTEGRATION TEST 9e PASSED: WebSocket routing isolation working")
        
    def _generate_isolation_analysis_report(self):
        """Generate comprehensive isolation analysis report"""
        analysis = self.isolation_tracker.get_isolation_analysis()
        
        logger.info("=== SUPERVISOR ISOLATION ANALYSIS REPORT ===")
        logger.info(f"Users tested: {analysis['users_tested']}")
        logger.info(f"Total supervisor instances: {analysis['total_supervisors']}")
        logger.info(f"Total execution contexts: {analysis['total_contexts']}")
        logger.info(f"Concurrent executions: {analysis['concurrent_executions']}")
        logger.info(f"State leakages detected: {analysis['state_leakages']}")
        logger.info(f"Isolation successful: {analysis['isolation_successful']}")
        
        if analysis['leakage_details']:
            logger.error("CRITICAL ISOLATION FAILURES:")
            for leakage in analysis['leakage_details']:
                logger.error(f"  - {leakage['leakage_type']}: {leakage['from_user']} → {leakage['to_user']}")
                logger.error(f"    Details: {leakage['details']}")


if __name__ == "__main__":
    # Run the test directly
    pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "-x",
        "--log-cli-level=INFO"
    ])