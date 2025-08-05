from typing import Any, Dict
from app.services.deep_agent_v3.tools.base import BaseTool, ToolMetadata

class CostEstimator(BaseTool):
    metadata = ToolMetadata(
        name="CostEstimator",
        description="Estimates the cost of a given prompt using the llm_connector.",
        version="1.0.0",
        status="production"
    )

    async def execute(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Estimates the cost of a given prompt using the llm_connector."""
        estimation_prompt = f"""
        Given the following prompt, estimate the cost in USD to run it.
        Prompt: {prompt}
        Context: {context}
        
        Return only the estimated cost as a float.
        """
        
        response = await self.llm_connector.get_completion(estimation_prompt)
        
        try:
            estimated_cost = float(response)
        except (ValueError, TypeError):
            estimated_cost = 0.01  # Default value if parsing fails
            
        return {"estimated_cost_usd": estimated_cost}