from typing import Any, Dict
from app.services.apex_optimizer_agent.tools.base import BaseTool, ToolMetadata

class CostEstimator(BaseTool):
    name = "cost_estimator"
    metadata = ToolMetadata(
        name="CostEstimator",
        description="Estimates the cost of a given prompt using the llm_connector.",
        version="1.0.0",
        status="in_review"
    )

    from app.services.apex_optimizer_agent.tools.context import ToolContext

class CostEstimator(BaseTool):
    name = "cost_estimator"
    metadata = ToolMetadata(
        name="CostEstimator",
        description="Estimates the cost of a given prompt using the llm_connector.",
        version="1.0.0",
        status="in_review"
    )

    async def run(self, prompt: str, context: ToolContext) -> Dict[str, Any]:
        """Estimates the cost of a given prompt using the llm_connector."""
        estimation_prompt = f"""
        Given the following prompt, estimate the cost in USD to run it.
        Prompt: {prompt}
        Context: {context}
        
        Return only the estimated cost as a float.
        """
        
        llm = self.get_llm()
        response = await llm.ainvoke(estimation_prompt)
        
        try:
            estimated_cost = float(response.content)
        except (ValueError, TypeError):
            estimated_cost = 0.01  # Default value if parsing fails
            
        return {"estimated_cost_usd": estimated_cost}