"""Adaptive Budget Controller - Main orchestrator for adaptive budget management."""

from typing import Dict, List, Optional, Union, Any
import logging
from .budget_manager import TokenBudgetManager
from .adaptive_models import (
    AdaptiveConfig, ExecutionState, ExecutionResult, ExecutionPlan,
    CheckpointResult, RestartDecision, RestartContext, TodoItem
)
from .proactive_planner import ProactivePlanner
from .quarter_manager import QuarterManager
from .safe_restart import SafeRestartManager
from .trend_analyzer import BudgetTrendAnalyzer


logger = logging.getLogger(__name__)


class AdaptiveBudgetController(TokenBudgetManager):
    """
    Main orchestrator for adaptive budget management with percentage-based triggers.
    Extends TokenBudgetManager to provide adaptive execution with checkpoints and restarts.
    """

    def __init__(self, total_budget: Union[int, float],
                 adaptive_mode: bool = True,
                 enforcement_mode: str = "warn",
                 restart_threshold: float = 0.9,
                 checkpoint_intervals: Optional[List[float]] = None,
                 min_completion_probability: float = 0.5,
                 config: Optional[AdaptiveConfig] = None):
        """
        Initialize the adaptive budget controller.

        Args:
            total_budget: Total budget for execution
            adaptive_mode: Enable adaptive features
            enforcement_mode: Budget enforcement mode ("warn" or "block")
            restart_threshold: Usage threshold to trigger restart consideration
            checkpoint_intervals: List of checkpoints for evaluation (default: [0.25, 0.5, 0.75, 1.0])
            min_completion_probability: Minimum acceptable completion probability
            config: Adaptive configuration object
        """
        super().__init__(overall_budget=total_budget, enforcement_mode=enforcement_mode)

        self.config = config or AdaptiveConfig()
        self.adaptive_mode = adaptive_mode and self.config.enabled
        self.restart_threshold = config.restart_threshold if config else restart_threshold
        self.checkpoint_intervals = checkpoint_intervals or self.config.checkpoint_intervals
        self.min_completion_probability = config.min_completion_probability if config else min_completion_probability
        self.total_budget = float(total_budget)

        # Initialize components
        self.quarter_manager = QuarterManager(self.total_budget, self.config)
        self.proactive_planner = ProactivePlanner(self.config)
        self.safe_restart_manager = SafeRestartManager(self.config)
        self.trend_analyzer = BudgetTrendAnalyzer(self.config)

        # Execution state
        self.execution_history: List[ExecutionState] = []
        self._processed_checkpoints: set = set()
        self.restart_count = 0

        logger.info(f"AdaptiveBudgetController initialized with budget {total_budget}, "
                   f"adaptive_mode={adaptive_mode}, enforcement_mode={enforcement_mode}")

    def execute_adaptive_command(self, command: str, context: dict) -> ExecutionResult:
        """
        Main execution method showing integration with SafeRestartManager infrastructure.

        Phase 1: Pre-execution setup with guaranteed safe restart points
        Phase 2: Execute todos with checkpoint interval monitoring
        """
        if not self.adaptive_mode:
            # Fall back to standard budget management
            return self.execute_standard_command(command, context)

        try:
            # PHASE 1: Pre-execution setup
            execution_plan = self.proactive_planner.create_execution_plan(
                command, context, self.total_budget
            )

            restart_plan = self.safe_restart_manager.create_precomputed_restart_plan(
                execution_plan.todos
            )

            # Validate that safe restart points are guaranteed
            if not self.safe_restart_manager.validate_restart_plan_has_guaranteed_points():
                logger.warning("No guaranteed safe restart points available, falling back to standard execution")
                return self.execute_standard_command(command, context)

            # PHASE 2: Execute todos with checkpoint interval monitoring
            execution_state = ExecutionState(
                todos=execution_plan.todos,
                quarter_plans=execution_plan.quarter_distribution
            )

            return self.execute_todos_with_checkpoints(execution_state)

        except Exception as e:
            logger.error(f"Adaptive execution failed: {e}")
            if self.config.fallback_to_standard:
                return self.execute_standard_command(command, context)
            raise

    def execute_todos_with_checkpoints(self, execution_state: ExecutionState) -> ExecutionResult:
        """Execute todos with checkpoint monitoring and restart capability."""
        for todo in execution_state.todos:
            # Execute todo
            todo_result = self.execute_todo(todo)
            execution_state.record_todo_completion(todo, todo_result)

            # Update usage and check checkpoint intervals
            current_usage_percentage = execution_state.total_usage / self.total_budget

            # Check if any checkpoint interval has been reached
            if self.should_trigger_evaluation(current_usage_percentage, self.checkpoint_intervals):
                checkpoint_result = self.process_checkpoint(execution_state, current_usage_percentage)

                if checkpoint_result.restart_recommended:
                    # Use SafeRestartManager to find best restart point and capture context
                    restart_point = self.safe_restart_manager.get_best_available_restart_point(execution_state)
                    if restart_point:
                        restart_context = self.safe_restart_manager.capture_restart_context(
                            execution_state, restart_point
                        )

                        # Execute restart with preserved context
                        return self.execute_restart(restart_context)

        return ExecutionResult(
            success=True,
            todos_completed=execution_state.completed_todos,
            total_tokens_used=int(execution_state.total_usage)
        )

    def execute_todo(self, todo: TodoItem) -> Any:
        """Execute a single todo item. This would integrate with actual command execution."""
        # This is a placeholder for the actual todo execution logic
        # In the real implementation, this would call the appropriate tools/agents
        logger.info(f"Executing todo: {todo.description}")

        # Simulate execution with some token usage
        simulated_usage = todo.estimated_tokens * (0.8 + 0.4 * hash(todo.todo_id) % 100 / 100)
        todo.actual_tokens = int(simulated_usage)
        todo.status = "completed"

        # Record usage in parent budget manager
        self.record_usage("adaptive_execution", todo.actual_tokens)

        return {"tokens_used": todo.actual_tokens, "success": True}

    def process_checkpoint(self, execution_state: ExecutionState, usage_percentage: float) -> CheckpointResult:
        """Process checkpoint evaluation at quarter boundaries."""
        # Identify and mark checkpoint
        current_checkpoint = self.get_next_checkpoint(usage_percentage, self.checkpoint_intervals)
        if current_checkpoint:
            self.mark_checkpoint_processed(current_checkpoint)
            logger.info(f"Processing checkpoint at {current_checkpoint:.1%} usage")

        # Update runtime safe restart points
        self.safe_restart_manager.update_runtime_safe_points(execution_state)

        # Convert fractional checkpoint to quarter index for trend analyzer
        current_quarter = self.checkpoint_to_quarter_index(current_checkpoint, self.checkpoint_intervals)

        # Analyze trends and redistribute todos
        trend_analysis = self.trend_analyzer.analyze_usage_trend(
            current_quarter,
            execution_state.planned_budget_for_checkpoint(current_checkpoint, self.checkpoint_intervals),
            execution_state.actual_usage,
            execution_state.completed_todos,
            execution_state.remaining_todos
        )

        # Redistribute remaining todos across remaining quarters
        updated_quarter_plans = self.trend_analyzer.update_quarter_allocations(
            execution_state.quarter_plans,
            current_quarter,
            trend_analysis
        )

        # Apply the updated quarter plans
        execution_state.update_quarter_plans(updated_quarter_plans)

        # Evaluate restart conditions
        restart_recommended = self.evaluate_restart_conditions(
            usage_percentage,
            trend_analysis.completion_probability
        )

        return CheckpointResult(
            checkpoint=current_checkpoint,
            trend_analysis=trend_analysis,
            restart_recommended=restart_recommended,
            updated_quarter_plans=updated_quarter_plans
        )

    def checkpoint_to_quarter_index(self, checkpoint: Optional[float], checkpoint_intervals: List[float]) -> int:
        """
        Convert fractional checkpoint to quarter index based on configured intervals.
        Handles arbitrary checkpoint intervals, not just 0.25/0.5/0.75/1.0.
        """
        if not checkpoint or not checkpoint_intervals:
            return 4  # Default fallback

        sorted_intervals = sorted(checkpoint_intervals)

        # Find which quarter this checkpoint represents
        for i, interval in enumerate(sorted_intervals):
            if checkpoint <= interval:
                return i + 1  # Return 1-based quarter index

        # If checkpoint is beyond all intervals, it's the final quarter
        return len(sorted_intervals)

    def should_trigger_evaluation(self, usage_percentage: float, checkpoint_intervals: List[float]) -> bool:
        """
        Determine if checkpoint evaluation should trigger based on configured intervals.
        Evaluations must run at EVERY quarter interval regardless of enforcement mode.
        """
        # Block mode supersedes adaptive behavior
        if self.enforcement_mode == "block":
            return False

        # Check if we've crossed any checkpoint interval
        for interval in checkpoint_intervals:
            if usage_percentage >= interval and not self.checkpoint_reached(interval):
                return True

        return False

    def checkpoint_reached(self, interval: float) -> bool:
        """Track which checkpoint intervals have already been processed."""
        return interval in self._processed_checkpoints

    def mark_checkpoint_processed(self, interval: float):
        """Mark a checkpoint interval as processed."""
        self._processed_checkpoints.add(interval)

    def get_next_checkpoint(self, usage_percentage: float, checkpoint_intervals: List[float]) -> Optional[float]:
        """Get the next unprocessed checkpoint that should trigger evaluation."""
        for interval in sorted(checkpoint_intervals):
            if interval not in self._processed_checkpoints and usage_percentage >= interval:
                return interval
        return None

    def evaluate_restart_conditions(self, usage_percentage: float, completion_probability: float) -> bool:
        """
        Restart logic following exact conditions:
        1. Block mode supersedes everything (no restart)
        2. If completion_probability < 0.5, then BOTH conditions must be met:
           a) usage_percentage >= restart_threshold
           b) completion_probability < min_completion_probability
        """
        # Block mode prevents restart
        if self.enforcement_mode == "block":
            return False

        # Only consider restart when completion probability drops below threshold
        if completion_probability >= self.min_completion_probability:
            return False

        # Check restart count limit
        if self.restart_count >= self.config.max_restarts:
            logger.warning(f"Maximum restart count ({self.config.max_restarts}) reached")
            return False

        # BOTH conditions must be met for restart:
        usage_exceeds_threshold = usage_percentage >= self.restart_threshold
        probability_too_low = completion_probability < self.min_completion_probability

        if usage_exceeds_threshold and probability_too_low:
            logger.info(f"Restart conditions met: usage={usage_percentage:.1%}, "
                       f"probability={completion_probability:.1%}")
            return True

        return False

    def execute_restart(self, restart_context: RestartContext) -> ExecutionResult:
        """Execute restart with preserved context."""
        self.restart_count += 1
        logger.info(f"Executing restart #{self.restart_count} from {restart_context.restart_point.reason}")

        # Prepare fresh session with context
        session_prep = self.safe_restart_manager.prepare_restart_session(restart_context)

        # Create new execution state with remaining todos and lessons learned
        fresh_state = ExecutionState(
            todos=restart_context.remaining_todos,
            context_data=restart_context.preserved_data
        )

        # Apply lessons learned to todo estimates
        for todo in fresh_state.todos:
            # Apply estimation adjustments from lessons
            adjustments = restart_context.recommended_approach.get('estimation_adjustments', {})
            category_adjustment = adjustments.get(todo.category.value, 1.0)
            todo.estimated_tokens = int(todo.estimated_tokens * category_adjustment)

        # Update quarter plans with fresh allocations
        fresh_quarter_plans = {}
        for quarter, budget in session_prep.initial_budget_allocation.items():
            from .adaptive_models import QuarterPlan
            fresh_quarter_plans[quarter] = QuarterPlan(allocated_budget=budget)

        fresh_state.quarter_plans = fresh_quarter_plans

        # Execute with fresh context
        try:
            result = self.execute_todos_with_checkpoints(fresh_state)
            result.restart_occurred = True
            result.restart_context = restart_context
            return result
        except Exception as e:
            logger.error(f"Restart execution failed: {e}")
            # Return partial results
            return ExecutionResult(
                success=False,
                todos_completed=fresh_state.completed_todos,
                total_tokens_used=int(fresh_state.total_usage),
                restart_occurred=True,
                restart_context=restart_context
            )

    def execute_standard_command(self, command: str, context: dict) -> ExecutionResult:
        """Execute command using standard budget management (fallback)."""
        logger.info("Executing with standard budget management")

        # This would integrate with the existing command execution system
        # For now, return a simple result
        return ExecutionResult(
            success=True,
            todos_completed=[],
            total_tokens_used=0
        )

    def get_execution_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics about adaptive execution."""
        return {
            'total_budget': self.total_budget,
            'total_usage': self.total_usage,
            'usage_percentage': (self.total_usage / self.total_budget * 100) if self.total_budget > 0 else 0,
            'adaptive_mode': self.adaptive_mode,
            'enforcement_mode': self.enforcement_mode,
            'restart_count': self.restart_count,
            'processed_checkpoints': list(self._processed_checkpoints),
            'checkpoint_intervals': self.checkpoint_intervals,
            'quarter_statistics': self.quarter_manager.get_quarter_statistics(),
            'trend_summary': self.trend_analyzer.get_trend_summary()
        }

    def reset_for_new_session(self):
        """Reset state for a new execution session."""
        self._processed_checkpoints.clear()
        self.restart_count = 0
        self.execution_history.clear()
        self.total_usage = 0
        logger.info("AdaptiveBudgetController reset for new session")

    def validate_configuration(self) -> List[str]:
        """Validate the current configuration and return any issues."""
        issues = []

        # Check enforcement mode compatibility
        if self.enforcement_mode == "block" and self.adaptive_mode:
            issues.append("Block enforcement mode is incompatible with adaptive features")

        # Check checkpoint intervals
        if not self.checkpoint_intervals or len(self.checkpoint_intervals) == 0:
            issues.append("No checkpoint intervals configured")

        for interval in self.checkpoint_intervals:
            if not (0 < interval <= 1.0):
                issues.append(f"Invalid checkpoint interval: {interval} (must be between 0 and 1)")

        # Check restart threshold
        if not (0 < self.restart_threshold <= 1.0):
            issues.append(f"Invalid restart threshold: {self.restart_threshold} (must be between 0 and 1)")

        # Check completion probability threshold
        if not (0 < self.min_completion_probability <= 1.0):
            issues.append(f"Invalid completion probability threshold: {self.min_completion_probability}")

        # Validate quarter manager
        quarter_issues = self.quarter_manager.validate_quarter_allocation()
        issues.extend(quarter_issues)

        return issues

    def optimize_configuration(self) -> AdaptiveConfig:
        """Optimize configuration based on historical performance."""
        # This would analyze historical data to suggest optimal settings
        # For now, return current config
        return self.config

    @property
    def is_adaptive_mode(self) -> bool:
        """Check if adaptive mode is enabled and compatible."""
        return self.adaptive_mode and self.enforcement_mode != "block"

    def __str__(self) -> str:
        return f"AdaptiveBudgetController(budget={self.total_budget}, mode={self.enforcement_mode}, adaptive={self.adaptive_mode})"

    def __repr__(self) -> str:
        return self.__str__()