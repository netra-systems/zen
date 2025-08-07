from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class ActionsToMeetGoalsSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="ActionsToMeetGoalsSubAgent",
            description="Formulates actionable recommendations and configurations.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="actions_to_meet_goals"
        )

    def get_initial_prompt(self):
        return (
            "You are the Actions to Meet Goals Sub-Agent. Your role is to take the analysis "
            "from the Optimizations Core Sub-Agent and formulate concrete, actionable "
            "recommendations. This may include generating configuration files, suggesting "
            "code changes, or providing a list of steps to be taken. Your output should be "
            "clear, concise, and easy to implement."
        )
