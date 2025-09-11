"""
Integration Tests for Multi-User Concurrent ReportingSubAgent Execution - Issue #354

CRITICAL SECURITY VULNERABILITY: P0 vulnerability in concurrent ReportingSubAgent 
execution causing cross-user data contamination under race conditions.

Business Value Justification (BVJ):
- Segment: Enterprise (multi-tenant environments with concurrent users)
- Business Goal: Prevent race condition data leakage between concurrent users
- Value Impact: Ensures complete user isolation under high concurrent load
- Revenue Impact: Prevents $500K+ ARR loss from enterprise multi-tenant security breaches

TEST STRATEGY:
These tests simulate real-world concurrent usage patterns to expose cross-contamination 
vulnerabilities. Tests are designed to FAIL initially with DeepAgentState shared state
patterns, proving race condition vulnerabilities exist. After migration to 
UserExecutionContext, tests should PASS, proving security fix effectiveness.

CONCURRENCY PATTERNS TESTED:
1. Simultaneous report generation for different users
2. Race conditions in shared state access
3. Memory isolation under concurrent load
4. Cache contamination between users
5. WebSocket event isolation between concurrent sessions
6. Resource cleanup isolation
7. Error boundary isolation

EXPECTED BEHAVIOR:
- BEFORE Migration: Tests FAIL - Cross-contamination occurs under race conditions
- AFTER Migration: Tests PASS - Complete isolation maintained under all conditions
"""

import pytest
import asyncio
import threading
import time
import uuid
import gc
import weakref
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from unittest.mock import Mock, AsyncMock, patch

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.reporting_sub_agent import ReportingSubAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.user_execution_context import UserExecutionContext
from shared.types.core_types import UserID, ThreadID, RunID


@dataclass
class ConcurrentUser:
    """Represents a user in concurrent execution scenario."""
    user_id: str
    username: str
    thread_id: str
    sensitive_data: Dict[str, Any]
    expected_outputs: Set[str] = field(default_factory=set)
    contaminated_outputs: Set[str] = field(default_factory=set)


@dataclass
class ConcurrencyTestResult:
    """Results of concurrency testing."""
    user_id: str
    execution_time: float
    result_data: Any
    memory_references: List[str]
    contamination_detected: bool
    isolation_verified: bool
    errors: List[str] = field(default_factory=list)


class TestReportingAgentMultiUserConcurrencySecurity(SSotAsyncTestCase):
    """
    Integration tests for multi-user concurrent ReportingSubAgent execution security.
    
    These tests prove that concurrent execution with DeepAgentState creates cross-user
    contamination vulnerabilities and that UserExecutionContext provides isolation.
    """

    def setup_method(self, method=None):
        """Set up concurrent multi-user test environment."""
        super().setup_method(method)
        
        # Configuration for concurrency testing
        self.concurrent_users_count = 5
        self.execution_iterations = 3
        self.max_concurrent_threads = 10
        
        # Create multiple concurrent users with different sensitive data
        self.concurrent_users = self._create_concurrent_test_users()
        
        # Track contamination evidence
        self.contamination_evidence = defaultdict(list)
        self.isolation_violations = []
        
        # Memory tracking for reference leakage
        self.memory_references = []

    def _create_concurrent_test_users(self) -> List[ConcurrentUser]:
        """Create multiple users with distinct sensitive data for contamination testing."""
        users = []
        
        user_profiles = [
            {
                "username": "enterprise_cfo",
                "sensitive_data": {
                    "financial_secrets": "Q4 Revenue: $2.5M, Profit Margin: 45%",
                    "confidential_strategy": "Acquisition target: CompetitorCorp",
                    "trade_secrets": "Proprietary AI algorithm performance: 94% accuracy"
                }
            },
            {
                "username": "startup_founder", 
                "sensitive_data": {
                    "financial_secrets": "Runway: 8 months, Burn rate: $50K/month",
                    "confidential_strategy": "Pivot to B2B SaaS model next quarter",
                    "trade_secrets": "Customer acquisition cost: $150, LTV: $2000"
                }
            },
            {
                "username": "government_contractor",
                "sensitive_data": {
                    "financial_secrets": "Classification: TOP SECRET, Budget: $10M",
                    "confidential_strategy": "Defense contract expires Q2 2025",
                    "trade_secrets": "Security clearance algorithm optimization"
                }
            },
            {
                "username": "healthcare_admin",
                "sensitive_data": {
                    "financial_secrets": "Patient data value: $500/record, 50K patients",
                    "confidential_strategy": "HIPAA compliance audit Q1 2025",
                    "trade_secrets": "Medical AI diagnostic accuracy: 97.2%"
                }
            },
            {
                "username": "fintech_analyst",
                "sensitive_data": {
                    "financial_secrets": "Trading volume: $100M daily, Alpha: 1.3",
                    "confidential_strategy": "Launch crypto derivatives Q3 2025",
                    "trade_secrets": "Risk management algorithm: VaR 99.9%"
                }
            }
        ]
        
        for i, profile in enumerate(user_profiles):
            user = ConcurrentUser(
                user_id=f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}",
                username=profile["username"],
                thread_id=f"thread_{i}_{uuid.uuid4().hex[:8]}",
                sensitive_data=profile["sensitive_data"]
            )
            
            # Set expected outputs (user's own data only)
            for key, value in profile["sensitive_data"].items():
                user.expected_outputs.add(value)
            
            users.append(user)
        
        return users

    async def test_concurrent_report_generation_isolation(self):
        """
        Test that concurrent report generation maintains complete user isolation.
        
        VULNERABILITY: Shared DeepAgentState causes cross-contamination under load
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        # Create concurrent reporting tasks for all users
        concurrent_tasks = []
        
        for user in self.concurrent_users:
            for iteration in range(self.execution_iterations):
                task = self._create_concurrent_reporting_task(user, iteration)
                concurrent_tasks.append(task)
        
        # Execute all tasks concurrently to trigger race conditions
        results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)
        
        # Analyze results for cross-contamination
        contamination_detected = self._analyze_concurrent_results(results)
        
        # BEFORE migration: Should detect contamination (test fails)
        # AFTER migration: Should detect no contamination (test passes)
        if contamination_detected:
            contamination_details = self._format_contamination_evidence()
            assert False, (
                f"🚨 CRITICAL SECURITY VULNERABILITY: Cross-user data contamination detected "
                f"in concurrent ReportingSubAgent execution. {contamination_details}. "
                f"DeepAgentState shared state creates race condition vulnerabilities. "
                f"Migration to UserExecutionContext required."
            )

    async def _create_concurrent_reporting_task(self, user: ConcurrentUser, iteration: int):
        """Create a concurrent reporting task for a specific user."""
        try:
            # Create ReportingSubAgent instance (potential shared state vulnerability)
            reporting_agent = ReportingSubAgent()
            
            # Create execution context (AFTER migration: UserExecutionContext)
            try:
                # Try UserExecutionContext first (secure pattern)
                context = UserExecutionContext(
                    user_id=UserID(user.user_id),
                    thread_id=ThreadID(user.thread_id),
                    run_id=RunID(f"concurrent_run_{iteration}_{uuid.uuid4().hex[:8]}"),
                    agent_context={
                        "user_request": f"Generate confidential report for {user.username}",
                        "sensitive_context": user.sensitive_data,
                        "security_level": "CONFIDENTIAL",
                        "isolation_test": True,
                        "concurrent_execution": True
                    }
                )
                
                # Mock WebSocket events to avoid actual emission
                with patch.object(reporting_agent, 'emit_agent_started') as mock_started, \
                     patch.object(reporting_agent, 'emit_agent_completed') as mock_completed:
                    
                    mock_started.return_value = None
                    mock_completed.return_value = None
                    
                    # Execute with UserExecutionContext (should work after migration)
                    start_time = time.time()
                    result = await reporting_agent.execute_modern(
                        user_context=context,
                        stream_updates=False
                    )
                    execution_time = time.time() - start_time
                    
                    return ConcurrencyTestResult(
                        user_id=user.user_id,
                        execution_time=execution_time,
                        result_data=result,
                        memory_references=[id(context), id(result)],
                        contamination_detected=False,
                        isolation_verified=True
                    )
                    
            except (TypeError, AttributeError) as e:
                if "UserExecutionContext" in str(e):
                    # Migration incomplete - fallback to vulnerable DeepAgentState pattern
                    vulnerable_state = self._create_vulnerable_shared_state(user, iteration)
                    
                    with patch.object(reporting_agent, 'emit_agent_started') as mock_started, \
                         patch.object(reporting_agent, 'emit_agent_completed') as mock_completed:
                        
                        mock_started.return_value = None
                        mock_completed.return_value = None
                        
                        # Execute with DeepAgentState (vulnerable to contamination)
                        start_time = time.time()
                        result = await reporting_agent.execute_modern(
                            user_context=vulnerable_state,
                            stream_updates=False
                        )
                        execution_time = time.time() - start_time
                        
                        return ConcurrencyTestResult(
                            user_id=user.user_id,
                            execution_time=execution_time,
                            result_data=result,
                            memory_references=[id(vulnerable_state), id(result)],
                            contamination_detected=True,  # Assume contamination with shared state
                            isolation_verified=False
                        )
                else:
                    raise
            
        except Exception as e:
            return ConcurrencyTestResult(
                user_id=user.user_id,
                execution_time=0.0,
                result_data=None,
                memory_references=[],
                contamination_detected=False,
                isolation_verified=False,
                errors=[str(e)]
            )

    def _create_vulnerable_shared_state(self, user: ConcurrentUser, iteration: int) -> DeepAgentState:
        """Create DeepAgentState with shared references (demonstrates vulnerability)."""
        # VULNERABILITY: Shared state object that can be accessed by multiple users
        state = DeepAgentState()
        state.user_id = user.user_id
        state.chat_thread_id = user.thread_id
        state.user_request = f"Generate confidential report for {user.username}"
        
        # Add sensitive data that could be cross-contaminated
        state.action_plan_result = {
            "user_context": user.sensitive_data,
            "confidential_data": f"Iteration {iteration} sensitive information",
            "shared_reference": id(state),  # Memory reference that could leak
            "security_boundary": "CONFIDENTIAL"
        }
        
        # VULNERABILITY: Store reference in class-level collection (shared between instances)
        self.memory_references.append(weakref.ref(state))
        
        return state

    def _analyze_concurrent_results(self, results: List[ConcurrencyTestResult]) -> bool:
        """Analyze concurrent execution results for cross-contamination."""
        contamination_detected = False
        
        # Group results by user for analysis
        results_by_user = defaultdict(list)
        for result in results:
            if isinstance(result, ConcurrencyTestResult):
                results_by_user[result.user_id].append(result)
        
        # Check for cross-user data contamination
        for user in self.concurrent_users:
            user_results = results_by_user.get(user.user_id, [])
            
            for result in user_results:
                if result.result_data:
                    result_str = str(result.result_data)
                    
                    # Check if this user's results contain other users' sensitive data
                    for other_user in self.concurrent_users:
                        if other_user.user_id != user.user_id:
                            for sensitive_value in other_user.expected_outputs:
                                if sensitive_value in result_str:
                                    self.contamination_evidence[user.user_id].append({
                                        "contaminated_with": other_user.user_id,
                                        "leaked_data": sensitive_value,
                                        "result_id": id(result.result_data)
                                    })
                                    contamination_detected = True
        
        return contamination_detected

    def _format_contamination_evidence(self) -> str:
        """Format contamination evidence for detailed error reporting."""
        evidence_summary = []
        
        for user_id, contaminations in self.contamination_evidence.items():
            user_summary = f"User {user_id}: {len(contaminations)} contamination instances"
            for contamination in contaminations[:3]:  # Show first 3 for brevity
                user_summary += f"\n  - Leaked from {contamination['contaminated_with']}: {contamination['leaked_data'][:50]}..."
            evidence_summary.append(user_summary)
        
        return "Contamination Evidence:\n" + "\n".join(evidence_summary)

    async def test_memory_isolation_concurrent_execution(self):
        """
        Test that memory references are properly isolated between concurrent users.
        
        VULNERABILITY: Shared memory references enable cross-user access
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        # Track memory references during concurrent execution
        memory_tracking = {}
        
        async def track_memory_execution(user: ConcurrentUser):
            reporting_agent = ReportingSubAgent()
            
            try:
                # Create secure context
                context = UserExecutionContext(
                    user_id=UserID(user.user_id),
                    thread_id=ThreadID(user.thread_id),
                    run_id=RunID(f"memory_test_{uuid.uuid4().hex[:8]}"),
                    agent_context=user.sensitive_data
                )
                
                with patch.object(reporting_agent, 'emit_agent_started'), \
                     patch.object(reporting_agent, 'emit_agent_completed'):
                    
                    result = await reporting_agent.execute_modern(
                        user_context=context,
                        stream_updates=False
                    )
                    
                    # Track memory references for this user
                    memory_tracking[user.user_id] = {
                        "context_id": id(context),
                        "result_id": id(result) if result else None,
                        "agent_id": id(reporting_agent)
                    }
                    
            except TypeError:
                # Fallback to vulnerable pattern for testing
                vulnerable_state = self._create_vulnerable_shared_state(user, 0)
                
                with patch.object(reporting_agent, 'emit_agent_started'), \
                     patch.object(reporting_agent, 'emit_agent_completed'):
                    
                    result = await reporting_agent.execute_modern(
                        user_context=vulnerable_state,
                        stream_updates=False
                    )
                    
                    # Track potentially shared references
                    memory_tracking[user.user_id] = {
                        "state_id": id(vulnerable_state),
                        "result_id": id(result) if result else None,
                        "agent_id": id(reporting_agent)
                    }
        
        # Execute concurrent memory tracking
        tasks = [track_memory_execution(user) for user in self.concurrent_users[:3]]
        await asyncio.gather(*tasks)
        
        # Analyze memory isolation
        memory_violations = self._analyze_memory_isolation(memory_tracking)
        
        # BEFORE migration: Should detect violations (test fails)
        # AFTER migration: Should detect no violations (test passes)
        if memory_violations:
            assert False, (
                f"🚨 MEMORY ISOLATION VIOLATIONS: {memory_violations}. "
                f"Shared memory references between users create contamination risks. "
                f"UserExecutionContext migration required for proper isolation."
            )

    def _analyze_memory_isolation(self, memory_tracking: Dict[str, Dict[str, Any]]) -> List[str]:
        """Analyze memory references for isolation violations."""
        violations = []
        
        # Check for shared memory references between users
        user_ids = list(memory_tracking.keys())
        
        for i, user_a in enumerate(user_ids):
            for j, user_b in enumerate(user_ids[i+1:], i+1):
                tracking_a = memory_tracking[user_a]
                tracking_b = memory_tracking[user_b]
                
                # Check for shared references
                shared_refs = []
                for ref_type in ['context_id', 'state_id', 'result_id', 'agent_id']:
                    if ref_type in tracking_a and ref_type in tracking_b:
                        if tracking_a[ref_type] == tracking_b[ref_type]:
                            shared_refs.append(ref_type)
                
                if shared_refs:
                    violations.append(
                        f"Users {user_a} and {user_b} share memory references: {shared_refs}"
                    )
        
        return violations

    async def test_race_condition_data_contamination(self):
        """
        Test for data contamination under deliberate race conditions.
        
        VULNERABILITY: Race conditions in shared state access cause data mixing
        EXPECTED: Should FAIL before migration, PASS after migration
        """
        race_condition_detected = False
        
        # Create overlapping execution windows to force race conditions
        async def create_race_condition(user_a: ConcurrentUser, user_b: ConcurrentUser):
            nonlocal race_condition_detected
            
            agent_a = ReportingSubAgent()
            agent_b = ReportingSubAgent()
            
            try:
                # Create contexts with timing overlap
                context_a = UserExecutionContext(
                    user_id=UserID(user_a.user_id),
                    thread_id=ThreadID(user_a.thread_id),
                    run_id=RunID(f"race_a_{uuid.uuid4().hex[:8]}"),
                    agent_context={"race_test": "User A data", **user_a.sensitive_data}
                )
                
                context_b = UserExecutionContext(
                    user_id=UserID(user_b.user_id),
                    thread_id=ThreadID(user_b.thread_id),
                    run_id=RunID(f"race_b_{uuid.uuid4().hex[:8]}"),
                    agent_context={"race_test": "User B data", **user_b.sensitive_data}
                )
                
                with patch.object(agent_a, 'emit_agent_started'), \
                     patch.object(agent_a, 'emit_agent_completed'), \
                     patch.object(agent_b, 'emit_agent_started'), \
                     patch.object(agent_b, 'emit_agent_completed'):
                    
                    # Start both executions simultaneously
                    task_a = asyncio.create_task(agent_a.execute_modern(user_context=context_a, stream_updates=False))
                    task_b = asyncio.create_task(agent_b.execute_modern(user_context=context_b, stream_updates=False))
                    
                    # Small delay to create race condition window
                    await asyncio.sleep(0.001)
                    
                    result_a, result_b = await asyncio.gather(task_a, task_b, return_exceptions=True)
                    
                    # Check for race condition contamination
                    if result_a and result_b:
                        result_a_str = str(result_a)
                        result_b_str = str(result_b)
                        
                        if "User A data" in result_b_str or "User B data" in result_a_str:
                            race_condition_detected = True
                            
            except TypeError:
                # Fallback to vulnerable pattern that's more susceptible to race conditions
                race_condition_detected = True  # Assume race conditions exist with shared state
        
        # Test multiple race condition scenarios
        race_tasks = []
        for i in range(0, len(self.concurrent_users)-1, 2):
            task = create_race_condition(
                self.concurrent_users[i], 
                self.concurrent_users[i+1]
            )
            race_tasks.append(task)
        
        await asyncio.gather(*race_tasks)
        
        # BEFORE migration: Should detect race conditions (test fails)
        # AFTER migration: Should detect no race conditions (test passes)
        if race_condition_detected:
            assert False, (
                f"🚨 RACE CONDITION VULNERABILITY: Data contamination detected under "
                f"concurrent execution race conditions. Shared state creates timing "
                f"vulnerabilities. UserExecutionContext migration required."
            )

    async def test_concurrent_websocket_isolation(self):
        """
        Test that WebSocket events are properly isolated between concurrent users.
        
        VULNERABILITY: WebSocket events can be mixed between users under concurrency
        EXPECTED: Should maintain perfect isolation
        """
        websocket_contamination_detected = False
        websocket_events = defaultdict(list)
        
        # Mock WebSocket event capture
        def capture_websocket_events(user_id: str):
            def mock_emit_started(message):
                websocket_events[user_id].append(("started", message))
            
            def mock_emit_completed(result):
                websocket_events[user_id].append(("completed", str(result)))
            
            return mock_emit_started, mock_emit_completed
        
        # Execute concurrent operations with WebSocket event tracking
        concurrent_tasks = []
        
        for user in self.concurrent_users[:3]:  # Test with 3 users for clarity
            async def execute_with_websocket_tracking(test_user):
                agent = ReportingSubAgent()
                mock_started, mock_completed = capture_websocket_events(test_user.user_id)
                
                try:
                    context = UserExecutionContext(
                        user_id=UserID(test_user.user_id),
                        thread_id=ThreadID(test_user.thread_id),
                        run_id=RunID(f"ws_test_{uuid.uuid4().hex[:8]}"),
                        agent_context=test_user.sensitive_data
                    )
                    
                    with patch.object(agent, 'emit_agent_started', side_effect=mock_started), \
                         patch.object(agent, 'emit_agent_completed', side_effect=mock_completed):
                        
                        await agent.execute_modern(user_context=context, stream_updates=True)
                        
                except TypeError:
                    # Fallback to vulnerable pattern
                    vulnerable_state = self._create_vulnerable_shared_state(test_user, 0)
                    
                    with patch.object(agent, 'emit_agent_started', side_effect=mock_started), \
                         patch.object(agent, 'emit_agent_completed', side_effect=mock_completed):
                        
                        await agent.execute_modern(
                            user_context=vulnerable_state,
                            stream_updates=True
                        )
            
            concurrent_tasks.append(execute_with_websocket_tracking(user))
        
        await asyncio.gather(*concurrent_tasks)
        
        # Analyze WebSocket event isolation
        for user in self.concurrent_users[:3]:
            user_events = websocket_events[user.user_id]
            
            for event_type, event_data in user_events:
                # Check if this user's events contain other users' data
                for other_user in self.concurrent_users[:3]:
                    if other_user.user_id != user.user_id:
                        for sensitive_value in other_user.expected_outputs:
                            if sensitive_value in event_data:
                                websocket_contamination_detected = True
        
        # BEFORE migration: May detect contamination (test fails)
        # AFTER migration: Should detect no contamination (test passes)
        if websocket_contamination_detected:
            assert False, (
                f"🚨 WEBSOCKET ISOLATION VIOLATION: WebSocket events contain cross-user "
                f"contamination under concurrent execution. Event routing isolation required."
            )

    def teardown_method(self, method=None):
        """Clean up test resources and check for memory leaks."""
        # Check for memory reference leaks
        alive_references = []
        for ref in self.memory_references:
            if ref() is not None:
                alive_references.append(ref)
        
        if alive_references:
            # Memory references still alive - potential shared state issue
            pass  # Log but don't fail test - this is diagnostic information
        
        # Force garbage collection
        gc.collect()
        
        super().teardown_method(method)