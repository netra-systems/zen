"""
Error Recovery Integration Test - Issue #1059 Agent Golden Path Tests

Business Value Justification:
- Segment: All tiers - System reliability and fault tolerance
- Business Goal: Validate system graceful degradation and error recovery capabilities
- Value Impact: Ensures system remains functional during failures, maintaining user experience
- Revenue Impact: Prevents revenue loss from system failures ($500K+ ARR protection)

PURPOSE:
This integration test validates that the system gracefully handles agent failures,
recovers from error conditions, and maintains service availability even when
individual agents or components fail. This is critical for production reliability.

CRITICAL ERROR RECOVERY SCENARIOS:
1. Agent processing timeouts and recovery
2. WebSocket connection failures and reconnection
3. Tool execution errors and fallback handling
4. Invalid input handling and user feedback
5. System overload conditions and graceful degradation
6. Partial failures with continued service availability

CRITICAL DESIGN:
- NO DOCKER usage - tests run against GCP staging environment
- Real error condition simulation with controlled recovery testing
- Comprehensive validation of error handling and user communication
- Performance monitoring during error conditions
- User experience preservation during failures
- System stability validation after recovery

SCOPE:
1. Agent timeout and recovery scenarios
2. WebSocket connection resilience testing
3. Tool execution failure handling
4. System overload and graceful degradation
5. Error communication and user feedback validation
6. Recovery performance and stability assessment

AGENT_SESSION_ID: agent-session-2025-09-14-1430
Issue #1059: Agent Golden Path Integration Tests - Step 1 Implementation
"""

import asyncio
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum

import pytest
import websockets
from websockets import ConnectionClosed, WebSocketException

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, AuthenticatedUser
from tests.e2e.staging_config import StagingTestConfig
from shared.isolated_environment import get_env

logger = logging.getLogger(__name__)


class ErrorScenarioType(Enum):
    """Types of error scenarios for recovery testing."""
    AGENT_TIMEOUT = "agent_timeout"
    WEBSOCKET_CONNECTION_FAILURE = "websocket_connection_failure"
    TOOL_EXECUTION_ERROR = "tool_execution_error"
    INVALID_INPUT_HANDLING = "invalid_input_handling"
    SYSTEM_OVERLOAD = "system_overload"
    PARTIAL_SERVICE_FAILURE = "partial_service_failure"


@dataclass
class ErrorScenario:
    """Represents an error scenario for testing."""
    scenario_type: ErrorScenarioType
    description: str
    trigger_message: Dict[str, Any]
    expected_recovery_behaviors: List[str]
    timeout_threshold: float
    success_criteria: List[str]


@dataclass
class ErrorRecoveryResult:
    """Results of error recovery testing for a specific scenario."""
    scenario_type: ErrorScenarioType
    error_triggered: bool
    recovery_successful: bool
    recovery_time: float
    user_feedback_provided: bool
    service_maintained: bool
    error_messages_received: List[str]
    recovery_events: List[Dict[str, Any]]
    final_user_experience: str  # "good", "degraded", "failed"
    business_continuity_maintained: bool


@dataclass
class ErrorRecoveryValidationResult:
    """Comprehensive error recovery validation results."""
    recovery_validation_successful: bool
    scenarios_tested: List[ErrorRecoveryResult]
    overall_reliability_score: float
    graceful_degradation_score: float
    user_experience_preservation_score: float
    system_stability_after_recovery: bool
    enterprise_reliability_readiness: bool
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)


class ErrorRecoveryValidator:
    """Validates system error recovery and fault tolerance."""
    
    # Recovery time thresholds (in seconds)
    EXCELLENT_RECOVERY_TIME = 5.0
    ACCEPTABLE_RECOVERY_TIME = 15.0
    POOR_RECOVERY_TIME = 30.0
    
    # Error indicators in responses
    ERROR_INDICATORS = [
        "error", "failed", "timeout", "unavailable", "unable to", 
        "system issue", "technical difficulty", "try again", "apologize"
    ]
    
    # Recovery indicators
    RECOVERY_INDICATORS = [
        "recovering", "retrying", "alternative", "fallback", 
        "trying again", "different approach", "backup", "restored"
    ]
    
    # User experience indicators
    GOOD_UX_INDICATORS = [
        "working on", "alternative solution", "different approach", 
        "still available", "partial result", "basic functionality"
    ]
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.error_scenarios: List[ErrorScenario] = []
        self.scenario_results: List[ErrorRecoveryResult] = []
        self.validation_start_time = time.time()
        self.baseline_performance: Optional[float] = None
        
    def create_error_scenarios(self) -> List[ErrorScenario]:
        """Create comprehensive error scenarios for testing."""
        scenarios = [
            ErrorScenario(
                scenario_type=ErrorScenarioType.AGENT_TIMEOUT,
                description="Test agent timeout handling with very complex request",
                trigger_message={
                    "message": "Please perform an extremely comprehensive analysis of all possible optimization strategies for a global enterprise SaaS platform across 47 different industries with detailed ROI calculations for each vertical, competitive analysis for 200+ competitors, market sizing for each geographic region, regulatory compliance requirements for 15 jurisdictions, technology architecture recommendations, staffing plans, budget allocations, risk assessments, and implementation timelines with quarterly milestones for the next 5 years. Include detailed financial projections, sensitivity analysis, and Monte Carlo simulations.",
                    "context": {"complexity_level": "extreme", "timeout_test": True}
                },
                expected_recovery_behaviors=["timeout_handling", "user_notification", "partial_results"],
                timeout_threshold=45.0,
                success_criteria=["user_notified", "graceful_failure", "system_stable"]
            ),
            
            ErrorScenario(
                scenario_type=ErrorScenarioType.INVALID_INPUT_HANDLING,
                description="Test handling of malformed or invalid input",
                trigger_message={
                    "message": "",  # Empty message
                    "context": {"test_invalid_input": True}
                },
                expected_recovery_behaviors=["input_validation", "user_guidance", "helpful_error"],
                timeout_threshold=10.0,
                success_criteria=["helpful_error_message", "user_guidance_provided", "system_stable"]
            ),
            
            ErrorScenario(
                scenario_type=ErrorScenarioType.TOOL_EXECUTION_ERROR,
                description="Test tool execution failure handling",
                trigger_message={
                    "message": "Please access the database table 'nonexistent_impossible_table_xyz_123' and perform complex analytics on columns that don't exist in our system.",
                    "context": {"tool_error_test": True, "expect_tool_failure": True}
                },
                expected_recovery_behaviors=["tool_error_handling", "fallback_approach", "user_explanation"],
                timeout_threshold=20.0,
                success_criteria=["error_explained", "alternative_provided", "system_stable"]
            ),
            
            ErrorScenario(
                scenario_type=ErrorScenarioType.WEBSOCKET_CONNECTION_FAILURE,
                description="Test WebSocket connection resilience",
                trigger_message={
                    "message": "Please provide a comprehensive business analysis while I test connection stability.",
                    "context": {"connection_test": True}
                },
                expected_recovery_behaviors=["connection_retry", "event_recovery", "state_preservation"],
                timeout_threshold=25.0,
                success_criteria=["connection_maintained", "events_delivered", "response_received"]
            )
        ]
        
        self.error_scenarios = scenarios
        return scenarios
    
    async def execute_error_scenario(self, scenario: ErrorScenario, 
                                   websocket_url: str, websocket_headers: Dict[str, str],
                                   connection_timeout: float = 15.0) -> ErrorRecoveryResult:
        """Execute a specific error scenario and validate recovery."""
        scenario_start_time = time.time()
        
        print(f"[ERROR RECOVERY] Executing scenario: {scenario.scenario_type.value}")
        print(f"[ERROR RECOVERY] Description: {scenario.description}")
        
        # Generate unique identifiers for this scenario
        thread_id = f"error_thread_{scenario.scenario_type.value}_{uuid.uuid4()}"
        run_id = f"error_run_{scenario.scenario_type.value}_{uuid.uuid4()}"
        
        # Prepare the test message
        test_message = {
            **scenario.trigger_message,
            "thread_id": thread_id,
            "run_id": run_id
        }
        
        # Initialize result tracking
        error_triggered = False
        recovery_successful = False
        user_feedback_provided = False
        service_maintained = True
        error_messages_received = []
        recovery_events = []
        
        try:
            # Handle WebSocket connection failure scenario specially
            if scenario.scenario_type == ErrorScenarioType.WEBSOCKET_CONNECTION_FAILURE:
                recovery_result = await self._test_websocket_resilience(
                    scenario, test_message, websocket_url, websocket_headers, scenario_start_time
                )
                return recovery_result
            
            # Standard error scenario testing
            async with websockets.connect(
                websocket_url,
                additional_headers=websocket_headers,
                timeout=connection_timeout,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                
                # Send the error-triggering message
                await websocket.send(json.dumps(test_message))
                
                # Monitor for error conditions and recovery
                monitoring_start = time.time()
                response_content = ""
                events_received = []
                
                while time.time() - monitoring_start < scenario.timeout_threshold:
                    try:
                        response_text = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=10.0
                        )
                        
                        response_data = json.loads(response_text)
                        event_type = response_data.get("type", response_data.get("event_type", "unknown"))
                        events_received.append(response_data)
                        
                        # Check for error indicators
                        content = response_data.get("content", response_data.get("message", ""))
                        if content:
                            response_content += content
                            
                            # Detect error conditions
                            content_lower = content.lower()
                            if any(indicator in content_lower for indicator in self.ERROR_INDICATORS):
                                error_triggered = True
                                error_messages_received.append(content)
                                print(f"[ERROR RECOVERY] Error detected: {content[:100]}...")
                            
                            # Detect recovery attempts
                            if any(indicator in content_lower for indicator in self.RECOVERY_INDICATORS):
                                recovery_events.append(response_data)
                                print(f"[ERROR RECOVERY] Recovery behavior detected: {content[:100]}...")
                            
                            # Check for user feedback
                            if any(indicator in content_lower for indicator in self.GOOD_UX_INDICATORS):
                                user_feedback_provided = True
                        
                        # Check for completion or system response
                        if event_type in ["agent_completed", "error", "system_error"]:
                            print(f"[ERROR RECOVERY] Scenario completion event: {event_type}")
                            break
                            
                    except asyncio.TimeoutError:
                        # Timeout might be expected for certain scenarios
                        if scenario.scenario_type == ErrorScenarioType.AGENT_TIMEOUT:
                            error_triggered = True
                            print(f"[ERROR RECOVERY] Expected timeout occurred for timeout scenario")
                        continue
                        
                    except (ConnectionClosed, WebSocketException) as e:
                        if scenario.scenario_type == ErrorScenarioType.WEBSOCKET_CONNECTION_FAILURE:
                            error_triggered = True
                            print(f"[ERROR RECOVERY] Expected WebSocket error: {e}")
                        else:
                            service_maintained = False
                            print(f"[ERROR RECOVERY] Unexpected WebSocket error: {e}")
                        break
                
        except Exception as e:
            print(f"[ERROR RECOVERY] Scenario execution error: {e}")
            service_maintained = False
            error_messages_received.append(f"Execution error: {e}")
        
        # Evaluate recovery success
        recovery_time = time.time() - scenario_start_time
        recovery_successful = self._evaluate_recovery_success(
            scenario, error_triggered, user_feedback_provided, 
            service_maintained, recovery_time, response_content
        )
        
        # Determine user experience quality
        final_user_experience = self._assess_user_experience(
            error_triggered, recovery_successful, user_feedback_provided, 
            service_maintained, response_content
        )
        
        # Check business continuity
        business_continuity_maintained = (
            service_maintained and 
            (recovery_successful or user_feedback_provided) and
            final_user_experience != "failed"
        )
        
        result = ErrorRecoveryResult(
            scenario_type=scenario.scenario_type,
            error_triggered=error_triggered,
            recovery_successful=recovery_successful,
            recovery_time=recovery_time,
            user_feedback_provided=user_feedback_provided,
            service_maintained=service_maintained,
            error_messages_received=error_messages_received,
            recovery_events=recovery_events,
            final_user_experience=final_user_experience,
            business_continuity_maintained=business_continuity_maintained
        )
        
        self.scenario_results.append(result)
        return result
    
    async def _test_websocket_resilience(self, scenario: ErrorScenario, 
                                       test_message: Dict[str, Any],
                                       websocket_url: str, websocket_headers: Dict[str, str],
                                       start_time: float) -> ErrorRecoveryResult:
        """Test WebSocket connection resilience with reconnection."""
        recovery_events = []
        error_messages_received = []
        user_feedback_provided = False
        service_maintained = True
        
        try:
            # Attempt initial connection
            async with websockets.connect(
                websocket_url,
                additional_headers=websocket_headers,
                timeout=10.0
            ) as websocket:
                
                # Send message
                await websocket.send(json.dumps(test_message))
                
                # Collect some initial response
                initial_response = ""
                for _ in range(3):  # Try to get a few events
                    try:
                        response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response_text)
                        content = response_data.get("content", response_data.get("message", ""))
                        if content:
                            initial_response += content
                            user_feedback_provided = True
                        recovery_events.append(response_data)
                    except asyncio.TimeoutError:
                        break
                
                # Simulate connection issues by closing and reconnecting
                print(f"[ERROR RECOVERY] Simulating connection resilience test")
                
            # Test reconnection capability (in real system this would be automatic)
            await asyncio.sleep(2.0)  # Brief pause
            
            # Attempt reconnection
            async with websockets.connect(
                websocket_url,
                additional_headers=websocket_headers,
                timeout=15.0
            ) as websocket2:
                
                # Test that new connection works
                reconnect_message = {
                    **test_message,
                    "message": "Testing connection resilience - can you confirm system is operational?",
                    "run_id": f"{test_message.get('run_id', '')}_reconnect"
                }
                
                await websocket2.send(json.dumps(reconnect_message))
                
                # Verify response
                try:
                    response_text = await asyncio.wait_for(websocket2.recv(), timeout=10.0)
                    response_data = json.loads(response_text)
                    recovery_events.append(response_data)
                    user_feedback_provided = True
                    print(f"[ERROR RECOVERY] Reconnection successful")
                except asyncio.TimeoutError:
                    service_maintained = False
                    print(f"[ERROR RECOVERY] Reconnection failed")
                
        except Exception as e:
            print(f"[ERROR RECOVERY] WebSocket resilience test error: {e}")
            service_maintained = False
            error_messages_received.append(f"Connection resilience error: {e}")
        
        recovery_time = time.time() - start_time
        error_triggered = True  # Connection issues are errors
        recovery_successful = service_maintained and user_feedback_provided
        
        return ErrorRecoveryResult(
            scenario_type=scenario.scenario_type,
            error_triggered=error_triggered,
            recovery_successful=recovery_successful,
            recovery_time=recovery_time,
            user_feedback_provided=user_feedback_provided,
            service_maintained=service_maintained,
            error_messages_received=error_messages_received,
            recovery_events=recovery_events,
            final_user_experience="good" if recovery_successful else "degraded",
            business_continuity_maintained=recovery_successful
        )
    
    def _evaluate_recovery_success(self, scenario: ErrorScenario, error_triggered: bool,
                                 user_feedback_provided: bool, service_maintained: bool,
                                 recovery_time: float, response_content: str) -> bool:
        """Evaluate if recovery was successful based on scenario criteria."""
        # Basic recovery requirements
        if not service_maintained:
            return False
        
        # Scenario-specific recovery criteria
        if scenario.scenario_type == ErrorScenarioType.AGENT_TIMEOUT:
            # For timeout scenarios, success means graceful handling
            return user_feedback_provided and error_triggered
        
        elif scenario.scenario_type == ErrorScenarioType.INVALID_INPUT_HANDLING:
            # For invalid input, success means helpful error message
            return (
                user_feedback_provided and 
                len(response_content) > 20 and  # Substantial response
                any(word in response_content.lower() for word in ["help", "try", "provide", "need"])
            )
        
        elif scenario.scenario_type == ErrorScenarioType.TOOL_EXECUTION_ERROR:
            # For tool errors, success means explanation and alternatives
            return (
                user_feedback_provided and
                any(word in response_content.lower() for word in ["alternative", "different", "another", "instead"])
            )
        
        elif scenario.scenario_type == ErrorScenarioType.WEBSOCKET_CONNECTION_FAILURE:
            # For connection issues, success means maintained service
            return service_maintained and user_feedback_provided
        
        else:
            # Default recovery criteria
            return user_feedback_provided and recovery_time < self.ACCEPTABLE_RECOVERY_TIME
    
    def _assess_user_experience(self, error_triggered: bool, recovery_successful: bool,
                              user_feedback_provided: bool, service_maintained: bool,
                              response_content: str) -> str:
        """Assess the quality of user experience during error recovery."""
        if not service_maintained:
            return "failed"
        
        if recovery_successful and user_feedback_provided:
            # Check if user got helpful information
            if len(response_content) > 50 and any(
                indicator in response_content.lower() 
                for indicator in self.GOOD_UX_INDICATORS + ["help", "assist", "support"]
            ):
                return "good"
            else:
                return "degraded"
        
        elif user_feedback_provided:
            return "degraded"
        else:
            return "failed"
    
    def validate_error_recovery(self) -> ErrorRecoveryValidationResult:
        """Validate overall error recovery capabilities."""
        if not self.scenario_results:
            return ErrorRecoveryValidationResult(
                recovery_validation_successful=False,
                scenarios_tested=[],
                overall_reliability_score=0.0,
                graceful_degradation_score=0.0,
                user_experience_preservation_score=0.0,
                system_stability_after_recovery=False,
                enterprise_reliability_readiness=False,
                error_messages=["No scenarios tested"]
            )
        
        # Calculate reliability metrics
        successful_recoveries = sum(1 for result in self.scenario_results if result.recovery_successful)
        maintained_services = sum(1 for result in self.scenario_results if result.service_maintained)
        good_user_experiences = sum(1 for result in self.scenario_results if result.final_user_experience == "good")
        business_continuity_maintained = sum(1 for result in self.scenario_results if result.business_continuity_maintained)
        
        total_scenarios = len(self.scenario_results)
        
        # Calculate scores
        overall_reliability_score = successful_recoveries / total_scenarios
        graceful_degradation_score = maintained_services / total_scenarios
        user_experience_preservation_score = (good_user_experiences + 
                                            sum(1 for result in self.scenario_results 
                                                if result.final_user_experience == "degraded") * 0.5) / total_scenarios
        
        # System stability assessment
        system_stability_after_recovery = maintained_services >= total_scenarios * 0.8
        
        # Enterprise readiness assessment
        enterprise_reliability_readiness = (
            overall_reliability_score >= 0.7 and
            graceful_degradation_score >= 0.8 and
            user_experience_preservation_score >= 0.6 and
            system_stability_after_recovery
        )
        
        # Performance metrics
        average_recovery_time = sum(result.recovery_time for result in self.scenario_results) / total_scenarios
        performance_metrics = {
            "total_scenarios_tested": total_scenarios,
            "successful_recoveries": successful_recoveries,
            "average_recovery_time": average_recovery_time,
            "service_availability_rate": maintained_services / total_scenarios,
            "business_continuity_rate": business_continuity_maintained / total_scenarios
        }
        
        # Overall validation success
        recovery_validation_successful = (
            overall_reliability_score >= 0.6 and  # At least 60% recovery success
            graceful_degradation_score >= 0.7 and  # At least 70% graceful degradation
            system_stability_after_recovery
        )
        
        return ErrorRecoveryValidationResult(
            recovery_validation_successful=recovery_validation_successful,
            scenarios_tested=self.scenario_results,
            overall_reliability_score=overall_reliability_score,
            graceful_degradation_score=graceful_degradation_score,
            user_experience_preservation_score=user_experience_preservation_score,
            system_stability_after_recovery=system_stability_after_recovery,
            enterprise_reliability_readiness=enterprise_reliability_readiness,
            performance_metrics=performance_metrics
        )


class TestErrorRecoveryIntegration(SSotAsyncTestCase):
    """
    Error Recovery Integration Tests.
    
    Tests that the system gracefully handles various error conditions
    and recovers while maintaining user experience and service availability.
    """
    
    def setup_method(self, method=None):
        """Set up error recovery test environment."""
        super().setup_method(method)
        self.env = get_env()
        
        # Environment configuration
        test_env = self.env.get("TEST_ENV", "test")
        if test_env == "staging" or self.env.get("ENVIRONMENT") == "staging":
            self.test_env = "staging"
            self.staging_config = StagingTestConfig()
            self.websocket_url = self.staging_config.urls.websocket_url
            self.timeout = 70.0  # Longer timeout for error scenarios
        else:
            self.test_env = "test"
            self.websocket_url = self.env.get("TEST_WEBSOCKET_URL", "ws://localhost:8002/ws")
            self.timeout = 50.0
            
        self.e2e_helper = E2EWebSocketAuthHelper(environment=self.test_env)
        
        # Error recovery test configuration
        self.error_recovery_timeout = 90.0  # Allow time for recovery processes
        self.connection_timeout = 20.0      # Connection establishment
        
        logger.info(f"[ERROR RECOVERY SETUP] Test environment: {self.test_env}")
        logger.info(f"[ERROR RECOVERY SETUP] WebSocket URL: {self.websocket_url}")
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.error_recovery
    @pytest.mark.timeout(150)  # Allow extra time for error recovery testing
    async def test_comprehensive_error_recovery_validation(self):
        """
        Test comprehensive error recovery across multiple failure scenarios.
        
        Validates:
        1. Agent timeout handling with graceful user feedback
        2. Invalid input handling with helpful error messages
        3. Tool execution error recovery with alternatives
        4. WebSocket connection resilience and reconnection
        5. System stability after error recovery
        6. User experience preservation during failures
        
        BVJ: This test validates system reliability and fault tolerance,
        protecting the $500K+ ARR by ensuring users receive service
        even during error conditions and system failures.
        """
        test_start_time = time.time()
        print(f"[ERROR RECOVERY] Starting comprehensive error recovery validation test")
        print(f"[ERROR RECOVERY] Environment: {self.test_env}")
        
        # Create authenticated user for error recovery testing
        recovery_user = await self.e2e_helper.create_authenticated_user(
            email=f"error_recovery_{int(time.time())}@test.com",
            permissions=["read", "write", "chat", "agent_execution", "error_testing"]
        )
        
        # Initialize error recovery validator
        validator = ErrorRecoveryValidator(user_id=recovery_user.user_id)
        
        # Create comprehensive error scenarios
        error_scenarios = validator.create_error_scenarios()
        print(f"[ERROR RECOVERY] Created {len(error_scenarios)} error scenarios for testing")
        
        websocket_headers = self.e2e_helper.get_websocket_headers(recovery_user.jwt_token)
        scenario_results = []
        
        # Execute each error scenario
        for i, scenario in enumerate(error_scenarios, 1):
            print(f"[ERROR RECOVERY] Executing error scenario {i}/{len(error_scenarios)}: {scenario.scenario_type.value}")
            
            try:
                result = await validator.execute_error_scenario(
                    scenario=scenario,
                    websocket_url=self.websocket_url,
                    websocket_headers=websocket_headers,
                    connection_timeout=self.connection_timeout
                )
                
                scenario_results.append(result)
                
                print(f"[ERROR RECOVERY] Scenario {i} completed:")
                print(f"  - Error Triggered: {result.error_triggered}")
                print(f"  - Recovery Successful: {result.recovery_successful}")
                print(f"  - Recovery Time: {result.recovery_time:.2f}s")
                print(f"  - User Feedback Provided: {result.user_feedback_provided}")
                print(f"  - Service Maintained: {result.service_maintained}")
                print(f"  - User Experience: {result.final_user_experience}")
                print(f"  - Business Continuity: {result.business_continuity_maintained}")
                
            except Exception as e:
                print(f"[ERROR RECOVERY] Scenario {i} execution failed: {e}")
                # Continue with other scenarios
            
            # Brief pause between scenarios
            await asyncio.sleep(3.0)
        
        # Comprehensive error recovery validation
        validation_result = validator.validate_error_recovery()
        
        # Log comprehensive results
        test_duration = time.time() - test_start_time
        print(f"\n[ERROR RECOVERY RESULTS] Comprehensive Error Recovery Validation Results")
        print(f"[ERROR RECOVERY RESULTS] Test Duration: {test_duration:.2f}s")
        print(f"[ERROR RECOVERY RESULTS] Scenarios Tested: {len(validation_result.scenarios_tested)}")
        print(f"[ERROR RECOVERY RESULTS] Overall Reliability Score: {validation_result.overall_reliability_score:.2f}")
        print(f"[ERROR RECOVERY RESULTS] Graceful Degradation Score: {validation_result.graceful_degradation_score:.2f}")
        print(f"[ERROR RECOVERY RESULTS] User Experience Preservation: {validation_result.user_experience_preservation_score:.2f}")
        print(f"[ERROR RECOVERY RESULTS] System Stability After Recovery: {validation_result.system_stability_after_recovery}")
        print(f"[ERROR RECOVERY RESULTS] Enterprise Reliability Readiness: {validation_result.enterprise_reliability_readiness}")
        print(f"[ERROR RECOVERY RESULTS] Recovery Validation Successful: {validation_result.recovery_validation_successful}")
        print(f"[ERROR RECOVERY RESULTS] Performance Metrics: {validation_result.performance_metrics}")
        
        # Detailed scenario results
        for i, result in enumerate(validation_result.scenarios_tested, 1):
            print(f"\n[SCENARIO {i} RESULTS] {result.scenario_type.value}:")
            print(f"  - Error Triggered: {result.error_triggered}")
            print(f"  - Recovery Successful: {result.recovery_successful}")
            print(f"  - Recovery Time: {result.recovery_time:.2f}s")
            print(f"  - User Feedback: {result.user_feedback_provided}")
            print(f"  - Service Maintained: {result.service_maintained}")
            print(f"  - User Experience: {result.final_user_experience}")
            print(f"  - Business Continuity: {result.business_continuity_maintained}")
            if result.error_messages_received:
                print(f"  - Error Messages: {len(result.error_messages_received)} messages")
            if result.recovery_events:
                print(f"  - Recovery Events: {len(result.recovery_events)} events")
        
        # ASSERTIONS: Comprehensive error recovery validation
        
        # Scenario execution validation
        assert len(validation_result.scenarios_tested) >= 3, \
            f"Expected at least 3 error scenarios tested, got {len(validation_result.scenarios_tested)}"
        
        # Overall reliability validation
        assert validation_result.overall_reliability_score >= 0.5, \
            f"Overall reliability score {validation_result.overall_reliability_score:.2f} below minimum 0.5"
        
        # Graceful degradation validation
        assert validation_result.graceful_degradation_score >= 0.7, \
            f"Graceful degradation score {validation_result.graceful_degradation_score:.2f} below minimum 0.7"
        
        # System stability validation
        assert validation_result.system_stability_after_recovery, \
            "System stability not maintained after error recovery"
        
        # User experience validation
        assert validation_result.user_experience_preservation_score >= 0.4, \
            f"User experience preservation {validation_result.user_experience_preservation_score:.2f} below minimum 0.4"
        
        # Service availability validation
        service_availability = validation_result.performance_metrics.get("service_availability_rate", 0)
        assert service_availability >= 0.8, \
            f"Service availability rate {service_availability:.2f} below minimum 0.8"
        
        # Business continuity validation
        business_continuity = validation_result.performance_metrics.get("business_continuity_rate", 0)
        assert business_continuity >= 0.6, \
            f"Business continuity rate {business_continuity:.2f} below minimum 0.6"
        
        # Overall recovery validation
        assert validation_result.recovery_validation_successful, \
            f"Error recovery validation failed: {validation_result.error_messages}"
        
        print(f"[ERROR RECOVERY SUCCESS] Comprehensive error recovery validation passed!")
        print(f"[ERROR RECOVERY SUCCESS] System demonstrates reliable error handling and recovery")
        print(f"[ERROR RECOVERY SUCCESS] Overall reliability score: {validation_result.overall_reliability_score:.2f}")
        print(f"[ERROR RECOVERY SUCCESS] Graceful degradation score: {validation_result.graceful_degradation_score:.2f}")
        print(f"[ERROR RECOVERY SUCCESS] User experience preserved during failures")
        print(f"[ERROR RECOVERY SUCCESS] Enterprise reliability readiness: {validation_result.enterprise_reliability_readiness}")
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.timeout(60)
    async def test_system_overload_graceful_degradation(self):
        """
        Test system behavior under overload conditions with graceful degradation.
        
        Validates that the system maintains basic functionality even when
        under stress or overload conditions, providing degraded but functional service.
        """
        print(f"[OVERLOAD RECOVERY] Starting system overload graceful degradation test")
        
        # Create user for overload testing
        overload_user = await self.e2e_helper.create_authenticated_user(
            email=f"overload_test_{int(time.time())}@test.com",
            permissions=["read", "write", "chat"]
        )
        
        # Initialize validator
        validator = ErrorRecoveryValidator(user_id=overload_user.user_id)
        
        # Create overload scenario
        overload_scenario = ErrorScenario(
            scenario_type=ErrorScenarioType.SYSTEM_OVERLOAD,
            description="Test system overload handling",
            trigger_message={
                "message": "I need immediate assistance with multiple urgent business issues: customer acquisition optimization, financial analysis, market expansion strategy, competitive analysis, and operational efficiency improvements. Please provide comprehensive recommendations for all areas.",
                "context": {"priority": "urgent", "multiple_requests": True}
            },
            expected_recovery_behaviors=["load_management", "prioritization", "graceful_response"],
            timeout_threshold=35.0,
            success_criteria=["partial_response", "user_guidance", "system_stable"]
        )
        
        websocket_headers = self.e2e_helper.get_websocket_headers(overload_user.jwt_token)
        
        # Execute overload scenario
        result = await validator.execute_error_scenario(
            scenario=overload_scenario,
            websocket_url=self.websocket_url,
            websocket_headers=websocket_headers,
            connection_timeout=15.0
        )
        
        print(f"[OVERLOAD RECOVERY RESULTS] System Overload Test Results:")
        print(f"  - Service Maintained: {result.service_maintained}")
        print(f"  - User Feedback Provided: {result.user_feedback_provided}")
        print(f"  - Recovery Time: {result.recovery_time:.2f}s")
        print(f"  - Final User Experience: {result.final_user_experience}")
        
        # Overload recovery assertions
        assert result.service_maintained, \
            "System should maintain service even under overload conditions"
        
        assert result.user_feedback_provided, \
            "System should provide user feedback during overload conditions"
        
        assert result.final_user_experience != "failed", \
            f"User experience should not completely fail under overload: {result.final_user_experience}"
        
        print(f"[OVERLOAD RECOVERY SUCCESS] System overload graceful degradation validated successfully")


if __name__ == "__main__":
    # Allow running this test file directly
    import asyncio
    
    async def run_test():
        test_instance = TestErrorRecoveryIntegration()
        test_instance.setup_method()
        await test_instance.test_comprehensive_error_recovery_validation()
        print("Direct test execution completed successfully")
    
    asyncio.run(run_test())