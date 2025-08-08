from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.state import DeepAgentState
from langchain_core.messages import HumanMessage

class DataSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "DataSubAgent"

    @property
    def description(self) -> str:
        return "This agent gathers and enriches data for the optimization process."

    async def ainvoke(self, state: DeepAgentState) -> DeepAgentState:
        print(f"-----Invoking Data Agent-----")
        
        prompt = f"""
        You are the Data Agent. Your role is to gather and enrich data for the optimization process.
        
        User Request: {state['analysis_request'].request.query}
        Previous Messages: {state['messages']}
        
        Based on the user's request and the previous messages, gather and enrich the necessary data. 
        Then, respond with a summary of the data you have gathered and enriched, and indicate that the next step is to move to the OptimizationsCoreSubAgent.
        """
        
        result = await self.llm_manager.arun(prompt, tools=self.tools)
        
        return {
            **state,
            "messages": state["messages"] + [HumanMessage(content=result.content)],
            "current_agent": "OptimizationsCoreSubAgent",
        }
