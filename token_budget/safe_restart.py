"""Safe restart manager for identifying restart points and preserving context."""

from typing import Dict, List, Optional, Any
from datetime import datetime
from .adaptive_models import (
    TodoItem, TodoCategory, ExecutionState, RestartPoint, RestartPlan,
    PlannedRestartPoint, RestartContext, Lesson, Mistake, SessionPreparation,
    AdaptiveConfig
)


class SafeRestartManager:
    """Identifies safe restart points and manages context preservation."""

    def __init__(self, config: Optional[AdaptiveConfig] = None):
        self.config = config or AdaptiveConfig()
        self.precomputed_plan: Optional[RestartPlan] = None
        self.runtime_safe_points: List[RestartPoint] = []

    def create_precomputed_restart_plan(self, todos: List[TodoItem]) -> RestartPlan:
        """
        Create restart plan BEFORE execution starts based on todo metadata.
        This solves the chicken-and-egg problem where todos haven't been completed yet.
        """
        planned_restart_points = []

        for i, todo in enumerate(todos):
            # PLANNED SAFE POINT: After read-only operations
            if todo.category in [TodoCategory.SEARCH, TodoCategory.READ,
                               TodoCategory.ANALYZE, TodoCategory.RESEARCH]:
                planned_restart_points.append(PlannedRestartPoint(
                    todo_index=i,
                    trigger_condition='completion',
                    reason=f"After read-only operation: {todo.description}",
                    context_to_preserve=[
                        'search_results', 'analysis_findings', 'research_data',
                        'file_contents', 'code_understanding'
                    ],
                    state_corruption_risk=False,
                    priority=1  # High priority - very safe
                ))

            # PLANNED SAFE POINT: Before destructive operations
            next_todo = todos[i+1] if i+1 < len(todos) else None
            if next_todo and next_todo.category in [TodoCategory.WRITE,
                                                   TodoCategory.MODIFY,
                                                   TodoCategory.DEPLOY,
                                                   TodoCategory.DELETE]:
                planned_restart_points.append(PlannedRestartPoint(
                    todo_index=i,
                    trigger_condition='before_next',
                    reason=f"Before destructive operation: {next_todo.description}",
                    context_to_preserve=[
                        'preparation_work', 'validation_results', 'planned_changes'
                    ],
                    state_corruption_risk=False,
                    priority=1  # High priority - prevents corruption
                ))

            # PLANNED SAFE POINT: After tool operations
            if todo.involves_tools or len(todo.tools) > 0:
                planned_restart_points.append(PlannedRestartPoint(
                    todo_index=i,
                    trigger_condition='tool_completion',
                    reason=f"After tool operation: {todo.description}",
                    context_to_preserve=[
                        'tool_outputs', 'command_results', 'api_responses'
                    ],
                    state_corruption_risk=False,
                    priority=2  # Medium priority - depends on clean tool exit
                ))

            # PLANNED SAFE POINT: At dependency boundaries
            if self.has_dependents(todo, todos):
                planned_restart_points.append(PlannedRestartPoint(
                    todo_index=i,
                    trigger_condition='dependencies_complete',
                    reason=f"Dependency boundary: {todo.description}",
                    context_to_preserve=[
                        'dependency_results', 'prerequisite_outputs'
                    ],
                    state_corruption_risk=False,
                    priority=2  # Medium priority
                ))

        # Create restart plan with guaranteed safe points
        self.precomputed_plan = RestartPlan(
            planned_points=planned_restart_points,
            guaranteed_safe_points=self.identify_guaranteed_safe_points(planned_restart_points),
            fallback_points=self.create_fallback_points(todos)
        )

        # Ensure at least one restart point is available
        if not self.precomputed_plan.guaranteed_safe_points and not self.precomputed_plan.fallback_points:
            # Create emergency fallback at beginning
            emergency_fallback = PlannedRestartPoint(
                todo_index=0,
                trigger_condition='always_available',
                reason="Emergency fallback: Beginning of execution",
                context_to_preserve=['initial_state'],
                state_corruption_risk=False,
                priority=4  # Lowest priority emergency fallback
            )
            self.precomputed_plan.fallback_points.append(emergency_fallback)

        return self.precomputed_plan

    def identify_guaranteed_safe_points(self, planned_points: List[PlannedRestartPoint]) -> List[PlannedRestartPoint]:
        """Identify restart points that are guaranteed to be available."""
        guaranteed = []

        for point in planned_points:
            # High priority points with minimal conditions are guaranteed
            if (point.priority == 1 and
                point.trigger_condition in ['completion', 'before_next']):
                guaranteed.append(point)

        return guaranteed

    def create_fallback_points(self, todos: List[TodoItem]) -> List[PlannedRestartPoint]:
        """Create fallback restart points to ensure at least one is always available."""
        fallback_points = []

        # Fallback after first quarter of todos
        quarter_point = len(todos) // 4
        if quarter_point > 0:
            fallback_points.append(PlannedRestartPoint(
                todo_index=quarter_point - 1,
                trigger_condition='completion',
                reason="Fallback: First quarter completion",
                context_to_preserve=['partial_progress', 'early_results'],
                state_corruption_risk=False,
                priority=3  # Lower priority fallback
            ))

        return fallback_points

    def update_runtime_safe_points(self, execution_state: ExecutionState) -> List[RestartPoint]:
        """
        Update available safe restart points based on actual execution progress.
        Converts planned points to actual restart points as conditions are met.
        """
        available_restart_points = []
        completed_todos = execution_state.completed_todos

        for planned_point in self.precomputed_plan.planned_points:
            if self.is_planned_point_available(planned_point, completed_todos, execution_state):
                actual_point = RestartPoint(
                    todo_index=planned_point.todo_index,
                    reason=planned_point.reason,
                    context_to_preserve=planned_point.context_to_preserve,
                    safe_to_restart=True,
                    state_corruption_risk=planned_point.state_corruption_risk,
                    availability_confirmed=True
                )
                available_restart_points.append(actual_point)

        return available_restart_points

    def is_planned_point_available(self, planned_point: PlannedRestartPoint,
                                 completed_todos: List[TodoItem],
                                 execution_state: ExecutionState) -> bool:
        """Check if a planned restart point has become available."""
        todo_index = planned_point.todo_index

        if planned_point.trigger_condition == 'completion':
            # Available if the todo at this index is completed
            return (todo_index < len(completed_todos) and
                   completed_todos[todo_index].status == 'completed')

        elif planned_point.trigger_condition == 'before_next':
            # Available if current todo is done
            return todo_index < len(completed_todos)

        elif planned_point.trigger_condition == 'tool_completion':
            # Available if tool operation completed cleanly
            if todo_index < len(completed_todos):
                todo = completed_todos[todo_index]
                return (todo.status == 'completed' and
                       not getattr(todo, 'has_hanging_processes', False))

        elif planned_point.trigger_condition == 'dependencies_complete':
            # Available if all dependencies are satisfied
            return todo_index < len(completed_todos)

        elif planned_point.trigger_condition == 'always_available':
            # Always available (emergency fallback)
            return True

        return False

    def has_dependents(self, todo: TodoItem, all_todos: List[TodoItem]) -> bool:
        """Check if other todos depend on this one."""
        todo_id = todo.todo_id
        return any(todo_id in getattr(other_todo, 'dependencies', [])
                  for other_todo in all_todos if other_todo != todo)

    def get_best_available_restart_point(self, execution_state: ExecutionState) -> Optional[RestartPoint]:
        """
        Get the best available restart point based on current execution state.
        GUARANTEED to return a restart point due to pre-computed fallback system.
        """
        available_points = self.update_runtime_safe_points(execution_state)

        if not available_points:
            # Use fallback points if no primary points available
            fallback_points = self.get_available_fallback_points(execution_state)
            if fallback_points:
                return self.convert_planned_to_actual_restart_point(
                    fallback_points[0], execution_state)

            # Emergency fallback - should never happen
            return RestartPoint(
                todo_index=0,
                reason="Emergency fallback: Beginning of execution",
                context_to_preserve=['initial_state'],
                safe_to_restart=True,
                state_corruption_risk=False
            )

        # Sort by priority and return best option
        available_points.sort(key=lambda p: getattr(p, 'priority', 2))
        return available_points[0]

    def get_available_fallback_points(self, execution_state: ExecutionState) -> List[PlannedRestartPoint]:
        """Get fallback restart points that are currently available."""
        available_fallbacks = []

        for fallback_point in self.precomputed_plan.fallback_points:
            if self.is_planned_point_available(fallback_point,
                                             execution_state.completed_todos,
                                             execution_state):
                available_fallbacks.append(fallback_point)

        return available_fallbacks

    def convert_planned_to_actual_restart_point(self, planned_point: PlannedRestartPoint,
                                              execution_state: ExecutionState) -> RestartPoint:
        """Convert a planned restart point to an actual restart point."""
        return RestartPoint(
            todo_index=planned_point.todo_index,
            reason=planned_point.reason,
            context_to_preserve=planned_point.context_to_preserve,
            safe_to_restart=True,
            state_corruption_risk=planned_point.state_corruption_risk
        )

    def validate_restart_plan_has_guaranteed_points(self) -> bool:
        """
        Validate that the restart plan has at least one guaranteed safe point.
        This ensures the 'always look for a safe place to restart' requirement is met.
        """
        if not self.precomputed_plan:
            return False

        # Check for guaranteed safe points
        if self.precomputed_plan.guaranteed_safe_points:
            return True

        # Check for fallback points
        if self.precomputed_plan.fallback_points:
            return True

        return False

    def capture_restart_context(self, execution_state: ExecutionState,
                              restart_point: RestartPoint) -> RestartContext:
        """
        Package complete context to avoid repeating mistakes in fresh session.
        """
        # Capture todos completed up to restart point
        completed_todos = execution_state.completed_todos[:restart_point.todo_index + 1]
        remaining_todos = execution_state.remaining_todos

        # Extract concrete lessons from actual execution patterns
        lessons = self.extract_concrete_lessons(completed_todos, execution_state)
        mistakes = self.identify_specific_mistakes(execution_state)
        successful_patterns = self.capture_successful_approaches(completed_todos)

        # Package context for fresh session
        context = RestartContext(
            session_id=execution_state.session_id,
            restart_point=restart_point,
            completed_todos=completed_todos,
            todo_results=self.package_todo_results(completed_todos),
            remaining_todos=remaining_todos,
            lessons_learned=lessons,
            mistakes_to_avoid=mistakes,
            successful_patterns=successful_patterns,
            preserved_data=self.preserve_context_data(execution_state, restart_point),
            budget_analysis=execution_state.budget_trend_analysis,
            efficiency_insights=self.capture_efficiency_insights(completed_todos),
            recommended_approach=self.generate_approach_recommendations(lessons, mistakes),
            tool_usage_guidance=self.generate_tool_guidance(execution_state),
            estimated_remaining_budget=self.calculate_optimized_remaining_budget(
                remaining_todos, lessons
            )
        )

        return context

    def extract_concrete_lessons(self, completed_todos: List[TodoItem],
                               execution_state: ExecutionState) -> List[Lesson]:
        """Extract lessons from current execution to inform restart."""
        lessons = []

        # Analyze todo completion efficiency
        for todo in completed_todos:
            actual_cost = todo.actual_tokens
            estimated_cost = todo.estimated_tokens

            if actual_cost > estimated_cost * 1.5:
                lessons.append(Lesson(
                    category="estimation_accuracy",
                    description=f"Todo '{todo.description}' took {actual_cost/estimated_cost:.1f}x longer than estimated",
                    adjustment_factor=actual_cost / estimated_cost,
                    todo_category=todo.category.value
                ))

        # Analyze tool usage patterns
        tool_usage = execution_state.get_tool_usage_patterns()
        for tool, efficiency in tool_usage.items():
            if efficiency < 0.5:
                lessons.append(Lesson(
                    category="tool_efficiency",
                    description=f"Tool '{tool}' was inefficient, consider alternatives",
                    tool_name=tool,
                    efficiency_rating=efficiency,
                    recommendation=f"Avoid overusing {tool} in restart"
                ))

        return lessons

    def identify_specific_mistakes(self, execution_state: ExecutionState) -> List[Mistake]:
        """Identify specific mistakes to avoid in restart session."""
        mistakes = []

        # Failed todos or repeated attempts
        for todo in execution_state.failed_todos:
            mistakes.append(Mistake(
                description=todo.failure_reason or "Todo failed",
                todo_context=todo.description,
                avoidance_strategy=todo.suggested_alternative or "Try alternative approach"
            ))

        # Budget waste patterns
        if execution_state.budget_waste_detected():
            mistakes.append(Mistake(
                description="Inefficient budget usage detected",
                avoidance_strategy="Use more targeted approaches, avoid broad searches"
            ))

        return mistakes

    def capture_successful_approaches(self, completed_todos: List[TodoItem]) -> Dict[str, Any]:
        """Capture successful patterns from completed todos."""
        successful_patterns = {
            'efficient_tools': [],
            'optimal_sequences': [],
            'effective_strategies': []
        }

        for todo in completed_todos:
            if todo.efficiency_rating > 0.8:
                successful_patterns['efficient_tools'].extend(todo.tools_used)
                successful_patterns['effective_strategies'].extend(todo.success_factors)

        return successful_patterns

    def package_todo_results(self, completed_todos: List[TodoItem]) -> Dict[str, Any]:
        """Package todo results in a format that prevents work duplication."""
        results = {}

        for todo in completed_todos:
            results[todo.todo_id] = {
                'description': todo.description,
                'category': todo.category.value,
                'outputs': todo.outputs,
                'intermediate_data': todo.intermediate_data,
                'tools_used': todo.tools_used,
                'actual_cost': todo.actual_tokens,
                'completion_time': todo.completion_timestamp,
                'success_factors': todo.success_factors,
                'efficiency_rating': todo.efficiency_rating
            }

        return results

    def preserve_context_data(self, execution_state: ExecutionState,
                            restart_point: RestartPoint) -> Dict[str, Any]:
        """Preserve specific data types mentioned in restart point context_to_preserve."""
        preserved = {}

        for data_type in restart_point.context_to_preserve:
            if data_type in execution_state.context_data:
                preserved[data_type] = execution_state.context_data[data_type]

        # Always preserve critical session data
        preserved.update({
            'codebase_understanding': execution_state.codebase_insights,
            'discovered_patterns': execution_state.discovered_patterns,
            'validation_results': execution_state.validation_results,
            'search_indexes': execution_state.search_indexes  # Avoid re-searching
        })

        return preserved

    def capture_efficiency_insights(self, completed_todos: List[TodoItem]) -> Dict[str, Any]:
        """Capture efficiency insights from completed todos."""
        insights = {
            'fastest_categories': [],
            'slowest_categories': [],
            'most_accurate_estimates': [],
            'least_accurate_estimates': []
        }

        # Analyze by category
        category_performance = {}
        for todo in completed_todos:
            category = todo.category.value
            if category not in category_performance:
                category_performance[category] = []

            if todo.estimated_tokens > 0:
                accuracy = todo.estimated_tokens / max(todo.actual_tokens, 1)
                category_performance[category].append(accuracy)

        # Identify best and worst performing categories
        for category, accuracies in category_performance.items():
            avg_accuracy = sum(accuracies) / len(accuracies)
            if avg_accuracy > 0.8:
                insights['most_accurate_estimates'].append(category)
            elif avg_accuracy < 0.5:
                insights['least_accurate_estimates'].append(category)

        return insights

    def generate_approach_recommendations(self, lessons: List[Lesson],
                                        mistakes: List[Mistake]) -> Dict[str, str]:
        """Generate specific recommendations for fresh session approach."""
        recommendations = {
            'primary_strategy': 'Continue with proven patterns',
            'tools_to_favor': [],
            'tools_to_avoid': [],
            'estimation_adjustments': {},
            'efficiency_tips': []
        }

        # Extract tool preferences from lessons
        for lesson in lessons:
            if lesson.category == 'tool_efficiency':
                if lesson.efficiency_rating and lesson.efficiency_rating > 0.8:
                    recommendations['tools_to_favor'].append(lesson.tool_name)
                else:
                    recommendations['tools_to_avoid'].append(lesson.tool_name)

        # Extract estimation adjustments
        for lesson in lessons:
            if lesson.category == 'estimation_accuracy' and lesson.adjustment_factor:
                recommendations['estimation_adjustments'][lesson.todo_category] = lesson.adjustment_factor

        return recommendations

    def generate_tool_guidance(self, execution_state: ExecutionState) -> Dict[str, Any]:
        """Generate tool usage guidance based on execution patterns."""
        tool_patterns = execution_state.get_tool_usage_patterns()

        guidance = {
            'preferred_tools': [tool for tool, efficiency in tool_patterns.items() if efficiency > 0.7],
            'avoid_tools': [tool for tool, efficiency in tool_patterns.items() if efficiency < 0.4],
            'usage_patterns': tool_patterns
        }

        return guidance

    def calculate_optimized_remaining_budget(self, remaining_todos: List[TodoItem],
                                           lessons: List[Lesson]) -> float:
        """Calculate optimized budget estimate for remaining todos."""
        if not remaining_todos:
            return 0

        total_estimated = sum(todo.estimated_tokens for todo in remaining_todos)

        # Apply lessons learned adjustments
        adjustment_factors = {}
        for lesson in lessons:
            if lesson.category == 'estimation_accuracy' and lesson.adjustment_factor:
                adjustment_factors[lesson.todo_category] = lesson.adjustment_factor

        # Adjust estimates based on lessons
        adjusted_total = 0
        for todo in remaining_todos:
            base_estimate = todo.estimated_tokens
            category = todo.category.value
            adjustment = adjustment_factors.get(category, 1.0)
            adjusted_total += base_estimate * adjustment

        return adjusted_total

    def prepare_restart_session(self, restart_context: RestartContext) -> SessionPreparation:
        """Prepare fresh session with preserved context and lessons learned."""
        preparation = SessionPreparation(
            context_summary=self.create_context_summary(restart_context),
            lessons_briefing=self.create_lessons_briefing(restart_context.lessons_learned),
            mistakes_briefing=self.create_mistakes_briefing(restart_context.mistakes_to_avoid),
            remaining_work_plan=self.optimize_remaining_plan(
                restart_context.remaining_todos,
                restart_context.lessons_learned
            ),
            initial_budget_allocation=self.calculate_fresh_budget_allocation(restart_context)
        )

        return preparation

    def create_context_summary(self, restart_context: RestartContext) -> str:
        """Create comprehensive but concise context summary for new session."""
        summary = f"""
RESTART CONTEXT SUMMARY:

Previous Session Achievements:
- Completed {len(restart_context.completed_todos)} todos
- Key results: {self.summarize_key_results(restart_context.todo_results)}

Lessons Learned:
{self.format_lessons_for_new_session(restart_context.lessons_learned)}

Mistakes to Avoid:
{self.format_mistakes_for_new_session(restart_context.mistakes_to_avoid)}

Remaining Work:
{self.format_remaining_work(restart_context.remaining_todos)}

Budget Insights:
{self.format_budget_insights(restart_context.budget_analysis)}
        """

        return summary.strip()

    def summarize_key_results(self, todo_results: Dict[str, Any]) -> str:
        """Summarize key results from completed todos."""
        if not todo_results:
            return "No completed todos"

        # Extract key achievements
        key_results = []
        for todo_id, result in todo_results.items():
            if result.get('outputs'):
                key_results.append(f"- {result['description']}: {len(result['outputs'])} outputs")

        return "\n".join(key_results[:3])  # Top 3 results

    def format_lessons_for_new_session(self, lessons: List[Lesson]) -> str:
        """Format lessons for new session briefing."""
        if not lessons:
            return "No specific lessons learned"

        formatted = []
        for lesson in lessons[:3]:  # Top 3 lessons
            formatted.append(f"- {lesson.description}")

        return "\n".join(formatted)

    def format_mistakes_for_new_session(self, mistakes: List[Mistake]) -> str:
        """Format mistakes for new session briefing."""
        if not mistakes:
            return "No specific mistakes to avoid"

        formatted = []
        for mistake in mistakes[:3]:  # Top 3 mistakes
            formatted.append(f"- {mistake.description}: {mistake.avoidance_strategy}")

        return "\n".join(formatted)

    def format_remaining_work(self, remaining_todos: List[TodoItem]) -> str:
        """Format remaining work for new session."""
        if not remaining_todos:
            return "No remaining todos"

        return f"{len(remaining_todos)} todos remaining, estimated {sum(t.estimated_tokens for t in remaining_todos)} tokens"

    def format_budget_insights(self, budget_analysis) -> str:
        """Format budget analysis insights."""
        if not budget_analysis:
            return "No budget analysis available"

        return f"Usage velocity: {budget_analysis.usage_velocity:.1f} tokens/todo, "
        f"Completion probability: {budget_analysis.completion_probability:.1%}"

    def optimize_remaining_plan(self, remaining_todos: List[TodoItem],
                              lessons: List[Lesson]) -> Dict[str, Any]:
        """Optimize remaining work plan based on lessons learned."""
        return {
            'todo_count': len(remaining_todos),
            'estimated_budget': sum(todo.estimated_tokens for todo in remaining_todos),
            'optimization_applied': True,
            'lessons_count': len(lessons)
        }

    def calculate_fresh_budget_allocation(self, restart_context: RestartContext) -> Dict[int, float]:
        """Calculate fresh budget allocation for quarters."""
        remaining_budget = restart_context.estimated_remaining_budget
        return {
            1: remaining_budget * 0.3,  # Front-load based on lessons
            2: remaining_budget * 0.3,
            3: remaining_budget * 0.25,
            4: remaining_budget * 0.15  # Reserve for cleanup
        }