from typing import Any, Dict

from netra_backend.app.services.apex_optimizer_agent.tools.base import (
    BaseTool,
    ToolMetadata,
)
from netra_backend.app.services.context import ToolContext


class PerformancePredictor(BaseTool):
    name = "performance_predictor"
    metadata = ToolMetadata(
        name="PerformancePredictor",
        description="Predicts the performance of a given prompt using the llm_connector.",
        version="1.0.0",
        status="in_review"
    )

    async def run(self, context: ToolContext, prompt: str) -> Dict[str, Any]:
        """Predicts the performance of a given prompt using the llm_connector."""
        prediction_prompt = f"""
        Given the following prompt, predict the latency in milliseconds.
        Prompt: {prompt}
        Context: {context}
        
        Return only the predicted latency as an integer.
        """
        
        llm = context.llm_manager.get_llm(self.llm_name or "default")
        response = await llm.ainvoke(prediction_prompt)
        
        try:
            content = response.content if hasattr(response, 'content') else str(response)
            predicted_latency = int(content)
        except (ValueError, TypeError):
            predicted_latency = 250  # Default value if parsing fails
            
        return {"predicted_latency_ms": predicted_latency}
