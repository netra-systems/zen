#!/usr/bin/env python3
"""Debug script to understand agent isolation issue."""

import asyncio
from dataclasses import dataclass
from typing import Optional

# Mock the necessary imports
@dataclass
class UserExecutionContext:
    user_id: str
    thread_id: str = ""
    run_id: str = ""
    request_id: str = ""
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class BaseAgent:
    pass

@dataclass
class MockAgentForTesting(BaseAgent):
    """Test mock agent with dataclass decorator."""
    
    def __init__(self, name: str, user_context: UserExecutionContext, 
                 tool_dispatcher: Optional[object] = None,
                 websocket_bridge = None):
        self.name = name
        self.user_context = user_context
        self.tool_dispatcher = tool_dispatcher
        self.websocket_bridge = websocket_bridge
        self.execution_count = 0
        self.is_cleanup_called = False
        self._status = "initialized"

def test_agent_equality():
    """Test how agents compare for equality."""
    
    # Create contexts for two users
    user1_context = UserExecutionContext(
        user_id="user1",
        thread_id="thread_123",
        run_id="run_123",
        request_id="req_123",
        metadata={'custom_data': "user1_secret_data"}
    )
    
    user2_context = UserExecutionContext(
        user_id="user2",
        thread_id="thread_456",
        run_id="run_456",
        request_id="req_456",
        metadata={'custom_data': "user2_secret_data"}
    )
    
    # Create two agents with same name but different contexts
    agent1 = MockAgentForTesting("isolated_agent", user1_context)
    agent2 = MockAgentForTesting("isolated_agent", user2_context)
    
    print("Agent1 ID:", id(agent1))
    print("Agent2 ID:", id(agent2))
    print("Agents are same object:", agent1 is agent2)
    print("Agents are equal:", agent1 == agent2)
    
    # Test dictionary comparison
    dict1 = {"isolated_agent": agent1}
    dict2 = {"isolated_agent": agent2}
    
    print("Dict1:", dict1)
    print("Dict2:", dict2)
    print("Dicts are equal:", dict1 == dict2)
    print("Dicts are not equal:", dict1 != dict2)
    
    # Check user contexts
    print("User1 context:", agent1.user_context.user_id)
    print("User2 context:", agent2.user_context.user_id)
    print("Contexts are equal:", agent1.user_context == agent2.user_context)

if __name__ == "__main__":
    test_agent_equality()