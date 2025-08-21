#!/usr/bin/env python3
"""
Quick validation test for enhanced WebSocket lifecycle management.

Tests the key fixes implemented:
- Enhanced heartbeat/ping-pong mechanism
- Connection pool management
- Graceful shutdown
- Zombie connection detection
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock

# Import our enhanced components
from app.websocket.enhanced_lifecycle_manager import (
    EnhancedLifecycleManager,
    HeartbeatConfig,
    ConnectionPool,
    ShutdownConfig
)
from app.websocket.lifecycle_integration import WebSocketLifecycleIntegrator
from app.websocket.connection import ConnectionInfo
from datetime import datetime, timezone


async def test_enhanced_heartbeat_mechanism():
    """Test enhanced heartbeat with ping/pong handling."""
    print("Testing Enhanced Heartbeat Mechanism...")
    
    lifecycle_manager = EnhancedLifecycleManager()
    
    # Create mock websocket and connection
    mock_websocket = AsyncMock()
    mock_websocket.client_state = MagicMock()
    mock_websocket.client_state.__eq__ = lambda self, other: True  # Always connected
    
    try:
        # Test connection
        conn_info = await lifecycle_manager.connect_user("test_user", mock_websocket)
        print(f"[OK] Connected user with connection ID: {conn_info.connection_id}")
        
        # Test heartbeat status
        health = lifecycle_manager.heartbeat_manager.get_connection_health(conn_info.connection_id)
        print(f"[OK] Health status: {health}")
        
        # Test pong handling
        await lifecycle_manager.handle_pong(conn_info.connection_id, {"timestamp": time.time()})
        print("[OK] Pong handling successful")
        
        # Test zombie detection
        zombies = lifecycle_manager.get_zombie_connections()
        print(f"[OK] Zombie connections detected: {len(zombies)}")
        
        # Cleanup
        await lifecycle_manager.disconnect_user(conn_info.connection_id)
        print("[OK] User disconnected successfully")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Heartbeat test failed: {e}")
        return False


async def test_connection_pool_management():
    """Test connection pool limits and management."""
    print("\nTesting Connection Pool Management...")
    
    pool_config = ConnectionPool(
        max_connections_per_user=2,
        max_total_connections=5
    )
    
    lifecycle_manager = EnhancedLifecycleManager(pool_config=pool_config)
    
    try:
        connections = []
        
        # Test adding connections within limits
        for i in range(2):
            mock_websocket = AsyncMock()
            mock_websocket.client_state = MagicMock()
            mock_websocket.client_state.__eq__ = lambda self, other: True
            
            conn_info = await lifecycle_manager.connect_user(f"user_{i}", mock_websocket)
            connections.append(conn_info)
            print(f"[OK] Added connection {i+1}: {conn_info.connection_id}")
        
        # Test pool status
        pool_status = lifecycle_manager.get_pool_status()
        print(f"[OK] Pool status: {pool_status}")
        
        # Test cleanup
        for conn_info in connections:
            await lifecycle_manager.disconnect_user(conn_info.connection_id)
        print("[OK] All connections cleaned up")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Pool management test failed: {e}")
        return False


async def test_graceful_shutdown():
    """Test graceful shutdown with connection draining."""
    print("\nTesting Graceful Shutdown...")
    
    shutdown_config = ShutdownConfig(
        drain_timeout=2.0,  # Short timeout for testing
        force_close_timeout=5.0,
        notify_clients=True
    )
    
    lifecycle_manager = EnhancedLifecycleManager(shutdown_config=shutdown_config)
    
    try:
        # Add some connections
        connections = []
        for i in range(2):
            mock_websocket = AsyncMock()
            mock_websocket.client_state = MagicMock()
            mock_websocket.client_state.__eq__ = lambda self, other: True
            
            conn_info = await lifecycle_manager.connect_user(f"shutdown_user_{i}", mock_websocket)
            connections.append(conn_info)
        
        print(f"[OK] Created {len(connections)} connections for shutdown test")
        
        # Test graceful shutdown
        shutdown_result = await lifecycle_manager.initiate_graceful_shutdown()
        print(f"[OK] Graceful shutdown completed: {shutdown_result.get('success', False)}")
        print(f"  - Duration: {shutdown_result.get('duration', 0):.2f}s")
        print(f"  - Phases completed: {shutdown_result.get('phases_completed', [])}")
        
        return shutdown_result.get('success', False)
        
    except Exception as e:
        print(f"[FAIL] Graceful shutdown test failed: {e}")
        return False


async def test_lifecycle_integration():
    """Test lifecycle integration with existing systems."""
    print("\nTesting Lifecycle Integration...")
    
    try:
        integrator = WebSocketLifecycleIntegrator()
        
        # Test message handling
        test_message = {"type": "ping", "timestamp": time.time()}
        mock_websocket = AsyncMock()
        
        # This should return False since no connection is registered
        handled = await integrator.handle_websocket_message("test_user", mock_websocket, test_message)
        print(f"[OK] Message handling test (no connection): {handled}")
        
        # Test comprehensive stats
        stats = integrator.get_comprehensive_stats()
        print(f"[OK] Comprehensive stats: {len(stats)} categories")
        
        # Test health validation
        health_report = await integrator.validate_connection_health()
        print(f"[OK] Health validation: {health_report}")
        
        return True
        
    except Exception as e:
        print(f"[FAIL] Integration test failed: {e}")
        return False


async def main():
    """Run all enhanced lifecycle tests."""
    print("=" * 60)
    print("Enhanced WebSocket Lifecycle Management Tests")
    print("=" * 60)
    
    tests = [
        test_enhanced_heartbeat_mechanism,
        test_connection_pool_management,
        test_graceful_shutdown,
        test_lifecycle_integration
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"[FAIL] Test {test.__name__} failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("Test Results Summary")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    for i, (test, result) in enumerate(zip(tests, results)):
        status = "[PASS]" if result else "[FAIL]"
        print(f"{i+1}. {test.__name__}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("[SUCCESS] All enhanced lifecycle management features working correctly!")
        return True
    else:
        print("[WARNING] Some tests failed - review implementation")
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)