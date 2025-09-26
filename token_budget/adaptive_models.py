"""Adaptive budget management data models."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import uuid
from datetime import datetime


class TodoCategory(Enum):
    """Categories for todo items to identify safe restart points."""
    SEARCH = "search"
    READ = "read"
    ANALYZE = "analyze"
    RESEARCH = "research"
    PLANNING = "planning"
    VALIDATION = "validation"
    PREPARATION = "preparation"
    WRITE = "write"
    MODIFY = "modify"
    DEPLOY = "deploy"
    DELETE = "delete"
    TEST = "test"
    SETUP = "setup"
    SPAWN = "spawn"
    MONITOR = "monitor"
    MERGE = "merge"


@dataclass
class TodoItem:
    """Individual task item for adaptive execution."""
    todo_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    category: TodoCategory = TodoCategory.ANALYZE
    estimated_tokens: int = 0
    actual_tokens: int = 0
    dependencies: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    agents: List[str] = field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    safe_restart_after: bool = False
    involves_tools: bool = False
    has_partial_state: bool = False
    outputs: Dict[str, Any] = field(default_factory=dict)
    intermediate_data: Dict[str, Any] = field(default_factory=dict)
    tools_used: List[str] = field(default_factory=list)
    completion_timestamp: Optional[datetime] = None
    success_factors: List[str] = field(default_factory=list)
    efficiency_rating: float = 1.0
    failure_reason: Optional[str] = None
    suggested_alternative: Optional[str] = None


@dataclass
class QuarterPlan:
    """Budget allocation and tasks for a quarter."""
    allocated_budget: float
    assigned_budget: float = 0
    todos: List[TodoItem] = field(default_factory=list)
    todo_budget_map: Dict[str, float] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """Complete execution plan with todo distribution."""
    todos: List[TodoItem]
    quarter_distribution: Dict[int, QuarterPlan]
    total_estimated_budget: float
    safe_restart_points: List[int] = field(default_factory=list)


@dataclass
class TrendAnalysis:
    """Analysis of usage trends and predictions."""
    usage_velocity: float  # tokens per todo item
    estimation_accuracy: float  # multiplier for estimates
    completion_probability: float  # 0.0 to 1.0
    recommended_reallocation: Dict[int, float] = field(default_factory=dict)


@dataclass
class ExecutionState:
    """Current state of adaptive execution."""
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    todos: List[TodoItem] = field(default_factory=list)
    completed_todos: List[TodoItem] = field(default_factory=list)
    failed_todos: List[TodoItem] = field(default_factory=list)
    current_todo_index: int = 0
    quarter_plans: Dict[int, QuarterPlan] = field(default_factory=dict)
    total_usage: float = 0
    actual_usage: float = 0
    budget_trend_analysis: Optional[TrendAnalysis] = None
    context_data: Dict[str, Any] = field(default_factory=dict)
    codebase_insights: Dict[str, Any] = field(default_factory=dict)
    discovered_patterns: List[str] = field(default_factory=list)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    search_indexes: Dict[str, Any] = field(default_factory=dict)

    @property
    def remaining_todos(self) -> List[TodoItem]:
        """Get todos that are not yet completed."""
        completed_ids = {todo.todo_id for todo in self.completed_todos}
        return [todo for todo in self.todos if todo.todo_id not in completed_ids]

    def record_todo_completion(self, todo: TodoItem, result: Any) -> None:
        """Record the completion of a todo item."""
        todo.status = "completed"
        todo.completion_timestamp = datetime.now()
        if hasattr(result, 'tokens_used'):
            todo.actual_tokens = result.tokens_used
        self.completed_todos.append(todo)
        self.total_usage += todo.actual_tokens

    def planned_budget_for_checkpoint(self, checkpoint: float) -> float:
        """Get planned budget usage at a checkpoint."""
        # Calculate based on quarter progression
        if checkpoint <= 0.25:
            return self.quarter_plans.get(1, QuarterPlan(0)).allocated_budget
        elif checkpoint <= 0.5:
            return sum(self.quarter_plans.get(i, QuarterPlan(0)).allocated_budget for i in [1, 2])
        elif checkpoint <= 0.75:
            return sum(self.quarter_plans.get(i, QuarterPlan(0)).allocated_budget for i in [1, 2, 3])
        else:
            return sum(plan.allocated_budget for plan in self.quarter_plans.values())

    def update_quarter_plans(self, updated_plans: Dict[int, QuarterPlan]) -> None:
        """Update quarter plans with rebalanced todos."""
        self.quarter_plans = updated_plans

    def get_tool_usage_patterns(self) -> Dict[str, float]:
        """Analyze tool usage efficiency patterns."""
        tool_efficiency = {}
        for todo in self.completed_todos:
            for tool in todo.tools_used:
                if tool not in tool_efficiency:
                    tool_efficiency[tool] = []
                # Calculate efficiency as ratio of estimated to actual tokens
                efficiency = todo.estimated_tokens / max(todo.actual_tokens, 1)
                tool_efficiency[tool].append(efficiency)

        # Average efficiency per tool
        return {tool: sum(efficiencies) / len(efficiencies)
                for tool, efficiencies in tool_efficiency.items()}

    def budget_waste_detected(self) -> bool:
        """Detect if significant budget waste patterns exist."""
        if not self.completed_todos:
            return False

        # Calculate overall estimation accuracy
        total_estimated = sum(todo.estimated_tokens for todo in self.completed_todos)
        total_actual = sum(todo.actual_tokens for todo in self.completed_todos)

        if total_estimated == 0:
            return False

        # If actual usage is more than 50% over estimates, consider it waste
        return (total_actual / total_estimated) > 1.5


@dataclass
class PlannedRestartPoint:
    """Pre-computed potential restart point."""
    todo_index: int
    trigger_condition: str  # 'completion', 'before_next', 'tool_completion', etc.
    reason: str
    context_to_preserve: List[str]
    state_corruption_risk: bool
    priority: int  # 1=highest, 4=lowest


@dataclass
class RestartPoint:
    """Actual safe restart point."""
    todo_index: int
    reason: str
    context_to_preserve: List[str]
    safe_to_restart: bool
    state_corruption_risk: bool = False
    availability_confirmed: bool = False


@dataclass
class RestartPlan:
    """Complete restart strategy."""
    planned_points: List[PlannedRestartPoint]
    guaranteed_safe_points: List[PlannedRestartPoint]
    fallback_points: List[PlannedRestartPoint]


@dataclass
class Lesson:
    """Lesson learned from execution."""
    category: str
    description: str
    adjustment_factor: Optional[float] = None
    todo_category: Optional[str] = None
    tool_name: Optional[str] = None
    efficiency_rating: Optional[float] = None
    recommendation: Optional[str] = None


@dataclass
class Mistake:
    """Mistake to avoid in future execution."""
    description: str
    todo_context: Optional[str] = None
    avoidance_strategy: Optional[str] = None


@dataclass
class RestartContext:
    """Complete context for restarting execution."""
    session_id: str
    restart_point: RestartPoint
    completed_todos: List[TodoItem]
    todo_results: Dict[str, Any]
    remaining_todos: List[TodoItem]
    lessons_learned: List[Lesson]
    mistakes_to_avoid: List[Mistake]
    successful_patterns: Dict[str, Any]
    preserved_data: Dict[str, Any]
    budget_analysis: Optional[TrendAnalysis]
    efficiency_insights: Dict[str, Any]
    recommended_approach: Dict[str, str]
    tool_usage_guidance: Dict[str, Any]
    estimated_remaining_budget: float


@dataclass
class CheckpointResult:
    """Result of checkpoint evaluation."""
    checkpoint: float
    trend_analysis: TrendAnalysis
    restart_recommended: bool
    updated_quarter_plans: Dict[int, QuarterPlan]


@dataclass
class RestartDecision:
    """Decision on whether to restart execution."""
    should_restart: bool
    reason: str
    restart_point: Optional[RestartPoint] = None
    restart_context: Optional[RestartContext] = None


@dataclass
class ExecutionResult:
    """Result of command execution."""
    success: bool
    todos_completed: List[TodoItem]
    total_tokens_used: int = 0
    restart_occurred: bool = False
    restart_context: Optional[RestartContext] = None


@dataclass
class SessionPreparation:
    """Preparation data for fresh session."""
    context_summary: str
    lessons_briefing: str
    mistakes_briefing: str
    remaining_work_plan: Dict[str, Any]
    initial_budget_allocation: Dict[int, float]


@dataclass
class AdaptiveConfig:
    """Configuration for adaptive budget management."""
    enabled: bool = True
    min_completion_probability: float = 0.5
    restart_threshold: float = 0.9
    checkpoint_intervals: List[float] = field(default_factory=lambda: [0.25, 0.5, 0.75, 1.0])
    quarter_buffer: float = 0.05
    todo_estimation_buffer: float = 0.1
    max_restarts: int = 2
    context_preservation: bool = True
    learn_from_mistakes: bool = True
    detailed_logging: bool = True
    safe_restart_only: bool = True
    proactive_planning: bool = True
    todo_dependency_analysis: bool = True
    quarter_rebalancing: bool = True
    respect_block_mode: bool = True
    fallback_to_standard: bool = True