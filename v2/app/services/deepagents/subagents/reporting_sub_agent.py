from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.sub_agent import SubAgent

class ReportingSubAgent(SubAgent):
    def __init__(self, llm_manager: LLMManager, tools: List[BaseTool] = None):
        super().__init__(
            name="ReportingSubAgent",
            description="Summarizes the overall results and reports to the user.",
            llm_manager=llm_manager,
            tools=tools,
            sub_agent_type="reporting"
        )

    def get_initial_prompt(self):
        return (
            "You are the Reporting Sub-Agent. Your role is to summarize the entire process, "
            "from the initial request to the final recommendations. You will create a clear "
            "and concise report that is easy for the user to understand. The report should "
            "highlight the key findings, the actions taken, and the expected outcomes."
        )
