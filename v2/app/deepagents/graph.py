from ..deepagents.sub_agent import _create_task_tool, SubAgent
from ..deepagents.model import get_default_model
from ..deepagents.tools import (
    write_todos,
    write_file,
    read_file,
    ls,
    edit_file,
    update_todo,
)
from ..deepagents.state import DeepAgentState
from typing import Sequence, Union, Callable, Any, TypeVar, Type, Optional
from langchain_core.tools import BaseTool
from langchain_core.language_models import LanguageModelLike

from langgraph.prebuilt import create_react_agent

StateSchema = TypeVar("StateSchema", bound=DeepAgentState)
StateSchemaType = Type[StateSchema]

base_prompt = """You have access to a number of standard tools to help you manage and plan your work.

## Todos

You can manage a todo list to track your progress.

### `write_todos`

Use the `write_todos` tool to add new tasks to your todo list. This is especially useful for breaking down large, complex tasks into smaller, more manageable steps.

### `update_todo`

Use the `update_todo` tool to update the status of a task in your todo list. The available statuses are "pending", "in_progress", and "completed".

It is critical that you follow this lifecycle for each task:

1.  When you start working on a task, mark it as "in_progress".
2.  When you have completed a task, mark it as "completed".

Do not batch up multiple tasks before marking them as completed.

## `task`

- When doing web search, prefer to use the `task` tool in order to reduce context usage."""


def create_deep_agent(
    tools: Sequence[Union[BaseTool, Callable, dict[str, Any]]],
    instructions: str,
    model: Optional[Union[str, LanguageModelLike]] = None,
    subagents: list[SubAgent] = None,
    state_schema: Optional[StateSchemaType] = None,
):
    """Create a deep agent.

    This agent will by default have access to a tool to write todos (write_todos),
    and then four file editing tools: write_file, ls, read_file, edit_file.

    Args:
        tools: The additional tools the agent should have access to.
        instructions: The additional instructions the agent should have. Will go in
            the system prompt.
        model: The model to use.
        subagents: The subagents to use. Each subagent should be a dictionary with the
            following keys:
                - `name`
                - `description` (used by the main agent to decide whether to call the sub agent)
                - `prompt` (used as the system prompt in the subagent)
                - (optional) `tools`
        state_schema: The schema of the deep agent. Should subclass from DeepAgentState
    """
    prompt = instructions + base_prompt
    built_in_tools = [write_todos, update_todo, write_file, read_file, ls, edit_file]
    if model is None:
        model = get_default_model()
    state_schema = state_schema or DeepAgentState
    task_tool = _create_task_tool(
        list(tools) + built_in_tools,
        instructions,
        subagents or [],
        model,
        state_schema
    )
    all_tools = built_in_tools + list(tools) + [task_tool]
    return create_react_agent(
        model,
        prompt=prompt,
        tools=all_tools,
        state_schema=state_schema,
    )
