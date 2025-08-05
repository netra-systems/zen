import pytest
from unittest.mock import AsyncMock
from langchain_core.messages import HumanMessage, AIMessage, ToolCall
from langchain_core.runnables import RunnableLambda
from .deepagents.graph import create_deep_agent
from .deepagents.tools import update_todo

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

    # Wrap the llm mock in a RunnableLambda
    model = RunnableLambda(llm)

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
