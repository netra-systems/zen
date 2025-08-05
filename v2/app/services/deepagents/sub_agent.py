from typing import Any, Callable, List, Optional, Sequence, Type, Union
from langchain_core.language_models import LanguageModelLike
from langchain_core.tools import BaseTool
from langgraph.prebuilt import create_react_agent
from .state import DeepAgentState

class SubAgent(dict):
    def __init__(self, name: str, description: str, prompt: str, tools: Optional[list] = None):
        self["name"] = name
        self["description"] = description
        self["prompt"] = prompt
        self["tools"] = tools or []

def create_agent(
    llm: LanguageModelLike,
    tools: list,
    system_message: str,
) -> Callable[[dict], dict]:
    """Create an agent."""
    return create_react_agent(llm, tools, messages_modifier=system_message)

def _create_task_tool(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    subagents: list,
    model: LanguageModelLike,
    state_schema: Type[DeepAgentState],
) -> BaseTool:
    """Create a tool to delegate tasks to sub-agents."""
    from langchain_core.tools import tool

    @tool("task", return_direct=True)
    def task_tool(input: str) -> str:
        """Delegate a task to a sub-agent."""
        # Create the sub-agent
        agent = create_agent(
            model,
            tools,
            instructions,
        )
        # Execute the sub-agent
        return agent.invoke({"messages": [("user", input)]})

    return task_tool