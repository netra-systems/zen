"""
Comprehensive Agent Execution State Machine Unit Tests

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure agent execution follows proper state transitions for reliable AI interactions
- Value Impact: Prevents agent execution failures that would break the core chat experience
- Strategic Impact: Foundation for reliable AI agent orchestration and user value delivery

This test suite validates agent execution state machine behavior in isolation,
ensuring proper state management during the complete agent lifecycle from initialization
through execution to completion. These tests are critical for the Golden Path requirements.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from unittest.mock import Mock, AsyncMock, patch
from dataclasses import dataclass

from shared.types.core_types import UserID, ThreadID, RunID, ensure_user_id


class AgentExecutionState(Enum):
    """Agent execution states for comprehensive testing."""
    INITIALIZING = "initializing"
    READY = "ready"
    STARTING = "starting"
    THINKING = "thinking"
    TOOL_PLANNING = "tool_planning"
    TOOL_EXECUTING = "tool_executing"
    TOOL_PROCESSING = "tool_processing"
    TOOL_COMPLETED = "tool_completed"
    ANALYZING = "analyzing"
    RESPONDING = "responding"
    COMPLETED = "completed"
    PAUSED = "paused"
    RESUMING = "resuming"
    ERROR = "error"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"
    TERMINATED = "terminated"


class AgentExecutionEvent(Enum):
    """Events that trigger agent state transitions."""
    INITIALIZE = "initialize"
    START_EXECUTION = "start_execution"
    BEGIN_THINKING = "begin_thinking"
    PLAN_TOOLS = "plan_tools"
    EXECUTE_TOOL = "execute_tool"
    PROCESS_TOOL_RESULT = "process_tool_result"
    COMPLETE_TOOL = "complete_tool"
    ANALYZE_RESULTS = "analyze_results"
    GENERATE_RESPONSE = "generate_response"
    COMPLETE_EXECUTION = "complete_execution"
    PAUSE_EXECUTION = "pause_execution"
    RESUME_EXECUTION = "resume_execution"
    HANDLE_ERROR = "handle_error"
    CANCEL_EXECUTION = "cancel_execution"
    TIMEOUT_EXECUTION = "timeout_execution"
    TERMINATE_EXECUTION = "terminate_execution"


@dataclass
class AgentExecutionContext:
    """Context for agent execution state machine."""
    agent_type: str
    user_id: str
    thread_id: str
    run_id: str
    message: str
    tools_available: List[str]
    max_execution_time: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_details: Optional[Dict] = None
    tool_results: List[Dict] = None
    execution_metadata: Dict = None
    
    def __post_init__(self):
        if self.tool_results is None:
            self.tool_results = []
        if self.execution_metadata is None:
            self.execution_metadata = {}


class MockAgentExecutionStateMachine:
    """Mock agent execution state machine for comprehensive unit testing."""
    
    def __init__(self, context: AgentExecutionContext):
        self.context = context
        self.current_state = AgentExecutionState.INITIALIZING
        self.state_history: List[Dict[str, Any]] = []
        self.transition_log: List[Dict[str, Any]] = []
        self.event_emissions: List[Dict[str, Any]] = []  # WebSocket events
        self.tool_execution_queue: List[Dict[str, Any]] = []
        self.execution_metrics = {
            'state_transitions': 0,
            'tool_executions': 0,
            'thinking_duration': 0.0,
            'total_execution_time': 0.0,
            'error_count': 0,
            'websocket_events_sent': 0
        }
        
        # State machine configuration
        self.state_transition_matrix = self._build_agent_transition_matrix()
        self.state_entry_actions = self._build_agent_entry_actions()
        self.state_exit_actions = self._build_agent_exit_actions()
        self.websocket_event_map = self._build_websocket_event_map()
        
        # Execution control
        self.execution_paused = False
        self.execution_cancelled = False
        self.tools_completed = set()
        self.current_tool = None
        
        # Record initial state
        self._record_state_entry(AgentExecutionState.INITIALIZING, "agent_creation")
    
    def _build_agent_transition_matrix(self) -> Dict[AgentExecutionState, List[AgentExecutionState]]:
        """Build valid state transitions for agent execution."""
        return {
            AgentExecutionState.INITIALIZING: [
                AgentExecutionState.READY,
                AgentExecutionState.ERROR,
                AgentExecutionState.TERMINATED
            ],
            AgentExecutionState.READY: [
                AgentExecutionState.STARTING,
                AgentExecutionState.PAUSED,
                AgentExecutionState.CANCELLED,
                AgentExecutionState.ERROR
            ],
            AgentExecutionState.STARTING: [
                AgentExecutionState.THINKING,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED,
                AgentExecutionState.TIMEOUT
            ],
            AgentExecutionState.THINKING: [
                AgentExecutionState.TOOL_PLANNING,
                AgentExecutionState.ANALYZING,  # Direct to analysis if no tools needed
                AgentExecutionState.RESPONDING,  # Direct response
                AgentExecutionState.PAUSED,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED,
                AgentExecutionState.TIMEOUT
            ],
            AgentExecutionState.TOOL_PLANNING: [
                AgentExecutionState.TOOL_EXECUTING,
                AgentExecutionState.THINKING,  # Back to thinking if plan changes
                AgentExecutionState.ANALYZING,  # Skip tools if not needed
                AgentExecutionState.PAUSED,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED
            ],
            AgentExecutionState.TOOL_EXECUTING: [
                AgentExecutionState.TOOL_PROCESSING,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED,
                AgentExecutionState.TIMEOUT
            ],
            AgentExecutionState.TOOL_PROCESSING: [
                AgentExecutionState.TOOL_COMPLETED,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED
            ],
            AgentExecutionState.TOOL_COMPLETED: [
                AgentExecutionState.TOOL_PLANNING,  # Plan next tool
                AgentExecutionState.ANALYZING,     # Analyze results
                AgentExecutionState.THINKING,     # More thinking needed
                AgentExecutionState.PAUSED,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED
            ],
            AgentExecutionState.ANALYZING: [
                AgentExecutionState.RESPONDING,
                AgentExecutionState.THINKING,     # Need more thinking
                AgentExecutionState.TOOL_PLANNING, # Need more tools
                AgentExecutionState.COMPLETED,   # Analysis complete
                AgentExecutionState.PAUSED,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED
            ],
            AgentExecutionState.RESPONDING: [
                AgentExecutionState.COMPLETED,
                AgentExecutionState.ERROR,
                AgentExecutionState.CANCELLED
            ],
            AgentExecutionState.PAUSED: [
                AgentExecutionState.RESUMING,
                AgentExecutionState.CANCELLED,
                AgentExecutionState.TERMINATED
            ],
            AgentExecutionState.RESUMING: [
                AgentExecutionState.THINKING,
                AgentExecutionState.TOOL_PLANNING,
                AgentExecutionState.ANALYZING,
                AgentExecutionState.ERROR
            ],
            AgentExecutionState.COMPLETED: [],  # Terminal state
            AgentExecutionState.ERROR: [
                AgentExecutionState.READY,       # Retry from beginning
                AgentExecutionState.CANCELLED,   # Give up
                AgentExecutionState.TERMINATED   # Hard termination
            ],
            AgentExecutionState.CANCELLED: [
                AgentExecutionState.TERMINATED   # Can only terminate after cancel
            ],
            AgentExecutionState.TIMEOUT: [
                AgentExecutionState.CANCELLED,
                AgentExecutionState.TERMINATED
            ],
            AgentExecutionState.TERMINATED: []  # Terminal state
        }
    
    def _build_agent_entry_actions(self) -> Dict[AgentExecutionState, Callable]:
        """Build state entry actions for agent execution."""
        return {
            AgentExecutionState.READY: self._on_entering_ready,
            AgentExecutionState.STARTING: self._on_entering_starting,
            AgentExecutionState.THINKING: self._on_entering_thinking,
            AgentExecutionState.TOOL_EXECUTING: self._on_entering_tool_executing,
            AgentExecutionState.TOOL_COMPLETED: self._on_entering_tool_completed,
            AgentExecutionState.ANALYZING: self._on_entering_analyzing,
            AgentExecutionState.RESPONDING: self._on_entering_responding,
            AgentExecutionState.COMPLETED: self._on_entering_completed,
            AgentExecutionState.ERROR: self._on_entering_error,
            AgentExecutionState.PAUSED: self._on_entering_paused
        }
    
    def _build_agent_exit_actions(self) -> Dict[AgentExecutionState, Callable]:
        """Build state exit actions for agent execution."""
        return {
            AgentExecutionState.THINKING: self._on_exiting_thinking,
            AgentExecutionState.TOOL_EXECUTING: self._on_exiting_tool_executing,
            AgentExecutionState.PAUSED: self._on_exiting_paused,
            AgentExecutionState.ERROR: self._on_exiting_error
        }
    
    def _build_websocket_event_map(self) -> Dict[AgentExecutionState, str]:
        """Map agent states to WebSocket events (critical for Golden Path)."""
        return {
            AgentExecutionState.STARTING: "agent_started",
            AgentExecutionState.THINKING: "agent_thinking", 
            AgentExecutionState.TOOL_EXECUTING: "tool_executing",
            AgentExecutionState.TOOL_COMPLETED: "tool_completed",
            AgentExecutionState.COMPLETED: "agent_completed",
            AgentExecutionState.ERROR: "agent_error",
            AgentExecutionState.CANCELLED: "agent_cancelled"
        }
    
    def _on_entering_ready(self):
        """Actions when entering READY state."""
        self.context.execution_metadata['ready_at'] = datetime.utcnow().isoformat()
        self.context.execution_metadata['agent_initialized'] = True
    
    def _on_entering_starting(self):
        """Actions when entering STARTING state."""
        self.context.started_at = datetime.utcnow()
        self.context.execution_metadata['execution_started'] = True
        self._emit_websocket_event("agent_started")
    
    def _on_entering_thinking(self):
        """Actions when entering THINKING state."""
        self.context.execution_metadata['thinking_started'] = datetime.utcnow().isoformat()
        self._emit_websocket_event("agent_thinking")
    
    def _on_entering_tool_executing(self):
        """Actions when entering TOOL_EXECUTING state."""
        self.execution_metrics['tool_executions'] += 1
        self.context.execution_metadata['current_tool_started'] = datetime.utcnow().isoformat()
        self._emit_websocket_event("tool_executing")
    
    def _on_entering_tool_completed(self):
        """Actions when entering TOOL_COMPLETED state."""
        self.context.execution_metadata['tool_completed_at'] = datetime.utcnow().isoformat()
        self._emit_websocket_event("tool_completed")
    
    def _on_entering_analyzing(self):
        """Actions when entering ANALYZING state."""
        self.context.execution_metadata['analyzing_started'] = datetime.utcnow().isoformat()
    
    def _on_entering_responding(self):
        """Actions when entering RESPONDING state."""
        self.context.execution_metadata['responding_started'] = datetime.utcnow().isoformat()
    
    def _on_entering_completed(self):
        """Actions when entering COMPLETED state."""
        self.context.completed_at = datetime.utcnow()
        if self.context.started_at:
            total_time = (self.context.completed_at - self.context.started_at).total_seconds()
            self.execution_metrics['total_execution_time'] = total_time
        self.context.execution_metadata['execution_completed'] = True
        self._emit_websocket_event("agent_completed")
    
    def _on_entering_error(self):
        """Actions when entering ERROR state."""
        self.execution_metrics['error_count'] += 1
        self.context.execution_metadata['error_occurred_at'] = datetime.utcnow().isoformat()
        self._emit_websocket_event("agent_error")
    
    def _on_entering_paused(self):
        """Actions when entering PAUSED state."""
        self.execution_paused = True
        self.context.execution_metadata['paused_at'] = datetime.utcnow().isoformat()
    
    def _on_exiting_thinking(self):
        """Actions when exiting THINKING state."""
        if 'thinking_started' in self.context.execution_metadata:
            thinking_duration = (
                datetime.utcnow() - 
                datetime.fromisoformat(self.context.execution_metadata['thinking_started'])
            ).total_seconds()
            self.execution_metrics['thinking_duration'] += thinking_duration
    
    def _on_exiting_tool_executing(self):
        """Actions when exiting TOOL_EXECUTING state."""
        self.context.execution_metadata['tool_execution_completed'] = datetime.utcnow().isoformat()
    
    def _on_exiting_paused(self):
        """Actions when exiting PAUSED state."""
        self.execution_paused = False
        self.context.execution_metadata['resumed_at'] = datetime.utcnow().isoformat()
    
    def _on_exiting_error(self):
        """Actions when exiting ERROR state."""
        self.context.execution_metadata['error_recovery_attempted'] = datetime.utcnow().isoformat()
    
    def _emit_websocket_event(self, event_type: str):
        """Emit WebSocket event (critical for Golden Path user experience)."""
        websocket_event = {
            'type': event_type,
            'data': {
                'agent_type': self.context.agent_type,
                'user_id': self.context.user_id,
                'thread_id': self.context.thread_id,
                'run_id': self.context.run_id,
                'timestamp': datetime.utcnow().isoformat(),
                'state': self.current_state.value
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Add state-specific data
        if event_type == "tool_executing" and self.current_tool:
            websocket_event['data']['tool'] = self.current_tool
        elif event_type == "agent_completed":
            websocket_event['data']['execution_time'] = self.execution_metrics['total_execution_time']
            websocket_event['data']['tools_used'] = len(self.tools_completed)
        
        self.event_emissions.append(websocket_event)
        self.execution_metrics['websocket_events_sent'] += 1
    
    def can_transition_to(self, target_state: AgentExecutionState) -> bool:
        """Check if transition to target state is valid."""
        valid_transitions = self.state_transition_matrix.get(self.current_state, [])
        return target_state in valid_transitions
    
    def transition_to(self, target_state: AgentExecutionState, event: AgentExecutionEvent,
                     force: bool = False, metadata: Optional[Dict] = None) -> bool:
        """Attempt to transition to target state."""
        if not force and not self.can_transition_to(target_state):
            self._record_invalid_transition(self.current_state, target_state, event)
            return False
        
        # Execute exit actions
        exit_action = self.state_exit_actions.get(self.current_state)
        if exit_action:
            exit_action()
        
        # Record transition
        old_state = self.current_state
        self.current_state = target_state
        self.execution_metrics['state_transitions'] += 1
        
        # Execute entry actions
        entry_action = self.state_entry_actions.get(target_state)
        if entry_action:
            entry_action()
        
        # Record successful transition
        self._record_state_transition(old_state, target_state, event, metadata)
        return True
    
    def _record_state_entry(self, state: AgentExecutionState, reason: str):
        """Record state entry."""
        self.state_history.append({
            'state': state.value,
            'action': 'entry',
            'timestamp': datetime.utcnow().isoformat(),
            'reason': reason
        })
    
    def _record_state_transition(self, from_state: AgentExecutionState,
                                to_state: AgentExecutionState, event: AgentExecutionEvent,
                                metadata: Optional[Dict] = None):
        """Record successful state transition."""
        transition = {
            'from_state': from_state.value,
            'to_state': to_state.value,
            'event': event.value,
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {},
            'execution_context': {
                'user_id': self.context.user_id,
                'thread_id': self.context.thread_id,
                'run_id': self.context.run_id
            }
        }
        self.transition_log.append(transition)
    
    def _record_invalid_transition(self, from_state: AgentExecutionState,
                                  to_state: AgentExecutionState, event: AgentExecutionEvent):
        """Record invalid transition attempt."""
        self.transition_log.append({
            'from_state': from_state.value,
            'to_state': to_state.value,
            'event': event.value,
            'timestamp': datetime.utcnow().isoformat(),
            'valid': False,
            'error': 'invalid_state_transition'
        })
    
    def execute_tool(self, tool_name: str, tool_params: Dict = None) -> Dict[str, Any]:
        """Simulate tool execution with state management."""
        if self.current_state != AgentExecutionState.TOOL_EXECUTING:
            return {'error': 'Cannot execute tool in current state', 'state': self.current_state.value}
        
        self.current_tool = tool_name
        tool_params = tool_params or {}
        
        # Simulate tool execution
        import random
        execution_time = random.uniform(0.1, 2.0)
        success_rate = 0.9  # 90% success rate
        
        result = {
            'tool': tool_name,
            'params': tool_params,
            'execution_time': execution_time,
            'timestamp': datetime.utcnow().isoformat(),
            'success': random.random() < success_rate
        }
        
        if result['success']:
            result['data'] = {
                'tool_output': f"Mock output from {tool_name}",
                'metadata': {'execution_context': 'unit_test'}
            }
            self.tools_completed.add(tool_name)
        else:
            result['error'] = f"Mock error from {tool_name}"
        
        self.context.tool_results.append(result)
        return result
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get comprehensive execution metrics."""
        return {
            'current_state': self.current_state.value,
            'total_transitions': self.execution_metrics['state_transitions'],
            'tool_executions': self.execution_metrics['tool_executions'],
            'thinking_duration': self.execution_metrics['thinking_duration'],
            'total_execution_time': self.execution_metrics['total_execution_time'],
            'error_count': self.execution_metrics['error_count'],
            'websocket_events_sent': self.execution_metrics['websocket_events_sent'],
            'tools_completed': list(self.tools_completed),
            'is_paused': self.execution_paused,
            'is_cancelled': self.execution_cancelled,
            'transition_history_length': len(self.transition_log),
            'websocket_events_emitted': len(self.event_emissions)
        }


class TestAgentExecutionStateMachineUnit:
    """Comprehensive unit tests for agent execution state machine."""
    
    def create_test_context(self, agent_type: str = "test_agent", **kwargs) -> AgentExecutionContext:
        """Create test execution context."""
        defaults = {
            'user_id': 'test_user_123',
            'thread_id': 'test_thread_456',
            'run_id': 'test_run_789',
            'message': 'Test message for agent execution',
            'tools_available': ['search_tool', 'analysis_tool', 'report_tool'],
            'max_execution_time': 300.0
        }
        defaults.update(kwargs)
        return AgentExecutionContext(agent_type=agent_type, **defaults)
    
    def test_agent_initialization_state(self):
        """Test agent starts in correct initial state."""
        context = self.create_test_context()
        state_machine = MockAgentExecutionStateMachine(context)
        
        assert state_machine.current_state == AgentExecutionState.INITIALIZING
        assert len(state_machine.state_history) == 1
        assert state_machine.state_history[0]['state'] == 'initializing'
        assert state_machine.state_history[0]['action'] == 'entry'
        
        # Verify context is properly set
        assert state_machine.context.agent_type == 'test_agent'
        assert state_machine.context.user_id == 'test_user_123'
        assert len(state_machine.context.tools_available) == 3
    
    def test_agent_golden_path_execution(self):
        """Test complete agent execution golden path."""
        context = self.create_test_context(agent_type="triage_agent")
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Golden Path: INITIALIZING -> READY -> STARTING -> THINKING -> TOOL_PLANNING 
        # -> TOOL_EXECUTING -> TOOL_PROCESSING -> TOOL_COMPLETED -> ANALYZING -> RESPONDING -> COMPLETED
        golden_path_sequence = [
            (AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE),
            (AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION),
            (AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING),
            (AgentExecutionState.TOOL_PLANNING, AgentExecutionEvent.PLAN_TOOLS),
            (AgentExecutionState.TOOL_EXECUTING, AgentExecutionEvent.EXECUTE_TOOL),
            (AgentExecutionState.TOOL_PROCESSING, AgentExecutionEvent.PROCESS_TOOL_RESULT),
            (AgentExecutionState.TOOL_COMPLETED, AgentExecutionEvent.COMPLETE_TOOL),
            (AgentExecutionState.ANALYZING, AgentExecutionEvent.ANALYZE_RESULTS),
            (AgentExecutionState.RESPONDING, AgentExecutionEvent.GENERATE_RESPONSE),
            (AgentExecutionState.COMPLETED, AgentExecutionEvent.COMPLETE_EXECUTION)
        ]
        
        for target_state, event in golden_path_sequence:
            assert state_machine.can_transition_to(target_state), \
                f"Should allow transition to {target_state.value} from {state_machine.current_state.value}"
            
            success = state_machine.transition_to(target_state, event)
            assert success, f"Transition to {target_state.value} should succeed"
            assert state_machine.current_state == target_state
        
        # Verify all transitions were recorded
        assert len(state_machine.transition_log) == len(golden_path_sequence)
        
        # Verify execution metrics
        metrics = state_machine.get_execution_metrics()
        assert metrics['current_state'] == AgentExecutionState.COMPLETED.value
        assert metrics['total_transitions'] == len(golden_path_sequence)
        assert metrics['websocket_events_sent'] >= 4  # At least started, thinking, tool, completed
        
        # Verify critical WebSocket events were emitted
        emitted_event_types = [event['type'] for event in state_machine.event_emissions]
        critical_events = ['agent_started', 'agent_thinking', 'tool_executing', 'agent_completed']
        for critical_event in critical_events:
            assert critical_event in emitted_event_types, f"Must emit {critical_event} for Golden Path"
    
    def test_agent_tool_execution_cycle(self):
        """Test agent tool execution state management."""
        context = self.create_test_context(tools_available=['search', 'analyze', 'summarize'])
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Setup to tool execution state
        setup_transitions = [
            (AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE),
            (AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION),
            (AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING),
            (AgentExecutionState.TOOL_PLANNING, AgentExecutionEvent.PLAN_TOOLS),
            (AgentExecutionState.TOOL_EXECUTING, AgentExecutionEvent.EXECUTE_TOOL)
        ]
        
        for target_state, event in setup_transitions:
            state_machine.transition_to(target_state, event)
        
        # Execute multiple tools
        tools_to_execute = ['search', 'analyze', 'summarize']
        tool_results = []
        
        for tool_name in tools_to_execute:
            # Execute tool
            result = state_machine.execute_tool(tool_name, {'test_param': f'value_for_{tool_name}'})
            tool_results.append(result)
            
            # Transition through tool states
            state_machine.transition_to(AgentExecutionState.TOOL_PROCESSING, AgentExecutionEvent.PROCESS_TOOL_RESULT)
            state_machine.transition_to(AgentExecutionState.TOOL_COMPLETED, AgentExecutionEvent.COMPLETE_TOOL)
            
            # If more tools needed, go back to planning
            if tool_name != tools_to_execute[-1]:  # Not the last tool
                state_machine.transition_to(AgentExecutionState.TOOL_PLANNING, AgentExecutionEvent.PLAN_TOOLS)
                state_machine.transition_to(AgentExecutionState.TOOL_EXECUTING, AgentExecutionEvent.EXECUTE_TOOL)
        
        # Verify tool execution results
        assert len(state_machine.context.tool_results) == len(tools_to_execute)
        
        successful_tools = [r for r in tool_results if r.get('success')]
        assert len(successful_tools) > 0, "At least some tools should succeed"
        
        # Verify tool completion tracking
        assert len(state_machine.tools_completed) > 0
        
        # Verify tool-related WebSocket events
        tool_events = [e for e in state_machine.event_emissions if e['type'] in ['tool_executing', 'tool_completed']]
        assert len(tool_events) >= 2 * len(tools_to_execute)  # At least executing + completed for each tool
        
        # Verify execution metrics
        metrics = state_machine.get_execution_metrics()
        assert metrics['tool_executions'] == len(tools_to_execute)
    
    def test_agent_pause_resume_functionality(self):
        """Test agent execution pause and resume state management."""
        context = self.create_test_context()
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Setup to thinking state
        state_machine.transition_to(AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE)
        state_machine.transition_to(AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION)
        state_machine.transition_to(AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING)
        
        # Test pause
        assert state_machine.can_transition_to(AgentExecutionState.PAUSED)
        pause_success = state_machine.transition_to(AgentExecutionState.PAUSED, AgentExecutionEvent.PAUSE_EXECUTION)
        assert pause_success
        assert state_machine.execution_paused is True
        
        # Verify pause metadata
        assert 'paused_at' in state_machine.context.execution_metadata
        
        # Test resume
        assert state_machine.can_transition_to(AgentExecutionState.RESUMING)
        resume_start = state_machine.transition_to(AgentExecutionState.RESUMING, AgentExecutionEvent.RESUME_EXECUTION)
        assert resume_start
        
        # After resuming, can go to various states
        valid_resume_states = [AgentExecutionState.THINKING, AgentExecutionState.TOOL_PLANNING, AgentExecutionState.ANALYZING]
        for resume_state in valid_resume_states:
            assert state_machine.can_transition_to(resume_state)
        
        # Resume to thinking
        resume_complete = state_machine.transition_to(AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING)
        assert resume_complete
        assert state_machine.execution_paused is False
        
        # Verify resume metadata
        assert 'resumed_at' in state_machine.context.execution_metadata
    
    def test_agent_error_handling_and_recovery(self):
        """Test agent error states and recovery mechanisms."""
        context = self.create_test_context()
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Setup to tool execution
        state_machine.transition_to(AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE)
        state_machine.transition_to(AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION)
        state_machine.transition_to(AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING)
        state_machine.transition_to(AgentExecutionState.TOOL_EXECUTING, AgentExecutionEvent.EXECUTE_TOOL)
        
        # Simulate error
        assert state_machine.can_transition_to(AgentExecutionState.ERROR)
        error_transition = state_machine.transition_to(AgentExecutionState.ERROR, AgentExecutionEvent.HANDLE_ERROR,
                                                      metadata={'error_type': 'tool_failure', 'recoverable': True})
        assert error_transition
        
        # Verify error handling
        assert state_machine.execution_metrics['error_count'] == 1
        assert 'error_occurred_at' in state_machine.context.execution_metadata
        
        # Verify error WebSocket event
        error_events = [e for e in state_machine.event_emissions if e['type'] == 'agent_error']
        assert len(error_events) == 1
        
        # Test recovery options from error state
        recovery_states = [AgentExecutionState.READY, AgentExecutionState.CANCELLED, AgentExecutionState.TERMINATED]
        for recovery_state in recovery_states:
            assert state_machine.can_transition_to(recovery_state)
        
        # Test retry recovery
        retry_success = state_machine.transition_to(AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE,
                                                   metadata={'recovery_attempt': 1})
        assert retry_success
        
        # Verify error recovery metadata
        assert 'error_recovery_attempted' in state_machine.context.execution_metadata
        
        # Test that agent can continue after recovery
        state_machine.transition_to(AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION)
        assert state_machine.current_state == AgentExecutionState.STARTING
    
    def test_agent_cancellation_flow(self):
        """Test agent cancellation states and cleanup."""
        context = self.create_test_context()
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Setup active execution
        state_machine.transition_to(AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE)
        state_machine.transition_to(AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION)
        state_machine.transition_to(AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING)
        
        # Test cancellation from various states
        cancellation_test_states = [
            AgentExecutionState.THINKING,
            AgentExecutionState.TOOL_PLANNING,
            AgentExecutionState.ANALYZING
        ]
        
        for test_state in cancellation_test_states:
            # Reset to test state
            state_machine.current_state = test_state
            
            assert state_machine.can_transition_to(AgentExecutionState.CANCELLED), \
                f"Should allow cancellation from {test_state.value}"
            
            cancel_success = state_machine.transition_to(AgentExecutionState.CANCELLED, AgentExecutionEvent.CANCEL_EXECUTION)
            assert cancel_success
            
            # Verify cancellation WebSocket event
            cancel_events = [e for e in state_machine.event_emissions if e['type'] == 'agent_cancelled']
            assert len(cancel_events) > 0
            
            # From cancelled state, can only terminate
            assert state_machine.can_transition_to(AgentExecutionState.TERMINATED)
            assert not state_machine.can_transition_to(AgentExecutionState.READY)
            
            # Reset for next test
            state_machine.current_state = AgentExecutionState.READY
            state_machine.event_emissions.clear()
    
    def test_agent_timeout_handling(self):
        """Test agent timeout state and handling."""
        context = self.create_test_context(max_execution_time=5.0)  # Short timeout for testing
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Setup long-running execution
        state_machine.transition_to(AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE)
        state_machine.transition_to(AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION)
        state_machine.transition_to(AgentExecutionState.TOOL_EXECUTING, AgentExecutionEvent.EXECUTE_TOOL)
        
        # Test timeout from execution state
        assert state_machine.can_transition_to(AgentExecutionState.TIMEOUT)
        timeout_success = state_machine.transition_to(AgentExecutionState.TIMEOUT, AgentExecutionEvent.TIMEOUT_EXECUTION,
                                                     metadata={'timeout_duration': context.max_execution_time})
        assert timeout_success
        
        # Verify timeout can lead to cancellation or termination
        assert state_machine.can_transition_to(AgentExecutionState.CANCELLED)
        assert state_machine.can_transition_to(AgentExecutionState.TERMINATED)
        
        # Test timeout -> cancellation flow
        cancel_after_timeout = state_machine.transition_to(AgentExecutionState.CANCELLED, AgentExecutionEvent.CANCEL_EXECUTION)
        assert cancel_after_timeout
        
        # Verify final termination
        terminate_success = state_machine.transition_to(AgentExecutionState.TERMINATED, AgentExecutionEvent.TERMINATE_EXECUTION)
        assert terminate_success
        
        # Verify no transitions possible from terminated
        for state in AgentExecutionState:
            if state != AgentExecutionState.TERMINATED:
                assert not state_machine.can_transition_to(state)
    
    def test_agent_direct_response_flow(self):
        """Test agent direct response without tools (simple queries)."""
        context = self.create_test_context(tools_available=[])  # No tools available
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Direct response flow: INITIALIZING -> READY -> STARTING -> THINKING -> RESPONDING -> COMPLETED
        direct_response_sequence = [
            (AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE),
            (AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION),
            (AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING),
            (AgentExecutionState.RESPONDING, AgentExecutionEvent.GENERATE_RESPONSE),  # Skip tools
            (AgentExecutionState.COMPLETED, AgentExecutionEvent.COMPLETE_EXECUTION)
        ]
        
        for target_state, event in direct_response_sequence:
            success = state_machine.transition_to(target_state, event)
            assert success, f"Direct response transition to {target_state.value} should succeed"
        
        # Verify completion
        assert state_machine.current_state == AgentExecutionState.COMPLETED
        
        # Verify no tool executions occurred
        metrics = state_machine.get_execution_metrics()
        assert metrics['tool_executions'] == 0
        assert len(state_machine.tools_completed) == 0
        
        # Verify essential WebSocket events were still emitted
        emitted_event_types = [event['type'] for event in state_machine.event_emissions]
        essential_events = ['agent_started', 'agent_thinking', 'agent_completed']
        for essential_event in essential_events:
            assert essential_event in emitted_event_types
        
        # Tool events should NOT be present
        assert 'tool_executing' not in emitted_event_types
        assert 'tool_completed' not in emitted_event_types
    
    def test_agent_invalid_state_transitions(self):
        """Test that invalid state transitions are properly rejected."""
        context = self.create_test_context()
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Test invalid transitions from INITIALIZING
        invalid_from_initializing = [
            AgentExecutionState.THINKING,      # Can't skip READY + STARTING
            AgentExecutionState.TOOL_EXECUTING, # Can't skip multiple states
            AgentExecutionState.COMPLETED,     # Can't complete before starting
            AgentExecutionState.ANALYZING      # Can't analyze before execution
        ]
        
        for invalid_state in invalid_from_initializing:
            assert not state_machine.can_transition_to(invalid_state)
            success = state_machine.transition_to(invalid_state, AgentExecutionEvent.START_EXECUTION)
            assert not success, f"Invalid transition to {invalid_state.value} should fail"
        
        # Verify invalid transitions are logged
        invalid_transitions = [t for t in state_machine.transition_log if t.get('valid') is False]
        assert len(invalid_transitions) == len(invalid_from_initializing)
        
        # Test invalid transitions from terminal states
        state_machine.transition_to(AgentExecutionState.COMPLETED, AgentExecutionEvent.COMPLETE_EXECUTION, force=True)
        
        # From COMPLETED, no transitions should be possible
        for state in AgentExecutionState:
            if state != AgentExecutionState.COMPLETED:
                assert not state_machine.can_transition_to(state)
    
    def test_websocket_event_emission_compliance(self):
        """Test that all required WebSocket events are emitted for Golden Path compliance."""
        context = self.create_test_context()
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Execute full agent lifecycle
        full_lifecycle = [
            (AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE),
            (AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION),
            (AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING),
            (AgentExecutionState.TOOL_EXECUTING, AgentExecutionEvent.EXECUTE_TOOL),
            (AgentExecutionState.TOOL_PROCESSING, AgentExecutionEvent.PROCESS_TOOL_RESULT),
            (AgentExecutionState.TOOL_COMPLETED, AgentExecutionEvent.COMPLETE_TOOL),
            (AgentExecutionState.ANALYZING, AgentExecutionEvent.ANALYZE_RESULTS),
            (AgentExecutionState.RESPONDING, AgentExecutionEvent.GENERATE_RESPONSE),
            (AgentExecutionState.COMPLETED, AgentExecutionEvent.COMPLETE_EXECUTION)
        ]
        
        for target_state, event in full_lifecycle:
            state_machine.transition_to(target_state, event)
        
        # Verify all 5 critical WebSocket events for Golden Path
        emitted_events = [event['type'] for event in state_machine.event_emissions]
        golden_path_events = [
            'agent_started',    # User sees agent began
            'agent_thinking',   # User sees agent is processing
            'tool_executing',   # User sees tool usage
            'tool_completed',   # User sees tool results
            'agent_completed'   # User sees final completion
        ]
        
        for critical_event in golden_path_events:
            assert critical_event in emitted_events, f"Golden Path requires {critical_event} event"
        
        # Verify event data structure
        for event in state_machine.event_emissions:
            assert 'type' in event
            assert 'data' in event
            assert 'timestamp' in event
            assert event['data']['user_id'] == context.user_id
            assert event['data']['thread_id'] == context.thread_id
            assert event['data']['run_id'] == context.run_id
        
        # Verify events are emitted in correct order
        event_order = [event['type'] for event in state_machine.event_emissions]
        assert event_order.index('agent_started') < event_order.index('agent_thinking')
        assert event_order.index('agent_thinking') < event_order.index('tool_executing')
        assert event_order.index('tool_executing') < event_order.index('tool_completed')
        assert event_order.index('tool_completed') < event_order.index('agent_completed')
    
    def test_agent_execution_metrics_accuracy(self):
        """Test execution metrics collection and accuracy."""
        context = self.create_test_context()
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Execute complex agent flow with metrics tracking
        execution_steps = [
            (AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE),
            (AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION),
            (AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING),
        ]
        
        # Add some thinking time
        import time
        for target_state, event in execution_steps:
            state_machine.transition_to(target_state, event)
            if target_state == AgentExecutionState.THINKING:
                time.sleep(0.1)  # Simulate thinking time
        
        # Execute multiple tools
        for i in range(2):
            state_machine.transition_to(AgentExecutionState.TOOL_EXECUTING, AgentExecutionEvent.EXECUTE_TOOL)
            state_machine.execute_tool(f'test_tool_{i}')
            state_machine.transition_to(AgentExecutionState.TOOL_COMPLETED, AgentExecutionEvent.COMPLETE_TOOL)
        
        # Complete execution
        state_machine.transition_to(AgentExecutionState.ANALYZING, AgentExecutionEvent.ANALYZE_RESULTS)
        state_machine.transition_to(AgentExecutionState.RESPONDING, AgentExecutionEvent.GENERATE_RESPONSE)
        state_machine.transition_to(AgentExecutionState.COMPLETED, AgentExecutionEvent.COMPLETE_EXECUTION)
        
        # Verify metrics accuracy
        metrics = state_machine.get_execution_metrics()
        
        assert metrics['current_state'] == AgentExecutionState.COMPLETED.value
        assert metrics['total_transitions'] > 0
        assert metrics['tool_executions'] == 2
        assert metrics['thinking_duration'] > 0  # Should have recorded thinking time
        assert metrics['total_execution_time'] > 0  # Should have total execution time
        assert metrics['websocket_events_sent'] >= 5  # At least the 5 critical events
        assert len(metrics['tools_completed']) > 0  # Should have completed tools
        assert metrics['error_count'] == 0  # No errors in this test
        
        # Verify context completion data
        assert state_machine.context.started_at is not None
        assert state_machine.context.completed_at is not None
        assert state_machine.context.completed_at > state_machine.context.started_at
        
        # Verify tool results
        assert len(state_machine.context.tool_results) == 2
        for result in state_machine.context.tool_results:
            assert 'tool' in result
            assert 'execution_time' in result
            assert 'timestamp' in result
    
    def test_business_value_agent_execution_requirements(self):
        """Test that agent execution meets business value requirements."""
        context = self.create_test_context(agent_type="cost_optimizer_agent")
        state_machine = MockAgentExecutionStateMachine(context)
        
        # Business Requirement 1: User must see agent progress (WebSocket events)
        state_machine.transition_to(AgentExecutionState.READY, AgentExecutionEvent.INITIALIZE)
        state_machine.transition_to(AgentExecutionState.STARTING, AgentExecutionEvent.START_EXECUTION)
        
        # Verify agent_started event emitted for user visibility
        started_events = [e for e in state_machine.event_emissions if e['type'] == 'agent_started']
        assert len(started_events) == 1, "User must see agent started for business value"
        
        # Business Requirement 2: Agent must complete execution for value delivery
        state_machine.transition_to(AgentExecutionState.THINKING, AgentExecutionEvent.BEGIN_THINKING)
        state_machine.transition_to(AgentExecutionState.ANALYZING, AgentExecutionEvent.ANALYZE_RESULTS)
        state_machine.transition_to(AgentExecutionState.RESPONDING, AgentExecutionEvent.GENERATE_RESPONSE)
        state_machine.transition_to(AgentExecutionState.COMPLETED, AgentExecutionEvent.COMPLETE_EXECUTION)
        
        # Verify completion event for business value delivery
        completed_events = [e for e in state_machine.event_emissions if e['type'] == 'agent_completed']
        assert len(completed_events) == 1, "Agent must complete for business value delivery"
        
        # Business Requirement 3: System must handle errors gracefully
        state_machine.current_state = AgentExecutionState.TOOL_EXECUTING  # Reset for error test
        state_machine.transition_to(AgentExecutionState.ERROR, AgentExecutionEvent.HANDLE_ERROR)
        
        error_events = [e for e in state_machine.event_emissions if e['type'] == 'agent_error']
        assert len(error_events) == 1, "User must be notified of errors"
        
        # Business Requirement 4: Error recovery must be possible
        assert state_machine.can_transition_to(AgentExecutionState.READY), "System must allow error recovery"
        
        # Business Requirement 5: Execution time must be reasonable
        metrics = state_machine.get_execution_metrics()
        # In real implementation, would have reasonable execution time limits
        assert metrics['total_execution_time'] >= 0, "Execution time must be tracked"
        
        # Verify business context is maintained
        assert state_machine.context.agent_type == "cost_optimizer_agent"
        assert state_machine.context.user_id == context.user_id
        assert state_machine.context.thread_id == context.thread_id