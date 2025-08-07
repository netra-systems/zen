import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from app.services.deepagents.sub_agent import SubAgent
from app.llm.llm_manager import LLMManager
from langchain_core.messages import AIMessage, ToolCall

def update_todo(todo_id: str, status: str):
    """Updates a todo item."""
    return f"Todo {todo_id} updated to {status}"

class ConcreteSubAgent(SubAgent):
    def get_initial_prompt(self):
        return "Initial prompt"

@pytest.mark.asyncio
async def test_agent_completes_todos():
    # Mock the language model
    llm = AsyncMock()
    llm.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(
                    name="update_todo",
                    args={"todo_id": "1", "status": "completed"},
                    id="1",
                )
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(
                    name="update_todo",
                    args={"todo_id": "2", "status": "completed"},
                    id="2",
                )
            ],
        ),
        AIMessage(content="All tasks completed!"),
    ]

    # Mock the LLMManager
    llm_manager = MagicMock(spec=LLMManager)
    llm_manager.get_llm.return_value = llm

    # Define a simple agent with a todo list
    agent_def = ConcreteSubAgent(
        name="test_agent",
        description="A test agent",
        prompt="Complete the following tasks:",
        tools=[update_todo]
    )

    # ... rest of the test
