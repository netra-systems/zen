from typing import Any, Dict, List
from langchain_core.messages import HumanMessage
from app.db.models_clickhouse import AnalysisRequest
from app.llm.llm_manager import LLMManager
from app.services.deepagents.graph import Team
from app.services.deepagents.sub_agent import SubAgent
from app.services.apex_optimizer_agent.tool_builder import ToolBuilder
from sqlalchemy.ext.asyncio import AsyncSession
import json

class NetraOptimizerAgentSupervisor:
    def __init__(self, db_session: AsyncSession, llm_manager: LLMManager):
        self.db_session = db_session
        self.llm_manager = llm_manager

        agent_def = self._get_agent_definition(llm_manager)

        team = Team(agents=[agent_def], llm_manager=llm_manager)
        self.graph = team.create_graph()

    def _get_agent_definition(self, llm_manager: LLMManager) -> SubAgent:
        """Returns the definition of the Netra Optimizer Agent."""
        all_tools, _ = ToolBuilder.build_all(self.db_session, llm_manager)
        
        return SubAgent(
            name="netra_optimizer_agent",
            description="An agent for optimizing LLM usage.",
            prompt=(
                "You are an expert in optimizing LLM usage. Your goal is to analyze the user's request "
                "and provide a set of recommendations for improving their LLM usage. Start by using the "
                "`triage_request` tool to understand the user's needs."
            ),
            tools=list(all_tools.values())
        )

    async def start_agent(self, request: AnalysisRequest) -> Dict[str, Any]:
        initial_state = {
            "messages": [HumanMessage(content=request.query)]
        }
        # The last message in the stream is the final state
        final_state = None
        async for event in self.graph.astream(initial_state, {"recursion_limit": 100}):
            final_state = event
        
        return final_state

async def triage_request(query: str, llm_manager: LLMManager) -> Dict[str, Any]:
    """
    Analyzes the user's request to determine the primary optimization goal
    (e.g., cost, latency, quality) and extracts key parameters and constraints.
    This initial analysis helps route the request to the appropriate
    specialist agent or tool.
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
        llm = llm_manager.get_llm("default")
        response = await llm.ainvoke(query, system_prompt=system_prompt)
        
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