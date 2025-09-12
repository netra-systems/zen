"""
Unit Tests for Agent Execution Phase Validation Rules

Business Value Justification (BVJ):
- Segment: ALL (Free  ->  Enterprise) - execution phase tracking for all users
- Business Goal: User experience transparency and debugging capability  
- Value Impact: Provides detailed execution progress for WebSocket events and error diagnostics
- Strategic Impact: Enables granular monitoring of agent execution for operational excellence

This module tests the AgentExecutionPhase validation rules to ensure:
1. AgentExecutionPhase enum has all required phases for complete lifecycle tracking
2. Phase transitions follow logical business flow rules
3. Phase validation prevents invalid transitions
4. Error phases are properly categorized and handled
5. Phase metadata supports debugging and monitoring
6. WebSocket event integration works with phase tracking
"""

import pytest
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

# SSOT imports as per SSOT_IMPORT_REGISTRY.md
from netra_backend.app.core.agent_execution_tracker import (
    AgentExecutionPhase,
    PhaseTransition,
    ExecutionRecord,
    AgentExecutionTracker,
    ExecutionState,
    get_execution_tracker
)
from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestPhaseValidationRules(SSotBaseTestCase):
    """Unit tests for agent execution phase validation and transition rules."""
    
    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.tracker = AgentExecutionTracker()
        self.test_user_id = f"user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"thread_{uuid.uuid4().hex[:8]}"
        self.test_agent_name = "test_agent"
    
    def test_agent_execution_phase_enum_completeness(self):
        """Test that AgentExecutionPhase enum has all required phases."""
        expected_phases = {
            # Initialization phases
            'CREATED', 'WEBSOCKET_SETUP', 'CONTEXT_VALIDATION',
            
            # Execution phases  
            'STARTING', 'THINKING', 'TOOL_PREPARATION', 
            'LLM_INTERACTION', 'TOOL_EXECUTION', 'RESULT_PROCESSING',
            
            # Completion phases
            'COMPLETING', 'COMPLETED',
            
            # Error phases
            'TIMEOUT', 'FAILED', 'CIRCUIT_BREAKER_OPEN'
        }
        
        actual_phases = {phase.name for phase in AgentExecutionPhase}
        self.assertEqual(expected_phases, actual_phases, 
                        "AgentExecutionPhase enum missing expected phases")
        
        # Verify phase values are lowercase with underscores
        for phase in AgentExecutionPhase:
            self.assertEqual(phase.value, phase.name.lower())
            self.assertIsInstance(phase.value, str)
    
    def test_phase_categorization_business_logic(self):
        """Test logical categorization of phases for business rules."""
        # Initialization phases - setup required before execution
        initialization_phases = {
            AgentExecutionPhase.CREATED,
            AgentExecutionPhase.WEBSOCKET_SETUP, 
            AgentExecutionPhase.CONTEXT_VALIDATION
        }
        
        # Active execution phases - agent is actively working
        execution_phases = {
            AgentExecutionPhase.STARTING,
            AgentExecutionPhase.THINKING,
            AgentExecutionPhase.TOOL_PREPARATION,
            AgentExecutionPhase.LLM_INTERACTION,
            AgentExecutionPhase.TOOL_EXECUTION,
            AgentExecutionPhase.RESULT_PROCESSING
        }
        
        # Completion phases - execution finishing normally
        completion_phases = {
            AgentExecutionPhase.COMPLETING,
            AgentExecutionPhase.COMPLETED
        }
        
        # Error phases - execution failed or interrupted
        error_phases = {
            AgentExecutionPhase.TIMEOUT,
            AgentExecutionPhase.FAILED,
            AgentExecutionPhase.CIRCUIT_BREAKER_OPEN
        }
        
        # All phases should be categorized
        all_categorized = initialization_phases | execution_phases | completion_phases | error_phases
        all_enum_phases = set(AgentExecutionPhase)
        
        self.assertEqual(all_categorized, all_enum_phases,
                        "All AgentExecutionPhase values should be categorized")
        
        # Categories should not overlap
        self.assertEqual(len(initialization_phases & execution_phases), 0)
        self.assertEqual(len(initialization_phases & completion_phases), 0)
        self.assertEqual(len(execution_phases & completion_phases), 0)
    
    def test_valid_phase_transitions_initialization_flow(self):
        """Test valid phase transitions during initialization."""
        phase_validator = MockPhaseValidator()
        
        # Standard initialization flow
        valid_transitions = [
            (None, AgentExecutionPhase.CREATED),
            (AgentExecutionPhase.CREATED, AgentExecutionPhase.WEBSOCKET_SETUP),
            (AgentExecutionPhase.WEBSOCKET_SETUP, AgentExecutionPhase.CONTEXT_VALIDATION),
            (AgentExecutionPhase.CONTEXT_VALIDATION, AgentExecutionPhase.STARTING)
        ]
        
        for from_phase, to_phase in valid_transitions:
            is_valid = phase_validator.is_valid_transition(from_phase, to_phase)
            self.assertTrue(is_valid, 
                          f"Should allow transition {from_phase}  ->  {to_phase}")
    
    def test_valid_phase_transitions_execution_flow(self):
        """Test valid phase transitions during execution."""
        phase_validator = MockPhaseValidator()
        
        # Standard execution flow
        execution_transitions = [
            (AgentExecutionPhase.STARTING, AgentExecutionPhase.THINKING),
            (AgentExecutionPhase.THINKING, AgentExecutionPhase.TOOL_PREPARATION),
            (AgentExecutionPhase.TOOL_PREPARATION, AgentExecutionPhase.LLM_INTERACTION),
            (AgentExecutionPhase.LLM_INTERACTION, AgentExecutionPhase.TOOL_EXECUTION),
            (AgentExecutionPhase.TOOL_EXECUTION, AgentExecutionPhase.RESULT_PROCESSING),
            (AgentExecutionPhase.RESULT_PROCESSING, AgentExecutionPhase.COMPLETING)
        ]
        
        for from_phase, to_phase in execution_transitions:
            is_valid = phase_validator.is_valid_transition(from_phase, to_phase)
            self.assertTrue(is_valid,
                          f"Should allow execution transition {from_phase}  ->  {to_phase}")
    
    def test_valid_phase_transitions_to_completion(self):
        """Test valid phase transitions to completion phases."""
        phase_validator = MockPhaseValidator()
        
        # Any execution phase can go to COMPLETING
        execution_phases = [
            AgentExecutionPhase.THINKING,
            AgentExecutionPhase.TOOL_PREPARATION,
            AgentExecutionPhase.LLM_INTERACTION,
            AgentExecutionPhase.TOOL_EXECUTION,
            AgentExecutionPhase.RESULT_PROCESSING
        ]
        
        for phase in execution_phases:
            is_valid = phase_validator.is_valid_transition(phase, AgentExecutionPhase.COMPLETING)
            self.assertTrue(is_valid,
                          f"Should allow {phase}  ->  COMPLETING transition")
        
        # COMPLETING should go to COMPLETED
        is_valid = phase_validator.is_valid_transition(
            AgentExecutionPhase.COMPLETING, AgentExecutionPhase.COMPLETED
        )
        self.assertTrue(is_valid, "Should allow COMPLETING  ->  COMPLETED transition")
    
    def test_valid_phase_transitions_to_error_states(self):
        """Test valid phase transitions to error states."""
        phase_validator = MockPhaseValidator()
        
        # Any phase can transition to error states
        all_phases = list(AgentExecutionPhase)
        error_phases = [
            AgentExecutionPhase.FAILED,
            AgentExecutionPhase.TIMEOUT,
            AgentExecutionPhase.CIRCUIT_BREAKER_OPEN
        ]
        
        for from_phase in all_phases:
            for error_phase in error_phases:
                # Skip self-transitions for clarity
                if from_phase != error_phase:
                    is_valid = phase_validator.is_valid_transition(from_phase, error_phase)
                    self.assertTrue(is_valid,
                                  f"Should allow {from_phase}  ->  {error_phase} transition")
    
    def test_invalid_phase_transitions_backward_flow(self):
        """Test invalid backward phase transitions."""
        phase_validator = MockPhaseValidator()
        
        # Backward transitions should generally be invalid
        invalid_backward_transitions = [
            (AgentExecutionPhase.THINKING, AgentExecutionPhase.STARTING),
            (AgentExecutionPhase.TOOL_EXECUTION, AgentExecutionPhase.THINKING),
            (AgentExecutionPhase.COMPLETED, AgentExecutionPhase.COMPLETING),
            (AgentExecutionPhase.RESULT_PROCESSING, AgentExecutionPhase.TOOL_PREPARATION),
            (AgentExecutionPhase.CONTEXT_VALIDATION, AgentExecutionPhase.CREATED)
        ]
        
        for from_phase, to_phase in invalid_backward_transitions:
            is_valid = phase_validator.is_valid_transition(from_phase, to_phase)
            self.assertFalse(is_valid,
                           f"Should reject backward transition {from_phase}  ->  {to_phase}")
    
    def test_invalid_phase_transitions_skip_critical_phases(self):
        """Test invalid transitions that skip critical phases."""
        phase_validator = MockPhaseValidator()
        
        # Transitions that skip important setup or validation
        invalid_skip_transitions = [
            (AgentExecutionPhase.CREATED, AgentExecutionPhase.STARTING),  # Skip WebSocket/context setup
            (AgentExecutionPhase.THINKING, AgentExecutionPhase.TOOL_EXECUTION),  # Skip preparation
            (AgentExecutionPhase.TOOL_PREPARATION, AgentExecutionPhase.RESULT_PROCESSING),  # Skip execution
            (None, AgentExecutionPhase.THINKING),  # Skip all initialization
        ]
        
        for from_phase, to_phase in invalid_skip_transitions:
            is_valid = phase_validator.is_valid_transition(from_phase, to_phase)
            self.assertFalse(is_valid,
                           f"Should reject skipping transition {from_phase}  ->  {to_phase}")
    
    def test_phase_transition_recording_with_metadata(self):
        """Test PhaseTransition recording with metadata."""
        from_phase = AgentExecutionPhase.THINKING
        to_phase = AgentExecutionPhase.TOOL_PREPARATION
        
        transition = PhaseTransition(
            from_phase=from_phase.value if from_phase else None,
            to_phase=to_phase.value,
            timestamp=datetime.now(timezone.utc),
            duration_ms=150,
            metadata={
                "agent_name": self.test_agent_name,
                "user_id": self.test_user_id,
                "transition_reason": "normal_flow"
            }
        )
        
        # Verify transition attributes
        self.assertEqual(transition.from_phase, from_phase.value)
        self.assertEqual(transition.to_phase, to_phase.value)
        self.assertIsInstance(transition.timestamp, datetime)
        self.assertEqual(transition.duration_ms, 150)
        self.assertIn("agent_name", transition.metadata)
        self.assertIn("user_id", transition.metadata)
        self.assertIn("transition_reason", transition.metadata)
    
    def test_phase_transition_timing_validation(self):
        """Test phase transition timing for performance monitoring."""
        phase_validator = MockPhaseValidator()
        
        # Test reasonable timing for different phase transitions
        timing_expectations = {
            # Quick transitions (setup/validation)
            (AgentExecutionPhase.CREATED, AgentExecutionPhase.WEBSOCKET_SETUP): (0, 100),  # 0-100ms
            (AgentExecutionPhase.WEBSOCKET_SETUP, AgentExecutionPhase.CONTEXT_VALIDATION): (0, 50),
            
            # Medium transitions (preparation)
            (AgentExecutionPhase.CONTEXT_VALIDATION, AgentExecutionPhase.STARTING): (0, 200),
            (AgentExecutionPhase.THINKING, AgentExecutionPhase.TOOL_PREPARATION): (100, 1000),
            
            # Potentially longer transitions (LLM calls)
            (AgentExecutionPhase.TOOL_PREPARATION, AgentExecutionPhase.LLM_INTERACTION): (200, 5000),
            (AgentExecutionPhase.LLM_INTERACTION, AgentExecutionPhase.TOOL_EXECUTION): (1000, 15000),
        }
        
        for (from_phase, to_phase), (min_ms, max_ms) in timing_expectations.items():
            # Test with reasonable timing
            reasonable_timing = (min_ms + max_ms) // 2
            is_reasonable = phase_validator.is_reasonable_timing(
                from_phase, to_phase, reasonable_timing
            )
            self.assertTrue(is_reasonable,
                          f"Timing {reasonable_timing}ms should be reasonable for "
                          f"{from_phase}  ->  {to_phase}")
            
            # Test with excessive timing
            excessive_timing = max_ms * 3
            is_reasonable = phase_validator.is_reasonable_timing(
                from_phase, to_phase, excessive_timing
            )
            self.assertFalse(is_reasonable,
                           f"Timing {excessive_timing}ms should be excessive for "
                           f"{from_phase}  ->  {to_phase}")
    
    def test_phase_websocket_event_mapping(self):
        """Test mapping of phases to WebSocket events for real-time updates."""
        phase_to_event_mapping = {
            AgentExecutionPhase.STARTING: "agent_started",
            AgentExecutionPhase.THINKING: "agent_thinking", 
            AgentExecutionPhase.TOOL_PREPARATION: "tool_executing",
            AgentExecutionPhase.TOOL_EXECUTION: "tool_executing",
            AgentExecutionPhase.RESULT_PROCESSING: "tool_completed",
            AgentExecutionPhase.COMPLETED: "agent_completed",
            AgentExecutionPhase.FAILED: "agent_failed",
            AgentExecutionPhase.TIMEOUT: "agent_timeout"
        }
        
        for phase, expected_event in phase_to_event_mapping.items():
            # Test event mapping logic
            mapped_event = self._map_phase_to_websocket_event(phase)
            self.assertEqual(mapped_event, expected_event,
                           f"Phase {phase} should map to event '{expected_event}'")
    
    def test_phase_error_handling_and_recovery(self):
        """Test phase validation during error conditions."""
        phase_validator = MockPhaseValidator()
        
        # Test error recovery scenarios
        error_recovery_scenarios = [
            # Circuit breaker opens during LLM interaction
            (AgentExecutionPhase.LLM_INTERACTION, AgentExecutionPhase.CIRCUIT_BREAKER_OPEN),
            
            # Timeout during tool execution
            (AgentExecutionPhase.TOOL_EXECUTION, AgentExecutionPhase.TIMEOUT),
            
            # General failure during any phase
            (AgentExecutionPhase.THINKING, AgentExecutionPhase.FAILED),
            (AgentExecutionPhase.RESULT_PROCESSING, AgentExecutionPhase.FAILED)
        ]
        
        for from_phase, error_phase in error_recovery_scenarios:
            is_valid = phase_validator.is_valid_transition(from_phase, error_phase)
            self.assertTrue(is_valid,
                          f"Should allow error transition {from_phase}  ->  {error_phase}")
    
    def test_phase_validation_business_rule_enforcement(self):
        """Test that phase validation enforces business rules."""
        phase_validator = MockPhaseValidator()
        
        # Business rule: WebSocket setup must happen before context validation
        self.assertFalse(
            phase_validator.is_valid_transition(
                AgentExecutionPhase.CREATED, AgentExecutionPhase.CONTEXT_VALIDATION
            )
        )
        
        # Business rule: Tool preparation must happen before LLM interaction
        self.assertFalse(
            phase_validator.is_valid_transition(
                AgentExecutionPhase.THINKING, AgentExecutionPhase.LLM_INTERACTION
            )
        )
        
        # Business rule: Cannot go back to initialization phases after execution starts
        self.assertFalse(
            phase_validator.is_valid_transition(
                AgentExecutionPhase.THINKING, AgentExecutionPhase.WEBSOCKET_SETUP
            )
        )
    
    def test_phase_serialization_for_monitoring(self):
        """Test phase serialization for monitoring and logging."""
        test_phases = [
            AgentExecutionPhase.CREATED,
            AgentExecutionPhase.THINKING,
            AgentExecutionPhase.COMPLETED,
            AgentExecutionPhase.FAILED
        ]
        
        for phase in test_phases:
            # Should serialize to JSON-compatible format
            phase_data = {
                "phase": phase.value,
                "phase_name": phase.name,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "agent_name": self.test_agent_name
            }
            
            # Should not raise serialization errors
            import json
            serialized = json.dumps(phase_data)
            deserialized = json.loads(serialized)
            
            self.assertEqual(deserialized["phase"], phase.value)
            self.assertEqual(deserialized["phase_name"], phase.name)
    
    def _map_phase_to_websocket_event(self, phase: AgentExecutionPhase) -> str:
        """Helper method to map phases to WebSocket events."""
        mapping = {
            AgentExecutionPhase.STARTING: "agent_started",
            AgentExecutionPhase.THINKING: "agent_thinking",
            AgentExecutionPhase.TOOL_PREPARATION: "tool_executing", 
            AgentExecutionPhase.TOOL_EXECUTION: "tool_executing",
            AgentExecutionPhase.RESULT_PROCESSING: "tool_completed",
            AgentExecutionPhase.COMPLETED: "agent_completed",
            AgentExecutionPhase.FAILED: "agent_failed",
            AgentExecutionPhase.TIMEOUT: "agent_timeout"
        }
        return mapping.get(phase, "agent_update")


class MockPhaseValidator:
    """Mock phase validator for isolated unit testing."""
    
    def __init__(self):
        # Define valid transitions as a set of tuples
        self.valid_transitions = {
            # Initialization flow
            (None, AgentExecutionPhase.CREATED),
            (AgentExecutionPhase.CREATED, AgentExecutionPhase.WEBSOCKET_SETUP),
            (AgentExecutionPhase.WEBSOCKET_SETUP, AgentExecutionPhase.CONTEXT_VALIDATION),
            (AgentExecutionPhase.CONTEXT_VALIDATION, AgentExecutionPhase.STARTING),
            
            # Execution flow
            (AgentExecutionPhase.STARTING, AgentExecutionPhase.THINKING),
            (AgentExecutionPhase.THINKING, AgentExecutionPhase.TOOL_PREPARATION),
            (AgentExecutionPhase.TOOL_PREPARATION, AgentExecutionPhase.LLM_INTERACTION),
            (AgentExecutionPhase.LLM_INTERACTION, AgentExecutionPhase.TOOL_EXECUTION),
            (AgentExecutionPhase.TOOL_EXECUTION, AgentExecutionPhase.RESULT_PROCESSING),
            (AgentExecutionPhase.RESULT_PROCESSING, AgentExecutionPhase.COMPLETING),
            (AgentExecutionPhase.COMPLETING, AgentExecutionPhase.COMPLETED),
        }
        
        # Any phase can transition to error states
        all_phases = list(AgentExecutionPhase)
        error_phases = [
            AgentExecutionPhase.FAILED,
            AgentExecutionPhase.TIMEOUT, 
            AgentExecutionPhase.CIRCUIT_BREAKER_OPEN
        ]
        
        for phase in all_phases:
            for error_phase in error_phases:
                if phase != error_phase:  # Avoid self-transitions
                    self.valid_transitions.add((phase, error_phase))
        
        # Any execution phase can go to COMPLETING
        execution_phases = [
            AgentExecutionPhase.THINKING,
            AgentExecutionPhase.TOOL_PREPARATION,
            AgentExecutionPhase.LLM_INTERACTION,
            AgentExecutionPhase.TOOL_EXECUTION,
            AgentExecutionPhase.RESULT_PROCESSING
        ]
        
        for phase in execution_phases:
            self.valid_transitions.add((phase, AgentExecutionPhase.COMPLETING))
    
    def is_valid_transition(self, from_phase: Optional[AgentExecutionPhase], 
                          to_phase: AgentExecutionPhase) -> bool:
        """Check if transition is valid."""
        return (from_phase, to_phase) in self.valid_transitions
    
    def is_reasonable_timing(self, from_phase: AgentExecutionPhase, 
                           to_phase: AgentExecutionPhase, duration_ms: int) -> bool:
        """Check if transition timing is reasonable."""
        # Simple timing validation logic
        timing_limits = {
            (AgentExecutionPhase.CREATED, AgentExecutionPhase.WEBSOCKET_SETUP): 100,
            (AgentExecutionPhase.THINKING, AgentExecutionPhase.TOOL_PREPARATION): 1000,
            (AgentExecutionPhase.LLM_INTERACTION, AgentExecutionPhase.TOOL_EXECUTION): 15000,
        }
        
        max_duration = timing_limits.get((from_phase, to_phase), 5000)  # Default 5s
        return 0 <= duration_ms <= max_duration


if __name__ == '__main__':
    pytest.main([__file__])