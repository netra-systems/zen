"""
MCP Tool Registry

Manages tool registration, discovery, and execution.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime, UTC
import json
import inspect

from pydantic import BaseModel, Field
from app.logging_config import CentralLogger
from app.core.exceptions import NetraException

logger = CentralLogger()


class Tool(BaseModel):
    """Represents an MCP tool"""
    name: str
    description: str
    inputSchema: Dict[str, Any]
    outputSchema: Optional[Dict[str, Any]] = None
    handler: Optional[Callable] = Field(default=None, exclude=True)
    requires_auth: bool = True
    permissions: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    version: str = "1.0.0"


class ToolExecution(BaseModel):
    """Records tool execution details"""
    tool_name: str
    session_id: Optional[str]
    input_params: Dict[str, Any]
    output_result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time_ms: int = 0
    status: str = "pending"  # pending, success, error, timeout
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ToolRegistry:
    """
    Registry for MCP tools
    
    Manages tool registration, discovery, validation, and execution.
    """
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.executions: List[ToolExecution] = []
        self._initialize_builtin_tools()
        
    def _initialize_builtin_tools(self):
        """Initialize built-in Netra tools"""
        # Agent operations
        self.register_tool(Tool(
            name="run_agent",
            description="Execute a Netra agent with specified configuration",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_name": {"type": "string", "description": "Name of the agent to run"},
                    "input_data": {"type": "object", "description": "Input data for the agent"},
                    "config": {"type": "object", "description": "Agent configuration overrides"}
                },
                "required": ["agent_name", "input_data"]
            },
            handler=self._run_agent_handler,
            category="Agent Operations"
        ))
        
        self.register_tool(Tool(
            name="get_agent_status",
            description="Check the status of an agent execution",
            inputSchema={
                "type": "object",
                "properties": {
                    "run_id": {"type": "string", "description": "Agent run ID"}
                },
                "required": ["run_id"]
            },
            handler=self._get_agent_status_handler,
            category="Agent Operations"
        ))
        
        self.register_tool(Tool(
            name="list_agents",
            description="Get list of available agents and their capabilities",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Filter by category"}
                }
            },
            handler=self._list_agents_handler,
            category="Agent Operations"
        ))
        
        # Optimization tools
        self.register_tool(Tool(
            name="analyze_workload",
            description="Analyze AI workload characteristics",
            inputSchema={
                "type": "object",
                "properties": {
                    "workload_data": {"type": "object", "description": "Workload data to analyze"},
                    "metrics": {"type": "array", "items": {"type": "string"}, "description": "Metrics to calculate"}
                },
                "required": ["workload_data"]
            },
            handler=self._analyze_workload_handler,
            category="Optimization"
        ))
        
        self.register_tool(Tool(
            name="optimize_prompt",
            description="Optimize prompts for cost and performance",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {"type": "string", "description": "Prompt to optimize"},
                    "target": {"type": "string", "enum": ["cost", "performance", "balanced"], "description": "Optimization target"},
                    "model": {"type": "string", "description": "Target model"}
                },
                "required": ["prompt"]
            },
            handler=self._optimize_prompt_handler,
            category="Optimization"
        ))
        
        # Data management
        self.register_tool(Tool(
            name="query_corpus",
            description="Search the document corpus",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 10},
                    "filters": {"type": "object", "description": "Additional filters"}
                },
                "required": ["query"]
            },
            handler=self._query_corpus_handler,
            category="Data Management"
        ))
        
        self.register_tool(Tool(
            name="generate_synthetic_data",
            description="Generate synthetic test data",
            inputSchema={
                "type": "object",
                "properties": {
                    "schema": {"type": "object", "description": "Data schema"},
                    "count": {"type": "integer", "description": "Number of records", "default": 10},
                    "format": {"type": "string", "enum": ["json", "csv", "parquet"], "default": "json"}
                },
                "required": ["schema"]
            },
            handler=self._generate_synthetic_data_handler,
            category="Data Management"
        ))
        
        # Thread management
        self.register_tool(Tool(
            name="create_thread",
            description="Create a new conversation thread",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Thread title"},
                    "metadata": {"type": "object", "description": "Thread metadata"}
                }
            },
            handler=self._create_thread_handler,
            category="Thread Management"
        ))
        
        self.register_tool(Tool(
            name="get_thread_history",
            description="Retrieve thread message history",
            inputSchema={
                "type": "object",
                "properties": {
                    "thread_id": {"type": "string", "description": "Thread ID"},
                    "limit": {"type": "integer", "description": "Maximum messages", "default": 50}
                },
                "required": ["thread_id"]
            },
            handler=self._get_thread_history_handler,
            category="Thread Management"
        ))
        
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        if tool.name in self.tools:
            logger.warning(f"Overwriting existing tool: {tool.name}")
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")
        
    def unregister_tool(self, tool_name: str):
        """Unregister a tool"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")
            
    async def list_tools(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available tools for a session"""
        # TODO: Filter tools based on session permissions
        tools_list = []
        for tool in self.tools.values():
            tool_dict = {
                "name": tool.name,
                "description": tool.description,
                "inputSchema": tool.inputSchema
            }
            if tool.category:
                tool_dict["category"] = tool.category
            tools_list.append(tool_dict)
        return tools_list
        
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a tool with given arguments"""
        start_time = datetime.now(UTC)
        
        # Create execution record
        execution = ToolExecution(
            tool_name=tool_name,
            session_id=session_id,
            input_params=arguments
        )
        
        try:
            # Get tool
            if tool_name not in self.tools:
                raise NetraException(f"Tool not found: {tool_name}")
                
            tool = self.tools[tool_name]
            
            # Check permissions
            if tool.requires_auth and not session_id:
                raise NetraException("Authentication required")
            
            # Validate input against schema
            if tool.input_schema:
                from jsonschema import validate, ValidationError
                try:
                    validate(instance=arguments, schema=tool.input_schema)
                except ValidationError as ve:
                    raise NetraException(f"Invalid input: {ve.message}")
            
            # Execute handler
            if not tool.handler:
                raise NetraException(f"Tool {tool_name} has no handler")
                
            # Check if handler is async
            if inspect.iscoroutinefunction(tool.handler):
                result = await tool.handler(arguments, session_id)
            else:
                result = tool.handler(arguments, session_id)
                
            # Record success
            execution.output_result = result
            execution.status = "success"
            execution.execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            
            # Format response
            return {
                "content": [result] if not isinstance(result, list) else result,
                "isError": False
            }
            
        except Exception as e:
            # Record error
            execution.error = str(e)
            execution.status = "error"
            execution.execution_time_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)
            
            logger.error(f"Tool execution failed: {tool_name} - {e}", exc_info=True)
            
            return {
                "content": [{
                    "type": "text",
                    "text": f"Tool execution failed: {str(e)}"
                }],
                "isError": True
            }
        finally:
            # Store execution record
            self.executions.append(execution)
            
    # Tool handlers
    async def _run_agent_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for run_agent tool"""
        from app.services.agent_service import AgentService
        from app.db.postgres import get_async_db
        from app.agents.supervisor import SupervisorAgent
        import uuid
        
        agent_name = arguments["agent_name"]
        input_data = arguments["input_data"]
        config = arguments.get("config", {})
        
        try:
            # Initialize supervisor
            async with get_async_db() as db:
                supervisor = SupervisorAgent(db)
                
                # Generate run ID
                run_id = str(uuid.uuid4())
                
                # Execute agent through supervisor
                result = await supervisor.handle_request({
                    "action": "execute_agent",
                    "agent_name": agent_name,
                    "input_data": input_data,
                    "config": config,
                    "run_id": run_id,
                    "session_id": session_id
                })
                
                return {
                    "type": "text",
                    "text": f"Agent {agent_name} execution completed",
                    "run_id": run_id,
                    "result": result
                }
        except Exception as e:
            logger.error(f"Agent execution failed: {e}")
            return {
                "type": "text",
                "text": f"Agent execution failed: {str(e)}",
                "error": True
            }
        
    async def _get_agent_status_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for get_agent_status tool"""
        run_id = arguments["run_id"]
        
        # TODO: Implement actual status retrieval
        return {
            "type": "text",
            "text": f"Status for run {run_id}: completed"
        }
        
    async def _list_agents_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for list_agents tool"""
        category = arguments.get("category")
        
        # TODO: Get actual agent list from supervisor
        agents = [
            {"name": "TriageSubAgent", "category": "analysis", "description": "Request triage and approach determination"},
            {"name": "DataSubAgent", "category": "data", "description": "Data collection and context gathering"},
            {"name": "OptimizationsCoreSubAgent", "category": "optimization", "description": "Core optimization recommendations"},
            {"name": "ActionsToMeetGoalsSubAgent", "category": "planning", "description": "Goal-oriented action planning"},
            {"name": "ReportingSubAgent", "category": "reporting", "description": "Final report compilation"}
        ]
        
        if category:
            agents = [a for a in agents if a["category"] == category]
            
        return {
            "type": "text",
            "text": json.dumps(agents, indent=2)
        }
        
    async def _analyze_workload_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for analyze_workload tool"""
        workload_data = arguments["workload_data"]
        metrics = arguments.get("metrics", ["cost", "latency", "throughput"])
        
        # TODO: Implement actual workload analysis
        return {
            "type": "text",
            "text": f"Workload analysis complete. Metrics: {', '.join(metrics)}"
        }
        
    async def _optimize_prompt_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for optimize_prompt tool"""
        prompt = arguments["prompt"]
        target = arguments.get("target", "balanced")
        model = arguments.get("model", "claude-3-opus")
        
        # TODO: Implement actual prompt optimization
        return {
            "type": "text",
            "text": f"Optimized prompt for {target} on {model}: {prompt[:50]}..."
        }
        
    async def _query_corpus_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for query_corpus tool"""
        query = arguments["query"]
        limit = arguments.get("limit", 10)
        
        # TODO: Implement actual corpus query
        return {
            "type": "text",
            "text": f"Found {limit} results for query: {query}"
        }
        
    async def _generate_synthetic_data_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for generate_synthetic_data tool"""
        schema = arguments["schema"]
        count = arguments.get("count", 10)
        format_type = arguments.get("format", "json")
        
        # TODO: Implement actual synthetic data generation
        return {
            "type": "text",
            "text": f"Generated {count} records in {format_type} format"
        }
        
    async def _create_thread_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for create_thread tool"""
        title = arguments.get("title", "New Thread")
        metadata = arguments.get("metadata", {})
        
        # TODO: Implement actual thread creation
        return {
            "type": "text",
            "text": f"Created thread: {title}",
            "thread_id": "placeholder_thread_id"
        }
        
    async def _get_thread_history_handler(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Handler for get_thread_history tool"""
        thread_id = arguments["thread_id"]
        limit = arguments.get("limit", 50)
        
        # TODO: Implement actual thread history retrieval
        return {
            "type": "text",
            "text": f"Thread {thread_id} history (last {limit} messages)"
        }
        
    async def shutdown(self):
        """Clean up resources"""
        self.tools.clear()
        self.executions.clear()