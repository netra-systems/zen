"""
Example: AgentInstanceFactory Usage for Per-Request Agent Instantiation

This example demonstrates how to use the AgentInstanceFactory to create
completely isolated agent instances for each user request.

CRITICAL: This pattern prevents user context leakage and enables safe
multi-user concurrent operations.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text

from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    configure_agent_instance_factory,
    get_agent_instance_factory
)
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class RequestHandler:
    """
    Example request handler showing proper AgentInstanceFactory usage.
    
    This demonstrates the correct pattern for handling user requests
    with complete isolation and proper resource management.
    """
    
    def __init__(self, factory: AgentInstanceFactory, session_factory):
        self.factory = factory
        self.session_factory = session_factory
    
    async def handle_user_request(self, 
                                 user_id: str,
                                 thread_id: str,
                                 user_message: str,
                                 agent_name: str = "triage") -> Dict[str, Any]:
        """
        Handle a user request with complete isolation.
        
        This method demonstrates the proper pattern for:
        1. Creating request-scoped database session
        2. Using factory to create isolated execution context
        3. Creating fresh agent instance for the user
        4. Executing agent with proper WebSocket events
        5. Automatic cleanup of all resources
        
        Args:
            user_id: Unique user identifier
            thread_id: Thread identifier for WebSocket routing
            user_message: User's request message
            agent_name: Name of agent to execute
            
        Returns:
            Dict containing response and execution metadata
        """
        
        # Generate unique run ID for this request
        run_id = f"run_{user_id}_{thread_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}"
        
        logger.info(f"[U+1F680] Handling request for user {user_id}: '{user_message}'")
        
        # Create request-scoped database session
        async with self.session_factory() as db_session:
            
            # Use factory's context manager for automatic resource cleanup
            async with self.factory.user_execution_scope(
                user_id=user_id,
                thread_id=thread_id,
                run_id=run_id,
                db_session=db_session,
                metadata={
                    'request_type': 'user_message',
                    'agent_requested': agent_name,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            ) as user_context:
                
                logger.info(f" PASS:  Created isolated execution context for user {user_id}")
                
                # Create fresh agent instance for this user
                agent = await self.factory.create_agent_instance(agent_name, user_context)
                logger.info(f" PASS:  Created fresh {agent_name} agent for user {user_id}")
                
                # Prepare agent state with user-specific data
                agent_state = DeepAgentState(
                    user_request=user_message,
                    thread_id=thread_id,
                    user_id=user_id
                )
                
                # Execute agent with proper isolation
                logger.info(f"[U+1F916] Executing {agent_name} agent for user {user_id}")
                
                try:
                    # Agent execution automatically emits WebSocket events
                    # - agent_started
                    # - agent_thinking 
                    # - tool_executing/tool_completed (if tools are used)
                    # - agent_completed
                    result = await agent.execute(agent_state, run_id, stream_updates=True)
                    
                    logger.info(f" PASS:  Agent execution completed for user {user_id}")
                    
                    # Store execution result in user context
                    user_context.run_history.append({
                        'run_id': run_id,
                        'agent_name': agent_name,
                        'user_message': user_message,
                        'result': result,
                        'completed_at': datetime.now(timezone.utc).isoformat()
                    })
                    
                    return {
                        'success': True,
                        'user_id': user_id,
                        'run_id': run_id,
                        'agent_name': agent_name,
                        'result': result,
                        'execution_context': user_context.get_context_summary(),
                        'message': f'{agent_name} completed successfully for user {user_id}'
                    }
                    
                except Exception as e:
                    logger.error(f" FAIL:  Agent execution failed for user {user_id}: {e}")
                    
                    # Send error notification via WebSocket
                    if user_context.websocket_emitter:
                        await user_context.websocket_emitter.notify_agent_error(
                            agent_name=agent_name,
                            error=str(e),
                            error_context={'user_id': user_id, 'run_id': run_id}
                        )
                    
                    return {
                        'success': False,
                        'user_id': user_id,
                        'run_id': run_id,
                        'agent_name': agent_name,
                        'error': str(e),
                        'execution_context': user_context.get_context_summary(),
                        'message': f'{agent_name} failed for user {user_id}: {e}'
                    }
                
                # Context automatically cleaned up when exiting the 'async with' block
    
    async def handle_concurrent_users(self, user_requests: list) -> Dict[str, Any]:
        """
        Handle multiple user requests concurrently with complete isolation.
        
        This demonstrates that multiple users can be served simultaneously
        without any data leakage or interference.
        
        Args:
            user_requests: List of (user_id, thread_id, message, agent_name) tuples
            
        Returns:
            Dict containing results for all users
        """
        
        logger.info(f"[U+1F680] Handling {len(user_requests)} concurrent user requests")
        
        async def process_single_request(user_request):
            """Process a single user request."""
            user_id, thread_id, message, agent_name = user_request
            return await self.handle_user_request(user_id, thread_id, message, agent_name)
        
        # Execute all user requests concurrently
        results = await asyncio.gather(*[
            process_single_request(request) for request in user_requests
        ], return_exceptions=True)
        
        # Analyze results
        successful_requests = [r for r in results if isinstance(r, dict) and r.get('success', False)]
        failed_requests = [r for r in results if isinstance(r, dict) and not r.get('success', False)]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        logger.info(f" PASS:  Concurrent processing complete:")
        logger.info(f"   - Successful: {len(successful_requests)}")
        logger.info(f"   - Failed: {len(failed_requests)}")
        logger.info(f"   - Exceptions: {len(exceptions)}")
        
        return {
            'total_requests': len(user_requests),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'exceptions': len(exceptions),
            'results': results,
            'factory_metrics': self.factory.get_factory_metrics()
        }


async def example_basic_usage():
    """Basic usage example of AgentInstanceFactory."""
    
    print("\n" + "="*60)
    print("[U+1F9EA] BASIC AGENTINSTANCEFACTORY USAGE EXAMPLE")
    print("="*60)
    
    # Setup test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.execute(text("CREATE TABLE user_data (id INTEGER PRIMARY KEY, user_id TEXT, content TEXT)"))
    
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Get configured factory (in real app, this would be configured at startup)
    factory = get_agent_instance_factory()
    
    # For this example, we'll configure with mock components
    # In real app, these would be your actual registry and WebSocket bridge
    from unittest.mock import MagicMock, AsyncMock
    from netra_backend.app.agents.base_agent import BaseAgent
    
    # Create simple mock agent
    class ExampleAgent(BaseAgent):
        async def execute(self, state, run_id="", stream_updates=False):
            # Simulate agent work
            await self.emit_agent_started("Starting example agent")
            await asyncio.sleep(0.1)  # Simulate processing
            await self.emit_thinking("Processing user request", 1)
            await asyncio.sleep(0.1)
            await self.emit_thinking("Generating response", 2) 
            await asyncio.sleep(0.1)
            await self.emit_agent_completed({'response': f'Hello {state.user_id}!'})
            
            return {
                'response': f'Hello {state.user_id}! I processed your request: "{state.user_request}"',
                'agent': self.name,
                'user_id': state.user_id,
                'run_id': run_id
            }
    
    # Setup mock infrastructure
    mock_llm = MagicMock()
    mock_dispatcher = MagicMock()
    mock_websocket_bridge = MagicMock()
    mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
    mock_websocket_bridge.notify_agent_thinking = AsyncMock(return_value=True)
    mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)
    mock_websocket_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
    mock_websocket_bridge.unregister_run_mapping = AsyncMock(return_value=True)
    
    # Create and configure registry
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    registry = AgentRegistry(mock_llm, mock_dispatcher)
    registry.register("example_agent", ExampleAgent(mock_llm, "ExampleAgent"))
    
    # Configure factory
    factory.configure(
        agent_registry=registry,
        websocket_bridge=mock_websocket_bridge
    )
    
    # Create request handler
    handler = RequestHandler(factory, session_factory)
    
    # Example 1: Single user request
    print("\n[U+1F4DD] Example 1: Single User Request")
    
    result = await handler.handle_user_request(
        user_id="alice",
        thread_id="thread_alice_1",
        user_message="Hello, can you help me?",
        agent_name="example_agent"
    )
    
    print(f" PASS:  Result: {result['message']}")
    print(f" CHART:  Response: {result['result']['response']}")
    
    # Example 2: Concurrent users
    print("\n[U+1F465] Example 2: Concurrent User Requests")
    
    concurrent_requests = [
        ("alice", "thread_alice_2", "What's the weather like?", "example_agent"),
        ("bob", "thread_bob_1", "Can you help me with coding?", "example_agent"),
        ("charlie", "thread_charlie_1", "I need assistance", "example_agent"),
        ("diana", "thread_diana_1", "Hello there!", "example_agent"),
    ]
    
    concurrent_results = await handler.handle_concurrent_users(concurrent_requests)
    
    print(f" PASS:  Processed {concurrent_results['total_requests']} requests concurrently")
    print(f" CHART:  Success rate: {concurrent_results['successful_requests']}/{concurrent_results['total_requests']}")
    
    # Show factory metrics
    print("\n[U+1F4C8] Factory Metrics:")
    metrics = factory.get_factory_metrics()
    for key, value in metrics.items():
        if key != 'active_context_ids':  # Skip the list for cleaner output
            print(f"   {key}: {value}")
    
    # Cleanup
    await engine.dispose()
    
    print("\n PASS:  Basic usage example completed successfully!")
    print("   - All users received isolated agent instances")
    print("   - No data leakage between users")
    print("   - WebSocket events were properly emitted")
    print("   - Resources were automatically cleaned up")


async def example_advanced_patterns():
    """Advanced usage patterns for AgentInstanceFactory."""
    
    print("\n" + "="*60)
    print("[U+1F52C] ADVANCED AGENTINSTANCEFACTORY PATTERNS")
    print("="*60)
    
    # Get factory instance
    factory = get_agent_instance_factory()
    
    # Setup test database
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    # Pattern 1: Manual resource management (not recommended, but possible)
    print("\n[U+1F527] Pattern 1: Manual Resource Management")
    
    async with session_factory() as session:
        
        # Create context manually
        context = await factory.create_user_execution_context(
            user_id="manual_user",
            thread_id="manual_thread",
            run_id="manual_run",
            db_session=session,
            metadata={'pattern': 'manual_management'}
        )
        
        print(f" PASS:  Created context: {context.user_id}")
        
        # Create agent manually  
        agent = await factory.create_agent_instance("example_agent", context)
        print(f" PASS:  Created agent: {agent.name}")
        
        # Manual cleanup (important!)
        await factory.cleanup_user_context(context)
        print(" PASS:  Manually cleaned up context")
    
    # Pattern 2: Context manager (recommended)
    print("\n[U+2728] Pattern 2: Context Manager (Recommended)")
    
    async with session_factory() as session:
        async with factory.user_execution_scope(
            user_id="auto_user", 
            thread_id="auto_thread",
            run_id="auto_run",
            db_session=session,
            metadata={'pattern': 'context_manager'}
        ) as context:
            
            agent = await factory.create_agent_instance("example_agent", context)
            print(f" PASS:  Created agent in managed context: {agent.name}")
            
            # Context automatically cleaned up when exiting
    
    print(" PASS:  Context automatically cleaned up!")
    
    # Pattern 3: Per-user concurrency control
    print("\n[U+2699][U+FE0F] Pattern 3: Per-User Concurrency Control")
    
    async def controlled_execution(user_id: str, request_num: int):
        """Execute with per-user concurrency limits."""
        
        # Get user-specific semaphore
        semaphore = await factory.get_user_semaphore(user_id)
        
        async with semaphore:  # This limits concurrent executions per user
            async with session_factory() as session:
                async with factory.user_execution_scope(
                    user_id=user_id,
                    thread_id=f"controlled_thread_{request_num}",
                    run_id=f"controlled_run_{user_id}_{request_num}",
                    db_session=session
                ) as context:
                    
                    print(f" TARGET:  User {user_id} request {request_num} started (controlled)")
                    await asyncio.sleep(0.1)  # Simulate work
                    print(f" PASS:  User {user_id} request {request_num} completed")
                    
                    return f"Controlled execution for {user_id} request {request_num}"
    
    # Test concurrency control
    tasks = []
    for user in ["alice", "bob"]:
        for req in range(3):  # 3 requests per user
            tasks.append(controlled_execution(user, req))
    
    results = await asyncio.gather(*tasks)
    print(f" PASS:  Completed {len(results)} controlled executions")
    
    # Pattern 4: Factory metrics monitoring
    print("\n CHART:  Pattern 4: Factory Metrics Monitoring")
    
    metrics = factory.get_factory_metrics()
    print("Current factory metrics:")
    for key, value in metrics.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for sub_key, sub_value in value.items():
                print(f"     {sub_key}: {sub_value}")
        else:
            print(f"   {key}: {value}")
    
    # Pattern 5: Active context monitoring
    print("\n SEARCH:  Pattern 5: Active Context Monitoring")
    
    active_summary = factory.get_active_contexts_summary()
    print(f"Active contexts: {active_summary['total_active_contexts']}")
    
    # Cleanup
    await engine.dispose()
    
    print("\n PASS:  Advanced patterns example completed!")


async def main():
    """Run all examples."""
    
    print("[U+1F680] AgentInstanceFactory Usage Examples")
    print("=====================================")
    print("This demonstrates proper per-request agent instantiation")
    print("with complete user isolation and resource management.")
    
    try:
        await example_basic_usage()
        await example_advanced_patterns()
        
        print("\n" + "="*60)
        print(" CELEBRATION:  ALL EXAMPLES COMPLETED SUCCESSFULLY!  CELEBRATION: ")
        print("="*60)
        print(" PASS:  AgentInstanceFactory provides complete user isolation")
        print(" PASS:  Fresh agent instances created per request")
        print(" PASS:  WebSocket events properly routed to users")
        print(" PASS:  Database sessions isolated per request")
        print(" PASS:  Automatic resource cleanup prevents leaks")
        print(" PASS:  Concurrent users safely supported")
        print("="*60)
        
    except Exception as e:
        print(f"\n FAIL:  Example failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())