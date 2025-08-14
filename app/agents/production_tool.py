"""Production tool with real service integrations and error handling."""
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.agents.state import DeepAgentState
from app.logging_config import central_logger
from app.core.reliability_utils import create_tool_reliability_wrapper, create_default_tool_result

logger = central_logger.get_logger(__name__)

class ToolExecuteResponse(BaseModel):
    """Typed response for tool execution"""
    success: bool
    data: Optional[Any] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = {}

class ProductionTool:
    """Production tool with real service integrations and error handling"""
    
    def __init__(self, name: str):
        self.name = name
        self._init_circuit_breaker()
        
    def _init_circuit_breaker(self) -> None:
        """Initialize circuit breaker for tool reliability."""
        self.reliability = create_tool_reliability_wrapper(self.name)
        
    async def arun(self, kwargs: Dict[str, Any]) -> ToolExecuteResponse:
        """Run the production tool with typed response and reliability wrapper"""
        async def _execute_with_reliability():
            response = await self.execute(kwargs, None, None)
            return ToolExecuteResponse(**response)
        
        return await self.reliability.execute(_execute_with_reliability)
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        state: Optional[DeepAgentState],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute the production tool with reliability and error handling"""
        try:
            return await self._execute_with_reliability_wrapper(parameters, state, run_id)
        except Exception as e:
            return self._create_execution_error_response(e, run_id)
    
    async def _execute_with_reliability_wrapper(
        self, parameters: Dict[str, Any], state: Optional[DeepAgentState], run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute tool with reliability wrapper"""
        async def _execute_tool():
            return await self._execute_internal(parameters, state, run_id)
        return await self.reliability.execute(_execute_tool)
    
    def _create_execution_error_response(self, error: Exception, run_id: Optional[str]) -> Dict[str, Any]:
        """Create error response for execution failure"""
        logger.error(f"Tool {self.name} execution failed: {error}")
        return {
            "success": False,
            "error": str(error),
            "metadata": {"tool": self.name, "service": "production", "run_id": run_id}
        }
    
    async def _execute_internal(
        self,
        parameters: Dict[str, Any],
        state: Optional[DeepAgentState],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Internal execution method with service routing"""
        synthetic_result = await self._try_synthetic_tools(parameters)
        if synthetic_result:
            return synthetic_result
        
        corpus_result = await self._try_corpus_tools(parameters)
        if corpus_result:
            return corpus_result
            
        return await self._execute_default()
    
    async def _try_synthetic_tools(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to execute synthetic data tools."""
        from app.agents.production_tool_synthetic import SyntheticToolExecutor
        executor = SyntheticToolExecutor(self.name)
        return await executor.execute(parameters)
    
    async def _try_corpus_tools(self, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Try to execute corpus management tools."""
        from app.agents.production_tool_corpus import CorpusToolExecutor
        executor = CorpusToolExecutor(self.name)
        return await executor.execute(parameters)
    
    async def _execute_default(self) -> Dict[str, Any]:
        """Execute default tool response with proper error message"""
        return {
            "success": False, 
            "error": f"Tool '{self.name}' is not implemented. Available tools: synthetic data tools, corpus tools",
            "metadata": {"tool": self.name, "status": "not_implemented"}
        }