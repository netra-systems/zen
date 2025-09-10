#!/usr/bin/env python3
"""
Minimal test to reproduce supervisor agent instance creation failure.
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath('.'))

# Set environment for testing
os.environ['ENVIRONMENT'] = 'testing'

# Enable logging to see the actual errors
import logging
logging.basicConfig(level=logging.ERROR, format='%(levelname)s: %(message)s')

# Enable the specific loggers we need to see errors
logging.getLogger('netra_backend.app.agents.supervisor_consolidated').setLevel(logging.ERROR)
logging.getLogger('netra_backend.app.agents.supervisor.agent_instance_factory').setLevel(logging.ERROR)

async def test_supervisor_agent_creation():
    """Test the exact supervisor method that's failing."""
    print("Testing supervisor agent creation...")
    
    try:
        from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
        from netra_backend.app.services.user_execution_context import UserExecutionContext
        from netra_backend.app.llm.llm_manager import LLMManager
        from shared.id_generation import UnifiedIdGenerator
        
        print("Imports successful")
        
        # Create a minimal supervisor like the factory does
        llm_manager = LLMManager()
        supervisor = SupervisorAgent(
            llm_manager=llm_manager,
            websocket_bridge=None,  # This might be the issue
            db_session_factory=None,
            user_context=None
        )
        
        print("Supervisor created")
        
        # Manually configure the factory since execute() isn't being called
        print("Configuring factory manually...")
        supervisor.agent_instance_factory.configure(
            agent_class_registry=supervisor.agent_class_registry,
            websocket_bridge=None,  # This should now be allowed
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
        
        print("User context created")
        
        # Test the internal method that's failing
        try:
            agent_instances = await supervisor._create_isolated_agent_instances(user_context)
            print(f"SUCCESS: Created {len(agent_instances)} agent instances")
            return True
        except Exception as e:
            print(f"FAILED: {e}")
            raise
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    success = await test_supervisor_agent_creation()
    print(f"Test result: {'SUCCESS' if success else 'FAILED'}")
    return 0 if success else 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except Exception as e:
        print(f"Test failed: {e}")
        sys.exit(1)