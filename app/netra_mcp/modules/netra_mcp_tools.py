"""Netra MCP Server Tools Registration"""

import json
from typing import Dict, Any, List, Optional

from app.logging_config import CentralLogger
from app.core.exceptions_base import NetraException

logger = CentralLogger()


class NetraMCPTools:
    """Tool registration for Netra MCP Server"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
        """Register all tools with the MCP server"""
        self._register_agent_tools(server)
        self._register_optimization_tools(server)
        self._register_data_tools(server)
        self._register_thread_tools(server)
        self._register_catalog_tools(server)
    
    def _register_agent_tools(self, server):
        """Register agent operation tools"""
        self._register_run_agent_tool(server)
        self._register_agent_status_tool(server)
        self._register_list_agents_tool(server)
    
    def _register_run_agent_tool(self, server):
        """Register run agent tool"""
        @self.mcp.tool()
        async def run_agent(
            agent_name: str,
            input_data: Dict[str, Any],
            config: Optional[Dict[str, Any]] = None
        ) -> str:
            """Execute a Netra optimization agent"""
            return await self._execute_agent(server, agent_name, input_data, config)
    
    async def _execute_agent(self, server, agent_name: str, input_data: Dict[str, Any], 
                            config: Optional[Dict[str, Any]]) -> str:
        """Execute agent with error handling"""
        self._validate_agent_service(server)
        try:
            return await self._perform_agent_execution(server, agent_name, input_data, config)
        except Exception as e:
            return self._handle_agent_error(e)
    
    def _validate_agent_service(self, server) -> None:
        """Validate agent service availability"""
        if not server.agent_service:
            raise NetraException("Agent service not available")
    
    async def _perform_agent_execution(self, server, agent_name: str, input_data: Dict[str, Any], 
                                      config: Optional[Dict[str, Any]]) -> str:
        """Perform the actual agent execution"""
        thread_id = await self._create_agent_thread(server, agent_name)
        result = await server.agent_service.execute_agent(
            agent_name=agent_name, thread_id=thread_id,
            input_data=input_data, config=config or {}
        )
        return self._format_agent_result(thread_id, result)
    
    def _handle_agent_error(self, error: Exception) -> str:
        """Handle agent execution errors"""
        logger.error(f"Agent execution failed: {error}", exc_info=True)
        return json.dumps({"status": "error", "error": str(error)}, indent=2)
    
    async def _create_agent_thread(self, server, agent_name: str) -> Optional[str]:
        """Create thread for agent execution"""
        if not server.thread_service:
            return None
        return await server.thread_service.create_thread(
            title=f"MCP Agent: {agent_name}",
            metadata={"source": "mcp"}
        )
    
    def _format_agent_result(self, thread_id: Optional[str], result: Dict[str, Any]) -> str:
        """Format agent execution result"""
        return json.dumps({
            "status": "success",
            "thread_id": thread_id,
            "run_id": result.get("run_id"),
            "response": result.get("response")
        }, indent=2)
    
    def _register_agent_status_tool(self, server):
        """Register agent status tool"""
        @self.mcp.tool()
        async def get_agent_status(run_id: str) -> str:
            """Check the status of an agent execution"""
            if not server.agent_service:
                return json.dumps({"error": "Agent service not available"})
            try:
                status = await server.agent_service.get_run_status(run_id)
                return json.dumps(status, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    def _register_list_agents_tool(self, server):
        """Register list agents tool"""
        @self.mcp.tool()
        async def list_agents(category: Optional[str] = None) -> str:
            """List available Netra agents"""
            agents = self._get_available_agents()
            if category:
                agents = [a for a in agents if a["category"] == category]
            return json.dumps(agents, indent=2)
    
    def _get_available_agents(self) -> List[Dict[str, str]]:
        """Get list of available agents"""
        agent_groups = self._collect_agent_groups()
        return self._flatten_agent_groups(agent_groups)
    
    def _collect_agent_groups(self) -> List[List[Dict[str, str]]]:
        """Collect all agent groups"""
        return [
            self._get_orchestration_agents(), self._get_analysis_agents(),
            self._get_data_agents(), self._get_optimization_agents(),
            self._get_planning_agents(), self._get_reporting_agents()
        ]
    
    def _flatten_agent_groups(self, groups: List[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """Flatten grouped agents into single list"""
        result = []
        for group in groups:
            result.extend(group)
        return result
    
    def _get_orchestration_agents(self) -> List[Dict[str, str]]:
        """Get orchestration category agents"""
        return [{"name": "SupervisorAgent", "category": "orchestration",
                "description": "Main orchestrator for multi-agent optimization workflows"}]
    
    def _get_analysis_agents(self) -> List[Dict[str, str]]:
        """Get analysis category agents"""
        return [{"name": "TriageSubAgent", "category": "analysis",
                "description": "Request triage and approach determination"}]
    
    def _get_data_agents(self) -> List[Dict[str, str]]:
        """Get data category agents"""
        return [{"name": "DataSubAgent", "category": "data",
                "description": "Data collection and context gathering"}]
    
    def _get_optimization_agents(self) -> List[Dict[str, str]]:
        """Get optimization category agents"""
        return [{"name": "OptimizationsCoreSubAgent", "category": "optimization",
                "description": "Core optimization recommendations and strategies"}]
    
    def _get_planning_agents(self) -> List[Dict[str, str]]:
        """Get planning category agents"""
        return [{"name": "ActionsToMeetGoalsSubAgent", "category": "planning",
                "description": "Goal-oriented action planning and implementation"}]
    
    def _get_reporting_agents(self) -> List[Dict[str, str]]:
        """Get reporting category agents"""
        return [{"name": "ReportingSubAgent", "category": "reporting",
                "description": "Final report compilation and presentation"}]
    
    def _register_optimization_tools(self, server):
        """Register optimization tools"""
        self._register_workload_analyzer(server)
        self._register_prompt_optimizer(server)
        self._register_pipeline_executor(server)
        
    def _register_workload_analyzer(self, server):
        """Register workload analysis tool"""
        @self.mcp.tool()
        async def analyze_workload(
            workload_data: Dict[str, Any],
            metrics: Optional[List[str]] = None
        ) -> str:
            """Analyze AI workload characteristics and performance"""
            return await self._execute_workload_analysis(server, workload_data, metrics)
    
    async def _execute_workload_analysis(self, server, workload_data: Dict[str, Any], 
                                       metrics: Optional[List[str]]) -> str:
        """Execute workload analysis with error handling"""
        if not server.agent_service:
            return self._format_service_error("Agent service not available")
        try:
            return await self._perform_workload_analysis(server, workload_data, metrics)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_workload_analysis(self, server, workload_data: Dict[str, Any], 
                                        metrics: Optional[List[str]]) -> str:
        """Perform workload analysis with default metrics"""
        metrics = metrics or ["cost", "latency", "throughput", "token_usage"]
        analysis = await server.agent_service.analyze_workload(
            workload_data=workload_data, metrics=metrics
        )
        return json.dumps(analysis, indent=2)
    
    def _format_service_error(self, error_message: str) -> str:
        """Format service error response"""
        return json.dumps({"error": error_message})
    
    def _register_prompt_optimizer(self, server):
        """Register prompt optimization tool"""
        @self.mcp.tool()
        async def optimize_prompt(
            prompt: str,
            target: str = "balanced",
            model: Optional[str] = None
        ) -> str:
            """Optimize prompts for cost and performance"""
            return await self._execute_prompt_optimization(server, prompt, target, model)
    
    async def _execute_prompt_optimization(self, server, prompt: str, 
                                         target: str, model: Optional[str]) -> str:
        """Execute prompt optimization with error handling"""
        if not server.agent_service:
            return self._format_service_error("Agent service not available")
        try:
            return await self._perform_prompt_optimization(server, prompt, target, model)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_prompt_optimization(self, server, prompt: str, 
                                          target: str, model: Optional[str]) -> str:
        """Perform prompt optimization operation"""
        optimized = await server.agent_service.optimize_prompt(
            prompt=prompt, target=target, model=model
        )
        return json.dumps(optimized, indent=2)
    
    def _register_pipeline_executor(self, server):
        """Register optimization pipeline executor"""
        @self.mcp.tool()
        async def execute_optimization_pipeline(
            input_data: Dict[str, Any],
            optimization_goals: Optional[List[str]] = None
        ) -> str:
            """Execute full AI optimization pipeline"""
            return await self._execute_optimization_pipeline_impl(server, input_data, optimization_goals)
    
    async def _execute_optimization_pipeline_impl(self, server, input_data: Dict[str, Any],
                                                 optimization_goals: Optional[List[str]]) -> str:
        """Execute optimization pipeline implementation"""
        if not server.agent_service:
            return self._format_service_error("Agent service not available")
        try:
            return await self._perform_pipeline_execution(server, input_data, optimization_goals)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_pipeline_execution(self, server, input_data: Dict[str, Any],
                                         optimization_goals: Optional[List[str]]) -> str:
        """Perform pipeline execution with default goals"""
        goals = optimization_goals or ["cost", "performance", "quality"]
        thread_id = await self._create_pipeline_thread(server, goals)
        result = await self._execute_pipeline_agent(server, input_data, goals, thread_id)
        return self._format_pipeline_result(thread_id, result, goals)
    
    async def _create_pipeline_thread(self, server, goals: List[str]) -> Optional[str]:
        """Create thread for optimization pipeline"""
        if not server.thread_service:
            return None
        return await server.thread_service.create_thread(
            title="MCP Optimization Pipeline",
            metadata={"source": "mcp", "goals": goals}
        )
    
    async def _execute_pipeline_agent(self, server, input_data: Dict[str, Any], 
                                     goals: List[str], thread_id: Optional[str]):
        """Execute the pipeline agent with configuration"""
        return await server.agent_service.execute_agent(
            agent_name="SupervisorAgent",
            thread_id=thread_id,
            input_data={**input_data, "optimization_goals": goals},
            config={"pipeline_mode": True}
        )
    
    def _format_pipeline_result(self, thread_id: Optional[str], result: Dict[str, Any], 
                               goals: List[str]) -> str:
        """Format pipeline execution result"""
        return json.dumps({
            "status": "pipeline_started",
            "thread_id": thread_id,
            "run_id": result.get("run_id"),
            "optimization_goals": goals
        }, indent=2)
    
    def _register_data_tools(self, server):
        """Register data management tools"""
        self._register_corpus_query_tool(server)
        self._register_synthetic_data_tool(server)
    
    def _register_corpus_query_tool(self, server):
        """Register corpus query tool"""
        @self.mcp.tool()
        async def query_corpus(
            query: str,
            limit: int = 10,
            filters: Optional[Dict[str, Any]] = None
        ) -> str:
            """Search the document corpus for relevant information"""
            return await self._execute_corpus_query(server, query, limit, filters)
    
    async def _execute_corpus_query(self, server, query: str, limit: int, 
                                   filters: Optional[Dict[str, Any]]) -> str:
        """Execute corpus query with error handling"""
        if not server.corpus_service:
            return self._format_service_error("Corpus service not available")
        try:
            return await self._perform_corpus_search(server, query, limit, filters)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_corpus_search(self, server, query: str, limit: int, 
                                    filters: Optional[Dict[str, Any]]) -> str:
        """Perform corpus search operation"""
        results = await server.corpus_service.search(
            query=query, limit=limit, filters=filters or {}
        )
        return json.dumps(results, indent=2)
    
    def _register_synthetic_data_tool(self, server):
        """Register synthetic data generation tool"""
        @self.mcp.tool()
        async def generate_synthetic_data(
            schema: Dict[str, Any],
            count: int = 10,
            format: str = "json"
        ) -> str:
            """Generate synthetic test data for AI workloads"""
            return await self._execute_synthetic_data_generation(server, schema, count, format)
    
    async def _execute_synthetic_data_generation(self, server, schema: Dict[str, Any], 
                                               count: int, format: str) -> str:
        """Execute synthetic data generation with error handling"""
        if not server.synthetic_data_service:
            return self._format_service_error("Synthetic data service not available")
        try:
            return await self._perform_synthetic_generation(server, schema, count, format)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_synthetic_generation(self, server, schema: Dict[str, Any], 
                                           count: int, format: str) -> str:
        """Perform synthetic data generation"""
        data = await server.synthetic_data_service.generate(
            schema=schema, count=count, format_type=format
        )
        return self._format_synthetic_data_result(data, count, format)
    
    def _format_synthetic_data_result(self, data: Any, count: int, format: str) -> str:
        """Format synthetic data generation result"""
        if format == "json":
            return json.dumps({
                "status": "success", "count": count, "data": data
            }, indent=2)
        else:
            return json.dumps({
                "status": "success", "count": count, "format": format,
                "message": f"Generated {count} records in {format} format"
            }, indent=2)
    
    def _register_thread_tools(self, server):
        """Register thread management tools"""
        self._register_create_thread_tool(server)
        self._register_thread_history_tool(server)
    
    def _register_create_thread_tool(self, server):
        """Register create thread tool"""
        @self.mcp.tool()
        async def create_thread(
            title: str = "New Thread",
            metadata: Optional[Dict[str, Any]] = None
        ) -> str:
            """Create a new conversation thread"""
            return await self._execute_thread_creation(server, title, metadata)
    
    async def _execute_thread_creation(self, server, title: str, 
                                      metadata: Optional[Dict[str, Any]]) -> str:
        """Execute thread creation with error handling"""
        if not server.thread_service:
            return self._format_service_error("Thread service not available")
        try:
            return await self._perform_thread_creation(server, title, metadata)
        except Exception as e:
            return self._format_service_error(str(e))
    
    async def _perform_thread_creation(self, server, title: str, 
                                      metadata: Optional[Dict[str, Any]]) -> str:
        """Perform thread creation operation"""
        metadata = self._prepare_thread_metadata(metadata)
        thread_id = await server.thread_service.create_thread(
            title=title, metadata=metadata
        )
        return self._format_thread_result(thread_id, title)
    
    def _prepare_thread_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare metadata for thread creation"""
        result = metadata or {}
        result["source"] = "mcp"
        return result
    
    def _format_thread_result(self, thread_id: str, title: str) -> str:
        """Format thread creation result"""
        return json.dumps({
            "thread_id": thread_id, "title": title, "created": True
        }, indent=2)
    
    def _register_thread_history_tool(self, server):
        """Register thread history tool"""
        @self.mcp.tool()
        async def get_thread_history(thread_id: str, limit: int = 50) -> str:
            """Get thread message history"""
            if not server.thread_service:
                return json.dumps({"error": "Thread service not available"})
            try:
                messages = await server.thread_service.get_thread_messages(
                    thread_id=thread_id, limit=limit
                )
                return json.dumps(messages, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    def _register_catalog_tools(self, server):
        """Register supply catalog tools"""
        @self.mcp.tool()
        async def get_supply_catalog(filter: Optional[str] = None) -> str:
            """Get available AI models and providers"""
            return await self._execute_catalog_query(server, filter)
    
    async def _execute_catalog_query(self, server, filter: Optional[str]) -> str:
        """Execute catalog query with error handling"""
        if not server.supply_catalog_service:
            return self._get_mock_catalog()
        try:
            catalog = await server.supply_catalog_service.get_catalog(
                filter_criteria=filter
            )
            return json.dumps(catalog, indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def _get_mock_catalog(self) -> str:
        """Get mock catalog data when service unavailable"""
        catalog = {
            "providers": [
                {"name": "Anthropic",
                 "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"]},
                {"name": "OpenAI",
                 "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]},
                {"name": "Google",
                 "models": ["gemini-pro", "gemini-pro-vision"]}
            ]
        }
        return json.dumps(catalog, indent=2)