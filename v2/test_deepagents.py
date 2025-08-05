import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolCall
from app.services.deepagents.graph import SingleAgentTeam
from app.services.deepagents.sub_agent import SubAgent
from app.services.deepagents.tool_dispatcher import ToolDispatcher
from app.llm.llm_manager import LLMManager

# Mock the update_todo tool
async def update_todo(todo_id: str, status: str):
    return f"Todo {todo_id} has been updated to {status}"

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
    agent_def = SubAgent(
        name="test_agent",
        description="A test agent",
        prompt="Complete the following tasks:",
        tools=[update_todo]
    )

    # Create a ToolDispatcher
    tool_dispatcher = ToolDispatcher(tools=[update_todo])

    # Create a SingleAgentTeam
    team = SingleAgentTeam(agent=agent_def, llm_manager=llm_manager, tool_dispatcher=tool_dispatcher)
    graph = team.create_graph()

    # Initial state with a todo list
    initial_state = {
        "messages": [HumanMessage(content="Write a short summary of the book 'The Hobbit'.")],
        "todo_list": ["Read the book", "Write the summary"],
        "completed_steps": []
    }

    # Run the agent
    final_state = None
    async for event in graph.astream(initial_state, {"recursion_limit": 100}):
        final_state = event

    # Assert that all todos are completed
    assert len(final_state["todo_list"]) == 0