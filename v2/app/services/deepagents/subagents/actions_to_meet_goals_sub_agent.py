from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class ActionsToMeetGoalsSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="actions_to_meet_goals",
            description="You are the actions agent. Your job is to formulate a plan of action based on the proposed optimizations.",
            llm_manager=llm_manager,
            tools=tools
        )
