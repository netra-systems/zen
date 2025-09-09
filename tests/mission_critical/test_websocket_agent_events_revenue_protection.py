#!/usr/bin/env python
"""
MISSION CRITICAL TEST SUITE: WebSocket Agent Events Revenue Protection

THIS TEST SUITE PROTECTS $500K+ ARR - DEPLOYMENT BLOCKED IF FAILED

Business Value Justification (BVJ):
- Segment: Platform/Internal - Core Chat Infrastructure ($500K+ ARR)
- Business Goal: Revenue Protection - Ensure WebSocket events deliver substantive AI chat value
- Value Impact: Validates the 5 critical events that power 90% of platform business value
- Strategic Impact: Prevents silent failures that would block revenue-generating chat interactions

CRITICAL MISSION: Validate that ALL 5 WebSocket agent events are sent for every agent execution:
1. agent_started - User sees AI began processing their problem (REVENUE CRITICAL)
2. agent_thinking - Real-time reasoning visibility (USER ENGAGEMENT CRITICAL)  
3. tool_executing - Tool usage transparency (VALUE DEMONSTRATION CRITICAL)
4. tool_completed - Tool results display (ACTIONABLE INSIGHTS CRITICAL)
5. agent_completed - User knows when valuable response is ready (COMPLETION CRITICAL)

If ANY of these events are missing, users don't see AI value delivery and revenue is lost.

COMPLIANCE:
@compliance CLAUDE.md - WebSocket events enable substantive chat interactions (Section 6)
@compliance CLAUDE.md - Real services only, NO MOCKS (Mocks = Abomination)
@compliance SPEC/core.xml - Mission critical test patterns
@compliance SPEC/type_safety.xml - Strongly typed test validation

DEPLOYMENT POLICY: ANY FAILURE HERE BLOCKS PRODUCTION DEPLOYMENT
"""

import asyncio
import json
import os
import sys
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Set, Any, Optional, Tuple
import threading

# CRITICAL: Add project root to Python path for imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# Import SSOT dependencies
from shared.types.core_types import UserID, ThreadID, RunID, RequestID, WebSocketID
from shared.types.execution_types import StronglyTypedUserExecutionContext
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from shared.isolated_environment import get_env

# Import SSOT test framework
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, create_authenticated_user_context
from test_framework.ssot.websocket_golden_path_helpers import (
    WebSocketGoldenPathHelper,
    GoldenPathTestConfig,
    GoldenPathTestResult,
    test_websocket_golden_path,
    assert_golden_path_success
)
from test_framework.ssot.agent_event_validators import (
    AgentEventValidator,
    CriticalAgentEventType,
    assert_critical_events_received,
    get_critical_event_types,
    WebSocketEventMessage
)

# Import real services - NO MOCKS per CLAUDE.md
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.unified_docker_manager import UnifiedDockerManager, EnvironmentType


# ============================================================================
# MISSION CRITICAL TEST MARKERS
# ============================================================================

# Mark all tests as mission critical
pytestmark = [
    pytest.mark.mission_critical,
    pytest.mark.websocket,
    pytest.mark.revenue_protection,
    pytest.mark.timeout(300)  # 5 minute timeout for mission critical tests
]


# ============================================================================
# MISSION CRITICAL TEST CLASS
# ============================================================================

class TestWebSocketAgentEventsRevenueProtection(SSotBaseTestCase):
    """
    MISSION CRITICAL: WebSocket Agent Events Revenue Protection Test Suite
    
    This test class validates the 5 critical WebSocket events that deliver
    90% of platform business value ($500K+ ARR) through AI chat interactions.
    
    CRITICAL: ALL tests in this class MUST pass or deployment is blocked.
    Each test failure represents potential revenue loss.
    """
    
    @classmethod
    def setup_class(cls):
        """Set up mission critical test environment with real services."""
        super().setup_class()
        
        cls.env = get_env()
        cls.test_environment = cls.env.get("TEST_ENV", "test")
        cls.docker_manager = UnifiedDockerManager()
        cls.id_generator = UnifiedIdGenerator()
        
        logger.critical("🚨 MISSION CRITICAL TESTS STARTING - Revenue Protection Mode 🚨")
        logger.info(f"Environment: {cls.test_environment}")
        logger.info("Required: ALL 5 critical WebSocket events MUST be validated")
    
    @classmethod
    def teardown_class(cls):
        """Clean up mission critical test environment."""
        logger.critical("🚨 MISSION CRITICAL TESTS COMPLETED 🚨")
        super().teardown_class()
    
    def setup_method(self, method):
        """Set up individual test method."""
        super().setup_method(method)
        
        # Create test configuration
        self.golden_path_config = GoldenPathTestConfig.for_environment(self.test_environment)
        
        # Enable strict validation for mission critical tests
        self.golden_path_config.require_all_critical_events = True
        self.golden_path_config.validate_event_sequence = True
        self.golden_path_config.validate_event_timing = True
        self.golden_path_config.validate_business_value = True
        
        logger.info(f"🔍 Mission Critical Test: {method.__name__}")
    
    # ========================================================================
    # CRITICAL EVENT VALIDATION TESTS
    # ========================================================================
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_all_five_critical_events_received_single_user(self):
        """
        MISSION CRITICAL: Validate all 5 critical events are received for single user.
        
        This test MUST pass - it validates the core revenue-generating flow.
        Failure indicates users won't see AI value delivery.
        """
        logger.critical("🎯 TESTING: All 5 critical events for single user")
        
        # Create authenticated user context
        user_context = await create_authenticated_user_context(
            user_email="revenue_test_single@example.com",
            environment=self.test_environment,
            permissions=["read", "write"],
            websocket_enabled=True
        )
        
        # Execute golden path with strict validation
        result = await assert_golden_path_success(
            user_message="Analyze sample data and provide business insights",
            environment=self.test_environment,
            config=self.golden_path_config,
            user_context=user_context,
            custom_error_message="REVENUE CRITICAL: Single user golden path failed - this blocks ALL chat revenue!"
        )
        
        # CRITICAL: Validate all 5 events received
        critical_events = get_critical_event_types()
        received_event_types = set(result.validation_result.received_events)
        
        assert critical_events.issubset(received_event_types), (
            f"REVENUE FAILURE: Missing critical events {critical_events - received_event_types}. "
            f"This breaks the core platform value proposition and blocks revenue!"
        )
        
        # Validate business value score
        assert result.execution_metrics.business_value_score >= 100.0, (
            f"BUSINESS VALUE FAILURE: Score {result.execution_metrics.business_value_score}% < 100%. "
            f"Users won't see complete AI value delivery!"
        )
        
        # Validate user experience rating
        assert result.execution_metrics.user_experience_rating in ["EXCELLENT", "GOOD"], (
            f"USER EXPERIENCE FAILURE: Rating {result.execution_metrics.user_experience_rating} is insufficient. "
            f"Poor UX directly impacts revenue conversion!"
        )
        
        logger.success(f"✅ CRITICAL TEST PASSED: All 5 events received, UX: {result.execution_metrics.user_experience_rating}")
    
    @pytest.mark.critical
    @pytest.mark.asyncio  
    async def test_concurrent_multi_user_critical_events(self):
        """
        MISSION CRITICAL: Validate all 5 critical events under concurrent load.
        
        Tests 10+ concurrent users to ensure the system can handle real-world load
        while maintaining revenue-critical event delivery.
        """
        logger.critical("🎯 TESTING: Concurrent 10-user critical events validation")
        
        # Test with 10 concurrent users (realistic production load)
        user_count = 10
        helper = WebSocketGoldenPathHelper(
            config=self.golden_path_config,
            environment=self.test_environment
        )
        
        # Execute concurrent golden paths
        results = await helper.test_concurrent_golden_paths(
            user_count=user_count,
            timeout_per_user=60.0  # Allow more time under load
        )
        
        # CRITICAL: ALL users must receive all 5 events
        successful_users = 0
        failed_users = []
        critical_events = get_critical_event_types()
        
        for i, result in enumerate(results):
            user_id = f"user_{i+1}"
            
            if not result.success:
                failed_users.append(f"{user_id}: {result.validation_result.error_message}")
                continue
            
            # Check critical events
            received_events = set(result.validation_result.received_events)
            missing_events = critical_events - received_events
            
            if missing_events:
                failed_users.append(f"{user_id}: Missing events {missing_events}")
                continue
            
            # Check business value
            if result.execution_metrics.business_value_score < 100.0:
                failed_users.append(f"{user_id}: Business value score {result.execution_metrics.business_value_score}%")
                continue
            
            successful_users += 1
        
        # CRITICAL: Require 100% success rate for revenue protection
        success_rate = (successful_users / user_count) * 100
        assert success_rate >= 100.0, (
            f"REVENUE CRITICAL FAILURE: Only {successful_users}/{user_count} users ({success_rate:.1f}%) "
            f"received all critical events. This represents potential revenue loss!\n"
            f"Failed users: {failed_users}"
        )
        
        logger.success(f"✅ CONCURRENT TEST PASSED: {successful_users}/{user_count} users received all critical events")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_event_timing_performance_requirements(self):
        """
        MISSION CRITICAL: Validate event timing meets performance requirements.
        
        Tests that events are delivered within acceptable timeframes to ensure
        good user experience and revenue conversion.
        """
        logger.critical("🎯 TESTING: Event timing performance requirements")
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="timing_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Execute with performance monitoring
        start_time = time.time()
        result = await test_websocket_golden_path(
            user_message="Quick analysis request for timing test",
            environment=self.test_environment,
            config=self.golden_path_config,
            user_context=user_context
        )
        total_time = time.time() - start_time
        
        # CRITICAL: Validate timing requirements
        assert result.success, f"Performance test failed: {result.validation_result.error_message}"
        
        # First event must arrive quickly (user sees immediate response)
        assert result.execution_metrics.first_event_time <= 5.0, (
            f"TIMING FAILURE: First event took {result.execution_metrics.first_event_time:.2f}s > 5.0s. "
            f"Users will think system is broken!"
        )
        
        # Total execution must complete in reasonable time
        assert total_time <= 30.0, (
            f"PERFORMANCE FAILURE: Total execution took {total_time:.2f}s > 30.0s. "
            f"Users will abandon slow AI interactions!"
        )
        
        # Event throughput must be reasonable
        assert result.execution_metrics.throughput_events_per_second >= 0.1, (
            f"THROUGHPUT FAILURE: {result.execution_metrics.throughput_events_per_second:.2f} events/sec is too slow. "
            f"Poor throughput impacts user engagement!"
        )
        
        logger.success(
            f"✅ TIMING TEST PASSED: First event: {result.execution_metrics.first_event_time:.2f}s, "
            f"Total: {total_time:.2f}s, Throughput: {result.execution_metrics.throughput_events_per_second:.2f} events/sec"
        )
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_event_sequence_validation(self):
        """
        MISSION CRITICAL: Validate events are received in logical order.
        
        Tests that events follow the expected sequence to ensure coherent
        user experience and proper AI workflow visibility.
        """
        logger.critical("🎯 TESTING: Event sequence validation")
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="sequence_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Create validator to track sequence
        validator = AgentEventValidator(
            user_context=user_context,
            strict_mode=True,
            timeout_seconds=45.0
        )
        
        # Execute golden path
        helper = WebSocketGoldenPathHelper(
            config=self.golden_path_config,
            environment=self.test_environment
        )
        
        async with helper.authenticated_websocket_connection(user_context):
            # Send request
            await helper.send_golden_path_request(
                "Sequential analysis request for testing event order",
                user_context
            )
            
            # Capture events with custom validator
            captured_events = await helper.capture_events_with_timeout(timeout=45.0)
            
            # Record events in validator
            for event in captured_events:
                validator.record_event(event)
        
        # CRITICAL: Validate sequence
        sequence_valid, sequence_errors = validator.validate_event_sequence()
        assert sequence_valid, (
            f"EVENT SEQUENCE FAILURE: {sequence_errors}. "
            f"Out-of-order events confuse users and reduce trust in AI!"
        )
        
        # Validate expected flow pattern
        critical_events_sequence = [
            event.event_type for event in captured_events 
            if event.event_type in get_critical_event_types()
        ]
        
        # agent_started should come before agent_completed
        if (CriticalAgentEventType.AGENT_STARTED.value in critical_events_sequence and 
            CriticalAgentEventType.AGENT_COMPLETED.value in critical_events_sequence):
            
            started_idx = critical_events_sequence.index(CriticalAgentEventType.AGENT_STARTED.value)
            completed_idx = critical_events_sequence.index(CriticalAgentEventType.AGENT_COMPLETED.value)
            
            assert started_idx < completed_idx, (
                f"SEQUENCE FAILURE: agent_completed before agent_started. "
                f"This breaks logical flow and confuses users!"
            )
        
        logger.success(f"✅ SEQUENCE TEST PASSED: Events received in logical order: {critical_events_sequence}")
    
    @pytest.mark.critical
    @pytest.mark.asyncio
    async def test_business_value_content_validation(self):
        """
        MISSION CRITICAL: Validate event content delivers business value.
        
        Tests that events contain meaningful content that demonstrates
        AI value to users and drives revenue conversion.
        """
        logger.critical("🎯 TESTING: Business value content validation")
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="content_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Execute golden path
        result = await test_websocket_golden_path(
            user_message="Provide detailed analysis with actionable business insights",
            environment=self.test_environment,
            config=self.golden_path_config,
            user_context=user_context
        )
        
        assert result.success, f"Content validation test failed: {result.validation_result.error_message}"
        
        # CRITICAL: Validate content quality
        events_by_type = {}
        for event in result.events_received:
            events_by_type[event.event_type] = event
        
        # Validate agent_started content
        if CriticalAgentEventType.AGENT_STARTED.value in events_by_type:
            started_event = events_by_type[CriticalAgentEventType.AGENT_STARTED.value]
            assert started_event.data, "agent_started event missing data - users won't see AI activation!"
            assert started_event.data.get("agent"), "agent_started missing agent info - no AI identity!"
        
        # Validate tool_executing content
        if CriticalAgentEventType.TOOL_EXECUTING.value in events_by_type:
            executing_event = events_by_type[CriticalAgentEventType.TOOL_EXECUTING.value]
            assert executing_event.data, "tool_executing event missing data - no tool transparency!"
            assert executing_event.data.get("tool"), "tool_executing missing tool info - no capability demo!"
        
        # Validate tool_completed content
        if CriticalAgentEventType.TOOL_COMPLETED.value in events_by_type:
            completed_event = events_by_type[CriticalAgentEventType.TOOL_COMPLETED.value]
            assert completed_event.data, "tool_completed event missing data - no results shown!"
            assert completed_event.data.get("tool"), "tool_completed missing tool info - incomplete context!"
        
        # Validate agent_completed content
        if CriticalAgentEventType.AGENT_COMPLETED.value in events_by_type:
            final_event = events_by_type[CriticalAgentEventType.AGENT_COMPLETED.value]
            assert final_event.data, "agent_completed event missing data - no final value delivery!"
            assert final_event.data.get("agent"), "agent_completed missing agent info - incomplete closure!"
        
        logger.success("✅ CONTENT TEST PASSED: All events contain business value content")
    
    # ========================================================================
    # STRESS AND RELIABILITY TESTS
    # ========================================================================
    
    @pytest.mark.stress
    @pytest.mark.asyncio
    async def test_high_concurrency_revenue_protection(self):
        """
        STRESS TEST: Validate critical events under high concurrency.
        
        Tests 25+ concurrent users to ensure the system maintains
        revenue-critical event delivery under stress.
        """
        logger.critical("🎯 STRESS TESTING: 25-user high concurrency revenue protection")
        
        # Stress test with 25 concurrent users
        user_count = 25
        timeout_per_user = 120.0  # Longer timeout under stress
        
        # Create stress test configuration
        stress_config = GoldenPathTestConfig.for_environment(self.test_environment)
        stress_config.connection_timeout = 60.0
        stress_config.event_timeout = 90.0
        stress_config.max_retries = 5
        
        # Execute stress test
        helper = WebSocketGoldenPathHelper(
            config=stress_config,
            environment=self.test_environment
        )
        
        results = await helper.test_concurrent_golden_paths(
            user_count=user_count,
            timeout_per_user=timeout_per_user
        )
        
        # Analyze stress test results
        successful_users = 0
        high_performance_users = 0
        failed_users = []
        critical_events = get_critical_event_types()
        
        for i, result in enumerate(results):
            user_id = f"stress_user_{i+1}"
            
            if not result.success:
                failed_users.append(user_id)
                continue
            
            # Check critical events
            received_events = set(result.validation_result.received_events)
            if not critical_events.issubset(received_events):
                failed_users.append(user_id)
                continue
            
            successful_users += 1
            
            # Count high-performance users (excellent UX under stress)
            if result.execution_metrics.user_experience_rating == "EXCELLENT":
                high_performance_users += 1
        
        # CRITICAL: Require at least 80% success under stress
        success_rate = (successful_users / user_count) * 100
        assert success_rate >= 80.0, (
            f"STRESS TEST FAILURE: Only {successful_users}/{user_count} users ({success_rate:.1f}%) "
            f"succeeded under stress. System cannot handle production load! "
            f"Failed: {len(failed_users)} users"
        )
        
        # Log stress test metrics
        high_perf_rate = (high_performance_users / user_count) * 100
        logger.success(
            f"✅ STRESS TEST PASSED: {successful_users}/{user_count} successful ({success_rate:.1f}%), "
            f"{high_performance_users} excellent UX ({high_perf_rate:.1f}%)"
        )
    
    @pytest.mark.reliability
    @pytest.mark.asyncio
    async def test_event_delivery_reliability(self):
        """
        RELIABILITY TEST: Validate consistent event delivery across multiple runs.
        
        Executes multiple sequential golden paths to ensure reliable
        event delivery and consistent business value.
        """
        logger.critical("🎯 RELIABILITY TESTING: Multiple sequential golden path executions")
        
        run_count = 5
        successful_runs = 0
        business_value_scores = []
        execution_times = []
        
        for run_idx in range(run_count):
            logger.info(f"Reliability run {run_idx + 1}/{run_count}")
            
            try:
                # Create fresh user context for each run
                user_context = await create_authenticated_user_context(
                    user_email=f"reliability_test_run_{run_idx + 1}@example.com",
                    environment=self.test_environment,
                    websocket_enabled=True
                )
                
                # Execute golden path
                start_time = time.time()
                result = await test_websocket_golden_path(
                    user_message=f"Reliability test run {run_idx + 1} - analyze sample data",
                    environment=self.test_environment,
                    config=self.golden_path_config,
                    user_context=user_context
                )
                execution_time = time.time() - start_time
                
                if result.success:
                    successful_runs += 1
                    business_value_scores.append(result.execution_metrics.business_value_score)
                    execution_times.append(execution_time)
                
                # Small delay between runs
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Reliability run {run_idx + 1} failed: {e}")
        
        # CRITICAL: Require 100% reliability
        reliability_rate = (successful_runs / run_count) * 100
        assert reliability_rate >= 100.0, (
            f"RELIABILITY FAILURE: Only {successful_runs}/{run_count} runs ({reliability_rate:.1f}%) succeeded. "
            f"Inconsistent event delivery will cause customer churn!"
        )
        
        # Validate consistent business value
        if business_value_scores:
            avg_score = sum(business_value_scores) / len(business_value_scores)
            min_score = min(business_value_scores)
            assert min_score >= 100.0, (
                f"BUSINESS VALUE CONSISTENCY FAILURE: Min score {min_score}% < 100%. "
                f"Inconsistent value delivery impacts revenue!"
            )
        
        # Validate consistent performance
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            max_time = max(execution_times)
            assert max_time <= 45.0, (
                f"PERFORMANCE CONSISTENCY FAILURE: Max time {max_time:.2f}s > 45.0s. "
                f"Inconsistent performance hurts user experience!"
            )
        
        logger.success(
            f"✅ RELIABILITY TEST PASSED: {successful_runs}/{run_count} runs successful, "
            f"Avg score: {avg_score:.1f}%, Avg time: {avg_time:.2f}s"
        )
    
    # ========================================================================
    # EDGE CASE AND ERROR HANDLING TESTS
    # ========================================================================
    
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_connection_interruption_recovery(self):
        """
        EDGE CASE: Test event delivery after connection interruption.
        
        Simulates connection issues to ensure the system gracefully
        handles interruptions without losing critical events.
        """
        logger.critical("🎯 EDGE CASE TESTING: Connection interruption recovery")
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="interruption_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Create helper with retry configuration
        recovery_config = GoldenPathTestConfig.for_environment(self.test_environment)
        recovery_config.max_retries = 5
        recovery_config.connection_timeout = 45.0
        
        helper = WebSocketGoldenPathHelper(
            config=recovery_config,
            environment=self.test_environment
        )
        
        # Test recovery capability
        async with helper.authenticated_websocket_connection(user_context):
            # Send request
            await helper.send_golden_path_request(
                "Test request for interruption recovery validation",
                user_context
            )
            
            # Capture events (system should handle any interruptions gracefully)
            captured_events = await helper.capture_events_with_timeout(timeout=60.0)
        
        # CRITICAL: Validate recovery resulted in event delivery
        critical_events = get_critical_event_types()
        received_event_types = {event.event_type for event in captured_events}
        
        # Allow some tolerance for edge cases but require core events
        core_events = {
            CriticalAgentEventType.AGENT_STARTED.value,
            CriticalAgentEventType.AGENT_COMPLETED.value
        }
        
        assert core_events.issubset(received_event_types), (
            f"RECOVERY FAILURE: Core events {core_events - received_event_types} missing after recovery. "
            f"Connection issues must not block revenue-critical events!"
        )
        
        logger.success(f"✅ RECOVERY TEST PASSED: Core events delivered despite potential interruptions")
    
    @pytest.mark.edge_case
    @pytest.mark.asyncio
    async def test_large_message_event_handling(self):
        """
        EDGE CASE: Test event delivery with large message content.
        
        Ensures the system can handle large user requests while still
        delivering all critical events for business value.
        """
        logger.critical("🎯 EDGE CASE TESTING: Large message event handling")
        
        # Create user context
        user_context = await create_authenticated_user_context(
            user_email="large_message_test@example.com",
            environment=self.test_environment,
            websocket_enabled=True
        )
        
        # Create large message (simulating complex user request)
        large_message = (
            "Please analyze this large dataset and provide comprehensive insights. " * 100 +
            "Include detailed recommendations, statistical analysis, trend identification, "
            "risk assessment, opportunity analysis, competitive benchmarking, "
            "market segmentation, customer behavior patterns, revenue optimization, "
            "cost reduction strategies, operational efficiency improvements, "
            "technology stack recommendations, security considerations, "
            "scalability planning, and implementation roadmap with timelines."
        )
        
        # Execute with larger timeout for complex processing
        large_message_config = GoldenPathTestConfig.for_environment(self.test_environment)
        large_message_config.event_timeout = 90.0
        
        result = await test_websocket_golden_path(
            user_message=large_message,
            environment=self.test_environment,
            config=large_message_config,
            user_context=user_context
        )
        
        # CRITICAL: Large messages must not break event delivery
        assert result.success, (
            f"LARGE MESSAGE FAILURE: {result.validation_result.error_message}. "
            f"System must handle complex requests without losing events!"
        )
        
        # Validate all critical events received despite complexity
        critical_events = get_critical_event_types()
        received_events = set(result.validation_result.received_events)
        
        assert critical_events.issubset(received_events), (
            f"COMPLEX REQUEST FAILURE: Missing events {critical_events - received_events}. "
            f"Complex user requests must still deliver full business value!"
        )
        
        logger.success("✅ LARGE MESSAGE TEST PASSED: All critical events delivered for complex request")


# ============================================================================
# PYTEST FIXTURES FOR MISSION CRITICAL TESTS
# ============================================================================

@pytest.fixture(scope="class")
async def docker_services():
    """Ensure Docker services are running for mission critical tests."""
    docker_manager = UnifiedDockerManager()
    env = get_env()
    
    # Skip Docker startup if running in CI or staging environment
    if env.get("CI") or env.get("TEST_ENV") == "staging":
        logger.info("Skipping Docker startup in CI/staging environment")
        yield None
        return
    
    try:
        # Start services
        await docker_manager.ensure_services_running([
            "backend", "auth_service", "postgres", "redis"
        ])
        
        # Wait for services to be ready
        await asyncio.sleep(10)
        
        yield docker_manager
        
    except Exception as e:
        logger.error(f"Failed to start Docker services for mission critical tests: {e}")
        pytest.skip("Docker services not available - skipping mission critical tests")


@pytest.fixture(scope="function")
async def authenticated_test_context():
    """Create authenticated test context for individual tests."""
    context = await create_authenticated_user_context(
        user_email=f"mission_critical_{uuid.uuid4().hex[:8]}@example.com",
        environment=get_env().get("TEST_ENV", "test"),
        permissions=["read", "write"],
        websocket_enabled=True
    )
    return context


# ============================================================================
# MISSION CRITICAL TEST CONFIGURATION
# ============================================================================

# Configure pytest for mission critical tests
def pytest_configure(config):
    """Configure pytest for mission critical testing."""
    config.addinivalue_line(
        "markers", 
        "mission_critical: mark test as mission critical (blocks deployment if failed)"
    )
    config.addinivalue_line(
        "markers",
        "revenue_protection: mark test as protecting revenue-generating functionality"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection for mission critical priority."""
    # Prioritize mission critical tests
    mission_critical_tests = []
    other_tests = []
    
    for item in items:
        if "mission_critical" in [mark.name for mark in item.iter_markers()]:
            mission_critical_tests.append(item)
        else:
            other_tests.append(item)
    
    # Run mission critical tests first
    items[:] = mission_critical_tests + other_tests


# ============================================================================
# MISSION CRITICAL TEST EXECUTION HOOKS
# ============================================================================

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_call(pyfuncitem):
    """Hook for mission critical test execution."""
    if "mission_critical" in [mark.name for mark in pyfuncitem.iter_markers()]:
        logger.critical(f"🚨 EXECUTING MISSION CRITICAL TEST: {pyfuncitem.name} 🚨")


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(pyfuncitem, nextitem):
    """Hook for mission critical test teardown."""
    if "mission_critical" in [mark.name for mark in pyfuncitem.iter_markers()]:
        logger.critical(f"🚨 MISSION CRITICAL TEST COMPLETED: {pyfuncitem.name} 🚨")


if __name__ == "__main__":
    # Direct execution for debugging
    pytest.main([
        __file__,
        "-v",
        "-s", 
        "--tb=short",
        "-m", "mission_critical"
    ])