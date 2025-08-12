"""
MCP Service

Main service layer for MCP server integration with Netra platform.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.logging_config import CentralLogger
from app.core.exceptions import NetraException
from app.services.agent_service import AgentService
from app.services.thread_service import ThreadService
from app.services.corpus_service import CorpusService
from app.services.synthetic_data_service import SyntheticDataService
from app.services.security_service import SecurityService
from app.services.supply_catalog_service import SupplyCatalogService
from app.schemas import UserInDB
from app.mcp.server import MCPServer
from app.mcp.tools import ToolRegistry, Tool
from app.mcp.resources import ResourceManager, Resource

logger = CentralLogger()


class MCPClient(BaseModel):
    """MCP Client model"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    client_type: str  # claude, cursor, gemini, vscode, etc
    api_key_hash: Optional[str] = None
    permissions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)


class MCPToolExecution(BaseModel):
    """MCP Tool execution record"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    tool_name: str
    input_params: Dict[str, Any]
    output_result: Optional[Dict[str, Any]] = None
    execution_time_ms: int
    status: str  # success, error, timeout
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MCPService:
    """
    Main service for MCP server operations
    
    Integrates MCP functionality with existing Netra services.
    """
    
    def __init__(
        self,
        agent_service: AgentService,
        thread_service: ThreadService,
        corpus_service: CorpusService,
        synthetic_data_service: SyntheticDataService,
        security_service: SecurityService,
        supply_catalog_service: SupplyCatalogService
    ):
        self.agent_service = agent_service
        self.thread_service = thread_service
        self.corpus_service = corpus_service
        self.synthetic_data_service = synthetic_data_service
        self.security_service = security_service
        self.supply_catalog_service = supply_catalog_service
        
        # Initialize MCP server
        self.mcp_server = MCPServer()
        self._register_netra_tools()
        self._register_netra_resources()
        
    def _register_netra_tools(self):
        """Register Netra-specific tools with MCP"""
        tool_registry = self.mcp_server.tool_registry
        
        # Override default handlers with actual Netra implementations
        tool_registry.tools["run_agent"].handler = self.execute_agent
        tool_registry.tools["get_agent_status"].handler = self.get_agent_status
        tool_registry.tools["list_agents"].handler = self.list_available_agents
        tool_registry.tools["analyze_workload"].handler = self.analyze_workload
        tool_registry.tools["optimize_prompt"].handler = self.optimize_prompt
        tool_registry.tools["query_corpus"].handler = self.query_corpus
        tool_registry.tools["generate_synthetic_data"].handler = self.generate_synthetic_data
        tool_registry.tools["create_thread"].handler = self.create_thread
        tool_registry.tools["get_thread_history"].handler = self.get_thread_history
        
        # Add additional Netra-specific tools
        tool_registry.register_tool(Tool(
            name="get_supply_catalog",
            description="Get available models and providers",
            inputSchema={
                "type": "object",
                "properties": {
                    "filter": {"type": "string", "description": "Filter criteria"}
                }
            },
            handler=self.get_supply_catalog,
            category="Supply"
        ))
        
        tool_registry.register_tool(Tool(
            name="execute_optimization_pipeline",
            description="Execute full optimization pipeline",
            inputSchema={
                "type": "object",
                "properties": {
                    "input_data": {"type": "object", "description": "Input data for optimization"},
                    "optimization_goals": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["input_data"]
            },
            handler=self.execute_optimization_pipeline,
            category="Optimization"
        ))
        
    def _register_netra_resources(self):
        """Register Netra-specific resources with MCP"""
        resource_manager = self.mcp_server.resource_manager
        
        # Add additional Netra resources
        resource_manager.register_resource(Resource(
            uri="netra://optimization/history",
            name="Optimization History",
            description="Historical optimization results and recommendations",
            mimeType="application/json"
        ))
        
        resource_manager.register_resource(Resource(
            uri="netra://config/models",
            name="Model Configurations",
            description="Configured model parameters and settings",
            mimeType="application/json"
        ))
        
    async def execute_agent(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Execute a Netra agent"""
        try:
            agent_name = arguments["agent_name"]
            input_data = arguments["input_data"]
            config = arguments.get("config", {})
            
            # Create a thread for this execution
            thread_id = await self.thread_service.create_thread(
                title=f"MCP Agent Execution: {agent_name}",
                metadata={"mcp_session": session_id}
            )
            
            # Execute agent
            result = await self.agent_service.execute_agent(
                agent_name=agent_name,
                thread_id=thread_id,
                input_data=input_data,
                config=config
            )
            
            return {
                "type": "text",
                "text": json.dumps({
                    "status": "success",
                    "thread_id": thread_id,
                    "run_id": result.get("run_id"),
                    "initial_response": result.get("response")
                }, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error executing agent: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error executing agent: {str(e)}"
            }
            
    async def get_agent_status(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Get status of agent execution"""
        try:
            run_id = arguments["run_id"]
            
            status = await self.agent_service.get_run_status(run_id)
            
            return {
                "type": "text",
                "text": json.dumps(status, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error getting agent status: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error getting agent status: {str(e)}"
            }
            
    async def list_available_agents(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """List available agents"""
        try:
            category = arguments.get("category")
            
            agents = await self.agent_service.list_agents(category=category)
            
            return {
                "type": "text",
                "text": json.dumps(agents, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error listing agents: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error listing agents: {str(e)}"
            }
            
    async def analyze_workload(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Analyze AI workload"""
        try:
            workload_data = arguments["workload_data"]
            metrics = arguments.get("metrics", ["cost", "latency", "throughput"])
            
            # Use optimization agent for analysis
            analysis = await self.agent_service.analyze_workload(
                workload_data=workload_data,
                metrics=metrics
            )
            
            return {
                "type": "text",
                "text": json.dumps(analysis, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing workload: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error analyzing workload: {str(e)}"
            }
            
    async def optimize_prompt(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Optimize prompt for cost/performance"""
        try:
            prompt = arguments["prompt"]
            target = arguments.get("target", "balanced")
            model = arguments.get("model")
            
            # Use optimization service
            optimized = await self.agent_service.optimize_prompt(
                prompt=prompt,
                target=target,
                model=model
            )
            
            return {
                "type": "text",
                "text": json.dumps(optimized, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error optimizing prompt: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error optimizing prompt: {str(e)}"
            }
            
    async def query_corpus(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Query document corpus"""
        try:
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            filters = arguments.get("filters", {})
            
            results = await self.corpus_service.search(
                query=query,
                limit=limit,
                filters=filters
            )
            
            return {
                "type": "text",
                "text": json.dumps(results, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error querying corpus: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error querying corpus: {str(e)}"
            }
            
    async def generate_synthetic_data(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Generate synthetic test data"""
        try:
            schema = arguments["schema"]
            count = arguments.get("count", 10)
            format_type = arguments.get("format", "json")
            
            data = await self.synthetic_data_service.generate(
                schema=schema,
                count=count,
                format_type=format_type
            )
            
            return {
                "type": "text",
                "text": f"Generated {count} records in {format_type} format",
                "data": data if format_type == "json" else None
            }
            
        except Exception as e:
            logger.error(f"Error generating synthetic data: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error generating synthetic data: {str(e)}"
            }
            
    async def create_thread(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Create conversation thread"""
        try:
            title = arguments.get("title", "New Thread")
            metadata = arguments.get("metadata", {})
            metadata["mcp_session"] = session_id
            
            thread_id = await self.thread_service.create_thread(
                title=title,
                metadata=metadata
            )
            
            return {
                "type": "text",
                "text": json.dumps({
                    "thread_id": thread_id,
                    "title": title,
                    "created": True
                }, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error creating thread: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error creating thread: {str(e)}"
            }
            
    async def get_thread_history(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Get thread message history"""
        try:
            thread_id = arguments["thread_id"]
            limit = arguments.get("limit", 50)
            
            messages = await self.thread_service.get_thread_messages(
                thread_id=thread_id,
                limit=limit
            )
            
            return {
                "type": "text",
                "text": json.dumps(messages, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error getting thread history: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error getting thread history: {str(e)}"
            }
            
    async def get_supply_catalog(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Get supply catalog"""
        try:
            filter_criteria = arguments.get("filter")
            
            catalog = await self.supply_catalog_service.get_catalog(
                filter_criteria=filter_criteria
            )
            
            return {
                "type": "text",
                "text": json.dumps(catalog, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error getting supply catalog: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error getting supply catalog: {str(e)}"
            }
            
    async def execute_optimization_pipeline(self, arguments: Dict[str, Any], session_id: Optional[str]) -> Dict[str, Any]:
        """Execute full optimization pipeline"""
        try:
            input_data = arguments["input_data"]
            optimization_goals = arguments.get("optimization_goals", ["cost", "performance"])
            
            # Create thread for pipeline
            thread_id = await self.thread_service.create_thread(
                title="MCP Optimization Pipeline",
                metadata={
                    "mcp_session": session_id,
                    "goals": optimization_goals
                }
            )
            
            # Execute supervisor agent for full pipeline
            result = await self.agent_service.execute_agent(
                agent_name="SupervisorAgent",
                thread_id=thread_id,
                input_data={
                    **input_data,
                    "optimization_goals": optimization_goals
                },
                config={"pipeline_mode": True}
            )
            
            return {
                "type": "text",
                "text": json.dumps({
                    "status": "pipeline_started",
                    "thread_id": thread_id,
                    "run_id": result.get("run_id"),
                    "optimization_goals": optimization_goals
                }, indent=2)
            }
            
        except Exception as e:
            logger.error(f"Error executing optimization pipeline: {e}", exc_info=True)
            return {
                "type": "text",
                "text": f"Error executing optimization pipeline: {str(e)}"
            }
            
    async def register_client(
        self,
        db_session: AsyncSession,
        name: str,
        client_type: str,
        api_key: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> MCPClient:
        """Register a new MCP client"""
        try:
            # Hash API key if provided
            api_key_hash = None
            if api_key:
                api_key_hash = self.security_service.hash_password(api_key)
                
            client = MCPClient(
                name=name,
                client_type=client_type,
                api_key_hash=api_key_hash,
                permissions=permissions or [],
                metadata=metadata or {}
            )
            
            # TODO: Store in database
            logger.info(f"Registered MCP client: {client.id} ({client_type})")
            
            return client
            
        except Exception as e:
            logger.error(f"Error registering MCP client: {e}", exc_info=True)
            raise NetraException(f"Failed to register MCP client: {str(e)}")
            
    async def validate_client_access(
        self,
        db_session: AsyncSession,
        client_id: str,
        required_permission: str
    ) -> bool:
        """Validate client has required permission"""
        try:
            # TODO: Implement actual permission check from database
            return True
            
        except Exception as e:
            logger.error(f"Error validating client access: {e}", exc_info=True)
            return False
            
    async def record_tool_execution(
        self,
        db_session: AsyncSession,
        execution: MCPToolExecution
    ):
        """Record tool execution in database"""
        try:
            # TODO: Store in database
            logger.info(f"Recorded tool execution: {execution.tool_name} ({execution.status})")
            
        except Exception as e:
            logger.error(f"Error recording tool execution: {e}", exc_info=True)
            
    def get_mcp_server(self) -> MCPServer:
        """Get MCP server instance"""
        return self.mcp_server
