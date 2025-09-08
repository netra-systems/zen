"""Data Helper Agent Module

This agent generates data requests when insufficient data is available for optimization.
Business Value: Ensures comprehensive data collection for accurate optimization strategies.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.state import DeepAgentState
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
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: UnifiedToolDispatcher, context: Optional['UserExecutionContext'] = None):
        """Initialize the Data Helper Agent.
        
        Args:
            llm_manager: LLM manager for the agent
            tool_dispatcher: Tool dispatcher for the agent
            context: Optional UserExecutionContext for request isolation
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
        self.context = context  # Store for later use
    
    # === SSOT Abstract Method Implementations ===
    
    async def validate_preconditions(self, context: ExecutionContext) -> bool:
        """Validate execution preconditions for data request generation."""
        if not context.state.user_request:
            self.logger.warning(f"No user request provided for data helper in run_id: {context.run_id}")
            return False
        
        # Check if user request has sufficient length for meaningful analysis
        if len(context.state.user_request.strip()) < 10:
            self.logger.warning(f"User request too short for data helper analysis in run_id: {context.run_id}")
            return False
        
        return True
    
    async def execute_core_logic(self, context: ExecutionContext) -> Dict[str, Any]:
        """Execute core data request generation logic with WebSocket events."""
        # Emit thinking event for reasoning visibility
        await self.emit_thinking("Analyzing user request to identify data gaps...")
        
        try:
            # Extract triage result from state
            triage_result = getattr(context.state, 'triage_result', {})
            
            # Extract previous agent results from state
            previous_results = self._extract_previous_results(context.state)
            
            # Emit tool execution transparency
            await self.emit_tool_executing("data_helper", {
                "user_request": context.state.user_request[:100] + "..." if len(context.state.user_request) > 100 else context.state.user_request,
                "triage_result": bool(triage_result),
                "previous_results_count": len(previous_results)
            })
            
            # Generate data request using the tool
            data_request_result = await self.data_helper_tool.generate_data_request(
                user_request=context.state.user_request,
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
            
            # Update state with data request using context_tracking
            if not context.state.context_tracking:
                context.state.context_tracking = {}
            
            context.state.context_tracking['data_helper_result'] = data_request_result
            context.state.context_tracking['data_helper'] = {
                'success': data_request_result.get('success', False),
                'data_request': data_request_result.get('data_request', {}),
                'user_instructions': data_request_result.get('data_request', {}).get('user_instructions', ''),
                'structured_items': data_request_result.get('data_request', {}).get('structured_items', [])
            }
            
            # Emit progress completion
            await self.emit_progress("Data request generated successfully", is_complete=True)
            
            # Log successful execution
            logger.info(f"DataHelperAgent completed successfully for run_id: {context.run_id}")
            
            return {
                'success': True,
                'data_request': data_request_result.get('data_request', {}),
                'user_instructions': data_request_result.get('data_request', {}).get('user_instructions', ''),
                'structured_items': data_request_result.get('data_request', {}).get('structured_items', [])
            }
            
        except Exception as e:
            # Use unified error handler with proper ErrorContext
            error_context = ErrorContext(
                trace_id=ErrorContext.generate_trace_id(),
                operation="data_request_generation",
                details={"run_id": context.run_id, "error_type": type(e).__name__},
                component="DataHelperAgent"
            )
            
            # Log the error through unified system
            logger.error(f"Error in DataHelperAgent for run_id {context.run_id}: {str(e)}")
            
            # Emit error event for WebSocket transparency
            await self.emit_error(f"Data request generation failed: {str(e)}", "data_helper_error", {
                "run_id": context.run_id,
                "error_type": type(e).__name__
            })
            
            # Add error to state using context_tracking
            if not context.state.context_tracking:
                context.state.context_tracking = {}
            
            context.state.context_tracking['data_helper'] = {
                'success': False,
                'error': str(e),
                'fallback_message': self._get_fallback_message(context.state.user_request)
            }
            
            # Return error result but don't re-raise (let BaseAgent handle)
            return {
                'success': False,
                'error': str(e),
                'fallback_message': self._get_fallback_message(context.state.user_request)
            }
    
    # === Backward Compatibility Methods ===
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        """Execute the agent - backward compatibility method that delegates to modern execution.
        
        Args:
            state: Current agent state
            run_id: Run ID for tracking
            stream_updates: Whether to stream updates
        """
        # Use UserExecutionContext if available, otherwise create ExecutionContext for backward compatibility
        if self.context:
            # Modern pattern: Use UserExecutionContext
            await self.execute_modern(state, run_id, stream_updates)
        else:
            # Legacy pattern: Create ExecutionContext for backward compatibility
            context = ExecutionContext(
                run_id=run_id,
                agent_name=self.name,
                state=state,
                stream_updates=stream_updates,
                thread_id=getattr(state, 'chat_thread_id', None),
                user_id=getattr(state, 'user_id', None)
            )
            
            # Delegate to BaseAgent's modern execution
            await self.execute_modern(state, run_id, stream_updates)
    
    async def run(
        self,
        user_prompt: str,
        thread_id: str,
        user_id: str,
        run_id: str,
        state: Optional[DeepAgentState] = None
    ) -> DeepAgentState:
        """Execute the data helper agent - backward compatibility method.
        
        This method maintains backward compatibility while using the golden pattern internally.
        
        Args:
            user_prompt: The user's request
            thread_id: Thread ID for the conversation
            user_id: User ID
            run_id: Run ID for tracking
            state: Current agent state with context
            
        Returns:
            Updated DeepAgentState with data request
        """
        logger.info(f"DataHelperAgent.run() starting for run_id: {run_id}")
        
        # Initialize state if not provided
        if state is None:
            state = DeepAgentState()
            state.user_request = user_prompt
            state.chat_thread_id = thread_id
            state.user_id = user_id
        
        # Use UserExecutionContext if available, otherwise create ExecutionContext for backward compatibility
        if self.context:
            # Modern pattern: Use UserExecutionContext - update metadata for this execution
            if not hasattr(self.context, 'metadata'):
                self.context.metadata = {}
            self.context.metadata.update({
                'user_request': user_prompt,
                'run_id': run_id,
                'thread_id': thread_id,
                'user_id': user_id
            })
            context = self.context
        else:
            # Legacy pattern: Create ExecutionContext for backward compatibility
            context = ExecutionContext(
                run_id=run_id,
                agent_name=self.name,
                state=state,
                stream_updates=True,  # Default to true for legacy compatibility
                thread_id=thread_id,
                user_id=user_id
            )
        
        try:
            # Use modern execution pattern through BaseAgent
            if await self.validate_preconditions(context):
                result = await self.execute_core_logic(context)
                logger.info(f"DataHelperAgent.run() completed successfully for run_id: {run_id}")
            else:
                # Validation failed - add error to state using context_tracking
                logger.error(f"Validation failed in DataHelperAgent.run() for run_id: {run_id}")
                if not state.context_tracking:
                    state.context_tracking = {}
                
                state.context_tracking['data_helper'] = {
                    'success': False,
                    'error': 'Validation failed: insufficient or invalid user request',
                    'fallback_message': self._get_fallback_message(user_prompt)
                }
                
        except Exception as e:
            # This should rarely happen as execute_core_logic handles its own exceptions
            logger.error(f"Unexpected error in DataHelperAgent.run() for run_id {run_id}: {str(e)}")
            if not state.context_tracking:
                state.context_tracking = {}
                
            state.context_tracking['data_helper'] = {
                'success': False,
                'error': f"Unexpected error: {str(e)}",
                'fallback_message': self._get_fallback_message(user_prompt)
            }
        
        return state
    
    def _extract_previous_results(self, state: DeepAgentState) -> list:
        """Extract results from previous agents in the workflow.
        
        Args:
            state: Current agent state
            
        Returns:
            List of previous agent results
        """
        previous_results = []
        
        # Check for agent results in context_tracking
        if state.context_tracking:
            for agent_name, output in state.context_tracking.items():
                if agent_name != 'data_helper' and agent_name != 'data_helper_result':  # Don't include self
                    previous_results.append({
                        'agent_name': agent_name,
                        'result': output
                    })
        
        # Also check for specific result attributes on the state
        result_attributes = [
            'triage_result',
            'data_result',
            'optimizations_result',
            'action_plan_result'
        ]
        
        for attr in result_attributes:
            if hasattr(state, attr):
                value = getattr(state, attr)
                if value:  # Don't include None values
                    previous_results.append({
                        'agent_name': attr.replace('_result', ''),
                        'result': value
                    })
        
        return previous_results
    
    def _get_fallback_message(self, user_request: str) -> str:
        """Generate a fallback message if data request generation fails.
        
        Args:
            user_request: The original user request
            
        Returns:
            Fallback message string
        """
        return f"""To provide optimization recommendations for your request, we need additional information:
        
        1. Current system metrics and usage patterns
        2. Performance requirements and constraints  
        3. Budget and resource limitations
        4. Technical specifications
        
        Please provide this information to enable targeted optimization strategies."""
    
    async def process_message(
        self,
        message: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process a message and generate data request - backward compatibility method.
        
        Args:
            message: The message to process
            context: Additional context
            
        Returns:
            Processing result
        """
        # Extract necessary context
        user_prompt = message
        thread_id = context.get('thread_id', 'default')
        user_id = context.get('user_id', 'default')
        run_id = context.get('run_id', 'default')
        state = context.get('state')
        
        # Run the agent using backward compatible method
        updated_state = await self.run(
            user_prompt=user_prompt,
            thread_id=thread_id,
            user_id=user_id,
            run_id=run_id,
            state=state
        )
        
        # Return the result from context_tracking
        agent_output = updated_state.context_tracking.get('data_helper', {}) if updated_state.context_tracking else {}
        return {
            'success': agent_output.get('success', True),
            'state': updated_state,
            'data_request': agent_output
        }
    
    @classmethod
    def create_agent_with_context(cls, context) -> 'DataHelperAgent':
        """Factory method for creating DataHelperAgent with user context.
        
        This method enables the agent to be created through AgentInstanceFactory
        with proper user context isolation.
        
        Args:
            context: User execution context for isolation
            
        Returns:
            DataHelperAgent: Configured agent instance
        """
        # DataHelperAgent requires LLMManager and ToolDispatcher but doesn't pass tool_dispatcher to BaseAgent
        # so no deprecation warning is triggered
        return cls(llm_manager=None, tool_dispatcher=None, context=context)