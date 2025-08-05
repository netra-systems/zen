from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import NotRequired, Annotated, List, Optional
from typing import Literal
from typing_extensions import TypedDict


class Todo(TypedDict):
    """Todo to track."""

    id: str
    content: str
    status: Literal["pending", "in_progress", "completed"]


def file_reducer(l, r):
    if l is None:
        return r
    elif r is None:
        return l
    else:
        return {**l, **r}


class DeepAgentState(AgentState):
    todos: NotRequired[list[Todo]]
    files: Annotated[NotRequired[dict[str, str]], file_reducer]
    plan: NotRequired[List[str]]
    next: Optional[str] = None