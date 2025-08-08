from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.state import DeepAgentState
from langchain_core.messages import HumanMessage

class ReportingSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "ReportingSubAgent"

    @property
    def description(self) -> str:
        return "This agent summarizes the overall results and reports them to the user."

    async def ainvoke(self, state: DeepAgentState) -> DeepAgentState:
        print(f"-----Invoking ReportingSubAgent-----")
        
        prompt = f"""
        You are the Reporting Agent. Your role is to summarize the overall results and report them to the user.
        
        User Request: {state['analysis_request'].request.query}
        Previous Messages: {state['messages']}
        
        Based on the user's request and the actions and changes formulated, summarize the overall results and report them to the user. 
        Then, respond with a final summary of the results.
        """
        
        result = await self.llm_manager.arun(prompt, tools=self.tools)
        
        return {
            **state,
            "messages": state["messages"] + [HumanMessage(content=result.content)],
            "current_agent": "__end__",
        }