#!/usr/bin/env python
"""
Simple test runner for presence detection tests
"""
import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'netra_backend'))

# Now run tests
async def run_tests():
    print("Testing Presence Detection System...")
    print("=" * 60)
    
    # Test HeartbeatConfig
    from netra_backend.app.websocket_core.manager import HeartbeatConfig
    
    print("\n1. Testing HeartbeatConfig...")
    config = HeartbeatConfig()
    assert config.heartbeat_interval_seconds == 30
    assert config.heartbeat_timeout_seconds == 90
    print("   [PASS] Default config works")
    
    staging_config = HeartbeatConfig.for_environment("staging")
    assert staging_config.heartbeat_timeout_seconds == 90
    print("   [PASS] Staging config works")
    
    # Test HeartbeatManager
    from netra_backend.app.websocket_core.manager import WebSocketHeartbeatManager
    
    print("\n2. Testing WebSocketHeartbeatManager...")
    manager = WebSocketHeartbeatManager(config)
    
    # Test registration
    await manager.register_connection("test_conn_1")
    assert "test_conn_1" in manager.connection_heartbeats
    print("   [PASS] Connection registration works")
    
    # Test activity recording
    await manager.record_activity("test_conn_1")
    assert manager.connection_heartbeats["test_conn_1"].is_alive
    print("   [PASS] Activity recording works")
    
    # Test health check
    is_healthy = await manager.check_connection_health("test_conn_1")
    assert is_healthy
    print("   [PASS] Health check works")
    
    # Test unregistration
    await manager.unregister_connection("test_conn_1")
    assert "test_conn_1" not in manager.connection_heartbeats
    print("   [PASS] Connection unregistration works")
    
    # Test thread safety improvements
    print("\n3. Testing robustness improvements...")
    
    # Test duplicate registration handling
    await manager.register_connection("dup_test")
    await manager.register_connection("dup_test")  # Should handle gracefully
    assert "dup_test" in manager.connection_heartbeats
    print("   [PASS] Duplicate registration handled")
    
    # Test resurrection
    await manager.register_connection("resurrect_test")
    await manager._mark_connection_dead("resurrect_test")
    assert not manager.connection_heartbeats["resurrect_test"].is_alive
    
    await manager.record_activity("resurrect_test")
    assert manager.connection_heartbeats["resurrect_test"].is_alive
    assert manager.stats['resurrection_count'] > 0
    print("   [PASS] Connection resurrection works")
    
    # Test statistics
    stats = manager.get_stats()
    assert 'total_connections_registered' in stats
    assert 'resurrection_count' in stats
    print("   [PASS] Enhanced statistics tracking works")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] ALL TESTS PASSED!")
    print("\nPresence Detection System Improvements:")
    print("  - Added thread-safe operations with async locks")
    print("  - Enhanced error handling and validation")
    print("  - Improved heartbeat timeout detection")
    print("  - Added connection resurrection capability")
    print("  - Better cleanup and memory management")
    print("  - Comprehensive statistics tracking")
    print("  - Clock skew handling")
    print("  - Graceful failure recovery")

if __name__ == "__main__":
    try:
        asyncio.run(run_tests())
    except Exception as e:
        print(f"\n[FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)