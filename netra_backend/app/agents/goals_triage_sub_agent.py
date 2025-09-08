"""GoalsTriageSubAgent - Golden Pattern Implementation

Specialized agent for triaging and prioritizing business goals and objectives:
- Inherits all infrastructure from BaseAgent (reliability, execution, WebSocket events)
- Contains ONLY goal-specific triage and prioritization business logic
- Clean single inheritance pattern with zero infrastructure duplication
- Complete SSOT compliance for optimal maintainability

Business Value: Strategic goal prioritization for optimal business outcomes
BVJ: ALL segments | Strategic Planning | Converts raw goals into actionable priorities
"""

import time
from typing import Any, Dict, List, Optional
from enum import Enum

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.logging_config import central_logger
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.database.session_manager import DatabaseSessionManager
from netra_backend.app.core.serialization.unified_json_handler import (
    LLMResponseParser,
    JSONErrorFixer,
    UnifiedJSONHandler
)
from netra_backend.app.core.unified_error_handler import agent_error_handler
from netra_backend.app.schemas.shared_types import ErrorContext
from datetime import datetime, timezone
from uuid import uuid4

logger = central_logger.get_logger(__name__)


class GoalPriority(Enum):
    """Priority levels for business goals."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    DEFERRED = "deferred"


class GoalCategory(Enum):
    """Categories of business goals."""
    REVENUE = "revenue"
    COST_OPTIMIZATION = "cost_optimization"
    USER_EXPERIENCE = "user_experience"
    TECHNICAL_DEBT = "technical_debt"
    COMPLIANCE = "compliance"
    STRATEGIC = "strategic"
    OPERATIONAL = "operational"


class GoalTriageResult:
    """Result of goal triage analysis."""
    
    def __init__(self, 
                 goal_id: str,
                 original_goal: str,
                 priority: GoalPriority,
                 category: GoalCategory,
                 confidence_score: float,
                 rationale: str,
                 estimated_impact: str,
                 resource_requirements: Dict[str, Any],
                 timeline_estimate: str,
                 dependencies: List[str],
                 risk_assessment: Dict[str, Any]):
        self.goal_id = goal_id
        self.original_goal = original_goal
        self.priority = priority
        self.category = category
        self.confidence_score = confidence_score
        self.rationale = rationale
        self.estimated_impact = estimated_impact
        self.resource_requirements = resource_requirements
        self.timeline_estimate = timeline_estimate
        self.dependencies = dependencies
        self.risk_assessment = risk_assessment
        self.triage_timestamp = time.time()


class GoalsTriageSubAgent(BaseAgent):
    """Golden Pattern Goals Triage Agent.
    
    SSOT Compliance: Contains ONLY goal triage and prioritization business logic
    - All infrastructure (reliability, execution, WebSocket events) inherited from BaseAgent
    - WebSocket events critical for chat value delivery to users
    - Zero infrastructure duplication - follows golden pattern exactly
    """
    
    def __init__(self):
        """Initialize with BaseAgent infrastructure."""
        # Initialize BaseAgent with full infrastructure
        super().__init__(
            name="GoalsTriageSubAgent", 
            description="Triages and prioritizes business goals for strategic planning",
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,          # Enable caching for goal analysis
        )
        
    async def validate_preconditions(self, context: UserExecutionContext, user_request: str) -> bool:
        """Validate execution preconditions for goal triage."""
        if not user_request:
            self.logger.warning(f"No user request provided for goal triage in run_id: {context.run_id}")
            return False
            
        # Check if the request contains goals to triage
        goals_indicators = ["goal", "objective", "target", "achieve", "priority", "plan"]
        request_lower = user_request.lower()
        
        if not any(indicator in request_lower for indicator in goals_indicators):
            self.logger.warning(f"Request doesn't appear to contain goals to triage: {context.run_id}")
            # Still continue - we can provide guidance on goal setting
            
        return True

    async def execute_core_logic(self, context: UserExecutionContext, user_request: str, session_manager: DatabaseSessionManager) -> Dict[str, Any]:
        """Execute core goal triage logic with WebSocket events."""
        start_time = time.time()
        
        # CRITICAL: Emit agent_started for proper chat value delivery
        await self.emit_agent_started("Analyzing and prioritizing business goals for strategic planning")
        
        # WebSocket events for user visibility
        await self.emit_thinking("Starting goal triage analysis...")
        await self.emit_thinking("Extracting goals and objectives from user request...")
        
        # Business logic with progress updates
        await self.emit_progress("Identifying individual goals and requirements...")
        goals = await self._extract_goals_from_request(context, user_request)
        
        await self.emit_progress("Analyzing goal priorities and strategic impact...")
        triage_results = await self._triage_goals(context, goals)
        
        await self.emit_progress("Creating prioritized action plan...")
        prioritized_plan = await self._create_prioritized_plan(context, triage_results)
        
        await self.emit_progress("Finalizing strategic recommendations...")
        result = await self._finalize_goal_triage_result(context, triage_results, prioritized_plan, session_manager)
        
        # Completion events
        await self.emit_progress("Goal triage and prioritization completed successfully", is_complete=True)
        
        # CRITICAL: Emit agent_completed for proper chat value delivery
        execution_time_ms = (time.time() - start_time) * 1000
        result_data = {
            "success": True,
            "goals_analyzed": len(triage_results),
            "high_priority_goals": len([g for g in triage_results if g.priority in [GoalPriority.CRITICAL, GoalPriority.HIGH]]),
            "execution_time_ms": execution_time_ms,
            "categories_identified": len(set(g.category for g in triage_results))
        }
        await self.emit_agent_completed(result_data)
        
        return result

    async def _extract_goals_from_request(self, context: UserExecutionContext, user_request: str) -> List[str]:
        """Extract goals and objectives from the user request with tool transparency."""
        # Show tool execution for transparency
        await self.emit_tool_executing("goal_extractor", {"input_size_chars": len(user_request)})
        
        # Use LLM to extract goals
        extraction_prompt = f"""
        Analyze the following user request and extract all business goals, objectives, and targets mentioned:
        
        User Request: {user_request}
        
        Extract each goal as a separate item. If no explicit goals are mentioned, 
        infer reasonable business goals based on the context.
        
        Return as a JSON array of strings, each representing one goal.
        """
        
        try:
            llm_response = await self.llm_manager.ask_llm(
                extraction_prompt,
                llm_config_name='default'
            )
            
            # Parse the response to extract goals
            goals = self._parse_goals_from_llm_response(llm_response)
            
            await self.emit_tool_completed("goal_extractor", {
                "goals_extracted": len(goals),
                "response_size_chars": len(llm_response)
            })
            
            return goals
            
        except Exception as e:
            # Create error context with user execution context details
            error_context = ErrorContext(
                trace_id=str(uuid4()),
                operation="goal_extraction",
                agent_name="GoalsTriageSubAgent",
                operation_name="extract_goals_from_request",
                user_id=context.user_id,
                run_id=context.run_id,
                timestamp=datetime.now(timezone.utc),
                details={"user_request_length": len(user_request)}
            )
            
            # Handle error using unified error handler
            await agent_error_handler.handle_error(e, error_context)
            
            await self.emit_tool_completed("goal_extractor", {"error": str(e), "fallback_used": True})
            
            # Fallback: use basic text analysis
            return self._extract_goals_fallback(user_request)

    async def _triage_goals(self, context: UserExecutionContext, goals: List[str]) -> List[GoalTriageResult]:
        """Triage and prioritize the extracted goals."""
        triage_results = []
        
        for i, goal in enumerate(goals):
            await self.emit_tool_executing(f"goal_analyzer_{i+1}", {"goal": goal[:50] + "..."})
            
            # Analyze each goal for priority and category
            analysis_result = await self._analyze_single_goal(context, goal, i)
            triage_results.append(analysis_result)
            
            await self.emit_tool_completed(f"goal_analyzer_{i+1}", {
                "priority": analysis_result.priority.value,
                "category": analysis_result.category.value,
                "confidence": analysis_result.confidence_score
            })
        
        return triage_results

    async def _analyze_single_goal(self, context: UserExecutionContext, goal: str, goal_index: int) -> GoalTriageResult:
        """Analyze a single goal for priority, category, and other attributes."""
        
        analysis_prompt = f"""
        Analyze this business goal and provide strategic triage information:
        
        Goal: {goal}
        
        Please provide:
        1. Priority level (critical/high/medium/low/deferred)
        2. Category (revenue/cost_optimization/user_experience/technical_debt/compliance/strategic/operational)
        3. Confidence score (0.0-1.0)
        4. Rationale for the priority
        5. Estimated business impact
        6. Resource requirements (time, people, budget)
        7. Timeline estimate
        8. Dependencies
        9. Risk assessment
        
        Return as JSON with these exact fields:
        {{
            "priority": "high",
            "category": "revenue", 
            "confidence_score": 0.8,
            "rationale": "...",
            "estimated_impact": "...",
            "resource_requirements": {{"time": "...", "people": "...", "budget": "..."}},
            "timeline_estimate": "...",
            "dependencies": ["..."],
            "risk_assessment": {{"probability": "...", "impact": "...", "mitigation": "..."}}
        }}
        """
        
        try:
            llm_response = await self.llm_manager.ask_llm(
                analysis_prompt,
                llm_config_name='default'
            )
            
            # Parse LLM response and create result
            analysis_data = self._parse_goal_analysis_response(llm_response)
            
            return GoalTriageResult(
                goal_id=f"goal_{goal_index + 1}",
                original_goal=goal,
                priority=GoalPriority(analysis_data.get("priority", "medium")),
                category=GoalCategory(analysis_data.get("category", "operational")),
                confidence_score=analysis_data.get("confidence_score", 0.7),
                rationale=analysis_data.get("rationale", "Standard business priority analysis"),
                estimated_impact=analysis_data.get("estimated_impact", "Moderate positive impact expected"),
                resource_requirements=analysis_data.get("resource_requirements", {}),
                timeline_estimate=analysis_data.get("timeline_estimate", "3-6 months"),
                dependencies=analysis_data.get("dependencies", []),
                risk_assessment=analysis_data.get("risk_assessment", {})
            )
            
        except Exception as e:
            # Create error context with user execution context details
            error_context = ErrorContext(
                trace_id=str(uuid4()),
                operation="goal_analysis",
                agent_name="GoalsTriageSubAgent",
                operation_name="analyze_single_goal",
                user_id=context.user_id,
                run_id=context.run_id,
                timestamp=datetime.now(timezone.utc),
                details={
                    "goal_index": goal_index,
                    "goal_text": goal[:100],  # First 100 chars for context
                    "goal_length": len(goal)
                }
            )
            
            # Handle error using unified error handler
            await agent_error_handler.handle_error(e, error_context)
            
            # Fallback analysis
            return self._create_fallback_goal_analysis(goal, goal_index)

    async def _create_prioritized_plan(self, context: UserExecutionContext, triage_results: List[GoalTriageResult]) -> Dict[str, Any]:
        """Create a prioritized execution plan from triaged goals."""
        
        # Sort goals by priority
        priority_order = [GoalPriority.CRITICAL, GoalPriority.HIGH, GoalPriority.MEDIUM, GoalPriority.LOW, GoalPriority.DEFERRED]
        sorted_goals = sorted(triage_results, key=lambda g: priority_order.index(g.priority))
        
        # Group by category for strategic planning
        categories = {}
        for goal in sorted_goals:
            if goal.category.value not in categories:
                categories[goal.category.value] = []
            categories[goal.category.value].append(goal)
        
        # Create execution phases
        immediate_goals = [g for g in sorted_goals if g.priority in [GoalPriority.CRITICAL, GoalPriority.HIGH]]
        medium_term_goals = [g for g in sorted_goals if g.priority == GoalPriority.MEDIUM]
        long_term_goals = [g for g in sorted_goals if g.priority in [GoalPriority.LOW, GoalPriority.DEFERRED]]
        
        return {
            "execution_phases": {
                "immediate": [self._goal_to_dict(g) for g in immediate_goals],
                "medium_term": [self._goal_to_dict(g) for g in medium_term_goals],
                "long_term": [self._goal_to_dict(g) for g in long_term_goals]
            },
            "strategic_categories": categories,
            "total_goals": len(triage_results),
            "priority_distribution": {
                priority.value: len([g for g in sorted_goals if g.priority == priority])
                for priority in GoalPriority
            }
        }

    async def _finalize_goal_triage_result(self, context: UserExecutionContext, 
                                         triage_results: List[GoalTriageResult],
                                         prioritized_plan: Dict[str, Any],
                                         session_manager: DatabaseSessionManager) -> Dict[str, Any]:
        """Finalize and structure the goal triage results."""
        
        # Structure the result data
        goal_triage_result = {
            "triage_results": [self._goal_to_dict(g) for g in triage_results],
            "prioritized_plan": prioritized_plan,
            "metadata": {
                "total_goals_analyzed": len(triage_results),
                "analysis_timestamp": time.time(),
                "high_confidence_goals": len([g for g in triage_results if g.confidence_score >= 0.8]),
                "agent_version": "1.0.0",
                "user_id": context.user_id,
                "run_id": context.run_id,
                "thread_id": context.thread_id
            }
        }
        
        # Store result in context metadata for proper isolation
        if "goal_triage_results" not in context.metadata:
            context.metadata["goal_triage_results"] = []
        context.metadata["goal_triage_results"].append(goal_triage_result)
        
        return {
            "goal_triage_result": goal_triage_result,
            "recommendations": self._generate_strategic_recommendations(triage_results, prioritized_plan)
        }

    def _parse_goals_from_llm_response(self, response: str) -> List[str]:
        """Parse goals from LLM response using SSOT unified JSON handler."""
        # Use SSOT LLMResponseParser for safe JSON parsing
        parser = LLMResponseParser()
        parsed_goals = parser.safe_json_parse(response, fallback=None)
        
        # If we got a valid list, process it
        if isinstance(parsed_goals, list):
            return [str(goal) for goal in parsed_goals if goal]
        
        # Fallback: extract goals from text using existing logic
        lines = response.strip().split('\n')
        goals = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('{') and not line.startswith('['):
                # Remove common prefixes
                for prefix in ['- ', '* ', '• ', '1. ', '2. ', '3. ', '4. ', '5. ']:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break
                goals.append(line)
        
        return goals if goals else ["Improve business performance and user satisfaction"]

    def _parse_goal_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse goal analysis response from LLM using SSOT unified JSON handler."""
        # Use SSOT LLMResponseParser for proper JSON handling with error recovery
        parser = LLMResponseParser()
        parsed_response = parser.ensure_agent_response_is_json(response)
        
        # If we got a valid parsed response with expected structure, use it
        if isinstance(parsed_response, dict) and parsed_response.get("parsed", True):
            # Remove metadata fields added by ensure_agent_response_is_json if present
            clean_response = {k: v for k, v in parsed_response.items() 
                            if k not in ["type", "parsed", "message"]}
            if clean_response:
                return clean_response
        
        # If parsing failed or response is malformed, use fallback with error recovery
        if isinstance(parsed_response, dict) and not parsed_response.get("parsed", True):
            # Log the parsing issue for debugging
            self.logger.warning(f"LLM response parsing failed: {parsed_response.get('message', 'Unknown error')}")
            
            # Try to recover using JSONErrorFixer if we have raw_response
            if "raw_response" in parsed_response:
                error_fixer = JSONErrorFixer()
                recovered = error_fixer.recover_truncated_json(parsed_response["raw_response"])
                if recovered and isinstance(recovered, dict):
                    return recovered
        
        # Final fallback analysis
        return {
            "priority": "medium",
            "category": "operational",
            "confidence_score": 0.6,
            "rationale": "Automated analysis based on standard business priorities",
            "estimated_impact": "Positive impact on business operations expected",
            "resource_requirements": {"time": "moderate", "people": "2-3 team members", "budget": "standard"},
            "timeline_estimate": "3-6 months",
            "dependencies": [],
            "risk_assessment": {"probability": "low", "impact": "manageable", "mitigation": "standard risk management"}
        }

    def _extract_goals_fallback(self, user_request: str) -> List[str]:
        """Fallback goal extraction using basic text analysis."""
        # Look for goal-related keywords and extract surrounding context
        goal_keywords = ["achieve", "goal", "target", "objective", "aim", "want to", "need to", "improve", "optimize", "reduce", "increase"]
        
        sentences = user_request.split('.')
        potential_goals = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if any(keyword in sentence.lower() for keyword in goal_keywords):
                potential_goals.append(sentence)
        
        return potential_goals if potential_goals else ["Optimize business operations based on user requirements"]

    def _create_fallback_goal_analysis(self, goal: str, goal_index: int) -> GoalTriageResult:
        """Create fallback analysis when LLM analysis fails."""
        # Simple heuristic analysis
        goal_lower = goal.lower()
        
        # Determine priority based on keywords
        if any(word in goal_lower for word in ["critical", "urgent", "immediate", "crisis"]):
            priority = GoalPriority.CRITICAL
        elif any(word in goal_lower for word in ["important", "high", "priority", "asap"]):
            priority = GoalPriority.HIGH
        elif any(word in goal_lower for word in ["future", "eventually", "consider"]):
            priority = GoalPriority.LOW
        else:
            priority = GoalPriority.MEDIUM
        
        # Determine category based on keywords
        if any(word in goal_lower for word in ["revenue", "sales", "profit", "money", "income"]):
            category = GoalCategory.REVENUE
        elif any(word in goal_lower for word in ["cost", "expense", "budget", "save", "reduce"]):
            category = GoalCategory.COST_OPTIMIZATION
        elif any(word in goal_lower for word in ["user", "customer", "experience", "satisfaction"]):
            category = GoalCategory.USER_EXPERIENCE
        elif any(word in goal_lower for word in ["technical", "code", "debt", "refactor", "upgrade"]):
            category = GoalCategory.TECHNICAL_DEBT
        elif any(word in goal_lower for word in ["compliance", "regulation", "audit", "security"]):
            category = GoalCategory.COMPLIANCE
        elif any(word in goal_lower for word in ["strategic", "vision", "long-term", "roadmap"]):
            category = GoalCategory.STRATEGIC
        else:
            category = GoalCategory.OPERATIONAL
        
        return GoalTriageResult(
            goal_id=f"goal_{goal_index + 1}",
            original_goal=goal,
            priority=priority,
            category=category,
            confidence_score=0.6,  # Lower confidence for fallback
            rationale="Automated analysis using keyword heuristics",
            estimated_impact="Moderate positive business impact expected",
            resource_requirements={"time": "moderate", "people": "2-3 team members", "budget": "standard allocation"},
            timeline_estimate="3-6 months",
            dependencies=["Stakeholder approval", "Resource allocation"],
            risk_assessment={"probability": "medium", "impact": "manageable", "mitigation": "Regular monitoring and adjustment"}
        )

    def _goal_to_dict(self, goal: GoalTriageResult) -> Dict[str, Any]:
        """Convert GoalTriageResult to dictionary for serialization."""
        return {
            "goal_id": goal.goal_id,
            "original_goal": goal.original_goal,
            "priority": goal.priority.value,
            "category": goal.category.value,
            "confidence_score": goal.confidence_score,
            "rationale": goal.rationale,
            "estimated_impact": goal.estimated_impact,
            "resource_requirements": goal.resource_requirements,
            "timeline_estimate": goal.timeline_estimate,
            "dependencies": goal.dependencies,
            "risk_assessment": goal.risk_assessment,
            "triage_timestamp": goal.triage_timestamp
        }

    def _generate_strategic_recommendations(self, triage_results: List[GoalTriageResult], 
                                          prioritized_plan: Dict[str, Any]) -> List[str]:
        """Generate strategic recommendations based on goal analysis."""
        recommendations = []
        
        # Analyze priority distribution
        critical_count = len([g for g in triage_results if g.priority == GoalPriority.CRITICAL])
        high_count = len([g for g in triage_results if g.priority == GoalPriority.HIGH])
        
        if critical_count > 3:
            recommendations.append("Consider if all 'critical' goals are truly critical - focus may be too dispersed")
        
        if critical_count + high_count > len(triage_results) * 0.6:
            recommendations.append("High percentage of high-priority goals - consider resource constraints and timeline feasibility")
        
        # Analyze category distribution
        categories = set(g.category for g in triage_results)
        if len(categories) > 5:
            recommendations.append("Goals span many categories - consider focusing on 2-3 strategic areas for better execution")
        
        # Resource and timeline analysis
        immediate_goals = prioritized_plan["execution_phases"]["immediate"]
        if len(immediate_goals) > 5:
            recommendations.append("Many immediate goals identified - prioritize top 3 for focused execution")
        
        # Default recommendations
        recommendations.extend([
            "Review goal dependencies to identify potential bottlenecks",
            "Assign clear ownership and accountability for each priority goal",
            "Establish regular progress tracking and review cycles",
            "Consider quick wins to build momentum while working on strategic goals"
        ])
        
        return recommendations

    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute goal triage with proper user context isolation.
        
        Args:
            context: User execution context with isolated database session
            stream_updates: Whether to stream progress updates via WebSocket
            
        Returns:
            Goal triage results with priorities and recommendations
            
        Raises:
            ValueError: If context validation fails
            RuntimeError: If goal triage processing fails
        """
        # Validate context at entry point
        self._validate_context(context)
        
        # Extract user request from context metadata or raise error
        user_request = self._extract_user_request(context)
        
        self.logger.info(f"GoalsTriageSubAgent executing for user {context.user_id}, run {context.run_id}")
        
        # Create database session manager from context
        session_manager = DatabaseSessionManager()
        
        try:
            # Validate preconditions
            if not await self.validate_preconditions(context, user_request):
                raise ValueError("Goal triage preconditions not met")
            
            # Execute core logic with session isolation
            result = await self.execute_core_logic(context, user_request, session_manager)
            
            self.logger.info(f"GoalsTriageSubAgent completed successfully for user {context.user_id}")
            return result
            
        except Exception as e:
            # Create error context with user execution context details
            error_context = ErrorContext(
                trace_id=str(uuid4()),
                operation="execute",
                agent_name="GoalsTriageSubAgent",
                operation_name="execute",
                user_id=context.user_id,
                run_id=context.run_id,
                thread_id=context.thread_id,
                timestamp=datetime.now(timezone.utc),
                details={"stream_updates": stream_updates}
            )
            
            # Handle error using unified error handler
            await agent_error_handler.handle_error(e, error_context)
            
            # Execute fallback logic if main execution fails
            if stream_updates:
                await self.emit_thinking("Switching to fallback goal analysis due to processing issues...")
            
            return await self._execute_fallback_logic(context, user_request, session_manager)
            
        finally:
            # Ensure session cleanup
            try:
                await session_manager.close()
            except Exception as cleanup_error:
                # Create error context for cleanup failure
                cleanup_error_context = ErrorContext(
                    trace_id=str(uuid4()),
                    operation="session_cleanup",
                    agent_name="GoalsTriageSubAgent",
                    operation_name="execute_cleanup",
                    user_id=context.user_id,
                    run_id=context.run_id,
                    timestamp=datetime.now(timezone.utc),
                    details={"cleanup_operation": "session_manager.close()"}
                )
                
                # Handle cleanup error using unified error handler
                await agent_error_handler.handle_error(cleanup_error, cleanup_error_context)
        
    def _validate_context(self, context: UserExecutionContext) -> None:
        """Validate UserExecutionContext for goal triage.
        
        Args:
            context: User execution context to validate
            
        Raises:
            ValueError: If context is invalid or missing required data
        """
        if not isinstance(context, UserExecutionContext):
            raise ValueError(f"Expected UserExecutionContext, got {type(context)}")
        
        if not context.user_id:
            raise ValueError("Context must have valid user_id for proper isolation")
        
        if not context.run_id:
            raise ValueError("Context must have valid run_id for tracking")
        
        if not context.thread_id:
            raise ValueError("Context must have valid thread_id for conversation tracking")
        
        # Validate session isolation
        if not context.db_session:
            raise ValueError("Context must include database session for proper isolation")
        
        self.logger.debug(f"Context validation passed for user {context.user_id}, run {context.run_id}")
    
    def _extract_user_request(self, context: UserExecutionContext) -> str:
        """Extract user request from context metadata.
        
        Args:
            context: User execution context
            
        Returns:
            User request text
            
        Raises:
            ValueError: If user request is not found in context
        """
        user_request = context.metadata.get('user_request')
        if not user_request:
            # Try alternative keys
            user_request = context.metadata.get('request')
        
        if not user_request:
            raise ValueError(
                "No user request found in context metadata. "
                "Context must include 'user_request' or 'request' in metadata."
            )
        
        return str(user_request)
        
    async def _execute_fallback_logic(self, context: UserExecutionContext, 
                                    user_request: str, 
                                    session_manager: DatabaseSessionManager) -> Dict[str, Any]:
        """Fallback execution with proper WebSocket events and user isolation.
        
        Args:
            context: User execution context
            user_request: The user's request text
            session_manager: Database session manager for this request
            
        Returns:
            Fallback goal triage results
        """
        await self.emit_agent_started("Creating fallback goal triage due to processing issues")
        await self.emit_thinking("Switching to fallback goal analysis...")
            
        self.logger.warning(f"Using fallback goal triage for user {context.user_id}, run_id: {context.run_id}")
        
        # Simple fallback goal analysis with user isolation
        fallback_result = {
            "triage_results": [{
                "goal_id": "goal_1",
                "original_goal": user_request,
                "priority": "medium",
                "category": "operational",
                "confidence_score": 0.5,
                "rationale": "Fallback analysis - manual review recommended",
                "estimated_impact": "Positive impact expected - requires detailed analysis",
                "resource_requirements": {"time": "to be determined", "people": "to be assigned", "budget": "to be evaluated"},
                "timeline_estimate": "to be determined",
                "dependencies": ["Detailed requirements analysis"],
                "risk_assessment": {"probability": "unknown", "impact": "to be assessed", "mitigation": "thorough planning required"},
                "triage_timestamp": time.time()
            }],
            "prioritized_plan": {
                "execution_phases": {
                    "immediate": [],
                    "medium_term": [{"goal_id": "goal_1", "fallback": True}],
                    "long_term": []
                }
            },
            "metadata": {
                "total_goals_analyzed": 1,
                "analysis_timestamp": time.time(),
                "fallback_used": True,
                "agent_version": "1.0.0",
                "user_id": context.user_id,
                "run_id": context.run_id,
                "thread_id": context.thread_id
            }
        }
        
        # Store result in context metadata for proper isolation
        if "goal_triage_results" not in context.metadata:
            context.metadata["goal_triage_results"] = []
        context.metadata["goal_triage_results"].append(fallback_result)
        
        await self.emit_agent_completed({
            "success": True,
            "fallback_used": True,
            "goals_analyzed": 1,
            "message": "Goal triage completed using fallback method - manual review recommended"
        })
        
        return {
            "goal_triage_result": fallback_result,
            "recommendations": ["Manual review recommended for comprehensive goal analysis"]
        }
    
    @classmethod
    def create_agent_with_context(cls, context) -> 'GoalsTriageSubAgent':
        """Factory method for creating GoalsTriageSubAgent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            GoalsTriageSubAgent: Configured agent instance
        """
        # GoalsTriageSubAgent takes no constructor parameters
        return cls()

