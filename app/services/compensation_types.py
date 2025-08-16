"""
Compensation engine types and data models.
Defines core types, states, and data structures for compensation operations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable


class CompensationState(Enum):
    """States of compensation operations."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SagaState(Enum):
    """States of saga execution."""
    RUNNING = "running"
    COMPENSATING = "compensating"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class CompensationAction:
    """Represents a compensation action for a failed operation."""
    action_id: str
    operation_id: str
    action_type: str
    compensation_data: Dict[str, Any]
    handler: Callable[..., Awaitable[bool]]
    state: CompensationState = CompensationState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0


@dataclass
class SagaStep:
    """Represents a step in a saga transaction."""
    step_id: str
    operation: Callable[..., Awaitable[Any]]
    compensation: Optional[CompensationAction] = None
    dependencies: List[str] = field(default_factory=list)
    timeout: Optional[timedelta] = None
    retry_policy: Optional[Dict[str, Any]] = None
    critical: bool = False


@dataclass
class Saga:
    """Represents a complete saga transaction."""
    saga_id: str
    name: str
    steps: List[SagaStep] = field(default_factory=list)
    state: SagaState = SagaState.RUNNING
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    current_step: Optional[str] = None
    failed_step: Optional[str] = None
    compensation_actions: List[CompensationAction] = field(default_factory=list)
    
    def add_step(self, step: SagaStep) -> None:
        """Add a step to the saga."""
        self.steps.append(step)
    
    def get_step(self, step_id: str) -> Optional[SagaStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.step_id == step_id:
                return step
        return None
    
    def get_completed_steps(self) -> List[SagaStep]:
        """Get list of completed steps."""
        if not self.current_step:
            return []
        
        completed = []
        for step in self.steps:
            if step.step_id == self.current_step:
                break
            completed.append(step)
        return completed
    
    def get_pending_steps(self) -> List[SagaStep]:
        """Get list of pending steps."""
        if not self.current_step:
            return self.steps.copy()
        
        pending = []
        found_current = False
        for step in self.steps:
            if step.step_id == self.current_step:
                found_current = True
                continue
            if found_current:
                pending.append(step)
        return pending


def create_compensation_action(
    operation_id: str,
    action_type: str,
    compensation_data: Dict[str, Any],
    handler: Callable[..., Awaitable[bool]]
) -> CompensationAction:
    """Create a new compensation action."""
    return CompensationAction(
        action_id=f"comp_{operation_id}_{action_type}",
        operation_id=operation_id,
        action_type=action_type,
        compensation_data=compensation_data,
        handler=handler
    )


def create_saga_step(
    step_id: str,
    operation: Callable[..., Awaitable[Any]],
    compensation_handler: Optional[Callable[..., Awaitable[bool]]] = None,
    compensation_data: Optional[Dict[str, Any]] = None,
    dependencies: Optional[List[str]] = None,
    timeout_seconds: Optional[int] = None,
    critical: bool = False
) -> SagaStep:
    """Create a new saga step."""
    compensation = None
    if compensation_handler and compensation_data:
        compensation = create_compensation_action(
            operation_id=step_id,
            action_type="step_compensation",
            compensation_data=compensation_data,
            handler=compensation_handler
        )
    
    timeout = timedelta(seconds=timeout_seconds) if timeout_seconds else None
    
    return SagaStep(
        step_id=step_id,
        operation=operation,
        compensation=compensation,
        dependencies=dependencies or [],
        timeout=timeout,
        critical=critical
    )


def create_saga(saga_name: str, context: Optional[Dict[str, Any]] = None) -> Saga:
    """Create a new saga transaction."""
    return Saga(
        saga_id=f"saga_{saga_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        name=saga_name,
        context=context or {}
    )