
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolCall
from langchain_core.runnables import RunnableLambda
from .deepagents.graph import create_deep_agent
from .deepagents.tools import update_todo, write_todos
from .llm.llm_manager import LLMManager, LLMConfig
from langchain_core.language_models.chat_models import BaseChatModel

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

    # Create a mock that looks like a BaseChatModel
    mock_model = MagicMock(spec=BaseChatModel)
    mock_model.bind_tools.return_value = RunnableLambda(llm)

    # Create a mock LLMManager
    llm_manager = LLMManager({"default": LLMConfig(provider="google", model_name="gemini-1.5-flash-latest")})
    llm_manager._llm_cache["default"] = mock_model

    # Define a simple agent with a todo list
    agent = create_deep_agent(
        llm_manager=llm_manager,
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

@pytest.mark.asyncio
async def test_agent_creates_and_completes_todos():
    # Mock the language model
    llm = AsyncMock()
    llm.side_effect = [
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(
                    name="write_todos",
                    args={"todos": [{"id": "1", "content": "Test task", "status": "pending"}]},
                    id="1",
                )
            ],
        ),
        AIMessage(
            content="",
            tool_calls=[
                ToolCall(
                    name="update_todo",
                    args={"todo_id": "1", "status": "completed"},
                    id="2",
                )
            ],
        ),
        AIMessage(content="All tasks completed!"),
    ]

    # Create a mock that looks like a BaseChatModel
    mock_model = MagicMock(spec=BaseChatModel)
    mock_model.bind_tools.return_value = RunnableLambda(llm)

    # Create a mock LLMManager
    llm_manager = LLMManager({"default": LLMConfig(provider="google", model_name="gemini-1.5-flash-latest")})
    llm_manager._llm_cache["default"] = mock_model

    # Define a simple agent with a todo list
    agent = create_deep_agent(
        llm_manager=llm_manager,
        tools=[write_todos, update_todo],
        instructions="Create and complete a task.",
    )

    # Initial state without a todo list
    initial_state = {
        "messages": [HumanMessage(content="Create and complete a task.")],
    }

    # Run the agent
    final_state = await agent.ainvoke(initial_state)

    # Assert that all todos are completed
    assert all(todo["status"] == "completed" for todo in final_state["todos"])
