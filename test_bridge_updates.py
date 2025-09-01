"""
Simple test script to verify AgentWebSocketBridge updates
"""
import asyncio
import sys
from unittest.mock import AsyncMock, Mock, patch

# Add path for imports
sys.path.insert(0, 'netra_backend')

from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
)

async def test_notification_interface():
    """Test the new notification interface methods."""
    print("Testing AgentWebSocketBridge notification interface...")
    
    # Reset singleton
    AgentWebSocketBridge._instance = None
    bridge = AgentWebSocketBridge()
    
    with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_manager, \
         patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry') as mock_get_registry:
        
        # Setup mocks
        websocket_manager = AsyncMock()
        websocket_manager.send_to_thread = AsyncMock(return_value=True)
        mock_get_manager.return_value = websocket_manager
        
        registry = AsyncMock()
        registry.get_metrics = AsyncMock(return_value={"active_contexts": 0})
        registry.get_thread_id_for_run = AsyncMock(return_value="test_thread")
        mock_get_registry.return_value = registry
        
        # Initialize bridge
        result = await bridge.ensure_integration()
        assert result.success, "Bridge initialization failed"
        print("[SUCCESS] Bridge initialized successfully")
        
        # Test notify_agent_started
        success = await bridge.notify_agent_started(
            run_id="test_run",
            agent_name="test_agent",
            context={"user_query": "test query"}
        )
        assert success, "notify_agent_started failed"
        websocket_manager.send_to_thread.assert_called()
        print("[SUCCESS] notify_agent_started works")
        
        # Test notify_agent_thinking
        success = await bridge.notify_agent_thinking(
            run_id="test_run",
            agent_name="reasoning_agent",
            reasoning="Analyzing request",
            step_number=1,
            progress_percentage=25.0
        )
        assert success, "notify_agent_thinking failed"
        print("[SUCCESS] notify_agent_thinking works")
        
        # Test notify_tool_executing
        success = await bridge.notify_tool_executing(
            run_id="test_run",
            agent_name="data_agent",
            tool_name="database_query",
            parameters={"query": "SELECT * FROM users"}
        )
        assert success, "notify_tool_executing failed"
        print("[SUCCESS] notify_tool_executing works")
        
        # Test notify_tool_completed
        success = await bridge.notify_tool_completed(
            run_id="test_run",
            agent_name="data_agent",
            tool_name="database_query",
            result={"row_count": 42},
            execution_time_ms=123.4
        )
        assert success, "notify_tool_completed failed"
        print("[SUCCESS] notify_tool_completed works")
        
        # Test notify_agent_completed
        success = await bridge.notify_agent_completed(
            run_id="test_run",
            agent_name="analysis_agent",
            result={"insights": "Analysis complete"},
            execution_time_ms=5432.1
        )
        assert success, "notify_agent_completed failed"
        print("[SUCCESS] notify_agent_completed works")
        
        # Test notify_agent_error
        success = await bridge.notify_agent_error(
            run_id="test_run",
            agent_name="failing_agent",
            error="Test error",
            error_context={"error_type": "TestError"}
        )
        assert success, "notify_agent_error failed"
        print("[SUCCESS] notify_agent_error works")
        
        # Test notify_progress_update
        success = await bridge.notify_progress_update(
            run_id="test_run",
            agent_name="long_running_agent",
            progress={"percentage": 50.0, "message": "Half way done"}
        )
        assert success, "notify_progress_update failed"
        print("[SUCCESS] notify_progress_update works")
        
        # Test notify_custom
        success = await bridge.notify_custom(
            run_id="test_run",
            agent_name="custom_agent",
            notification_type="custom_event",
            data={"custom": "data"}
        )
        assert success, "notify_custom failed"
        print("[SUCCESS] notify_custom works")
        
        # Test parameter sanitization
        success = await bridge.notify_tool_executing(
            run_id="test_run",
            agent_name="secure_agent",
            tool_name="api_call",
            parameters={
                "api_key": "sk-secret123",
                "password": "pass123",
                "username": "john"
            }
        )
        assert success, "Sanitization test failed"
        
        # Verify sanitization worked
        call_args = websocket_manager.send_to_thread.call_args[0]
        notification = call_args[1]
        params = notification["payload"]["parameters"]
        assert params["api_key"] == "[REDACTED]", "API key not redacted"
        assert params["password"] == "[REDACTED]", "Password not redacted"
        assert params["username"] == "john", "Username should not be redacted"
        print("[SUCCESS] Parameter sanitization works")
        
        # Test thread_id resolution fallbacks
        registry.get_thread_id_for_run.return_value = None
        websocket_manager.send_to_thread.reset_mock()
        
        # Test with thread_id in run_id
        success = await bridge.notify_agent_started("thread_456_run_789", "test_agent")
        assert success, "Thread resolution from run_id failed"
        assert websocket_manager.send_to_thread.call_args[0][0] == "thread_456"
        print("[SUCCESS] Thread ID resolution from run_id works")
        
        # Test with run_id that is already a thread_id
        websocket_manager.send_to_thread.reset_mock()
        success = await bridge.notify_agent_started("thread_999", "test_agent")
        assert success, "Thread resolution for thread_id failed"
        assert websocket_manager.send_to_thread.call_args[0][0] == "thread_999"
        print("[SUCCESS] Thread ID resolution for direct thread_id works")
        
        # Test graceful handling without WebSocket manager
        bridge._websocket_manager = None
        success = await bridge.notify_agent_started("run_1", "agent")
        assert not success, "Should return False without WebSocket manager"
        print("[SUCCESS] Graceful handling without WebSocket manager works")
        
        # Cleanup
        await bridge.shutdown()
        print("[SUCCESS] Bridge shutdown complete")
    
    print("\n[SUCCESS] All notification interface tests passed!")

async def test_monitorable_component():
    """Test MonitorableComponent interface implementation."""
    print("\nTesting MonitorableComponent interface...")
    
    # Reset singleton
    AgentWebSocketBridge._instance = None
    bridge = AgentWebSocketBridge()
    
    # Test get_health_status
    health_status = await bridge.get_health_status()
    assert isinstance(health_status, dict), "get_health_status should return dict"
    assert "healthy" in health_status, "Health status missing 'healthy' key"
    assert "state" in health_status, "Health status missing 'state' key"
    assert "timestamp" in health_status, "Health status missing 'timestamp' key"
    print("[SUCCESS] get_health_status works")
    
    # Test get_metrics
    metrics = await bridge.get_metrics()
    assert isinstance(metrics, dict), "get_metrics should return dict"
    assert "total_initializations" in metrics, "Metrics missing 'total_initializations'"
    assert "successful_initializations" in metrics, "Metrics missing 'successful_initializations'"
    assert "registered_observers" in metrics, "Metrics missing 'registered_observers'"
    print("[SUCCESS] get_metrics works")
    
    # Test observer registration
    mock_observer = AsyncMock()
    mock_observer.__class__.__name__ = "MockObserver"
    mock_observer.on_component_health_change = AsyncMock()
    
    initial_count = metrics["registered_observers"]
    bridge.register_monitor_observer(mock_observer)
    
    metrics = await bridge.get_metrics()
    assert metrics["registered_observers"] == initial_count + 1, "Observer not registered"
    print("[SUCCESS] Observer registration works")
    
    # Test observer removal
    bridge.remove_monitor_observer(mock_observer)
    metrics = await bridge.get_metrics()
    assert metrics["registered_observers"] == initial_count, "Observer not removed"
    print("[SUCCESS] Observer removal works")
    
    # Cleanup
    await bridge.shutdown()
    print("[SUCCESS] MonitorableComponent tests passed!")

async def main():
    """Run all tests."""
    print("="*50)
    print("AgentWebSocketBridge Update Tests")
    print("="*50)
    
    await test_notification_interface()
    await test_monitorable_component()
    
    print("\n" + "="*50)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())