from app.llm.llm_manager import LLMManager
import json
from typing import Dict, Any, List

class Triage:
    def __init__(self, llm_manager: LLMManager):
        self.llm_manager = llm_manager

    async def triage_request(self, prompt: str) -> Dict[str, Any]:
        """
        Analyzes the user's prompt to determine the best course of action.
        """
        system_prompt = f"""
            You are an expert at triaging requests for a system that analyzes and optimizes LLM usage.
            Your task is to analyze the user's request and provide a structured response in JSON format with the following keys:
            1.  "triage_category": A high-level category for the request (e.g., "cost_optimization", "performance_tuning", "security_audit").
            2.  "confidence": A float between 0.0 and 1.0, representing your confidence in the categorization.
            3.  "justification": A brief explanation for your choice.
            4.  "suggested_next_steps": A list of recommended actions or tools to address the user's request.
        """
        try:
            llm = self.llm_manager.get_llm("default")
            response = await llm.ainvoke(prompt, system_prompt=system_prompt)
            
            response_data = json.loads(response.content)
            
            return {
                "triage_category": response_data.get("triage_category", "general_inquiry"),
                "confidence": response_data.get("confidence", 0.0),
                "justification": response_data.get("justification", "No justification provided."),
                "suggested_next_steps": response_data.get("suggested_next_steps", [])
            }

        except Exception as e:
            print(f"Error during triage: {e}")
        
        return {
            "triage_category": "general_inquiry",
            "confidence": 0.1,
            "justification": "An error occurred during triage, falling back to a general inquiry.",
            "suggested_next_steps": []
        }
