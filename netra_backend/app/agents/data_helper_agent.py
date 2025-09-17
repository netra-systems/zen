"""Data Helper Agent Module

This agent generates data requests when insufficient data is available for optimization.
Business Value: Ensures comprehensive data collection for accurate optimization strategies.

 PASS:  MIGRATION STATUS: FULLY MIGRATED to UserExecutionContext pattern
- Complete user isolation with UserExecutionContext
- Modern BaseAgent execution patterns
- Secure metadata storage and access
- WebSocket event integration
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.base_agent import BaseAgent
# SSOT COMPLIANCE: Import from core SSOT location
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.tools.data_helper import DataHelper
# SSOT Imports for compliance
from netra_backend.app.core.unified_error_handler import agent_error_handler
from netra_backend.app.schemas.shared_types import ErrorContext

logger = central_logger.get_logger(__name__)


class DataHelperAgent(BaseAgent):
    """Data Helper Agent for requesting additional data from users.
    
    This agent analyzes the context and generates comprehensive data requests
    to enable optimization strategies when data is insufficient.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher):
        """Initialize the Data Helper Agent.
        
        Args:
            llm_manager: LLM manager for the agent
            tool_dispatcher: Tool dispatcher for the agent
        """
        super().__init__(
            llm_manager=llm_manager,
            name="data_helper",
            description="Generates data requests when insufficient data is available",
            enable_reliability=False,  # DISABLED: Was hiding errors - see AGENT_RELIABILITY_ERROR_SUPPRESSION_ANALYSIS_20250903.md
            enable_execution_engine=True, # Get modern execution patterns
            enable_caching=True,          # Optional caching infrastructure
        )
        self.tool_dispatcher = tool_dispatcher
        self.data_helper_tool = DataHelper(llm_manager)
    
    @classmethod
    async def create_agent_with_context(cls, user_context: 'UserExecutionContext') -> 'DataHelperAgent':
        """Create DataHelperAgent with proper UserExecutionContext pattern.

        This method provides the correct constructor signature for the factory pattern,
        avoiding the constructor parameter mismatch with BaseAgent.create_agent_with_context.

        Args:
            user_context: User execution context for isolation

        Returns:
            DataHelperAgent instance configured for the user context
        """
        from netra_backend.app.llm.llm_manager import create_llm_manager
        # SSOT COMPLIANCE: Use factory pattern for tool dispatcher
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcherFactory

        # Create dependencies with proper user isolation
        llm_manager = create_llm_manager(user_context)
        tool_dispatcher = await UnifiedToolDispatcherFactory.create_for_request(user_context)
        
        # Create agent with correct constructor signature
        agent = cls(llm_manager=llm_manager, tool_dispatcher=tool_dispatcher)
        
        # Set user context for WebSocket integration
        if hasattr(agent, 'set_user_context'):
            agent.set_user_context(user_context)
        
        return agent
    
    async def _execute_with_user_context(self, context: 'UserExecutionContext', stream_updates: bool = False) -> 'UserExecutionContext':
        """Execute core data request generation logic with complete user isolation.
        
         PASS:  MIGRATED: Uses modern BaseAgent interface with UserExecutionContext for secure, isolated execution.
        
        Args:
            context: UserExecutionContext with complete request isolation
            stream_updates: Whether to enable streaming updates (not used by DataHelper currently)
            
        Returns:
            Enhanced UserExecutionContext with data request results
        """
        # Emit thinking event for reasoning visibility
        await self.emit_thinking("Analyzing user request to identify data gaps...")
        
        try:
            # Extract data from secure context metadata
            user_request = context.metadata.get('user_request', '')
            triage_result = context.metadata.get('triage_result', {})
            
            # Validate preconditions
            if not user_request or len(user_request.strip()) < 10:
                raise ValueError("Insufficient user request for data analysis")
            
            # Extract previous agent results from context
            previous_results = self._extract_previous_results_from_context(context)
            
            # Emit tool execution transparency
            await self.emit_tool_executing("data_helper", {
                "user_request_length": len(user_request),
                "triage_result_available": bool(triage_result),
                "previous_results_count": len(previous_results)
            })
            
            # Generate data request using the tool
            data_request_result = await self.data_helper_tool.generate_data_request(
                user_request=user_request,
                triage_result=triage_result,
                previous_results=previous_results
            )
            
            # Emit tool completion with sanitized results
            await self.emit_tool_completed("data_helper", {
                "success": data_request_result.get('success', False),
                "data_request_generated": bool(data_request_result.get('data_request')),
                "instructions_count": len(data_request_result.get('data_request', {}).get('user_instructions', '')),
                "structured_items_count": len(data_request_result.get('data_request', {}).get('structured_items', []))
            })
            
            # Store results using SSOT metadata storage (SECURE)
            self.store_metadata_result(context, 'data_result', data_request_result)
            self.store_metadata_result(context, 'data_request_generated', True)
            
            # Log successful execution
            logger.info(f"DataHelperAgent completed successfully: user_id={context.user_id}, run_id={context.run_id}")
            
            return context
            
        except Exception as e:
            # Use unified error handler with proper ErrorContext
            error_context = ErrorContext(
                trace_id=ErrorContext.generate_trace_id(),
                operation="data_request_generation",
                details={"run_id": context.run_id, "error_type": type(e).__name__},
                component="DataHelperAgent"
            )
            
            # Log the error through unified system
            logger.error(f"Error in DataHelperAgent: user_id={context.user_id}, run_id={context.run_id}, error={str(e)}")
            
            # Emit error event for WebSocket transparency (with cascading error prevention)
            try:
                await self.emit_error(f"Data helper error: {str(e)}", type(e).__name__)
            except Exception as emit_error:
                logger.error(f"Cascading error: Failed to emit error via WebSocket: {emit_error}")
            
            # Store error result using SSOT metadata storage (SECURE) (with cascading error prevention)
            try:
                self.store_metadata_result(context, 'data_helper_error', str(e))
            except Exception as metadata_error:
                logger.error(f"Cascading error: Failed to store error metadata: {metadata_error}")
            
            try:
                self.store_metadata_result(context, 'data_helper_fallback_message', 
                                         self._get_fallback_message(context.metadata.get('user_request', '')))
            except Exception as fallback_error:
                logger.error(f"Cascading error: Failed to store fallback message: {fallback_error}")
            
            # Return context with error state (don't re-raise - let BaseAgent handle)
            return context
    
    def _extract_previous_results_from_context(self, context: 'UserExecutionContext') -> Dict[str, Any]:
        """Extract previous agent results from UserExecutionContext metadata.
        
        Args:
            context: UserExecutionContext with metadata
            
        Returns:
            Dictionary of previous agent results
        """
        previous_results = {}
        
        # Extract known result types from context metadata
        result_keys = [
            'triage_result', 'data_result', 'optimizations_result',
            'action_plan_result', 'report_result', 'synthetic_data_result'
        ]
        
        for key in result_keys:
            value = context.metadata.get(key)
            if value is not None:
                previous_results[key] = value
        
        return previous_results
    
    def _get_fallback_message(self, user_request: str) -> str:
        """Generate a fallback message when data request generation fails.
        
        Args:
            user_request: Original user request (may be None or empty)
            
        Returns:
            Fallback message for the user
        """
        # Handle None or empty user request gracefully
        if not user_request:
            return (
                "I encountered an issue generating a specific data request. "
                "Please provide additional information about what you'd like me to analyze."
            )
        
        return (
            "I encountered an issue generating a specific data request. "
            "Please provide any additional information you think would be helpful "
            f"for analyzing your request: {user_request[:100]}..."
        )
    
