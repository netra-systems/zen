
from typing import Any, Dict, List
from langchain_core.tools import tool
from app.llm.llm_manager import LLMManager
from app.services.apex_optimizer_agent.triage import Triage
from app.services.deepagents.graph import SubAgent


def create_netra_optimizer_agent_tools(llm_manager: LLMManager) -> List[Any]:
    """Creates the tools for the Netra Optimizer Agent."""
    triage = Triage(llm_manager)

    @tool
    async def triage_request(query: str) -> Dict[str, Any]:
        """
        Analyzes the user's request to determine the primary optimization goal
        (e.g., cost, latency, quality) and extracts key parameters and constraints.
        This initial analysis helps route the request to the appropriate
        specialist agent or tool.
        """
        return await triage.triage_request(query)

    return [triage_request]


def get_netra_optimizer_agent_definition() -> SubAgent:
    """Returns the definition of the Netra Optimizer Agent."""
    return {
        "name": "netra_optimizer_agent",
        "description": "An agent for optimizing LLM usage.",
        "prompt": (
            "You are an expert in optimizing LLM usage. Your goal is to analyze the user's request "
            "and provide a set of recommendations for improving their LLM usage. Start by using the "
            "`triage_request` tool to understand the user's needs."
        ),
    }
