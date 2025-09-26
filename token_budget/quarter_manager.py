"""Quarter-based budget management system."""

from typing import Dict, List, Optional
from .adaptive_models import QuarterPlan, TodoItem, AdaptiveConfig


class QuarterManager:
    """Manages budget distribution across quarters with dynamic reallocation."""

    def __init__(self, total_budget: float, config: Optional[AdaptiveConfig] = None):
        self.total_budget = total_budget
        self.config = config or AdaptiveConfig()
        self.current_quarter = 1
        self.quarter_plans: Dict[int, QuarterPlan] = {}
        self._initialize_quarters()

    def _initialize_quarters(self) -> None:
        """Initialize quarter plans based on checkpoint intervals."""
        # Use checkpoint intervals to determine number of segments/quarters
        intervals = sorted(self.config.checkpoint_intervals)
        num_segments = len(intervals)

        # Calculate budget per segment
        base_segment_budget = self.total_budget / num_segments
        buffer_per_segment = base_segment_budget * self.config.quarter_buffer

        for i in range(1, num_segments + 1):
            self.quarter_plans[i] = QuarterPlan(
                allocated_budget=base_segment_budget + buffer_per_segment
            )

    def get_quarter_plan(self, quarter: int) -> Optional[QuarterPlan]:
        """Get the plan for a specific quarter."""
        return self.quarter_plans.get(quarter)

    def update_quarter_plan(self, quarter: int, plan: QuarterPlan) -> None:
        """Update the plan for a specific quarter."""
        self.quarter_plans[quarter] = plan

    def get_current_quarter_budget(self) -> float:
        """Get the allocated budget for the current quarter."""
        plan = self.quarter_plans.get(self.current_quarter)
        return plan.allocated_budget if plan else 0

    def get_remaining_budget_in_quarter(self, quarter: int) -> float:
        """Get remaining budget in a specific quarter."""
        plan = self.quarter_plans.get(quarter)
        if not plan:
            return 0
        return plan.allocated_budget - plan.assigned_budget

    def get_total_remaining_budget(self, from_quarter: int = 1) -> float:
        """Get total remaining budget from a specific quarter onwards."""
        total_remaining = 0
        for quarter in range(from_quarter, len(self.quarter_plans) + 1):
            plan = self.quarter_plans.get(quarter)
            if plan:
                total_remaining += plan.allocated_budget - plan.assigned_budget
        return total_remaining

    def reallocate_budget(self, source_quarter: int, target_quarter: int, amount: float) -> bool:
        """
        Reallocate budget from one quarter to another.

        Returns:
            bool: True if reallocation was successful
        """
        source_plan = self.quarter_plans.get(source_quarter)
        target_plan = self.quarter_plans.get(target_quarter)

        if not source_plan or not target_plan:
            return False

        # Check if source has enough available budget
        available_in_source = source_plan.allocated_budget - source_plan.assigned_budget
        if available_in_source < amount:
            return False

        # Perform reallocation
        source_plan.allocated_budget -= amount
        target_plan.allocated_budget += amount

        return True

    def rebalance_quarters(self, current_quarter: int, usage_trends: Dict[int, float]) -> Dict[int, QuarterPlan]:
        """
        Rebalance remaining quarters based on usage trends.

        Args:
            current_quarter: Current quarter being executed
            usage_trends: Trend multipliers for each remaining quarter

        Returns:
            Updated quarter plans
        """
        # Calculate total remaining budget
        remaining_budget = self.get_total_remaining_budget(current_quarter)
        remaining_quarters = list(range(current_quarter, len(self.quarter_plans) + 1))

        if not remaining_quarters or remaining_budget <= 0:
            return self.quarter_plans

        # Apply trend adjustments
        adjusted_weights = {}
        total_weight = 0

        for quarter in remaining_quarters:
            base_weight = 1.0  # Equal weight baseline
            trend_multiplier = usage_trends.get(quarter, 1.0)
            adjusted_weights[quarter] = base_weight * trend_multiplier
            total_weight += adjusted_weights[quarter]

        # Redistribute budget based on adjusted weights
        for quarter in remaining_quarters:
            if total_weight > 0:
                weight_ratio = adjusted_weights[quarter] / total_weight
                new_allocation = remaining_budget * weight_ratio

                # Update quarter plan while preserving existing assigned budget
                plan = self.quarter_plans[quarter]
                plan.allocated_budget = plan.assigned_budget + new_allocation

        return self.quarter_plans

    def distribute_todos_to_quarters(self, todos: List[TodoItem]) -> Dict[int, QuarterPlan]:
        """
        Distribute todos across quarters based on their characteristics.

        Returns:
            Updated quarter plans with todos assigned
        """
        # Clear existing todo assignments
        for plan in self.quarter_plans.values():
            plan.todos.clear()
            plan.todo_budget_map.clear()
            plan.assigned_budget = 0

        # Sort todos by execution order (considering dependencies)
        sorted_todos = self._sort_todos_by_execution_order(todos)

        # Distribute todos across quarters
        current_quarter = 1
        quarter_budget_used = 0

        for todo in sorted_todos:
            # Determine if todo fits in current quarter
            plan = self.quarter_plans[current_quarter]
            available_budget = plan.allocated_budget - quarter_budget_used

            if todo.estimated_tokens > available_budget and current_quarter < len(self.quarter_plans):
                # Move to next quarter
                current_quarter += 1
                quarter_budget_used = 0
                plan = self.quarter_plans[current_quarter]

            # Assign todo to current quarter
            plan.todos.append(todo)
            plan.assigned_budget += todo.estimated_tokens
            plan.todo_budget_map[todo.todo_id] = todo.estimated_tokens
            quarter_budget_used += todo.estimated_tokens

        return self.quarter_plans

    def _sort_todos_by_execution_order(self, todos: List[TodoItem]) -> List[TodoItem]:
        """Sort todos by their natural execution order considering dependencies."""
        sorted_todos = []
        remaining_todos = todos.copy()

        while remaining_todos:
            # Find todos with no unmet dependencies
            ready_todos = []
            completed_todo_ids = {todo.todo_id for todo in sorted_todos}

            for todo in remaining_todos:
                if all(dep_id in completed_todo_ids for dep_id in todo.dependencies):
                    ready_todos.append(todo)

            if not ready_todos:
                # Break circular dependencies by taking first todo
                ready_todos = [remaining_todos[0]]

            # Add ready todos to sorted list
            for todo in ready_todos:
                sorted_todos.append(todo)
                remaining_todos.remove(todo)

        return sorted_todos

    def get_quarter_statistics(self) -> Dict[int, Dict[str, float]]:
        """Get statistics for all quarters."""
        stats = {}

        for quarter, plan in self.quarter_plans.items():
            stats[quarter] = {
                'allocated_budget': plan.allocated_budget,
                'assigned_budget': plan.assigned_budget,
                'remaining_budget': plan.allocated_budget - plan.assigned_budget,
                'utilization_percentage': (plan.assigned_budget / plan.allocated_budget * 100) if plan.allocated_budget > 0 else 0,
                'todo_count': len(plan.todos)
            }

        return stats

    def advance_to_next_quarter(self) -> bool:
        """
        Advance to the next quarter.

        Returns:
            bool: True if advancement was successful, False if already at last quarter
        """
        if self.current_quarter < len(self.quarter_plans):
            self.current_quarter += 1
            return True
        return False

    def get_quarter_progress(self, quarter: int) -> float:
        """
        Get progress percentage for a specific quarter.

        Returns:
            float: Progress percentage (0.0 to 1.0)
        """
        plan = self.quarter_plans.get(quarter)
        if not plan or not plan.todos:
            return 0.0

        completed_todos = sum(1 for todo in plan.todos if todo.status == 'completed')
        return completed_todos / len(plan.todos)

    def get_overall_progress(self) -> float:
        """
        Get overall progress across all quarters.

        Returns:
            float: Overall progress percentage (0.0 to 1.0)
        """
        total_todos = sum(len(plan.todos) for plan in self.quarter_plans.values())
        if total_todos == 0:
            return 0.0

        completed_todos = sum(
            sum(1 for todo in plan.todos if todo.status == 'completed')
            for plan in self.quarter_plans.values()
        )

        return completed_todos / total_todos

    def validate_quarter_allocation(self) -> List[str]:
        """
        Validate quarter allocations and return any issues found.

        Returns:
            List[str]: List of validation issues
        """
        issues = []

        # Check if total allocated budget matches expected total
        total_allocated = sum(plan.allocated_budget for plan in self.quarter_plans.values())
        expected_total = self.total_budget * (1 + self.config.quarter_buffer)

        if abs(total_allocated - expected_total) > 1.0:  # Allow small floating point differences
            issues.append(f"Total allocated budget ({total_allocated}) doesn't match expected ({expected_total})")

        # Check for over-allocation in any quarter
        for quarter, plan in self.quarter_plans.items():
            if plan.assigned_budget > plan.allocated_budget:
                over_allocation = plan.assigned_budget - plan.allocated_budget
                issues.append(f"Quarter {quarter} over-allocated by {over_allocation}")

        # Check for empty quarters with budget
        for quarter, plan in self.quarter_plans.items():
            if plan.allocated_budget > 0 and len(plan.todos) == 0:
                issues.append(f"Quarter {quarter} has budget but no todos")

        return issues

    def optimize_quarter_distribution(self) -> None:
        """Optimize todo distribution across quarters for better balance."""
        all_todos = []

        # Collect all todos
        for plan in self.quarter_plans.values():
            all_todos.extend(plan.todos)

        if not all_todos:
            return

        # Redistribute todos optimally
        self.distribute_todos_to_quarters(all_todos)