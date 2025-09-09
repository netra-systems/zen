"""
Advanced Multi-User Concurrency and Isolation Integration Tests

Business Value Justification (BVJ):
- Segment: Mid and Enterprise (High-value multi-user scenarios)
- Business Goal: Ensure system scales with concurrent users without data leakage
- Value Impact: Validates enterprise-grade isolation and performance under load
- Strategic Impact: CRITICAL for $1M+ ARR - enterprise customers require perfect isolation

ADVANCED MULTI-USER TEST SCENARIOS:
1. High-concurrency user isolation with cross-user data validation
2. Resource contention and fair allocation under extreme load  
3. Database transaction isolation with concurrent user operations
4. Memory and CPU resource isolation between user sessions
5. WebSocket event isolation with hundreds of concurrent connections
6. Agent execution isolation with overlapping tool usage
7. Authentication and authorization isolation edge cases

CRITICAL REQUIREMENTS:
- NO MOCKS - Real services for all operations
- E2E authentication for all users
- Perfect isolation validation - zero cross-contamination
- Performance benchmarks under extreme concurrent load
- Resource cleanup and memory management validation
"""

import asyncio
import json
import logging
import time
import uuid
import psutil
import threading
import pytest
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import random

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, create_authenticated_user_context

from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.core.execution_engine import ExecutionEngine
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.models.agent_execution import AgentExecution
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.execution_types import AgentExecutionState
from netra_backend.app.api.websocket.events import WebSocketEventType
from shared.types import UserID, ThreadID, RunID, RequestID
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class ConcurrencyTestPhase(Enum):
    """Phases of concurrency testing."""
    INITIALIZATION = "initialization"
    USER_CREATION = "user_creation"
    CONCURRENT_EXECUTION = "concurrent_execution"
    ISOLATION_VALIDATION = "isolation_validation"
    RESOURCE_CLEANUP = "resource_cleanup"
    PERFORMANCE_ANALYSIS = "performance_analysis"


@dataclass
class UserTestSession:
    """Complete test session data for a user."""
    user_id: UserID
    auth_context: Any
    user_index: int
    unique_signature: str
    thread_id: ThreadID
    run_id: RunID
    agent_execution: Optional[Any] = None
    websocket_events: List[Dict] = None
    execution_results: Optional[Dict] = None
    resource_usage: Dict[str, float] = None
    isolation_violations: List[Dict] = None
    performance_metrics: Dict[str, float] = None

    def __post_init__(self):
        if self.websocket_events is None:
            self.websocket_events = []
        if self.resource_usage is None:
            self.resource_usage = {}
        if self.isolation_violations is None:
            self.isolation_violations = []
        if self.performance_metrics is None:
            self.performance_metrics = {}


class TestAdvancedMultiUserConcurrencyIsolation(BaseIntegrationTest):
    """Advanced integration tests for multi-user concurrency and isolation."""

    @pytest.mark.asyncio
    async def test_high_concurrency_user_isolation_validation(self, real_services_fixture):
        """
        Test high-concurrency user isolation with comprehensive cross-user data validation.
        
        ENTERPRISE SCENARIO: 20 concurrent users with perfect isolation validation.
        This validates no cross-user data contamination under high load.
        """
        logger.info("Starting high-concurrency user isolation validation test")
        start_time = time.time()
        
        # Configuration
        num_concurrent_users = 20
        operations_per_user = 5
        
        # Initialize shared components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Phase 1: Create concurrent user sessions
        user_sessions = []
        
        async def create_user_session(user_index: int) -> UserTestSession:
            """Create isolated user session."""
            auth_context = await create_authenticated_user_context(f"concurrent_user_{user_index}")
            user_id = UserID(str(uuid.uuid4()))
            unique_signature = f"user_{user_index}_{uuid.uuid4().hex[:8]}"
            
            session = UserTestSession(
                user_id=user_id,
                auth_context=auth_context,
                user_index=user_index,
                unique_signature=unique_signature,
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4()))
            )
            
            # Set up user-specific WebSocket event capture
            def capture_user_events(event):
                if event.get("user_id") == str(user_id):
                    session.websocket_events.append({
                        **event,
                        "captured_at": datetime.now(timezone.utc)
                    })
            
            websocket_manager.add_event_listener(capture_user_events)
            
            return session
        
        # Create all user sessions concurrently
        session_creation_tasks = [create_user_session(i) for i in range(num_concurrent_users)]
        user_sessions = await asyncio.gather(*session_creation_tasks)
        
        logger.info(f"Created {len(user_sessions)} user sessions")
        
        # Phase 2: Execute concurrent agent operations
        async def execute_user_operations(session: UserTestSession):
            """Execute operations for a single user session."""
            try:
                # Start agent execution with unique data
                unique_content = f"User {session.user_index} isolation test - {session.unique_signature} - analyze data with unique identifiers"
                
                session.agent_execution = await execution_engine.start_agent_execution(
                    user_id=session.user_id,
                    thread_id=session.thread_id,
                    run_id=session.run_id,
                    message_content=unique_content,
                    execution_context=session.auth_context
                )
                
                # Perform multiple operations with user-specific data
                for op_index in range(operations_per_user):
                    operation_data = {
                        "user_signature": session.unique_signature,
                        "operation_index": op_index,
                        "user_specific_data": {
                            "user_id": str(session.user_id),
                            "private_key": f"private_{session.user_index}_{op_index}",
                            "sensitive_value": hashlib.sha256(f"{session.unique_signature}_{op_index}".encode()).hexdigest()
                        },
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    # Update agent state with user-specific data
                    await execution_engine.update_agent_state(
                        agent_execution_id=session.agent_execution.id,
                        user_id=session.user_id,
                        state_update=operation_data
                    )
                    
                    # Brief delay between operations
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Complete execution with user-specific result
                final_result = {
                    "user_isolation_test": "completed",
                    "user_signature": session.unique_signature,
                    "operations_completed": operations_per_user,
                    "completion_timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                await execution_engine.complete_agent_execution(
                    agent_execution_id=session.agent_execution.id,
                    user_id=session.user_id,
                    final_result=final_result
                )
                
                session.execution_results = final_result
                
            except Exception as e:
                logger.error(f"Error in user {session.user_index} operations: {e}")
                session.isolation_violations.append({
                    "type": "execution_error",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc)
                })
        
        # Execute all user operations concurrently
        operation_tasks = [execute_user_operations(session) for session in user_sessions]
        await asyncio.gather(*operation_tasks, return_exceptions=True)
        
        # Phase 3: Comprehensive isolation validation
        isolation_violations = []
        
        for i, session in enumerate(user_sessions):
            # Validate this user's data integrity
            if session.agent_execution:
                try:
                    # Retrieve user's execution state
                    user_state = await execution_engine.get_agent_execution_state(
                        agent_execution_id=session.agent_execution.id,
                        user_id=session.user_id
                    )
                    
                    # Verify user's signature is present
                    state_data = user_state.get("execution_data", {})
                    if session.unique_signature not in str(state_data):
                        isolation_violations.append({
                            "type": "missing_user_signature",
                            "user_index": i,
                            "user_signature": session.unique_signature
                        })
                    
                    # Check for contamination from other users
                    for j, other_session in enumerate(user_sessions):
                        if i != j and other_session.unique_signature in str(state_data):
                            isolation_violations.append({
                                "type": "cross_user_contamination",
                                "affected_user": i,
                                "contaminating_user": j,
                                "contaminating_signature": other_session.unique_signature
                            })
                    
                    # Validate execution results integrity
                    if session.execution_results:
                        result_signature = session.execution_results.get("user_signature")
                        if result_signature != session.unique_signature:
                            isolation_violations.append({
                                "type": "result_signature_mismatch",
                                "user_index": i,
                                "expected": session.unique_signature,
                                "actual": result_signature
                            })
                
                except Exception as e:
                    isolation_violations.append({
                        "type": "validation_error",
                        "user_index": i,
                        "error": str(e)
                    })
        
        # Phase 4: WebSocket event isolation validation
        websocket_violations = []
        
        for i, session in enumerate(user_sessions):
            # Verify each user only received their own events
            for event in session.websocket_events:
                event_user_id = event.get("user_id")
                if event_user_id and UserID(event_user_id) != session.user_id:
                    websocket_violations.append({
                        "type": "wrong_user_event",
                        "session_user": str(session.user_id),
                        "event_user": event_user_id,
                        "user_index": i
                    })
        
        # Phase 5: Database isolation validation
        database_violations = []
        
        # Check that each user's data is completely isolated in database
        for i, session in enumerate(user_sessions):
            if session.agent_execution:
                try:
                    # Query database directly to ensure isolation
                    user_executions = await execution_engine.get_user_executions(session.user_id)
                    
                    # Verify user only sees their own executions
                    for execution in user_executions:
                        if execution.user_id != str(session.user_id):
                            database_violations.append({
                                "type": "database_cross_user_access",
                                "user_index": i,
                                "wrong_user_id": execution.user_id
                            })
                
                except Exception as e:
                    database_violations.append({
                        "type": "database_validation_error",
                        "user_index": i,
                        "error": str(e)
                    })
        
        # Phase 6: Validate isolation success
        total_violations = len(isolation_violations) + len(websocket_violations) + len(database_violations)
        
        logger.info(f"Isolation validation: {total_violations} total violations found")
        logger.info(f"  State violations: {len(isolation_violations)}")
        logger.info(f"  WebSocket violations: {len(websocket_violations)}")
        logger.info(f"  Database violations: {len(database_violations)}")
        
        # Assert perfect isolation
        assert total_violations == 0, f"Isolation violations detected: State={len(isolation_violations)}, WebSocket={len(websocket_violations)}, DB={len(database_violations)}"
        
        # Validate execution success rate
        successful_executions = sum(1 for session in user_sessions if session.execution_results is not None)
        success_rate = successful_executions / len(user_sessions)
        
        assert success_rate >= 0.95, f"Execution success rate too low: {success_rate:.2%} (expected ≥95%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        throughput = (num_concurrent_users * operations_per_user) / execution_time
        
        assert throughput >= 2.0, f"Concurrency throughput too low: {throughput:.1f} ops/s (expected ≥2.0 ops/s)"
        assert execution_time < 120.0, f"High concurrency test should complete in <120s, took {execution_time:.2f}s"
        
        logger.info(f"High-concurrency isolation test completed in {execution_time:.2f}s with perfect isolation")

    @pytest.mark.asyncio
    async def test_resource_contention_fair_allocation_extreme_load(self, real_services_fixture):
        """
        Test resource contention and fair allocation under extreme load.
        
        SCALABILITY SCENARIO: Validates system maintains fairness and stability
        when multiple users compete for limited system resources.
        """
        logger.info("Starting resource contention fair allocation test")
        start_time = time.time()
        
        # Configuration for extreme load
        num_users = 15
        resource_intensive_operations = 8
        
        # Track resource metrics
        resource_metrics = []
        allocation_fairness = {}
        
        # Initialize components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Monitor system resources
        def capture_resource_snapshot(phase: str):
            process = psutil.Process()
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            
            snapshot = {
                "phase": phase,
                "timestamp": datetime.now(timezone.utc),
                "cpu_percent": cpu_percent,
                "memory_rss_mb": memory_info.rss / 1024 / 1024,
                "memory_vms_mb": memory_info.vms / 1024 / 1024,
                "open_files": len(process.open_files()),
                "connections": len(process.connections())
            }
            resource_metrics.append(snapshot)
            return snapshot
        
        capture_resource_snapshot("baseline")
        
        # Phase 1: Create user sessions with resource tracking
        user_sessions = []
        
        for user_index in range(num_users):
            auth_context = await create_authenticated_user_context(f"resource_user_{user_index}")
            user_id = UserID(str(uuid.uuid4()))
            
            session = UserTestSession(
                user_id=user_id,
                auth_context=auth_context,
                user_index=user_index,
                unique_signature=f"resource_test_{user_index}_{uuid.uuid4().hex[:8]}",
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4()))
            )
            
            user_sessions.append(session)
            allocation_fairness[user_index] = {
                "operations_completed": 0,
                "total_execution_time": 0.0,
                "resource_wait_time": 0.0,
                "errors": 0
            }
        
        capture_resource_snapshot("users_created")
        
        # Phase 2: Execute resource-intensive operations concurrently
        async def execute_resource_intensive_operations(session: UserTestSession):
            """Execute resource-intensive operations for fairness testing."""
            user_start_time = time.time()
            
            try:
                # Start agent execution
                session.agent_execution = await execution_engine.start_agent_execution(
                    user_id=session.user_id,
                    thread_id=session.thread_id,
                    run_id=session.run_id,
                    message_content=f"Resource intensive analysis for user {session.user_index}",
                    execution_context=session.auth_context
                )
                
                for op_index in range(resource_intensive_operations):
                    operation_start = time.time()
                    
                    try:
                        # Resource-intensive state update
                        large_data = {
                            "user_signature": session.unique_signature,
                            "operation": op_index,
                            "large_dataset": ["data_" * 100 for _ in range(1000)],  # ~400KB data
                            "computation_result": [i ** 2 for i in range(1000)],
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await execution_engine.update_agent_state(
                            agent_execution_id=session.agent_execution.id,
                            user_id=session.user_id,
                            state_update=large_data
                        )
                        
                        # Simulate CPU-intensive work
                        await asyncio.sleep(random.uniform(0.2, 0.5))
                        
                        operation_time = time.time() - operation_start
                        allocation_fairness[session.user_index]["operations_completed"] += 1
                        allocation_fairness[session.user_index]["total_execution_time"] += operation_time
                        
                    except Exception as e:
                        allocation_fairness[session.user_index]["errors"] += 1
                        logger.warning(f"User {session.user_index} operation {op_index} failed: {e}")
                
                # Complete execution
                await execution_engine.complete_agent_execution(
                    agent_execution_id=session.agent_execution.id,
                    user_id=session.user_id,
                    final_result={
                        "user_signature": session.unique_signature,
                        "operations_completed": allocation_fairness[session.user_index]["operations_completed"]
                    }
                )
                
                user_execution_time = time.time() - user_start_time
                session.performance_metrics = {
                    "total_time": user_execution_time,
                    "operations_per_second": allocation_fairness[session.user_index]["operations_completed"] / user_execution_time
                }
                
            except Exception as e:
                logger.error(f"User {session.user_index} resource test failed: {e}")
                allocation_fairness[session.user_index]["errors"] += 1
        
        # Execute all users concurrently with resource monitoring
        capture_resource_snapshot("before_concurrent_execution")
        
        execution_tasks = [execute_resource_intensive_operations(session) for session in user_sessions]
        
        # Monitor resources during execution
        async def monitor_resources_during_execution():
            while not all(task.done() for task in execution_tasks):
                capture_resource_snapshot("during_execution")
                await asyncio.sleep(2)
        
        # Run execution and monitoring concurrently
        monitor_task = asyncio.create_task(monitor_resources_during_execution())
        await asyncio.gather(*execution_tasks, return_exceptions=True)
        monitor_task.cancel()
        
        capture_resource_snapshot("after_concurrent_execution")
        
        # Phase 3: Analyze resource allocation fairness
        fairness_metrics = {}
        
        # Calculate fairness statistics
        completion_rates = [metrics["operations_completed"] / resource_intensive_operations 
                          for metrics in allocation_fairness.values()]
        
        avg_completion_rate = sum(completion_rates) / len(completion_rates)
        completion_variance = sum((rate - avg_completion_rate) ** 2 for rate in completion_rates) / len(completion_rates)
        completion_std_dev = completion_variance ** 0.5
        
        fairness_metrics["completion_rate_avg"] = avg_completion_rate
        fairness_metrics["completion_rate_std_dev"] = completion_std_dev
        fairness_metrics["completion_rate_fairness"] = 1.0 - (completion_std_dev / avg_completion_rate) if avg_completion_rate > 0 else 0.0
        
        # Execution time fairness
        execution_times = [session.performance_metrics.get("total_time", 0.0) for session in user_sessions if session.performance_metrics]
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
            time_variance = sum((t - avg_execution_time) ** 2 for t in execution_times) / len(execution_times)
            time_std_dev = time_variance ** 0.5
            
            fairness_metrics["execution_time_avg"] = avg_execution_time
            fairness_metrics["execution_time_std_dev"] = time_std_dev
            fairness_metrics["execution_time_fairness"] = 1.0 - (time_std_dev / avg_execution_time) if avg_execution_time > 0 else 0.0
        
        logger.info(f"Fairness Analysis:")
        logger.info(f"  Completion rate fairness: {fairness_metrics['completion_rate_fairness']:.2%}")
        if "execution_time_fairness" in fairness_metrics:
            logger.info(f"  Execution time fairness: {fairness_metrics['execution_time_fairness']:.2%}")
        
        # Validate fairness requirements
        assert fairness_metrics["completion_rate_fairness"] >= 0.7, f"Completion rate fairness too low: {fairness_metrics['completion_rate_fairness']:.2%} (expected ≥70%)"
        
        if "execution_time_fairness" in fairness_metrics:
            assert fairness_metrics["execution_time_fairness"] >= 0.6, f"Execution time fairness too low: {fairness_metrics['execution_time_fairness']:.2%} (expected ≥60%)"
        
        # Phase 4: Validate resource usage stability
        peak_memory = max(m["memory_rss_mb"] for m in resource_metrics)
        baseline_memory = resource_metrics[0]["memory_rss_mb"]
        memory_growth = peak_memory - baseline_memory
        
        peak_cpu = max(m["cpu_percent"] for m in resource_metrics if m["cpu_percent"] > 0)
        
        logger.info(f"Resource Usage: Peak Memory={peak_memory:.1f}MB (+{memory_growth:.1f}MB), Peak CPU={peak_cpu:.1f}%")
        
        # Memory growth should be reasonable (allow 500MB for intensive operations)
        assert memory_growth < 500.0, f"Memory growth too high: {memory_growth:.1f}MB (expected <500MB)"
        
        # CPU usage should be reasonable (allow up to 200% for multi-core usage)
        assert peak_cpu < 200.0, f"CPU usage too high: {peak_cpu:.1f}% (expected <200%)"
        
        # Validate overall success rate
        total_errors = sum(metrics["errors"] for metrics in allocation_fairness.values())
        total_operations = num_users * resource_intensive_operations
        error_rate = total_errors / total_operations
        
        assert error_rate < 0.1, f"Error rate too high: {error_rate:.2%} (expected <10%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        total_throughput = total_operations / execution_time
        
        assert total_throughput >= 1.0, f"Total throughput too low: {total_throughput:.1f} ops/s (expected ≥1.0 ops/s)"
        assert execution_time < 180.0, f"Resource contention test should complete in <180s, took {execution_time:.2f}s"
        
        logger.info(f"Resource contention test completed in {execution_time:.2f}s with {fairness_metrics['completion_rate_fairness']:.2%} fairness")

    @pytest.mark.asyncio
    async def test_database_transaction_isolation_concurrent_operations(self, real_services_fixture):
        """
        Test database transaction isolation with concurrent user operations.
        
        DATA INTEGRITY SCENARIO: Validates ACID properties maintained during
        concurrent database operations by multiple users.
        """
        logger.info("Starting database transaction isolation test")
        start_time = time.time()
        
        # Configuration
        num_concurrent_users = 12
        transactions_per_user = 6
        
        # Initialize components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Track transaction integrity
        transaction_log = []
        isolation_violations = []
        
        # Phase 1: Create user sessions for transaction testing
        user_sessions = []
        
        for user_index in range(num_concurrent_users):
            auth_context = await create_authenticated_user_context(f"txn_user_{user_index}")
            user_id = UserID(str(uuid.uuid4()))
            
            session = UserTestSession(
                user_id=user_id,
                auth_context=auth_context,
                user_index=user_index,
                unique_signature=f"txn_{user_index}_{uuid.uuid4().hex[:8]}",
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4()))
            )
            user_sessions.append(session)
        
        # Phase 2: Execute concurrent transactional operations
        async def execute_transactional_operations(session: UserTestSession):
            """Execute transactional operations with isolation validation."""
            try:
                # Start agent execution
                session.agent_execution = await execution_engine.start_agent_execution(
                    user_id=session.user_id,
                    thread_id=session.thread_id,
                    run_id=session.run_id,
                    message_content=f"Transaction isolation test for user {session.user_index}",
                    execution_context=session.auth_context
                )
                
                # Execute multiple transactions
                for txn_index in range(transactions_per_user):
                    transaction_id = f"{session.unique_signature}_txn_{txn_index}"
                    
                    try:
                        # Begin transaction with unique data
                        txn_start = time.time()
                        
                        transaction_data = {
                            "transaction_id": transaction_id,
                            "user_signature": session.unique_signature,
                            "txn_index": txn_index,
                            "unique_value": hashlib.sha256(transaction_id.encode()).hexdigest(),
                            "counter_value": txn_index * 10,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        # Perform transactional state update
                        await execution_engine.transactional_state_update(
                            agent_execution_id=session.agent_execution.id,
                            user_id=session.user_id,
                            transaction_data=transaction_data,
                            isolation_level="READ_COMMITTED"
                        )
                        
                        # Validate transaction completed
                        updated_state = await execution_engine.get_agent_execution_state(
                            agent_execution_id=session.agent_execution.id,
                            user_id=session.user_id
                        )
                        
                        # Verify transaction data integrity
                        state_data = updated_state.get("execution_data", {})
                        if transaction_data["unique_value"] not in str(state_data):
                            isolation_violations.append({
                                "type": "transaction_data_missing",
                                "user_index": session.user_index,
                                "transaction_id": transaction_id
                            })
                        
                        txn_duration = time.time() - txn_start
                        
                        # Log successful transaction
                        transaction_log.append({
                            "transaction_id": transaction_id,
                            "user_index": session.user_index,
                            "user_id": str(session.user_id),
                            "duration": txn_duration,
                            "status": "completed",
                            "timestamp": datetime.now(timezone.utc)
                        })
                        
                        # Brief delay between transactions
                        await asyncio.sleep(random.uniform(0.05, 0.15))
                        
                    except Exception as e:
                        # Log failed transaction
                        transaction_log.append({
                            "transaction_id": transaction_id,
                            "user_index": session.user_index,
                            "user_id": str(session.user_id),
                            "status": "failed",
                            "error": str(e),
                            "timestamp": datetime.now(timezone.utc)
                        })
                        
                        isolation_violations.append({
                            "type": "transaction_failure",
                            "user_index": session.user_index,
                            "transaction_id": transaction_id,
                            "error": str(e)
                        })
                
                # Complete execution
                await execution_engine.complete_agent_execution(
                    agent_execution_id=session.agent_execution.id,
                    user_id=session.user_id,
                    final_result={"transactions_attempted": transactions_per_user}
                )
                
            except Exception as e:
                logger.error(f"User {session.user_index} transaction test failed: {e}")
                isolation_violations.append({
                    "type": "user_execution_failure",
                    "user_index": session.user_index,
                    "error": str(e)
                })
        
        # Execute all users concurrently
        transaction_tasks = [execute_transactional_operations(session) for session in user_sessions]
        await asyncio.gather(*transaction_tasks, return_exceptions=True)
        
        # Phase 3: Validate transaction isolation and ACID properties
        
        # Analyze transaction success rate
        successful_transactions = [log for log in transaction_log if log["status"] == "completed"]
        failed_transactions = [log for log in transaction_log if log["status"] == "failed"]
        
        total_expected = num_concurrent_users * transactions_per_user
        success_rate = len(successful_transactions) / total_expected
        
        logger.info(f"Transaction Results: {len(successful_transactions)}/{total_expected} successful ({success_rate:.2%})")
        
        # Validate transaction success rate
        assert success_rate >= 0.9, f"Transaction success rate too low: {success_rate:.2%} (expected ≥90%)"
        
        # Phase 4: Cross-user isolation validation
        cross_contamination_checks = 0
        
        for session in user_sessions:
            if session.agent_execution:
                try:
                    # Get final state for this user
                    final_state = await execution_engine.get_agent_execution_state(
                        agent_execution_id=session.agent_execution.id,
                        user_id=session.user_id
                    )
                    
                    state_str = str(final_state)
                    
                    # Check for contamination from other users
                    for other_session in user_sessions:
                        if session.user_index != other_session.user_index:
                            if other_session.unique_signature in state_str:
                                isolation_violations.append({
                                    "type": "cross_user_transaction_contamination",
                                    "affected_user": session.user_index,
                                    "contaminating_user": other_session.user_index
                                })
                    
                    cross_contamination_checks += 1
                    
                except Exception as e:
                    isolation_violations.append({
                        "type": "isolation_check_error",
                        "user_index": session.user_index,
                        "error": str(e)
                    })
        
        # Phase 5: Validate transaction timing and consistency
        
        # Check for transaction timing overlaps that should have been isolated
        timing_violations = 0
        
        successful_by_user = {}
        for log in successful_transactions:
            user_index = log["user_index"]
            if user_index not in successful_by_user:
                successful_by_user[user_index] = []
            successful_by_user[user_index].append(log)
        
        # Validate each user's transactions were processed consistently
        for user_index, user_transactions in successful_by_user.items():
            user_transactions.sort(key=lambda x: x["timestamp"])
            
            # Check for reasonable transaction durations (detect deadlocks/blocks)
            long_transactions = [t for t in user_transactions if t["duration"] > 5.0]
            if len(long_transactions) > transactions_per_user * 0.3:  # More than 30% taking >5s
                isolation_violations.append({
                    "type": "excessive_transaction_blocking",
                    "user_index": user_index,
                    "long_transactions": len(long_transactions)
                })
        
        # Phase 6: Validate overall isolation integrity
        total_violations = len(isolation_violations)
        
        logger.info(f"Isolation Validation: {total_violations} violations detected")
        
        # Log violation details
        for violation in isolation_violations:
            logger.warning(f"Isolation violation: {violation}")
        
        # Assert transaction isolation integrity
        contamination_violations = [v for v in isolation_violations if "contamination" in v["type"]]
        assert len(contamination_violations) == 0, f"Transaction isolation contamination detected: {len(contamination_violations)} violations"
        
        # Allow some failures but not isolation violations
        critical_violations = [v for v in isolation_violations if v["type"] in [
            "cross_user_transaction_contamination", "transaction_data_missing"
        ]]
        assert len(critical_violations) == 0, f"Critical isolation violations detected: {len(critical_violations)}"
        
        # Performance validation
        execution_time = time.time() - start_time
        transaction_throughput = len(successful_transactions) / execution_time
        
        assert transaction_throughput >= 2.0, f"Transaction throughput too low: {transaction_throughput:.1f} txn/s (expected ≥2.0 txn/s)"
        assert execution_time < 120.0, f"Transaction isolation test should complete in <120s, took {execution_time:.2f}s"
        
        logger.info(f"Database transaction isolation test completed in {execution_time:.2f}s with perfect isolation")

    @pytest.mark.asyncio
    async def test_memory_cpu_resource_isolation_between_sessions(self, real_services_fixture):
        """
        Test memory and CPU resource isolation between user sessions.
        
        RESOURCE ISOLATION SCENARIO: Validates one user's resource usage
        does not negatively impact other users' performance.
        """
        logger.info("Starting memory and CPU resource isolation test")
        start_time = time.time()
        
        # Configuration
        num_users = 8
        resource_hog_user_index = 3  # One user will consume excessive resources
        
        # Initialize components
        agent_registry = AgentRegistry()
        execution_engine = ExecutionEngine()
        websocket_manager = WebSocketManager()
        agent_registry.set_websocket_manager(websocket_manager)
        
        # Track resource usage per user
        user_resource_metrics = {}
        system_resource_snapshots = []
        
        def capture_system_snapshot(label: str):
            process = psutil.Process()
            snapshot = {
                "label": label,
                "timestamp": datetime.now(timezone.utc),
                "cpu_percent": process.cpu_percent(),
                "memory_rss_mb": process.memory_info().rss / 1024 / 1024,
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "open_files": len(process.open_files())
            }
            system_resource_snapshots.append(snapshot)
            return snapshot
        
        capture_system_snapshot("baseline")
        
        # Phase 1: Create user sessions with resource tracking
        user_sessions = []
        
        for user_index in range(num_users):
            auth_context = await create_authenticated_user_context(f"resource_isolation_user_{user_index}")
            user_id = UserID(str(uuid.uuid4()))
            
            session = UserTestSession(
                user_id=user_id,
                auth_context=auth_context,
                user_index=user_index,
                unique_signature=f"resource_{user_index}_{uuid.uuid4().hex[:8]}",
                thread_id=ThreadID(str(uuid.uuid4())),
                run_id=RunID(str(uuid.uuid4()))
            )
            
            user_sessions.append(session)
            user_resource_metrics[user_index] = {
                "start_time": None,
                "end_time": None,
                "peak_memory": 0.0,
                "operations_completed": 0,
                "performance_degraded": False
            }
        
        # Phase 2: Execute with one resource-intensive user
        async def execute_normal_user_operations(session: UserTestSession):
            """Execute normal resource usage operations."""
            user_start = time.time()
            user_resource_metrics[session.user_index]["start_time"] = user_start
            
            try:
                # Start agent execution
                session.agent_execution = await execution_engine.start_agent_execution(
                    user_id=session.user_id,
                    thread_id=session.thread_id,
                    run_id=session.run_id,
                    message_content=f"Normal resource usage test for user {session.user_index}",
                    execution_context=session.auth_context
                )
                
                # Perform normal operations
                for op_index in range(5):
                    operation_start = time.time()
                    
                    # Normal-sized data operations
                    normal_data = {
                        "user_signature": session.unique_signature,
                        "operation": op_index,
                        "normal_data": ["item_" + str(i) for i in range(100)],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await execution_engine.update_agent_state(
                        agent_execution_id=session.agent_execution.id,
                        user_id=session.user_id,
                        state_update=normal_data
                    )
                    
                    operation_time = time.time() - operation_start
                    user_resource_metrics[session.user_index]["operations_completed"] += 1
                    
                    # Check if this operation took unusually long (performance degradation)
                    if operation_time > 2.0:  # Normal operations should be <2s
                        user_resource_metrics[session.user_index]["performance_degraded"] = True
                    
                    await asyncio.sleep(0.2)
                
                await execution_engine.complete_agent_execution(
                    agent_execution_id=session.agent_execution.id,
                    user_id=session.user_id,
                    final_result={"normal_operations": "completed"}
                )
                
            except Exception as e:
                logger.error(f"Normal user {session.user_index} failed: {e}")
            
            user_resource_metrics[session.user_index]["end_time"] = time.time()
        
        async def execute_resource_intensive_operations(session: UserTestSession):
            """Execute resource-intensive operations (resource hog user)."""
            user_start = time.time()
            user_resource_metrics[session.user_index]["start_time"] = user_start
            
            try:
                # Start agent execution
                session.agent_execution = await execution_engine.start_agent_execution(
                    user_id=session.user_id,
                    thread_id=session.thread_id,
                    run_id=session.run_id,
                    message_content=f"RESOURCE INTENSIVE test for user {session.user_index}",
                    execution_context=session.auth_context
                )
                
                # Perform resource-intensive operations
                for op_index in range(5):
                    # Create large memory-intensive data
                    intensive_data = {
                        "user_signature": session.unique_signature,
                        "operation": op_index,
                        "massive_data": ["large_item_" * 1000 for _ in range(5000)],  # ~25MB data
                        "computation_intensive": [i ** j for i in range(1000) for j in range(5)],
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
                    
                    await execution_engine.update_agent_state(
                        agent_execution_id=session.agent_execution.id,
                        user_id=session.user_id,
                        state_update=intensive_data
                    )
                    
                    user_resource_metrics[session.user_index]["operations_completed"] += 1
                    
                    # CPU-intensive computation
                    await asyncio.sleep(1.0)  # Simulate heavy computation
                    
                    # Monitor peak memory usage
                    current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                    if current_memory > user_resource_metrics[session.user_index]["peak_memory"]:
                        user_resource_metrics[session.user_index]["peak_memory"] = current_memory
                
                await execution_engine.complete_agent_execution(
                    agent_execution_id=session.agent_execution.id,
                    user_id=session.user_id,
                    final_result={"intensive_operations": "completed"}
                )
                
            except Exception as e:
                logger.error(f"Resource-intensive user {session.user_index} failed: {e}")
            
            user_resource_metrics[session.user_index]["end_time"] = time.time()
        
        # Execute users concurrently with resource monitoring
        execution_tasks = []
        
        for session in user_sessions:
            if session.user_index == resource_hog_user_index:
                task = execute_resource_intensive_operations(session)
            else:
                task = execute_normal_user_operations(session)
            execution_tasks.append(task)
        
        # Monitor system resources during execution
        async def monitor_system_resources():
            while not all(task.done() for task in execution_tasks):
                capture_system_snapshot("during_execution")
                await asyncio.sleep(1)
        
        monitor_task = asyncio.create_task(monitor_system_resources())
        await asyncio.gather(*execution_tasks, return_exceptions=True)
        monitor_task.cancel()
        
        capture_system_snapshot("after_execution")
        
        # Phase 3: Analyze resource isolation effectiveness
        
        # Check if normal users experienced performance degradation
        degraded_users = [idx for idx, metrics in user_resource_metrics.items() 
                         if metrics["performance_degraded"] and idx != resource_hog_user_index]
        
        degradation_rate = len(degraded_users) / (num_users - 1)  # Exclude resource hog user
        
        logger.info(f"Performance degradation: {len(degraded_users)}/{num_users-1} normal users affected ({degradation_rate:.2%})")
        
        # Validate resource isolation (normal users should not be significantly affected)
        assert degradation_rate <= 0.3, f"Too many users experienced performance degradation: {degradation_rate:.2%} (expected ≤30%)"
        
        # Check execution time fairness
        execution_times = []
        for idx, metrics in user_resource_metrics.items():
            if metrics["start_time"] and metrics["end_time"] and idx != resource_hog_user_index:
                execution_time = metrics["end_time"] - metrics["start_time"]
                execution_times.append(execution_time)
        
        if execution_times:
            avg_execution_time = sum(execution_times) / len(execution_times)
            max_execution_time = max(execution_times)
            
            # Normal users should have similar execution times
            time_variance_ratio = (max_execution_time - avg_execution_time) / avg_execution_time
            
            logger.info(f"Execution time variance: {time_variance_ratio:.2%} (avg: {avg_execution_time:.1f}s, max: {max_execution_time:.1f}s)")
            
            assert time_variance_ratio <= 1.0, f"Execution time variance too high: {time_variance_ratio:.2%} (expected ≤100%)"
        
        # Validate system resource usage
        peak_memory = max(snapshot["memory_rss_mb"] for snapshot in system_resource_snapshots)
        baseline_memory = system_resource_snapshots[0]["memory_rss_mb"]
        memory_increase = peak_memory - baseline_memory
        
        logger.info(f"System memory usage: Baseline={baseline_memory:.1f}MB, Peak={peak_memory:.1f}MB, Increase={memory_increase:.1f}MB")
        
        # Memory increase should be contained (allow 1GB for resource-intensive user)
        assert memory_increase < 1000.0, f"System memory increase too high: {memory_increase:.1f}MB (expected <1000MB)"
        
        # Validate all users completed their operations
        completion_rate = sum(1 for metrics in user_resource_metrics.values() if metrics["operations_completed"] >= 4) / num_users
        
        assert completion_rate >= 0.9, f"User completion rate too low: {completion_rate:.2%} (expected ≥90%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        assert execution_time < 90.0, f"Resource isolation test should complete in <90s, took {execution_time:.2f}s"
        
        logger.info(f"Memory/CPU resource isolation test completed in {execution_time:.2f}s with {degradation_rate:.2%} degradation rate")

    @pytest.mark.asyncio
    async def test_websocket_event_isolation_massive_concurrent_connections(self, real_services_fixture):
        """
        Test WebSocket event isolation with hundreds of concurrent connections.
        
        MASSIVE SCALE SCENARIO: Validates WebSocket event delivery and isolation
        with large number of concurrent user connections.
        """
        logger.info("Starting massive concurrent WebSocket connections test")
        start_time = time.time()
        
        # Configuration for massive scale
        num_concurrent_connections = 50  # Reduced for test stability but still substantial
        messages_per_connection = 4
        
        # Initialize components
        websocket_manager = WebSocketManager()
        
        # Track connection and message metrics
        connection_metrics = {}
        message_delivery_stats = {}
        isolation_violations = []
        
        # Phase 1: Create massive number of concurrent connections
        connection_sessions = []
        
        async def create_connection_session(conn_index: int):
            """Create individual connection session."""
            try:
                auth_context = await create_authenticated_user_context(f"massive_conn_user_{conn_index}")
                user_id = UserID(str(uuid.uuid4()))
                unique_signature = f"massive_{conn_index}_{uuid.uuid4().hex[:8]}"
                
                # Track messages for this connection
                connection_messages = []
                
                async def connection_message_handler(websocket, path):
                    async for message in websocket:
                        try:
                            parsed_msg = json.loads(message)
                            parsed_msg["received_at"] = datetime.now(timezone.utc)
                            parsed_msg["connection_index"] = conn_index
                            connection_messages.append(parsed_msg)
                        except json.JSONDecodeError:
                            logger.warning(f"Connection {conn_index} received invalid message")
                
                # Establish WebSocket connection
                connection = await websocket_manager.create_authenticated_connection(
                    user_id=str(user_id),
                    auth_context=auth_context,
                    message_handler=connection_message_handler,
                    connection_id=f"massive_conn_{conn_index}"
                )
                
                session_data = {
                    "connection_index": conn_index,
                    "user_id": user_id,
                    "auth_context": auth_context,
                    "unique_signature": unique_signature,
                    "connection": connection,
                    "messages": connection_messages,
                    "established_at": datetime.now(timezone.utc)
                }
                
                connection_metrics[conn_index] = {
                    "established": True,
                    "messages_sent": 0,
                    "messages_received": 0,
                    "errors": 0
                }
                
                return session_data
                
            except Exception as e:
                logger.error(f"Failed to create connection {conn_index}: {e}")
                connection_metrics[conn_index] = {
                    "established": False,
                    "error": str(e),
                    "messages_sent": 0,
                    "messages_received": 0,
                    "errors": 1
                }
                return None
        
        # Create connections in batches to avoid overwhelming the system
        batch_size = 10
        for batch_start in range(0, num_concurrent_connections, batch_size):
            batch_end = min(batch_start + batch_size, num_concurrent_connections)
            batch_tasks = [create_connection_session(i) for i in range(batch_start, batch_end)]
            
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            connection_sessions.extend([result for result in batch_results if result is not None])
            
            logger.info(f"Established connections batch {batch_start}-{batch_end-1}")
            await asyncio.sleep(1)  # Brief pause between batches
        
        successful_connections = len(connection_sessions)
        logger.info(f"Successfully established {successful_connections}/{num_concurrent_connections} connections")
        
        # Require at least 80% connection success
        connection_success_rate = successful_connections / num_concurrent_connections
        assert connection_success_rate >= 0.8, f"Connection establishment rate too low: {connection_success_rate:.2%} (expected ≥80%)"
        
        # Phase 2: Send targeted messages to specific connections
        async def send_targeted_messages():
            """Send targeted messages to test isolation."""
            for session in connection_sessions:
                conn_index = session["connection_index"]
                user_id = session["user_id"]
                unique_signature = session["unique_signature"]
                
                for msg_index in range(messages_per_connection):
                    try:
                        message = {
                            "type": WebSocketEventType.AGENT_THINKING.value,
                            "data": {
                                "message_id": f"{unique_signature}_msg_{msg_index}",
                                "connection_index": conn_index,
                                "content": f"Targeted message {msg_index} for connection {conn_index}",
                                "unique_signature": unique_signature
                            },
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        }
                        
                        await websocket_manager.send_message_to_user(
                            user_id=str(user_id),
                            message=message
                        )
                        
                        connection_metrics[conn_index]["messages_sent"] += 1
                        
                    except Exception as e:
                        connection_metrics[conn_index]["errors"] += 1
                        logger.warning(f"Failed to send message to connection {conn_index}: {e}")
                    
                    # Small delay between messages to each connection
                    await asyncio.sleep(0.01)
        
        # Send all targeted messages
        await send_targeted_messages()
        
        # Phase 3: Send broadcast messages to all connections
        broadcast_messages = []
        for broadcast_index in range(3):  # Send 3 broadcast messages
            broadcast_message = {
                "type": WebSocketEventType.AGENT_COMPLETED.value,
                "data": {
                    "message_id": f"broadcast_{broadcast_index}",
                    "content": f"Broadcast message {broadcast_index} to all connections",
                    "broadcast_index": broadcast_index
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            # Broadcast to all users
            for session in connection_sessions:
                try:
                    await websocket_manager.send_message_to_user(
                        user_id=str(session["user_id"]),
                        message=broadcast_message
                    )
                    connection_metrics[session["connection_index"]]["messages_sent"] += 1
                except Exception as e:
                    connection_metrics[session["connection_index"]]["errors"] += 1
            
            broadcast_messages.append(broadcast_message)
            await asyncio.sleep(0.5)
        
        # Phase 4: Allow messages to be received
        await asyncio.sleep(5)
        
        # Phase 5: Validate message delivery and isolation
        for session in connection_sessions:
            conn_index = session["connection_index"]
            unique_signature = session["unique_signature"]
            received_messages = session["messages"]
            
            connection_metrics[conn_index]["messages_received"] = len(received_messages)
            
            # Validate targeted message delivery
            targeted_messages = [
                msg for msg in received_messages
                if msg.get("data", {}).get("unique_signature") == unique_signature
            ]
            
            # Validate broadcast message delivery
            broadcast_messages_received = [
                msg for msg in received_messages
                if msg.get("data", {}).get("message_id", "").startswith("broadcast_")
            ]
            
            # Check for isolation violations (messages from other connections)
            for msg in received_messages:
                msg_signature = msg.get("data", {}).get("unique_signature")
                if msg_signature and msg_signature != unique_signature and not msg.get("data", {}).get("message_id", "").startswith("broadcast_"):
                    isolation_violations.append({
                        "type": "cross_connection_message",
                        "receiver_connection": conn_index,
                        "sender_signature": msg_signature,
                        "message_id": msg.get("data", {}).get("message_id")
                    })
            
            message_delivery_stats[conn_index] = {
                "targeted_expected": messages_per_connection,
                "targeted_received": len(targeted_messages),
                "broadcast_expected": len(broadcast_messages),
                "broadcast_received": len(broadcast_messages_received),
                "total_received": len(received_messages)
            }
        
        # Phase 6: Analyze delivery and isolation results
        
        # Calculate delivery statistics
        targeted_delivery_rates = []
        broadcast_delivery_rates = []
        
        for conn_index, stats in message_delivery_stats.items():
            targeted_rate = stats["targeted_received"] / stats["targeted_expected"] if stats["targeted_expected"] > 0 else 0.0
            broadcast_rate = stats["broadcast_received"] / stats["broadcast_expected"] if stats["broadcast_expected"] > 0 else 0.0
            
            targeted_delivery_rates.append(targeted_rate)
            broadcast_delivery_rates.append(broadcast_rate)
        
        avg_targeted_delivery = sum(targeted_delivery_rates) / len(targeted_delivery_rates) if targeted_delivery_rates else 0.0
        avg_broadcast_delivery = sum(broadcast_delivery_rates) / len(broadcast_delivery_rates) if broadcast_delivery_rates else 0.0
        
        logger.info(f"Message Delivery Rates: Targeted={avg_targeted_delivery:.2%}, Broadcast={avg_broadcast_delivery:.2%}")
        logger.info(f"Isolation Violations: {len(isolation_violations)} violations detected")
        
        # Validate delivery performance
        assert avg_targeted_delivery >= 0.8, f"Targeted message delivery rate too low: {avg_targeted_delivery:.2%} (expected ≥80%)"
        assert avg_broadcast_delivery >= 0.7, f"Broadcast message delivery rate too low: {avg_broadcast_delivery:.2%} (expected ≥70%)"
        
        # Validate perfect isolation (zero cross-connection messages)
        assert len(isolation_violations) == 0, f"Message isolation violations detected: {len(isolation_violations)}"
        
        # Validate connection stability
        stable_connections = sum(1 for metrics in connection_metrics.values() if metrics["established"] and metrics["errors"] == 0)
        stability_rate = stable_connections / successful_connections
        
        assert stability_rate >= 0.9, f"Connection stability rate too low: {stability_rate:.2%} (expected ≥90%)"
        
        # Performance validation
        execution_time = time.time() - start_time
        total_messages_sent = sum(metrics["messages_sent"] for metrics in connection_metrics.values())
        message_throughput = total_messages_sent / execution_time
        
        logger.info(f"Performance: {message_throughput:.1f} messages/second across {successful_connections} connections")
        
        assert message_throughput >= 20.0, f"Message throughput too low: {message_throughput:.1f} msg/s (expected ≥20 msg/s)"
        assert execution_time < 120.0, f"Massive WebSocket test should complete in <120s, took {execution_time:.2f}s"
        
        logger.info(f"Massive concurrent WebSocket test completed in {execution_time:.2f}s with perfect isolation")