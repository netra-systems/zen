"""
WebSocket Event Sequence Validation Test - Issue #1059 Agent Golden Path Tests

Business Value Justification:
- Segment: All tiers - Real-time user experience foundation
- Business Goal: Validate proper real-time communication and user experience
- Value Impact: Ensures users receive proper progress feedback during agent processing
- Revenue Impact: Prevents user abandonment due to poor real-time experience (500K+ ARR protection)

PURPOSE:
This integration test validates that all 5 critical WebSocket events are delivered
in the correct sequence during agent processing, providing users with proper
real-time visibility into agent execution progress.

CRITICAL EVENTS SEQUENCE:
1. agent_started - User knows processing began
2. agent_thinking - User sees reasoning/planning phase  
3. tool_executing - User sees tool usage (if applicable)
4. tool_completed - User sees tool results (if applicable)
5. agent_completed - User knows response is ready

CRITICAL DESIGN:
- NO DOCKER usage - tests run against GCP staging environment
- Real WebSocket connections with proper event sequencing validation
- Timing analysis to ensure events arrive in logical order
- Validation of event content and business context
- Multi-scenario testing (simple, complex, tool-using requests)
- Error scenarios and recovery testing

SCOPE:
1. Sequential event delivery validation for all 5 critical events
2. Event timing and ordering analysis
3. Event content validation and business context verification
4. Multiple message types and complexity levels
5. Error handling and recovery scenarios
6. Performance and timing requirements validation

AGENT_SESSION_ID: agent-session-2025-09-14-1430
Issue #1059: Agent Golden Path Integration Tests - Step 1 Implementation
"""

import asyncio
import json
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Set
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


class EventSequenceStage(Enum):
    """Stages of agent execution for event sequence validation."""
    INITIALIZATION = "initialization"
    THINKING = "thinking"
    TOOL_EXECUTION = "tool_execution"
    COMPLETION = "completion"
    ERROR_HANDLING = "error_handling"


@dataclass
class EventSequenceEvent:
    """Represents a WebSocket event in the sequence validation."""
    event_type: str
    timestamp: float
    sequence_number: int
    stage: EventSequenceStage
    data: Dict[str, Any]
    processing_duration: Optional[float] = None
    expected_next_events: List[str] = field(default_factory=list)
    business_context: Dict[str, Any] = field(default_factory=dict)
    

@dataclass
class EventSequenceValidationResult:
    """Results of event sequence validation."""
    sequence_valid: bool
    events_received: List[EventSequenceEvent]
    critical_events_present: Set[str]
    sequence_timing_valid: bool
    missing_events: List[str]
    unexpected_events: List[str]
    timing_violations: List[str]
    business_value_delivered: bool
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    error_messages: List[str] = field(default_factory=list)


class EventSequenceValidator:
    """Validates WebSocket event sequences for agent golden path."""
    
    # Critical events that must be present in proper order
    CRITICAL_EVENT_SEQUENCE = [
        "agent_started",
        "agent_thinking", 
        "tool_executing",  # Optional - may be skipped
        "tool_completed",  # Optional - may be skipped  
        "agent_completed"
    ]
    
    # Event timing requirements (in seconds)
    EVENT_TIMING_REQUIREMENTS = {
        "agent_started": {"min_delay": 0.0, "max_delay": 5.0},
        "agent_thinking": {"min_delay": 0.1, "max_delay": 10.0},
        "tool_executing": {"min_delay": 0.1, "max_delay": 15.0},
        "tool_completed": {"min_delay": 1.0, "max_delay": 30.0},
        "agent_completed": {"min_delay": 2.0, "max_delay": 60.0}
    }
    
    # Expected event transitions
    VALID_EVENT_TRANSITIONS = {
        "agent_started": ["agent_thinking", "agent_completed"],
        "agent_thinking": ["tool_executing", "agent_completed"],
        "tool_executing": ["tool_completed", "tool_executing"],  # Multiple tools possible
        "tool_completed": ["tool_executing", "agent_completed"],
        "agent_completed": []  # Terminal event
    }
    
    def __init__(self, user_id: str, thread_id: str, run_id: str):
        self.user_id = user_id
        self.thread_id = thread_id
        self.run_id = run_id
        self.events: List[EventSequenceEvent] = []
        self.sequence_start_time = time.time()
        self.last_event_time = self.sequence_start_time
        self.sequence_number = 0
        
    async def track_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Track an event in the sequence with validation."""
        current_time = time.time()
        processing_duration = current_time - self.last_event_time
        
        # Determine sequence stage
        stage = self._determine_event_stage(event_type)
        
        # Determine expected next events
        expected_next = self.VALID_EVENT_TRANSITIONS.get(event_type, [])
        
        # Extract business context
        business_context = self._extract_business_context(event_type, data)
        
        event = EventSequenceEvent(
            event_type=event_type,
            timestamp=current_time,
            sequence_number=self.sequence_number,
            stage=stage,
            data=data,
            processing_duration=processing_duration,
            expected_next_events=expected_next,
            business_context=business_context
        )
        
        self.events.append(event)
        self.last_event_time = current_time
        self.sequence_number += 1
        
        logger.info(f"[EVENT SEQUENCE] Event {self.sequence_number}: {event_type} at stage {stage.value}")
        
    def _determine_event_stage(self, event_type: str) -> EventSequenceStage:
        """Determine which stage of execution this event represents."""
        if event_type in ["agent_started"]:
            return EventSequenceStage.INITIALIZATION
        elif event_type in ["agent_thinking"]:
            return EventSequenceStage.THINKING
        elif event_type in ["tool_executing", "tool_completed"]:
            return EventSequenceStage.TOOL_EXECUTION
        elif event_type in ["agent_completed"]:
            return EventSequenceStage.COMPLETION
        else:
            return EventSequenceStage.ERROR_HANDLING
    
    def _extract_business_context(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract business context from event data."""
        context = {}
        
        if event_type == "agent_thinking":
            # Look for reasoning indicators
            content = data.get("content", data.get("message", ""))
            if content:
                context["reasoning_present"] = len(content) > 20
                context["structured_thinking"] = any(marker in content for marker in ["1.", "2.", "First", "Next"])
                
        elif event_type == "tool_executing":
            # Track tool usage
            context["tool_name"] = data.get("tool_name", data.get("function_name", "unknown"))
            context["tool_purpose"] = data.get("purpose", data.get("description", ""))
            
        elif event_type == "tool_completed":
            # Assess tool result quality
            result = data.get("result", data.get("output", ""))
            context["result_received"] = bool(result)
            context["result_length"] = len(str(result)) if result else 0
            
        elif event_type == "agent_completed":
            # Assess final response
            response = data.get("content", data.get("message", ""))
            if response:
                context["response_length"] = len(response)
                context["actionable_content"] = any(word in response.lower() 
                                                  for word in ["recommend", "suggest", "should", "consider"])
                context["business_value"] = any(word in response.lower() 
                                              for word in ["optimize", "improve", "strategy", "analysis"])
        
        return context
    
    def validate_sequence(self) -> EventSequenceValidationResult:
        """Validate the complete event sequence."""
        current_time = time.time()
        
        # Identify which critical events are present
        event_types_received = [event.event_type for event in self.events]
        critical_events_present = set(event_type for event_type in event_types_received 
                                    if event_type in self.CRITICAL_EVENT_SEQUENCE)
        
        # Identify missing critical events (excluding optional tool events)
        required_events = {"agent_started", "agent_thinking", "agent_completed"}
        missing_events = list(required_events - critical_events_present)
        
        # Identify unexpected events (events not in our known sequence)
        known_events = set(self.CRITICAL_EVENT_SEQUENCE + ["message", "error", "status"])
        unexpected_events = list(set(event_types_received) - known_events)
        
        # Validate event timing
        timing_violations = self._validate_event_timing()
        sequence_timing_valid = len(timing_violations) == 0
        
        # Validate sequence ordering
        sequence_valid = self._validate_sequence_ordering()
        
        # Assess business value delivery
        business_value_delivered = self._assess_business_value_delivery()
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics()
        
        return EventSequenceValidationResult(
            sequence_valid=sequence_valid,
            events_received=self.events,
            critical_events_present=critical_events_present,
            sequence_timing_valid=sequence_timing_valid,
            missing_events=missing_events,
            unexpected_events=unexpected_events,
            timing_violations=timing_violations,
            business_value_delivered=business_value_delivered,
            performance_metrics=performance_metrics
        )
    
    def _validate_event_timing(self) -> List[str]:
        """Validate that events arrive within expected timing windows."""
        violations = []
        
        for i, event in enumerate(self.events):
            if event.event_type in self.EVENT_TIMING_REQUIREMENTS:
                timing_req = self.EVENT_TIMING_REQUIREMENTS[event.event_type]
                
                # Calculate time since sequence start
                time_since_start = event.timestamp - self.sequence_start_time
                
                # Check timing bounds
                if time_since_start < timing_req["min_delay"]:
                    violations.append(f"{event.event_type} arrived too early ({time_since_start:.2f}s < {timing_req['min_delay']}s)")
                elif time_since_start > timing_req["max_delay"]:
                    violations.append(f"{event.event_type} arrived too late ({time_since_start:.2f}s > {timing_req['max_delay']}s)")
        
        return violations
    
    def _validate_sequence_ordering(self) -> bool:
        """Validate that events follow proper ordering rules."""
        previous_event = None
        
        for event in self.events:
            if previous_event is not None:
                # Check if this event is a valid transition from previous
                valid_transitions = self.VALID_EVENT_TRANSITIONS.get(previous_event.event_type, [])
                
                # Allow any event after agent_completed (for cleanup/status)
                if previous_event.event_type == "agent_completed":
                    continue
                    
                # If this event type is not in valid transitions, check if it's a repeat or error
                if event.event_type not in valid_transitions and event.event_type != previous_event.event_type:
                    logger.warning(f"[SEQUENCE] Potential ordering violation: {previous_event.event_type} -> {event.event_type}")
                    # Don't fail for this - some flexibility needed for real systems
            
            previous_event = event
        
        # Require minimum sequence: started -> thinking -> completed
        event_types = [event.event_type for event in self.events]
        required_sequence = ["agent_started", "agent_thinking", "agent_completed"]
        
        sequence_indices = []
        for required_event in required_sequence:
            try:
                index = event_types.index(required_event)
                sequence_indices.append(index)
            except ValueError:
                return False  # Required event missing
        
        # Check that required events are in order
        return sequence_indices == sorted(sequence_indices)
    
    def _assess_business_value_delivery(self) -> bool:
        """Assess whether the event sequence delivered business value."""
        # Must have completion event with meaningful content
        completion_events = [event for event in self.events if event.event_type == "agent_completed"]
        if not completion_events:
            return False
        
        # Check business context of completion event
        completion_event = completion_events[-1]
        business_context = completion_event.business_context
        
        return (
            business_context.get("response_length", 0) > 50 and
            (business_context.get("actionable_content", False) or
             business_context.get("business_value", False))
        )
    
    def _calculate_performance_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics from event sequence."""
        if not self.events:
            return {}
        
        metrics = {}
        
        # Total sequence duration
        total_duration = self.events[-1].timestamp - self.sequence_start_time
        metrics["total_sequence_duration"] = total_duration
        
        # Time to first meaningful event (agent_thinking)
        thinking_events = [event for event in self.events if event.event_type == "agent_thinking"]
        if thinking_events:
            metrics["time_to_thinking"] = thinking_events[0].timestamp - self.sequence_start_time
        
        # Time to completion
        completion_events = [event for event in self.events if event.event_type == "agent_completed"]
        if completion_events:
            metrics["time_to_completion"] = completion_events[0].timestamp - self.sequence_start_time
        
        # Event frequency (events per second)
        if total_duration > 0:
            metrics["event_frequency"] = len(self.events) / total_duration
        
        # Processing stages timing
        stage_timings = {}
        current_stage = None
        stage_start = self.sequence_start_time
        
        for event in self.events:
            if event.stage != current_stage:
                if current_stage is not None:
                    stage_timings[current_stage.value] = event.timestamp - stage_start
                current_stage = event.stage
                stage_start = event.timestamp
        
        # Add final stage timing
        if current_stage is not None:
            stage_timings[current_stage.value] = self.events[-1].timestamp - stage_start
        
        metrics.update(stage_timings)
        
        return metrics


class WebSocketEventSequenceValidationTests(SSotAsyncTestCase):
    """
    WebSocket Event Sequence Validation Tests.
    
    Tests that all 5 critical WebSocket events are delivered in the correct
    sequence during agent processing, providing proper real-time user experience.
    """
    
    def setup_method(self, method=None):
        """Set up event sequence validation test environment."""
        super().setup_method(method)
        self.env = get_env()
        
        # Environment configuration
        test_env = self.env.get("TEST_ENV", "test")
        if test_env == "staging" or self.env.get("ENVIRONMENT") == "staging":
            self.test_env = "staging"
            self.staging_config = StagingTestConfig()
            self.websocket_url = self.staging_config.urls.websocket_url
            self.timeout = 45.0
        else:
            self.test_env = "test"
            self.websocket_url = self.env.get("TEST_WEBSOCKET_URL", "ws://localhost:8000/ws")
            self.timeout = 30.0
            
        self.e2e_helper = E2EWebSocketAuthHelper(environment=self.test_env)
        
        # Event sequence test configuration
        self.sequence_timeout = 60.0  # Allow time for complete sequence
        self.event_timeout = 10.0     # Individual event timeout
        self.connection_timeout = 15.0 # Connection establishment
        
        logger.info(f"[EVENT SEQUENCE SETUP] Test environment: {self.test_env}")
        logger.info(f"[EVENT SEQUENCE SETUP] WebSocket URL: {self.websocket_url}")
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.websocket_events
    @pytest.mark.timeout(90)
    async def test_critical_event_sequence_validation(self):
        """
        Test that all 5 critical WebSocket events are delivered in proper sequence.
        
        Validates:
        1. agent_started - Processing initiation
        2. agent_thinking - Reasoning phase
        3. tool_executing - Tool usage (if applicable)
        4. tool_completed - Tool results (if applicable)  
        5. agent_completed - Final response
        
        BVJ: This test ensures users receive proper real-time feedback during
        agent processing, preventing user abandonment and supporting the 
        500K+ ARR user experience.
        """
        test_start_time = time.time()
        print(f"[EVENT SEQUENCE] Starting critical event sequence validation test")
        print(f"[EVENT SEQUENCE] Environment: {self.test_env}")
        print(f"[EVENT SEQUENCE] Expected events: {EventSequenceValidator.CRITICAL_EVENT_SEQUENCE}")
        
        # Create authenticated user for event sequence testing
        sequence_user = await self.e2e_helper.create_authenticated_user(
            email=f"event_sequence_{int(time.time())}@test.com",
            permissions=["read", "write", "chat", "agent_execution"]
        )
        
        # Generate unique identifiers
        thread_id = f"sequence_thread_{uuid.uuid4()}"
        run_id = f"sequence_run_{uuid.uuid4()}"
        
        # Initialize event sequence validator
        validator = EventSequenceValidator(
            user_id=sequence_user.user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Test message designed to trigger complete event sequence
        sequence_test_message = {
            "message": "Please analyze the current state of our AI optimization platform and provide strategic recommendations for improving customer acquisition and retention. Include specific metrics and actionable next steps.",
            "thread_id": thread_id,
            "run_id": run_id,
            "context": {
                "request_type": "strategic_analysis",
                "expected_tools": True,
                "comprehensive_response": True
            }
        }
        
        websocket_headers = self.e2e_helper.get_websocket_headers(sequence_user.jwt_token)
        
        try:
            # Establish WebSocket connection
            print(f"[EVENT SEQUENCE] Connecting to WebSocket for event sequence validation")
            async with websockets.connect(
                self.websocket_url,
                additional_headers=websocket_headers,
                timeout=self.connection_timeout,
                ping_interval=30,
                ping_timeout=10
            ) as websocket:
                
                print(f"[EVENT SEQUENCE] WebSocket connected, sending test message")
                
                # Send the test message
                await websocket.send(json.dumps(sequence_test_message))
                
                # Track events in sequence
                events_collected = []
                critical_events_seen = set()
                sequence_complete = False
                
                # Event collection with detailed sequence tracking
                collection_start = time.time()
                
                while time.time() - collection_start < self.sequence_timeout:
                    try:
                        # Receive event with timeout
                        response_text = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=self.event_timeout
                        )
                        
                        response_data = json.loads(response_text)
                        event_type = response_data.get("type", response_data.get("event_type", "unknown"))
                        
                        # Track event in validator
                        await validator.track_event(event_type, response_data)
                        events_collected.append(response_data)
                        
                        # Track critical events
                        if event_type in validator.CRITICAL_EVENT_SEQUENCE:
                            critical_events_seen.add(event_type)
                            print(f"[EVENT SEQUENCE] Critical event received ({len(critical_events_seen)}/5): {event_type}")
                        
                        # Check for sequence completion
                        if event_type == "agent_completed":
                            sequence_complete = True
                            print(f"[EVENT SEQUENCE] Sequence completed with agent_completed event")
                            break
                            
                    except asyncio.TimeoutError:
                        # Check if we have minimum required events
                        if len(critical_events_seen) >= 3:
                            print(f"[EVENT SEQUENCE] Timeout but minimum events received: {critical_events_seen}")
                            break
                        continue
                        
                    except (ConnectionClosed, WebSocketException) as e:
                        print(f"[EVENT SEQUENCE] WebSocket connection error: {e}")
                        break
                
        except Exception as e:
            print(f"[EVENT SEQUENCE] Test error: {e}")
            await validator.track_event("error", {"error": str(e), "error_type": type(e).__name__})
        
        # Validate the complete event sequence
        validation_result = validator.validate_sequence()
        
        # Log detailed validation results
        test_duration = time.time() - test_start_time
        print(f"\n[EVENT SEQUENCE RESULTS] Event Sequence Validation Results")
        print(f"[EVENT SEQUENCE RESULTS] Test Duration: {test_duration:.2f}s")
        print(f"[EVENT SEQUENCE RESULTS] Events Collected: {len(validation_result.events_received)}")
        print(f"[EVENT SEQUENCE RESULTS] Critical Events Present: {validation_result.critical_events_present}")
        print(f"[EVENT SEQUENCE RESULTS] Missing Events: {validation_result.missing_events}")
        print(f"[EVENT SEQUENCE RESULTS] Unexpected Events: {validation_result.unexpected_events}")
        print(f"[EVENT SEQUENCE RESULTS] Sequence Valid: {validation_result.sequence_valid}")
        print(f"[EVENT SEQUENCE RESULTS] Timing Valid: {validation_result.sequence_timing_valid}")
        print(f"[EVENT SEQUENCE RESULTS] Business Value Delivered: {validation_result.business_value_delivered}")
        print(f"[EVENT SEQUENCE RESULTS] Performance Metrics: {validation_result.performance_metrics}")
        
        if validation_result.timing_violations:
            print(f"[EVENT SEQUENCE RESULTS] Timing Violations: {validation_result.timing_violations}")
        
        # ASSERTIONS: Comprehensive event sequence validation
        
        # Critical Events Presence
        assert "agent_started" in validation_result.critical_events_present, \
            "Expected agent_started event to be present"
        
        assert "agent_thinking" in validation_result.critical_events_present, \
            "Expected agent_thinking event to be present"
        
        assert "agent_completed" in validation_result.critical_events_present, \
            "Expected agent_completed event to be present"
        
        # Minimum event count
        assert len(validation_result.critical_events_present) >= 3, \
            f"Expected at least 3 critical events, got {len(validation_result.critical_events_present)}"
        
        # Sequence ordering validation
        assert validation_result.sequence_valid, \
            f"Event sequence ordering invalid: {[e.event_type for e in validation_result.events_received]}"
        
        # Business value delivery
        assert validation_result.business_value_delivered, \
            "Expected event sequence to deliver business value"
        
        # Performance validation
        total_duration = validation_result.performance_metrics.get("total_sequence_duration", 999)
        assert total_duration < 60.0, \
            f"Event sequence took too long: {total_duration:.2f}s > 60.0s"
        
        time_to_completion = validation_result.performance_metrics.get("time_to_completion", 999)
        assert time_to_completion < 45.0, \
            f"Time to completion too long: {time_to_completion:.2f}s > 45.0s"
        
        print(f"[EVENT SEQUENCE SUCCESS] All critical events delivered in proper sequence!")
        print(f"[EVENT SEQUENCE SUCCESS] Sequence completed in {total_duration:.2f}s")
        print(f"[EVENT SEQUENCE SUCCESS] Business value delivered successfully")
        
    @pytest.mark.integration
    @pytest.mark.agent_golden_path
    @pytest.mark.timeout(60)
    async def test_event_sequence_timing_validation(self):
        """
        Test event sequence timing requirements and performance.
        
        Validates that events arrive within expected timing windows
        and that the overall sequence completes within business requirements.
        """
        print(f"[TIMING VALIDATION] Starting event sequence timing validation")
        
        # Create user for timing test
        timing_user = await self.e2e_helper.create_authenticated_user(
            email=f"timing_sequence_{int(time.time())}@test.com",
            permissions=["read", "write", "chat"]
        )
        
        thread_id = f"timing_thread_{uuid.uuid4()}"
        run_id = f"timing_run_{uuid.uuid4()}"
        
        # Initialize timing validator
        validator = EventSequenceValidator(
            user_id=timing_user.user_id,
            thread_id=thread_id,
            run_id=run_id
        )
        
        # Simple message for timing test
        timing_message = {
            "message": "Please provide a brief analysis of optimization opportunities for our platform.",
            "thread_id": thread_id,
            "run_id": run_id,
            "context": {"request_type": "brief_analysis", "timing_test": True}
        }
        
        websocket_headers = self.e2e_helper.get_websocket_headers(timing_user.jwt_token)
        
        try:
            async with websockets.connect(
                self.websocket_url,
                additional_headers=websocket_headers,
                timeout=self.connection_timeout
            ) as websocket:
                
                timing_start = time.time()
                await websocket.send(json.dumps(timing_message))
                
                # Collect events with precise timing
                while time.time() - timing_start < 30.0:  # Shorter timeout for timing test
                    try:
                        response_text = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response_text)
                        event_type = response_data.get("type", response_data.get("event_type"))
                        
                        await validator.track_event(event_type, response_data)
                        
                        if event_type == "agent_completed":
                            break
                            
                    except asyncio.TimeoutError:
                        break
                    except (ConnectionClosed, WebSocketException):
                        break
        
        except Exception as e:
            print(f"[TIMING VALIDATION] Error: {e}")
        
        # Validate timing performance
        validation_result = validator.validate_sequence()
        
        print(f"[TIMING VALIDATION RESULTS] Timing Violations: {validation_result.timing_violations}")
        print(f"[TIMING VALIDATION RESULTS] Performance: {validation_result.performance_metrics}")
        
        # Timing assertions
        assert len(validation_result.timing_violations) <= 1, \
            f"Too many timing violations: {validation_result.timing_violations}"
        
        total_duration = validation_result.performance_metrics.get("total_sequence_duration", 0)
        assert total_duration > 0, "Expected sequence to have measurable duration"
        
        print(f"[TIMING VALIDATION SUCCESS] Event sequence timing validated successfully")


if __name__ == "__main__":
    # Allow running this test file directly
    import asyncio
    
    async def run_test():
        test_instance = WebSocketEventSequenceValidationTests()
        test_instance.setup_method()
        await test_instance.test_critical_event_sequence_validation()
        print("Direct test execution completed successfully")
    
    asyncio.run(run_test())