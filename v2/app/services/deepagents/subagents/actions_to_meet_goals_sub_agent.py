from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.state import DeepAgentState
from langchain_core.messages import HumanMessage

class ActionsToMeetGoalsSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "ActionsToMeetGoalsSubAgent"

    @property
    def description(self) -> str:
        return "This agent formulates tangible actions and changes to meet optimization goals."

    async def ainvoke(self, state: DeepAgentState) -> DeepAgentState:
        print(f"-----Invoking ActionsToMeetGoalsSubAgent-----")
        
        prompt = f"""
        You are the Actions To Meet Goals Agent. Your role is to formulate tangible actions and changes to meet the optimization goals.
        
        User Request: {state['analysis_request'].request.query}
        Previous Messages: {state['messages']}
        
        Based on the user's request and the optimization strategies formulated, formulate tangible actions and changes to meet the optimization goals. 
        Then, respond with a summary of the actions and changes you have formulated, and indicate that the next step is to move to the ReportingSubAgent.
        """
        
        result = await self.llm_manager.arun(prompt, tools=self.tools)
        
        return {
            **state,
            "messages": state["messages"] + [HumanMessage(content=result.content)],
            "current_agent": "ReportingSubAgent",
        }
