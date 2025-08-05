from typing import Any, Dict
from app.services.deep_agent_v3.tools.base import BaseTool, ToolMetadata

class PerformancePredictor(BaseTool):
    name = "performance_predictor"
    metadata = ToolMetadata(
        name="PerformancePredictor",
        description="Predicts the performance of a given prompt using the llm_connector.",
        version="1.0.0",
        status="in_review"
    )

    async def run(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Predicts the performance of a given prompt using the llm_connector."""
        prediction_prompt = f"""
        Given the following prompt, predict the latency in milliseconds.
        Prompt: {prompt}
        Context: {context}
        
        Return only the predicted latency as an integer.
        """
        
        llm = self.get_llm()
        response = await llm.ainvoke(prediction_prompt)
        
        try:
            predicted_latency = int(response.content)
        except (ValueError, TypeError):
            predicted_latency = 250  # Default value if parsing fails
            
        return {"predicted_latency_ms": predicted_latency}