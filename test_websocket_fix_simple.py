"""
Simple WebSocket-Agent Integration Fix Validation Test
"""
import asyncio
import uuid
from unittest.mock import AsyncMock, Mock

# Test imports
from netra_backend.app.agents.supervisor.execution_engine import ExecutionEngine
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.services.user_execution_context import UserExecutionContext

class MockLLMManager:
    pass

class MockWebSocketManager:
    def __init__(self):
        self.events = []
        
    async def create_bridge(self, user_context):
        return MockAgentWebSocketBridge(self)

class MockAgentWebSocketBridge:
    def __init__(self, websocket_manager):
        self._websocket_manager = websocket_manager
        self.notifications = []
    
    async def notify_agent_started(self, run_id, agent_name, context):
        event = {'type': 'agent_started', 'run_id': run_id, 'agent_name': agent_name}
        self.notifications.append(event)
        self._websocket_manager.events.append(event)
        return True
        
    async def notify_agent_thinking(self, run_id, agent_name, reasoning, step_number=None, progress_percentage=None):
        event = {'type': 'agent_thinking', 'run_id': run_id, 'agent_name': agent_name}
        self.notifications.append(event)
        self._websocket_manager.events.append(event)
        return True
        
    async def notify_tool_executing(self, run_id, agent_name, tool_name, parameters=None):
        event = {'type': 'tool_executing', 'run_id': run_id, 'agent_name': agent_name}
        self.notifications.append(event)
        self._websocket_manager.events.append(event)
        return True
        
    async def notify_tool_completed(self, run_id, agent_name, tool_name, result=None, execution_time_ms=None):
        event = {'type': 'tool_completed', 'run_id': run_id, 'agent_name': agent_name}
        self.notifications.append(event)
        self._websocket_manager.events.append(event)
        return True
        
    async def notify_agent_completed(self, run_id, agent_name, result, execution_time_ms=None):
        event = {'type': 'agent_completed', 'run_id': run_id, 'agent_name': agent_name}
        self.notifications.append(event)
        self._websocket_manager.events.append(event)
        return True

async def test_websocket_integration():
    print("Starting WebSocket-Agent Integration Test...")
    
    # Setup
    mock_llm_manager = MockLLMManager()
    mock_websocket_manager = MockWebSocketManager()
    
    user_context = UserExecutionContext(
        user_id="test_user_123",
        request_id=str(uuid.uuid4()),
        thread_id="test_thread_123",
        run_id="test_run_123"
    )
    
    # Create agent registry with proper initialization
    registry = AgentRegistry(mock_llm_manager)
    await registry.initialize()  # Initialize the registry
    registry.set_websocket_manager(mock_websocket_manager)
    
    # Debug: Check if registry is properly created
    print(f"Registry created: {registry}")
    print(f"Registry type: {type(registry)}")
    print(f"Registry bool: {bool(registry)}")
    
    # Create WebSocket bridge
    websocket_bridge = await mock_websocket_manager.create_bridge(user_context)
    
    # TEST 1: ExecutionEngine can be created with direct instantiation (with proper parameters)
    try:
        execution_engine = ExecutionEngine(registry, websocket_bridge, user_context)
        print("SUCCESS: ExecutionEngine created with direct instantiation (proper validation working)")
    except RuntimeError as e:
        if "Direct ExecutionEngine instantiation is no longer supported" in str(e):
            print("FAILED: RuntimeError still blocking direct instantiation")
            return False
        else:
            raise e
    except ValueError as e:
        if "AgentRegistry is required" in str(e):
            print("VALIDATION WORKING: ExecutionEngine properly validates parameters")
            # Try with proper parameters
            execution_engine = ExecutionEngine(registry, websocket_bridge, user_context)
            print("SUCCESS: ExecutionEngine created with proper parameters")
        else:
            raise e
    
    # TEST 2: UserWebSocketEmitter is properly created
    user_emitter = await execution_engine._ensure_user_emitter(user_context)
    if user_emitter is not None:
        print("SUCCESS: UserWebSocketEmitter created")
    else:
        print("FAILED: UserWebSocketEmitter not created")
        return False
    
    # TEST 3: WebSocket events can be sent
    agent_context = AgentExecutionContext(
        agent_name="TestAgent",
        run_id=user_context.run_id,
        thread_id=user_context.thread_id,
        user_id=user_context.user_id
    )
    
    # Send test events
    await execution_engine.send_agent_thinking(agent_context, "Test thinking", 1)
    await execution_engine.send_tool_executing(agent_context, "test_tool")
    test_report = {"status": "completed"}
    await execution_engine.send_final_report(agent_context, test_report, 1000.0)
    
    # Validate events
    events = mock_websocket_manager.events
    event_types = [event['type'] for event in events]
    
    expected_events = ['agent_thinking', 'tool_executing', 'agent_completed']
    success = True
    
    for expected_event in expected_events:
        if expected_event in event_types:
            print(f"SUCCESS: {expected_event} event sent")
        else:
            print(f"FAILED: {expected_event} event missing")
            success = False
    
    print(f"\nTotal events captured: {len(events)}")
    print("Event types:", event_types)
    
    if success:
        print("\nOVERALL RESULT: SUCCESS!")
        print("- ExecutionEngine direct instantiation: FIXED")
        print("- Per-user WebSocket emitters: WORKING")
        print("- Critical WebSocket events: WORKING")
        return True
    else:
        print("\nOVERALL RESULT: FAILED")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_websocket_integration())
    print(f"\nTest result: {'PASSED' if result else 'FAILED'}")
    exit(0 if result else 1)