#!/usr/bin/env python3
"""
RequestScopedAgentExecutor Simple Demo - Per-Request Agent Execution

A simple demonstration of the RequestScopedAgentExecutor showing:
- Per-request user isolation
- WebSocket event scoping  
- Resource cleanup
- Factory patterns
"""

import asyncio
import sys
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock

# Add the project root to Python path for imports
sys.path.insert(0, 'C:\\Users\\antho\\OneDrive\\Desktop\\Netra\\netra-core-generation-1')

from netra_backend.app.agents.supervisor.request_scoped_executor import (
    RequestScopedAgentExecutor,
    RequestScopedExecutorFactory
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionResult
# Note: DeepAgentState eliminated - using UserExecutionContext pattern instead
from netra_backend.app.services.websocket_event_emitter import WebSocketEventEmitter


async def demo_basic_usage():
    """Demonstrate basic RequestScopedAgentExecutor usage."""
    print("=" * 60)
    print("DEMO: Basic RequestScopedAgentExecutor Usage")
    print("=" * 60)
    
    # Create user context
    user_context = UserExecutionContext.from_request(
        user_id="demo_alice",
        thread_id="demo_thread_alice", 
        run_id="demo_run_001",
        metadata={"demo": "basic_usage"}
    )
    
    # Mock WebSocket manager
    mock_ws_manager = Mock()
    mock_ws_manager.send_to_thread = AsyncMock(return_value=True)
    
    # Create WebSocket event emitter
    event_emitter = WebSocketEventEmitter(user_context, mock_ws_manager)
    
    # Mock agent registry  
    mock_registry = Mock()
    
    # Create request-scoped executor
    executor = RequestScopedAgentExecutor(user_context, event_emitter, mock_registry)
    
    try:
        print(f"Created executor for user: {user_context.user_id}")
        print(f"Context ID: {user_context.get_correlation_id()}")
        
        # Create test state data (embedded in UserExecutionContext)
        # Note: UserExecutionContext contains user state, so we just pass context directly
        test_state_data = {
            "user_request": "Analyze user data",
            "user_id": user_context.user_id,
            "run_id": user_context.run_id
        }
        
        # Mock the agent execution
        mock_result = AgentExecutionResult(
            success=True,
            state=user_context,  # Now uses UserExecutionContext instead of DeepAgentState
            duration=1.2
        )
        executor._agent_core.execute_agent = AsyncMock(return_value=mock_result)
        
        print("\nExecuting agent...")
        result = await executor.execute_agent("demo_agent", user_context)
        
        print(f"SUCCESS: Agent execution completed!")
        print(f"  Duration: {result.duration:.2f}s")
        print(f"  User ID: {result.state.user_id}")  # UserExecutionContext.user_id
        
        # Show metrics
        metrics = executor.get_metrics()
        print(f"\nMetrics:")
        print(f"  Total Executions: {metrics['total_executions']}")
        print(f"  Success Rate: {metrics['success_rate']:.1%}")
        
    finally:
        await executor.dispose()
        print("\nExecutor disposed successfully")


async def demo_user_isolation():
    """Demonstrate complete user isolation."""
    print("\n" + "=" * 60)
    print("DEMO: Complete User Isolation")
    print("=" * 60)
    
    # Create contexts for different users
    users = []
    executors = []
    
    for i in range(3):
        user_context = UserExecutionContext.from_request(
            user_id=f"demo_user_{i+1}",
            thread_id=f"demo_thread_{i+1}",
            run_id=f"demo_run_{i+1}",
            metadata={"user_number": i+1}
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
    
    print("Creating isolated executors for 3 users...")
    
    # Create executors for each user
    for user_context in users:
        event_emitter = WebSocketEventEmitter(user_context, mock_ws_manager)
        executor = RequestScopedAgentExecutor(user_context, event_emitter, mock_registry)
        executors.append(executor)
        print(f"  User {user_context.user_id}: {user_context.get_correlation_id()}")
    
    # Simulate concurrent execution
    async def simulate_user_work(user_index, executor):
        user_context = executor.get_user_context()
        # DeepAgentState eliminated - UserExecutionContext contains all user state
        test_state_data = {
            "user_request": f"User {user_index+1}'s request",
            "user_id": user_context.user_id,
            "run_id": user_context.run_id
        }
        
        # Mock execution
        mock_result = AgentExecutionResult(
            success=True,
            state=user_context,  # Uses UserExecutionContext instead of DeepAgentState
            duration=0.5 + (user_index * 0.2)
        )
        executor._agent_core.execute_agent = AsyncMock(return_value=mock_result)
        
        # Stagger execution starts
        await asyncio.sleep(0.1 * user_index)
        result = await executor.execute_agent(f"agent_{user_index+1}", user_context)
        return user_index + 1, result
    
    print("\nRunning concurrent executions...")
    
    # Run all users concurrently
    tasks = [simulate_user_work(i, executor) for i, executor in enumerate(executors)]
    results = await asyncio.gather(*tasks)
    
    print("\nResults:")
    for user_num, result in results:
        print(f"  User {user_num}: {result.state.user_id} - Duration: {result.duration:.2f}s")  # UserExecutionContext.user_id
    
    # Verify isolation
    print("\nVerifying User Isolation:")
    for i, executor in enumerate(executors):
        metrics = executor.get_metrics()
        print(f"  User {i+1}:")
        print(f"    Context ID: {metrics['context_id']}")
        print(f"    Executions: {metrics['total_executions']}")
        
        # Verify no cross-contamination
        assert metrics['total_executions'] == 1, f"User {i+1} should have 1 execution only"
    
    print("SUCCESS: User isolation verified - no data leakage!")
    
    # Check WebSocket routing
    print(f"\nWebSocket Messages: {len(sent_messages)} sent to {len(set(msg[0] for msg in sent_messages))} threads")
    
    # Clean up
    for executor in executors:
        await executor.dispose()


async def demo_comparison():
    """Show key differences from singleton pattern."""
    print("\n" + "=" * 60)
    print("DEMO: Comparison with Singleton Pattern")
    print("=" * 60)
    
    print("OLD SINGLETON PROBLEMS:")
    print("  - Global state shared between all users")
    print("  - Mixed user execution in single collections")
    print("  - WebSocket events could leak between users")
    print("  - Memory leaks from global accumulation")
    
    print("\nNEW REQUEST-SCOPED BENEFITS:")
    print("  - Complete user isolation (no shared state)")
    print("  - Per-request execution tracking")  
    print("  - User-scoped WebSocket notifications")
    print("  - Automatic resource cleanup")
    print("  - Horizontal scaling friendly")
    
    # Demo isolation with two users
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
    
    print(f"\nIsolation Verification:")
    print(f"  User 1: {executor1.get_user_context().get_correlation_id()}")
    print(f"  User 2: {executor2.get_user_context().get_correlation_id()}")
    print(f"  Share State: {id(executor1._request_executions) == id(executor2._request_executions)}")
    print(f"  Share Metrics: {id(executor1._metrics) == id(executor2._metrics)}")
    
    # Verify different instances
    assert id(executor1._request_executions) != id(executor2._request_executions)
    assert id(executor1._metrics) != id(executor2._metrics)
    assert executor1.get_user_context() != executor2.get_user_context()
    
    print("SUCCESS: Perfect isolation confirmed!")
    
    # Clean up
    await executor1.dispose()
    await executor2.dispose()


async def main():
    """Run all demos."""
    print("RequestScopedAgentExecutor Demo")
    print("Demonstrates per-request agent execution with complete user isolation")
    
    try:
        await demo_basic_usage()
        await demo_user_isolation()
        await demo_comparison()
        
        print("\n" + "=" * 60)
        print("ALL DEMOS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nKey Benefits:")
        print("  - Complete user isolation (no global state)")
        print("  - Per-request execution tracking")
        print("  - User-scoped WebSocket notifications")
        print("  - Automatic resource cleanup")
        print("  - Compatible with existing interfaces")
        
        print("\nIntegration Steps:")
        print("  1. Replace ExecutionEngine singleton with RequestScopedAgentExecutor per-request")
        print("  2. Use UserExecutionContext to carry user state")
        print("  3. Use WebSocketEventEmitter for user-scoped notifications")
        print("  4. Dispose executors when request completes")
        
    except Exception as e:
        print(f"\nDemo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)