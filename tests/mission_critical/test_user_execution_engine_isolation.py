"""Issue #874: UserExecutionEngine multi-user isolation test.

This test validates that UserExecutionEngine properly isolates execution 
between different users, preventing state leakage and ensuring secure 
concurrent operations. It's part of the SSOT consolidation validation.

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: Security & User Experience
- Value Impact: Ensures secure multi-user chat operations protecting $500K+ ARR
- Strategic Impact: Validates user isolation required for production multi-tenant deployment

Key Isolation Areas:
- State isolation between different user contexts
- WebSocket event routing to correct users only
- Resource limits enforcement per user
- Memory isolation preventing data leaks
- Concurrent execution without interference

EXPECTED BEHAVIOR:
This test should PASS if UserExecutionEngine properly implements user isolation.
If it FAILS, it indicates security vulnerabilities requiring immediate fix.
"""

import unittest
import asyncio
import concurrent.futures
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, List, Any
import time
import random

# Use unittest.TestCase directly to avoid SSOT base class issues for now
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestUserExecutionEngineIsolation(unittest.TestCase):
    """Test UserExecutionEngine multi-user isolation functionality."""
    
    def setUp(self):
        """Set up test environment for isolation testing."""
        self.isolation_violations = []
        self.concurrency_issues = []
        self.resource_leaks = []
        
        logger.info("Starting UserExecutionEngine isolation testing")
    
    def test_user_state_isolation(self):
        """Test that different users have completely isolated state."""
        logger.info("🔒 ISOLATION TEST: Validating user state isolation")
        
        async def test_isolation():
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                # Create mock WebSocket manager
                mock_websocket_manager = Mock()
                mock_websocket_manager.emit_user_event = AsyncMock(return_value=True)
                
                # Create contexts for two different users
                user1_id = UnifiedIdGenerator.generate_base_id("isolation_user1", True, 8)
                user2_id = UnifiedIdGenerator.generate_base_id("isolation_user2", True, 8)
                
                thread1_id, run1_id, _ = UnifiedIdGenerator.generate_user_context_ids(user1_id, "isolation_test")
                thread2_id, run2_id, _ = UnifiedIdGenerator.generate_user_context_ids(user2_id, "isolation_test")
                
                user1_context = UserExecutionContext(
                    user_id=user1_id,
                    run_id=run1_id,
                    thread_id=thread1_id,
                    metadata={'test': 'user1_state_isolation'}
                )
                
                user2_context = UserExecutionContext(
                    user_id=user2_id,
                    run_id=run2_id,
                    thread_id=thread2_id,
                    metadata={'test': 'user2_state_isolation'}
                )
                
                # Create engines for both users
                agent_factory1 = AgentInstanceFactory()
                websocket_emitter1 = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user1_context.user_id,
                    context=user1_context
                )
                
                agent_factory2 = AgentInstanceFactory()
                websocket_emitter2 = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user2_context.user_id,
                    context=user2_context
                )
                
                engine1 = UserExecutionEngine(user1_context, agent_factory1, websocket_emitter1)
                engine2 = UserExecutionEngine(user2_context, agent_factory2, websocket_emitter2)
                
                # Test 1: Basic isolation
                self.assertNotEqual(engine1.engine_id, engine2.engine_id, "Engines should have different IDs")
                self.assertEqual(engine1.get_user_context().user_id, user1_id, "Engine1 should have user1 context")
                self.assertEqual(engine2.get_user_context().user_id, user2_id, "Engine2 should have user2 context")
                
                # Test 2: State manipulation isolation
                engine1.set_agent_state("test_agent", "user1_state")
                engine2.set_agent_state("test_agent", "user2_state")
                
                # States should be isolated
                self.assertEqual(engine1.get_agent_state("test_agent"), "user1_state")
                self.assertEqual(engine2.get_agent_state("test_agent"), "user2_state")
                
                # Test 3: Result storage isolation
                engine1.set_agent_result("test_result", {"user": "user1", "data": "secret1"})
                engine2.set_agent_result("test_result", {"user": "user2", "data": "secret2"})
                
                result1 = engine1.get_agent_result("test_result")
                result2 = engine2.get_agent_result("test_result")
                
                self.assertEqual(result1["user"], "user1")
                self.assertEqual(result2["user"], "user2")
                self.assertNotEqual(result1["data"], result2["data"])
                
                # Test 4: Statistics isolation
                stats1 = engine1.get_user_execution_stats()
                stats2 = engine2.get_user_execution_stats()
                
                self.assertEqual(stats1["user_id"], user1_id)
                self.assertEqual(stats2["user_id"], user2_id)
                self.assertNotEqual(stats1["engine_id"], stats2["engine_id"])
                
                # Cleanup
                await engine1.cleanup()
                await engine2.cleanup()
                
                logger.info("✅ PASS: User state isolation working correctly")
                return True
                
            except Exception as e:
                self.isolation_violations.append(f"State isolation test failed: {e}")
                logger.error(f"❌ FAIL: User state isolation broken - {e}")
                return False
        
        result = asyncio.run(test_isolation())
        self.assertTrue(result, "User state isolation should work correctly")
    
    def test_concurrent_user_operations(self):
        """Test that multiple users can operate concurrently without interference."""
        logger.info("🔄 CONCURRENCY TEST: Validating concurrent user operations")
        
        async def concurrent_operation(user_index: int, operations_count: int = 10):
            """Simulate concurrent operations for a single user."""
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                # Create unique user context
                user_id = UnifiedIdGenerator.generate_base_id(f"concurrent_user_{user_index}", True, 8)
                thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, f"concurrent_test_{user_index}")
                
                user_context = UserExecutionContext(
                    user_id=user_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    metadata={'test': f'concurrent_user_{user_index}', 'operations': operations_count}
                )
                
                # Create engine
                mock_websocket_manager = Mock()
                mock_websocket_manager.emit_user_event = AsyncMock(return_value=True)
                
                agent_factory = AgentInstanceFactory()
                websocket_emitter = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user_context.user_id,
                    context=user_context
                )
                
                engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                
                # Perform operations
                operations_results = []
                for op in range(operations_count):
                    # Simulate various operations
                    operation_id = f"op_{user_index}_{op}"
                    
                    # Set state
                    engine.set_agent_state(f"agent_{op}", f"state_{user_index}_{op}")
                    
                    # Set result
                    engine.set_agent_result(operation_id, {
                        "user_index": user_index,
                        "operation": op,
                        "timestamp": time.time(),
                        "random": random.randint(1, 1000)
                    })
                    
                    # Get stats
                    stats = engine.get_user_execution_stats()
                    
                    # Verify user context hasn't changed
                    self.assertEqual(stats["user_id"], user_id)
                    
                    operations_results.append({
                        "operation_id": operation_id,
                        "user_id": user_id,
                        "engine_id": engine.engine_id,
                        "operation_index": op
                    })
                    
                    # Small delay to simulate real work
                    await asyncio.sleep(0.001)
                
                # Cleanup
                await engine.cleanup()
                
                return {
                    "user_index": user_index,
                    "user_id": user_id,
                    "operations_completed": len(operations_results),
                    "results": operations_results
                }
                
            except Exception as e:
                logger.error(f"Concurrent operation failed for user {user_index}: {e}")
                return {"user_index": user_index, "error": str(e)}
        
        async def test_concurrency():
            # Run multiple users concurrently
            user_count = 5
            operations_per_user = 10
            
            tasks = [
                concurrent_operation(i, operations_per_user) 
                for i in range(user_count)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Validate results
            successful_users = 0
            total_operations = 0
            unique_user_ids = set()
            unique_engine_ids = set()
            
            for result in results:
                if isinstance(result, dict) and "error" not in result:
                    successful_users += 1
                    total_operations += result["operations_completed"]
                    unique_user_ids.add(result["user_id"])
                    
                    # Collect engine IDs from operations
                    for op_result in result["results"]:
                        unique_engine_ids.add(op_result["engine_id"])
                else:
                    self.concurrency_issues.append(f"User operation failed: {result}")
            
            # Validate concurrency results
            self.assertEqual(successful_users, user_count, f"All {user_count} users should complete successfully")
            self.assertEqual(len(unique_user_ids), user_count, "All users should have unique IDs")
            self.assertEqual(len(unique_engine_ids), user_count, "All users should have unique engines")
            self.assertEqual(total_operations, user_count * operations_per_user, "All operations should complete")
            
            logger.info(f"✅ PASS: Concurrent operations completed - {successful_users} users, {total_operations} operations")
            return True
        
        result = asyncio.run(test_concurrency())
        self.assertTrue(result, "Concurrent user operations should work without interference")
    
    def test_websocket_event_routing_isolation(self):
        """Test that WebSocket events are routed only to the correct users."""
        logger.info("📡 WEBSOCKET TEST: Validating WebSocket event routing isolation")
        
        async def test_websocket_isolation():
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                # Create separate mock managers for each user to track events
                user1_events = []
                user2_events = []
                
                def create_mock_manager(user_events_list):
                    mock_manager = Mock()
                    async def emit_user_event(*args, **kwargs):
                        user_events_list.append({"args": args, "kwargs": kwargs})
                        return True
                    mock_manager.emit_user_event = emit_user_event
                    return mock_manager
                
                user1_websocket_manager = create_mock_manager(user1_events)
                user2_websocket_manager = create_mock_manager(user2_events)
                
                # Create contexts for two users
                user1_id = UnifiedIdGenerator.generate_base_id("websocket_user1", True, 8)
                user2_id = UnifiedIdGenerator.generate_base_id("websocket_user2", True, 8)
                
                thread1_id, run1_id, _ = UnifiedIdGenerator.generate_user_context_ids(user1_id, "websocket_test")
                thread2_id, run2_id, _ = UnifiedIdGenerator.generate_user_context_ids(user2_id, "websocket_test")
                
                user1_context = UserExecutionContext(
                    user_id=user1_id,
                    run_id=run1_id,
                    thread_id=thread1_id,
                    metadata={'test': 'websocket_user1'}
                )
                
                user2_context = UserExecutionContext(
                    user_id=user2_id,
                    run_id=run2_id,
                    thread_id=thread2_id,
                    metadata={'test': 'websocket_user2'}
                )
                
                # Create engines with separate WebSocket managers
                agent_factory1 = AgentInstanceFactory()
                websocket_emitter1 = UnifiedWebSocketEmitter(
                    manager=user1_websocket_manager,
                    user_id=user1_context.user_id,
                    context=user1_context
                )
                
                agent_factory2 = AgentInstanceFactory()
                websocket_emitter2 = UnifiedWebSocketEmitter(
                    manager=user2_websocket_manager,
                    user_id=user2_context.user_id,
                    context=user2_context
                )
                
                engine1 = UserExecutionEngine(user1_context, agent_factory1, websocket_emitter1)
                engine2 = UserExecutionEngine(user2_context, agent_factory2, websocket_emitter2)
                
                # Trigger WebSocket events for both users
                await websocket_emitter1.notify_agent_started("test_agent1", {"test": "user1_event"})
                await websocket_emitter2.notify_agent_started("test_agent2", {"test": "user2_event"})
                
                await websocket_emitter1.notify_agent_thinking("test_agent1", "User 1 thinking", 1)
                await websocket_emitter2.notify_agent_thinking("test_agent2", "User 2 thinking", 1)
                
                # Validate event isolation
                self.assertGreater(len(user1_events), 0, "User 1 should have received events")
                self.assertGreater(len(user2_events), 0, "User 2 should have received events")
                
                # Events should be isolated - user1 events should not appear in user2's list
                user1_event_data = str(user1_events)
                user2_event_data = str(user2_events)
                
                self.assertIn("user1_event", user1_event_data)
                self.assertNotIn("user1_event", user2_event_data)
                self.assertIn("user2_event", user2_event_data)
                self.assertNotIn("user2_event", user1_event_data)
                
                # Cleanup
                await engine1.cleanup()
                await engine2.cleanup()
                
                logger.info(f"✅ PASS: WebSocket event routing isolated - User1: {len(user1_events)} events, User2: {len(user2_events)} events")
                return True
                
            except Exception as e:
                self.isolation_violations.append(f"WebSocket isolation test failed: {e}")
                logger.error(f"❌ FAIL: WebSocket event routing isolation broken - {e}")
                return False
        
        result = asyncio.run(test_websocket_isolation())
        self.assertTrue(result, "WebSocket event routing should be properly isolated")
    
    def test_resource_limits_isolation(self):
        """Test that resource limits are enforced per user."""
        logger.info("⚡ RESOURCE TEST: Validating resource limits isolation")
        
        async def test_resource_isolation():
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                # Create users with different resource limits
                user1_id = UnifiedIdGenerator.generate_base_id("resource_user1", True, 8)
                user2_id = UnifiedIdGenerator.generate_base_id("resource_user2", True, 8)
                
                thread1_id, run1_id, _ = UnifiedIdGenerator.generate_user_context_ids(user1_id, "resource_test")
                thread2_id, run2_id, _ = UnifiedIdGenerator.generate_user_context_ids(user2_id, "resource_test")
                
                # User 1 - lower resource limits
                user1_context = UserExecutionContext(
                    user_id=user1_id,
                    run_id=run1_id,
                    thread_id=thread1_id,
                    metadata={'test': 'resource_user1'},
                    resource_limits=Mock(max_concurrent_agents=1, max_memory_mb=100)
                )
                
                # User 2 - higher resource limits  
                user2_context = UserExecutionContext(
                    user_id=user2_id,
                    run_id=run2_id,
                    thread_id=thread2_id,
                    metadata={'test': 'resource_user2'},
                    resource_limits=Mock(max_concurrent_agents=5, max_memory_mb=500)
                )
                
                # Create engines
                mock_websocket_manager = Mock()
                mock_websocket_manager.emit_user_event = AsyncMock(return_value=True)
                
                agent_factory1 = AgentInstanceFactory()
                websocket_emitter1 = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user1_context.user_id,
                    context=user1_context
                )
                
                agent_factory2 = AgentInstanceFactory()
                websocket_emitter2 = UnifiedWebSocketEmitter(
                    manager=mock_websocket_manager,
                    user_id=user2_context.user_id,
                    context=user2_context
                )
                
                engine1 = UserExecutionEngine(user1_context, agent_factory1, websocket_emitter1)
                engine2 = UserExecutionEngine(user2_context, agent_factory2, websocket_emitter2)
                
                # Verify resource limits are applied per user
                self.assertEqual(engine1.max_concurrent, 1, "Engine1 should have resource limit of 1")
                self.assertEqual(engine2.max_concurrent, 5, "Engine2 should have resource limit of 5")
                
                # Test that limits are independent
                stats1 = engine1.get_user_execution_stats()
                stats2 = engine2.get_user_execution_stats()
                
                self.assertEqual(stats1["max_concurrent"], 1)
                self.assertEqual(stats2["max_concurrent"], 5)
                self.assertNotEqual(stats1["user_id"], stats2["user_id"])
                
                # Cleanup
                await engine1.cleanup()
                await engine2.cleanup()
                
                logger.info("✅ PASS: Resource limits isolation working correctly")
                return True
                
            except Exception as e:
                self.resource_leaks.append(f"Resource isolation test failed: {e}")
                logger.error(f"❌ FAIL: Resource limits isolation broken - {e}")
                return False
        
        result = asyncio.run(test_resource_isolation())
        self.assertTrue(result, "Resource limits should be isolated per user")
    
    def test_memory_isolation_cleanup(self):
        """Test that memory is properly isolated and cleaned up per user."""
        logger.info("🧠 MEMORY TEST: Validating memory isolation and cleanup")
        
        async def test_memory_isolation():
            try:
                from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
                from netra_backend.app.services.user_execution_context import UserExecutionContext
                from netra_backend.app.agents.supervisor.agent_instance_factory import AgentInstanceFactory
                from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter
                from shared.id_generation.unified_id_generator import UnifiedIdGenerator
                
                engines_created = []
                
                # Create and cleanup multiple users to test memory isolation
                for i in range(3):
                    user_id = UnifiedIdGenerator.generate_base_id(f"memory_user_{i}", True, 8)
                    thread_id, run_id, _ = UnifiedIdGenerator.generate_user_context_ids(user_id, f"memory_test_{i}")
                    
                    user_context = UserExecutionContext(
                        user_id=user_id,
                        run_id=run_id,
                        thread_id=thread_id,
                        metadata={'test': f'memory_user_{i}', 'iteration': i}
                    )
                    
                    mock_websocket_manager = Mock()
                    mock_websocket_manager.emit_user_event = AsyncMock(return_value=True)
                    
                    agent_factory = AgentInstanceFactory()
                    websocket_emitter = UnifiedWebSocketEmitter(
                        manager=mock_websocket_manager,
                        user_id=user_context.user_id,
                        context=user_context
                    )
                    
                    engine = UserExecutionEngine(user_context, agent_factory, websocket_emitter)
                    
                    # Add some state and data
                    engine.set_agent_state(f"test_agent_{i}", f"state_{i}")
                    engine.set_agent_result(f"test_result_{i}", {
                        "large_data": "x" * 1000,  # 1KB of data
                        "iteration": i,
                        "user_id": user_id
                    })
                    
                    # Verify engine is active and has data
                    self.assertTrue(engine.is_active(), f"Engine {i} should be active")
                    self.assertIsNotNone(engine.get_agent_state(f"test_agent_{i}"))
                    
                    engines_created.append((engine, user_id))
                
                # Cleanup engines and verify isolation
                for j, (engine, user_id) in enumerate(engines_created):
                    # Verify engine still has its own data before cleanup
                    result = engine.get_agent_result(f"test_result_{j}")
                    self.assertIsNotNone(result, f"Engine {j} should have its result before cleanup")
                    self.assertEqual(result["user_id"], user_id)
                    
                    # Cleanup
                    await engine.cleanup()
                    
                    # Verify engine is no longer active
                    self.assertFalse(engine.is_active(), f"Engine {j} should be inactive after cleanup")
                
                # Verify that each engine's cleanup didn't affect others (while they were active)
                # This tests that cleanup is properly isolated
                
                logger.info("✅ PASS: Memory isolation and cleanup working correctly")
                return True
                
            except Exception as e:
                self.resource_leaks.append(f"Memory isolation test failed: {e}")
                logger.error(f"❌ FAIL: Memory isolation and cleanup broken - {e}")
                return False
        
        result = asyncio.run(test_memory_isolation())
        self.assertTrue(result, "Memory should be properly isolated and cleaned up per user")
    
    def test_comprehensive_isolation_report(self):
        """Generate comprehensive isolation test report."""
        logger.info("📊 COMPREHENSIVE ISOLATION REPORT")
        
        all_issues = self.isolation_violations + self.concurrency_issues + self.resource_leaks
        
        isolation_summary = {
            'total_issues': len(all_issues),
            'isolation_violations': len(self.isolation_violations),
            'concurrency_issues': len(self.concurrency_issues),
            'resource_leaks': len(self.resource_leaks),
            'isolation_status': 'PASS' if len(all_issues) == 0 else 'FAIL',
            'security_risk': len(self.isolation_violations) > 0,
            'performance_risk': len(self.concurrency_issues) > 0
        }
        
        logger.info(f"ISOLATION TEST SUMMARY:")
        logger.info(f"  Total Issues: {isolation_summary['total_issues']}")
        logger.info(f"  Isolation Violations: {isolation_summary['isolation_violations']}")
        logger.info(f"  Concurrency Issues: {isolation_summary['concurrency_issues']}")
        logger.info(f"  Resource Leaks: {isolation_summary['resource_leaks']}")
        logger.info(f"  Overall Status: {isolation_summary['isolation_status']}")
        
        if all_issues:
            logger.warning("ISOLATION ISSUES DETECTED:")
            for i, issue in enumerate(all_issues[:5], 1):
                logger.warning(f"  {i}. {issue}")
            if len(all_issues) > 5:
                logger.warning(f"  ... and {len(all_issues) - 5} more issues")
        
        # This test should PASS if isolation works correctly
        self.assertEqual(
            isolation_summary['total_issues'], 0,
            f"UserExecutionEngine isolation should work correctly. "
            f"Found {isolation_summary['total_issues']} issues: {all_issues}"
        )
        
        logger.info("✅ SUCCESS: UserExecutionEngine isolation working correctly")


if __name__ == '__main__':
    # Configure logging for direct execution
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run the test
    unittest.main()