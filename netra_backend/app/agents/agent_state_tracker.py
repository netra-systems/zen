"""Agent State Tracker for explicit execution phase tracking.

This module provides comprehensive state tracking for agent execution phases
to enable better monitoring, debugging, and user feedback.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Stability & Transparency
- Value Impact: Enables real-time visibility into agent execution phases for debugging and user feedback
- Strategic Impact: Improves user experience by providing clear progress indication and failure diagnosis

Key Features:
- Explicit tracking of agent execution phases
- State transition validation
- WebSocket event emission for state changes
- Execution bottleneck detection
- Progress reporting with timestamps
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class AgentExecutionPhase(Enum):
    """Explicit phases of agent execution for comprehensive tracking."""
    # Initialization phases
    CREATED = "created"
    WEBSOCKET_SETUP = "websocket_setup"
    CONTEXT_VALIDATION = "context_validation"
    
    # Execution phases
    STARTING = "starting"
    THINKING = "thinking"
    TOOL_PREPARATION = "tool_preparation"
    LLM_INTERACTION = "llm_interaction"
    TOOL_EXECUTION = "tool_execution"
    RESULT_PROCESSING = "result_processing"
    
    # Completion phases
    COMPLETING = "completing"
    COMPLETED = "completed"
    
    # Error phases
    TIMEOUT = "timeout"
    FAILED = "failed"
    CIRCUIT_BREAKER_OPEN = "circuit_breaker_open"


@dataclass
class PhaseTransition:
    """Records a transition between execution phases."""
    from_phase: Optional[AgentExecutionPhase]
    to_phase: AgentExecutionPhase
    timestamp: datetime
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    websocket_event_sent: bool = False


@dataclass
class AgentExecutionState:
    """Complete state tracking for an agent execution."""
    agent_name: str
    run_id: str
    user_id: str
    current_phase: AgentExecutionPhase
    start_time: datetime
    last_update: datetime
    phase_history: List[PhaseTransition] = field(default_factory=list)
    execution_metadata: Dict[str, Any] = field(default_factory=dict)
    warning_count: int = 0
    error_count: int = 0
    
    def get_total_duration_ms(self) -> float:
        """Get total execution duration in milliseconds."""
        current_time = datetime.now(timezone.utc)
        return (current_time - self.start_time).total_seconds() * 1000
    
    def get_phase_duration_ms(self, phase: AgentExecutionPhase) -> float:
        """Get duration spent in a specific phase."""
        total_duration = 0.0
        for transition in self.phase_history:
            if transition.to_phase == phase:
                total_duration += transition.duration_ms
        return total_duration
    
    def get_current_phase_duration_ms(self) -> float:
        """Get duration of current phase."""
        if not self.phase_history:
            return self.get_total_duration_ms()
        
        last_transition = self.phase_history[-1]
        current_time = datetime.now(timezone.utc)
        return (current_time - last_transition.timestamp).total_seconds() * 1000


class AgentStateTracker:
    """Comprehensive agent state tracking with WebSocket integration."""
    
    def __init__(self):
        self.active_executions: Dict[str, AgentExecutionState] = {}
        self.completed_executions: List[AgentExecutionState] = []
        self.max_completed_history = 100
        
        # Phase transition rules for validation
        self.valid_transitions = {
            None: [AgentExecutionPhase.CREATED],
            AgentExecutionPhase.CREATED: [
                AgentExecutionPhase.WEBSOCKET_SETUP,
                AgentExecutionPhase.FAILED
            ],
            AgentExecutionPhase.WEBSOCKET_SETUP: [
                AgentExecutionPhase.CONTEXT_VALIDATION,
                AgentExecutionPhase.FAILED
            ],
            AgentExecutionPhase.CONTEXT_VALIDATION: [
                AgentExecutionPhase.STARTING,
                AgentExecutionPhase.FAILED
            ],
            AgentExecutionPhase.STARTING: [
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.THINKING: [
                AgentExecutionPhase.TOOL_PREPARATION,
                AgentExecutionPhase.LLM_INTERACTION,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.TOOL_PREPARATION: [
                AgentExecutionPhase.TOOL_EXECUTION,
                AgentExecutionPhase.LLM_INTERACTION,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.LLM_INTERACTION: [
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.TOOL_EXECUTION,
                AgentExecutionPhase.RESULT_PROCESSING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT,
                AgentExecutionPhase.CIRCUIT_BREAKER_OPEN
            ],
            AgentExecutionPhase.TOOL_EXECUTION: [
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.LLM_INTERACTION,
                AgentExecutionPhase.RESULT_PROCESSING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.RESULT_PROCESSING: [
                AgentExecutionPhase.COMPLETING,
                AgentExecutionPhase.THINKING,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ],
            AgentExecutionPhase.COMPLETING: [
                AgentExecutionPhase.COMPLETED,
                AgentExecutionPhase.FAILED,
                AgentExecutionPhase.TIMEOUT
            ]
        }
        
        logger.info("Agent State Tracker initialized")
    
    def start_execution(
        self, 
        agent_name: str, 
        run_id: str, 
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Start tracking a new agent execution.
        
        Args:
            agent_name: Name of the agent
            run_id: Execution run ID
            user_id: User ID for isolation
            metadata: Optional execution metadata
            
        Returns:
            Execution ID for tracking
        """
        execution_id = f"{agent_name}_{run_id}_{int(time.time() * 1000)}"
        start_time = datetime.now(timezone.utc)
        
        state = AgentExecutionState(
            agent_name=agent_name,
            run_id=run_id,
            user_id=user_id,
            current_phase=AgentExecutionPhase.CREATED,
            start_time=start_time,
            last_update=start_time,
            execution_metadata=metadata or {}
        )
        
        self.active_executions[execution_id] = state
        
        logger.info(f"🎬 Started execution tracking: {execution_id} ({agent_name})")
        return execution_id
    
    async def transition_phase(
        self, 
        execution_id: str, 
        new_phase: AgentExecutionPhase,
        metadata: Optional[Dict[str, Any]] = None,
        websocket_manager: Optional[Any] = None
    ) -> bool:
        """Transition agent to a new execution phase.
        
        Args:
            execution_id: Execution ID
            new_phase: New phase to transition to
            metadata: Optional metadata for the transition
            websocket_manager: Optional WebSocket manager for event emission
            
        Returns:
            True if transition was successful, False if invalid
        """
        if execution_id not in self.active_executions:
            logger.error(f"❌ Unknown execution ID: {execution_id}")
            return False
        
        state = self.active_executions[execution_id]
        current_time = datetime.now(timezone.utc)
        
        # Validate transition
        valid_next_phases = self.valid_transitions.get(state.current_phase, [])
        if new_phase not in valid_next_phases:
            logger.warning(
                f"⚠️ Invalid phase transition for {execution_id}: "
                f"{state.current_phase} -> {new_phase}. "
                f"Valid transitions: {valid_next_phases}"
            )
            # Allow the transition but log as warning
        
        # Calculate duration of previous phase
        duration_ms = (current_time - state.last_update).total_seconds() * 1000
        
        # Create transition record
        transition = PhaseTransition(
            from_phase=state.current_phase,
            to_phase=new_phase,
            timestamp=current_time,
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        # Update state
        state.current_phase = new_phase
        state.last_update = current_time
        state.phase_history.append(transition)
        
        # Emit WebSocket event if manager available
        websocket_event_sent = False
        if websocket_manager:
            try:
                await self._emit_phase_event(state, transition, websocket_manager)
                transition.websocket_event_sent = True
                websocket_event_sent = True
            except Exception as e:
                logger.error(f"Failed to emit WebSocket event for phase transition: {e}")
        
        logger.info(
            f"📈 Phase transition {execution_id}: {transition.from_phase} -> {new_phase} "
            f"(duration: {duration_ms:.1f}ms, websocket: {websocket_event_sent})"
        )
        
        return True
    
    async def _emit_phase_event(
        self, 
        state: AgentExecutionState, 
        transition: PhaseTransition,
        websocket_manager: Any
    ) -> None:
        """Emit WebSocket event for phase transition."""
        # Map phases to appropriate WebSocket events
        phase_to_event = {
            AgentExecutionPhase.STARTING: ("agent_started", "Agent is starting execution"),
            AgentExecutionPhase.THINKING: ("agent_thinking", f"Agent is thinking... (step {len(state.phase_history)})"),
            AgentExecutionPhase.TOOL_PREPARATION: ("agent_thinking", "Preparing tools for execution..."),
            AgentExecutionPhase.LLM_INTERACTION: ("agent_thinking", "Interacting with AI language model..."),
            AgentExecutionPhase.TOOL_EXECUTION: ("tool_executing", "Executing tools..."),
            AgentExecutionPhase.RESULT_PROCESSING: ("agent_thinking", "Processing results..."),
            AgentExecutionPhase.COMPLETING: ("agent_thinking", "Finalizing response..."),
            AgentExecutionPhase.COMPLETED: ("agent_completed", "Agent execution completed successfully"),
            AgentExecutionPhase.FAILED: ("agent_error", "Agent execution failed"),
            AgentExecutionPhase.TIMEOUT: ("agent_error", "Agent execution timed out"),
            AgentExecutionPhase.CIRCUIT_BREAKER_OPEN: ("agent_error", "Service temporarily unavailable")
        }
        
        event_info = phase_to_event.get(transition.to_phase)
        if not event_info:
            return
        
        event_type, message = event_info
        
        try:
            if event_type == "agent_started":
                await websocket_manager.notify_agent_started(
                    run_id=state.run_id,
                    agent_name=state.agent_name,
                    context={
                        "phase": transition.to_phase.value,
                        "total_duration_ms": state.get_total_duration_ms(),
                        "metadata": transition.metadata
                    }
                )
            elif event_type == "agent_thinking":
                await websocket_manager.notify_agent_thinking(
                    run_id=state.run_id,
                    agent_name=state.agent_name,
                    reasoning=message,
                    step_number=len(state.phase_history)
                )
            elif event_type == "tool_executing":
                await websocket_manager.notify_tool_executing(
                    run_id=state.run_id,
                    agent_name=state.agent_name,
                    tool_name="execution_tools",
                    parameters=transition.metadata
                )
            elif event_type == "agent_completed":
                await websocket_manager.notify_agent_completed(
                    run_id=state.run_id,
                    agent_name=state.agent_name,
                    result={
                        "success": True,
                        "total_duration_ms": state.get_total_duration_ms(),
                        "phase_count": len(state.phase_history),
                        "warnings": state.warning_count,
                        "metadata": state.execution_metadata
                    },
                    execution_time_ms=int(state.get_total_duration_ms())
                )
            elif event_type == "agent_error":
                await websocket_manager.notify_agent_error(
                    run_id=state.run_id,
                    agent_name=state.agent_name,
                    error=message,
                    error_context={
                        "phase": transition.to_phase.value,
                        "total_duration_ms": state.get_total_duration_ms(),
                        "metadata": transition.metadata
                    }
                )
            
            logger.debug(f"📡 Emitted {event_type} event for {state.agent_name}")
            
        except Exception as e:
            logger.error(f"Failed to emit {event_type} event: {e}")
            raise
    
    def complete_execution(self, execution_id: str, success: bool = True) -> None:
        """Complete execution tracking.
        
        Args:
            execution_id: Execution ID
            success: Whether execution was successful
        """
        if execution_id not in self.active_executions:
            logger.error(f"❌ Unknown execution ID for completion: {execution_id}")
            return
        
        state = self.active_executions.pop(execution_id)
        
        # Final phase transition
        final_phase = AgentExecutionPhase.COMPLETED if success else AgentExecutionPhase.FAILED
        if state.current_phase != final_phase:
            current_time = datetime.now(timezone.utc)
            duration_ms = (current_time - state.last_update).total_seconds() * 1000
            
            transition = PhaseTransition(
                from_phase=state.current_phase,
                to_phase=final_phase,
                timestamp=current_time,
                duration_ms=duration_ms
            )
            
            state.current_phase = final_phase
            state.last_update = current_time
            state.phase_history.append(transition)
        
        # Add to completed history
        self.completed_executions.append(state)
        if len(self.completed_executions) > self.max_completed_history:
            self.completed_executions = self.completed_executions[-self.max_completed_history:]
        
        total_duration = state.get_total_duration_ms()
        logger.info(
            f"🏁 Completed execution tracking: {execution_id} "
            f"(success: {success}, duration: {total_duration:.1f}ms, phases: {len(state.phase_history)})"
        )
    
    def get_execution_state(self, execution_id: str) -> Optional[AgentExecutionState]:
        """Get current execution state."""
        return self.active_executions.get(execution_id)
    
    def get_active_executions(self) -> Dict[str, AgentExecutionState]:
        """Get all active executions."""
        return self.active_executions.copy()
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get execution summary statistics."""
        active_count = len(self.active_executions)
        completed_count = len(self.completed_executions)
        
        # Analyze phase distribution for active executions
        phase_distribution = {}
        for state in self.active_executions.values():
            phase = state.current_phase.value
            phase_distribution[phase] = phase_distribution.get(phase, 0) + 1
        
        # Analyze completed executions
        success_count = len([s for s in self.completed_executions if s.current_phase == AgentExecutionPhase.COMPLETED])
        failure_count = completed_count - success_count
        
        summary = {
            "active_executions": active_count,
            "completed_executions": completed_count,
            "success_rate": (success_count / completed_count * 100) if completed_count > 0 else 0,
            "phase_distribution": phase_distribution,
            "performance": {
                "success_count": success_count,
                "failure_count": failure_count
            }
        }
        
        if self.completed_executions:
            durations = [s.get_total_duration_ms() for s in self.completed_executions]
            summary["performance"]["avg_duration_ms"] = sum(durations) / len(durations)
            summary["performance"]["max_duration_ms"] = max(durations)
            summary["performance"]["min_duration_ms"] = min(durations)
        
        return summary
    
    def detect_stuck_executions(self, timeout_ms: float = 30000) -> List[str]:
        """Detect executions that appear to be stuck.
        
        Args:
            timeout_ms: Timeout threshold in milliseconds
            
        Returns:
            List of execution IDs that appear stuck
        """
        stuck_executions = []
        current_time = datetime.now(timezone.utc)
        
        for execution_id, state in self.active_executions.items():
            phase_duration = state.get_current_phase_duration_ms()
            if phase_duration > timeout_ms:
                stuck_executions.append(execution_id)
                logger.warning(
                    f"🐌 Detected stuck execution: {execution_id} "
                    f"(phase: {state.current_phase.value}, duration: {phase_duration:.1f}ms)"
                )
        
        return stuck_executions


# Global state tracker instance
_state_tracker: Optional[AgentStateTracker] = None


def get_agent_state_tracker() -> AgentStateTracker:
    """Get or create the global agent state tracker."""
    global _state_tracker
    if _state_tracker is None:
        _state_tracker = AgentStateTracker()
    return _state_tracker