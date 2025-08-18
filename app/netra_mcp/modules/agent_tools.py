"""Agent Tools Module - MCP tools for agent operations"""

import json
from typing import Dict, Any, List, Optional
from app.logging_config import CentralLogger
from app.core.exceptions_base import NetraException

logger = CentralLogger()


class AgentTools:
    """Agent operation tools registration"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
        """Register all agent tools with the MCP server"""
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