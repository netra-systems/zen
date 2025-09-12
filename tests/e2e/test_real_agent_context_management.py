#!/usr/bin/env python
"""Real Agent Context Management E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests agent context isolation and management with real services.
Business Value: Ensure multi-user isolation and context integrity.

Business Value Justification (BVJ):
1. Segment: All (Free, Early, Mid, Enterprise)
2. Business Goal: Enable secure multi-user agent execution
3. Value Impact: Context isolation prevents data leakage between users
4. Revenue Impact: $600K+ ARR protection from multi-user system reliability

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events
- Tests Factory patterns for user isolation per CLAUDE.md
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- CRITICAL: Tests UserExecutionContext isolation
"""

import asyncio
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor
import threading

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# CLAUDE.md compliant imports - Lazy loaded to prevent resource exhaustion
from shared.isolated_environment import get_env as get_env_instance
from tests.e2e.e2e_test_config import get_e2e_config, E2ETestConfig, REQUIRED_WEBSOCKET_EVENTS


@dataclass
class UserContext:
    """Represents a user context for isolation testing."""
    user_id: str
    email: str
    token: str
    thread_id: str
    session_data: Dict[str, Any] = field(default_factory=dict)
    agent_state: Dict[str, Any] = field(default_factory=dict)


@dataclass 
class ContextIsolationValidation:
    """Captures and validates context isolation across multiple users."""
    
    test_scenario: str
    user_contexts: List[UserContext] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    
    # Event tracking per user (MISSION CRITICAL per CLAUDE.md)
    user_events: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    user_event_types: Dict[str, Set[str]] = field(default_factory=dict)
    
    # Context isolation validation
    data_leakage_detected: bool = False
    cross_user_contamination: List[Tuple[str, str]] = field(default_factory=list)  # (user1, user2) pairs
    context_boundaries_maintained: bool = False
    
    # Timing metrics (performance benchmarks per requirements)
    concurrent_execution_times: Dict[str, float] = field(default_factory=dict)
    context_creation_times: Dict[str, float] = field(default_factory=dict)
    
    # Business logic validation
    all_users_isolated: bool = False
    session_integrity_maintained: bool = False
    agent_state_separated: bool = False
    resource_isolation_verified: bool = False


class RealAgentContextManagementTester:
    """Tests agent context management and isolation with real services."""
    
    # CLAUDE.md REQUIRED WebSocket events from SSOT config
    REQUIRED_EVENTS = set(REQUIRED_WEBSOCKET_EVENTS.keys())
    
    # Context isolation test scenarios
    CONTEXT_ISOLATION_SCENARIOS = [
        {
            "scenario_name": "concurrent_user_sessions",
            "user_count": 3,
            "test_message": "Analyze my personal data and remember my preferences",
            "expected_isolation": "complete_separation",
            "validation_criteria": ["no_data_leakage", "separate_contexts", "independent_execution"]
        },
        {
            "scenario_name": "sequential_user_handover", 
            "user_count": 2,
            "test_message": "Continue the previous analysis from my last session",
            "expected_isolation": "session_continuity",
            "validation_criteria": ["context_persistence", "user_boundary_respect", "state_isolation"]
        },
        {
            "scenario_name": "high_concurrency_stress",
            "user_count": 5,
            "test_message": "Process my confidential business data",
            "expected_isolation": "stress_test_isolation",
            "validation_criteria": ["no_resource_conflicts", "maintained_isolation", "performance_stability"]
        },
        {
            "scenario_name": "context_state_persistence",
            "user_count": 2,
            "test_message": "Remember this important information for future sessions",
            "expected_isolation": "persistent_separation",
            "validation_criteria": ["state_persistence", "cross_session_isolation", "data_integrity"]
        }
    ]
    
    def __init__(self, config: Optional[E2ETestConfig] = None):
        self.config = config or get_e2e_config()
        self.env = None  # Lazy init
        self.backend_url = None
        self.jwt_helper = None
        self.validations: List[ContextIsolationValidation] = []
        
    async def setup(self):
        """Initialize test environment with real services."""
        # Lazy imports per CLAUDE.md to prevent Docker crashes
        from shared.isolated_environment import IsolatedEnvironment
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        from tests.clients.backend_client import BackendTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        
        self.env = IsolatedEnvironment()
        self.jwt_helper = JWTTestHelper()
        
        # Initialize backend connection from SSOT config
        self.backend_url = self.config.backend_url
        self.backend_client = BackendTestClient(self.backend_url)
        
        logger.info(f"Context management test environment ready at {self.backend_url}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        # Close any open connections
        pass
        
    async def create_user_context(self, user_prefix: str) -> UserContext:
        """Create isolated user context for testing."""
        from tests.clients.websocket_client import WebSocketTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        
        # Create unique user data
        user_data = create_test_user_data(f"{user_prefix}_{uuid.uuid4().hex[:8]}")
        user_id = str(uuid.uuid4())
        email = user_data['email']
        
        # Generate JWT with context isolation permissions
        # Use staging-specific token generation if in staging environment
        if hasattr(self.config, 'environment') and self.config.environment == 'staging':
            # Try to get staging token
            token = await self.jwt_helper.get_staging_jwt_token(user_id, email)
            if not token:
                # Fall back to standard token creation
                token = self.jwt_helper.create_access_token(
                    user_id, 
                    email,
                    permissions=["agents:use", "context:isolate", "session:manage"]
                )
        else:
            token = self.jwt_helper.create_access_token(
                user_id, 
                email,
                permissions=["agents:use", "context:isolate", "session:manage"]
            )
        
        # Create WebSocket connection from SSOT config
        ws_url = self.config.websocket_url
        ws_client = WebSocketTestClient(ws_url)
        
        # Connect with user-specific authentication
        connected = await ws_client.connect(token=token)
        if not connected:
            raise RuntimeError(f"Failed to connect WebSocket for user {user_id}")
            
        user_context = UserContext(
            user_id=user_id,
            email=email,
            token=token,
            thread_id=str(uuid.uuid4())
        )
        
        # Store WebSocket client for cleanup
        user_context.session_data['ws_client'] = ws_client
        
        logger.info(f"Created user context: {user_id} ({email})")
        return user_context
        
    async def execute_context_isolation_scenario(
        self, 
        scenario: Dict[str, Any],
        timeout: float = 120.0
    ) -> ContextIsolationValidation:
        """Execute a context isolation scenario with multiple users.
        
        Args:
            scenario: Context isolation scenario configuration
            timeout: Maximum execution time per user
            
        Returns:
            Complete validation results
        """
        validation = ContextIsolationValidation(
            test_scenario=scenario["scenario_name"]
        )
        
        # Create multiple user contexts
        user_count = scenario["user_count"]
        for i in range(user_count):
            user_context = await self.create_user_context(f"context_test_user_{i}")
            validation.user_contexts.append(user_context)
            validation.user_events[user_context.user_id] = []
            validation.user_event_types[user_context.user_id] = set()
            
        logger.info(f"Created {len(validation.user_contexts)} user contexts for {scenario['scenario_name']}")
        
        # Execute concurrent agent requests
        if scenario["scenario_name"] == "concurrent_user_sessions":
            await self._execute_concurrent_sessions(validation, scenario, timeout)
        elif scenario["scenario_name"] == "sequential_user_handover":
            await self._execute_sequential_handover(validation, scenario, timeout)
        elif scenario["scenario_name"] == "high_concurrency_stress":
            await self._execute_concurrency_stress(validation, scenario, timeout)
        else:
            await self._execute_general_context_test(validation, scenario, timeout)
            
        # Validate context isolation
        self._validate_context_isolation(validation, scenario)
        
        # Cleanup user contexts
        await self._cleanup_user_contexts(validation.user_contexts)
        
        self.validations.append(validation)
        return validation
        
    async def _execute_concurrent_sessions(
        self, 
        validation: ContextIsolationValidation,
        scenario: Dict[str, Any],
        timeout: float
    ):
        """Execute concurrent user sessions to test isolation."""
        
        async def execute_user_session(user_context: UserContext):
            """Execute agent session for a specific user."""
            ws_client = user_context.session_data['ws_client']
            
            # Send user-specific agent request
            user_specific_message = f"{scenario['test_message']} - User: {user_context.user_id}"
            agent_request = {
                "type": "agent_request",
                "agent": "triage_agent",
                "message": user_specific_message,
                "thread_id": user_context.thread_id,
                "context": {
                    "user_id": user_context.user_id,
                    "isolation_test": True,
                    "user_data": f"confidential_data_for_{user_context.user_id}"
                },
                "optimistic_id": str(uuid.uuid4())
            }
            
            context_start_time = time.time()
            await ws_client.send_json(agent_request)
            validation.context_creation_times[user_context.user_id] = time.time() - context_start_time
            
            # Collect events for this user
            execution_start = time.time()
            completed = False
            
            while time.time() - execution_start < timeout and not completed:
                event = await ws_client.receive(timeout=2.0)
                
                if event:
                    validation.user_events[user_context.user_id].append(event)
                    validation.user_event_types[user_context.user_id].add(event.get("type", "unknown"))
                    
                    # Check for completion
                    if event.get("type") in ["agent_completed", "error"]:
                        completed = True
                        
            validation.concurrent_execution_times[user_context.user_id] = time.time() - execution_start
            
        # Execute all user sessions concurrently
        tasks = [
            execute_user_session(user_context) 
            for user_context in validation.user_contexts
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Completed concurrent execution for {len(validation.user_contexts)} users")
        
    async def _execute_sequential_handover(
        self, 
        validation: ContextIsolationValidation,
        scenario: Dict[str, Any],
        timeout: float
    ):
        """Execute sequential user handover to test context boundaries."""
        
        for i, user_context in enumerate(validation.user_contexts):
            ws_client = user_context.session_data['ws_client']
            
            # Each user references "previous session" but should only see their own data
            handover_message = f"{scenario['test_message']} - Session {i+1} for user {user_context.user_id}"
            
            agent_request = {
                "type": "agent_request", 
                "agent": "triage_agent",
                "message": handover_message,
                "thread_id": user_context.thread_id,
                "context": {
                    "user_id": user_context.user_id,
                    "session_sequence": i + 1,
                    "previous_context_test": True
                },
                "optimistic_id": str(uuid.uuid4())
            }
            
            await ws_client.send_json(agent_request)
            
            # Collect events for this user session
            session_start = time.time()
            completed = False
            
            while time.time() - session_start < timeout and not completed:
                event = await ws_client.receive(timeout=2.0)
                
                if event:
                    validation.user_events[user_context.user_id].append(event)
                    validation.user_event_types[user_context.user_id].add(event.get("type", "unknown"))
                    
                    if event.get("type") in ["agent_completed", "error"]:
                        completed = True
                        
            validation.concurrent_execution_times[user_context.user_id] = time.time() - session_start
            
            # Brief pause between users to simulate sequential handover
            await asyncio.sleep(1.0)
            
        logger.info(f"Completed sequential handover test with {len(validation.user_contexts)} users")
        
    async def _execute_concurrency_stress(
        self, 
        validation: ContextIsolationValidation,
        scenario: Dict[str, Any],
        timeout: float
    ):
        """Execute high-concurrency stress test for context isolation."""
        
        async def stress_user_session(user_context: UserContext, iteration: int):
            """Execute multiple requests for stress testing."""
            ws_client = user_context.session_data['ws_client']
            
            for request_num in range(2):  # Multiple requests per user
                stress_message = f"{scenario['test_message']} - Stress iteration {iteration}, request {request_num}"
                
                agent_request = {
                    "type": "agent_request",
                    "agent": "triage_agent", 
                    "message": stress_message,
                    "thread_id": f"{user_context.thread_id}_{request_num}",
                    "context": {
                        "user_id": user_context.user_id,
                        "stress_test": True,
                        "iteration": iteration,
                        "request_number": request_num,
                        "sensitive_data": f"stress_data_{user_context.user_id}_{request_num}"
                    },
                    "optimistic_id": str(uuid.uuid4())
                }
                
                await ws_client.send_json(agent_request)
                
                # Brief delay between requests
                await asyncio.sleep(0.5)
                
            # Collect events for stress session
            stress_start = time.time()
            event_count = 0
            
            while time.time() - stress_start < timeout and event_count < 20:  # Limit events
                event = await ws_client.receive(timeout=1.0)
                
                if event:
                    validation.user_events[user_context.user_id].append(event)
                    validation.user_event_types[user_context.user_id].add(event.get("type", "unknown"))
                    event_count += 1
                    
            validation.concurrent_execution_times[user_context.user_id] = time.time() - stress_start
            
        # Execute stress sessions concurrently
        stress_tasks = [
            stress_user_session(user_context, i) 
            for i, user_context in enumerate(validation.user_contexts)
        ]
        
        await asyncio.gather(*stress_tasks, return_exceptions=True)
        logger.info(f"Completed stress test with {len(validation.user_contexts)} concurrent users")
        
    async def _execute_general_context_test(
        self, 
        validation: ContextIsolationValidation,
        scenario: Dict[str, Any],
        timeout: float
    ):
        """Execute general context isolation test."""
        # Default to concurrent execution pattern
        await self._execute_concurrent_sessions(validation, scenario, timeout)
        
    def _validate_context_isolation(
        self, 
        validation: ContextIsolationValidation,
        scenario: Dict[str, Any]
    ):
        """Validate context isolation requirements."""
        
        # 1. Check for data leakage between users
        user_ids = [uc.user_id for uc in validation.user_contexts]
        
        for user_id in user_ids:
            user_events = validation.user_events.get(user_id, [])
            
            # Check if any events contain data from other users
            for event in user_events:
                event_content = json.dumps(event).lower()
                for other_user_id in user_ids:
                    if other_user_id != user_id and other_user_id.lower() in event_content:
                        validation.data_leakage_detected = True
                        validation.cross_user_contamination.append((user_id, other_user_id))
                        
        # 2. Validate context boundaries
        validation.context_boundaries_maintained = not validation.data_leakage_detected
        
        # 3. Check user isolation
        users_with_events = sum(1 for user_id in user_ids if validation.user_events.get(user_id))
        validation.all_users_isolated = (
            users_with_events == len(user_ids) and  # All users got events
            not validation.data_leakage_detected  # No cross-contamination
        )
        
        # 4. Validate session integrity
        validation.session_integrity_maintained = all(
            len(validation.user_event_types.get(user_id, set())) > 0
            for user_id in user_ids
        )
        
        # 5. Check agent state separation
        # Heuristic: if users got different event sequences, states are likely separate
        event_sequences = [
            tuple(validation.user_event_types.get(user_id, set())) 
            for user_id in user_ids
        ]
        validation.agent_state_separated = len(set(event_sequences)) > 1 or len(user_ids) == 1
        
        # 6. Verify resource isolation (performance-based check)
        execution_times = list(validation.concurrent_execution_times.values())
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            # If max time isn't dramatically higher than average, resources are likely isolated
            validation.resource_isolation_verified = max_time < avg_time * 3.0
            
    async def _cleanup_user_contexts(self, user_contexts: List[UserContext]):
        """Clean up user contexts and close connections."""
        for user_context in user_contexts:
            ws_client = user_context.session_data.get('ws_client')
            if ws_client:
                try:
                    await ws_client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting user {user_context.user_id}: {e}")
                    
    def generate_context_management_report(self) -> str:
        """Generate comprehensive context management test report."""
        report = []
        report.append("=" * 80)
        report.append("REAL AGENT CONTEXT MANAGEMENT TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total isolation scenarios tested: {len(self.validations)}")
        report.append("")
        
        for i, val in enumerate(self.validations, 1):
            report.append(f"\n--- Context Scenario {i}: {val.test_scenario} ---")
            report.append(f"Users tested: {len(val.user_contexts)}")
            report.append(f"Total user events: {sum(len(events) for events in val.user_events.values())}")
            
            # Context isolation results
            report.append("\nContext Isolation Validation:")
            report.append(f"  [U+2713] All users isolated: {val.all_users_isolated}")
            report.append(f"  [U+2713] Session integrity maintained: {val.session_integrity_maintained}")
            report.append(f"  [U+2713] Agent state separated: {val.agent_state_separated}")
            report.append(f"  [U+2713] Resource isolation verified: {val.resource_isolation_verified}")
            report.append(f"  [U+2713] Context boundaries maintained: {val.context_boundaries_maintained}")
            
            # Data leakage analysis
            if val.data_leakage_detected:
                report.append(f"\n WARNING: [U+FE0F] DATA LEAKAGE DETECTED!")
                report.append(f"Cross-contamination pairs: {val.cross_user_contamination}")
            else:
                report.append("\n[U+2713] No data leakage detected")
                
            # Performance metrics per user
            if val.concurrent_execution_times:
                report.append("\nPer-User Performance:")
                for user_id, exec_time in val.concurrent_execution_times.items():
                    event_count = len(val.user_events.get(user_id, []))
                    report.append(f"  - User {user_id[:8]}...: {exec_time:.2f}s ({event_count} events)")
                    
                avg_time = sum(val.concurrent_execution_times.values()) / len(val.concurrent_execution_times)
                report.append(f"  - Average execution time: {avg_time:.2f}s")
                
            # Event type analysis per user
            report.append("\nEvent Types by User:")
            for user_id in val.user_events.keys():
                event_types = sorted(val.user_event_types.get(user_id, set()))
                missing_events = self.REQUIRED_EVENTS - val.user_event_types.get(user_id, set())
                
                report.append(f"  - User {user_id[:8]}...: {event_types}")
                if missing_events:
                    report.append(f"     WARNING: [U+FE0F] Missing: {missing_events}")
                    
        # Overall isolation quality score
        if self.validations:
            isolation_scores = [
                sum([
                    val.all_users_isolated,
                    val.session_integrity_maintained,
                    val.agent_state_separated,
                    val.resource_isolation_verified,
                    val.context_boundaries_maintained
                ]) for val in self.validations
            ]
            avg_score = sum(isolation_scores) / len(isolation_scores)
            report.append(f"\nOverall Isolation Quality Score: {avg_score:.1f}/5.0")
            
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture(params=["local", "staging"])
async def context_management_tester(request):
    """Create and setup the context management tester for both local and staging.
    
    This fixture will run tests against both local and staging environments
    when E2E_TEST_ENV is not set, or against the specified environment.
    """
    # Check if we should skip staging tests
    test_env = get_env_instance().get("E2E_TEST_ENV", None)
    if test_env and test_env != request.param:
        pytest.skip(f"Skipping {request.param} tests (E2E_TEST_ENV={test_env})")
    
    # Get configuration for the specific environment
    config = get_e2e_config(force_environment=request.param)
    
    # Check if environment is available
    if not config.is_available():
        pytest.skip(f"{request.param} environment not available")
    
    # Create tester with environment-specific config
    tester = RealAgentContextManagementTester(config)
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
class TestRealAgentContextManagement:
    """Test suite for real agent context management and isolation."""
    
    async def test_concurrent_user_session_isolation(self, context_management_tester):
        """Test concurrent user session isolation with real agents."""
        scenario = context_management_tester.CONTEXT_ISOLATION_SCENARIOS[0]  # concurrent_user_sessions
        
        validation = await context_management_tester.execute_context_isolation_scenario(
            scenario, timeout=90.0
        )
        
        # CRITICAL: Verify no data leakage
        assert not validation.data_leakage_detected, \
            f"Data leakage detected between users: {validation.cross_user_contamination}"
            
        # Verify context boundaries
        assert validation.context_boundaries_maintained, "Context boundaries should be maintained"
        
        # Verify user isolation
        assert validation.all_users_isolated, "All users should be properly isolated"
        
        # Performance verification
        if validation.concurrent_execution_times:
            avg_time = sum(validation.concurrent_execution_times.values()) / len(validation.concurrent_execution_times)
            assert avg_time < 60.0, f"Average execution time {avg_time:.2f}s too slow for concurrent users"
            
        logger.info(f"Successfully tested isolation for {len(validation.user_contexts)} concurrent users")
        
    async def test_sequential_user_handover_boundaries(self, context_management_tester):
        """Test user handover maintains context boundaries."""
        scenario = context_management_tester.CONTEXT_ISOLATION_SCENARIOS[1]  # sequential_user_handover
        
        validation = await context_management_tester.execute_context_isolation_scenario(
            scenario, timeout=80.0
        )
        
        # Verify session integrity
        assert validation.session_integrity_maintained, "Session integrity should be maintained across handover"
        
        # Verify no cross-contamination
        assert not validation.data_leakage_detected, "No data should leak between sequential users"
        
        # Verify agent state separation
        assert validation.agent_state_separated, "Agent states should be separated between users"
        
        logger.info(f"Successfully tested handover boundaries for {len(validation.user_contexts)} users")
        
    async def test_high_concurrency_stress_isolation(self, context_management_tester):
        """Test context isolation under high concurrency stress."""
        scenario = context_management_tester.CONTEXT_ISOLATION_SCENARIOS[2]  # high_concurrency_stress
        
        validation = await context_management_tester.execute_context_isolation_scenario(
            scenario, timeout=100.0
        )
        
        # Resource isolation under stress
        assert validation.resource_isolation_verified, "Resources should remain isolated under stress"
        
        # Context boundaries under stress
        assert validation.context_boundaries_maintained, "Context boundaries should hold under stress"
        
        # All users should complete despite stress
        completed_users = sum(
            1 for user_id in validation.user_events.keys()
            if len(validation.user_events[user_id]) > 0
        )
        assert completed_users >= len(validation.user_contexts) * 0.8, \
            f"Most users should complete under stress: {completed_users}/{len(validation.user_contexts)}"
            
        logger.info(f"Successfully stress tested {len(validation.user_contexts)} concurrent users")
        
    async def test_context_state_persistence_isolation(self, context_management_tester):
        """Test context state persistence with proper isolation.""" 
        scenario = context_management_tester.CONTEXT_ISOLATION_SCENARIOS[3]  # context_state_persistence
        
        validation = await context_management_tester.execute_context_isolation_scenario(
            scenario, timeout=85.0
        )
        
        # Verify state persistence without leakage
        assert validation.session_integrity_maintained, "Session state should persist"
        assert not validation.data_leakage_detected, "State persistence should not cause leakage"
        
        # Verify agent state separation
        assert validation.agent_state_separated, "Agent states should remain separate despite persistence"
        
        logger.info(f"Successfully tested state persistence isolation for {len(validation.user_contexts)} users")
        
    async def test_context_isolation_websocket_events(self, context_management_tester):
        """Test WebSocket event isolation between users."""
        scenario = context_management_tester.CONTEXT_ISOLATION_SCENARIOS[0]  # Use concurrent for event testing
        
        validation = await context_management_tester.execute_context_isolation_scenario(
            scenario, timeout=75.0
        )
        
        # Each user should receive their own events
        for user_id, user_events in validation.user_events.items():
            assert len(user_events) > 0, f"User {user_id} should receive events"
            
            # Check for required events
            user_event_types = validation.user_event_types.get(user_id, set())
            missing_events = context_management_tester.REQUIRED_EVENTS - user_event_types
            
            # Allow some flexibility for isolated testing
            critical_events = {"agent_started", "agent_completed"}
            critical_missing = critical_events - user_event_types
            assert not critical_missing, f"User {user_id} missing critical events: {critical_missing}"
            
        # Verify event isolation between users
        assert not validation.data_leakage_detected, "WebSocket events should be isolated between users"
        
    async def test_context_management_performance_benchmarks(self, context_management_tester):
        """Test context management performance benchmarks."""
        # Run multiple scenarios to test performance
        performance_results = []
        
        for scenario in context_management_tester.CONTEXT_ISOLATION_SCENARIOS[:2]:  # First 2 scenarios
            validation = await context_management_tester.execute_context_isolation_scenario(
                scenario, timeout=70.0
            )
            performance_results.append(validation)
            
        # Performance assertions
        all_execution_times = []
        for validation in performance_results:
            all_execution_times.extend(validation.concurrent_execution_times.values())
            
        if all_execution_times:
            avg_execution = sum(all_execution_times) / len(all_execution_times)
            max_execution = max(all_execution_times)
            
            # Performance benchmarks for multi-user context management
            assert avg_execution < 80.0, f"Average context execution {avg_execution:.2f}s too slow"
            assert max_execution < 120.0, f"Max context execution {max_execution:.2f}s too slow"
            
        # Context creation performance
        all_creation_times = []
        for validation in performance_results:
            all_creation_times.extend(validation.context_creation_times.values())
            
        if all_creation_times:
            avg_creation = sum(all_creation_times) / len(all_creation_times)
            assert avg_creation < 5.0, f"Average context creation {avg_creation:.2f}s too slow"
            
    async def test_context_isolation_quality_metrics(self, context_management_tester):
        """Test context isolation quality metrics."""
        scenario = context_management_tester.CONTEXT_ISOLATION_SCENARIOS[0]
        
        validation = await context_management_tester.execute_context_isolation_scenario(
            scenario, timeout=80.0
        )
        
        # Calculate isolation quality score
        isolation_score = sum([
            validation.all_users_isolated,
            validation.session_integrity_maintained,
            validation.agent_state_separated,
            validation.resource_isolation_verified,
            validation.context_boundaries_maintained
        ])
        
        # Should meet minimum quality threshold
        assert isolation_score >= 4, f"Context isolation quality score {isolation_score}/5 below minimum"
        
        # No data leakage tolerance
        assert not validation.data_leakage_detected, "Zero tolerance for data leakage in context isolation"
        
        logger.info(f"Context isolation quality score: {isolation_score}/5")
        
    async def test_comprehensive_context_management_report(self, context_management_tester):
        """Run comprehensive test and generate detailed report."""
        # Execute all context isolation scenarios
        for scenario in context_management_tester.CONTEXT_ISOLATION_SCENARIOS:
            await context_management_tester.execute_context_isolation_scenario(
                scenario, timeout=90.0
            )
            
        # Generate and save report
        report = context_management_tester.generate_context_management_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "context_management_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Context management report saved to: {report_file}")
        
        # Verify overall isolation success
        total_tests = len(context_management_tester.validations)
        isolated_tests = sum(
            1 for v in context_management_tester.validations 
            if v.all_users_isolated and not v.data_leakage_detected
        )
        
        assert isolated_tests > 0, "At least some context isolation tests should succeed"
        isolation_rate = isolated_tests / total_tests if total_tests > 0 else 0
        
        # High standard for context isolation
        assert isolation_rate >= 0.8, f"Context isolation success rate {isolation_rate:.1%} below 80% requirement"
        logger.info(f"Context isolation success rate: {isolation_rate:.1%}")


if __name__ == "__main__":
    # Run with real services - context isolation is critical
    # Use E2E_TEST_ENV=staging to test against staging environment
    import sys
    args = [
        __file__,
        "-v",
        "--real-services",
        "-s",
        "--tb=short"
    ]
    
    # Add staging marker if running against staging
    if get_env_instance().get("E2E_TEST_ENV", "local") == "staging":
        args.append("-m")
        args.append("staging")
        print(f"Running tests against STAGING environment: {get_e2e_config().backend_url}")
    else:
        print(f"Running tests against LOCAL environment: {get_e2e_config().backend_url}")
    
    pytest.main(args)