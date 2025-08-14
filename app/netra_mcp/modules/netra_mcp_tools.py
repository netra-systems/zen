"""Netra MCP Server Tools Registration"""

import json
from typing import Dict, Any, List, Optional

from app.logging_config import CentralLogger
from app.core.exceptions import NetraException

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
        
        @self.mcp.tool()
        async def run_agent(
            agent_name: str,
            input_data: Dict[str, Any],
            config: Optional[Dict[str, Any]] = None
        ) -> str:
            """Execute a Netra optimization agent"""
            if not server.agent_service:
                raise NetraException("Agent service not available")
                
            try:
                thread_id = None
                if server.thread_service:
                    thread_id = await server.thread_service.create_thread(
                        title=f"MCP Agent: {agent_name}",
                        metadata={"source": "mcp"}
                    )
                
                result = await server.agent_service.execute_agent(
                    agent_name=agent_name,
                    thread_id=thread_id,
                    input_data=input_data,
                    config=config or {}
                )
                
                return json.dumps({
                    "status": "success",
                    "thread_id": thread_id,
                    "run_id": result.get("run_id"),
                    "response": result.get("response")
                }, indent=2)
                
            except Exception as e:
                logger.error(f"Agent execution failed: {e}", exc_info=True)
                return json.dumps({"status": "error", "error": str(e)}, indent=2)
        
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
        
        @self.mcp.tool()
        async def list_agents(category: Optional[str] = None) -> str:
            """List available Netra agents"""
            agents = [
                {"name": "SupervisorAgent", "category": "orchestration",
                 "description": "Main orchestrator for multi-agent optimization workflows"},
                {"name": "TriageSubAgent", "category": "analysis",
                 "description": "Request triage and approach determination"},
                {"name": "DataSubAgent", "category": "data",
                 "description": "Data collection and context gathering"},
                {"name": "OptimizationsCoreSubAgent", "category": "optimization",
                 "description": "Core optimization recommendations and strategies"},
                {"name": "ActionsToMeetGoalsSubAgent", "category": "planning",
                 "description": "Goal-oriented action planning and implementation"},
                {"name": "ReportingSubAgent", "category": "reporting",
                 "description": "Final report compilation and presentation"}
            ]
            
            if category:
                agents = [a for a in agents if a["category"] == category]
                
            return json.dumps(agents, indent=2)
    
    def _register_optimization_tools(self, server):
        """Register optimization tools"""
        
        @self.mcp.tool()
        async def analyze_workload(
            workload_data: Dict[str, Any],
            metrics: Optional[List[str]] = None
        ) -> str:
            """Analyze AI workload characteristics and performance"""
            if not server.agent_service:
                return json.dumps({"error": "Agent service not available"})
                
            try:
                metrics = metrics or ["cost", "latency", "throughput", "token_usage"]
                analysis = await server.agent_service.analyze_workload(
                    workload_data=workload_data,
                    metrics=metrics
                )
                return json.dumps(analysis, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def optimize_prompt(
            prompt: str,
            target: str = "balanced",
            model: Optional[str] = None
        ) -> str:
            """Optimize prompts for cost and performance"""
            if not server.agent_service:
                return json.dumps({"error": "Agent service not available"})
                
            try:
                optimized = await server.agent_service.optimize_prompt(
                    prompt=prompt, target=target, model=model
                )
                return json.dumps(optimized, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def execute_optimization_pipeline(
            input_data: Dict[str, Any],
            optimization_goals: Optional[List[str]] = None
        ) -> str:
            """Execute full AI optimization pipeline"""
            if not server.agent_service:
                return json.dumps({"error": "Agent service not available"})
                
            try:
                goals = optimization_goals or ["cost", "performance", "quality"]
                
                thread_id = None
                if server.thread_service:
                    thread_id = await server.thread_service.create_thread(
                        title="MCP Optimization Pipeline",
                        metadata={"source": "mcp", "goals": goals}
                    )
                
                result = await server.agent_service.execute_agent(
                    agent_name="SupervisorAgent",
                    thread_id=thread_id,
                    input_data={**input_data, "optimization_goals": goals},
                    config={"pipeline_mode": True}
                )
                
                return json.dumps({
                    "status": "pipeline_started",
                    "thread_id": thread_id,
                    "run_id": result.get("run_id"),
                    "optimization_goals": goals
                }, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    def _register_data_tools(self, server):
        """Register data management tools"""
        
        @self.mcp.tool()
        async def query_corpus(
            query: str,
            limit: int = 10,
            filters: Optional[Dict[str, Any]] = None
        ) -> str:
            """Search the document corpus for relevant information"""
            if not server.corpus_service:
                return json.dumps({"error": "Corpus service not available"})
                
            try:
                results = await server.corpus_service.search(
                    query=query, limit=limit, filters=filters or {}
                )
                return json.dumps(results, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
        @self.mcp.tool()
        async def generate_synthetic_data(
            schema: Dict[str, Any],
            count: int = 10,
            format: str = "json"
        ) -> str:
            """Generate synthetic test data for AI workloads"""
            if not server.synthetic_data_service:
                return json.dumps({"error": "Synthetic data service not available"})
                
            try:
                data = await server.synthetic_data_service.generate(
                    schema=schema, count=count, format_type=format
                )
                
                if format == "json":
                    return json.dumps({
                        "status": "success", "count": count, "data": data
                    }, indent=2)
                else:
                    return json.dumps({
                        "status": "success", "count": count, "format": format,
                        "message": f"Generated {count} records in {format} format"
                    }, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
    
    def _register_thread_tools(self, server):
        """Register thread management tools"""
        
        @self.mcp.tool()
        async def create_thread(
            title: str = "New Thread",
            metadata: Optional[Dict[str, Any]] = None
        ) -> str:
            """Create a new conversation thread"""
            if not server.thread_service:
                return json.dumps({"error": "Thread service not available"})
                
            try:
                metadata = metadata or {}
                metadata["source"] = "mcp"
                
                thread_id = await server.thread_service.create_thread(
                    title=title, metadata=metadata
                )
                
                return json.dumps({
                    "thread_id": thread_id, "title": title, "created": True
                }, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})
        
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
            if not server.supply_catalog_service:
                # Return mock data if service not available
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
                
            try:
                catalog = await server.supply_catalog_service.get_catalog(
                    filter_criteria=filter
                )
                return json.dumps(catalog, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})