#!/usr/bin/env python3
"""
Debug script to reproduce the agent instance creation failure.
This script will help identify the exact issue causing "Failed to create any isolated agent instances".
"""

import asyncio
import sys
import traceback
from typing import Dict, Any

# Add project root to path
import os
sys.path.insert(0, os.path.abspath('.'))

# Set environment for testing
os.environ['ENVIRONMENT'] = 'testing'

# Fix Windows console encoding - careful not to conflict with other modules
if sys.platform == 'win32' and hasattr(sys.stdout, 'buffer'):
    import codecs
    try:
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)
    except AttributeError:
        pass  # Already modified by another module

async def test_agent_creation():
    """Test agent instance creation to debug the failure."""
    print("=" * 60)
    print("TESTING AGENT INSTANCE CREATION")
    print("=" * 60)
    
    try:
        # Import required modules
        from netra_backend.app.agents.supervisor.agent_class_initialization import initialize_agent_class_registry
        from netra_backend.app.agents.supervisor.agent_instance_factory import get_agent_instance_factory
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
        from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
        from shared.id_generation import UnifiedIdGenerator
        
        print("OK All imports successful")
        
        # Step 1: Initialize agent class registry
        print("\n1. Initializing agent class registry...")
        registry = initialize_agent_class_registry()
        print(f"OK Registry initialized with {len(registry)} agents: {registry.list_agent_names()}")
        
        # Step 2: Create LLM manager
        print("\n2. Creating LLM manager...")
        llm_manager = LLMManager()
        print(f"OK LLM manager created: {llm_manager}")
        
        # Step 3: Create WebSocket bridge (mock for testing)
        print("\n3. Creating WebSocket bridge...")
        try:
            websocket_manager = UnifiedWebSocketManager()
            websocket_bridge = AgentWebSocketBridge(websocket_manager)
            print(f"OK WebSocket bridge created: {websocket_bridge}")
        except Exception as e:
            print(f"WARN WebSocket bridge creation failed (non-critical for test): {e}")
            websocket_bridge = None
        
        # Step 4: Configure agent instance factory
        print("\n4. Configuring agent instance factory...")
        factory = get_agent_instance_factory()
        factory.configure(
            agent_class_registry=registry,
            websocket_bridge=websocket_bridge,
            websocket_manager=websocket_manager if websocket_bridge else None,
            llm_manager=llm_manager,
            tool_dispatcher=None  # Will be created per-request
        )
        print("OK Factory configured")
        
        # Step 5: Create user execution context
        print("\n5. Creating user execution context...")
        user_context = UserExecutionContext(
            user_id="test_user",
            thread_id="test_thread",
            run_id=UnifiedIdGenerator.generate_base_id("run"),
            request_id=UnifiedIdGenerator.generate_base_id("req"),
            websocket_client_id="test_client"
        )
        print(f"OK User context created: {user_context.user_id}")
        
        # Step 6: Test creating each agent individually
        print("\n6. Testing individual agent creation...")
        agent_names = ["triage", "reporting", "data_helper", "data", "optimization", "actions", "goals_triage", "synthetic_data"]
        
        created_agents = {}
        failed_agents = {}
        
        for agent_name in agent_names:
            try:
                print(f"\n   Testing {agent_name}...")
                agent_instance = await factory.create_agent_instance(
                    agent_name=agent_name,
                    user_context=user_context
                )
                created_agents[agent_name] = agent_instance
                print(f"   OK {agent_name} created successfully: {type(agent_instance).__name__}")
                
            except Exception as e:
                failed_agents[agent_name] = str(e)
                print(f"   FAIL {agent_name} failed: {e}")
                print(f"      Error type: {type(e).__name__}")
                traceback.print_exc()
        
        # Summary
        print(f"\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"OK Successfully created: {len(created_agents)} agents")
        for name in created_agents:
            print(f"   - {name}")
            
        print(f"\nFAIL Failed to create: {len(failed_agents)} agents")
        for name, error in failed_agents.items():
            print(f"   - {name}: {error}")
        
        if len(created_agents) == 0:
            print("\nCRITICAL: No agents could be created - this explains the supervisor error!")
            return False
        else:
            print(f"\nSUCCESS: {len(created_agents)}/{len(agent_names)} agents created successfully")
            return True
            
    except Exception as e:
        print(f"\nCRITICAL ERROR during test setup: {e}")
        traceback.print_exc()
        return False

async def main():
    """Main test function."""
    success = await test_agent_creation()
    print(f"\nTest completed. Success: {success}")
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nTest failed with exception: {e}")
        traceback.print_exc()
        sys.exit(1)