"""Data Helper Agent Module

This agent generates data requests when insufficient data is available for optimization.
Business Value: Ensures comprehensive data collection for accurate optimization strategies.
"""

from typing import Any, Dict, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger
from netra_backend.app.tools.data_helper import DataHelper

logger = central_logger.get_logger(__name__)


class DataHelperAgent(BaseAgent):
    """Data Helper Agent for requesting additional data from users.
    
    This agent analyzes the context and generates comprehensive data requests
    to enable optimization strategies when data is insufficient.
    """
    
    def __init__(self, llm_manager: LLMManager, tool_dispatcher: ToolDispatcher):
        """Initialize the Data Helper Agent.
        
        Args:
            llm_manager: LLM manager for the agent
            tool_dispatcher: Tool dispatcher for the agent
        """
        super().__init__(
            llm_manager=llm_manager,
            name="data_helper",
            description="Generates data requests when insufficient data is available"
        )
        self.tool_dispatcher = tool_dispatcher
        self.data_helper_tool = DataHelper(llm_manager)
    
    async def execute(self, state: DeepAgentState, run_id: str, stream_updates: bool = False) -> None:
        """Execute the agent - implements the abstract method from AgentLifecycleMixin.
        
        Args:
            state: Current agent state
            run_id: Run ID for tracking
            stream_updates: Whether to stream updates (unused)
        """
        # Call the run method with extracted parameters from state
        user_prompt = getattr(state, 'user_request', '')
        thread_id = getattr(state, 'thread_id', '')
        user_id = getattr(state, 'user_id', '')
        
        # Execute the run method and update state in place
        updated_state = await self.run(
            user_prompt=user_prompt,
            thread_id=thread_id,
            user_id=user_id,
            run_id=run_id,
            state=state
        )
        
        # Copy updated attributes back to the original state
        for key, value in updated_state.__dict__.items():
            setattr(state, key, value)
    
    async def run(
        self,
        user_prompt: str,
        thread_id: str,
        user_id: str,
        run_id: str,
        state: Optional[DeepAgentState] = None
    ) -> DeepAgentState:
        """Execute the data helper agent.
        
        Args:
            user_prompt: The user's request
            thread_id: Thread ID for the conversation
            user_id: User ID
            run_id: Run ID for tracking
            state: Current agent state with context
            
        Returns:
            Updated DeepAgentState with data request
        """
        logger.info(f"DataHelperAgent starting for run_id: {run_id}")
        
        # Initialize state if not provided
        if state is None:
            state = DeepAgentState()
            state.user_request = user_prompt
        
        try:
            # Extract triage result from state
            triage_result = getattr(state, 'triage_result', {})
            
            # Extract previous agent results from state
            previous_results = self._extract_previous_results(state)
            
            # Generate data request using the tool
            data_request_result = await self.data_helper_tool.generate_data_request(
                user_request=user_prompt,
                triage_result=triage_result,
                previous_results=previous_results
            )
            
            # Update state with data request
            state.data_helper_result = data_request_result
            
            # Add to agent outputs
            if not hasattr(state, 'agent_outputs'):
                state.agent_outputs = {}
            state.agent_outputs['data_helper'] = {
                'success': data_request_result.get('success', False),
                'data_request': data_request_result.get('data_request', {}),
                'user_instructions': data_request_result.get('data_request', {}).get('user_instructions', ''),
                'structured_items': data_request_result.get('data_request', {}).get('structured_items', [])
            }
            
            # Log successful execution
            logger.info(f"DataHelperAgent completed successfully for run_id: {run_id}")
            
        except Exception as e:
            logger.error(f"Error in DataHelperAgent for run_id {run_id}: {str(e)}")
            
            # Add error to state
            if not hasattr(state, 'agent_outputs'):
                state.agent_outputs = {}
            state.agent_outputs['data_helper'] = {
                'success': False,
                'error': str(e),
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
        
        # Check for agent outputs in state
        if hasattr(state, 'agent_outputs') and state.agent_outputs:
            for agent_name, output in state.agent_outputs.items():
                if agent_name != 'data_helper':  # Don't include self
                    previous_results.append({
                        'agent_name': agent_name,
                        'result': output
                    })
        
        # Also check for specific result attributes
        result_attributes = [
            'triage_result',
            'data_result',
            'optimization_result',
            'actions_result'
        ]
        
        for attr in result_attributes:
            if hasattr(state, attr):
                value = getattr(state, attr)
                if value and attr not in ['data_helper_result']:  # Don't include self
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
        """Process a message and generate data request.
        
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
        
        # Run the agent
        updated_state = await self.run(
            user_prompt=user_prompt,
            thread_id=thread_id,
            user_id=user_id,
            run_id=run_id,
            state=state
        )
        
        # Return the result
        return {
            'success': True,
            'state': updated_state,
            'data_request': updated_state.agent_outputs.get('data_helper', {})
        }