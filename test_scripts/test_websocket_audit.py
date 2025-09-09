"""WebSocket Bridge Audit Test - Verify Core Functionality"""

import asyncio
import sys
from pathlib import Path
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment
sys.path.append(str(Path(__file__).parent))

# Test 1: Verify run_id generation includes thread_id
def test_run_id_generation():
    """Verify run_id includes thread_id for proper event routing"""
    from netra_backend.app.orchestration.agent_execution_registry import extract_thread_id_from_run_id
    
    test_cases = [
        ("run_thread_123_abc456", "thread_123"),  # Standard format
        ("run_thread-456_def789", "thread-456"),   # With hyphen
        ("run_chat_789_ghi012", "chat_789"),       # Chat prefix
        ("run_abc123", None),                      # Legacy format (no thread)
        ("run_", None),                             # Invalid format
    ]
    
    print("\n=== TEST 1: Run ID Generation ===")
    all_passed = True
    for run_id, expected in test_cases:
        result = extract_thread_id_from_run_id(run_id)
        passed = result == expected
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"{status} {run_id} -> {result} (expected: {expected})")
    
    return all_passed


# Test 2: Verify WebSocketBridgeAdapter has all 5 critical events
def test_websocket_adapter_events():
    """Verify WebSocketBridgeAdapter implements all critical events"""
    from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
    
    critical_events = [
        "emit_agent_started",
        "emit_thinking",
        "emit_tool_executing",
        "emit_tool_completed", 
        "emit_agent_completed"
    ]
    
    print("\n=== TEST 2: WebSocketBridgeAdapter Events ===")
    adapter = WebSocketBridgeAdapter()
    all_present = True
    
    for event in critical_events:
        has_event = hasattr(adapter, event) and callable(getattr(adapter, event))
        all_present = all_present and has_event
        status = "PASS" if has_event else "FAIL"
        print(f"{status} {event}: {'Present' if has_event else 'MISSING'}")
    
    return all_present


# Test 3: Verify BaseAgent includes WebSocketBridgeAdapter
def test_base_agent_integration():
    """Verify BaseAgent properly integrates WebSocketBridgeAdapter"""
    from netra_backend.app.agents.base_agent import BaseAgent
    from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter
    
    print("\n=== TEST 3: BaseAgent Integration ===")
    
    # Create a test agent
    class TestAgent(BaseAgent):
        async def process(self, task_data):
            return {"result": "test"}
    
    agent = TestAgent("TestAgent")
    
    # Check for adapter
    has_adapter = hasattr(agent, '_websocket_adapter')
    adapter_type_correct = isinstance(getattr(agent, '_websocket_adapter', None), WebSocketBridgeAdapter)
    has_bridge_method = hasattr(agent, 'set_websocket_bridge')
    
    all_correct = has_adapter and adapter_type_correct and has_bridge_method
    
    print(f"{'PASS' if has_adapter else 'FAIL'} Has _websocket_adapter: {has_adapter}")
    print(f"{'PASS' if adapter_type_correct else 'FAIL'} Adapter is WebSocketBridgeAdapter: {adapter_type_correct}")
    print(f"{'PASS' if has_bridge_method else 'FAIL'} Has set_websocket_bridge method: {has_bridge_method}")
    
    return all_correct


# Test 4: Verify AgentExecutionCore sets websocket bridge
async def test_execution_core_bridge_setting():
    """Verify AgentExecutionCore properly sets WebSocket bridge on agents"""
    from netra_backend.app.agents.supervisor.agent_execution_core import AgentExecutionCore
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    from netra_backend.app.core.registry.universal_registry import AgentRegistry
    
    print("\n=== TEST 4: AgentExecutionCore Bridge Setting ===")
    
    try:
        # Create required dependencies
        bridge = AgentWebSocketBridge()
        registry = AgentRegistry()
        
        # Create execution core with registry
        core = AgentExecutionCore(registry=registry, websocket_bridge=bridge)
        
        # Check if core has bridge
        has_bridge = core.websocket_bridge is not None
        bridge_correct = core.websocket_bridge == bridge
        
        # Check if set_websocket_bridge method exists
        has_method = hasattr(core, 'set_websocket_bridge')
        
        all_correct = has_bridge and bridge_correct and has_method
        
        print(f"{'PASS' if has_bridge else 'FAIL'} Core has websocket_bridge: {has_bridge}")
        print(f"{'PASS' if bridge_correct else 'FAIL'} Bridge is correctly set: {bridge_correct}")
        print(f"{'PASS' if has_method else 'FAIL'} Has set_websocket_bridge method: {has_method}")
        
        return all_correct
        
    except Exception as e:
        print(f"FAIL Error: {e}")
        return False


# Test 5: Verify AgentWebSocketBridge singleton
def test_websocket_bridge_singleton():
    """Verify AgentWebSocketBridge uses singleton pattern"""
    from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
    
    print("\n=== TEST 5: AgentWebSocketBridge Singleton ===")
    
    bridge1 = AgentWebSocketBridge()
    bridge2 = AgentWebSocketBridge()
    
    is_singleton = bridge1 is bridge2
    
    print(f"{'PASS' if is_singleton else 'FAIL'} Singleton pattern: {is_singleton}")
    print(f"  Bridge1 ID: {id(bridge1)}")
    print(f"  Bridge2 ID: {id(bridge2)}")
    
    return is_singleton


# Main test runner
async def run_all_tests():
    """Run all audit tests"""
    print("=" * 50)
    print("WEBSOCKET BRIDGE AUDIT - CORE FUNCTIONALITY")
    print("=" * 50)
    
    results = []
    
    # Test 1: Run ID generation
    results.append(("Run ID Generation", test_run_id_generation()))
    
    # Test 2: WebSocket adapter events
    results.append(("WebSocket Adapter Events", test_websocket_adapter_events()))
    
    # Test 3: BaseAgent integration
    results.append(("BaseAgent Integration", test_base_agent_integration()))
    
    # Test 4: Execution core bridge setting
    result = await test_execution_core_bridge_setting()
    results.append(("Execution Core Bridge", result))
    
    # Test 5: Singleton pattern
    results.append(("WebSocket Bridge Singleton", test_websocket_bridge_singleton()))
    
    # Summary
    print("\n" + "=" * 50)
    print("AUDIT SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results:
        all_passed = all_passed and passed
        status = "PASS" if passed else "FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("ALL TESTS PASSED - WebSocket Bridge is FUNCTIONAL")
    else:
        print("SOME TESTS FAILED - Issues need to be fixed")
    print("=" * 50)
    
    return all_passed


if __name__ == "__main__":
    result = asyncio.run(run_all_tests())
    sys.exit(0 if result else 1)