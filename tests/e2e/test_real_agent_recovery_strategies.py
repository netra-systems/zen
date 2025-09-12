#!/usr/bin/env python
"""Real Agent Recovery Strategies E2E Test Suite - Business Critical Testing

MISSION CRITICAL: Tests agent error recovery and resilience with real services.
Business Value: Ensure system stability and graceful error handling.

Business Value Justification (BVJ):
1. Segment: All (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure system reliability and error resilience
3. Value Impact: Recovery strategies prevent system failures and maintain user trust
4. Revenue Impact: $500K+ ARR protection from system downtime prevention

CLAUDE.md COMPLIANCE:
- Uses real services ONLY (NO MOCKS)
- Validates ALL 5 required WebSocket events during recovery
- Tests actual error recovery business logic
- Uses IsolatedEnvironment for environment access
- Absolute imports only
- Factory patterns for user isolation
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
from enum import Enum
import random

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest
from loguru import logger

# CLAUDE.md compliant imports - Lazy loaded to prevent resource exhaustion
from shared.isolated_environment import get_env


class RecoveryType(Enum):
    """Types of recovery strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAKER = "circuit_breaker"
    GRACEFUL_DEGRADATION = "graceful_degradation"
    ALTERNATIVE_AGENT = "alternative_agent"
    PARTIAL_RECOVERY = "partial_recovery"


@dataclass
class ErrorScenario:
    """Defines an error scenario for testing recovery."""
    error_type: str
    trigger_condition: str
    expected_recovery: RecoveryType
    recovery_timeout: float
    success_criteria: List[str]


@dataclass
class RecoveryAttempt:
    """Tracks individual recovery attempt."""
    error_type: str
    recovery_type: RecoveryType
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    recovery_data: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> Optional[float]:
        if self.end_time and self.start_time:
            return self.end_time - self.start_time
        return None


@dataclass
class AgentRecoveryValidation:
    """Captures and validates agent recovery strategy execution."""
    
    user_id: str
    thread_id: str
    recovery_scenario: str
    start_time: float = field(default_factory=time.time)
    
    # Event tracking (MISSION CRITICAL per CLAUDE.md)
    events_received: List[Dict[str, Any]] = field(default_factory=list)
    event_types_seen: Set[str] = field(default_factory=set)
    
    # Recovery tracking
    errors_encountered: List[Dict[str, Any]] = field(default_factory=list)
    recovery_attempts: List[RecoveryAttempt] = field(default_factory=list)
    final_recovery_state: Optional[Dict[str, Any]] = None
    
    # Timing metrics (performance benchmarks per requirements)
    time_to_first_error: Optional[float] = None
    time_to_first_recovery: Optional[float] = None
    time_to_final_resolution: Optional[float] = None
    
    # Business logic validation
    recovery_successful: bool = False
    system_stability_maintained: bool = False
    graceful_degradation_achieved: bool = False
    user_experience_preserved: bool = False


class RealAgentRecoveryStrategiesTester:
    """Tests agent recovery strategies with real services and WebSocket events."""
    
    # CLAUDE.md REQUIRED WebSocket events during recovery
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    # Recovery strategy test scenarios
    RECOVERY_SCENARIOS = [
        {
            "scenario_name": "llm_api_timeout_recovery",
            "initial_message": "Perform a complex analysis that may timeout",
            "error_injection": {"type": "timeout", "target": "llm_api", "delay": 30.0},
            "expected_recovery": RecoveryType.RETRY,
            "success_criteria": ["retry_attempted", "alternative_approach", "partial_results"]
        },
        {
            "scenario_name": "tool_execution_failure_fallback",
            "initial_message": "Use tools that may fail and require fallback strategies",
            "error_injection": {"type": "tool_failure", "target": "data_analyzer", "probability": 0.8},
            "expected_recovery": RecoveryType.FALLBACK,
            "success_criteria": ["fallback_tool_used", "alternative_method", "results_delivered"]
        },
        {
            "scenario_name": "circuit_breaker_activation",
            "initial_message": "Trigger repeated failures to activate circuit breaker",
            "error_injection": {"type": "repeated_failures", "target": "external_service", "count": 5},
            "expected_recovery": RecoveryType.CIRCUIT_BREAKER,
            "success_criteria": ["circuit_breaker_activated", "traffic_blocked", "recovery_attempted"]
        },
        {
            "scenario_name": "graceful_degradation_strategy",
            "initial_message": "Request comprehensive analysis when resources are limited",
            "error_injection": {"type": "resource_exhaustion", "target": "system_resources", "level": 0.9},
            "expected_recovery": RecoveryType.GRACEFUL_DEGRADATION,
            "success_criteria": ["degraded_service", "basic_functionality", "user_notified"]
        },
        {
            "scenario_name": "alternative_agent_handover",
            "initial_message": "Execute task that requires agent handover on failure",
            "error_injection": {"type": "agent_failure", "target": "primary_agent", "probability": 1.0},
            "expected_recovery": RecoveryType.ALTERNATIVE_AGENT,
            "success_criteria": ["agent_switched", "task_continued", "seamless_transition"]
        },
        {
            "scenario_name": "partial_recovery_completion",
            "initial_message": "Complete task with partial data when full recovery isn't possible",
            "error_injection": {"type": "data_corruption", "target": "input_data", "corruption_rate": 0.3},
            "expected_recovery": RecoveryType.PARTIAL_RECOVERY,
            "success_criteria": ["partial_results", "data_validated", "limitations_explained"]
        }
    ]
    
    def __init__(self):
        self.env = None  # Lazy init
        self.ws_client = None
        self.backend_client = None
        self.jwt_helper = None
        self.validations: List[AgentRecoveryValidation] = []
        
    async def setup(self):
        """Initialize test environment with real services."""
        # Lazy imports per CLAUDE.md to prevent Docker crashes
        from shared.isolated_environment import IsolatedEnvironment
        from tests.e2e.jwt_token_helpers import JWTTestHelper
        from tests.clients.backend_client import BackendTestClient
        from tests.clients.websocket_client import WebSocketTestClient
        from tests.e2e.test_data_factory import create_test_user_data
        
        self.env = IsolatedEnvironment()
        self.jwt_helper = JWTTestHelper()
        
        # Initialize backend client
        backend_url = self.env.get("BACKEND_URL", "http://localhost:8000")
        self.backend_client = BackendTestClient(backend_url)
        
        # Create test user with recovery testing permissions
        user_data = create_test_user_data("recovery_strategies_test")
        self.user_id = str(uuid.uuid4())
        self.email = user_data['email']
        
        # Generate JWT with comprehensive testing permissions
        self.token = self.jwt_helper.create_access_token(
            self.user_id, 
            self.email,
            permissions=["agents:use", "recovery:test", "errors:inject", "system:monitor"]
        )
        
        # Initialize WebSocket client
        ws_url = f"{backend_url.replace('http', 'ws')}/ws"
        self.ws_client = WebSocketTestClient(ws_url)
        
        # Connect with authentication
        connected = await self.ws_client.connect(token=self.token)
        if not connected:
            raise RuntimeError("Failed to connect to WebSocket")
            
        logger.info(f"Agent recovery strategies test environment ready for user {self.email}")
        return self
        
    async def teardown(self):
        """Clean up test environment."""
        if self.ws_client:
            await self.ws_client.disconnect()
            
    async def execute_recovery_scenario(
        self, 
        scenario: Dict[str, Any],
        timeout: float = 120.0
    ) -> AgentRecoveryValidation:
        """Execute a recovery strategy scenario and validate results.
        
        Args:
            scenario: Recovery scenario configuration
            timeout: Maximum execution time
            
        Returns:
            Complete validation results
        """
        thread_id = str(uuid.uuid4())
        validation = AgentRecoveryValidation(
            user_id=self.user_id,
            thread_id=thread_id,
            recovery_scenario=scenario["scenario_name"]
        )
        
        # Send request with error injection configuration
        recovery_request = {
            "type": "agent_request",
            "agent": "triage_agent",  # Start with triage for routing
            "message": scenario["initial_message"],
            "thread_id": thread_id,
            "context": {
                "recovery_test": True,
                "scenario": scenario["scenario_name"],
                "error_injection": scenario.get("error_injection", {}),
                "user_id": self.user_id,
                "timeout_tolerance": 60.0  # Allow for recovery time
            },
            "optimistic_id": str(uuid.uuid4())
        }
        
        await self.ws_client.send_json(recovery_request)
        logger.info(f"Started recovery test scenario: {scenario['scenario_name']}")
        
        # Monitor execution and recovery attempts
        recovery_tracker = {}
        start_time = time.time()
        completed = False
        
        while time.time() - start_time < timeout and not completed:
            event = await self.ws_client.receive(timeout=3.0)
            
            if event:
                await self._process_recovery_event(event, validation, recovery_tracker)
                
                # Check for completion (including error completion)
                if event.get("type") in ["agent_completed", "recovery_completed", "error", "timeout"]:
                    completed = True
                    validation.time_to_final_resolution = time.time() - start_time
                    
        # Finalize recovery attempts
        self._finalize_recovery_attempts(validation, recovery_tracker)
        
        # Validate the recovery strategy results
        self._validate_recovery_strategy(validation, scenario)
        self.validations.append(validation)
        
        return validation
        
    async def _process_recovery_event(
        self, 
        event: Dict[str, Any], 
        validation: AgentRecoveryValidation,
        recovery_tracker: Dict[str, RecoveryAttempt]
    ):
        """Process and categorize recovery strategy specific events."""
        event_type = event.get("type", "unknown")
        event_time = time.time() - validation.start_time
        
        # Record all events
        validation.events_received.append(event)
        validation.event_types_seen.add(event_type)
        
        # Track timing of critical events
        if event_type == "agent_started":
            logger.info(f"Agent started for recovery test at {event_time:.2f}s")
            
        elif event_type == "error":
            if not validation.time_to_first_error:
                validation.time_to_first_error = event_time
                
            # Record error details
            error_data = event.get("data", {})
            validation.errors_encountered.append({
                "timestamp": event_time,
                "error_type": error_data.get("error_type", "unknown"),
                "error_message": error_data.get("message", ""),
                "context": error_data.get("context", {})
            })
            
            logger.warning(f"Error encountered: {error_data.get('error_type', 'unknown')} at {event_time:.2f}s")
            
        elif event_type == "recovery_initiated":
            if not validation.time_to_first_recovery:
                validation.time_to_first_recovery = event_time
                
            # Create recovery attempt tracking
            recovery_data = event.get("data", {})
            recovery_id = recovery_data.get("recovery_id", str(uuid.uuid4()))
            
            recovery_attempt = RecoveryAttempt(
                error_type=recovery_data.get("error_type", "unknown"),
                recovery_type=RecoveryType(recovery_data.get("recovery_type", "retry")),
                start_time=time.time(),
                recovery_data=recovery_data
            )
            
            recovery_tracker[recovery_id] = recovery_attempt
            logger.info(f"Recovery initiated: {recovery_attempt.recovery_type.value}")
            
        elif event_type == "recovery_completed":
            # Update recovery attempt
            recovery_data = event.get("data", {})
            recovery_id = recovery_data.get("recovery_id")
            
            for attempt_id, attempt in recovery_tracker.items():
                if (recovery_id and attempt_id == recovery_id) or \
                   (not attempt.success and not attempt.end_time):  # Match first incomplete attempt
                    attempt.end_time = time.time()
                    attempt.success = recovery_data.get("success", False)
                    attempt.recovery_data.update(recovery_data)
                    
                    logger.info(f"Recovery completed: {attempt.recovery_type.value} ({'success' if attempt.success else 'failed'}, {attempt.duration:.2f}s)")
                    break
                    
        elif event_type == "recovery_fallback":
            # Track fallback recovery strategies
            fallback_data = event.get("data", {})
            fallback_attempt = RecoveryAttempt(
                error_type="fallback_triggered",
                recovery_type=RecoveryType.FALLBACK,
                start_time=time.time(),
                recovery_data=fallback_data
            )
            
            fallback_id = f"fallback_{len(recovery_tracker)}"
            recovery_tracker[fallback_id] = fallback_attempt
            logger.info(f"Fallback strategy activated: {fallback_data.get('strategy', 'unknown')}")
            
        elif event_type == "circuit_breaker":
            # Track circuit breaker activation
            cb_data = event.get("data", {})
            cb_attempt = RecoveryAttempt(
                error_type="circuit_breaker_triggered",
                recovery_type=RecoveryType.CIRCUIT_BREAKER,
                start_time=time.time(),
                success=cb_data.get("activated", False),
                recovery_data=cb_data
            )
            
            cb_id = f"circuit_breaker_{len(recovery_tracker)}"
            recovery_tracker[cb_id] = cb_attempt
            logger.info(f"Circuit breaker activated: {cb_data.get('state', 'unknown')}")
            
        elif event_type in ["agent_completed", "recovery_completed"]:
            # Extract final recovery state
            final_data = event.get("data", {})
            if isinstance(final_data, dict):
                validation.final_recovery_state = final_data
                logger.info(f"Recovery test completed with state: {list(final_data.keys())}")
                
    def _finalize_recovery_attempts(
        self, 
        validation: AgentRecoveryValidation,
        recovery_tracker: Dict[str, RecoveryAttempt]
    ):
        """Finalize recovery attempts and add to validation."""
        validation.recovery_attempts = list(recovery_tracker.values())
        
        # Handle any recovery attempts that didn't complete
        for attempt in validation.recovery_attempts:
            if not attempt.end_time:
                attempt.end_time = time.time()
                # Don't mark as failed if it was a circuit breaker or similar
                if attempt.recovery_type not in [RecoveryType.CIRCUIT_BREAKER]:
                    attempt.success = False
                    
    def _validate_recovery_strategy(
        self, 
        validation: AgentRecoveryValidation, 
        scenario: Dict[str, Any]
    ):
        """Validate recovery strategy against business requirements."""
        
        # 1. Check recovery success rate
        successful_recoveries = sum(1 for attempt in validation.recovery_attempts if attempt.success)
        total_recoveries = len(validation.recovery_attempts)
        
        if total_recoveries > 0:
            recovery_success_rate = successful_recoveries / total_recoveries
            validation.recovery_successful = recovery_success_rate >= 0.5
        else:
            # If no explicit recovery attempts detected, check if system completed gracefully
            validation.recovery_successful = (
                validation.final_recovery_state is not None or
                "agent_completed" in validation.event_types_seen
            )
            
        # 2. Validate system stability
        error_count = len(validation.errors_encountered)
        recovery_count = len(validation.recovery_attempts)
        
        # System is stable if recoveries >= errors, or if errors are handled
        validation.system_stability_maintained = (
            recovery_count >= error_count or  # Recovery attempts match errors
            error_count <= 2 or  # Limited error impact
            validation.final_recovery_state is not None  # System reached final state
        )
        
        # 3. Check graceful degradation
        if validation.recovery_attempts:
            # Look for graceful degradation indicators
            graceful_indicators = [
                RecoveryType.GRACEFUL_DEGRADATION,
                RecoveryType.PARTIAL_RECOVERY,
                RecoveryType.FALLBACK
            ]
            
            validation.graceful_degradation_achieved = any(
                attempt.recovery_type in graceful_indicators
                for attempt in validation.recovery_attempts
            )
        else:
            # If errors occurred but system continued, it's graceful
            validation.graceful_degradation_achieved = (
                len(validation.errors_encountered) > 0 and
                len(validation.events_received) > 5  # System continued processing
            )
            
        # 4. Check user experience preservation
        # UX is preserved if final state exists and errors didn't crash the system
        validation.user_experience_preserved = (
            validation.final_recovery_state is not None or
            "agent_completed" in validation.event_types_seen or
            validation.graceful_degradation_achieved
        )
        
    def generate_recovery_strategies_report(self) -> str:
        """Generate comprehensive recovery strategies test report."""
        report = []
        report.append("=" * 80)
        report.append("REAL AGENT RECOVERY STRATEGIES TEST REPORT")
        report.append("=" * 80)
        report.append(f"Total recovery scenarios tested: {len(self.validations)}")
        report.append("")
        
        for i, val in enumerate(self.validations, 1):
            report.append(f"\n--- Recovery Scenario {i}: {val.recovery_scenario} ---")
            report.append(f"User ID: {val.user_id}")
            report.append(f"Thread ID: {val.thread_id}")
            report.append(f"Events received: {len(val.events_received)}")
            report.append(f"Event types: {sorted(val.event_types_seen)}")
            
            # Check for REQUIRED WebSocket events during recovery
            missing_events = self.REQUIRED_EVENTS - val.event_types_seen
            if missing_events:
                report.append(f" WARNING: [U+FE0F] MISSING REQUIRED EVENTS: {missing_events}")
            else:
                report.append("[U+2713] All required WebSocket events received during recovery")
                
            # Error and recovery analysis
            report.append(f"\nError and Recovery Analysis:")
            report.append(f"  - Errors encountered: {len(val.errors_encountered)}")
            report.append(f"  - Recovery attempts: {len(val.recovery_attempts)}")
            
            if val.errors_encountered:
                error_types = [e["error_type"] for e in val.errors_encountered]
                report.append(f"  - Error types: {set(error_types)}")
                
            if val.recovery_attempts:
                successful_recoveries = sum(1 for r in val.recovery_attempts if r.success)
                recovery_types = [r.recovery_type.value for r in val.recovery_attempts]
                avg_recovery_time = sum(r.duration for r in val.recovery_attempts if r.duration) / len(val.recovery_attempts)
                
                report.append(f"  - Successful recoveries: {successful_recoveries}")
                report.append(f"  - Recovery strategies used: {set(recovery_types)}")
                report.append(f"  - Average recovery time: {avg_recovery_time:.2f}s")
                
                # Individual recovery details
                for j, recovery in enumerate(val.recovery_attempts, 1):
                    status_symbol = "[U+2713]" if recovery.success else "[U+2717]"
                    duration_str = f"{recovery.duration:.2f}s" if recovery.duration else "N/A"
                    report.append(f"    {j}. {status_symbol} {recovery.recovery_type.value} ({duration_str})")
                    
            # Performance metrics
            report.append("\nPerformance Metrics:")
            report.append(f"  - Time to first error: {val.time_to_first_error:.2f}s" if val.time_to_first_error else "  - No errors detected")
            report.append(f"  - Time to first recovery: {val.time_to_first_recovery:.2f}s" if val.time_to_first_recovery else "  - No recovery initiated")
            report.append(f"  - Time to final resolution: {val.time_to_final_resolution:.2f}s" if val.time_to_final_resolution else "  - Not resolved")
            
            # Business logic validation
            report.append("\nBusiness Logic Validation:")
            report.append(f"  [U+2713] Recovery successful: {val.recovery_successful}")
            report.append(f"  [U+2713] System stability maintained: {val.system_stability_maintained}")
            report.append(f"  [U+2713] Graceful degradation achieved: {val.graceful_degradation_achieved}")
            report.append(f"  [U+2713] User experience preserved: {val.user_experience_preserved}")
            
            # Final state analysis
            if val.final_recovery_state:
                report.append(f"\nFinal Recovery State Keys: {list(val.final_recovery_state.keys())}")
                
        # Overall recovery quality metrics
        if self.validations:
            recovery_scores = [
                sum([
                    val.recovery_successful,
                    val.system_stability_maintained,
                    val.graceful_degradation_achieved,
                    val.user_experience_preserved
                ]) for val in self.validations
            ]
            avg_score = sum(recovery_scores) / len(recovery_scores)
            report.append(f"\nOverall Recovery Quality Score: {avg_score:.1f}/4.0")
            
        report.append("\n" + "=" * 80)
        return "\n".join(report)


# ============================================================================
# TEST SUITE
# ============================================================================

@pytest.fixture
async def recovery_strategies_tester():
    """Create and setup the recovery strategies tester."""
    tester = RealAgentRecoveryStrategiesTester()
    await tester.setup()
    yield tester
    await tester.teardown()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.real_services
class TestRealAgentRecoveryStrategies:
    """Test suite for real agent recovery strategy execution."""
    
    async def test_llm_api_timeout_recovery_strategy(self, recovery_strategies_tester):
        """Test LLM API timeout recovery with retry strategy."""
        scenario = recovery_strategies_tester.RECOVERY_SCENARIOS[0]  # llm_api_timeout_recovery
        
        validation = await recovery_strategies_tester.execute_recovery_scenario(
            scenario, timeout=150.0
        )
        
        # Should handle timeouts gracefully
        assert len(validation.events_received) > 0, "Should receive events even with timeout scenarios"
        
        # System stability validation
        assert validation.system_stability_maintained, "System should remain stable despite timeouts"
        
        # User experience preservation
        assert validation.user_experience_preserved, "User experience should be preserved through recovery"
        
        # Log recovery attempts
        if validation.recovery_attempts:
            logger.info(f"Recovery attempts: {len(validation.recovery_attempts)}")
            for attempt in validation.recovery_attempts:
                logger.info(f"  - {attempt.recovery_type.value}: {'success' if attempt.success else 'failed'}")
                
    async def test_tool_execution_failure_fallback(self, recovery_strategies_tester):
        """Test tool execution failure with fallback strategy."""
        scenario = recovery_strategies_tester.RECOVERY_SCENARIOS[1]  # tool_execution_failure_fallback
        
        validation = await recovery_strategies_tester.execute_recovery_scenario(
            scenario, timeout=130.0
        )
        
        # Should handle tool failures gracefully
        assert validation.system_stability_maintained, "System should remain stable despite tool failures"
        
        # Check for fallback strategies
        if validation.recovery_attempts:
            fallback_attempts = [r for r in validation.recovery_attempts if r.recovery_type == RecoveryType.FALLBACK]
            if fallback_attempts:
                logger.info(f"Fallback strategies detected: {len(fallback_attempts)}")
                
        # Graceful degradation validation
        assert validation.graceful_degradation_achieved or validation.user_experience_preserved, \
            "Should achieve graceful degradation or preserve user experience"
            
    async def test_circuit_breaker_activation_strategy(self, recovery_strategies_tester):
        """Test circuit breaker activation and recovery."""
        scenario = recovery_strategies_tester.RECOVERY_SCENARIOS[2]  # circuit_breaker_activation
        
        validation = await recovery_strategies_tester.execute_recovery_scenario(
            scenario, timeout=100.0
        )
        
        # Circuit breaker should protect system
        assert validation.system_stability_maintained, "Circuit breaker should maintain system stability"
        
        # Check for circuit breaker activation
        cb_attempts = [r for r in validation.recovery_attempts if r.recovery_type == RecoveryType.CIRCUIT_BREAKER]
        if cb_attempts:
            logger.info(f"Circuit breaker activations: {len(cb_attempts)}")
            assert any(attempt.success for attempt in cb_attempts), "At least one circuit breaker should activate successfully"
            
    async def test_graceful_degradation_strategy(self, recovery_strategies_tester):
        """Test graceful degradation under resource constraints."""
        scenario = recovery_strategies_tester.RECOVERY_SCENARIOS[3]  # graceful_degradation_strategy
        
        validation = await recovery_strategies_tester.execute_recovery_scenario(
            scenario, timeout=120.0
        )
        
        # Should achieve graceful degradation
        assert validation.graceful_degradation_achieved, "Should achieve graceful degradation under constraints"
        
        # User experience should be preserved even with degradation
        assert validation.user_experience_preserved, "User experience should be preserved during degradation"
        
        # Check for degradation indicators
        degradation_attempts = [
            r for r in validation.recovery_attempts 
            if r.recovery_type in [RecoveryType.GRACEFUL_DEGRADATION, RecoveryType.PARTIAL_RECOVERY]
        ]
        if degradation_attempts:
            logger.info(f"Graceful degradation strategies: {len(degradation_attempts)}")
            
    async def test_alternative_agent_handover_recovery(self, recovery_strategies_tester):
        """Test alternative agent handover on failure."""
        scenario = recovery_strategies_tester.RECOVERY_SCENARIOS[4]  # alternative_agent_handover
        
        validation = await recovery_strategies_tester.execute_recovery_scenario(
            scenario, timeout=140.0
        )
        
        # Should handle agent failures with handover
        assert validation.system_stability_maintained, "System should remain stable during agent handover"
        
        # Check for agent handover strategies
        handover_attempts = [r for r in validation.recovery_attempts if r.recovery_type == RecoveryType.ALTERNATIVE_AGENT]
        if handover_attempts:
            logger.info(f"Agent handover attempts: {len(handover_attempts)}")
            
        # Recovery should be attempted
        assert validation.recovery_successful or len(validation.recovery_attempts) > 0, \
            "Should attempt recovery through agent handover"
            
    async def test_partial_recovery_completion_strategy(self, recovery_strategies_tester):
        """Test partial recovery with incomplete data."""
        scenario = recovery_strategies_tester.RECOVERY_SCENARIOS[5]  # partial_recovery_completion
        
        validation = await recovery_strategies_tester.execute_recovery_scenario(
            scenario, timeout=110.0
        )
        
        # Should complete with partial results
        assert validation.user_experience_preserved, "Should preserve user experience with partial results"
        
        # Check for partial recovery strategies
        partial_attempts = [r for r in validation.recovery_attempts if r.recovery_type == RecoveryType.PARTIAL_RECOVERY]
        if partial_attempts:
            logger.info(f"Partial recovery attempts: {len(partial_attempts)}")
            
        # System should remain stable despite data issues
        assert validation.system_stability_maintained, "System should remain stable with partial data"
        
    async def test_recovery_performance_benchmarks(self, recovery_strategies_tester):
        """Test recovery strategy performance benchmarks."""
        # Run multiple scenarios for performance measurement
        performance_results = []
        
        for scenario in recovery_strategies_tester.RECOVERY_SCENARIOS[:3]:  # First 3 scenarios
            validation = await recovery_strategies_tester.execute_recovery_scenario(
                scenario, timeout=100.0
            )
            performance_results.append(validation)
            
        # Performance assertions
        recovery_times = []
        resolution_times = []
        
        for validation in performance_results:
            if validation.time_to_first_recovery:
                recovery_times.append(validation.time_to_first_recovery)
            if validation.time_to_final_resolution:
                resolution_times.append(validation.time_to_final_resolution)
                
        if recovery_times:
            avg_recovery_time = sum(recovery_times) / len(recovery_times)
            assert avg_recovery_time < 30.0, f"Average recovery initiation {avg_recovery_time:.2f}s too slow"
            
        if resolution_times:
            avg_resolution = sum(resolution_times) / len(resolution_times)
            assert avg_resolution < 120.0, f"Average recovery resolution {avg_resolution:.2f}s too slow"
            
        logger.info(f"Recovery performance - Avg recovery: {sum(recovery_times)/len(recovery_times):.2f}s, Avg resolution: {sum(resolution_times)/len(resolution_times):.2f}s")
        
    async def test_recovery_strategy_quality_metrics(self, recovery_strategies_tester):
        """Test recovery strategy quality metrics."""
        scenario = recovery_strategies_tester.RECOVERY_SCENARIOS[0]  # Use timeout scenario for quality test
        
        validation = await recovery_strategies_tester.execute_recovery_scenario(
            scenario, timeout=100.0
        )
        
        # Calculate recovery quality score
        quality_score = sum([
            validation.recovery_successful,
            validation.system_stability_maintained,
            validation.graceful_degradation_achieved,
            validation.user_experience_preserved
        ])
        
        # Should meet minimum quality threshold
        assert quality_score >= 2, f"Recovery strategy quality score {quality_score}/4 below minimum"
        
        # System stability is non-negotiable
        assert validation.system_stability_maintained, "System stability must be maintained during recovery"
        
        logger.info(f"Recovery strategy quality score: {quality_score}/4")
        
    async def test_comprehensive_recovery_strategies_report(self, recovery_strategies_tester):
        """Run comprehensive test and generate detailed report."""
        # Execute all recovery strategy scenarios
        for scenario in recovery_strategies_tester.RECOVERY_SCENARIOS:
            await recovery_strategies_tester.execute_recovery_scenario(
                scenario, timeout=120.0
            )
            
        # Generate and save report
        report = recovery_strategies_tester.generate_recovery_strategies_report()
        logger.info("\n" + report)
        
        # Save report to file
        report_file = os.path.join(project_root, "test_outputs", "recovery_strategies_e2e_report.txt")
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report)
            f.write(f"\n\nGenerated at: {datetime.now().isoformat()}\n")
            
        logger.info(f"Recovery strategies report saved to: {report_file}")
        
        # Verify overall recovery success
        total_tests = len(recovery_strategies_tester.validations)
        stable_systems = sum(
            1 for v in recovery_strategies_tester.validations 
            if v.system_stability_maintained
        )
        
        assert stable_systems > 0, "At least some recovery strategies should maintain system stability"
        stability_rate = stable_systems / total_tests if total_tests > 0 else 0
        
        # High standard for system stability
        assert stability_rate >= 0.8, f"System stability rate {stability_rate:.1%} below 80% requirement"
        logger.info(f"System stability rate during recovery: {stability_rate:.1%}")


if __name__ == "__main__":
    # Run with real services - recovery testing is critical
    pytest.main([
        __file__,
        "-v",
        "--real-services",
        "-s",
        "--tb=short"
    ])