"""Optimization Tools Module - MCP tools for optimization operations"""

import json
from typing import Dict, Any, List, Optional


class OptimizationTools:
    """Optimization tools registration"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
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