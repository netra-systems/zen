from typing import TypedDict, Annotated, List, Union
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class Todo(TypedDict):
    id: str
    task: str
    status: str
    items: List[str]

class DeepAgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    todos: List[Todo]
    files: dict
    current_agent: str
