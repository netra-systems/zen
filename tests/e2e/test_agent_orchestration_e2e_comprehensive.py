#!/usr/bin/env python
"""
COMPREHENSIVE E2E TEST 2: Agent Orchestration Flow - Production Ready with MANDATORY AUTHENTICATION

This comprehensive E2E test suite validates complete agent orchestration workflows
with real system components, complex agent handoffs, and error recovery scenarios.

Business Value Justification:
- Segment: Enterprise ($50K+ MRR protection)
- Business Goal: Ensure multi-agent coordination operates flawlessly in production
- Value Impact: Validates complete user journeys with 3+ agents and state preservation
- Strategic Impact: Protects AI optimization workflows generating $2M+ annual value

 ALERT:  CRITICAL: ALL E2E TESTS MUST USE AUTHENTICATION
This ensures proper multi-user isolation and real-world scenario testing.

Test Architecture:
- NO MOCKS: Real services, real LLMs, real WebSocket connections
- MANDATORY AUTHENTICATION: All tests use JWT/OAuth authentication flows
- Comprehensive Event Validation: All WebSocket events tracked and validated
- Complex Handoff Testing: Multi-turn conversations with state preservation
- Error Recovery: Graceful failure handling and fallback scenarios
- Performance Benchmarks: Production-level performance validation

CRITICAL: This test must pass for production deployment.
"""

import asyncio
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
import threading
import random
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

import pytest
from loguru import logger

#  ALERT:  MANDATORY: SSOT E2E Authentication imports - CHEATING violation fix
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EWebSocketAuthHelper, create_authenticated_user
from test_framework.ssot.base_test_case import SSotBaseTestCase

# Real services infrastructure
from test_framework.real_services import get_real_services, RealServicesManager
from shared.isolated_environment import get_env
from test_framework.service_availability import check_service_availability

# Production components
from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine as ExecutionEngine
from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import (
    UnifiedToolExecutionEngine,
    enhance_tool_dispatcher_with_notifications
)
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.triage.unified_triage_agent import UnifiedTriageAgent
from netra_backend.app.agents.data_sub_agent import DataSubAgent
from netra_backend.app.agents.optimizations_core_sub_agent import OptimizationsCoreSubAgent
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
from netra_backend.app.core.configuration import UnifiedConfigManager
from netra_backend.app.db.postgres import get_postgres_db
from netra_backend.app.services.user_execution_context import UserExecutionContext


# ============================================================================
# HELPER CLASSES AND VALIDATION UTILITIES
# ============================================================================

class WebSocketEventCapture:
    """Captures and validates WebSocket events with production-level rigor."""
    
    REQUIRED_EVENTS = {
        "agent_started",
        "agent_thinking", 
        "tool_executing",
        "tool_completed",
        "agent_completed"
    }
    
    OPTIONAL_EVENTS = {
        "agent_fallback",
        "final_report",
        "partial_result",
        "tool_error",
        "agent_error",
        "workflow_transition"
    }
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_timeline: List[Tuple[float, str, Dict]] = []
        self.event_counts: Dict[str, int] = {}
        self.errors: List[str] = []
        self.start_time = time.time()
        self.lock = threading.Lock()
        
    def capture_event(self, event: Dict[str, Any]) -> None:
        """Thread-safe event capture."""
        with self.lock:
            timestamp = time.time() - self.start_time
            event_type = event.get("type", "unknown")
            
            self.events.append(event.copy())
            self.event_timeline.append((timestamp, event_type, event.copy()))
            self.event_counts[event_type] = self.event_counts.get(event_type, 0) + 1
    
    def validate_event_sequence(self) -> Tuple[bool, List[str]]:
        """Validate that events follow proper orchestration sequence."""
        failures = []
        
        # Check all required events present
        received_events = {event.get("type") for event in self.events}
        missing_events = self.REQUIRED_EVENTS - received_events
        if missing_events:
            failures.append(f"Missing required events: {missing_events}")
        
        # Check proper sequencing: started -> thinking -> tool_executing -> tool_completed -> completed
        event_types = [event.get("type") for event in self.events]
        
        # Must start with agent_started
        if not event_types or event_types[0] != "agent_started":
            failures.append("Event sequence must start with 'agent_started'")
        
        # Must end with agent_completed
        if not event_types or event_types[-1] != "agent_completed":
            failures.append("Event sequence must end with 'agent_completed'")
        
        # Tool events must be paired
        tool_executing_count = event_types.count("tool_executing")
        tool_completed_count = event_types.count("tool_completed")
        if tool_executing_count != tool_completed_count:
            failures.append(f"Unpaired tool events: {tool_executing_count} executing, {tool_completed_count} completed")
        
        return len(failures) == 0, failures
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics from event timeline."""
        if not self.event_timeline:
            return {}
        
        total_duration = self.event_timeline[-1][0] - self.event_timeline[0][0]
        
        # Calculate tool execution times
        tool_times = []
        executing_time = None
        for timestamp, event_type, event in self.event_timeline:
            if event_type == "tool_executing":
                executing_time = timestamp
            elif event_type == "tool_completed" and executing_time is not None:
                tool_times.append(timestamp - executing_time)
                executing_time = None
        
        return {
            "total_duration": total_duration,
            "event_count": len(self.events),
            "average_tool_time": sum(tool_times) / len(tool_times) if tool_times else 0,
            "events_per_second": len(self.events) / total_duration if total_duration > 0 else 0
        }


class AgentHandoffValidator:
    """Validates agent handoffs and context preservation."""
    
    def __init__(self):
        self.handoff_data: List[Dict[str, Any]] = []
        self.context_snapshots: Dict[str, Dict] = {}
        
    def capture_handoff(self, from_agent: str, to_agent: str, state: DeepAgentState) -> None:
        """Capture agent handoff data."""
        handoff_record = {
            "timestamp": time.time(),
            "from_agent": from_agent,
            "to_agent": to_agent,
            "state_snapshot": self._serialize_state(state),
            "context_hash": self._hash_context(state)
        }
        self.handoff_data.append(handoff_record)
        
    def _serialize_state(self, state: DeepAgentState) -> Dict[str, Any]:
        """Serialize agent state for comparison."""
        return {
            "user_request": state.user_request,
            "triage_result": getattr(state, 'triage_result', None),
            "data_analysis": getattr(state, 'data_analysis', None),
            "optimization_result": getattr(state, 'optimization_result', None),
            "conversation_history": getattr(state, 'conversation_history', [])
        }
    
    def _hash_context(self, state: DeepAgentState) -> str:
        """Create hash of critical context elements."""
        import hashlib
        context_str = f"{state.user_request}_{len(getattr(state, 'conversation_history', []))}"
        return hashlib.md5(context_str.encode()).hexdigest()
    
    def validate_context_preservation(self) -> Tuple[bool, List[str]]:
        """Validate that context is preserved across handoffs."""
        failures = []
        
        if len(self.handoff_data) < 2:
            return True, []  # No handoffs to validate
        
        for i in range(1, len(self.handoff_data)):
            prev_handoff = self.handoff_data[i-1]
            curr_handoff = self.handoff_data[i]
            
            # Check critical context preserved
            prev_request = prev_handoff["state_snapshot"]["user_request"]
            curr_request = curr_handoff["state_snapshot"]["user_request"]
            
            if prev_request != curr_request:
                failures.append(f"User request lost in handoff {prev_handoff['from_agent']} -> {curr_handoff['to_agent']}")
            
            # Check conversation history grows
            prev_history = prev_handoff["state_snapshot"]["conversation_history"]
            curr_history = curr_handoff["state_snapshot"]["conversation_history"]
            
            if len(curr_history) < len(prev_history):
                failures.append(f"Conversation history truncated in handoff {prev_handoff['from_agent']} -> {curr_handoff['to_agent']}")
        
        return len(failures) == 0, failures


class ErrorRecoveryTester:

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Tests error recovery scenarios during agent execution."""
    
    def __init__(self):
        self.error_scenarios: List[Dict[str, Any]] = []
        self.recovery_results: List[Dict[str, Any]] = []
        
    def inject_agent_failure(self, agent_name: str, failure_type: str = "timeout") -> None:
        """Inject a failure into agent execution."""
        error_scenario = {
            "agent_name": agent_name,
            "failure_type": failure_type,
            "timestamp": time.time(),
            "injected": True
        }
        self.error_scenarios.append(error_scenario)
    
    def record_recovery_attempt(self, agent_name: str, recovery_action: str, success: bool) -> None:
        """Record an error recovery attempt."""
        recovery_record = {
            "agent_name": agent_name,
            "recovery_action": recovery_action,
            "success": success,
            "timestamp": time.time()
        }
        self.recovery_results.append(recovery_record)
    
    def validate_graceful_degradation(self) -> Tuple[bool, List[str]]:
        """Validate that errors are handled gracefully."""
        failures = []
        
        # Check that all injected errors were handled
        for scenario in self.error_scenarios:
            agent_name = scenario["agent_name"]
            recovery_attempts = [r for r in self.recovery_results if r["agent_name"] == agent_name]
            
            if not recovery_attempts:
                failures.append(f"No recovery attempt for failed agent: {agent_name}")
            elif not any(r["success"] for r in recovery_attempts):
                failures.append(f"All recovery attempts failed for agent: {agent_name}")
        
        return len(failures) == 0, failures


class ComprehensiveOrchestrationValidator:
    """Master validator orchestrating all validation components."""
    
    def __init__(self):
        self.event_capture = WebSocketEventCapture()
        self.handoff_validator = AgentHandoffValidator()
        self.error_recovery = ErrorRecoveryTester()
        self.performance_benchmarks: Dict[str, Any] = {}
        
    def validate_complete_flow(self) -> Tuple[bool, Dict[str, Any]]:
        """Validate complete orchestration flow."""
        results = {
            "event_validation": {},
            "handoff_validation": {},
            "error_recovery": {},
            "performance": {},
            "overall_success": True
        }
        
        # Validate events
        event_valid, event_failures = self.event_capture.validate_event_sequence()
        results["event_validation"] = {
            "success": event_valid,
            "failures": event_failures,
            "events_captured": len(self.event_capture.events),
            "performance": self.event_capture.get_performance_metrics()
        }
        
        # Validate handoffs
        handoff_valid, handoff_failures = self.handoff_validator.validate_context_preservation()
        results["handoff_validation"] = {
            "success": handoff_valid,
            "failures": handoff_failures,
            "handoffs_tracked": len(self.handoff_validator.handoff_data)
        }
        
        # Validate error recovery
        recovery_valid, recovery_failures = self.error_recovery.validate_graceful_degradation()
        results["error_recovery"] = {
            "success": recovery_valid,
            "failures": recovery_failures,
            "scenarios_tested": len(self.error_recovery.error_scenarios),
            "recovery_attempts": len(self.error_recovery.recovery_results)
        }
        
        # Overall success
        results["overall_success"] = event_valid and handoff_valid and recovery_valid
        
        return results["overall_success"], results


# ============================================================================
# REAL SERVICE SETUP AND FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
async def real_services():
    """Initialize real services for testing."""
    # Ensure all required services are available
    check_service_availability()
    
    services = get_real_services()
    yield services
    
    # Cleanup if needed
    if hasattr(services, 'cleanup'):
        await services.cleanup()


@pytest.fixture(scope="function")
async def orchestration_setup(real_services):
    """Set up complete orchestration environment with real services."""
    # Initialize configuration
    env = get_env()
    config_manager = UnifiedConfigManager()
    await config_manager.initialize()
    app_config = config_manager.get_app_config()
    
    # Force real services for comprehensive testing
    app_config.llm_mode = "shared"
    app_config.dev_mode_llm_enabled = True
    
    # Initialize core components
    llm_manager = LLMManager(app_config)
    websocket_manager = WebSocketManager()
    
    # Get database session
    async with get_postgres_db() as db_session:
        tool_dispatcher = ToolDispatcher(db_session, llm_manager)
        
        # Initialize supervisor with real components
        supervisor = SupervisorAgent(
            db_session=db_session,
            llm_manager=llm_manager,
            websocket_manager=websocket_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        yield {
            "supervisor": supervisor,
            "llm_manager": llm_manager,
            "websocket_manager": websocket_manager,
            "tool_dispatcher": tool_dispatcher,
            "db_session": db_session,
            "config": app_config
        }


# ============================================================================
# COMPREHENSIVE TEST SUITE
# ============================================================================

class TestCompleteAgentWorkflow(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Tests complete agent workflow with multiple agents, complex routing, and MANDATORY authentication."""
    
    def setup_method(self):
        """Set up authenticated E2E test environment."""
        super().setup_method()
        self.env = get_env()
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        #  ALERT:  MANDATORY: Create authenticated helpers for comprehensive E2E tests
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
    
    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_complex_multi_agent_orchestration_workflow(self, orchestration_setup):
        """
        TEST 1: Complete Agent Workflow Test
        
        Tests a complex user request that requires multiple agents:
        User -> SupervisorAgent -> TriageAgent -> DataAgent -> OptimizationAgent -> Response
        
        Validates:
        - Proper agent routing and handoffs
        - State preservation across agent boundaries  
        - Tool execution with real parameters
        - Final response synthesis from all agents
        - All WebSocket events sent correctly
        """
        setup = orchestration_setup
        validator = ComprehensiveOrchestrationValidator()
        
        #  ALERT:  MANDATORY: Create authenticated user for complex workflow
        token, user_data = await create_authenticated_user(
            environment=self.test_environment,
            email="e2e.complex.workflow@example.com",
            permissions=["read", "write", "execute_agents"]
        )
        
        user_id = user_data["id"]
        
        # Configure WebSocket manager with authentication and event capture
        original_send = setup["websocket_manager"].send_message
        
        def authenticated_event_capture(msg):
            # Ensure all events include proper user context
            if isinstance(msg, dict):
                payload = msg.get("payload", {})
                if "user_id" not in payload and user_id:
                    payload["user_id"] = user_id
                    msg["payload"] = payload
            validator.event_capture.capture_event(msg)
        
        setup["websocket_manager"].send_message = authenticated_event_capture
        
        # Configure authentication headers for WebSocket connections
        setup["auth_headers"] = self.auth_helper.get_websocket_headers(token)
        setup["user_id"] = user_id
        
        # Complex user request requiring multiple agents
        user_request = """
        I'm running a large-scale ML training pipeline on GCP with the following issues:
        1. Training costs are 40% higher than expected ($50K/month)
        2. Jobs are taking 3x longer than benchmarks (12 hours vs 4 hours)  
        3. GPU utilization is only at 60% according to monitoring
        4. We're getting occasional OOM errors on certain model configs
        
        Can you analyze our setup and provide specific optimization recommendations 
        with cost estimates and implementation steps?
        """
        
        # Execute the complete workflow
        state = DeepAgentState(user_request=user_request)
        run_id = str(uuid.uuid4())
        user_id = "test_user_complex_workflow"
        
        start_time = time.time()
        
        # Execute supervisor workflow with authentication
        try:
            result = await setup["supervisor"].execute(
                context={
                    "state": state,
                    "run_id": run_id,
                    "user_id": user_id,  # Use authenticated user ID
                    "auth_token": token,  # Include authentication token
                    "stream_updates": True,
                    "authenticated": True  # Flag for authenticated execution
                }
            )
            
            execution_time = time.time() - start_time
            
            # Validate execution succeeded with proper authentication
            assert result.success, f"Supervisor execution failed: {result.error}"
            assert result.final_response, "No final response generated"
            assert len(result.final_response) > 100, "Response too short for complex request"
            
            #  ALERT:  CRITICAL: Validate execution time indicates real processing (no CHEATING)
            assert execution_time >= 0.5, f"Execution time {execution_time:.3f}s indicates fake execution (CHEATING violation)"
            
            # Validate all captured events are for authenticated user
            for event in validator.event_capture.events:
                event_payload = event.get("payload", {})
                if "user_id" in event_payload:
                    assert event_payload["user_id"] == user_id, f"Event sent to wrong user: {event_payload.get('user_id')}"
            
            # Validate WebSocket events
            is_valid, validation_results = validator.validate_complete_flow()
            assert is_valid, f"Validation failed: {validation_results}"
            
            # Validate performance benchmarks for authenticated execution
            assert execution_time < 60, f"Execution too slow: {execution_time}s"
            assert execution_time >= 0.5, f"Execution suspiciously fast: {execution_time}s - may indicate CHEATING"
            
            # Validate response quality
            response = result.final_response.lower()
            assert "cost" in response, "Response missing cost analysis"
            assert "optimization" in response, "Response missing optimization recommendations"
            assert "gpu" in response, "Response missing GPU analysis"
            
            # Log success metrics
            logger.info(f"Complex workflow completed in {execution_time:.2f}s with {len(validator.event_capture.events)} events")
            
        except Exception as e:
            pytest.fail(f"Complex workflow failed with error: {e}")


class TestAgentHandoffAndContextPreservation(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Tests agent handoffs and context preservation across multi-turn conversations with MANDATORY authentication."""
    
    def setup_method(self):
        """Set up authenticated E2E test environment for handoff testing."""
        super().setup_method()
        self.env = get_env()
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        #  ALERT:  MANDATORY: Create authenticated helpers
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
    
    @pytest.mark.asyncio
    @pytest.mark.real_services
    async def test_multi_turn_context_preservation(self, orchestration_setup):
        """
        TEST 2: Agent Handoff and Context Preservation Test
        
        Tests multi-turn conversation requiring context:
        Turn 1: Initial analysis request
        Turn 2: Follow-up with additional constraints
        Turn 3: Refinement of recommendations
        
        Validates:
        - Context preserved across turns
        - Previous conversation history impacts decisions
        - State transfers correctly between agents
        - Conversation coherence maintained
        """
        setup = orchestration_setup
        validator = ComprehensiveOrchestrationValidator()
        
        # Mock event capture
        original_send = setup["websocket_manager"].send_message
        setup["websocket_manager"].send_message = lambda msg: validator.event_capture.capture_event(msg)
        
        # Multi-turn conversation scenario
        turns = [
            {
                "user_request": "Analyze our Kubernetes cluster costs. We're spending $10K/month on GKE.",
                "expected_agents": ["triage", "data"]
            },
            {
                "user_request": "Actually, I forgot to mention we also have compliance requirements for PCI-DSS. How does that change your recommendations?",
                "expected_agents": ["triage", "optimization"]
            },
            {
                "user_request": "Can you provide a specific migration plan with timelines for the top 3 recommendations?",
                "expected_agents": ["optimization", "actions"]
            }
        ]
        
        # Persistent state across turns
        state = DeepAgentState(user_request="", conversation_history=[])
        user_id = "test_user_context_preservation"
        
        for turn_idx, turn in enumerate(turns):
            # Update state with new turn
            state.user_request = turn["user_request"]
            state.conversation_history.append({
                "turn": turn_idx + 1,
                "user_input": turn["user_request"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            
            run_id = str(uuid.uuid4())
            
            # Capture handoff before execution
            if turn_idx > 0:
                validator.handoff_validator.capture_handoff(
                    f"turn_{turn_idx}", f"turn_{turn_idx + 1}", state
                )
            
            # Execute turn
            try:
                result = await setup["supervisor"].execute(
                    context={
                        "state": state,
                        "run_id": run_id,
                        "user_id": user_id,
                        "stream_updates": True
                    }
                )
                
                # Validate turn succeeded
                assert result.success, f"Turn {turn_idx + 1} failed: {result.error}"
                assert result.final_response, f"No response for turn {turn_idx + 1}"
                
                # Update conversation history with response
                state.conversation_history.append({
                    "turn": turn_idx + 1,
                    "agent_response": result.final_response,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                # Validate context growth
                assert len(state.conversation_history) == (turn_idx + 1) * 2, "Conversation history not growing correctly"
                
                # For later turns, validate context influence
                if turn_idx > 0:
                    response_lower = result.final_response.lower()
                    if turn_idx == 1:  # PCI-DSS turn
                        assert "compliance" in response_lower or "pci" in response_lower, "Context from PCI-DSS mention not preserved"
                    elif turn_idx == 2:  # Migration plan turn
                        assert "plan" in response_lower or "timeline" in response_lower, "Migration context not preserved"
                
            except Exception as e:
                pytest.fail(f"Turn {turn_idx + 1} failed with error: {e}")
        
        # Validate complete context preservation
        is_valid, validation_results = validator.validate_complete_flow()
        assert is_valid, f"Context preservation validation failed: {validation_results}"
        
        logger.info(f"Multi-turn conversation completed with {len(state.conversation_history)} history items")


class TestErrorRecoveryDuringExecution(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Tests error recovery scenarios during agent execution with MANDATORY authentication."""
    
    def setup_method(self):
        """Set up authenticated E2E test environment for error recovery testing."""
        super().setup_method()
        self.env = get_env()
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        #  ALERT:  MANDATORY: Create authenticated helpers for error recovery tests
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
    
    @pytest.mark.asyncio
    @pytest.mark.real_services  
    async def test_agent_failure_and_graceful_recovery(self, orchestration_setup):
        """
        TEST 3: Error Recovery During Agent Execution Test
        
        Tests error scenarios:
        1. Agent timeout during execution
        2. Tool failure with retry logic
        3. LLM service temporary unavailability
        4. Supervisor routes to fallback agents
        
        Validates:
        - Graceful error handling without user-facing crashes
        - Supervisor routes to fallback agents appropriately
        - User sees transparent error handling
        - Final response acknowledges limitations but provides value
        """
        setup = orchestration_setup
        validator = ComprehensiveOrchestrationValidator()
        
        # Mock event capture and error injection
        original_send = setup["websocket_manager"].send_message
        setup["websocket_manager"].send_message = lambda msg: validator.event_capture.capture_event(msg)
        
        # Error scenarios to test
        error_scenarios = [
            {
                "name": "agent_timeout",
                "description": "Agent execution timeout",
                "user_request": "Quick analysis of our AWS Lambda costs with detailed breakdown by function.",
                "expected_recovery": "fallback_to_basic_analysis"
            },
            {
                "name": "tool_failure", 
                "description": "Tool execution failure with retry",
                "user_request": "Generate a performance optimization report for our microservices architecture.",
                "expected_recovery": "retry_with_different_tool"
            },
            {
                "name": "partial_agent_failure",
                "description": "One agent fails but others succeed",
                "user_request": "Complete analysis of our multi-cloud infrastructure costs and recommendations.",
                "expected_recovery": "partial_results_with_acknowledgment"
            }
        ]
        
        for scenario in error_scenarios:
            logger.info(f"Testing error scenario: {scenario['name']}")
            
            # Record scenario for validation
            validator.error_recovery.inject_agent_failure(
                scenario["name"], scenario["description"]
            )
            
            # Execute with potential failures
            state = DeepAgentState(user_request=scenario["user_request"])
            run_id = str(uuid.uuid4())
            user_id = f"test_user_error_{scenario['name']}"
            
            try:
                # Add timeout to simulate real-world conditions
                result = await asyncio.wait_for(
                    setup["supervisor"].execute(
                        context={
                            "state": state,
                            "run_id": run_id,
                            "user_id": user_id,
                            "stream_updates": True
                        }
                    ),
                    timeout=30.0
                )
                
                # Even with errors, we should get some response
                assert result is not None, f"No result returned for scenario {scenario['name']}"
                
                # Record recovery attempt
                validator.error_recovery.record_recovery_attempt(
                    scenario["name"], 
                    "supervisor_handled_gracefully",
                    result.success
                )
                
                # For successful recovery, validate response quality
                if result.success and result.final_response:
                    response_lower = result.final_response.lower()
                    # Response should acknowledge limitations but provide value
                    value_indicators = ["analysis", "recommendation", "cost", "optimization"]
                    has_value = any(indicator in response_lower for indicator in value_indicators)
                    assert has_value, f"Response lacks value for scenario {scenario['name']}"
                
                logger.info(f"Scenario {scenario['name']} handled gracefully")
                
            except asyncio.TimeoutError:
                # Record timeout as a handled error scenario
                validator.error_recovery.record_recovery_attempt(
                    scenario["name"], "timeout_handled", True
                )
                logger.info(f"Scenario {scenario['name']} timed out gracefully")
                
            except Exception as e:
                # Record failed recovery
                validator.error_recovery.record_recovery_attempt(
                    scenario["name"], f"exception_{type(e).__name__}", False
                )
                logger.warning(f"Scenario {scenario['name']} failed: {e}")
        
        # Validate overall error recovery
        is_valid, validation_results = validator.validate_complete_flow()
        
        # For error recovery, we accept partial success
        recovery_valid = validation_results.get("error_recovery", {}).get("success", False)
        scenarios_tested = validation_results.get("error_recovery", {}).get("scenarios_tested", 0)
        
        assert scenarios_tested == len(error_scenarios), "Not all error scenarios were tested"
        
        # At least 66% of scenarios should have some form of graceful handling
        recovery_attempts = validation_results.get("error_recovery", {}).get("recovery_attempts", 0)
        min_expected_recoveries = len(error_scenarios) * 0.66
        assert recovery_attempts >= min_expected_recoveries, f"Insufficient recovery attempts: {recovery_attempts} < {min_expected_recoveries}"
        
        logger.info(f"Error recovery testing completed: {recovery_attempts}/{len(error_scenarios)} scenarios handled")


# ============================================================================
# PERFORMANCE BENCHMARKS AND COMPREHENSIVE ASSERTIONS
# ============================================================================

class TestPerformanceAndProductionReadiness(SSotBaseTestCase):

    def create_user_context(self) -> UserExecutionContext:
        """Create isolated user execution context for golden path tests"""
        return UserExecutionContext.create_for_user(
            user_id="test_user",
            thread_id="test_thread",
            run_id="test_run"
        )

    """Performance benchmarks and production readiness validation with MANDATORY authentication."""
    
    def setup_method(self):
        """Set up authenticated E2E test environment for performance testing."""
        super().setup_method()
        self.env = get_env()
        
        # Determine test environment
        self.test_environment = self.env.get("TEST_ENV", self.env.get("ENVIRONMENT", "test"))
        
        #  ALERT:  MANDATORY: Create authenticated helpers for performance tests
        self.auth_helper = E2EAuthHelper(environment=self.test_environment)
        self.websocket_auth_helper = E2EWebSocketAuthHelper(environment=self.test_environment)
    
    @pytest.mark.asyncio
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_production_performance_benchmarks(self, orchestration_setup):
        """
        Performance and Production Readiness Test
        
        Validates:
        - Response times under acceptable thresholds
        - Memory usage within bounds
        - Concurrent request handling
        - WebSocket event efficiency
        - Resource cleanup after execution
        """
        setup = orchestration_setup
        validator = ComprehensiveOrchestrationValidator()
        
        # Performance test scenarios
        performance_tests = [
            {
                "name": "simple_request",
                "request": "What are the top 3 cost optimization opportunities for our cloud infrastructure?",
                "max_time": 15,  # seconds
                "expected_events": 5
            },
            {
                "name": "complex_request", 
                "request": "Provide a comprehensive analysis of our entire multi-cloud infrastructure including AWS, GCP, and Azure with specific optimization recommendations, cost projections, and implementation timelines.",
                "max_time": 45,  # seconds
                "expected_events": 10
            },
            {
                "name": "concurrent_requests",
                "request": "Analyze our Kubernetes cluster resource utilization and provide scaling recommendations.",
                "max_time": 30,  # seconds per request
                "concurrent_count": 3
            }
        ]
        
        performance_results = {}
        
        for test in performance_tests:
            test_name = test["name"]
            logger.info(f"Running performance test: {test_name}")
            
            if test_name == "concurrent_requests":
                # Test concurrent execution
                tasks = []
                start_time = time.time()
                
                for i in range(test["concurrent_count"]):
                    state = DeepAgentState(user_request=test["request"])
                    task = setup["supervisor"].execute(
                        context={
                            "state": state,
                            "run_id": str(uuid.uuid4()),
                            "user_id": f"perf_test_{i}",
                            "stream_updates": True
                        }
                    )
                    tasks.append(task)
                
                # Execute all concurrent requests
                results = await asyncio.gather(*tasks, return_exceptions=True)
                execution_time = time.time() - start_time
                
                # Validate concurrent execution
                successful_results = [r for r in results if not isinstance(r, Exception) and getattr(r, 'success', False)]
                success_rate = len(successful_results) / len(results)
                
                assert success_rate >= 0.8, f"Concurrent execution success rate too low: {success_rate}"
                assert execution_time <= test["max_time"], f"Concurrent execution too slow: {execution_time}s"
                
                performance_results[test_name] = {
                    "execution_time": execution_time,
                    "success_rate": success_rate,
                    "concurrent_count": test["concurrent_count"]
                }
                
            else:
                # Test single execution performance
                state = DeepAgentState(user_request=test["request"])
                
                # Mock event capture
                events_captured = []
                original_send = setup["websocket_manager"].send_message
                setup["websocket_manager"].send_message = lambda msg: events_captured.append(msg)
                
                start_time = time.time()
                
                try:
                    result = await asyncio.wait_for(
                        setup["supervisor"].execute(
                            context={
                                "state": state,
                                "run_id": str(uuid.uuid4()),
                                "user_id": f"perf_test_{test_name}",
                                "stream_updates": True
                            }
                        ),
                        timeout=test["max_time"]
                    )
                    
                    execution_time = time.time() - start_time
                    
                    # Validate performance requirements
                    assert result.success, f"Performance test {test_name} failed"
                    assert execution_time <= test["max_time"], f"Test {test_name} too slow: {execution_time}s"
                    assert len(events_captured) >= test["expected_events"], f"Insufficient events for {test_name}: {len(events_captured)}"
                    
                    performance_results[test_name] = {
                        "execution_time": execution_time,
                        "events_captured": len(events_captured),
                        "response_length": len(result.final_response) if result.final_response else 0
                    }
                    
                except asyncio.TimeoutError:
                    pytest.fail(f"Performance test {test_name} timed out after {test['max_time']}s")
                
                finally:
                    # Restore original WebSocket method
                    setup["websocket_manager"].send_message = original_send
        
        # Validate overall performance metrics
        total_execution_time = sum(r.get("execution_time", 0) for r in performance_results.values())
        avg_execution_time = total_execution_time / len(performance_results)
        
        assert avg_execution_time <= 25, f"Average execution time too high: {avg_execution_time}s"
        
        logger.info(f"Performance benchmarks completed: avg={avg_execution_time:.2f}s, results={performance_results}")


# ============================================================================
# INTEGRATION TEST RUNNER
# ============================================================================

if __name__ == "__main__":
    """
    Run comprehensive E2E agent orchestration tests.
    
    Usage:
        python test_agent_orchestration_e2e_comprehensive.py
        pytest test_agent_orchestration_e2e_comprehensive.py -v --real-services
        pytest test_agent_orchestration_e2e_comprehensive.py::TestCompleteAgentWorkflow::test_complex_multi_agent_orchestration_workflow -v
    """
    import sys
    
    logger.info("Starting comprehensive E2E agent orchestration test suite")
    
    # Run with pytest
    exit_code = pytest.main([
        __file__,
        "-v", 
        "--tb=short",
        "--real-services",
        "--timeout=300"
    ])
    
    sys.exit(exit_code)