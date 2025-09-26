"""Proactive planner for creating execution plans before command start."""

import re
from typing import Dict, List, Optional, Any
from .adaptive_models import (
    TodoItem, TodoCategory, ExecutionPlan, QuarterPlan,
    AdaptiveConfig
)


class ProactivePlanner:
    """Creates detailed todo lists and execution plans before command execution."""

    def __init__(self, config: Optional[AdaptiveConfig] = None):
        self.config = config or AdaptiveConfig()
        self.todo_id_counter = 1

    def create_execution_plan(self, command: str, context: dict, total_budget: float) -> ExecutionPlan:
        """
        Create a comprehensive todo list and quarter-based execution plan BEFORE starting.

        Steps:
        1. Analyze command and break into discrete steps
        2. Estimate resource requirements for each step
        3. Create detailed todo list with priorities
        4. Distribute todos across quarters based on dependencies and complexity
        5. Allocate budget to each todo item
        """
        # Parse command and create todo items
        todos = self.parse_command_to_todos(command, context)

        # Estimate resource needs for each todo
        for todo in todos:
            todo.estimated_tokens = self.estimate_todo_complexity(todo)
            todo.dependencies = self.identify_dependencies(todo, todos)
            todo.safe_restart_after = self.is_safe_restart_point(todo)

        # Distribute across quarters
        quarter_plan = self.distribute_todos_by_quarters(todos, total_budget)

        return ExecutionPlan(
            todos=todos,
            quarter_distribution=quarter_plan,
            total_estimated_budget=sum(t.estimated_tokens for t in todos),
            safe_restart_points=self.compile_restart_points(todos)
        )

    def parse_command_to_todos(self, command: str, context: dict) -> List[TodoItem]:
        """
        Break down slash command into concrete, actionable todo items that map
        to specific tools, agents, and operations. Each todo must have estimated budget.
        """
        # Extract command type and parameters
        command_type = self.extract_command_type(command)
        command_params = self.extract_command_parameters(command, context)

        # Generate specific todos based on command type
        todos = []

        if command_type in ['analyze-code', 'analyze']:
            todos = self.create_analyze_code_todos(command_params)
        elif command_type in ['debug-issue', 'debug']:
            todos = self.create_debug_todos(command_params)
        elif command_type in ['test-fix', 'test']:
            todos = self.create_test_fix_todos(command_params)
        elif command_type in ['optimize', 'performance']:
            todos = self.create_optimization_todos(command_params)
        elif command_type in ['generate', 'create']:
            todos = self.create_generation_todos(command_params)
        elif command_type in ['refactor']:
            todos = self.create_refactor_todos(command_params)
        else:
            # Generic command breakdown
            todos = self.create_generic_todos(command, command_params)

        # Apply estimation buffer
        for todo in todos:
            todo.estimated_tokens = int(todo.estimated_tokens * (1 + self.config.todo_estimation_buffer))

        return todos

    def create_analyze_code_todos(self, params: Dict[str, Any]) -> List[TodoItem]:
        """Create todos for code analysis commands."""
        return [
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Search codebase for relevant patterns and files",
                category=TodoCategory.SEARCH,
                estimated_tokens=150,
                tools=['Grep', 'Glob'],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Read and understand key files identified",
                category=TodoCategory.READ,
                estimated_tokens=300,
                tools=['Read'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Analyze code structure and patterns",
                category=TodoCategory.ANALYZE,
                estimated_tokens=400,
                tools=['Task'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Generate comprehensive analysis report",
                category=TodoCategory.WRITE,
                estimated_tokens=200,
                tools=['Write'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=False  # Writing operation - not safe to restart during
            )
        ]

    def create_debug_todos(self, params: Dict[str, Any]) -> List[TodoItem]:
        """Create todos for debugging commands."""
        return [
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Reproduce issue with test case",
                category=TodoCategory.TEST,
                estimated_tokens=200,
                tools=['Bash'],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Search logs for error patterns",
                category=TodoCategory.SEARCH,
                estimated_tokens=100,
                tools=['Grep'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Analyze root cause of issue",
                category=TodoCategory.ANALYZE,
                estimated_tokens=300,
                tools=['Task'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Implement fix for the issue",
                category=TodoCategory.MODIFY,
                estimated_tokens=250,
                tools=['Edit', 'MultiEdit'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=False
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Validate fix with tests",
                category=TodoCategory.TEST,
                estimated_tokens=150,
                tools=['Bash'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            )
        ]

    def create_test_fix_todos(self, params: Dict[str, Any]) -> List[TodoItem]:
        """Create todos for test fixing commands."""
        return [
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Run failing tests to understand issues",
                category=TodoCategory.TEST,
                estimated_tokens=150,
                tools=['Bash'],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Analyze test failures and error messages",
                category=TodoCategory.ANALYZE,
                estimated_tokens=200,
                tools=['Read', 'Grep'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Fix test implementation issues",
                category=TodoCategory.MODIFY,
                estimated_tokens=300,
                tools=['Edit', 'MultiEdit'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=False
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Verify all tests pass",
                category=TodoCategory.TEST,
                estimated_tokens=100,
                tools=['Bash'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            )
        ]

    def create_optimization_todos(self, params: Dict[str, Any]) -> List[TodoItem]:
        """Create todos for optimization commands."""
        return [
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Profile application performance",
                category=TodoCategory.ANALYZE,
                estimated_tokens=250,
                tools=['Bash', 'Task'],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Identify performance bottlenecks",
                category=TodoCategory.ANALYZE,
                estimated_tokens=300,
                tools=['Read', 'Grep'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Implement performance optimizations",
                category=TodoCategory.MODIFY,
                estimated_tokens=400,
                tools=['Edit', 'MultiEdit'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=False
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Benchmark improvements",
                category=TodoCategory.TEST,
                estimated_tokens=200,
                tools=['Bash'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            )
        ]

    def create_generation_todos(self, params: Dict[str, Any]) -> List[TodoItem]:
        """Create todos for generation/creation commands."""
        return [
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Research existing patterns and conventions",
                category=TodoCategory.RESEARCH,
                estimated_tokens=200,
                tools=['Read', 'Grep'],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Plan structure and architecture",
                category=TodoCategory.PLANNING,
                estimated_tokens=150,
                tools=['Task'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Generate core implementation",
                category=TodoCategory.WRITE,
                estimated_tokens=350,
                tools=['Write', 'MultiEdit'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=False
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Validate implementation with tests",
                category=TodoCategory.TEST,
                estimated_tokens=200,
                tools=['Bash'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            )
        ]

    def create_refactor_todos(self, params: Dict[str, Any]) -> List[TodoItem]:
        """Create todos for refactoring commands."""
        return [
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Analyze current code structure",
                category=TodoCategory.ANALYZE,
                estimated_tokens=300,
                tools=['Read', 'Grep', 'Task'],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Plan refactoring strategy",
                category=TodoCategory.PLANNING,
                estimated_tokens=200,
                tools=['Task'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Execute refactoring changes",
                category=TodoCategory.MODIFY,
                estimated_tokens=400,
                tools=['Edit', 'MultiEdit'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=False
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Verify refactoring with tests",
                category=TodoCategory.TEST,
                estimated_tokens=150,
                tools=['Bash'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            )
        ]

    def create_generic_todos(self, command: str, params: Dict[str, Any]) -> List[TodoItem]:
        """Create generic todos for unknown commands."""
        return [
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description=f"Analyze requirements for command: {command}",
                category=TodoCategory.ANALYZE,
                estimated_tokens=200,
                tools=['Task'],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Plan execution strategy",
                category=TodoCategory.PLANNING,
                estimated_tokens=150,
                tools=['Task'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Execute planned actions",
                category=TodoCategory.MODIFY,
                estimated_tokens=300,
                tools=['Edit', 'Write', 'Bash'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=False
            ),
            TodoItem(
                todo_id=f"todo_{self.get_next_id()}",
                description="Validate results",
                category=TodoCategory.VALIDATION,
                estimated_tokens=100,
                tools=['Bash', 'Read'],
                dependencies=[f"todo_{self.todo_id_counter-1}"],
                safe_restart_after=True
            )
        ]

    def distribute_todos_by_quarters(self, todos: List[TodoItem], total_budget: float) -> Dict[int, QuarterPlan]:
        """
        Distribute concrete todo items across quarters with specific budget allocations.
        Uses dynamic quarter count based on checkpoint intervals.
        """
        # Use checkpoint intervals to determine number of quarters
        num_quarters = len(self.config.checkpoint_intervals)

        # Calculate base quarter budgets (equal distribution)
        base_quarter_budget = total_budget / num_quarters

        # Create quarter plans dynamically
        quarter_plans = {}
        for i in range(1, num_quarters + 1):
            quarter_plans[i] = QuarterPlan(allocated_budget=base_quarter_budget)

        # Sort todos by dependencies
        sorted_todos = self.sort_todos_by_dependencies(todos)

        # Distribute todos ensuring logical quarter boundaries
        current_quarter = 1
        remaining_budget = quarter_plans[current_quarter].allocated_budget

        for todo in sorted_todos:
            # Determine best quarter for this todo based on category
            preferred_quarter = self.get_preferred_quarter(todo)

            # Check if preferred quarter has space
            if (preferred_quarter >= current_quarter and
                preferred_quarter <= num_quarters and
                todo.estimated_tokens <= quarter_plans[preferred_quarter].allocated_budget - quarter_plans[preferred_quarter].assigned_budget):
                target_quarter = preferred_quarter
            else:
                # Use current quarter if preferred is not available
                target_quarter = current_quarter
                # Move to next quarter if current is full
                if todo.estimated_tokens > remaining_budget and current_quarter < num_quarters:
                    current_quarter += 1
                    target_quarter = current_quarter
                    remaining_budget = quarter_plans[current_quarter].allocated_budget

            # Assign todo to target quarter
            quarter_plans[target_quarter].todos.append(todo)
            quarter_plans[target_quarter].assigned_budget += todo.estimated_tokens
            quarter_plans[target_quarter].todo_budget_map[todo.todo_id] = todo.estimated_tokens

            if target_quarter == current_quarter:
                remaining_budget -= todo.estimated_tokens

        # Validate and rebalance if needed
        for quarter, plan in quarter_plans.items():
            if plan.assigned_budget > plan.allocated_budget * 1.1:  # 10% overflow tolerance
                self.rebalance_quarter_distribution(quarter_plans, quarter)

        return quarter_plans

    def get_preferred_quarter(self, todo: TodoItem) -> int:
        """Determine the preferred quarter for a todo based on its category."""
        num_quarters = len(self.config.checkpoint_intervals)

        # Map categories to proportional quarters based on available quarters
        if todo.category in [TodoCategory.SEARCH, TodoCategory.READ, TodoCategory.RESEARCH, TodoCategory.SETUP]:
            return 1  # Early data collection (always first quarter)
        elif todo.category in [TodoCategory.ANALYZE, TodoCategory.PLANNING]:
            return min(2, num_quarters)  # Analysis phase (second quarter if available, else last)
        elif todo.category in [TodoCategory.WRITE, TodoCategory.MODIFY, TodoCategory.DEPLOY]:
            return min(max(num_quarters - 1, 1), num_quarters)  # Implementation phase (second to last, or first if only one)
        else:
            return num_quarters  # Validation and completion (always last quarter)

    def sort_todos_by_dependencies(self, todos: List[TodoItem]) -> List[TodoItem]:
        """Sort todos ensuring dependencies are satisfied before dependents."""
        sorted_todos = []
        remaining_todos = todos.copy()

        while remaining_todos:
            # Find todos with no unmet dependencies
            ready_todos = []
            for todo in remaining_todos:
                if self.dependencies_satisfied(todo, [t.todo_id for t in sorted_todos]):
                    ready_todos.append(todo)

            if not ready_todos:
                # Circular dependency or error - break it
                ready_todos = [remaining_todos[0]]

            # Add ready todos to sorted list
            for todo in ready_todos:
                sorted_todos.append(todo)
                remaining_todos.remove(todo)

        return sorted_todos

    def dependencies_satisfied(self, todo: TodoItem, completed_todo_ids: List[str]) -> bool:
        """Check if all dependencies for a todo are in the completed list."""
        if not todo.dependencies:
            return True
        return all(dep_id in completed_todo_ids for dep_id in todo.dependencies)

    def rebalance_quarter_distribution(self, quarter_plans: Dict[int, QuarterPlan], overloaded_quarter: int):
        """Rebalance todos when a quarter exceeds its budget allocation."""
        overloaded_plan = quarter_plans[overloaded_quarter]

        # Move some todos to later quarters
        for quarter in range(overloaded_quarter + 1, 5):
            if quarter in quarter_plans:
                target_plan = quarter_plans[quarter]
                available_budget = target_plan.allocated_budget - target_plan.assigned_budget

                # Move todos that fit in available budget
                todos_to_move = []
                for todo in overloaded_plan.todos:
                    if todo.estimated_tokens <= available_budget:
                        todos_to_move.append(todo)
                        available_budget -= todo.estimated_tokens

                        # Stop if overload is resolved
                        if overloaded_plan.assigned_budget - sum(t.estimated_tokens for t in todos_to_move) <= overloaded_plan.allocated_budget:
                            break

                # Execute the move
                for todo in todos_to_move:
                    overloaded_plan.todos.remove(todo)
                    overloaded_plan.assigned_budget -= todo.estimated_tokens
                    del overloaded_plan.todo_budget_map[todo.todo_id]

                    target_plan.todos.append(todo)
                    target_plan.assigned_budget += todo.estimated_tokens
                    target_plan.todo_budget_map[todo.todo_id] = todo.estimated_tokens

                if overloaded_plan.assigned_budget <= overloaded_plan.allocated_budget:
                    break

    def extract_command_type(self, command: str) -> str:
        """Extract the main command type from the command string."""
        # Remove leading slash and extract first part
        clean_command = command.lstrip('/')
        return clean_command.split()[0] if clean_command.split() else clean_command

    def extract_command_parameters(self, command: str, context: dict) -> Dict[str, Any]:
        """Extract parameters from command and context."""
        params = {'command': command}
        params.update(context)
        return params

    def estimate_todo_complexity(self, todo: TodoItem) -> int:
        """Estimate token complexity for a todo based on category and tools."""
        base_estimates = {
            TodoCategory.SEARCH: 100,
            TodoCategory.READ: 200,
            TodoCategory.ANALYZE: 300,
            TodoCategory.RESEARCH: 250,
            TodoCategory.PLANNING: 150,
            TodoCategory.VALIDATION: 100,
            TodoCategory.PREPARATION: 100,
            TodoCategory.WRITE: 300,
            TodoCategory.MODIFY: 250,
            TodoCategory.DEPLOY: 200,
            TodoCategory.DELETE: 50,
            TodoCategory.TEST: 150,
            TodoCategory.SETUP: 100,
            TodoCategory.SPAWN: 200,
            TodoCategory.MONITOR: 100,
            TodoCategory.MERGE: 150
        }

        base_estimate = base_estimates.get(todo.category, 200)

        # Adjust based on tools
        tool_multipliers = {
            'Task': 1.5,  # Agent tasks are more complex
            'Bash': 1.2,  # Command execution
            'Edit': 1.1,  # File editing
            'MultiEdit': 1.3,  # Multiple file editing
            'Write': 1.2,  # File writing
            'Read': 1.0,  # File reading
            'Grep': 1.0,  # Searching
            'Glob': 1.0   # Pattern matching
        }

        multiplier = 1.0
        for tool in todo.tools:
            multiplier *= tool_multipliers.get(tool, 1.0)

        return int(base_estimate * multiplier)

    def identify_dependencies(self, todo: TodoItem, all_todos: List[TodoItem]) -> List[str]:
        """Identify dependencies for a todo based on logical flow."""
        dependencies = []

        # Find todos that this one logically depends on
        for other_todo in all_todos:
            if other_todo.todo_id == todo.todo_id:
                continue

            # Analysis depends on search/read
            if (todo.category == TodoCategory.ANALYZE and
                other_todo.category in [TodoCategory.SEARCH, TodoCategory.READ]):
                dependencies.append(other_todo.todo_id)

            # Modify depends on analyze/planning
            if (todo.category == TodoCategory.MODIFY and
                other_todo.category in [TodoCategory.ANALYZE, TodoCategory.PLANNING]):
                dependencies.append(other_todo.todo_id)

            # Test depends on modify/write
            if (todo.category == TodoCategory.TEST and
                other_todo.category in [TodoCategory.MODIFY, TodoCategory.WRITE]):
                dependencies.append(other_todo.todo_id)

        return dependencies

    def is_safe_restart_point(self, todo: TodoItem) -> bool:
        """Determine if completion of this todo represents a safe restart point."""
        safe_categories = [
            TodoCategory.SEARCH, TodoCategory.READ, TodoCategory.ANALYZE,
            TodoCategory.RESEARCH, TodoCategory.PLANNING, TodoCategory.VALIDATION,
            TodoCategory.PREPARATION, TodoCategory.TEST
        ]
        return todo.category in safe_categories

    def compile_restart_points(self, todos: List[TodoItem]) -> List[int]:
        """Compile indices of todos that are safe restart points."""
        restart_points = []
        for i, todo in enumerate(todos):
            if todo.safe_restart_after:
                restart_points.append(i)
        return restart_points

    def get_next_id(self) -> int:
        """Get next todo ID."""
        current_id = self.todo_id_counter
        self.todo_id_counter += 1
        return current_id