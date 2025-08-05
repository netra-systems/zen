import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolCall
from langchain_core.runnables import Runnable
from app.deepagents.graph import create_deep_agent
from app.deepagents.tools import update_todo

class MockRunnable(Runnable):
    def __init__(self, llm):
        self.llm = llm

    async def ainvoke(self, *args, **kwargs):
        return await self.llm(*args, **kwargs)

    def invoke(self, *args, **kwargs):
        # Not used in this test, but required by the abstract class
        pass

    def bind_tools(self, *args, **kwargs):
        return self

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

    # Wrap the llm mock in a custom Runnable
    model = MockRunnable(llm)

    # Define a simple agent with a todo list
    agent = create_deep_agent(
        model=model,
        tools=[update_todo],
        instructions="Complete the following tasks:",
    )

    # Initial state with a todo list
    initial_state = {
        "messages": [HumanMessage(content="Write a short summary of the book 'The Hobbit'.")],
        "todos": [
            {"id": "1", "content": "Read the book", "status": "pending"},
            {"id": "2", "content": "Write the summary", "status": "pending"},
        ],
    }

    # Run the agent
    final_state = await agent.ainvoke(initial_state)

    # Assert that all todos are completed
    assert all(todo["status"] == "completed" for todo in final_state["todos"])
