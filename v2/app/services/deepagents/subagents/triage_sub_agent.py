from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.state import DeepAgentState
from langchain_core.messages import HumanMessage

class TriageSubAgent(SubAgent):
    @property
    def name(self) -> str:
        return "TriageSubAgent"

    @property
    def description(self) -> str:
        return "This agent triages the user's request and determines the next step."

    async def ainvoke(self, state: DeepAgentState) -> DeepAgentState:
        print(f"-----Invoking Triage Agent-----")
        
        prompt = f"""
        You are the Triage Agent. Your role is to analyze the user's request and determine the next step in the process.
        
        User Request: {state['analysis_request'].request.query}
        
        Based on the user's request, determine which of the following agents should be activated next:
        - DataSubAgent: If the request requires gathering or enriching data.
        - OptimizationsCoreSubAgent: If the request requires analyzing data and formulating optimization strategies.
        - ActionsToMeetGoalsSubAgent: If the request requires formulating tangible actions and changes to meet optimization goals.
        - ReportingSubAgent: If the request requires summarizing the overall results and reporting them to the user.
        
        Respond with the name of the next agent to activate. For example, if the next agent should be DataSubAgent, respond with "DataSubAgent".
        """
        
        result = await self.llm_manager.arun(prompt, tools=self.tools)
        
        # The result from the LLM should be the name of the next agent
        next_agent = result.content.strip()
        
        return {
            **state,
            "messages": [HumanMessage(content=result.content)],
            "current_agent": next_agent,
        }