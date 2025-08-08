import json
from typing import Any
from app.services.apex_optimizer_agent.models import AgentState
from app.config import AppConfig

class ToolDispatcher:
    def __init__(self, llm_connector: any, settings: AppConfig):
        self.llm_connector = llm_connector
        self.settings = settings

    async def run(self, state: AgentState) -> str:
        """Uses an LLM to decide which tool to use based on the user's request."""
        if not state.request.query:
            return "No query found in the request."

        prompt = f'''
        Given the user query, select the best tool to answer the request.
        User Query: {state.request.query}
        Available Tools: ["cost_reduction_quality_preservation", "tool_latency_optimization", "cost_simulation_for_increased_usage", "advanced_optimization_for_core_function", "new_model_effectiveness_analysis", "kv_cache_optimization_audit", "multi_objective_optimization"]
        Output Format (JSON ONLY):
        {{
            "tool_name": "<selected_tool_name>",
            "arguments": {{<arguments_for_the_tool>}}
        }}
        '''

        response_text = await self.llm_connector.generate_text_async(prompt, self.settings.llm_configs['analysis'].model_name, self.settings.llm_configs['analysis'].model_name)
        tool_data = json.loads(response_text)

        state.current_tool_name = tool_data.get("tool_name")
        state.current_tool_args = tool_data.get("arguments")

        return f"Successfully dispatched tool: {state.current_tool_name}"