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
            print(f"SUCCESS: Successfully created engine: {engine.engine_id}")
            print(f"   User ID: {engine.context.user_id}")
            print(f"   Run ID: {engine.context.run_id}")
            return True
            
    except Exception as e:
        print(f"ERROR: Engine creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main debug function."""
    print("Debug: Concurrent User Isolation Issues")
    print("=" * 50)
    
    # Test single engine creation first
    single_success = await test_single_engine_creation()
    
    if single_success:
        print("\nSUCCESS: Basic engine creation works")
    else:
        print("\nERROR: Basic engine creation failed - check dependencies")


if __name__ == "__main__":
    asyncio.run(main())