"""Netra MCP Server Prompts Registration"""

from typing import Dict, Any, List, Optional


class NetraMCPPrompts:
    """Prompt registration for Netra MCP Server"""
    
    def __init__(self, mcp_instance: Any) -> None:
        self.mcp = mcp_instance
        
    def register_all(self, server: Any) -> None:
        """Register all prompts with the MCP server"""
        self._register_optimization_prompt(server)
        self._register_prompt_optimization(server)
        self._register_model_selection(server)
    
    def _register_optimization_prompt(self, server: Any) -> None:
        """Register optimization request prompt"""
        
        @self.mcp.prompt()
        async def optimization_request(
            workload_description: str,
            monthly_budget: float,
            quality_requirements: str = "high"
        ) -> List[Dict[str, str]]:
            """Generate an optimization request prompt"""
            content = self._build_optimization_content(workload_description, monthly_budget, quality_requirements)
            return self._create_user_prompt(content)
    
    def _register_prompt_optimization(self, server: Any) -> None:
        """Register prompt optimization prompt"""
        
        @self.mcp.prompt()
        async def prompt_optimization(
            original_prompt: str,
            target_model: str,
            optimization_goal: str = "balanced"
        ) -> List[Dict[str, str]]:
            """Generate a prompt optimization request"""
            system_prompt = self._get_prompt_engineer_system_message()
            user_content = self._build_prompt_optimization_content(original_prompt, target_model, optimization_goal)
            return [system_prompt, self._create_user_message(user_content)]
    
    def _register_model_selection(self, server: Any) -> None:
        """Register model selection prompt"""
        
        @self.mcp.prompt()
        async def model_selection(
            task_description: str,
            constraints: Optional[Dict[str, Any]] = None
        ) -> List[Dict[str, str]]:
            """Generate a model selection request"""
            constraints_str = self._format_constraints(constraints)
            content = self._build_model_selection_content(task_description, constraints_str)
            return self._create_user_prompt(content)
    
    def _build_optimization_content(self, workload_description: str, 
                                   monthly_budget: float, quality_requirements: str) -> str:
        """Build optimization request content"""
        return f"""Please analyze and optimize the following AI workload:

Workload Description: {workload_description}
Monthly Budget: ${monthly_budget:,.2f}
Quality Requirements: {quality_requirements}

Please provide:
1. Current cost analysis
2. Optimization recommendations
3. Implementation strategy
4. Expected savings
5. Quality impact assessment"""
    
    def _create_user_prompt(self, content: str) -> List[Dict[str, str]]:
        """Create user prompt structure"""
        return [{"role": "user", "content": content}]
    
    def _get_prompt_engineer_system_message(self) -> Dict[str, str]:
        """Get system message for prompt engineering"""
        return {
            "role": "system",
            "content": "You are an expert prompt engineer specializing in optimizing prompts for different LLMs."
        }
    
    def _build_prompt_optimization_content(self, original_prompt: str, 
                                          target_model: str, optimization_goal: str) -> str:
        """Build prompt optimization content"""
        return f"""Optimize the following prompt for {target_model} with a focus on {optimization_goal}:

Original Prompt:
{original_prompt}

Please provide:
1. Optimized prompt
2. Explanation of changes
3. Expected token reduction
4. Quality impact assessment"""
    
    def _create_user_message(self, content: str) -> Dict[str, str]:
        """Create user message structure"""
        return {"role": "user", "content": content}
    
    def _format_constraints(self, constraints: Optional[Dict[str, Any]]) -> str:
        """Format constraints for display"""
        if not constraints:
            return "No specific constraints"
        return "\n".join([f"- {k}: {v}" for k, v in constraints.items()])
    
    def _build_model_selection_content(self, task_description: str, constraints_str: str) -> str:
        """Build model selection content"""
        return f"""Help me select the best AI model for this task:

Task: {task_description}

Constraints:
{constraints_str}

Please recommend:
1. Primary model choice
2. Alternative options
3. Trade-offs analysis
4. Cost comparison
5. Performance expectations"""