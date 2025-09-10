#!/usr/bin/env python3
"""
Test each agent individually to understand constructor patterns.
"""

import asyncio
import sys
import os
import traceback

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Set environment for testing
os.environ['ENVIRONMENT'] = 'testing'

async def test_each_agent():
    """Test each agent individually to see which ones work."""
    print("Testing each agent individually...")
    
    try:
        from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
        from netra_backend.app.agents.supervisor.agent_class_initialization import initialize_agent_class_registry
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from shared.id_generation import UnifiedIdGenerator
        
        print("Imports successful")
        
        # Initialize agent class registry
        print("\n1. Initializing agent class registry...")
        registry = initialize_agent_class_registry()
        print(f"Registry size: {len(registry)}")
        
        # Create factory and configure
        print("\n2. Configuring factory...")
        factory = get_agent_instance_factory()
        llm_manager = LLMManager()
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=None,
            websocket_manager=None,
            llm_manager=llm_manager,
            tool_dispatcher=None
        )
        print("Factory configured")
        
        # Create user context
        user_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=UnifiedIdGenerator.generate_base_id("run"),
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id="test_client"
        )
        
        # Test each agent the supervisor tries to create
        agent_names = ["triage", "reporting", "data_helper", "data", "optimization", "actions", "goals_triage", "synthetic_data"]
        
        results = {}
        for agent_name in agent_names:
            print(f"\n3. Testing {agent_name}...")
            try:
                agent_instance = await factory.create_agent_instance(
                    agent_name=agent_name,
                    user_context=user_context
                )
                results[agent_name] = "SUCCESS"
                print(f"   SUCCESS: {type(agent_instance).__name__}")
                
            except Exception as e:
                results[agent_name] = str(e)
                print(f"   FAILED: {e}")
                
        # Summary
        print(f"\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        successes = [name for name, result in results.items() if result == "SUCCESS"]
        failures = [(name, result) for name, result in results.items() if result != "SUCCESS"]
        
        print(f"✓ Successes ({len(successes)}): {successes}")
        print(f"✗ Failures ({len(failures)}):")
        for name, error in failures:
            print(f"   - {name}: {error}")
            
        return len(successes) > 0
            
    except Exception as e:
        print(f"ERROR in test setup: {e}")
        traceback.print_exc()
        return False

async def main():
    success = await test_each_agent()
    print(f"\nTest result: {'SUCCESS' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)