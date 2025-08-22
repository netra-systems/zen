"""Pipeline execution for NACIS Chat Orchestrator.

Date Created: 2025-01-22
Last Updated: 2025-01-22

Business Value: Executes agent pipelines with proper orchestration and data flow.
"""

from typing import Any, Dict, List

from netra_backend.app.agents.base.interface import ExecutionContext
from netra_backend.app.agents.chat_orchestrator.intent_classifier import IntentType
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class PipelineExecutor:
    """Executes agent pipelines according to execution plans."""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.agent_registry = orchestrator.agent_registry
        self.execution_engine = orchestrator.execution_engine
        self.trace_logger = orchestrator.trace_logger
    
    async def execute(self, context: ExecutionContext, 
                     plan: List[Dict], intent: IntentType) -> Dict[str, Any]:
        """Execute the agent pipeline according to plan."""
        result = self._initialize_result(intent)
        accumulated_data = {}
        for step in plan:
            step_result = await self._execute_step(context, step, accumulated_data)
            self._update_result(result, step, step_result)
            self._accumulate_data(accumulated_data, step_result)
        return result
    
    def _initialize_result(self, intent: IntentType) -> Dict[str, Any]:
        """Initialize pipeline result structure."""
        return {
            "intent": intent.value,
            "steps": [],
            "data": {},
            "status": "processing"
        }
    
    async def _execute_step(self, context: ExecutionContext, step: Dict,
                          accumulated_data: Dict) -> Any:
        """Execute a single pipeline step."""
        agent_name = step["agent"]
        action = step["action"]
        params = step.get("params", {})
        await self._log_step_start(agent_name, action, params)
        return await self._route_to_agent(context, agent_name, action, params, accumulated_data)
    
    async def _log_step_start(self, agent_name: str, action: str, params: Dict) -> None:
        """Log the start of a pipeline step."""
        await self.trace_logger.log(
            f"Executing {agent_name}.{action}",
            params
        )
    
    async def _route_to_agent(self, context: ExecutionContext, agent_name: str,
                            action: str, params: Dict, accumulated_data: Dict) -> Any:
        """Route execution to appropriate agent."""
        self._prepare_context(context, accumulated_data)
        if self._is_agent_available(agent_name):
            return await self._execute_agent(context, agent_name)
        return self._create_placeholder_result(agent_name, action)
    
    def _prepare_context(self, context: ExecutionContext, accumulated_data: Dict) -> None:
        """Prepare context with accumulated data."""
        if context.state:
            context.state.accumulated_data = accumulated_data
    
    def _is_agent_available(self, agent_name: str) -> bool:
        """Check if agent is available in registry."""
        return agent_name in self.agent_registry.agents
    
    async def _execute_agent(self, context: ExecutionContext, agent_name: str) -> Any:
        """Execute registered agent."""
        agent = self.agent_registry.get_agent(agent_name)
        return await self.execution_engine.execute_agent(agent, context)
    
    def _create_placeholder_result(self, agent_name: str, action: str) -> Dict:
        """Create placeholder for unimplemented agents."""
        logger.info(f"Agent {agent_name} not yet implemented")
        return {
            "status": "pending",
            "agent": agent_name,
            "action": action,
            "message": "Agent implementation pending"
        }
    
    def _update_result(self, result: Dict, step: Dict, step_result: Any) -> None:
        """Update pipeline result with step outcome."""
        result["steps"].append({
            "agent": step["agent"],
            "action": step["action"],
            "result": step_result
        })
    
    def _accumulate_data(self, accumulated_data: Dict, step_result: Any) -> None:
        """Accumulate data from step result."""
        if isinstance(step_result, dict):
            accumulated_data.update(step_result)