"""Compensation models and types.

Contains all dataclasses, enums, and type definitions for compensation system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, List, Optional

from netra_backend.app.core.error_recovery import RecoveryContext


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
    executed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SagaStep:
    """Represents a step in a saga with forward and compensation actions."""
    step_id: str
    name: str
    forward_action: Callable[..., Awaitable[Any]]
    compensation_action: Callable[..., Awaitable[bool]]
    forward_params: Dict[str, Any] = field(default_factory=dict)
    compensation_params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    executed: bool = False
    compensated: bool = False
    error: Optional[str] = None


@dataclass
class Saga:
    """Represents a saga transaction with multiple steps."""
    saga_id: str
    name: str
    steps: List[SagaStep] = field(default_factory=list)
    state: SagaState = SagaState.RUNNING
    created_at: datetime = field(default_factory=datetime.now)
    timeout: timedelta = field(default_factory=lambda: timedelta(minutes=15))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if saga has expired."""
        return datetime.now() - self.created_at > self.timeout
    
    @property
    def executed_steps(self) -> List[SagaStep]:
        """Get all executed steps."""
        return [step for step in self.steps if step.executed]
    
    @property
    def failed_steps(self) -> List[SagaStep]:
        """Get all failed steps."""
        return [step for step in self.steps if step.error is not None]


class BaseCompensationHandler(ABC):
    """Abstract base class for compensation handlers."""
    
    @abstractmethod
    async def can_compensate(self, context: RecoveryContext) -> bool:
        """Check if this handler can compensate the given operation."""
        pass
    
    @abstractmethod
    async def execute_compensation(
        self,
        action: CompensationAction,
        context: RecoveryContext
    ) -> bool:
        """Execute the compensation action."""
        pass
    
    @abstractmethod
    def get_priority(self) -> int:
        """Get handler priority (lower number = higher priority)."""
        pass