"""
Test WebSocket Event Validation Logic for Golden Path

CRITICAL UNIT TEST: This validates the 5 mission-critical WebSocket events that
enable the $500K+ ARR chat experience and business value delivery.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Ensure critical WebSocket events are delivered for user experience
- Value Impact: Missing events = broken chat experience = revenue loss
- Strategic Impact: Core platform reliability for user engagement and conversion

GOLDEN PATH CRITICAL ISSUE #4: Missing WebSocket Events
This test validates the event validation logic for:
1. agent_started - User sees AI began work
2. agent_thinking - Real-time reasoning updates
3. tool_executing - Tool usage transparency  
4. tool_completed - Tool results display
5. agent_completed - Final results ready
"""

import pytest
import json
import time
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from dataclasses import dataclass, field
from unittest.mock import Mock

# SSOT imports following CLAUDE.md absolute import rules
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from shared.types.core_types import UserID, ThreadID, RunID, WebSocketID
from shared.id_generation.unified_id_generator import UnifiedIdGenerator
from netra_backend.app.core.unified_id_manager import generate_user_id, generate_thread_id, UnifiedIDManager


class WebSocketEventType(Enum):
    """Critical WebSocket event types for Golden Path."""
    AGENT_STARTED = "agent_started"
    AGENT_THINKING = "agent_thinking"
    TOOL_EXECUTING = "tool_executing"
    TOOL_COMPLETED = "tool_completed"
    AGENT_COMPLETED = "agent_completed"
    
    # Additional system events
    CONNECTION_READY = "connection_ready"
    ERROR = "error"
    SYSTEM_STATUS = "system_status"


@dataclass
class WebSocketEvent:
    """WebSocket event structure for validation."""
    event_type: WebSocketEventType
    user_id: UserID
    thread_id: ThreadID
    run_id: RunID
    timestamp: float = field(default_factory=time.time)
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    event_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for transmission."""
        return {
            "type": self.event_type.value,
            "user_id": str(self.user_id),
            "thread_id": str(self.thread_id),
            "run_id": str(self.run_id),
            "timestamp": self.timestamp,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "data": self.data or {},
            "event_id": self.event_id
        }
    
    @classmethod
    def from_dict(cls, event_dict: Dict[str, Any]) -> 'WebSocketEvent':
        """Create event from dictionary."""
        return cls(
            event_type=WebSocketEventType(event_dict["type"]),
            user_id=UserID(event_dict["user_id"]),
            thread_id=ThreadID(event_dict["thread_id"]),
            run_id=RunID(event_dict["run_id"]),
            timestamp=event_dict.get("timestamp", time.time()),
            agent_name=event_dict.get("agent_name"),
            tool_name=event_dict.get("tool_name"),
            data=event_dict.get("data", {}),
            event_id=event_dict.get("event_id")
        )


class WebSocketEventValidator:
    """
    Core logic for validating WebSocket events in the Golden Path.
    This is the system under test - extracted from production code for unit testing.
    """
    
    def __init__(self):
        self.required_events = self._get_required_events()
        self.event_order_rules = self._get_event_order_rules()
        self.event_content_rules = self._get_event_content_rules()
        
    def _get_required_events(self) -> Set[WebSocketEventType]:
        """Get the 5 mission-critical events required for business value."""
        return {
            WebSocketEventType.AGENT_STARTED,
            WebSocketEventType.AGENT_THINKING,
            WebSocketEventType.TOOL_EXECUTING,
            WebSocketEventType.TOOL_COMPLETED,
            WebSocketEventType.AGENT_COMPLETED
        }
    
    def _get_event_order_rules(self) -> Dict[WebSocketEventType, List[WebSocketEventType]]:
        """Get event ordering rules (what must come before what)."""
        return {
            WebSocketEventType.AGENT_STARTED: [],  # Can be first
            WebSocketEventType.AGENT_THINKING: [WebSocketEventType.AGENT_STARTED],
            WebSocketEventType.TOOL_EXECUTING: [
                WebSocketEventType.AGENT_STARTED, 
                WebSocketEventType.AGENT_THINKING
            ],
            WebSocketEventType.TOOL_COMPLETED: [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING, 
                WebSocketEventType.TOOL_EXECUTING
            ],
            WebSocketEventType.AGENT_COMPLETED: [
                WebSocketEventType.AGENT_STARTED,
                WebSocketEventType.AGENT_THINKING
            ]
        }
    
    def _get_event_content_rules(self) -> Dict[WebSocketEventType, Dict[str, Any]]:
        """Get content validation rules for each event type."""
        return {
            WebSocketEventType.AGENT_STARTED: {
                "required_fields": ["agent_name"],
                "optional_fields": ["user_message", "context"],
                "data_type": dict
            },
            WebSocketEventType.AGENT_THINKING: {
                "required_fields": ["agent_name"],
                "optional_fields": ["reasoning", "next_steps"],
                "data_type": dict
            },
            WebSocketEventType.TOOL_EXECUTING: {
                "required_fields": ["agent_name", "tool_name"],
                "optional_fields": ["tool_params", "expected_duration"],
                "data_type": dict
            },
            WebSocketEventType.TOOL_COMPLETED: {
                "required_fields": ["agent_name", "tool_name"],
                "optional_fields": ["tool_result", "execution_time"],
                "data_type": dict
            },
            WebSocketEventType.AGENT_COMPLETED: {
                "required_fields": ["agent_name"],
                "optional_fields": ["final_response", "execution_summary"],
                "data_type": dict
            }
        }
    
    def validate_event_sequence(self, events: List[WebSocketEvent]) -> Dict[str, Any]:
        """
        Validate a sequence of WebSocket events for completeness and order.
        
        Returns:
            Dict with validation results
        """
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "missing_events": [],
            "order_violations": [],
            "content_errors": [],
            "event_count": len(events),
            "coverage_percentage": 0.0
        }
        
        if not events:
            validation_result["valid"] = False
            validation_result["errors"].append("No events provided")
            return validation_result
        
        # Check for required events
        event_types_received = {event.event_type for event in events}
        missing_events = self.required_events - event_types_received
        
        if missing_events:
            validation_result["missing_events"] = list(missing_events)
            validation_result["errors"].extend([
                f"Missing critical event: {event.value}" for event in missing_events
            ])
            validation_result["valid"] = False
        
        # Calculate coverage percentage
        validation_result["coverage_percentage"] = (
            len(event_types_received & self.required_events) / len(self.required_events)
        ) * 100
        
        # Check event order
        order_violations = self._check_event_order(events)
        if order_violations:
            validation_result["order_violations"] = order_violations
            validation_result["errors"].extend(order_violations)
            validation_result["valid"] = False
        
        # Check event content
        content_errors = self._check_event_content(events)
        if content_errors:
            validation_result["content_errors"] = content_errors
            validation_result["errors"].extend(content_errors)
            validation_result["valid"] = False
        
        # Performance warnings
        if len(events) > 20:
            validation_result["warnings"].append(
                f"High event count ({len(events)}) may indicate performance issues"
            )
        
        return validation_result
    
    def _check_event_order(self, events: List[WebSocketEvent]) -> List[str]:
        """Check if events are in proper order."""
        violations = []
        
        # Group events by agent to check order within each agent's lifecycle
        agent_events = {}
        for event in events:
            agent_name = event.agent_name or "unknown"
            if agent_name not in agent_events:
                agent_events[agent_name] = []
            agent_events[agent_name].append(event)
        
        # Check order for each agent
        for agent_name, agent_event_list in agent_events.items():
            # Sort by timestamp
            agent_event_list.sort(key=lambda x: x.timestamp)
            
            for i, event in enumerate(agent_event_list):
                # Check if prerequisites are met
                prerequisites = self.event_order_rules.get(event.event_type, [])
                previous_events = agent_event_list[:i]
                previous_types = {e.event_type for e in previous_events}
                
                missing_prerequisites = set(prerequisites) - previous_types
                if missing_prerequisites:
                    violations.append(
                        f"Agent {agent_name}: {event.event_type.value} missing prerequisites: "
                        f"{[p.value for p in missing_prerequisites]}"
                    )
        
        return violations
    
    def _check_event_content(self, events: List[WebSocketEvent]) -> List[str]:
        """Check event content against validation rules."""
        content_errors = []
        
        for event in events:
            if event.event_type in self.event_content_rules:
                rules = self.event_content_rules[event.event_type]
                errors = self._validate_event_content(event, rules)
                content_errors.extend(errors)
        
        return content_errors
    
    def _validate_event_content(self, event: WebSocketEvent, rules: Dict[str, Any]) -> List[str]:
        """Validate individual event content."""
        errors = []
        
        # Check data type
        if event.data is None:
            event.data = {}
        
        expected_type = rules.get("data_type", dict)
        if not isinstance(event.data, expected_type):
            errors.append(
                f"Event {event.event_type.value}: data should be {expected_type.__name__}, "
                f"got {type(event.data).__name__}"
            )
            return errors  # Skip further validation if type is wrong
        
        # Check required fields
        required_fields = rules.get("required_fields", [])
        
        # Check in event data
        for field in required_fields:
            if field == "agent_name":
                if not event.agent_name:
                    errors.append(f"Event {event.event_type.value}: missing agent_name")
            elif field == "tool_name":
                if not event.tool_name:
                    errors.append(f"Event {event.event_type.value}: missing tool_name")
            elif field not in event.data:
                errors.append(f"Event {event.event_type.value}: missing required field '{field}'")
        
        return errors
    
    def validate_single_event(self, event: WebSocketEvent) -> Dict[str, Any]:
        """Validate a single WebSocket event."""
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "event_type": event.event_type.value,
            "is_critical": event.event_type in self.required_events
        }
        
        # Content validation
        if event.event_type in self.event_content_rules:
            rules = self.event_content_rules[event.event_type]
            content_errors = self._validate_event_content(event, rules)
            
            if content_errors:
                validation_result["errors"].extend(content_errors)
                validation_result["valid"] = False
        
        # Timestamp validation
        current_time = time.time()
        if event.timestamp > current_time + 60:  # Future event beyond reasonable clock skew
            validation_result["warnings"].append("Event timestamp is in the future")
        elif event.timestamp < current_time - 3600:  # Event older than 1 hour
            validation_result["warnings"].append("Event timestamp is very old")
        
        return validation_result
    
    def get_missing_events_for_completion(
        self, 
        received_events: List[WebSocketEvent]
    ) -> List[WebSocketEventType]:
        """Get list of events still needed for complete Golden Path."""
        received_types = {event.event_type for event in received_events}
        missing = self.required_events - received_types
        return list(missing)
    
    def calculate_event_quality_score(self, events: List[WebSocketEvent]) -> Dict[str, Any]:
        """Calculate overall quality score for event sequence."""
        if not events:
            return {"score": 0.0, "grade": "F", "details": "No events"}
        
        validation = self.validate_event_sequence(events)
        
        # Base score from coverage
        coverage_score = validation["coverage_percentage"]
        
        # Deduct for violations
        order_penalty = len(validation["order_violations"]) * 15
        content_penalty = len(validation["content_errors"]) * 10
        missing_penalty = len(validation["missing_events"]) * 20
        
        final_score = max(0, coverage_score - order_penalty - content_penalty - missing_penalty)
        
        # Grade assignment
        if final_score >= 95:
            grade = "A+"
        elif final_score >= 90:
            grade = "A"
        elif final_score >= 80:
            grade = "B"
        elif final_score >= 70:
            grade = "C"
        elif final_score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        return {
            "score": final_score,
            "grade": grade,
            "coverage": validation["coverage_percentage"],
            "penalties": {
                "order": order_penalty,
                "content": content_penalty,
                "missing": missing_penalty
            },
            "details": validation
        }


class TestWebSocketEventValidator(SSotAsyncTestCase):
    """Test WebSocket event validation logic."""
    
    def setup_method(self, method=None):
        """Setup test with event validator."""
        super().setup_method(method)
        self.event_validator = WebSocketEventValidator()
        self.id_generator = UnifiedIdGenerator()
        
        # Test context
        self.user_id = UserID(generate_user_id())
        self.thread_id = ThreadID(generate_thread_id())
        thread_id_str = str(self.thread_id)
        self.run_id = RunID(UnifiedIDManager.generate_run_id(thread_id_str))
        
        # Test metrics
        self.record_metric("test_category", "unit")
        self.record_metric("golden_path_component", "websocket_event_validation")
        
    def _create_test_event(
        self, 
        event_type: WebSocketEventType,
        agent_name: str = "test_agent",
        tool_name: str = None,
        data: Dict[str, Any] = None,
        timestamp: float = None
    ) -> WebSocketEvent:
        """Helper to create test events."""
        return WebSocketEvent(
            event_type=event_type,
            user_id=self.user_id,
            thread_id=self.thread_id,
            run_id=self.run_id,
            agent_name=agent_name,
            tool_name=tool_name,
            data=data or {},
            timestamp=timestamp or time.time()
        )
    
    @pytest.mark.unit
    def test_complete_golden_path_event_sequence_validation(self):
        """Test validation of complete Golden Path event sequence."""
        # Create complete event sequence
        base_time = time.time()
        events = [
            self._create_test_event(
                WebSocketEventType.AGENT_STARTED, 
                agent_name="data_agent",
                data={"message": "Starting data analysis"},
                timestamp=base_time
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_THINKING, 
                agent_name="data_agent",
                data={"reasoning": "Analyzing cost data"},
                timestamp=base_time + 1
            ),
            self._create_test_event(
                WebSocketEventType.TOOL_EXECUTING, 
                agent_name="data_agent",
                tool_name="cost_analyzer",
                data={"tool_params": {"period": "30d"}},
                timestamp=base_time + 2
            ),
            self._create_test_event(
                WebSocketEventType.TOOL_COMPLETED, 
                agent_name="data_agent",
                tool_name="cost_analyzer",
                data={"tool_result": {"total_cost": 1000}},
                timestamp=base_time + 3
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_COMPLETED, 
                agent_name="data_agent",
                data={"final_response": "Analysis complete"},
                timestamp=base_time + 4
            )
        ]
        
        result = self.event_validator.validate_event_sequence(events)
        
        # Assertions
        assert result["valid"] is True, f"Complete sequence should be valid: {result}"
        assert len(result["errors"]) == 0, f"Should have no errors: {result['errors']}"
        assert len(result["missing_events"]) == 0, f"Should have no missing events: {result['missing_events']}"
        assert result["coverage_percentage"] == 100.0, f"Should have 100% coverage: {result['coverage_percentage']}"
        assert len(result["order_violations"]) == 0, f"Should have no order violations: {result['order_violations']}"
        
        self.record_metric("complete_sequence_validation_passed", True)
        self.record_metric("coverage_percentage", result["coverage_percentage"])
        
    @pytest.mark.unit
    def test_missing_critical_events_detection(self):
        """Test detection of missing critical WebSocket events."""
        # Create incomplete event sequence (missing tool events)
        incomplete_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED, agent_name="data_agent"),
            self._create_test_event(WebSocketEventType.AGENT_THINKING, agent_name="data_agent"),
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED, agent_name="data_agent")
        ]
        
        result = self.event_validator.validate_event_sequence(incomplete_events)
        
        # Assertions
        assert result["valid"] is False, "Incomplete sequence should be invalid"
        assert len(result["missing_events"]) == 2, f"Should detect 2 missing events: {result['missing_events']}"
        assert WebSocketEventType.TOOL_EXECUTING in result["missing_events"], \
            "Should detect missing tool_executing"
        assert WebSocketEventType.TOOL_COMPLETED in result["missing_events"], \
            "Should detect missing tool_completed"
        assert result["coverage_percentage"] == 60.0, f"Should have 60% coverage: {result['coverage_percentage']}"
        
        self.record_metric("missing_events_detection_passed", True)
        
    @pytest.mark.unit
    def test_event_order_violation_detection(self):
        """Test detection of event order violations."""
        # Create events in wrong order (tool_executing before agent_started)
        base_time = time.time()
        wrong_order_events = [
            self._create_test_event(
                WebSocketEventType.TOOL_EXECUTING, 
                agent_name="data_agent",
                tool_name="analyzer",
                timestamp=base_time
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_STARTED, 
                agent_name="data_agent",
                timestamp=base_time + 1
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_THINKING, 
                agent_name="data_agent",
                timestamp=base_time + 2
            ),
            self._create_test_event(
                WebSocketEventType.TOOL_COMPLETED, 
                agent_name="data_agent",
                tool_name="analyzer",
                timestamp=base_time + 3
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_COMPLETED, 
                agent_name="data_agent",
                timestamp=base_time + 4
            )
        ]
        
        result = self.event_validator.validate_event_sequence(wrong_order_events)
        
        # Assertions
        assert result["valid"] is False, "Wrong order should be invalid"
        assert len(result["order_violations"]) > 0, f"Should detect order violations: {result['order_violations']}"
        
        # Check specific violation
        violations_text = " ".join(result["order_violations"])
        assert "tool_executing" in violations_text.lower(), "Should detect tool_executing order violation"
        assert "missing prerequisites" in violations_text.lower(), "Should identify missing prerequisites"
        
        self.record_metric("order_violation_detection_passed", True)
        
    @pytest.mark.unit
    def test_event_content_validation(self):
        """Test validation of event content structure and fields."""
        # Test event with missing required fields
        invalid_event = self._create_test_event(
            WebSocketEventType.TOOL_EXECUTING,
            agent_name=None,  # Missing required agent_name
            tool_name=None,   # Missing required tool_name
            data={}
        )
        
        validation = self.event_validator.validate_single_event(invalid_event)
        
        # Assertions
        assert validation["valid"] is False, "Event with missing fields should be invalid"
        assert len(validation["errors"]) >= 2, f"Should detect missing fields: {validation['errors']}"
        assert any("agent_name" in error for error in validation["errors"]), \
            "Should detect missing agent_name"
        assert any("tool_name" in error for error in validation["errors"]), \
            "Should detect missing tool_name"
        
        # Test valid event
        valid_event = self._create_test_event(
            WebSocketEventType.TOOL_EXECUTING,
            agent_name="data_agent",
            tool_name="cost_analyzer",
            data={"tool_params": {"period": "30d"}}
        )
        
        valid_result = self.event_validator.validate_single_event(valid_event)
        assert valid_result["valid"] is True, f"Valid event should pass: {valid_result}"
        
        self.record_metric("content_validation_passed", True)
        
    @pytest.mark.unit
    def test_event_quality_scoring(self):
        """Test event quality scoring algorithm."""
        # Perfect sequence
        perfect_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED, agent_name="agent1"),
            self._create_test_event(WebSocketEventType.AGENT_THINKING, agent_name="agent1"),
            self._create_test_event(WebSocketEventType.TOOL_EXECUTING, agent_name="agent1", tool_name="tool1"),
            self._create_test_event(WebSocketEventType.TOOL_COMPLETED, agent_name="agent1", tool_name="tool1"),
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED, agent_name="agent1")
        ]
        
        perfect_score = self.event_validator.calculate_event_quality_score(perfect_events)
        assert perfect_score["score"] >= 95, f"Perfect sequence should score A+: {perfect_score}"
        assert perfect_score["grade"] == "A+", f"Grade should be A+: {perfect_score['grade']}"
        assert perfect_score["coverage"] == 100.0, "Should have 100% coverage"
        
        # Imperfect sequence (missing events, wrong order)
        imperfect_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED, agent_name="agent1"),
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED, agent_name="agent1")
        ]
        
        imperfect_score = self.event_validator.calculate_event_quality_score(imperfect_events)
        assert imperfect_score["score"] < 50, f"Imperfect sequence should score poorly: {imperfect_score}"
        assert imperfect_score["grade"] in ["D", "F"], f"Grade should be D or F: {imperfect_score['grade']}"
        assert imperfect_score["coverage"] < 100.0, "Should have incomplete coverage"
        
        self.record_metric("quality_scoring_passed", True)
        self.record_metric("perfect_score", perfect_score["score"])
        self.record_metric("imperfect_score", imperfect_score["score"])
        
    @pytest.mark.unit
    def test_multi_agent_event_sequence_validation(self):
        """Test validation of events from multiple agents in pipeline."""
        base_time = time.time()
        
        # Create events for Data  ->  Optimization  ->  Report pipeline
        multi_agent_events = [
            # Data Agent
            self._create_test_event(
                WebSocketEventType.AGENT_STARTED, 
                agent_name="data_agent",
                timestamp=base_time
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_THINKING, 
                agent_name="data_agent",
                timestamp=base_time + 1
            ),
            self._create_test_event(
                WebSocketEventType.TOOL_EXECUTING, 
                agent_name="data_agent",
                tool_name="data_collector",
                timestamp=base_time + 2
            ),
            self._create_test_event(
                WebSocketEventType.TOOL_COMPLETED, 
                agent_name="data_agent",
                tool_name="data_collector",
                timestamp=base_time + 3
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_COMPLETED, 
                agent_name="data_agent",
                timestamp=base_time + 4
            ),
            
            # Optimization Agent
            self._create_test_event(
                WebSocketEventType.AGENT_STARTED, 
                agent_name="optimization_agent",
                timestamp=base_time + 5
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_THINKING, 
                agent_name="optimization_agent",
                timestamp=base_time + 6
            ),
            self._create_test_event(
                WebSocketEventType.TOOL_EXECUTING, 
                agent_name="optimization_agent",
                tool_name="optimizer",
                timestamp=base_time + 7
            ),
            self._create_test_event(
                WebSocketEventType.TOOL_COMPLETED, 
                agent_name="optimization_agent",
                tool_name="optimizer",
                timestamp=base_time + 8
            ),
            self._create_test_event(
                WebSocketEventType.AGENT_COMPLETED, 
                agent_name="optimization_agent",
                timestamp=base_time + 9
            )
        ]
        
        result = self.event_validator.validate_event_sequence(multi_agent_events)
        
        # Should be valid (each agent follows proper order)
        assert result["valid"] is True, f"Multi-agent sequence should be valid: {result}"
        assert result["coverage_percentage"] == 100.0, "Should have full coverage"
        assert len(result["order_violations"]) == 0, "Should have no order violations"
        
        self.record_metric("multi_agent_validation_passed", True)
        self.record_metric("agents_tested", 2)
        
    @pytest.mark.unit
    def test_get_missing_events_for_completion(self):
        """Test calculation of missing events needed for completion."""
        # Partial event sequence
        partial_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED, agent_name="agent1"),
            self._create_test_event(WebSocketEventType.AGENT_THINKING, agent_name="agent1"),
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED, agent_name="agent1")
        ]
        
        missing = self.event_validator.get_missing_events_for_completion(partial_events)
        
        assert len(missing) == 2, f"Should identify 2 missing events: {missing}"
        assert WebSocketEventType.TOOL_EXECUTING in missing, "Should identify missing tool_executing"
        assert WebSocketEventType.TOOL_COMPLETED in missing, "Should identify missing tool_completed"
        
        # Complete sequence
        complete_events = [
            self._create_test_event(WebSocketEventType.AGENT_STARTED, agent_name="agent1"),
            self._create_test_event(WebSocketEventType.AGENT_THINKING, agent_name="agent1"),
            self._create_test_event(WebSocketEventType.TOOL_EXECUTING, agent_name="agent1", tool_name="tool1"),
            self._create_test_event(WebSocketEventType.TOOL_COMPLETED, agent_name="agent1", tool_name="tool1"),
            self._create_test_event(WebSocketEventType.AGENT_COMPLETED, agent_name="agent1")
        ]
        
        complete_missing = self.event_validator.get_missing_events_for_completion(complete_events)
        assert len(complete_missing) == 0, f"Complete sequence should have no missing events: {complete_missing}"
        
        self.record_metric("missing_events_calculation_passed", True)
        
    @pytest.mark.unit
    def test_event_serialization_and_deserialization(self):
        """Test event conversion to/from dictionary format."""
        original_event = self._create_test_event(
            WebSocketEventType.TOOL_EXECUTING,
            agent_name="test_agent",
            tool_name="test_tool",
            data={"param1": "value1", "param2": 42}
        )
        
        # Serialize
        event_dict = original_event.to_dict()
        assert isinstance(event_dict, dict), "Should serialize to dictionary"
        assert event_dict["type"] == "tool_executing", "Should preserve event type"
        assert event_dict["agent_name"] == "test_agent", "Should preserve agent name"
        assert event_dict["tool_name"] == "test_tool", "Should preserve tool name"
        assert event_dict["data"]["param1"] == "value1", "Should preserve data"
        
        # Deserialize
        reconstructed_event = WebSocketEvent.from_dict(event_dict)
        assert reconstructed_event.event_type == original_event.event_type, "Should preserve event type"
        assert reconstructed_event.agent_name == original_event.agent_name, "Should preserve agent name"
        assert reconstructed_event.tool_name == original_event.tool_name, "Should preserve tool name"
        assert reconstructed_event.data == original_event.data, "Should preserve data"
        assert str(reconstructed_event.user_id) == str(original_event.user_id), "Should preserve user ID"
        
        self.record_metric("serialization_test_passed", True)
        
    @pytest.mark.unit
    def test_timestamp_validation(self):
        """Test validation of event timestamps."""
        current_time = time.time()
        
        # Future timestamp (beyond reasonable clock skew)
        future_event = self._create_test_event(
            WebSocketEventType.AGENT_STARTED,
            timestamp=current_time + 120  # 2 minutes in future
        )
        
        future_result = self.event_validator.validate_single_event(future_event)
        assert len(future_result["warnings"]) > 0, "Should warn about future timestamp"
        assert any("future" in warning.lower() for warning in future_result["warnings"]), \
            "Should specifically warn about future timestamp"
        
        # Very old timestamp
        old_event = self._create_test_event(
            WebSocketEventType.AGENT_STARTED,
            timestamp=current_time - 7200  # 2 hours ago
        )
        
        old_result = self.event_validator.validate_single_event(old_event)
        assert len(old_result["warnings"]) > 0, "Should warn about old timestamp"
        assert any("old" in warning.lower() for warning in old_result["warnings"]), \
            "Should specifically warn about old timestamp"
        
        # Normal timestamp
        normal_event = self._create_test_event(
            WebSocketEventType.AGENT_STARTED,
            timestamp=current_time
        )
        
        normal_result = self.event_validator.validate_single_event(normal_event)
        assert len([w for w in normal_result["warnings"] if "timestamp" in w.lower()]) == 0, \
            "Should not warn about normal timestamp"
        
        self.record_metric("timestamp_validation_passed", True)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])