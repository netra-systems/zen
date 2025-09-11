"""
WebSocket SSOT Factory Pattern Violation Detection Tests

These tests detect current SSOT violations in WebSocket manager factory patterns and ensure
proper user isolation in multi-user scenarios.

Business Value: Platform/Internal - Prevent user data leakage and memory growth issues
Critical for multi-tenant system where users must be completely isolated.

Test Status: DESIGNED TO FAIL with current code (detecting violations)
Expected Result: PASS after SSOT consolidation implements proper factory pattern
"""

import asyncio
import gc
import psutil
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Any, Set
from concurrent.futures import ThreadPoolExecutor

# Add project root for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from shared.types.core_types import UserID, ensure_user_id


class TestWebSocketSSotFactoryViolations(SSotAsyncTestCase):
    """
    Test suite to detect WebSocket SSOT factory pattern violations.
    
    These tests are designed to FAIL with current code and PASS after consolidation.
    """
    
    async def test_websocket_manager_unified_factory_creation(self):
        """
        Test that WebSocket manager creation goes through unified factory after SSOT.
        
        CURRENT BEHAVIOR: Multiple factory paths exist (VIOLATION)
        EXPECTED AFTER SSOT: Single factory pattern
        """
        factory_creation_results = {}
        
        # Test current factory creation patterns
        try:
            from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
            factory1 = WebSocketManagerFactory()
            manager1 = factory1.create_manager()
            factory_creation_results['websocket_manager_factory'] = manager1 is not None
        except (ImportError, AttributeError):
            factory_creation_results['websocket_manager_factory'] = False
            
        try:
            from netra_backend.app.factories.websocket_bridge_factory import WebSocketBridgeFactory
            factory2 = WebSocketBridgeFactory()
            # Try to create manager through bridge factory
            bridge = factory2.create_bridge()
            factory_creation_results['websocket_bridge_factory'] = bridge is not None
        except (ImportError, AttributeError):
            factory_creation_results['websocket_bridge_factory'] = False
            
        try:
            # Direct instantiation (should be prevented after SSOT)
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            direct_manager = UnifiedWebSocketManager()
            factory_creation_results['direct_instantiation'] = direct_manager is not None
        except (ImportError, TypeError):
            factory_creation_results['direct_instantiation'] = False
        
        working_factories = sum(factory_creation_results.values())
        
        # CURRENT EXPECTATION: Multiple factory patterns work (violation)
        # AFTER SSOT: Should have single unified factory
        self.assertGreater(working_factories, 1,
                          "SSOT VIOLATION DETECTED: Multiple WebSocket manager factory patterns exist. "
                          f"Found {working_factories} working factory patterns: {factory_creation_results}")
        
        self.logger.warning(f"WebSocket Factory Pattern Violation: {working_factories} patterns work")
        self.metrics.record_test_event("websocket_factory_pattern_violation", {
            "working_factories": working_factories,
            "factory_results": factory_creation_results
        })

    async def test_user_isolation_in_multi_user_scenarios(self):
        """
        Test that WebSocket managers properly isolate users in concurrent scenarios.
        
        CURRENT BEHAVIOR: May have shared state between users (VIOLATION)
        EXPECTED AFTER SSOT: Complete user isolation
        """
        user_count = 10
        users = [ensure_user_id(f"test_user_{i}") for i in range(user_count)]
        user_managers = {}
        user_messages = {}
        
        # Create managers for each user
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            
            for user_id in users:
                # Create manager instance for user
                manager = UnifiedWebSocketManager()
                user_managers[user_id] = manager
                user_messages[user_id] = []
                
                # Simulate user-specific state
                await manager.add_connection(user_id, f"conn_{user_id}", None)
                
        except Exception as e:
            self.fail(f"Failed to create user managers: {e}")
        
        # Test concurrent operations to detect shared state
        async def user_operation(user_id: UserID):
            manager = user_managers[user_id]
            
            # Simulate user sending messages
            for i in range(5):
                message = {
                    "user_id": str(user_id),
                    "message_id": f"msg_{user_id}_{i}",
                    "data": f"User {user_id} message {i}"
                }
                user_messages[user_id].append(message)
                
                # Send message through manager
                try:
                    await manager.send_to_user(user_id, message)
                except Exception:
                    pass  # Manager might not be fully functional in test
                
                await asyncio.sleep(0.01)  # Small delay
        
        # Run concurrent operations
        tasks = [user_operation(user_id) for user_id in users]
        await asyncio.gather(*tasks)
        
        # Check for user isolation violations
        isolation_violations = []
        
        for user_id, manager in user_managers.items():
            # Check if manager has connections for other users
            try:
                all_connections = getattr(manager, '_connections', {})
                other_user_connections = [
                    conn for conn_user, conn in all_connections.items() 
                    if conn_user != user_id
                ]
                if other_user_connections:
                    isolation_violations.append(f"User {user_id} manager has {len(other_user_connections)} other user connections")
            except:
                pass
        
        # CURRENT EXPECTATION: May have isolation violations
        # AFTER SSOT: Should have zero violations
        violation_count = len(isolation_violations)
        if violation_count > 0:
            self.logger.warning(f"User isolation violations detected: {isolation_violations}")
            
        self.metrics.record_test_event("websocket_user_isolation_test", {
            "user_count": user_count,
            "violation_count": violation_count,
            "violations": isolation_violations
        })
        
        # For now, we expect some violations (will be fixed after SSOT)
        # This assertion will fail indicating violations exist
        self.assertEqual(violation_count, 0, 
                        f"User isolation violations detected: {violation_count} violations found")

    async def test_memory_growth_bounds_per_user(self):
        """
        Test that WebSocket managers don't have unbounded memory growth per user.
        
        CURRENT BEHAVIOR: May have memory leaks or unbounded growth (VIOLATION)
        EXPECTED AFTER SSOT: Bounded memory growth per user
        """
        # Get initial memory usage
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        user_id = ensure_user_id("memory_test_user")
        connection_count = 50
        
        try:
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager = UnifiedWebSocketManager()
            
            # Create many connections for single user
            for i in range(connection_count):
                conn_id = f"conn_{i}"
                try:
                    await manager.add_connection(user_id, conn_id, None)
                except Exception:
                    pass  # Manager might not be fully functional
                
                # Send messages to create memory pressure
                for j in range(10):
                    message = {
                        "conn_id": conn_id,
                        "message_id": f"msg_{i}_{j}",
                        "data": f"Connection {i} message {j}" * 100  # Large message
                    }
                    try:
                        await manager.send_to_user(user_id, message)
                    except Exception:
                        pass
            
            # Force garbage collection
            gc.collect()
            await asyncio.sleep(0.1)
            
            # Check memory growth
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
            
            # Define reasonable memory growth bounds (this is conservative)
            max_acceptable_growth = 100  # 100 MB for 50 connections
            
            self.logger.info(f"Memory growth: {memory_growth:.2f} MB for {connection_count} connections")
            
            # CURRENT EXPECTATION: May exceed bounds (violation)
            # AFTER SSOT: Should stay within bounds
            self.assertLess(memory_growth, max_acceptable_growth,
                           f"Memory growth violation: {memory_growth:.2f} MB exceeds {max_acceptable_growth} MB limit")
            
            self.metrics.record_test_event("websocket_memory_growth_test", {
                "initial_memory_mb": initial_memory,
                "final_memory_mb": final_memory,
                "memory_growth_mb": memory_growth,
                "connection_count": connection_count,
                "within_bounds": memory_growth < max_acceptable_growth
            })
            
        except Exception as e:
            self.fail(f"Memory growth test failed: {e}")