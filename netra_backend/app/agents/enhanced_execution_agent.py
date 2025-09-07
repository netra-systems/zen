"""Enhanced agent with proper WebSocket event notifications.

Business Value: Ensures real-time agent status updates for improved UX.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.agents.supervisor.user_execution_context import UserExecutionContext
# DatabaseSessionManager removed - use SSOT database module get_db() instead
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class EnhancedExecutionAgent(BaseAgent):
    """Enhanced agent that properly sends WebSocket notifications during execution."""
    
    def __init__(self, llm_manager: LLMManager, name: str = "EnhancedAgent",
                 description: str = "Agent with proper WebSocket notifications"):
        super().__init__(llm_manager, name, description)
        self.execution_steps = []
        self.tools_used = []
    
    async def execute(self, context: UserExecutionContext, stream_updates: bool = False) -> Any:
        """Execute agent with proper WebSocket notifications using UserExecutionContext pattern.
        
        Args:
            context: User execution context containing all request-scoped state
            stream_updates: Whether to stream progress updates
            
        Returns:
            Execution result
        """
        try:
            # Validate user context and ensure isolation
            if not isinstance(context, UserExecutionContext):
                raise TypeError(f"Expected UserExecutionContext, got {type(context)}")
            
            # Database session available via context.db_session if needed
            
            # Start execution
            await self._begin_execution(context, stream_updates)
            
            # Process with thinking updates
            result = await self._process_with_thinking(context, stream_updates, session_manager)
            
            # Execute tools if needed
            if self._needs_tools(context):
                await self._execute_tools(context, stream_updates, session_manager)
            
            # Send final report
            await self._send_execution_report(context, stream_updates, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced agent execution failed for user {context.user_id}: {e}")
            await self.emit_error(f"Execution failed: {str(e)}")
            raise
    
    async def _begin_execution(self, context: UserExecutionContext, 
                               stream_updates: bool) -> None:
        """Begin execution with initial notifications."""
        if stream_updates:
            # Extract user request from context metadata or use default
            user_request = context.metadata.get('user_request', 'user request')
            # Send initial thinking update using new WebSocket bridge pattern
            await self.emit_thinking(
                f"Starting to process: {str(user_request)[:100]}...",
                step_number=1
            )
    
    async def _process_with_thinking(self, context: UserExecutionContext, 
                                    stream_updates: bool, 
                                    session_manager: Optional[DatabaseSessionManager]) -> str:
        """Process request with thinking updates using context pattern."""
        thinking_steps = [
            "Analyzing the user's request...",
            "Identifying key requirements and constraints...",
            "Determining the best approach to solve this...",
            "Formulating a comprehensive response..."
        ]
        
        result_parts = []
        
        for i, thought in enumerate(thinking_steps, 1):
            if stream_updates:
                # Send thinking update using new WebSocket bridge pattern
                await self.emit_thinking(thought, step_number=i)
            
            # Simulate processing
            await asyncio.sleep(0.1)
            
            # Generate partial result
            partial = f"Step {i}: Completed {thought.lower()}"
            result_parts.append(partial)
            
            if stream_updates:
                # Send partial result using new WebSocket bridge pattern
                await self.emit_progress(
                    "\n".join(result_parts),
                    is_complete=(i == len(thinking_steps))
                )
        
        # Process with LLM if available
        if self.llm_manager:
            response = await self._process_with_llm(context)
            result_parts.append(f"\nLLM Response: {response}")
        
        return "\n".join(result_parts)
    
    async def _process_with_llm(self, context: UserExecutionContext) -> str:
        """Process with LLM using context pattern."""
        try:
            # Extract user prompt from context metadata
            user_prompt = context.metadata.get('user_request', 'No request provided')
            
            # Simple LLM call with user isolation
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": str(user_prompt)}
            ]
            response = await self.llm_manager.chat_completion(messages)
            return response.get("content", "No response generated")
        except Exception as e:
            logger.error(f"LLM processing failed for user {context.user_id}: {e}")
            user_prompt = context.metadata.get('user_request', 'request')
            return f"Processing completed with fallback response for: {str(user_prompt)}"
    
    def _needs_tools(self, context: UserExecutionContext) -> bool:
        """Check if tools are needed using context pattern."""
        # Simple heuristic: check if prompt mentions analysis, data, or tools
        user_request = context.metadata.get('user_request', '')
        prompt_lower = str(user_request).lower()
        tool_keywords = ["analyze", "calculate", "data", "tool", "search", "find"]
        return any(keyword in prompt_lower for keyword in tool_keywords)
    
    async def _execute_tools(self, context: UserExecutionContext, 
                           stream_updates: bool, 
                           session_manager: Optional[DatabaseSessionManager]) -> None:
        """Execute tools with notifications using context pattern."""
        tools = ["data_analyzer", "calculator", "search_engine"]
        
        for tool_name in tools:
            if stream_updates:
                # Send tool executing notification using new WebSocket bridge pattern
                await self.emit_tool_executing(tool_name)
            
            # Simulate tool execution with user context isolation
            await asyncio.sleep(0.2)
            result = {
                "status": "success", 
                "data": f"Results from {tool_name} for user {context.user_id[:8]}...",
                "user_isolated": True
            }
            self.tools_used.append(tool_name)
            
            if stream_updates:
                # Send tool completed notification using new WebSocket bridge pattern
                await self.emit_tool_completed(tool_name, result)
    
    async def _send_execution_report(self, context: UserExecutionContext,
                                    stream_updates: bool, result: str) -> None:
        """Send final execution report using context pattern."""
        if not stream_updates:
            return
        
        # Calculate execution metrics
        execution_time = time.time() - self.start_time if self.start_time else 0
        
        # Build comprehensive report with user context isolation
        user_request = context.metadata.get('user_request', 'No request provided')
        report = {
            "summary": "Agent execution completed successfully",
            "user_request": str(user_request),
            "result": result,
            "user_id": context.user_id[:8] + "...",  # Truncated for security
            "run_id": context.run_id,
            "metrics": {
                "execution_time_ms": execution_time * 1000,
                "steps_completed": len(self.execution_steps),
                "tools_used": len(self.tools_used),
                "tool_names": self.tools_used
            },
            "status": "success"
        }
        
        # Send final report using new WebSocket bridge pattern
        await self.emit_agent_completed(report)


class EnhancedSupervisorWrapper:
    """Wrapper to enhance existing supervisor with proper notifications using UserExecutionContext pattern."""
    
    def __init__(self, supervisor):
        self.supervisor = supervisor
        self.websocket_manager = getattr(supervisor, 'websocket_manager', None)
    
    async def run_with_notifications(self, context: UserExecutionContext) -> Any:
        """Run supervisor with enhanced WebSocket notifications using UserExecutionContext pattern.
        
        Args:
            context: User execution context containing all request-scoped state
            
        Returns:
            Execution result
        """
        # Validate context
        if not isinstance(context, UserExecutionContext):
            raise TypeError(f"Expected UserExecutionContext, got {type(context)}")
        
        user_request = context.metadata.get('user_request', 'No request provided')
        
        # Send initial notifications using WebSocket bridge pattern
        if hasattr(self.supervisor, 'engine') and self.supervisor.engine:
            engine = self.supervisor.engine
            if hasattr(engine, 'websocket_notifier'):
                notifier = engine.websocket_notifier
                
                # Create simple execution context for backward compatibility
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                legacy_context = AgentExecutionContext(
                    agent_name="Supervisor",
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    user_id=context.user_id
                )
                
                # Send agent started
                await notifier.send_agent_started(legacy_context)
                
                # Send initial thinking
                await notifier.send_agent_thinking(
                    legacy_context, 
                    "Processing your request...",
                    step_number=1
                )
        
        # Run the actual supervisor with context pattern
        # Note: This assumes the supervisor has been migrated to accept UserExecutionContext
        if hasattr(self.supervisor, 'execute_with_context'):
            result = await self.supervisor.execute_with_context(context)
        elif hasattr(self.supervisor, 'execute'):
            # Try new execute signature
            try:
                result = await self.supervisor.execute(context, stream_updates=True)
            except TypeError:
                # Fallback to legacy interface
                result = await self.supervisor.run(
                    str(user_request), 
                    context.thread_id, 
                    context.user_id, 
                    context.run_id
                )
        else:
            # Use run method as fallback
            result = await self.supervisor.run(
                str(user_request), 
                context.thread_id, 
                context.user_id, 
                context.run_id
            )
        
        # Send completion notifications
        if hasattr(self.supervisor, 'engine') and self.supervisor.engine:
            engine = self.supervisor.engine
            if hasattr(engine, 'websocket_notifier'):
                notifier = engine.websocket_notifier
                
                # Create legacy context for backward compatibility
                from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
                legacy_context = AgentExecutionContext(
                    agent_name="Supervisor",
                    run_id=context.run_id,
                    thread_id=context.thread_id,
                    user_id=context.user_id
                )
                
                # Send final report
                report = {
                    "summary": "Request processed successfully",
                    "user_request": str(user_request),
                    "final_answer": getattr(result, 'final_answer', str(result) if result else 'Completed'),
                    "user_id": context.user_id[:8] + "...",  # Truncated for security
                    "status": "success"
                }
                
                await notifier.send_final_report(legacy_context, report, 1000.0)
                
                # Send agent completed
                await notifier.send_agent_completed(legacy_context, report, 1000.0)
        
        return result