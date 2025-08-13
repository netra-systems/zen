"""Netra MCP Server Prompts Registration"""

from typing import Dict, Any, List, Optional


class NetraMCPPrompts:
    """Prompt registration for Netra MCP Server"""
    
    def __init__(self, mcp_instance):
        self.mcp = mcp_instance
        
    def register_all(self, server):
        """Register all prompts with the MCP server"""
        self._register_optimization_prompt(server)
        self._register_prompt_optimization(server)
        self._register_model_selection(server)
    
    def _register_optimization_prompt(self, server):
        """Register optimization request prompt"""
        
        @self.mcp.prompt()
        async def optimization_request(
            workload_description: str,
            monthly_budget: float,
            quality_requirements: str = "high"
        ) -> List[Dict[str, str]]:
            """Generate an optimization request prompt"""
            return [
                {
                    "role": "user",
                    "content": f"""Please analyze and optimize the following AI workload:

Workload Description: {workload_description}
Monthly Budget: ${monthly_budget:,.2f}
Quality Requirements: {quality_requirements}

Please provide:
1. Current cost analysis
2. Optimization recommendations
3. Implementation strategy
4. Expected savings
5. Quality impact assessment"""
                }
            ]
    
    def _register_prompt_optimization(self, server):
        """Register prompt optimization prompt"""
        
        @self.mcp.prompt()
        async def prompt_optimization(
            original_prompt: str,
            target_model: str,
            optimization_goal: str = "balanced"
        ) -> List[Dict[str, str]]:
            """Generate a prompt optimization request"""
            return [
                {
                    "role": "system",
                    "content": "You are an expert prompt engineer specializing in optimizing prompts for different LLMs."
                },
                {
                    "role": "user",
                    "content": f"""Optimize the following prompt for {target_model} with a focus on {optimization_goal}:

Original Prompt:
{original_prompt}

Please provide:
1. Optimized prompt
2. Explanation of changes
3. Expected token reduction
4. Quality impact assessment"""
                }
            ]
    
    def _register_model_selection(self, server):
        """Register model selection prompt"""
        
        @self.mcp.prompt()
        async def model_selection(
            task_description: str,
            constraints: Optional[Dict[str, Any]] = None
        ) -> List[Dict[str, str]]:
            """Generate a model selection request"""
            constraints_str = ""
            if constraints:
                constraints_str = "\n".join([f"- {k}: {v}" for k, v in constraints.items()])
            
            return [
                {
                    "role": "user",
                    "content": f"""Help me select the best AI model for this task:

Task: {task_description}

Constraints:
{constraints_str if constraints_str else "No specific constraints"}

Please recommend:
1. Primary model choice
2. Alternative options
3. Trade-offs analysis
4. Cost comparison
5. Performance expectations"""
                }
            ]