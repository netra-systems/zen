
from typing import Any, List
import pytest
from unittest.mock import AsyncMock, MagicMock
from langchain_core.messages import HumanMessage, AIMessage, ToolCall, BaseMessage
from .deepagents.graph import create_deep_agent
from .deepagents.tools import update_todo, write_todos
from .llm.llm_manager import LLMManager, LLMConfig
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.outputs import ChatGeneration, ChatResult

class MockChatModel(BaseChatModel):
    """A mock chat model for testing purposes."""
    side_effect: List[Any]
    call_count: int = 0

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.call_count < len(self.side_effect):
            result = self.side_effect[self.call_count]
            self.call_count += 1
            return ChatResult(generations=[ChatGeneration(message=result)])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="No more responses"))])

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if self.call_count < len(self.side_effect):
            result = self.side_effect[self.call_count]
            self.call_count += 1
            return ChatResult(generations=[ChatGeneration(message=result)])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="No more responses"))])

    def bind_tools(self, tools):
        return self # Return self to allow chaining

    @property
    def _llm_type(self) -> str:
        return "mock_chat_model"

@pytest.mark.asyncio
async def test_agent_completes_todos():
    # Mock the language model
    llm_side_effect = [
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

    mock_model = MockChatModel(side_effect=llm_side_effect)

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
        "next": "",
    }

    # Run the agent
    final_state = await agent.ainvoke(initial_state)

    # Assert that all todos are completed
    assert all(todo["status"] == "completed" for todo in final_state["todos"])

@pytest.mark.asyncio
async def test_agent_creates_and_completes_todos():
    # Mock the language model
    llm_side_effect = [
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

    mock_model = MockChatModel(side_effect=llm_side_effect)

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
        "next": "",
    }

    # Run the agent
    final_state = await agent.ainvoke(initial_state)

    # Assert that all todos are completed
    assert all(todo["status"] == "completed" for todo in final_state["todos"])
