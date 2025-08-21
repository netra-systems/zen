"""Agent Tools Module - MCP tools for agent operations"""

import json
from typing import Dict, Any, List, Optional
from netra_backend.app.logging_config import CentralLogger
from netra_backend.app.core.exceptions_base import NetraException

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
        result = await self._execute_agent_service(server, agent_name, thread_id, input_data, config)
        return self._format_agent_result(thread_id, result)
    
    async def _execute_agent_service(self, server, agent_name: str, thread_id: Optional[str],
                                    input_data: Dict[str, Any], config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute agent via service"""
        return await server.agent_service.execute_agent(
            agent_name=agent_name, thread_id=thread_id,
            input_data=input_data, config=config or {}
        )
    
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
            return await self._get_agent_run_status(server, run_id)
    
    async def _get_agent_run_status(self, server, run_id: str) -> str:
        """Get agent run status with error handling"""
        if not server.agent_service:
            return json.dumps({"error": "Agent service not available"})
        try:
            return await self._fetch_agent_status(server, run_id)
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    async def _fetch_agent_status(self, server, run_id: str) -> str:
        """Fetch status from agent service"""
        status = await server.agent_service.get_run_status(run_id)
        return json.dumps(status, indent=2)
    
    def _register_list_agents_tool(self, server):
        """Register list agents tool"""
        @self.mcp.tool()
        async def list_agents(category: Optional[str] = None) -> str:
            """List available Netra agents"""
            agents = self._get_available_agents()
            filtered_agents = self._filter_agents_by_category(agents, category)
            return json.dumps(filtered_agents, indent=2)
    
    def _filter_agents_by_category(self, agents: List[Dict[str, str]], 
                                  category: Optional[str]) -> List[Dict[str, str]]:
        """Filter agents by category if specified"""
        if category:
            return [a for a in agents if a["category"] == category]
        return agents
    
    def _get_available_agents(self) -> List[Dict[str, str]]:
        """Get list of available agents"""
        agent_groups = self._collect_agent_groups()
        return self._flatten_agent_groups(agent_groups)
    
    def _collect_agent_groups(self) -> List[List[Dict[str, str]]]:
        """Collect all agent groups"""
        core_groups = self._get_core_agent_groups()
        extended_groups = self._get_extended_agent_groups()
        return core_groups + extended_groups
    
    def _get_core_agent_groups(self) -> List[List[Dict[str, str]]]:
        """Get core agent groups"""
        return [
            self._get_orchestration_agents(), self._get_analysis_agents(),
            self._get_data_agents()
        ]
    
    def _get_extended_agent_groups(self) -> List[List[Dict[str, str]]]:
        """Get extended agent groups"""
        return [
            self._get_optimization_agents(), self._get_planning_agents(),
            self._get_reporting_agents()
        ]
    
    def _flatten_agent_groups(self, groups: List[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """Flatten grouped agents into single list"""
        result = []
        self._extend_result_with_groups(result, groups)
        return result
    
    def _extend_result_with_groups(self, result: List[Dict[str, str]], 
                                  groups: List[List[Dict[str, str]]]) -> None:
        """Extend result list with agent groups"""
        for group in groups:
            result.extend(group)
    
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