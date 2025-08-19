"""Debug script to test WebSocket agent registration and message flow"""

import asyncio
import json
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.logging_config import central_logger
from app.agents.supervisor_consolidated import SupervisorAgent
from app.llm.llm_manager import LLMManager
from app.agents.tool_dispatcher import ToolDispatcher
from app.ws_manager import manager as websocket_manager
from app.services.agent_service_core import AgentService
# config import not needed for this test

logger = central_logger.get_logger(__name__)

async def test_agent_registration():
    """Test if agents are properly registered during initialization"""
    print("\n=== Testing Agent Registration ===")
    
    # Create supervisor with components
    from app.schemas import AppConfig
    config = AppConfig()
    llm_manager = LLMManager(config)
    tool_dispatcher = ToolDispatcher({})
    
    supervisor = SupervisorAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    # Check if agents are registered
    registered_agents = supervisor.registry.list_agents()
    print(f"Registered agents: {registered_agents}")
    
    if not registered_agents:
        print("❌ No agents registered! This is the problem!")
        return False
    
    expected_agents = ["triage", "data", "optimization", "actions", "reporting"]
    for agent_name in expected_agents:
        agent = supervisor.registry.get(agent_name)
        if agent:
            print(f"✅ Agent '{agent_name}' registered: {type(agent).__name__}")
        else:
            print(f"❌ Agent '{agent_name}' NOT registered!")
            
    return len(registered_agents) > 0

async def test_message_flow():
    """Test the complete message flow from WebSocket to agent execution"""
    print("\n=== Testing Message Flow ===")
    
    # Create components
    from app.schemas import AppConfig
    config = AppConfig()
    llm_manager = LLMManager(config)
    tool_dispatcher = ToolDispatcher({})
    supervisor = SupervisorAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    # Create agent service
    agent_service = AgentService(supervisor)
    
    # Test message
    test_message = {
        "type": "user_message",
        "payload": {
            "content": "Test message - GPT-5 is too expensive, switch to claude 4.1?",
            "references": []
        }
    }
    
    print(f"Sending test message: {json.dumps(test_message, indent=2)}")
    
    try:
        # Process the message (without actual WebSocket connection)
        await agent_service.handle_websocket_message(
            user_id="test_user",
            message=json.dumps(test_message),
            db_session=None
        )
        print("✅ Message processed successfully")
        return True
    except Exception as e:
        print(f"❌ Error processing message: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_supervisor_run():
    """Test direct supervisor run to see if pipeline works"""
    print("\n=== Testing Direct Supervisor Run ===")
    
    # Create components
    from app.schemas import AppConfig
    config = AppConfig()
    llm_manager = LLMManager(config)
    tool_dispatcher = ToolDispatcher({})
    supervisor = SupervisorAgent(
        llm_manager=llm_manager,
        tool_dispatcher=tool_dispatcher,
        websocket_manager=websocket_manager
    )
    
    try:
        # Try to run supervisor directly
        result = await supervisor.run(
            user_request="Test: GPT-5 is too expensive, switch to claude 4.1?",
            thread_id="test_thread",
            user_id="test_user",
            run_id="test_run"
        )
        print(f"✅ Supervisor run completed: {result}")
        return True
    except Exception as e:
        print(f"❌ Error in supervisor run: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Run all tests"""
    print("=" * 60)
    print("WebSocket Agent Debug Script")
    print("=" * 60)
    
    # Test 1: Agent Registration
    registration_ok = await test_agent_registration()
    
    # Test 2: Message Flow
    message_flow_ok = await test_message_flow()
    
    # Test 3: Direct Supervisor Run
    supervisor_run_ok = await test_supervisor_run()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print(f"  Agent Registration: {'✅ PASS' if registration_ok else '❌ FAIL'}")
    print(f"  Message Flow: {'✅ PASS' if message_flow_ok else '❌ FAIL'}")
    print(f"  Supervisor Run: {'✅ PASS' if supervisor_run_ok else '❌ FAIL'}")
    print("=" * 60)
    
    if not (registration_ok and message_flow_ok and supervisor_run_ok):
        print("\n🔴 WebSocket regression confirmed!")
        print("   The issue is likely in agent registration or pipeline execution.")
    else:
        print("\n🟢 All tests passed - agents and pipeline working correctly.")

if __name__ == "__main__":
    asyncio.run(main())