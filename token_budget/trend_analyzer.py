"""Budget trend analyzer for usage patterns and completion probability predictions."""

from typing import Dict, List, Optional, Any
import statistics
from .adaptive_models import (
    TodoItem, TrendAnalysis, QuarterPlan, AdaptiveConfig
)


class BudgetTrendAnalyzer:
    """Analyzes budget usage trends and updates predictions."""

    def __init__(self, config: Optional[AdaptiveConfig] = None):
        self.config = config or AdaptiveConfig()
        self.historical_data: List[Dict] = []
        self.quarter_history: Dict[int, List[float]] = {}

    def analyze_usage_trend(self, quarter: int, planned_budget: float, actual_usage: float,
                          completed_todos: List[TodoItem], remaining_todos: List[TodoItem]) -> TrendAnalysis:
        """
        Analyze budget usage trends and update predictions.

        Returns:
        - Usage velocity (tokens per todo item)
        - Accuracy of initial estimates
        - Projected completion probability
        - Recommended budget reallocation
        """
        # Ensure quarter_history is initialized for all quarters
        max_quarters = len(self.config.checkpoint_intervals)
        for q in range(1, max_quarters + 1):
            if q not in self.quarter_history:
                self.quarter_history[q] = []

        # Calculate actual vs. estimated accuracy
        accuracy = self.calculate_estimation_accuracy(completed_todos)

        # Project remaining resource needs
        remaining_budget = self.calculate_remaining_budget(quarter, actual_usage, planned_budget)
        updated_estimates = self.update_todo_estimates(remaining_todos, accuracy)

        # Calculate usage velocity
        velocity = self.calculate_usage_velocity(completed_todos)

        # Recalculate completion probability
        completion_probability = self.calculate_completion_probability(
            remaining_budget, updated_estimates, velocity
        )

        # Record data for historical analysis
        self.record_quarter_data(quarter, actual_usage, planned_budget, velocity, accuracy)

        return TrendAnalysis(
            usage_velocity=velocity,
            estimation_accuracy=accuracy,
            completion_probability=completion_probability,
            recommended_reallocation=self.suggest_budget_reallocation(
                remaining_todos, remaining_budget, quarter
            )
        )

    def calculate_estimation_accuracy(self, completed_todos: List[TodoItem]) -> float:
        """Calculate the accuracy of initial estimates vs actual usage."""
        if not completed_todos:
            return 1.0

        accuracies = []
        for todo in completed_todos:
            if todo.estimated_tokens > 0 and todo.actual_tokens > 0:
                # Calculate accuracy as ratio (closer to 1.0 is better)
                accuracy = todo.estimated_tokens / todo.actual_tokens
                accuracies.append(accuracy)

        if not accuracies:
            return 1.0

        # Return average accuracy, clamped to reasonable bounds
        avg_accuracy = statistics.mean(accuracies)
        return max(0.1, min(3.0, avg_accuracy))  # Clamp between 0.1x and 3.0x

    def calculate_usage_velocity(self, completed_todos: List[TodoItem]) -> float:
        """Calculate average tokens used per completed todo."""
        if not completed_todos:
            return 0.0

        total_tokens = sum(todo.actual_tokens for todo in completed_todos)
        return total_tokens / len(completed_todos)

    def calculate_remaining_budget(self, quarter: int, actual_usage: float, planned_usage: float) -> float:
        """Calculate remaining budget based on current usage patterns."""
        # This should be calculated by the calling context based on total budget
        # For now, return a placeholder that indicates budget calculation is needed
        return max(0, planned_usage - actual_usage)

    def update_todo_estimates(self, remaining_todos: List[TodoItem], accuracy: float) -> List[TodoItem]:
        """Update todo estimates based on observed accuracy patterns."""
        updated_todos = []

        for todo in remaining_todos:
            updated_todo = TodoItem(
                todo_id=todo.todo_id,
                description=todo.description,
                category=todo.category,
                estimated_tokens=int(todo.estimated_tokens / accuracy),  # Adjust estimate
                actual_tokens=todo.actual_tokens,
                dependencies=todo.dependencies,
                tools=todo.tools,
                agents=todo.agents,
                status=todo.status,
                safe_restart_after=todo.safe_restart_after,
                involves_tools=todo.involves_tools
            )
            updated_todos.append(updated_todo)

        return updated_todos

    def calculate_completion_probability(self, remaining_budget: float,
                                       updated_todos: List[TodoItem],
                                       velocity: float) -> float:
        """Calculate the probability of completing all remaining todos within budget."""
        if not updated_todos or remaining_budget <= 0:
            return 0.0

        # Simple approach: sum updated estimates and compare to remaining budget
        total_estimated = sum(todo.estimated_tokens for todo in updated_todos)

        if total_estimated <= 0:
            return 1.0

        # Calculate probability based on budget ratio with some uncertainty
        budget_ratio = remaining_budget / total_estimated

        # Add velocity-based adjustment
        if velocity > 0:
            # If velocity is high, we might finish faster
            velocity_adjustment = min(0.2, velocity / 1000)  # Cap at 20% boost
            budget_ratio += velocity_adjustment

        # Apply sigmoid curve to get probability between 0 and 1
        probability = self.sigmoid(budget_ratio - 1)

        return max(0.0, min(1.0, probability))

    def sigmoid(self, x: float) -> float:
        """Apply sigmoid function to map ratio to probability."""
        import math
        try:
            return 1 / (1 + math.exp(-2 * x))
        except OverflowError:
            return 0.0 if x < 0 else 1.0

    def suggest_budget_reallocation(self, remaining_todos: List[TodoItem],
                                  remaining_budget: float, current_quarter: int) -> Dict[int, float]:
        """Suggest budget reallocation across remaining quarters."""
        if not remaining_todos or remaining_budget <= 0:
            return {}

        # Group todos by preferred quarter
        max_quarters = len(self.config.checkpoint_intervals)
        quarter_todos = {quarter: [] for quarter in range(current_quarter, max_quarters + 1)}

        for todo in remaining_todos:
            preferred_quarter = self.get_todo_preferred_quarter(todo, current_quarter)
            quarter_todos[preferred_quarter].append(todo)

        # Calculate budget needs per quarter
        reallocation = {}
        total_estimated = sum(todo.estimated_tokens for todo in remaining_todos)

        if total_estimated > 0:
            for quarter in range(current_quarter, 5):
                todos_in_quarter = quarter_todos[quarter]
                quarter_estimated = sum(todo.estimated_tokens for todo in todos_in_quarter)

                # Proportional allocation based on todos in each quarter
                if quarter_estimated > 0:
                    quarter_ratio = quarter_estimated / total_estimated
                    reallocation[quarter] = remaining_budget * quarter_ratio

        return reallocation

    def get_todo_preferred_quarter(self, todo: TodoItem, current_quarter: int) -> int:
        """Determine preferred quarter for a todo based on its characteristics."""
        from .adaptive_models import TodoCategory

        # Map categories to preferred quarters (relative to current)
        category_quarters = {
            TodoCategory.SEARCH: 0,      # Execute ASAP
            TodoCategory.READ: 0,        # Execute ASAP
            TodoCategory.RESEARCH: 0,    # Execute ASAP
            TodoCategory.ANALYZE: 1,     # Next quarter
            TodoCategory.PLANNING: 1,    # Next quarter
            TodoCategory.WRITE: 2,       # Later quarter
            TodoCategory.MODIFY: 2,      # Later quarter
            TodoCategory.DEPLOY: 3,      # Final quarter
            TodoCategory.VALIDATION: 3,  # Final quarter
            TodoCategory.TEST: 2         # Testing quarter
        }

        relative_quarter = category_quarters.get(todo.category, 1)
        max_quarters = len(self.config.checkpoint_intervals)
        preferred_quarter = min(max_quarters, current_quarter + relative_quarter)

        return preferred_quarter

    def update_quarter_allocations(self, quarter_plans: Dict[int, QuarterPlan],
                                 current_quarter: int, trend_analysis: TrendAnalysis) -> Dict[int, QuarterPlan]:
        """
        Redistribute todos across remaining quarters based on usage trends.
        """
        # Get remaining todos from current and future quarters
        remaining_todos = []
        for q in range(current_quarter, 5):
            if q in quarter_plans:
                remaining_todos.extend(quarter_plans[q].todos)

        # Apply updated estimates from trend analysis
        accuracy = trend_analysis.estimation_accuracy
        for todo in remaining_todos:
            # Adjust estimates based on observed accuracy
            todo.estimated_tokens = int(todo.estimated_tokens / accuracy)

        # Clear existing assignments for remaining quarters
        for q in range(current_quarter, 5):
            if q in quarter_plans:
                quarter_plans[q].todos.clear()
                quarter_plans[q].todo_budget_map.clear()
                quarter_plans[q].assigned_budget = 0

        # Redistribute todos based on trend analysis recommendations
        reallocation = trend_analysis.recommended_reallocation

        # Update quarter budgets based on reallocation
        for quarter, new_budget in reallocation.items():
            if quarter in quarter_plans:
                quarter_plans[quarter].allocated_budget = new_budget

        # Redistribute todos to quarters
        self.redistribute_todos(remaining_todos, quarter_plans, current_quarter)

        return quarter_plans

    def redistribute_todos(self, todos: List[TodoItem], quarter_plans: Dict[int, QuarterPlan], current_quarter: int):
        """Redistribute todos across quarters with updated budget allocations."""
        # Sort todos by dependencies and priority
        sorted_todos = self.sort_todos_for_redistribution(todos)

        for todo in sorted_todos:
            # Find the best quarter for this todo
            best_quarter = self.find_best_quarter_for_todo(todo, quarter_plans, current_quarter)

            if best_quarter and best_quarter in quarter_plans:
                plan = quarter_plans[best_quarter]
                plan.todos.append(todo)
                plan.assigned_budget += todo.estimated_tokens
                plan.todo_budget_map[todo.todo_id] = todo.estimated_tokens

    def find_best_quarter_for_todo(self, todo: TodoItem, quarter_plans: Dict[int, QuarterPlan],
                                 current_quarter: int) -> Optional[int]:
        """Find the best quarter for a todo based on available budget and preferences."""
        preferred_quarter = self.get_todo_preferred_quarter(todo, current_quarter)

        # Try preferred quarter first
        for quarter in [preferred_quarter] + list(range(current_quarter, 5)):
            if quarter in quarter_plans:
                plan = quarter_plans[quarter]
                available_budget = plan.allocated_budget - plan.assigned_budget

                if available_budget >= todo.estimated_tokens:
                    return quarter

        # If no quarter has enough budget, assign to the one with most available space
        best_quarter = None
        max_available = 0

        for quarter in range(current_quarter, 5):
            if quarter in quarter_plans:
                plan = quarter_plans[quarter]
                available = plan.allocated_budget - plan.assigned_budget
                if available > max_available:
                    max_available = available
                    best_quarter = quarter

        return best_quarter

    def sort_todos_for_redistribution(self, todos: List[TodoItem]) -> List[TodoItem]:
        """Sort todos for optimal redistribution considering dependencies."""
        # Simple topological sort based on dependencies
        sorted_todos = []
        remaining_todos = todos.copy()

        while remaining_todos:
            # Find todos with no unmet dependencies
            ready_todos = []
            completed_ids = {todo.todo_id for todo in sorted_todos}

            for todo in remaining_todos:
                if all(dep_id in completed_ids for dep_id in todo.dependencies):
                    ready_todos.append(todo)

            if not ready_todos:
                # Break circular dependencies
                ready_todos = [remaining_todos[0]]

            # Sort ready todos by priority (shorter estimates first)
            ready_todos.sort(key=lambda t: t.estimated_tokens)

            # Add to sorted list
            for todo in ready_todos:
                sorted_todos.append(todo)
                remaining_todos.remove(todo)

        return sorted_todos

    def record_quarter_data(self, quarter: int, actual_usage: float, planned_usage: float,
                          velocity: float, accuracy: float):
        """Record data for historical analysis."""
        data_point = {
            'quarter': quarter,
            'actual_usage': actual_usage,
            'planned_usage': planned_usage,
            'velocity': velocity,
            'accuracy': accuracy,
            'usage_ratio': actual_usage / planned_usage if planned_usage > 0 else 1.0
        }

        self.historical_data.append(data_point)
        if quarter in self.quarter_history:
            self.quarter_history[quarter].append(actual_usage)

    def get_historical_performance(self, quarter: int) -> Dict[str, float]:
        """Get historical performance data for a specific quarter."""
        quarter_data = [d for d in self.historical_data if d['quarter'] == quarter]

        if not quarter_data:
            return {'avg_accuracy': 1.0, 'avg_velocity': 0.0, 'avg_usage_ratio': 1.0}

        return {
            'avg_accuracy': statistics.mean(d['accuracy'] for d in quarter_data),
            'avg_velocity': statistics.mean(d['velocity'] for d in quarter_data),
            'avg_usage_ratio': statistics.mean(d['usage_ratio'] for d in quarter_data)
        }

    def predict_quarter_performance(self, quarter: int, planned_budget: float) -> Dict[str, float]:
        """Predict performance for a quarter based on historical data."""
        historical = self.get_historical_performance(quarter)

        # Predict based on historical averages
        predicted_usage = planned_budget * historical['avg_usage_ratio']
        predicted_velocity = historical['avg_velocity']
        predicted_accuracy = historical['avg_accuracy']

        return {
            'predicted_usage': predicted_usage,
            'predicted_velocity': predicted_velocity,
            'predicted_accuracy': predicted_accuracy,
            'confidence': min(1.0, len(self.quarter_history.get(quarter, [])) / 5.0)  # More data = higher confidence
        }

    def get_trend_summary(self) -> Dict[str, Any]:
        """Get a summary of all trend analysis data."""
        if not self.historical_data:
            return {'status': 'no_data'}

        recent_data = self.historical_data[-5:]  # Last 5 data points

        return {
            'total_data_points': len(self.historical_data),
            'recent_accuracy': statistics.mean(d['accuracy'] for d in recent_data),
            'recent_velocity': statistics.mean(d['velocity'] for d in recent_data),
            'recent_usage_ratio': statistics.mean(d['usage_ratio'] for d in recent_data),
            'quarters_analyzed': len(set(d['quarter'] for d in self.historical_data)),
            'trend_direction': self.calculate_trend_direction()
        }

    def calculate_trend_direction(self) -> str:
        """Calculate overall trend direction (improving, declining, stable)."""
        if len(self.historical_data) < 3:
            return 'insufficient_data'

        recent_accuracy = statistics.mean(d['accuracy'] for d in self.historical_data[-3:])
        early_accuracy = statistics.mean(d['accuracy'] for d in self.historical_data[:3])

        if recent_accuracy > early_accuracy * 1.1:
            return 'improving'
        elif recent_accuracy < early_accuracy * 0.9:
            return 'declining'
        else:
            return 'stable'