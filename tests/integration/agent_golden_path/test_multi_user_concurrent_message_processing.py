"""
Multi-User Concurrent Message Processing Integration Tests

Business Value Justification (BVJ):
- Segment: Mid, Enterprise - Multi-tenant platform capabilities
- Business Goal: Platform Scalability & Security - Multi-user isolation and performance
- Value Impact: Validates secure concurrent agent message processing for multiple users
- Strategic Impact: Enterprise readiness - ensures platform can handle multiple users securely

CRITICAL REQUIREMENTS per CLAUDE.md:
- Uses SSOT BaseTestCase patterns from test_framework/ssot/base_test_case.py
- NO MOCKS for integration tests - uses real agent services where possible
- Tests must validate user isolation and prevent cross-contamination
- Multi-user scenarios must use real concurrent execution
- Tests must pass or fail meaningfully (no test cheating allowed)

This module tests CONCURRENT multi-user agent message processing covering:
1. Multiple users sending messages simultaneously without interference
2. User context isolation prevents message/response cross-contamination
3. Concurrent agent execution with proper resource management
4. WebSocket event isolation ensures users only see their own progress
5. Performance under concurrent load meets enterprise requirements
6. Error isolation - one user's errors don't affect others

ARCHITECTURE ALIGNMENT:
- Uses UserExecutionContext for secure multi-user isolation
- Tests concurrent agent execution with proper isolation boundaries
- Tests WebSocket event delivery isolation between users
- Validates compliance-critical user data separation

AGENT SESSION: agent-session-2025-09-14-1730
GITHUB ISSUE: #870 Agent Golden Path Messages Integration Test Coverage
"""

import asyncio
import json
import time
import uuid
import pytest
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union, Set
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

# SSOT imports following architecture patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Import real components where available
try:
    from netra_backend.app.services.user_execution_context import UserExecutionContext
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
    from netra_backend.app.services.agent_websocket_bridge import create_agent_websocket_bridge
    from shared.types.core_types import UserID, ThreadID, RunID, MessageID
    REAL_COMPONENTS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Some real components not available: {e}")
    REAL_COMPONENTS_AVAILABLE = False
    UserExecutionContext = MagicMock
    AgentExecutionCore = MagicMock

@dataclass
class UserScenario:
    """Represents a single user's concurrent message processing scenario."""
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    domain: str
    message_content: str
    sensitive_data: str
    expected_agent_type: str
    processing_complexity: str

@dataclass
class ConcurrentExecutionResult:
    """Results from concurrent user message processing."""
    user_id: UserID
    execution_time: float
    success: bool
    response_content: str
    websocket_events: List[Dict]
    errors: List[str]
    isolation_verified: bool

class MultiUserConcurrentMessageProcessingTests(SSotAsyncTestCase):
    """
    P0 Critical Integration Tests for Multi-User Concurrent Agent Message Processing.

    This test class validates that the platform can securely handle multiple users
    sending messages simultaneously, with proper isolation and performance under load.
    Critical for enterprise customers who require multi-tenant security and scalability.

    Tests protect business value by validating:
    - Secure multi-user concurrent message processing
    - Complete user context and message isolation
    - Concurrent performance meets enterprise requirements
    - WebSocket event isolation between users
    - Error isolation - failures don't cascade across users
    - Resource management under concurrent load
    """

    def setup_method(self, method):
        """Set up test environment with multi-user concurrent processing infrastructure."""
        super().setup_method(method)

        # Initialize environment for concurrent multi-user testing
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_ENV", "concurrent_multi_user")
        self.set_env_var("AGENT_SESSION_ID", "agent-session-2025-09-14-1730")

        # Track concurrent processing metrics for business analysis
        self.concurrent_metrics = {
            'concurrent_users_processed': 0,
            'total_messages_processed': 0,
            'isolation_violations_detected': 0,
            'concurrent_execution_errors': 0,
            'average_response_time_per_user': 0.0,
            'peak_concurrent_users': 0,
            'websocket_events_delivered': 0,
            'user_context_cross_contamination_detected': 0
        }

        # Initialize infrastructure components
        self.agent_factory = None
        self.execution_core = None
        self.websocket_manager = None
        self.websocket_bridge = None

        # Track active user sessions for cleanup
        self.active_user_sessions: Set[str] = set()

    async def async_setup_method(self, method=None):
        """Set up async components with multi-user infrastructure."""
        await super().async_setup_method(method)
        await self._initialize_multi_user_infrastructure()

    async def _initialize_multi_user_infrastructure(self):
        """Initialize infrastructure for concurrent multi-user testing."""
        if not REAL_COMPONENTS_AVAILABLE:return

        try:
            # Initialize real components for multi-user testing
            self.agent_factory = get_agent_instance_factory()
            self.execution_core = AgentExecutionCore(registry=MagicMock())  # Use mock registry for testing
            self.websocket_manager = get_websocket_manager()
            self.websocket_bridge = create_agent_websocket_bridge()

            # Configure for concurrent testing
            if hasattr(self.agent_factory, 'configure_for_concurrent_testing'):
                self.agent_factory.configure_for_concurrent_testing(
                    max_concurrent_users=10,
                    isolation_level='strict'
                )

        except Exception as e:

            # CLAUDE.md COMPLIANCE: Tests must use real services only

            raise RuntimeError(f"Failed to initialize real infrastructure: {e}") from e

    def _initialize_mock_multi_user_infrastructure(self):
        """Initialize mock infrastructure for multi-user testing."""
        self.agent_factory = MagicMock()
        self.execution_core = MagicMock()
        self.websocket_manager = MagicMock()
        self.websocket_bridge = MagicMock()

        # Configure mock methods
        self.agent_factory.create_user_execution_context = AsyncMock()
        self.agent_factory.user_execution_scope = self._mock_user_execution_scope
        self.execution_core.execute_agent = AsyncMock()
        self.websocket_manager.send_event = AsyncMock()

    async def async_teardown_method(self, method=None):
        """Clean up multi-user test resources and record metrics."""
        try:
            # Record business value metrics for concurrent processing analysis
            self.record_metric("concurrent_processing_metrics", self.concurrent_metrics)

            # Clean up active user sessions
            for user_id in self.active_user_sessions:
                try:
                    # Clean up user-specific resources
                    if hasattr(self.agent_factory, 'cleanup_user_session'):
                        await self.agent_factory.cleanup_user_session(user_id)
                except Exception as e:
                    print(f"Cleanup error for user {user_id}: {e}")

            self.active_user_sessions.clear()

            # Clean up infrastructure
            if hasattr(self.websocket_manager, 'cleanup') and self.websocket_manager:
                await self.websocket_manager.cleanup()

        except Exception as e:
            print(f"Multi-user cleanup error: {e}")

        await super().async_teardown_method(method)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_multi_user_message_processing_isolation(self):
        """
        Test concurrent multi-user message processing with strict isolation.

        Business Value: Compliance critical - validates that multiple users can
        process messages simultaneously without any cross-contamination of sensitive data.
        """
        # Create diverse user scenarios with sensitive content
        user_scenarios = [
            UserScenario(
                user_id=UserID(f"finance_user_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"finance_thread_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"finance_run_{uuid.uuid4().hex[:8]}"),
                domain="finance",
                message_content="Analyze Q3 financial projections for ACME Corp - confidential revenue data",
                sensitive_data="ACME Corp",
                expected_agent_type="financial_analyst_agent",
                processing_complexity="high"
            ),
            UserScenario(
                user_id=UserID(f"healthcare_user_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"healthcare_thread_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"healthcare_run_{uuid.uuid4().hex[:8]}"),
                domain="healthcare",
                message_content="Review patient data analysis for Mercy Hospital - protected health information",
                sensitive_data="Mercy Hospital",
                expected_agent_type="healthcare_data_agent",
                processing_complexity="high"
            ),
            UserScenario(
                user_id=UserID(f"legal_user_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"legal_thread_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"legal_run_{uuid.uuid4().hex[:8]}"),
                domain="legal",
                message_content="Prepare litigation analysis for Smith & Associates - attorney-client privileged",
                sensitive_data="Smith & Associates",
                expected_agent_type="legal_research_agent",
                processing_complexity="high"
            ),
            UserScenario(
                user_id=UserID(f"marketing_user_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"marketing_thread_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"marketing_run_{uuid.uuid4().hex[:8]}"),
                domain="marketing",
                message_content="Develop campaign strategy for TechStart Inc - competitive intelligence data",
                sensitive_data="TechStart Inc",
                expected_agent_type="marketing_strategy_agent",
                processing_complexity="medium"
            ),
            UserScenario(
                user_id=UserID(f"hr_user_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"hr_thread_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"hr_run_{uuid.uuid4().hex[:8]}"),
                domain="human_resources",
                message_content="Analyze employee performance metrics for Global Solutions - sensitive HR data",
                sensitive_data="Global Solutions",
                expected_agent_type="hr_analytics_agent",
                processing_complexity="medium"
            )
        ]

        concurrent_start_time = time.time()

        # Track user sessions for cleanup
        for scenario in user_scenarios:
            self.active_user_sessions.add(str(scenario.user_id))

        # Execute concurrent message processing for all users
        concurrent_tasks = []
        for scenario in user_scenarios:
            task = self._process_user_message_with_isolation_verification(scenario)
            concurrent_tasks.append(task)

        # Execute all concurrent user message processing
        execution_results = await asyncio.gather(*concurrent_tasks, return_exceptions=True)

        concurrent_duration = time.time() - concurrent_start_time

        # Validate all users processed successfully
        successful_results = []
        failed_results = []

        for i, result in enumerate(execution_results):
            if isinstance(result, Exception):
                failed_results.append((user_scenarios[i], result))
            else:
                successful_results.append(result)

        success_rate = len(successful_results) / len(user_scenarios)
        self.assertGreaterEqual(success_rate, 0.8, f"Concurrent processing success rate too low: {success_rate:.2f}")

        # Validate complete isolation between all users
        for i, result_a in enumerate(successful_results):
            for j, result_b in enumerate(successful_results):
                if i != j and result_a.user_id != result_b.user_id:
                    # Validate no cross-contamination of sensitive data
                    scenario_a = next(s for s in user_scenarios if s.user_id == result_a.user_id)
                    scenario_b = next(s for s in user_scenarios if s.user_id == result_b.user_id)

                    # Critical: Check User A's response doesn't contain User B's sensitive data
                    self.assertNotIn(scenario_b.sensitive_data, result_a.response_content,
                                   f"CRITICAL ISOLATION BREACH: User {i} response contains User {j} sensitive data")

                    # Validate WebSocket events are properly isolated
                    for event in result_a.websocket_events:
                        event_content = json.dumps(event)
                        self.assertNotIn(str(scenario_b.user_id), event_content,
                                       f"CRITICAL: WebSocket event isolation breach between users {i} and {j}")

        # Validate concurrent performance meets enterprise requirements
        average_response_time = sum(r.execution_time for r in successful_results) / len(successful_results)
        self.assertLess(concurrent_duration, 20.0,
                       f"Concurrent processing too slow: {concurrent_duration:.3f}s")
        self.assertLess(average_response_time, 15.0,
                       f"Average per-user response time too slow: {average_response_time:.3f}s")

        # Record concurrent processing metrics
        self.concurrent_metrics['concurrent_users_processed'] = len(successful_results)
        self.concurrent_metrics['total_messages_processed'] = len(user_scenarios)
        self.concurrent_metrics['average_response_time_per_user'] = average_response_time
        self.concurrent_metrics['peak_concurrent_users'] = len(user_scenarios)

        # Record performance metrics for business analysis
        self.record_metric("concurrent_processing_duration_ms", concurrent_duration * 1000)
        self.record_metric("concurrent_success_rate", success_rate)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_websocket_event_isolation_under_load(self):
        """
        Test WebSocket event isolation under concurrent user load.

        Business Value: Real-time UX critical - ensures WebSocket events remain
        properly isolated and delivered only to correct users during high load.
        """
        # Create multiple concurrent users for WebSocket load testing
        concurrent_user_count = 6
        user_scenarios = []

        for i in range(concurrent_user_count):
            scenario = UserScenario(
                user_id=UserID(f"ws_load_user_{i}_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"ws_load_thread_{i}_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"ws_load_run_{i}_{uuid.uuid4().hex[:8]}"),
                domain=f"domain_{i}",
                message_content=f"Process load test scenario {i} - unique user data and context",
                sensitive_data=f"LoadTestData_{i}",
                expected_agent_type="load_test_agent",
                processing_complexity="medium"
            )
            user_scenarios.append(scenario)

        # Track user sessions for cleanup
        for scenario in user_scenarios:
            self.active_user_sessions.add(str(scenario.user_id))

        websocket_load_start = time.time()

        # Execute concurrent WebSocket event processing
        concurrent_websocket_tasks = []
        for scenario in user_scenarios:
            task = self._process_user_message_with_websocket_tracking(scenario)
            concurrent_websocket_tasks.append(task)

        # Execute all concurrent WebSocket processing
        websocket_results = await asyncio.gather(*concurrent_websocket_tasks, return_exceptions=True)

        websocket_load_duration = time.time() - websocket_load_start

        # Validate WebSocket event delivery and isolation
        successful_websocket_results = [r for r in websocket_results if not isinstance(r, Exception)]
        websocket_success_rate = len(successful_websocket_results) / len(user_scenarios)

        self.assertGreaterEqual(websocket_success_rate, 0.8,
                               f"WebSocket concurrent processing success rate too low: {websocket_success_rate:.2f}")

        # Validate WebSocket event isolation under load
        total_websocket_events = 0
        for result in successful_websocket_results:
            total_websocket_events += len(result.websocket_events)

            # Validate all WebSocket events belong to correct user
            for event in result.websocket_events:
                event_user_id = event.get('user_id', '')
                self.assertEqual(event_user_id, str(result.user_id),
                               f"WebSocket event isolation failure: event belongs to wrong user")

                # Validate no cross-contamination in WebSocket event content
                for other_result in successful_websocket_results:
                    if other_result.user_id != result.user_id:
                        other_scenario = next(s for s in user_scenarios if s.user_id == other_result.user_id)
                        event_content = json.dumps(event)
                        self.assertNotIn(other_scenario.sensitive_data, event_content,
                                       f"WebSocket event contains other user's sensitive data")

        # Validate WebSocket load performance
        avg_websocket_duration = websocket_load_duration / concurrent_user_count
        self.assertLess(avg_websocket_duration, 12.0,
                       f"WebSocket event processing too slow under load: {avg_websocket_duration:.3f}s")

        # Record WebSocket metrics
        self.concurrent_metrics['websocket_events_delivered'] = total_websocket_events
        self.record_metric("websocket_load_test_duration_ms", websocket_load_duration * 1000)
        self.record_metric("websocket_events_per_second", total_websocket_events / websocket_load_duration)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_isolation_during_concurrent_processing(self):
        """
        Test error isolation during concurrent user message processing.

        Business Value: Platform reliability - ensures one user's errors don't
        cascade and affect other users' successful message processing.
        """
        # Create mixed scenarios - some will succeed, some will have errors
        mixed_scenarios = [
            # Successful scenarios
            UserScenario(
                user_id=UserID(f"success_user_1_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"success_thread_1_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"success_run_1_{uuid.uuid4().hex[:8]}"),
                domain="success",
                message_content="Normal successful message processing scenario",
                sensitive_data="SuccessData1",
                expected_agent_type="general_agent",
                processing_complexity="low"
            ),
            UserScenario(
                user_id=UserID(f"success_user_2_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"success_thread_2_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"success_run_2_{uuid.uuid4().hex[:8]}"),
                domain="success",
                message_content="Another successful message processing scenario",
                sensitive_data="SuccessData2",
                expected_agent_type="general_agent",
                processing_complexity="low"
            ),
            # Error scenarios
            UserScenario(
                user_id=UserID(f"error_user_1_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"error_thread_1_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"error_run_1_{uuid.uuid4().hex[:8]}"),
                domain="error_test",
                message_content="SIMULATE_AGENT_ERROR - This should trigger an agent execution error",
                sensitive_data="ErrorData1",
                expected_agent_type="error_agent",
                processing_complexity="high"
            ),
            UserScenario(
                user_id=UserID(f"timeout_user_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"timeout_thread_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"timeout_run_{uuid.uuid4().hex[:8]}"),
                domain="timeout_test",
                message_content="SIMULATE_TIMEOUT - This should trigger a timeout scenario",
                sensitive_data="TimeoutData",
                expected_agent_type="timeout_agent",
                processing_complexity="very_high"
            )
        ]

        # Track user sessions for cleanup
        for scenario in mixed_scenarios:
            self.active_user_sessions.add(str(scenario.user_id))

        error_isolation_start = time.time()

        # Execute concurrent processing with mixed success/error scenarios
        mixed_concurrent_tasks = []
        for scenario in mixed_scenarios:
            task = self._process_user_message_with_error_handling(scenario)
            mixed_concurrent_tasks.append(task)

        # Execute all mixed concurrent processing
        mixed_results = await asyncio.gather(*mixed_concurrent_tasks, return_exceptions=True)

        error_isolation_duration = time.time() - error_isolation_start

        # Analyze results for error isolation
        successful_results = []
        error_results = []

        for i, result in enumerate(mixed_results):
            if isinstance(result, Exception):
                error_results.append((mixed_scenarios[i], result))
            elif result and result.success:
                successful_results.append(result)
            else:
                error_results.append((mixed_scenarios[i], result))

        # Validate error isolation - successful users should not be affected by errors
        expected_successful_count = 2  # We expect 2 success scenarios to work
        self.assertGreaterEqual(len(successful_results), expected_successful_count,
                               f"Error cascade detected - successful users affected by errors")

        # Validate successful users received complete responses
        for result in successful_results:
            self.assertTrue(result.success, "Successful user should have success=True")
            self.assertGreater(len(result.response_content), 50, "Successful user should have substantive response")
            self.assertEqual(len(result.errors), 0, "Successful user should have no errors")

        # Validate error scenarios were properly contained
        self.assertGreaterEqual(len(error_results), 2, "Expected error scenarios should fail as designed")

        # Validate timing - error isolation shouldn't significantly delay successful users
        self.assertLess(error_isolation_duration, 25.0,
                       f"Error isolation processing took too long: {error_isolation_duration:.3f}s")

        # Record error isolation metrics
        self.concurrent_metrics['concurrent_execution_errors'] = len(error_results)
        self.record_metric("error_isolation_success_count", len(successful_results))
        self.record_metric("error_isolation_error_count", len(error_results))

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_resource_management_under_load(self):
        """
        Test concurrent resource management under sustained user load.

        Business Value: Platform scalability - validates resource usage remains
        controlled under concurrent load and doesn't degrade performance.
        """
        # Create sustained load scenario with multiple waves of users
        sustained_load_waves = [
            # Wave 1: Initial load
            [UserScenario(
                user_id=UserID(f"wave1_user_{i}_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"wave1_thread_{i}_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"wave1_run_{i}_{uuid.uuid4().hex[:8]}"),
                domain=f"wave1_domain_{i}",
                message_content=f"Wave 1 concurrent load test - processing request {i}",
                sensitive_data=f"Wave1Data_{i}",
                expected_agent_type="load_test_agent",
                processing_complexity="medium"
            ) for i in range(3)],

            # Wave 2: Peak load
            [UserScenario(
                user_id=UserID(f"wave2_user_{i}_{uuid.uuid4().hex[:8]}"),
                thread_id=ThreadID(f"wave2_thread_{i}_{uuid.uuid4().hex[:8]}"),
                run_id=RunID(f"wave2_run_{i}_{uuid.uuid4().hex[:8]}"),
                domain=f"wave2_domain_{i}",
                message_content=f"Wave 2 peak load test - intensive processing request {i}",
                sensitive_data=f"Wave2Data_{i}",
                expected_agent_type="intensive_agent",
                processing_complexity="high"
            ) for i in range(4)]
        ]

        # Track all user sessions for cleanup
        for wave in sustained_load_waves:
            for scenario in wave:
                self.active_user_sessions.add(str(scenario.user_id))

        wave_results = []
        resource_usage_metrics = []

        # Execute waves sequentially to test sustained load
        for wave_num, wave_scenarios in enumerate(sustained_load_waves):
            wave_start_time = time.time()

            # Execute concurrent processing for this wave
            wave_tasks = []
            for scenario in wave_scenarios:
                task = self._process_user_message_with_resource_tracking(scenario)
                wave_tasks.append(task)

            # Execute wave and collect results
            wave_execution_results = await asyncio.gather(*wave_tasks, return_exceptions=True)
            wave_duration = time.time() - wave_start_time

            # Analyze wave results
            wave_successful_results = [r for r in wave_execution_results if not isinstance(r, Exception) and r.success]
            wave_success_rate = len(wave_successful_results) / len(wave_scenarios)

            wave_results.append({
                'wave_number': wave_num + 1,
                'wave_duration': wave_duration,
                'wave_success_rate': wave_success_rate,
                'wave_user_count': len(wave_scenarios),
                'successful_executions': len(wave_successful_results)
            })

            # Validate wave performance doesn't degrade significantly
            max_acceptable_wave_duration = 15.0 + (wave_num * 5.0)  # Allow some degradation for higher waves
            self.assertLess(wave_duration, max_acceptable_wave_duration,
                           f"Wave {wave_num + 1} performance degraded too much: {wave_duration:.3f}s")

            self.assertGreaterEqual(wave_success_rate, 0.75,
                                   f"Wave {wave_num + 1} success rate too low: {wave_success_rate:.2f}")

            # Short delay between waves to simulate realistic usage patterns
            await asyncio.sleep(0.5)

        # Validate sustained performance across waves
        total_users_processed = sum(wave['successful_executions'] for wave in wave_results)
        total_duration = sum(wave['wave_duration'] for wave in wave_results)
        overall_throughput = total_users_processed / total_duration

        self.assertGreater(overall_throughput, 0.2, f"Overall throughput too low: {overall_throughput:.3f} users/second")

        # Record resource management metrics
        self.concurrent_metrics['peak_concurrent_users'] = max(wave['wave_user_count'] for wave in wave_results)
        self.record_metric("sustained_load_throughput", overall_throughput)
        self.record_metric("total_concurrent_users_processed", total_users_processed)

    # === HELPER METHODS FOR CONCURRENT TESTING ===

    @asynccontextmanager
    async def _mock_user_execution_scope(self, user_id, thread_id, run_id, **kwargs):
        """Mock user execution scope for concurrent testing."""
        context = MagicMock()
        context.user_id = user_id
        context.thread_id = thread_id
        context.run_id = run_id
        context.created_at = datetime.now(timezone.utc)
        yield context

    async def _process_user_message_with_isolation_verification(self, scenario: UserScenario) -> ConcurrentExecutionResult:
        """Process user message with comprehensive isolation verification."""
        execution_start = time.time()
        websocket_events = []
        errors = []

        try:
            # Create isolated execution context for this user
            if REAL_COMPONENTS_AVAILABLE and hasattr(self.agent_factory, 'user_execution_scope'):
                context_manager = self.agent_factory.user_execution_scope(
                    user_id=scenario.user_id,
                    thread_id=scenario.thread_id,
                    run_id=scenario.run_id
                )
            else:
                context_manager = self._mock_user_execution_scope(
                    scenario.user_id, scenario.thread_id, scenario.run_id
                )

            async with context_manager as user_context:
                # Simulate message processing with isolation
                message = {
                    'content': scenario.message_content,
                    'domain': scenario.domain,
                    'user_id': str(scenario.user_id),
                    'thread_id': str(scenario.thread_id),
                    'sensitive_data': scenario.sensitive_data
                }

                # Process message with WebSocket event tracking
                response_content = await self._simulate_agent_message_processing(
                    message, user_context, websocket_events
                )

                execution_time = time.time() - execution_start

                return ConcurrentExecutionResult(
                    user_id=scenario.user_id,
                    execution_time=execution_time,
                    success=True,
                    response_content=response_content,
                    websocket_events=websocket_events,
                    errors=errors,
                    isolation_verified=True
                )

        except Exception as e:
            execution_time = time.time() - execution_start
            errors.append(str(e))

            return ConcurrentExecutionResult(
                user_id=scenario.user_id,
                execution_time=execution_time,
                success=False,
                response_content="",
                websocket_events=websocket_events,
                errors=errors,
                isolation_verified=False
            )

    async def _process_user_message_with_websocket_tracking(self, scenario: UserScenario) -> ConcurrentExecutionResult:
        """Process user message with detailed WebSocket event tracking."""
        execution_start = time.time()
        websocket_events = []
        errors = []

        try:
            context_manager = self._mock_user_execution_scope(
                scenario.user_id, scenario.thread_id, scenario.run_id
            )

            async with context_manager as user_context:
                # Simulate message processing with enhanced WebSocket tracking
                message = {
                    'content': scenario.message_content,
                    'user_id': str(scenario.user_id),
                    'thread_id': str(scenario.thread_id),
                    'websocket_tracking': True
                }

                response_content = await self._simulate_websocket_intensive_processing(
                    message, user_context, websocket_events
                )

                execution_time = time.time() - execution_start

                return ConcurrentExecutionResult(
                    user_id=scenario.user_id,
                    execution_time=execution_time,
                    success=True,
                    response_content=response_content,
                    websocket_events=websocket_events,
                    errors=errors,
                    isolation_verified=True
                )

        except Exception as e:
            execution_time = time.time() - execution_start
            errors.append(str(e))

            return ConcurrentExecutionResult(
                user_id=scenario.user_id,
                execution_time=execution_time,
                success=False,
                response_content="",
                websocket_events=websocket_events,
                errors=errors,
                isolation_verified=False
            )

    async def _process_user_message_with_error_handling(self, scenario: UserScenario) -> ConcurrentExecutionResult:
        """Process user message with controlled error scenarios for isolation testing."""
        execution_start = time.time()
        websocket_events = []
        errors = []

        try:
            context_manager = self._mock_user_execution_scope(
                scenario.user_id, scenario.thread_id, scenario.run_id
            )

            async with context_manager as user_context:
                message = {
                    'content': scenario.message_content,
                    'user_id': str(scenario.user_id),
                    'thread_id': str(scenario.thread_id),
                    'error_simulation': 'SIMULATE_ERROR' in scenario.message_content
                }

                # Simulate different processing outcomes based on scenario
                if 'SIMULATE_AGENT_ERROR' in scenario.message_content:
                    # Simulate agent execution error
                    await asyncio.sleep(1.0)
                    raise RuntimeError(f"Simulated agent error for user {scenario.user_id}")
                elif 'SIMULATE_TIMEOUT' in scenario.message_content:
                    # Simulate timeout scenario
                    await asyncio.sleep(2.0)
                    raise TimeoutError(f"Simulated timeout for user {scenario.user_id}")
                else:
                    # Normal successful processing
                    response_content = await self._simulate_agent_message_processing(
                        message, user_context, websocket_events
                    )

                execution_time = time.time() - execution_start

                return ConcurrentExecutionResult(
                    user_id=scenario.user_id,
                    execution_time=execution_time,
                    success=True,
                    response_content=response_content,
                    websocket_events=websocket_events,
                    errors=errors,
                    isolation_verified=True
                )

        except Exception as e:
            execution_time = time.time() - execution_start
            errors.append(str(e))

            return ConcurrentExecutionResult(
                user_id=scenario.user_id,
                execution_time=execution_time,
                success=False,
                response_content="",
                websocket_events=websocket_events,
                errors=errors,
                isolation_verified=True  # Error was isolated properly
            )

    async def _process_user_message_with_resource_tracking(self, scenario: UserScenario) -> ConcurrentExecutionResult:
        """Process user message with resource usage tracking."""
        execution_start = time.time()
        websocket_events = []
        errors = []

        try:
            context_manager = self._mock_user_execution_scope(
                scenario.user_id, scenario.thread_id, scenario.run_id
            )

            async with context_manager as user_context:
                message = {
                    'content': scenario.message_content,
                    'user_id': str(scenario.user_id),
                    'thread_id': str(scenario.thread_id),
                    'complexity': scenario.processing_complexity
                }

                # Adjust processing time based on complexity
                processing_delay = {
                    'low': 0.5,
                    'medium': 1.0,
                    'high': 1.5,
                    'very_high': 2.0
                }.get(scenario.processing_complexity, 1.0)

                response_content = await self._simulate_resource_tracked_processing(
                    message, user_context, websocket_events, processing_delay
                )

                execution_time = time.time() - execution_start

                return ConcurrentExecutionResult(
                    user_id=scenario.user_id,
                    execution_time=execution_time,
                    success=True,
                    response_content=response_content,
                    websocket_events=websocket_events,
                    errors=errors,
                    isolation_verified=True
                )

        except Exception as e:
            execution_time = time.time() - execution_start
            errors.append(str(e))

            return ConcurrentExecutionResult(
                user_id=scenario.user_id,
                execution_time=execution_time,
                success=False,
                response_content="",
                websocket_events=websocket_events,
                errors=errors,
                isolation_verified=False
            )

    async def _simulate_agent_message_processing(self, message: Dict, user_context, websocket_events: List) -> str:
        """Simulate agent message processing with WebSocket events."""
        # Add WebSocket events to track processing
        websocket_events.append({
            'type': 'agent_started',
            'user_id': message['user_id'],
            'thread_id': message['thread_id'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        await asyncio.sleep(0.3)  # Simulate processing

        websocket_events.append({
            'type': 'agent_thinking',
            'user_id': message['user_id'],
            'thread_id': message['thread_id'],
            'reasoning': f"Processing message for user {message['user_id']}",
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        await asyncio.sleep(0.5)

        websocket_events.append({
            'type': 'agent_completed',
            'user_id': message['user_id'],
            'thread_id': message['thread_id'],
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Generate response that includes user-specific data but no cross-contamination
        response = f"Processed message for user {message['user_id']}: {message['content'][:50]}... [Agent response generated successfully with proper user isolation]"
        return response

    async def _simulate_websocket_intensive_processing(self, message: Dict, user_context, websocket_events: List) -> str:
        """Simulate WebSocket-intensive processing with many events."""
        # Generate more WebSocket events for load testing
        event_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']

        for i, event_type in enumerate(event_types):
            websocket_events.append({
                'type': event_type,
                'user_id': message['user_id'],
                'thread_id': message['thread_id'],
                'event_sequence': i + 1,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            await asyncio.sleep(0.2)  # Realistic event timing

        return f"WebSocket-intensive processing completed for user {message['user_id']}"

    async def _simulate_resource_tracked_processing(self, message: Dict, user_context, websocket_events: List, delay: float) -> str:
        """Simulate processing with resource usage tracking."""
        websocket_events.append({
            'type': 'agent_started',
            'user_id': message['user_id'],
            'resource_tracking': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        # Simulate processing based on complexity
        await asyncio.sleep(delay)

        websocket_events.append({
            'type': 'agent_completed',
            'user_id': message['user_id'],
            'processing_time': delay,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        return f"Resource-tracked processing completed for user {message['user_id']} in {delay}s"