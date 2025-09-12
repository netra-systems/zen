#!/usr/bin/env python3
"""Debug script for concurrent user isolation issues."""

import asyncio
import uuid
from unittest.mock import MagicMock, patch

from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext


async def test_single_engine_creation():
    """Test creating a single engine to see basic issues."""
    print("Testing single engine creation...")
    
    # Create mock WebSocket bridge
    mock_bridge = MagicMock()
    mock_bridge.is_connected.return_value = True
    mock_bridge.emit = asyncio.coroutine(lambda *args, **kwargs: True)
    mock_bridge.emit_to_user = asyncio.coroutine(lambda *args, **kwargs: True)
    
    # Create factory
    factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
    
    # Create user context
    context = UserExecutionContext(
        user_id=f"test_user_{uuid.uuid4().hex[:8]}",
        thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
        run_id=f"test_run_{uuid.uuid4().hex[:8]}",
        request_id=f"test_req_{uuid.uuid4().hex[:8]}",
        websocket_client_id=f"test_ws_{uuid.uuid4().hex[:8]}",
        agent_context={"test": True},
        audit_metadata={"test_type": "debug"}
    )
    
    try:
        print(f"Creating engine for user: {context.user_id}")
        
        # Mock the agent factory creation
        with patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory') as mock_factory_class:
            mock_factory = MagicMock()
            mock_factory._agent_registry = MagicMock()
            mock_factory._websocket_bridge = mock_bridge
            mock_factory_class.return_value = mock_factory
            
            engine = await factory.create_for_user(context)
            print(f" PASS:  Successfully created engine: {engine.engine_id}")
            print(f"   User ID: {engine.context.user_id}")
            print(f"   Run ID: {engine.context.run_id}")
            return True
            
    except Exception as e:
        print(f" FAIL:  Engine creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_concurrent_engine_creation():
    """Test concurrent engine creation to see isolation issues."""
    print("\nTesting concurrent engine creation...")
    
    # Create mock WebSocket bridge
    mock_bridge = MagicMock()
    mock_bridge.is_connected.return_value = True
    mock_bridge.emit = asyncio.coroutine(lambda *args, **kwargs: True)
    mock_bridge.emit_to_user = asyncio.coroutine(lambda *args, **kwargs: True)
    
    # Create factory
    factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
    
    async def create_user_engine(user_id: str):
        """Create engine for a specific user."""
        context = UserExecutionContext(
            user_id=f"concurrent_user_{user_id}_{uuid.uuid4().hex[:8]}",
            thread_id=f"concurrent_thread_{user_id}_{uuid.uuid4().hex[:8]}",
            run_id=f"concurrent_run_{user_id}_{uuid.uuid4().hex[:8]}",
            request_id=f"concurrent_req_{user_id}_{uuid.uuid4().hex[:8]}",
            websocket_client_id=f"concurrent_ws_{user_id}_{uuid.uuid4().hex[:8]}",
            agent_context={"concurrent_test": True, "user_id": user_id},
            audit_metadata={"test_type": "concurrent", "user_id": user_id}
        )
        
        try:
            with patch('netra_backend.app.agents.supervisor.execution_engine_factory.AgentInstanceFactory') as mock_factory_class:
                mock_factory = MagicMock()
                mock_factory._agent_registry = MagicMock()
                mock_factory._websocket_bridge = mock_bridge
                mock_factory_class.return_value = mock_factory
                
                engine = await factory.create_for_user(context)
                print(f" PASS:  User {user_id}: Created engine {engine.engine_id}")
                return (user_id, engine)
                
        except Exception as e:
            print(f" FAIL:  User {user_id}: Engine creation failed: {e}")
            return (user_id, None)
    
    # Create engines for multiple users concurrently
    user_ids = [f"user_{i}" for i in range(5)]
    tasks = [create_user_engine(user_id) for user_id in user_ids]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_engines = []
    for result in results:
        if not isinstance(result, Exception):
            user_id, engine = result
            if engine is not None:
                successful_engines.append((user_id, engine))
    
    print(f"\n CHART:  Results: {len(successful_engines)}/{len(user_ids)} engines created successfully")
    
    # Check isolation
    if len(successful_engines) > 1:
        user_ids_created = [user_id for user_id, _ in successful_engines]
        print(f" PASS:  User isolation check: {len(set(user_ids_created))} unique users")
        
        # Check that each engine has unique context
        contexts = [engine.context for _, engine in successful_engines]
        unique_user_ids = set(ctx.user_id for ctx in contexts)
        unique_run_ids = set(ctx.run_id for ctx in contexts)
        
        print(f"   Unique user IDs: {len(unique_user_ids)}")
        print(f"   Unique run IDs: {len(unique_run_ids)}")
        
        if len(unique_user_ids) == len(successful_engines) and len(unique_run_ids) == len(successful_engines):
            print(" PASS:  Isolation verified: All contexts are unique")
            return True
        else:
            print(" FAIL:  Isolation failure: Shared contexts detected")
            return False
    else:
        print(" FAIL:  Cannot test isolation: Too few engines created")
        return False


async def main():
    """Main debug function."""
    print(" SEARCH:  Debug: Concurrent User Isolation Issues")
    print("=" * 50)
    
    # Test single engine creation first
    single_success = await test_single_engine_creation()
    
    if single_success:
        # Test concurrent creation
        concurrent_success = await test_concurrent_engine_creation()
        
        if concurrent_success:
            print("\n PASS:  All tests passed - isolation working correctly")
        else:
            print("\n FAIL:  Concurrent isolation test failed")
    else:
        print("\n FAIL:  Basic engine creation failed - check dependencies")


if __name__ == "__main__":
    asyncio.run(main())