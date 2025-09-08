#!/usr/bin/env python3
"""
RequestScopedAgentExecutor Demo - Per-Request Agent Execution with User Isolation

This demo shows how to use the RequestScopedAgentExecutor to replace the singleton
ExecutionEngine pattern and achieve complete user isolation.

Key Benefits Demonstrated:
1. Complete user isolation (no shared state)
2. Per-request execution tracking  
3. User-scoped WebSocket notifications
4. Proper resource cleanup
5. Compatible interface with existing code

Run this demo to see the RequestScopedAgentExecutor in action!
"""

import asyncio
import sys
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Add the project root to Python path for imports
sys.path.insert(0, 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1')

from netra_backend.app.agents.supervisor.request_scoped_executor import (
    RequestScopedAgentExecutor,
    RequestScopedExecutorFactory,
    create_full_request_execution_stack
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.services.websocket_event_emitter import WebSocketEventEmitter


async def demo_basic_usage():
    """Demonstrate basic RequestScopedAgentExecutor usage."""
    print("=" * 60)
    print("DEMO 1: Basic RequestScopedAgentExecutor Usage")
    print("=" * 60)
    
    # Create user context for Alice
    alice_context = UserExecutionContext.from_request(
        user_id="demo_alice",
        thread_id="demo_thread_alice", 
        run_id="demo_run_alice_001",
        metadata={"demo": "alice_session"}
    )
    
    # Mock WebSocket manager
    mock_ws_manager = Mock()
    mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
    
    # Create WebSocket event emitter
    event_emitter = WebSocketEventEmitter(alice_context, mock_ws_manager)
    
    # Mock agent registry  
    mock_registry = Mock()
    mock_agent = Mock()
    mock_agent.process = AsyncMock(return_value="Alice's agent result")
    mock_registry.get = Mock(return_value=mock_agent)
    
    # Create request-scoped executor
    async with RequestScopedAgentExecutor(
        alice_context, event_emitter, mock_registry
    ) as executor:
        
        print(f"✅ Created executor for user: {alice_context.user_id}")
        print(f"   Context ID: {alice_context.get_correlation_id()}")
        
        # Create test state
        test_state = DeepAgentState(
            user_request="Alice wants to analyze her data",
            user_id=alice_context.user_id,
            run_id=alice_context.run_id
        )
        
        # Mock the agent execution core 
        mock_result = AgentExecutionResult(
            success=True,
            state=test_state,
            duration=1.2
        )
        
        # Mock the agent core execution (for demo purposes)
        executor._agent_core.execute_agent = AsyncMock(return_value=mock_result)
        
        print("\n🔄 Executing agent for Alice...")
        result = await executor.execute_agent("demo_agent", test_state)
        
        print(f"✅ Agent execution completed!")
        print(f"   Success: {result.success}")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   User Request: {result.state.user_request}")
        
        # Show metrics
        metrics = executor.get_metrics()
        print(f"\n📊 Execution Metrics:")
        print(f"   Total Executions: {metrics['total_executions']}")
        print(f"   Success Rate: {metrics['success_rate']:.1%}")
        print(f"   User Context: {metrics['user_context']['user_id']}")
    
    print("\n✅ Executor disposed automatically (async context manager)")


async def demo_user_isolation():
    """Demonstrate complete user isolation between concurrent users."""
    print("\n" + "=" * 60)
    print("🔐 DEMO 2: Complete User Isolation")
    print("=" * 60)
    
    # Create contexts for different users
    users = []
    executors = []
    
    for i in range(3):
        user_context = UserExecutionContext.from_request(
            user_id=f"demo_user_{i+1}",
            thread_id=f"demo_thread_{i+1}",
            run_id=f"demo_run_{i+1}_001",
            metadata={"demo": f"user_{i+1}_session", "priority": i+1}
        )
        users.append(user_context)
    
    # Mock WebSocket manager (shared infrastructure)
    mock_ws_manager = Mock()
    sent_messages = []
    
    async def track_messages(thread_id, message):
        sent_messages.append((thread_id, message))
        return True
    
    mock_ws_manager.send_to_thread = track_messages
    
    # Mock agent registry
    mock_registry = Mock()
    
    print("👥 Creating isolated executors for 3 concurrent users...")
    
    # Create executors for each user
    for user_context in users:
        event_emitter = WebSocketEventEmitter(user_context, mock_ws_manager)
        executor = RequestScopedAgentExecutor(user_context, event_emitter, mock_registry)
        executors.append(executor)
        
        print(f"   User {user_context.user_id}: Context {user_context.get_correlation_id()}")
    
    # Simulate concurrent execution
    async def simulate_user_work(user_index, executor):
        """Simulate work for a specific user."""
        user_context = executor.get_user_context()
        
        # Create user-specific state
        test_state = DeepAgentState(
            user_request=f"User {user_index+1}'s unique request",
            user_id=user_context.user_id,
            run_id=user_context.run_id
        )
        
        # Mock execution
        mock_result = AgentExecutionResult(
            success=True,
            state=test_state,
            duration=0.5 + (user_index * 0.3)  # Different durations
        )
        executor._agent_core.execute_agent = AsyncMock(return_value=mock_result)
        
        # Execute
        await asyncio.sleep(0.1 * user_index)  # Stagger starts
        result = await executor.execute_agent(f"agent_for_user_{user_index+1}", test_state)
        
        return user_index + 1, result
    
    print("\n🏃‍♂️ Running concurrent executions...")
    
    # Run all users concurrently
    tasks = [simulate_user_work(i, executor) for i, executor in enumerate(executors)]
    results = await asyncio.gather(*tasks)
    
    print("\n✅ All executions completed! Results:")
    for user_num, result in results:
        print(f"   User {user_num}: {result.state.user_request}")
        print(f"     Success: {result.success}, Duration: {result.duration:.2f}s")
    
    # Verify isolation by checking metrics
    print("\n🔒 Verifying User Isolation:")
    for i, executor in enumerate(executors):
        metrics = executor.get_metrics()
        print(f"   User {i+1} Metrics:")
        print(f"     Context ID: {metrics['context_id']}")
        print(f"     Total Executions: {metrics['total_executions']}")
        print(f"     User ID: {metrics['user_context']['user_id']}")
        
        # Verify no cross-contamination
        assert metrics['total_executions'] == 1, f"User {i+1} should have 1 execution only"
        assert f"demo_user_{i+1}" in metrics['user_context']['user_id'], f"User {i+1} context mismatch"
    
    print("\n✅ User isolation verified - no data leakage between users!")
    
    # Check WebSocket message routing
    print(f"\n📡 WebSocket Messages Sent: {len(sent_messages)}")
    thread_ids = set(msg[0] for msg in sent_messages)
    print(f"   Unique Thread IDs: {len(thread_ids)} (should be 3)")
    assert len(thread_ids) == 3, "Messages should go to 3 different threads"
    
    # Clean up
    for executor in executors:
        await executor.dispose()


async def demo_factory_patterns():
    """Demonstrate factory patterns for easier usage."""
    print("\n" + "=" * 60)
    print("🏭 DEMO 3: Factory Patterns & Convenience Functions")
    print("=" * 60)
    
    # Create user context
    user_context = UserExecutionContext.from_request(
        user_id="demo_factory_user",
        thread_id="demo_factory_thread",
        run_id="demo_factory_run_001"
    )
    
    print("🔧 Method 1: Using RequestScopedExecutorFactory")
    
    # Mock dependencies
    mock_ws_manager = Mock()
    mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
    event_emitter = WebSocketEventEmitter(user_context, mock_ws_manager)
    mock_registry = Mock()
    
    # Create via factory
    executor = await RequestScopedExecutorFactory.create_executor(
        user_context, event_emitter, mock_registry
    )
    
    print(f"✅ Factory created executor for: {user_context.user_id}")
    
    # Test it works
    test_state = DeepAgentState(user_request="Factory test request")
    mock_result = AgentExecutionResult(success=True, state=test_state, duration=0.8)
    executor._agent_core.execute_agent = AsyncMock(return_value=mock_result)
    
    result = await executor.execute_agent("factory_agent", test_state)
    print(f"✅ Factory executor worked: Success={result.success}")
    
    await executor.dispose()
    
    print("\n🔧 Method 2: Using Convenience Function")
    
    # Use convenience function to create full stack
    try:
        # This would normally create the full stack but requires more mocking
        print("📦 create_full_request_execution_stack() available for production use")
        print("   (Creates both WebSocketEventEmitter and RequestScopedAgentExecutor)")
    except Exception as e:
        print(f"   Skipping full stack demo due to dependencies: {e}")


async def demo_comparison_with_singleton():
    """Show the key differences from singleton ExecutionEngine."""
    print("\n" + "=" * 60)
    print("⚖️  DEMO 4: Comparison with Singleton Pattern")
    print("=" * 60)
    
    print("❌ OLD SINGLETON PATTERN PROBLEMS:")
    print("   • Global state shared between all users")
    print("   • active_runs dictionary mixed all users")
    print("   • Single semaphore for ALL user concurrency")
    print("   • WebSocket events could leak between users")
    print("   • Memory leaks from global collections")
    
    print("\n✅ NEW REQUEST-SCOPED PATTERN BENEFITS:")
    print("   • Complete user isolation (no shared state)")
    print("   • Per-request execution tracking")  
    print("   • User-scoped WebSocket notifications")
    print("   • Automatic resource cleanup")
    print("   • Horizontal scaling friendly")
    print("   • Memory efficient (no global accumulation)")
    
    # Create two "users" to demonstrate isolation
    user1_context = UserExecutionContext.from_request(
        user_id="comparison_user_1", thread_id="thread_1", run_id="run_1"
    )
    user2_context = UserExecutionContext.from_request(
        user_id="comparison_user_2", thread_id="thread_2", run_id="run_2"
    )
    
    mock_ws_manager = Mock()
    mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
    mock_registry = Mock()
    
    # Create separate executors
    emitter1 = WebSocketEventEmitter(user1_context, mock_ws_manager)
    emitter2 = WebSocketEventEmitter(user2_context, mock_ws_manager)
    
    executor1 = RequestScopedAgentExecutor(user1_context, emitter1, mock_registry)
    executor2 = RequestScopedAgentExecutor(user2_context, emitter2, mock_registry)
    
    print(f"\n🔒 Isolation Verification:")
    print(f"   User 1 Context: {executor1.get_user_context().get_correlation_id()}")
    print(f"   User 2 Context: {executor2.get_user_context().get_correlation_id()}")
    print(f"   Executors Share State: {id(executor1._request_executions) == id(executor2._request_executions)}")
    print(f"   Executors Share Metrics: {id(executor1._metrics) == id(executor2._metrics)}")
    
    # Verify different object instances
    assert id(executor1._request_executions) != id(executor2._request_executions), "Should have separate execution tracking"
    assert id(executor1._metrics) != id(executor2._metrics), "Should have separate metrics"
    assert executor1.get_user_context() != executor2.get_user_context(), "Should have different contexts"
    
    print("✅ Perfect isolation confirmed!")
    
    # Clean up
    await executor1.dispose()
    await executor2.dispose()


async def main():
    """Run all demos."""
    print("🚀 RequestScopedAgentExecutor Demo")
    print("Demonstrates per-request agent execution with complete user isolation")
    
    try:
        await demo_basic_usage()
        await demo_user_isolation()
        await demo_factory_patterns()
        await demo_comparison_with_singleton()
        
        print("\n" + "=" * 60)
        print("🎉 ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\n✅ Key Takeaways:")
        print("   • RequestScopedAgentExecutor provides complete user isolation")
        print("   • No global state - each request gets its own executor")
        print("   • WebSocket events are properly scoped to users")
        print("   • Automatic resource cleanup prevents memory leaks")
        print("   • Compatible interface with existing ExecutionEngine usage")
        print("   • Factory patterns available for easy integration")
        
        print("\n🔧 Integration Guide:")
        print("   1. Replace ExecutionEngine(registry, websocket) with:")
        print("      RequestScopedAgentExecutor(user_context, event_emitter, registry)")
        print("   2. Create per-request instead of singleton instances")
        print("   3. Use UserExecutionContext to carry user state")
        print("   4. Use WebSocketEventEmitter for user-scoped notifications")
        print("   5. Dispose executors when request completes")
        
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    asyncio.run(main())