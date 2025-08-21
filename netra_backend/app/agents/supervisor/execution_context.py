"""Execution context and result types for supervisor agent."""

from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from netra_backend.app.agents.state import DeepAgentState


# Import ExecutionStrategy from the authoritative source for compatibility
from netra_backend.app.core.interfaces_execution import ExecutionStrategy


class AgentExecutionStrategy(Enum):
    """Execution strategies for agent pipelines"""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


@dataclass
class AgentExecutionContext:
    """Context for agent execution"""
    run_id: str
    thread_id: str
    user_id: str
    agent_name: str
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgentExecutionResult:
    """Result of agent execution"""
    success: bool
    state: Optional[DeepAgentState] = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineStep:
    """Represents a step in an execution pipeline"""
    agent_name: str
    strategy: AgentExecutionStrategy = AgentExecutionStrategy.SEQUENTIAL
    condition: Optional[callable] = None
    dependencies: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)