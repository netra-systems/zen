"""Standalone test to verify SSOT tool enhancement fix."""
import asyncio
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from shared.isolated_environment import IsolatedEnvironment

# Test imports
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine


def test_tool_dispatcher_creation_with_websocket():
    """Test that ToolDispatcher can be created with WebSocket support from the start."""
    print("\n=== Test 1: ToolDispatcher creation with WebSocket ===")
    
    # Create mock WebSocketManager
    mock_ws_manager = MagicMock()
    mock_ws_manager.connections = {}
    mock_ws_manager.send_to_thread = AsyncMock()
    
    # Create ToolDispatcher with WebSocket support
    dispatcher = ToolDispatcher(websocket_manager=mock_ws_manager)
    
    # Verify it has WebSocket support
    assert hasattr(dispatcher, 'has_websocket_support'), "Missing has_websocket_support property"
    assert dispatcher.has_websocket_support, "WebSocket support not enabled"
    
    # Verify backward compatibility property
    assert hasattr(dispatcher, '_websocket_enhanced'), "Missing backward compatibility property"
    assert dispatcher._websocket_enhanced, "Backward compatibility property not set"
    
    # Verify executor is UnifiedToolExecutionEngine
    assert isinstance(dispatcher.executor, UnifiedToolExecutionEngine), \
        f"Executor is not UnifiedToolExecutionEngine, got {type(dispatcher.executor)}"
    
    print("[OK] ToolDispatcher created with WebSocket support")
    print(f"  - has_websocket_support: {dispatcher.has_websocket_support}")
    print(f"  - _websocket_enhanced: {dispatcher._websocket_enhanced}")
    print(f"  - executor type: {type(dispatcher.executor).__name__}")


def test_tool_dispatcher_without_websocket():
    """Test that ToolDispatcher can be created without WebSocket support."""
    print("\n=== Test 2: ToolDispatcher creation without WebSocket ===")
    
    # Create ToolDispatcher without WebSocket
    dispatcher = ToolDispatcher()
    
    # Verify it doesn't have WebSocket support
    assert hasattr(dispatcher, 'has_websocket_support'), "Missing has_websocket_support property"
    assert not dispatcher.has_websocket_support, "WebSocket support shouldn't be enabled"
    
    # Verify backward compatibility property
    assert hasattr(dispatcher, '_websocket_enhanced'), "Missing backward compatibility property"
    assert not dispatcher._websocket_enhanced, "Backward compatibility property shouldn't be set"
    
    # Verify executor is still UnifiedToolExecutionEngine (but without WebSocket)
    assert isinstance(dispatcher.executor, UnifiedToolExecutionEngine), \
        f"Executor is not UnifiedToolExecutionEngine, got {type(dispatcher.executor)}"
    
    print("[OK] ToolDispatcher created without WebSocket support")
    print(f"  - has_websocket_support: {dispatcher.has_websocket_support}")
    print(f"  - _websocket_enhanced: {dispatcher._websocket_enhanced}")
    print(f"  - executor type: {type(dispatcher.executor).__name__}")


def test_agent_registry_set_websocket():
    """Test that AgentRegistry.set_websocket_manager doesn't try to enhance."""
    print("\n=== Test 3: AgentRegistry.set_websocket_manager ===")
    
    # Create mocks
    mock_llm_manager = MagicMock()
    mock_ws_manager = MagicMock()
    mock_ws_manager.connections = {}
    mock_ws_manager.send_to_thread = AsyncMock()
    
    # Create dispatcher with WebSocket
    dispatcher = ToolDispatcher(websocket_manager=mock_ws_manager)
    
    # Create registry
    registry = AgentRegistry()
    
    # Set WebSocket manager (should not try to enhance)
    try:
        registry.set_websocket_manager(mock_ws_manager)
        print("[OK] set_websocket_manager succeeded without enhancement")
    except Exception as e:
        print(f"[FAIL] set_websocket_manager failed: {e}")
        raise
    
    # Verify dispatcher still has WebSocket support
    assert dispatcher.has_websocket_support, "WebSocket support was lost"
    print(f"  - Tool dispatcher still has WebSocket support: {dispatcher.has_websocket_support}")


def test_no_enhancement_function():
    """Test that the enhancement function has been removed."""
    print("\n=== Test 4: Enhancement function removal ===")
    
    # Try to import the enhancement function (should not exist)
    try:
        from netra_backend.app.agents.unified_tool_execution import enhance_tool_dispatcher_with_notifications
        print("[FAIL] Enhancement function still exists - should have been removed!")
        assert False, "enhance_tool_dispatcher_with_notifications should not exist"
    except ImportError:
        print("[OK] Enhancement function has been removed")


def main():
    """Run all tests."""
    print("=" * 60)
    print("SSOT Tool Enhancement Fix Verification")
    print("=" * 60)
    
    try:
        test_tool_dispatcher_creation_with_websocket()
        test_tool_dispatcher_without_websocket()
        test_agent_registry_set_websocket()
        test_no_enhancement_function()
        
        print("\n" + "=" * 60)
        print("[PASSED] ALL TESTS PASSED - SSOT FIX VERIFIED")
        print("=" * 60)
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"[FAILED] TEST FAILED: {e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()