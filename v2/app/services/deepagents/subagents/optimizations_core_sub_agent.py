from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.state import DeepAgentState
from langchain_core.messages import HumanMessage

class OptimizationsCoreSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "OptimizationsCoreSubAgent"

    @property
    def description(self) -> str:
        return "This agent analyzes data and formulates optimization strategies."

    async def ainvoke(self, state: DeepAgentState) -> DeepAgentState:
        print(f"-----Invoking OptimizationsCoreSubAgent-----")
        
        prompt = f"""
        You are the Optimizations Core Agent. Your role is to analyze the data provided and formulate optimization strategies.
        
        User Request: {state['analysis_request'].request.query}
        Previous Messages: {state['messages']}
        
        Based on the user's request and the data gathered, analyze the data and formulate optimization strategies. 
        Then, respond with a summary of the optimization strategies you have formulated, and indicate that the next step is to move to the ActionsToMeetGoalsSubAgent.
        """
        
        result = await self.llm_manager.arun(prompt, tools=self.tools)
        
        return {
            **state,
            "messages": state["messages"] + [HumanMessage(content=result.content)],
            "current_agent": "ActionsToMeetGoalsSubAgent",
        }
