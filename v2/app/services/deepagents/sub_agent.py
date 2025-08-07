from abc import ABC, abstractmethod
from typing import List
from langchain_core.tools import BaseTool
from app.llm.llm_manager import LLMManager
from app.services.deepagents.state import DeepAgentState
from langchain_core.messages import HumanMessage

class SubAgent(ABC):
    def __init__(
        self,
        name: str,
        description: str,
        llm_manager: LLMManager,
        tools: List[BaseTool] = None,
        sub_agent_type: str = "base"
    ):
        self.name = name
        self.description = description
        self.llm_manager = llm_manager
        self.tools = tools or []
        self.sub_agent_type = sub_agent_type

    @abstractmethod
    def get_initial_prompt(self) -> str:
        """
        Returns the initial prompt for the sub-agent.
        """
        pass

    def as_runnable(self):
        """
        Returns a runnable that can be used in the graph.
        """
        return self

    def __call__(self, state: DeepAgentState):
        """
        The main entry point for the sub-agent.
        """
        # Add the initial prompt to the messages
        initial_prompt = self.get_initial_prompt()
        state["messages"].append(HumanMessage(content=initial_prompt))
        
        # Get the LLM
        llm = self.llm_manager.get_llm()

        # Invoke the LLM
        response = llm.invoke(state["messages"])

        # Update the state
        state["messages"].append(response)
        state["tool_calls"] = response.tool_calls
        state["current_agent"] = self.sub_agent_type

        return state