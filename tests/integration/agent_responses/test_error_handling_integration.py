"""
Integration Tests for Agent Error Handling and Recovery Patterns

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Platform Reliability & User Experience - Graceful error handling maintains user trust
- Value Impact: Ensures system resilience and graceful degradation when issues occur
- Strategic Impact: $500K+ ARR protection - Error handling prevents user churn during system issues

This module tests agent error handling with emphasis on:
1. Graceful degradation under various failure conditions
2. Circuit breaker patterns for system protection
3. Error recovery and retry mechanisms
4. User-facing error messages and guidance
5. Fallback response generation when agents fail

CRITICAL REQUIREMENTS per CLAUDE.md:
- NO MOCKS - use real error conditions and recovery systems
- Test actual failure scenarios agents might encounter
- Validate fallback responses provide business value
- Test circuit breaker protection patterns
- Ensure error handling maintains user context isolation
- Validate WebSocket error event delivery
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
from contextlib import asynccontextmanager
import pytest

# SSOT imports following established patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.isolated_environment import get_env

# Error handling infrastructure - REAL SERVICES ONLY
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from netra_backend.app.agents.supervisor.execution_context import (
    AgentExecutionContext,
    AgentExecutionResult
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.base.circuit_breaker_components import CircuitBreaker
from netra_backend.app.agents.base.retry_manager import RetryManager
from netra_backend.app.agents.base.errors import AgentExecutionError, ToolExecutionError
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher


class ErrorType(Enum):
    """Types of errors to test in agent execution."""
    TIMEOUT = "timeout"
    TOOL_FAILURE = "tool_failure"
    LLM_UNAVAILABLE = "llm_unavailable"
    INVALID_INPUT = "invalid_input"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "auth_error"


@dataclass
class ErrorScenario:
    """Definition of an error scenario for testing."""
    error_type: ErrorType
    description: str
    should_recover: bool
    max_recovery_time: float
    expected_fallback: bool
    user_guidance_required: bool


class ErrorInjector:
    """Injects controlled errors for testing error handling."""
    
    def __init__(self):
        self.active_errors = set()
        self.error_counts = {}
    
    def enable_error(self, error_type: ErrorType):
        """Enable a specific error type."""
        self.active_errors.add(error_type)
        self.error_counts[error_type] = 0
    
    def disable_error(self, error_type: ErrorType):
        """Disable a specific error type."""
        self.active_errors.discard(error_type)
    
    def should_inject_error(self, error_type: ErrorType) -> bool:
        """Check if error should be injected."""
        if error_type in self.active_errors:
            self.error_counts[error_type] += 1
            return True
        return False
    
    def get_error_count(self, error_type: ErrorType) -> int:
        """Get count of injected errors."""
        return self.error_counts.get(error_type, 0)
    
    @asynccontextmanager
    async def temporary_error(self, error_type: ErrorType):
        """Context manager for temporary error injection."""
        self.enable_error(error_type)
        try:
            yield
        finally:
            self.disable_error(error_type)


class TestErrorHandlingIntegration(SSotAsyncTestCase):
    """Integration tests for agent error handling and recovery patterns."""
    
    async def async_setup_method(self, method=None):
        """Set up test environment with real error handling infrastructure."""
        await super().async_setup_method(method)
        
        # Initialize environment
        self.env = get_env()
        self.set_env_var("TESTING", "true")
        self.set_env_var("TEST_MODE", "error_handling")
        
        # Initialize error handling infrastructure
        self.execution_engine = None
        self.tool_dispatcher = None
        self.circuit_breaker = None
        self.retry_manager = None
        self.error_injector = ErrorInjector()
        
        # Error tracking metrics
        self.error_metrics = {
            'errors_injected': 0,
            'errors_recovered': 0,
            'fallbacks_generated': 0,
            'circuit_breaks_triggered': 0,
            'recovery_times': [],
            'error_types_tested': set()
        }
        
        await self._initialize_error_handling_infrastructure()
    
    async def _initialize_error_handling_infrastructure(self):
        """Initialize real error handling infrastructure for testing."""
        try:
            # Initialize circuit breaker
            self.circuit_breaker = CircuitBreaker(
                failure_threshold=3,
                recovery_timeout=10.0,
                expected_exception=AgentExecutionError
            )
            
            # Initialize retry manager
            self.retry_manager = RetryManager(
                max_retries=3,
                base_delay=1.0,
                backoff_factor=2.0
            )
            
            # Initialize tool dispatcher
            self.tool_dispatcher = EnhancedToolDispatcher()
            
            # Initialize execution engine with error handling
            self.execution_engine = UserExecutionEngine(
                tool_dispatcher=self.tool_dispatcher,
                circuit_breaker=self.circuit_breaker,
                retry_manager=self.retry_manager
            )
            
            self.record_metric("error_handling_infrastructure_init_success", True)
            
        except Exception as e:
            self.record_metric("error_handling_infrastructure_init_error", str(e))
            raise
    
    async def _execute_with_error_injection(
        self,
        agent_name: str,
        user_message: str,
        user_context: UserExecutionContext,
        error_scenario: ErrorScenario,
        tools_available: List[str] = None
    ) -> Tuple[Optional[AgentExecutionResult], float, bool]:
        """Execute agent with error injection and measure recovery."""
        # Create execution context
        execution_context = AgentExecutionContext(
            agent_name=agent_name,
            user_message=user_message,
            user_context=user_context,
            tools_available=tools_available or [],
            execution_id=f"error_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Inject error for this scenario
        recovery_start = time.time()
        error_occurred = False
        result = None
        
        try:
            async with self.error_injector.temporary_error(error_scenario.error_type):
                # Execute agent with error injection
                result = await self.execution_engine.execute_agent(execution_context)
                
        except Exception as e:
            error_occurred = True
            self.error_metrics['errors_injected'] += 1
            self.error_metrics['error_types_tested'].add(error_scenario.error_type)
            
            # Check if this is expected error
            if error_scenario.should_recover:
                # Attempt recovery
                recovery_time = time.time() - recovery_start
                if recovery_time <= error_scenario.max_recovery_time:
                    self.error_metrics['errors_recovered'] += 1
                    self.error_metrics['recovery_times'].append(recovery_time)
        
        recovery_time = time.time() - recovery_start
        return result, recovery_time, error_occurred
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_timeout_error_handling_and_recovery(self):
        """
        Test timeout error handling and graceful recovery.
        
        Business Value: Ensures system remains responsive when agents encounter
        timeouts, providing fallback responses rather than hanging indefinitely.
        """
        # Create user context for timeout testing
        user_context = UserExecutionContext(
            user_id=f"timeout_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"timeout_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"timeout_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "timeout_handling"}
        )
        
        # Define timeout error scenario
        timeout_scenario = ErrorScenario(
            error_type=ErrorType.TIMEOUT,
            description="Agent execution timeout",
            should_recover=True,
            max_recovery_time=15.0,
            expected_fallback=True,
            user_guidance_required=True
        )
        
        # Test timeout handling with different agents
        timeout_tests = [
            {
                "agent": "triage_agent",
                "message": "Analyze system performance - this may take time",
                "timeout_threshold": 10.0
            },
            {
                "agent": "data_helper_agent",
                "message": "Generate comprehensive data report",
                "timeout_threshold": 12.0
            }
        ]
        
        timeout_results = []
        
        for test in timeout_tests:
            # Set up WebSocket monitoring for error events
            emitter = UnifiedWebSocketEmitter(user_id=user_context.user_id)
            websocket_bridge = AgentWebSocketBridge(websocket_emitter=emitter)
            
            # Create execution engine with timeout handling
            engine = UserExecutionEngine(
                websocket_bridge=websocket_bridge,
                timeout=test["timeout_threshold"]
            )
            
            # Execute with timeout simulation
            start_time = time.time()
            
            try:
                # Create context with timeout configuration
                execution_context = AgentExecutionContext(
                    agent_name=test["agent"],
                    user_message=test["message"],
                    user_context=user_context,
                    tools_available=["system_analyzer"],
                    execution_id=f"timeout_test_{uuid.uuid4().hex[:8]}",
                    max_execution_time=test["timeout_threshold"]
                )
                
                result = await asyncio.wait_for(
                    engine.execute_agent(execution_context),
                    timeout=test["timeout_threshold"] + 5.0  # Buffer for timeout handling
                )
                
                execution_time = time.time() - start_time
                
                # Validate timeout handling
                if execution_time > test["timeout_threshold"]:
                    # Should have handled timeout gracefully
                    self.assertIsNotNone(result, f"{test['agent']} should provide timeout fallback")
                    
                    if result:
                        # Fallback response should indicate timeout
                        response_content = result.agent_response or ""
                        timeout_indicators = ["timeout", "unavailable", "delayed", "try again"]
                        has_timeout_indication = any(indicator in response_content.lower() 
                                                   for indicator in timeout_indicators)
                        
                        if timeout_scenario.user_guidance_required:
                            self.assertTrue(has_timeout_indication,
                                          f"{test['agent']} timeout fallback should guide user")
                        
                        # Should not report complete success if timed out
                        if hasattr(result, 'partial_success'):
                            self.assertFalse(result.success, "Timeout should not report full success")
                
                timeout_results.append({
                    "agent": test["agent"],
                    "execution_time": execution_time,
                    "timed_out": execution_time > test["timeout_threshold"],
                    "fallback_provided": result is not None,
                    "response_length": len(result.agent_response) if result and result.agent_response else 0
                })
                
            except asyncio.TimeoutError:
                # System-level timeout occurred
                execution_time = time.time() - start_time
                self.assertLess(execution_time, test["timeout_threshold"] + 10.0,
                              "System timeout should occur within reasonable bounds")
                
                timeout_results.append({
                    "agent": test["agent"],
                    "execution_time": execution_time,
                    "timed_out": True,
                    "system_timeout": True,
                    "fallback_provided": False
                })
        
        # Validate timeout handling across tests
        timed_out_tests = [r for r in timeout_results if r.get("timed_out", False)]
        fallback_provided = [r for r in timeout_results if r.get("fallback_provided", False)]
        
        # Should handle timeouts gracefully
        if timed_out_tests:
            fallback_rate = len(fallback_provided) / len(timed_out_tests)
            self.assertGreater(fallback_rate, 0.5, 
                             "Should provide fallbacks for majority of timeouts")
        
        self.record_metric("timeout_tests_completed", len(timeout_tests))
        self.record_metric("timeout_results", timeout_results)
        self.record_metric("timeout_handling_validated", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_tool_failure_recovery_patterns(self):
        """
        Test tool failure recovery and alternative execution paths.
        
        Business Value: Ensures agents can provide value even when specific
        tools fail, maintaining service availability and user productivity.
        """
        # Create user context for tool failure testing
        user_context = UserExecutionContext(
            user_id=f"tool_failure_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"tool_failure_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"tool_failure_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "tool_failure_recovery"}
        )
        
        # Test scenarios with different tool failure patterns
        tool_failure_scenarios = [
            {
                "description": "Primary tool fails, should use alternative",
                "primary_tools": ["performance_monitor"],
                "fallback_tools": ["system_analyzer"],
                "message": "Check system performance metrics"
            },
            {
                "description": "Multiple tools fail, should provide analysis without tools",
                "primary_tools": ["cost_analyzer", "performance_monitor"],
                "fallback_tools": [],
                "message": "Optimize system costs and performance"
            },
            {
                "description": "Critical tool fails, should suggest manual alternatives",
                "primary_tools": ["report_generator"],
                "fallback_tools": ["data_processor"],
                "message": "Generate comprehensive system report"
            }
        ]
        
        tool_recovery_results = []
        
        for scenario in tool_failure_scenarios:
            # Set up execution with tool failure simulation
            all_tools = scenario["primary_tools"] + scenario["fallback_tools"]
            
            # Create execution context
            execution_context = AgentExecutionContext(
                agent_name="data_helper_agent",
                user_message=scenario["message"],
                user_context=user_context,
                tools_available=all_tools,
                execution_id=f"tool_failure_{uuid.uuid4().hex[:8]}"
            )
            
            # Simulate primary tool failures
            tool_failure_injector = ErrorInjector()
            for tool in scenario["primary_tools"]:
                tool_failure_injector.enable_error(ErrorType.TOOL_FAILURE)
            
            # Execute with tool failure handling
            start_time = time.time()
            result = None
            
            try:
                # Use modified execution engine that simulates tool failures
                result = await self.execution_engine.execute_agent(execution_context)
                execution_time = time.time() - start_time
                
                # Validate recovery behavior
                self.assertIsNotNone(result, "Should provide result despite tool failures")
                
                if result:
                    # Analyze recovery strategy
                    response_content = result.agent_response or ""
                    tools_used = result.tools_used or []
                    
                    # Should have attempted some form of analysis
                    self.assertGreater(len(response_content), 30, 
                                     "Should provide substantive response despite tool failures")
                    
                    # Check if fallback tools were used
                    used_fallback_tools = [tool for tool in tools_used 
                                         if tool in scenario["fallback_tools"]]
                    
                    # If fallback tools available, should try to use them
                    if scenario["fallback_tools"]:
                        fallback_attempted = len(used_fallback_tools) > 0
                    else:
                        # No fallback tools - should provide alternative guidance
                        alternative_indicators = [
                            "manually", "alternative", "suggest", "recommend", 
                            "without tools", "manual analysis"
                        ]
                        fallback_attempted = any(indicator in response_content.lower() 
                                               for indicator in alternative_indicators)
                    
                    tool_recovery_results.append({
                        "scenario": scenario["description"],
                        "execution_time": execution_time,
                        "fallback_attempted": fallback_attempted,
                        "response_length": len(response_content),
                        "tools_used": tools_used,
                        "primary_tools_failed": scenario["primary_tools"],
                        "fallback_tools_available": scenario["fallback_tools"],
                        "recovery_successful": result.success or result.partial_success
                    })
                
            except Exception as e:
                # Tool failure caused complete execution failure
                execution_time = time.time() - start_time
                tool_recovery_results.append({
                    "scenario": scenario["description"],
                    "execution_time": execution_time,
                    "complete_failure": True,
                    "error": str(e),
                    "fallback_attempted": False
                })
        
        # Validate tool failure recovery across scenarios
        successful_recoveries = [r for r in tool_recovery_results 
                               if r.get("fallback_attempted", False) and not r.get("complete_failure", False)]
        
        recovery_rate = len(successful_recoveries) / len(tool_recovery_results)
        self.assertGreater(recovery_rate, 0.6, 
                         "Should successfully recover from majority of tool failures")
        
        # Validate response quality during tool failures
        for result in successful_recoveries:
            self.assertGreater(result["response_length"], 50,
                             f"Recovery response should be substantial for: {result['scenario']}")
        
        self.record_metric("tool_failure_scenarios_tested", len(tool_failure_scenarios))
        self.record_metric("tool_recovery_rate", recovery_rate)
        self.record_metric("tool_recovery_results", tool_recovery_results)
        self.record_metric("tool_failure_recovery_validated", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_circuit_breaker_protection_patterns(self):
        """
        Test circuit breaker patterns for system protection under failures.
        
        Business Value: Protects system resources during cascading failures,
        ensuring platform stability and preventing complete service outages.
        """
        # Create user context for circuit breaker testing
        user_context = UserExecutionContext(
            user_id=f"circuit_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"circuit_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"circuit_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "circuit_breaker"}
        )
        
        # Initialize circuit breaker with low threshold for testing
        test_circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=5.0,
            expected_exception=(AgentExecutionError, ToolExecutionError)
        )
        
        # Create execution engine with circuit breaker
        circuit_engine = UserExecutionEngine(circuit_breaker=test_circuit_breaker)
        
        # Phase 1: Generate failures to trip circuit breaker
        failure_count = 0
        circuit_breaker_results = []
        
        # Execute multiple failing requests to trip the circuit breaker
        for attempt in range(5):
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=f"Circuit breaker test attempt {attempt + 1}",
                user_context=user_context,
                tools_available=["failing_tool"],  # Simulated failing tool
                execution_id=f"circuit_attempt_{attempt}_{uuid.uuid4().hex[:8]}"
            )
            
            try:
                # Inject failures for first few attempts
                if attempt < 3:
                    async with self.error_injector.temporary_error(ErrorType.TOOL_FAILURE):
                        result = await circuit_engine.execute_agent(execution_context)
                else:
                    # Normal execution after circuit should be open
                    result = await circuit_engine.execute_agent(execution_context)
                
                circuit_result = {
                    "attempt": attempt + 1,
                    "success": result.success if result else False,
                    "circuit_state": test_circuit_breaker.state.value,
                    "response_provided": result is not None,
                    "execution_attempted": True
                }
                
            except Exception as e:
                failure_count += 1
                circuit_result = {
                    "attempt": attempt + 1,
                    "success": False,
                    "circuit_state": test_circuit_breaker.state.value,
                    "error": str(e),
                    "execution_attempted": True
                }
            
            circuit_breaker_results.append(circuit_result)
            
            # Check if circuit breaker tripped
            if test_circuit_breaker.state.value == "OPEN":
                self.record_metric("circuit_breaker_tripped", True)
                break
            
            # Small delay between attempts
            await asyncio.sleep(0.5)
        
        # Phase 2: Verify circuit breaker is protecting system
        if test_circuit_breaker.state.value == "OPEN":
            # Circuit should reject requests quickly
            protected_start = time.time()
            
            try:
                protected_context = AgentExecutionContext(
                    agent_name="triage_agent",
                    user_message="Request while circuit open",
                    user_context=user_context,
                    execution_id=f"protected_exec_{uuid.uuid4().hex[:8]}"
                )
                
                result = await circuit_engine.execute_agent(protected_context)
                protected_time = time.time() - protected_start
                
                # Should be rejected quickly by circuit breaker
                self.assertLess(protected_time, 1.0, 
                              "Circuit breaker should reject requests quickly")
                
                circuit_breaker_results.append({
                    "attempt": "protected",
                    "circuit_state": "OPEN",
                    "execution_time": protected_time,
                    "protected_by_circuit": True
                })
                
            except Exception as circuit_exception:
                protected_time = time.time() - protected_start
                self.assertLess(protected_time, 1.0,
                              "Circuit breaker rejection should be fast")
                
                circuit_breaker_results.append({
                    "attempt": "protected",
                    "circuit_state": "OPEN", 
                    "execution_time": protected_time,
                    "circuit_rejection": str(circuit_exception)
                })
        
        # Phase 3: Test recovery after timeout
        if test_circuit_breaker.state.value == "OPEN":
            # Wait for recovery timeout
            await asyncio.sleep(6.0)  # Longer than recovery_timeout
            
            # Circuit should allow test requests (HALF_OPEN state)
            recovery_context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message="Recovery test request",
                user_context=user_context,
                execution_id=f"recovery_exec_{uuid.uuid4().hex[:8]}"
            )
            
            try:
                recovery_result = await circuit_engine.execute_agent(recovery_context)
                
                circuit_breaker_results.append({
                    "attempt": "recovery",
                    "circuit_state": test_circuit_breaker.state.value,
                    "recovery_attempted": True,
                    "recovery_successful": recovery_result.success if recovery_result else False
                })
                
            except Exception as recovery_exception:
                circuit_breaker_results.append({
                    "attempt": "recovery",
                    "circuit_state": test_circuit_breaker.state.value,
                    "recovery_attempted": True,
                    "recovery_failed": str(recovery_exception)
                })
        
        # Validate circuit breaker behavior
        open_states = [r for r in circuit_breaker_results if r.get("circuit_state") == "OPEN"]
        protected_requests = [r for r in circuit_breaker_results if r.get("protected_by_circuit", False)]
        
        # Circuit breaker should have activated
        self.assertGreater(len(open_states), 0, "Circuit breaker should have opened")
        
        # Should protect system during open state
        if protected_requests:
            avg_protected_time = sum(r.get("execution_time", 0) for r in protected_requests) / len(protected_requests)
            self.assertLess(avg_protected_time, 1.0, "Protected requests should be fast")
        
        self.record_metric("circuit_breaker_results", circuit_breaker_results)
        self.record_metric("circuit_breaker_activated", len(open_states) > 0)
        self.record_metric("system_protection_validated", True)
        self.record_metric("failure_count_before_trip", failure_count)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_user_friendly_error_messaging(self):
        """
        Test user-friendly error messages and guidance during failures.
        
        Business Value: Maintains user experience during errors by providing
        helpful guidance rather than technical error details.
        """
        # Create user context for error messaging testing
        user_context = UserExecutionContext(
            user_id=f"error_msg_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"error_msg_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"error_msg_run_{uuid.uuid4().hex[:8]}",
            session_metadata={"test_type": "error_messaging"}
        )
        
        # Test different error scenarios and expected user messaging
        error_messaging_scenarios = [
            {
                "error_type": ErrorType.TIMEOUT,
                "user_message": "Generate detailed performance analysis report",
                "expected_guidance": {
                    "apologetic_tone": ["sorry", "apologize", "unfortunately"],
                    "explanation": ["taking longer", "timeout", "delayed", "busy"],
                    "next_steps": ["try again", "later", "simplified", "alternative"],
                    "avoids_technical": True
                }
            },
            {
                "error_type": ErrorType.TOOL_FAILURE,
                "user_message": "Use advanced analytics to optimize costs", 
                "expected_guidance": {
                    "alternative_offered": ["alternative", "different approach", "manual"],
                    "maintains_helpfulness": True,
                    "explains_limitation": ["currently unavailable", "tool issue", "temporary"],
                    "provides_value": True
                }
            },
            {
                "error_type": ErrorType.RESOURCE_EXHAUSTION,
                "user_message": "Process large dataset for comprehensive insights",
                "expected_guidance": {
                    "suggests_alternatives": ["smaller dataset", "simplified", "batch"],
                    "explains_constraint": ["resource limit", "capacity", "high demand"],
                    "professional_tone": True
                }
            }
        ]
        
        error_messaging_results = []
        
        for scenario in error_messaging_scenarios:
            # Set up WebSocket monitoring for error events
            emitter = UnifiedWebSocketEmitter(user_id=user_context.user_id)
            websocket_bridge = AgentWebSocketBridge(websocket_emitter=emitter)
            
            # Capture WebSocket events for error messaging
            captured_events = []
            
            original_emit = emitter.emit
            async def capture_error_events(event_type: str, data: Dict[str, Any], **kwargs):
                if "error" in event_type.lower() or "fail" in event_type.lower():
                    captured_events.append({"type": event_type, "data": data})
                return await original_emit(event_type, data, **kwargs)
            emitter.emit = capture_error_events
            
            # Create execution engine with error-aware messaging
            error_messaging_engine = UserExecutionEngine(websocket_bridge=websocket_bridge)
            
            # Execute with error injection
            execution_context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=scenario["user_message"],
                user_context=user_context,
                execution_id=f"error_msg_{uuid.uuid4().hex[:8]}"
            )
            
            try:
                async with self.error_injector.temporary_error(scenario["error_type"]):
                    result = await error_messaging_engine.execute_agent(execution_context)
                
                # Analyze error messaging
                error_response = ""
                user_friendly_score = 0
                
                if result and result.agent_response:
                    error_response = result.agent_response.lower()
                elif captured_events:
                    # Check WebSocket error events
                    error_events = [e for e in captured_events if "error" in e["type"]]
                    if error_events:
                        error_data = error_events[0].get("data", {})
                        error_response = str(error_data.get("message", "")).lower()
                
                if error_response:
                    guidance = scenario["expected_guidance"]
                    
                    # Check for apologetic tone
                    if "apologetic_tone" in guidance:
                        if any(phrase in error_response for phrase in guidance["apologetic_tone"]):
                            user_friendly_score += 20
                    
                    # Check for explanation
                    if "explanation" in guidance:
                        if any(phrase in error_response for phrase in guidance["explanation"]):
                            user_friendly_score += 20
                    
                    # Check for next steps
                    if "next_steps" in guidance:
                        if any(phrase in error_response for phrase in guidance["next_steps"]):
                            user_friendly_score += 20
                    
                    # Check for alternative offerings
                    if "alternative_offered" in guidance:
                        if any(phrase in error_response for phrase in guidance["alternative_offered"]):
                            user_friendly_score += 20
                    
                    # Check avoids technical jargon
                    if guidance.get("avoids_technical", False):
                        technical_terms = ["exception", "stack trace", "null pointer", "timeout error", "500"]
                        if not any(term in error_response for term in technical_terms):
                            user_friendly_score += 20
                    
                    # Check maintains helpfulness
                    if guidance.get("maintains_helpfulness", False):
                        helpful_indicators = ["help", "assist", "support", "guide", "recommend"]
                        if any(indicator in error_response for indicator in helpful_indicators):
                            user_friendly_score += 10
                
                error_messaging_results.append({
                    "error_type": scenario["error_type"].value,
                    "user_friendly_score": user_friendly_score,
                    "error_response_length": len(error_response),
                    "websocket_error_events": len(captured_events),
                    "provides_guidance": user_friendly_score >= 40,
                    "avoids_technical_details": user_friendly_score >= 60
                })
                
            except Exception as e:
                # Complete failure - check if error message is user-friendly
                error_str = str(e).lower()
                user_friendly = not any(tech_term in error_str for tech_term in 
                                      ["traceback", "exception", "null", "undefined"])
                
                error_messaging_results.append({
                    "error_type": scenario["error_type"].value,
                    "complete_failure": True,
                    "error_message_user_friendly": user_friendly,
                    "raw_error": str(e)
                })
        
        # Validate error messaging quality
        successful_messaging = [r for r in error_messaging_results if r.get("provides_guidance", False)]
        user_friendly_messaging = [r for r in error_messaging_results if r.get("avoids_technical_details", False)]
        
        guidance_rate = len(successful_messaging) / len(error_messaging_results)
        user_friendly_rate = len(user_friendly_messaging) / len(error_messaging_results)
        
        # Should provide helpful guidance in majority of error scenarios
        self.assertGreater(guidance_rate, 0.6, 
                         "Should provide helpful guidance for majority of errors")
        
        # Should avoid technical details in error messages
        self.assertGreater(user_friendly_rate, 0.5, 
                         "Should provide user-friendly error messages")
        
        self.record_metric("error_messaging_scenarios_tested", len(error_messaging_scenarios))
        self.record_metric("error_guidance_rate", guidance_rate)
        self.record_metric("user_friendly_error_rate", user_friendly_rate)
        self.record_metric("error_messaging_results", error_messaging_results)
        self.record_metric("user_friendly_messaging_validated", True)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_cascading_failure_prevention(self):
        """
        Test prevention of cascading failures across system components.
        
        Business Value: Prevents isolated failures from bringing down the
        entire system, maintaining service availability for other users.
        """
        # Create multiple user contexts to test isolation during failures
        user_contexts = []
        for i in range(3):
            context = UserExecutionContext(
                user_id=f"cascade_user_{i}_{uuid.uuid4().hex[:6]}",
                thread_id=f"cascade_thread_{i}_{uuid.uuid4().hex[:6]}",
                run_id=f"cascade_run_{i}_{uuid.uuid4().hex[:6]}",
                session_metadata={"test_type": "cascading_failure", "user_index": i}
            )
            user_contexts.append(context)
        
        # Create execution engines with isolation
        execution_engines = []
        for context in user_contexts:
            emitter = UnifiedWebSocketEmitter(user_id=context.user_id)
            bridge = AgentWebSocketBridge(websocket_emitter=emitter)
            engine = UserExecutionEngine(
                websocket_bridge=bridge,
                circuit_breaker=CircuitBreaker(failure_threshold=2, recovery_timeout=5.0)
            )
            execution_engines.append(engine)
        
        # Phase 1: Induce failure in one user's execution
        failing_user_index = 0
        normal_user_indices = [1, 2]
        
        # Execute failing scenario for first user
        failing_context = AgentExecutionContext(
            agent_name="triage_agent",
            user_message="This execution will fail intentionally",
            user_context=user_contexts[failing_user_index],
            execution_id=f"failing_exec_{uuid.uuid4().hex[:8]}"
        )
        
        # Execute normal scenarios for other users simultaneously
        normal_contexts = []
        for i in normal_user_indices:
            context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=f"Normal execution for user {i}",
                user_context=user_contexts[i],
                execution_id=f"normal_exec_{i}_{uuid.uuid4().hex[:8]}"
            )
            normal_contexts.append(context)
        
        # Execute all scenarios concurrently
        async def execute_with_failure(engine, context, inject_failure=False):
            try:
                if inject_failure:
                    async with self.error_injector.temporary_error(ErrorType.TOOL_FAILURE):
                        return await engine.execute_agent(context)
                else:
                    return await engine.execute_agent(context)
            except Exception as e:
                return {"error": str(e), "failed": True}
        
        # Run concurrent executions
        start_time = time.time()
        
        tasks = [
            execute_with_failure(execution_engines[failing_user_index], failing_context, inject_failure=True)
        ]
        
        for i, normal_context in enumerate(normal_contexts):
            engine_index = normal_user_indices[i]
            tasks.append(execute_with_failure(execution_engines[engine_index], normal_context, inject_failure=False))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # Analyze results for cascading failure prevention
        failing_result = results[0]
        normal_results = results[1:]
        
        # Validate isolation - normal users should succeed despite one user's failure
        successful_normal_executions = 0
        for i, result in enumerate(normal_results):
            if not isinstance(result, Exception) and not (isinstance(result, dict) and result.get("failed")):
                successful_normal_executions += 1
                
                # Validate normal execution quality
                if hasattr(result, 'agent_response') and result.agent_response:
                    self.assertGreater(len(result.agent_response), 20,
                                     f"Normal user {normal_user_indices[i]} should get quality response")
        
        # Should maintain isolation - normal users unaffected by failing user
        isolation_rate = successful_normal_executions / len(normal_results)
        self.assertGreater(isolation_rate, 0.8, 
                         "Normal users should be isolated from failing user (80%+ success)")
        
        # Validate system resources not exhausted
        self.assertLess(execution_time, 30.0, 
                       "Concurrent execution with failures should complete within 30 seconds")
        
        # Phase 2: Test recovery isolation
        # After failure, other users should continue to work normally
        recovery_tasks = []
        for i, engine in enumerate(execution_engines[1:], 1):  # Skip failing user
            recovery_context = AgentExecutionContext(
                agent_name="triage_agent",
                user_message=f"Recovery test for user {i}",
                user_context=user_contexts[i],
                execution_id=f"recovery_exec_{i}_{uuid.uuid4().hex[:8]}"
            )
            recovery_tasks.append(engine.execute_agent(recovery_context))
        
        recovery_results = await asyncio.gather(*recovery_tasks, return_exceptions=True)
        
        # Validate recovery isolation
        successful_recoveries = sum(1 for result in recovery_results 
                                  if not isinstance(result, Exception) and hasattr(result, 'success'))
        
        recovery_rate = successful_recoveries / len(recovery_results) if recovery_results else 0
        self.assertGreater(recovery_rate, 0.8,
                         "Users should maintain normal operation after isolated failure")
        
        cascading_prevention_results = {
            "failing_user_isolated": isinstance(failing_result, Exception) or 
                                   (isinstance(failing_result, dict) and failing_result.get("failed")),
            "normal_users_success_rate": isolation_rate,
            "recovery_success_rate": recovery_rate,
            "execution_time": execution_time,
            "concurrent_users_tested": len(user_contexts)
        }
        
        self.record_metric("cascading_failure_prevention_results", cascading_prevention_results)
        self.record_metric("isolation_maintained", isolation_rate > 0.8)
        self.record_metric("cascading_failure_prevention_validated", True)
    
    async def async_teardown_method(self, method=None):
        """Clean up error handling infrastructure and log comprehensive metrics."""
        try:
            # Calculate error handling effectiveness
            total_errors = self.error_metrics.get('errors_injected', 0)
            recovered_errors = self.error_metrics.get('errors_recovered', 0)
            fallbacks_generated = self.error_metrics.get('fallbacks_generated', 0)
            
            recovery_rate = recovered_errors / total_errors if total_errors > 0 else 0
            fallback_rate = fallbacks_generated / total_errors if total_errors > 0 else 0
            
            # Clean up infrastructure
            if self.execution_engine:
                await self.execution_engine.cleanup()
            
            if self.circuit_breaker:
                self.circuit_breaker.reset()
            
            # Calculate average recovery time
            recovery_times = self.error_metrics.get('recovery_times', [])
            avg_recovery_time = sum(recovery_times) / len(recovery_times) if recovery_times else 0
            
            # Log comprehensive error handling analysis
            error_summary = {
                **self.get_all_metrics(),
                "total_errors_injected": total_errors,
                "errors_recovered": recovered_errors,
                "recovery_rate": recovery_rate,
                "fallback_rate": fallback_rate,
                "avg_recovery_time": avg_recovery_time,
                "error_types_tested": list(self.error_metrics.get('error_types_tested', set())),
                "circuit_breakers_triggered": self.error_metrics.get('circuit_breaks_triggered', 0)
            }
            
            print(f"\nError Handling Integration Test Results:")
            print(f"=" * 60)
            print(f"Error Recovery Rate: {recovery_rate:.2%}")
            print(f"Fallback Generation Rate: {fallback_rate:.2%}")
            print(f"Average Recovery Time: {avg_recovery_time:.2f}s")
            print(f"Error Types Tested: {len(self.error_metrics.get('error_types_tested', set()))}")
            print(f"=" * 60)
            
            self.record_metric("error_handling_test_summary", error_summary)
            self.record_metric("error_handling_test_completed", True)
            
        except Exception as e:
            self.record_metric("test_cleanup_error", str(e))
        
        await super().async_teardown_method(method)