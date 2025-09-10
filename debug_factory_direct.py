#!/usr/bin/env python3
"""
Direct test of the agent instance factory to see what's going wrong.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Set environment for testing
os.environ['ENVIRONMENT'] = 'testing'

async def test_factory_direct():
    """Test the factory directly."""
    print("Testing agent instance factory directly...")
    
    try:
        from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
        from netra_backend.app.agents.supervisor.agent_class_registry import get_agent_class_registry
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from shared.id_generation import UnifiedIdGenerator
        
        print("Imports successful")
        
        # Initialize agent class registry
        print("\n1. Initializing agent class registry...")
        from netra_backend.app.agents.supervisor.agent_class_initialization import initialize_agent_class_registry
        registry = initialize_agent_class_registry()
        print(f"Registry agents: {registry.list_agent_names()}")
        print(f"Registry frozen: {registry.is_frozen()}")
        print(f"Registry size: {len(registry)}")
        
        # Get factory
        print("\n2. Getting factory...")
        factory = get_agent_instance_factory()
        print(f"Factory created: {factory}")
        
        # Configure factory
        print("\n3. Configuring factory...")
        llm_manager = LLMManager()
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=None,  # Should be allowed now
            websocket_manager=None,
            llm_manager=llm_manager,
            tool_dispatcher=None
        )
        print("Factory configured")
        
        # Create user context
        print("\n4. Creating user context...")
        user_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=UnifiedIdGenerator.generate_base_id("run"),
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id="test_client"
        )
        print("User context created")
        
        # Test creating one agent
        print("\n5. Testing single agent creation...")
        test_agent = "triage"  # Start with triage
        
        try:
            print(f"Creating {test_agent}...")
            agent_instance = await factory.create_agent_instance(
                agent_name=test_agent,
                user_context=user_context
            )
            print(f"SUCCESS: Created {test_agent}: {type(agent_instance).__name__}")
            return True
            
        except Exception as e:
            print(f"FAILED to create {test_agent}: {e}")
            # Print the full traceback
            import traceback
            traceback.print_exc()
            return False
            
    except Exception as e:
        print(f"ERROR in test setup: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_factory_direct()
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)