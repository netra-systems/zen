"""Optimizations Core Sub-Agent using Golden Pattern

Clean optimization agent following BaseAgent golden pattern.
Contains ONLY optimization-specific business logic - all infrastructure 
(reliability, execution, WebSocket events) inherited from BaseAgent.

Business Value: Core optimization recommendations drive customer cost savings.
Target segments: Growth & Enterprise. High revenue impact through performance fees.
BVJ: Growth & Enterprise | Performance & Cost Optimization | +30% cost reduction for customers
"""

from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.prompts import optimizations_core_prompt_template
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.agents.utils import extract_json_from_response
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class OptimizationsCoreSubAgent(BaseAgent):
    """Clean optimization agent using BaseAgent infrastructure.
    
    Contains ONLY optimization-specific business logic - all infrastructure 
    (reliability, execution, WebSocket events) inherited from BaseAgent.
    """
    
    def __init__(self, llm_manager: Optional[LLMManager] = None, 
                 tool_dispatcher: Optional[UnifiedToolDispatcher] = None,
                 websocket_manager: Optional[Any] = None):
        """Initialize OptimizationsCoreSubAgent.
        
        CRITICAL: LLM manager is required for this agent to function.
        During architectural migration, some instantiation paths don't provide it.
        See FIVE_WHYS_ANALYSIS_20250904.md for root cause analysis.
        """
        # Initialize BaseAgent with full infrastructure
        # Only pass tool_dispatcher if it's not None to avoid deprecation warning
        base_kwargs = {
            "llm_manager": llm_manager,
            "name": "OptimizationsCoreSubAgent", 
            "description": "Enhanced optimization agent using UserExecutionContext pattern",
            "enable_reliability": True,      # Get circuit breaker + retry
            "enable_execution_engine": True, # Get modern execution patterns
            "enable_caching": True,          # Enable caching for optimization results
        }
        
        # FIVE WHYS FIX: Validate critical dependency at construction time
        if llm_manager is None:
            import warnings
            warnings.warn(
                "OptimizationsCoreSubAgent instantiated without LLMManager - "
                "will fail at runtime if LLM operations are attempted. "
                "This is a known issue from incomplete architectural migration.",
                RuntimeWarning,
                stacklevel=2
            )
        
        # Only add tool_dispatcher if it's provided to avoid deprecation warning
        if tool_dispatcher is not None:
            base_kwargs["tool_dispatcher"] = tool_dispatcher
            
        super().__init__(**base_kwargs)
        self.tool_dispatcher = tool_dispatcher
        self.websocket_manager = websocket_manager

    async def _validate_context_data(self, context: UserExecutionContext) -> bool:
        """Validate execution preconditions for optimization analysis."""
        # Get data from context metadata - agents store execution state there
        data_result = context.metadata.get('data_result')
        triage_result = context.metadata.get('triage_result')
        
        if not data_result:
            self.logger.warning(f"No data result available for optimization in run_id: {context.run_id}")
            return False
            
        if not triage_result:
            self.logger.warning(f"No triage result available for optimization in run_id: {context.run_id}")
            return False
            
        if not self.llm_manager:
            self.logger.error(f"No LLM manager available for optimization in run_id: {context.run_id}")
            return False
            
        return True
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Dict[str, Any]:
        """Execute optimization analysis with proper session isolation.
        
        Args:
            context: User execution context with database session
            stream_updates: Whether to stream progress updates
            
        Returns:
            Dict with optimization analysis results
            
        Raises:
            ValueError: If context validation fails
        """
        logger.info(f"OptimizationsCoreSubAgent executing for user {context.user_id}, run {context.run_id}")
        
        # Validate context at method entry
        if not isinstance(context, UserExecutionContext):
            raise ValueError(f"Invalid context type: {type(context)}")
        
        # Validate required data is available
        if not await self._validate_context_data(context):
            raise ValueError("Required data not available for optimization analysis")
        
        # Use SSOT database session pattern instead of legacy DatabaseSessionManager
        # session_manager = DatabaseSessionManager(context)  # LEGACY - removed
        session_manager = None  # Updated to use SSOT get_db() pattern directly
        
        try:
            if stream_updates:
                await self._emit_agent_started(context)
            
            # Execute optimization analysis workflow with session isolation
            result = await self._execute_optimization_workflow(context, session_manager, stream_updates)
            
            if stream_updates:
                await self._emit_agent_completed(context, result)
            
            logger.info(f"OptimizationsCoreSubAgent completed for user {context.user_id}")
            return result
            
        except Exception as e:
            error_msg = f"Optimization analysis failed: {str(e)}"
            logger.error(error_msg)
            
            if stream_updates:
                await self._emit_error(context, error_msg, "OptimizationError")
            
            # Ensure session is rolled back on error
            if session_manager:
                await session_manager.rollback()
            raise
        finally:
            # Ensure session is closed
            if session_manager:
                await session_manager.close()
    
    async def _execute_optimization_workflow(self, context: UserExecutionContext, 
                                           session_manager: Any, 
                                           stream_updates: bool) -> Dict[str, Any]:
        """Execute optimization analysis workflow with session isolation."""
        if stream_updates:
            await self._emit_thinking(context, "Starting optimization analysis based on data insights...")
            await self._emit_progress(context, "Analyzing data patterns and formulating optimization strategies...")
        
        # Build prompt and execute LLM
        prompt = self._build_optimization_prompt(context)
        
        if stream_updates:
            await self._emit_tool_executing(context, "llm_analysis", {
                "model": "optimizations_core",
                "prompt_length": len(prompt)
            })
        
        try:
            # CRITICAL: Validate LLM manager is available (Five Whys Fix)
            if not self.llm_manager:
                error_msg = (
                    "❌ LLM manager is None - agent was instantiated without required dependency. "
                    "This indicates incomplete architectural migration between legacy AgentRegistry "
                    "and new factory patterns. See FIVE_WHYS_ANALYSIS_20250904.md"
                )
                self.logger.error(error_msg)
                raise RuntimeError(error_msg)
                
            llm_response = await self.llm_manager.ask_llm(prompt, llm_config_name='optimizations_core')
            
            if stream_updates:
                await self._emit_tool_completed(context, "llm_analysis", {
                    "response_length": len(llm_response),
                    "status": "success"
                })
            
        except Exception as e:
            if stream_updates:
                await self._emit_tool_completed(context, "llm_analysis", {
                    "status": "error",
                    "error": str(e)
                })
            raise
        
        # Process the response
        if stream_updates:
            await self._emit_progress(context, "Processing optimization recommendations...")
        
        result = await self._process_optimization_response(llm_response, context)
        
        if stream_updates:
            await self._emit_progress(context, "Optimization strategies formulated successfully", is_complete=True)
        
        return result
    
    async def _process_optimization_response(self, llm_response_str: str, 
                                           context: UserExecutionContext) -> Dict[str, Any]:
        """Process LLM response and update context metadata."""
        optimizations_result = self._extract_and_validate_result(llm_response_str, context.run_id)
        
        # Store result in context metadata for other agents to access
        context.metadata['optimizations_result'] = self._create_optimizations_result(optimizations_result)
        
        return optimizations_result
    
    def _extract_and_validate_result(self, llm_response_str: str, run_id: str) -> Dict[str, Any]:
        """Extract and validate JSON result from LLM response."""
        optimizations_result = extract_json_from_response(llm_response_str)
        if not optimizations_result:
            logger.warning(f"Could not extract JSON from LLM response for run_id: {run_id}. Using default optimizations.")
            optimizations_result = {"optimizations": []}
        return optimizations_result
    
    def _build_optimization_prompt(self, context: UserExecutionContext) -> str:
        """Build the optimization prompt from context data."""
        return optimizations_core_prompt_template.format(
            data=context.metadata.get('data_result'),
            triage_result=context.metadata.get('triage_result'),
            user_request=context.metadata.get('user_request')
        )
    
    def _create_default_fallback_result(self) -> Dict[str, Any]:
        """Create default fallback optimization result."""
        return {
            "optimization_type": "general",
            "recommendations": self._get_default_recommendations(),
            "confidence_score": 0.5,
            "metadata": self._get_fallback_metadata()
        }
    
    def _get_default_recommendations(self) -> List[str]:
        """Get default optimization recommendations."""
        return [
            "Basic optimization analysis - review current resource utilization",
            "Consider cost optimization opportunities based on usage patterns",
            "Evaluate performance improvements for critical workloads"
        ]
    
    def _get_fallback_metadata(self) -> Dict[str, Any]:
        """Get fallback metadata dictionary."""
        return {
            "fallback_used": True,
            "reason": "Primary optimization analysis failed"
        }
    
    
    def _create_optimizations_result(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dictionary to structured optimization result."""
        recommendations = self._extract_recommendations(data)
        processed_recommendations = self._process_recommendations(recommendations)
        return self._build_optimizations_result_dict(data, processed_recommendations)
    
    def _extract_recommendations(self, data: Dict[str, Any]) -> Any:
        """Extract recommendations from data dict."""
        return data.get("recommendations", data.get("optimizations", []))
    
    def _process_recommendations(self, recommendations: Any) -> List[str]:
        """Process recommendations to ensure they're a list of strings."""
        if isinstance(recommendations, list):
            return self._convert_recommendation_list(recommendations)
        return [str(recommendations)] if recommendations else []
    
    def _convert_recommendation_list(self, recommendations: List) -> List[str]:
        """Convert list of recommendations to strings."""
        fixed_recommendations = []
        for rec in recommendations:
            converted_rec = self._convert_single_recommendation(rec)
            fixed_recommendations.append(converted_rec)
        return fixed_recommendations
    
    def _convert_single_recommendation(self, rec: Any) -> str:
        """Convert single recommendation to string."""
        if isinstance(rec, dict):
            return rec.get("description", str(rec))
        return str(rec)
    
    def _build_optimizations_result_dict(self, data: Dict[str, Any], recommendations: List[str]) -> Dict[str, Any]:
        """Build optimization result dictionary from processed data."""
        result_params = self._build_optimization_result_params(data, recommendations)
        return result_params
    
    def _build_optimization_result_params(self, data: Dict[str, Any], recommendations: List[str]) -> Dict[str, Any]:
        """Build parameters dictionary for OptimizationsResult."""
        base_params = self._get_base_optimization_params(data, recommendations)
        extended_params = self._get_extended_optimization_params(data)
        return {**base_params, **extended_params}
    
    def _get_base_optimization_params(self, data: Dict[str, Any], recommendations: List[str]) -> Dict[str, Any]:
        """Get base optimization parameters."""
        return {
            "optimization_type": self._get_optimization_type(data),
            "recommendations": recommendations,
            "confidence_score": data.get("confidence_score", 0.8)
        }
    
    def _get_extended_optimization_params(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get extended optimization parameters."""
        return {
            "cost_savings": data.get("cost_savings"),
            "performance_improvement": data.get("performance_improvement"),
            "metadata": data.get("metadata", {})
        }
    
    def _get_optimization_type(self, data: Dict[str, Any]) -> str:
        """Extract optimization type from data with fallback."""
        return data.get("optimization_type", data.get("type", "general"))
    
    # WebSocket Event Methods for Streaming Support
    
    async def _emit_agent_started(self, context: UserExecutionContext) -> None:
        """Emit agent started event."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.send_agent_started(
                context.user_id,
                context.run_id,
                self.__class__.__name__,
                "Starting optimization analysis..."
            )
    
    async def _emit_agent_completed(self, context: UserExecutionContext, result: Dict[str, Any]) -> None:
        """Emit agent completed event."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.send_agent_completed(
                context.user_id,
                context.run_id,
                self.__class__.__name__,
                result
            )
    
    async def _emit_thinking(self, context: UserExecutionContext, message: str) -> None:
        """Emit agent thinking event."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.send_agent_thinking(
                context.user_id,
                context.run_id,
                self.__class__.__name__,
                message
            )
    
    async def _emit_progress(self, context: UserExecutionContext, message: str, is_complete: bool = False) -> None:
        """Emit progress update event."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.send_progress_update(
                context.user_id,
                context.run_id,
                message,
                is_complete
            )
    
    async def _emit_tool_executing(self, context: UserExecutionContext, tool_name: str, params: Dict[str, Any]) -> None:
        """Emit tool executing event."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.send_tool_executing(
                context.user_id,
                context.run_id,
                tool_name,
                params
            )
    
    async def _emit_tool_completed(self, context: UserExecutionContext, tool_name: str, result: Dict[str, Any]) -> None:
        """Emit tool completed event."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.send_tool_completed(
                context.user_id,
                context.run_id,
                tool_name,
                result
            )
    
    async def _emit_error(self, context: UserExecutionContext, error_message: str, error_type: str) -> None:
        """Emit error event."""
        if hasattr(self, 'websocket_manager') and self.websocket_manager:
            await self.websocket_manager.send_agent_error(
                context.user_id,
                context.run_id,
                self.__class__.__name__,
                error_message,
                error_type
            )
    
    @classmethod
    def create_agent_with_context(cls, context: 'UserExecutionContext') -> 'OptimizationsCoreSubAgent':
        """Factory method for creating OptimizationsCoreSubAgent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation, following the golden pattern from UnifiedTriageAgent.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            OptimizationsCoreSubAgent: Configured agent instance with proper context
        """
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
        
        # Create dependencies (these will be injected later by the factory)
        llm_manager = LLMManager()
        tool_dispatcher = UnifiedToolDispatcher.create_for_user(context)
        
        # Create agent with proper context following triage agent pattern
        agent = cls(
            llm_manager=llm_manager,
            tool_dispatcher=tool_dispatcher
        )
        
        # Set user context for WebSocket integration
        if hasattr(agent, 'set_user_context'):
            agent.set_user_context(context)
        
        return agent
