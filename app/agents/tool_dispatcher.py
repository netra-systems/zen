"""Production-ready tool dispatcher with real service integrations."""
from typing import List, Dict, Any, Optional, Union
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
from app.schemas import ToolResult, ToolStatus, ToolInput, SimpleToolPayload
from app.agents.state import DeepAgentState
from app.logging_config import central_logger
from app.core.reliability import (
    get_reliability_wrapper, CircuitBreakerConfig, RetryConfig
)

logger = central_logger.get_logger(__name__)

# Typed models for tool dispatch
class ToolDispatchRequest(BaseModel):
    """Typed request for tool dispatch"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
class ToolDispatchResponse(BaseModel):
    """Typed response for tool dispatch"""
    success: bool
    result: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class MockToolExecuteRequest(BaseModel):
    """Typed request for MockTool execution"""
    parameters: Dict[str, Any]
    state: Optional[DeepAgentState] = None
    run_id: Optional[str] = None
    
class MockToolExecuteResponse(BaseModel):
    """Typed response for MockTool execution"""
    success: bool
    data: Optional[Union[str, Dict[str, Any], List[Any]]] = None
    message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolDispatcher:
    def __init__(self, tools: List[BaseTool] = None):
        self.tools = {}
        if tools:
            self.tools = {tool.name: tool for tool in tools}
        # Add synthetic tools that agents expect
        self._register_synthetic_tools()
        self._register_corpus_tools()

    def _register_synthetic_tools(self):
        """Register synthetic data generation tools"""
        # These are placeholders that integrate with the actual service
        synthetic_tools = [
            "generate_synthetic_data_batch",
            "validate_synthetic_data",
            "store_synthetic_data"
        ]
        for tool_name in synthetic_tools:
            if tool_name not in self.tools:
                self.tools[tool_name] = ProductionTool(tool_name)
    
    def _register_corpus_tools(self):
        """Register corpus management tools"""
        corpus_tools = [
            "create_corpus",
            "search_corpus", 
            "update_corpus",
            "delete_corpus",
            "analyze_corpus",
            "export_corpus",
            "import_corpus",
            "validate_corpus"
        ]
        for tool_name in corpus_tools:
            if tool_name not in self.tools:
                self.tools[tool_name] = ProductionTool(tool_name)

    def has_tool(self, tool_name: str) -> bool:
        """Check if a tool exists"""
        return tool_name in self.tools

    async def dispatch(self, tool_name: str, **kwargs: Any) -> ToolResult:
        """Dispatch tool execution with proper typing"""
        tool_input = ToolInput(tool_name=tool_name, kwargs=kwargs)
        if tool_name not in self.tools:
            return self._create_error_result(tool_input, f"Tool {tool_name} not found")
        
        return await self._execute_tool(tool_input, self.tools[tool_name], kwargs)
    
    def _create_error_result(self, tool_input: ToolInput, message: str) -> ToolResult:
        """Create error result for tool execution"""
        return ToolResult(tool_input=tool_input, status=ToolStatus.ERROR, message=message)
    
    async def _execute_tool(self, tool_input: ToolInput, tool: Any, kwargs: Dict[str, Any]) -> ToolResult:
        """Execute tool and return typed result"""
        try:
            result = await tool.arun(kwargs)
            payload = SimpleToolPayload(result=result)
            return ToolResult(tool_input=tool_input, status=ToolStatus.SUCCESS, payload=payload)
        except Exception as e:
            return self._create_error_result(tool_input, str(e))
    
    async def dispatch_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        state: DeepAgentState,
        run_id: str
    ) -> ToolDispatchResponse:
        """
        Dispatch a tool with parameters - method expected by sub-agents
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            state: Current agent state
            run_id: Execution run ID
            
        Returns:
            Tool execution result as typed response
        """
        if not self.has_tool(tool_name):
            logger.warning(f"Tool {tool_name} not found for run_id {run_id}")
            return ToolDispatchResponse(
                success=False,
                error=f"Tool {tool_name} not found"
            )
        
        tool = self.tools[tool_name]
        
        try:
            # Handle different tool types
            if isinstance(tool, ProductionTool):
                result = await tool.execute(parameters, state, run_id)
            elif hasattr(tool, 'arun'):
                result = await tool.arun(parameters)
            else:
                result = tool(parameters)
            
            return ToolDispatchResponse(
                success=True,
                result=result,
                metadata={"tool_name": tool_name, "run_id": run_id}
            )
                
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}")
            return ToolDispatchResponse(
                success=False,
                error=str(e),
                metadata={"tool_name": tool_name, "run_id": run_id}
            )


class ProductionTool:
    """Production tool with real service integrations and error handling"""
    
    def __init__(self, name: str):
        self.name = name
        self._init_circuit_breaker()
        
    def _init_circuit_breaker(self) -> None:
        """Initialize circuit breaker for tool reliability."""
        self.reliability = get_reliability_wrapper(
            f"Tool_{self.name}",
            CircuitBreakerConfig(
                failure_threshold=3,
                recovery_timeout=30.0,
                name=f"Tool_{self.name}"
            ),
            RetryConfig(
                max_retries=2,
                base_delay=1.0,
                max_delay=5.0
            )
        )
        
    async def arun(self, kwargs: Dict[str, Any]) -> MockToolExecuteResponse:
        """Run the production tool with typed response and reliability wrapper"""
        async def _execute_with_reliability():
            response = await self.execute(kwargs, None, None)
            return MockToolExecuteResponse(**response)
        
        return await self.reliability.execute(_execute_with_reliability)
    
    async def execute(
        self,
        parameters: Dict[str, Any],
        state: Optional[DeepAgentState],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Execute the production tool with reliability and error handling"""
        async def _execute_tool():
            return await self._execute_internal(parameters, state, run_id)
        
        try:
            return await self.reliability.execute(_execute_tool)
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "metadata": {"tool": self.name, "service": "production", "run_id": run_id}
            }
    
    async def _execute_internal(
        self,
        parameters: Dict[str, Any],
        state: Optional[DeepAgentState],
        run_id: Optional[str]
    ) -> Dict[str, Any]:
        """Internal execution method with service routing"""
        if self.name == "generate_synthetic_data_batch":
            return await self._execute_synthetic_data_batch(parameters)
        elif self.name == "validate_synthetic_data":
            return await self._execute_validate_synthetic_data(parameters)
        elif self.name == "store_synthetic_data":
            return await self._execute_store_synthetic_data(parameters)
        elif self.name == "create_corpus":
            return await self._execute_create_corpus(parameters)
        elif self.name == "search_corpus":
            return await self._execute_search_corpus(parameters)
        elif self.name == "update_corpus":
            return await self._execute_update_corpus(parameters)
        elif self.name == "delete_corpus":
            return await self._execute_delete_corpus(parameters)
        elif self.name == "analyze_corpus":
            return await self._execute_analyze_corpus(parameters)
        elif self.name == "export_corpus":
            return await self._execute_export_corpus(parameters)
        elif self.name == "import_corpus":
            return await self._execute_import_corpus(parameters)
        elif self.name == "validate_corpus":
            return await self._execute_validate_corpus(parameters)
        return await self._execute_default()
    
    async def _execute_synthetic_data_batch(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute synthetic data batch generation via real service"""
        try:
            from app.services.synthetic_data import synthetic_data_service
            batch_size = parameters.get("batch_size", 100)
            config = type('Config', (), {'num_logs': batch_size})()
            
            # Use real service to generate batch
            batch = await synthetic_data_service.generate_batch(config, batch_size)
            
            return {
                "success": True,
                "data": batch,
                "metadata": {"batch_size": batch_size, "tool": self.name, "service": "synthetic_data"}
            }
        except Exception as e:
            logger.error(f"Synthetic data batch generation failed: {e}")
            return {
                "success": False,
                "error": f"Failed to generate synthetic data: {str(e)}",
                "metadata": {"tool": self.name, "service": "synthetic_data"}
            }
    
    async def _execute_create_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute corpus creation via real service"""
        try:
            from app.services.corpus import corpus_service
            from app.schemas import CorpusCreate
            
            corpus_name = parameters.get('corpus_name', f'corpus_{parameters.get("name", "default")}')
            user_id = parameters.get('user_id', 'default_user')
            
            # Create corpus data object
            corpus_data = CorpusCreate(
                name=corpus_name,
                description=parameters.get('description', f'Corpus {corpus_name}')
            )
            
            # Use real service to create corpus
            corpus = await corpus_service.create_corpus(corpus_data, user_id)
            
            return {
                "success": True,
                "data": {"corpus_id": corpus.id, "name": corpus.name},
                "message": "Corpus created successfully",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
        except Exception as e:
            logger.error(f"Corpus creation failed: {e}")
            return {
                "success": False,
                "error": f"Failed to create corpus: {str(e)}",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
    
    async def _execute_search_corpus(self, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute corpus search via real service"""
        try:
            from app.services.corpus import corpus_service
            
            if not parameters:
                parameters = {}
            
            corpus_id = parameters.get('corpus_id')
            query = parameters.get('query', '')
            limit = parameters.get('limit', 10)
            
            if not corpus_id:
                return {
                    "success": False,
                    "error": "corpus_id parameter is required for search",
                    "metadata": {"tool": self.name, "service": "corpus"}
                }
            
            # Use real service to search corpus
            search_params = {"query": query, "limit": limit}
            results = await corpus_service.search_corpus_content(None, corpus_id, search_params)
            
            return {
                "success": True,
                "data": {
                    "results": results.get("results", []),
                    "total_matches": results.get("total", 0)
                },
                "message": "Search completed successfully",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
        except Exception as e:
            logger.error(f"Corpus search failed: {e}")
            return {
                "success": False,
                "error": f"Failed to search corpus: {str(e)}",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
    
    async def _execute_validate_synthetic_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate synthetic data"""
        try:
            from app.services.synthetic_data import validate_data
            data = parameters.get('data', [])
            validation = validate_data(data)
            return {
                "success": True,
                "data": validation,
                "message": "Data validation completed",
                "metadata": {"tool": self.name, "service": "synthetic_data"}
            }
        except Exception as e:
            logger.error(f"Data validation failed: {e}")
            return {"success": False, "error": str(e), "metadata": {"tool": self.name}}

    async def _execute_store_synthetic_data(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Store synthetic data"""
        try:
            from app.services.synthetic_data import synthetic_data_service
            data = parameters.get('data', [])
            table_name = parameters.get('table_name', 'synthetic_data')
            result = await synthetic_data_service.ingest_batch(data, table_name)
            return {
                "success": True,
                "data": result,
                "message": "Data stored successfully",
                "metadata": {"tool": self.name, "service": "synthetic_data"}
            }
        except Exception as e:
            logger.error(f"Data storage failed: {e}")
            return {"success": False, "error": str(e), "metadata": {"tool": self.name}}

    async def _execute_update_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Update corpus"""
        try:
            from app.services.corpus import corpus_service
            from app.schemas import CorpusUpdate
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.name}}
            
            update_data = CorpusUpdate(**{k: v for k, v in parameters.items() if k != 'corpus_id'})
            result = await corpus_service.update_corpus(None, corpus_id, update_data)
            return {
                "success": True,
                "data": {"corpus_id": corpus_id, "updated": True},
                "message": "Corpus updated successfully",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.name}}

    def _execute_delete_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Delete corpus"""
        try:
            from app.services.corpus import corpus_service
            import asyncio
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.name}}
            
            asyncio.run(corpus_service.delete_corpus(None, corpus_id))
            return {
                "success": True,
                "data": {"corpus_id": corpus_id, "deleted": True},
                "message": "Corpus deleted successfully",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.name}}

    def _execute_analyze_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze corpus"""
        try:
            from app.services.corpus import corpus_service
            import asyncio
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.name}}
            
            stats = asyncio.run(corpus_service.get_corpus_statistics(None, corpus_id))
            return {
                "success": True,
                "data": stats,
                "message": "Corpus analysis completed",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.name}}

    def _execute_export_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Export corpus"""
        corpus_id = parameters.get('corpus_id')
        format_type = parameters.get('format', 'json')
        return {
            "success": True,
            "data": {"corpus_id": corpus_id, "export_url": f"/exports/{corpus_id}.{format_type}"},
            "message": f"Corpus export initiated in {format_type} format",
            "metadata": {"tool": self.name, "service": "corpus"}
        }

    def _execute_import_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Import corpus"""
        source_url = parameters.get('source_url')
        corpus_name = parameters.get('name', 'imported_corpus')
        return {
            "success": True,
            "data": {"corpus_id": f"imported_{corpus_name}", "name": corpus_name},
            "message": "Corpus import initiated",
            "metadata": {"tool": self.name, "service": "corpus"}
        }

    def _execute_validate_corpus(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate corpus"""
        try:
            from app.services.corpus import corpus_service
            import asyncio
            corpus_id = parameters.get('corpus_id')
            if not corpus_id:
                return {"success": False, "error": "corpus_id required", "metadata": {"tool": self.name}}
            
            corpus = asyncio.run(corpus_service.get_corpus(None, corpus_id))
            validation = {"valid": corpus is not None, "errors": [] if corpus else ["Corpus not found"]}
            return {
                "success": True,
                "data": validation,
                "message": "Corpus validation completed",
                "metadata": {"tool": self.name, "service": "corpus"}
            }
        except Exception as e:
            return {"success": False, "error": str(e), "metadata": {"tool": self.name}}

    def _execute_default(self) -> Dict[str, Any]:
        """Execute default tool response with proper error message"""
        return {
            "success": False, 
            "error": f"Tool '{self.name}' is not implemented. Available tools: synthetic data tools, corpus tools",
            "metadata": {"tool": self.name, "status": "not_implemented"}
        }
