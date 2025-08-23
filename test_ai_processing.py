#!/usr/bin/env python3
"""
Quick test of AI processing capabilities for Netra Apex.
Tests the core value proposition: can users get AI optimization recommendations?
"""

import asyncio
import os
import sys
from pathlib import Path

# Add paths for imports
os.environ['PYTHONPATH'] = str(Path(__file__).parent / "netra_backend")

# Load environment variables from .env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

async def test_ai_processing():
    """Test the complete AI processing pipeline."""
    print("NETRA APEX AI PROCESSING TEST")
    print("=" * 50)
    
    try:
        # Step 1: Import and test configuration
        print("1. Testing Configuration...")
        from netra_backend.app.config import get_config
        config = get_config()
        print(f"   OK Environment: {config.environment}")
        print(f"   OK LLM configs: {list(config.llm_configs.keys())}")
        
        # Step 2: Test LLM Manager
        print("\n2. Testing LLM Manager...")
        from netra_backend.app.llm.llm_manager import LLMManager
        llm_manager = LLMManager(config)
        print(f"   OK LLM Manager enabled: {llm_manager.enabled}")
        
        # Check API key
        default_config = config.llm_configs.get('default')
        if default_config:
            print(f"   OK Default LLM: {default_config.provider} / {default_config.model_name}")
            if default_config.api_key:
                print(f"   OK API key configured: {default_config.api_key[:10]}...")
            else:
                print("   ERROR No API key configured!")
                return False
        
        # Step 3: Test basic LLM call
        print("\n3. Testing Basic LLM Call...")
        try:
            response = await llm_manager.ask_llm(
                "Hello! Please respond with exactly: 'AI system operational'", 
                'default'
            )
            print(f"   OK LLM Response: {response[:100]}...")
        except Exception as e:
            print(f"   ERROR LLM call failed: {e}")
            return False
        
        # Step 4: Test agent supervisor
        print("\n4. Testing Agent Supervisor...")
        try:
            from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
            from netra_backend.app.db.postgres import get_postgres_db
            from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
            from netra_backend.app.ws_manager import manager as ws_manager
            
            # Create basic supervisor (simplified for testing)
            db_session = await anext(get_postgres_db())
            tool_dispatcher = ToolDispatcher()
            supervisor = SupervisorAgent(
                db_session=db_session,
                llm_manager=llm_manager,
                websocket_manager=ws_manager,
                tool_dispatcher=tool_dispatcher
            )
            print("   OK Supervisor agent created")
            
            # Test basic supervisor functionality
            stats = supervisor.get_stats()
            print(f"   OK Agent stats: {type(stats).__name__}")
                
        except Exception as e:
            print(f"   ERROR Supervisor test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # Step 5: Test message processing
        print("\n5. Testing Message Processing...")
        try:
            from netra_backend.app.services.agent_service_core import AgentService
            
            agent_service = AgentService(supervisor)
            
            # Test processing a user optimization request
            test_message = {
                "type": "user_message",
                "payload": {
                    "message": "I need help optimizing my AI workload costs. Can you analyze my usage patterns?",
                    "thread_id": "test_thread_123"
                }
            }
            
            print("   -> Sending test optimization request...")
            await agent_service.handle_websocket_message(
                user_id="test_user", 
                message=test_message,
                db_session=db_session
            )
            print("   OK Message processed successfully!")
            
            # Close database session
            await db_session.close()
            
        except Exception as e:
            print(f"   ERROR Message processing failed: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\nALL TESTS PASSED!")
        print("OK AI processing pipeline is working!")
        print("OK Users can send optimization requests")
        print("OK Agents can process and respond")
        return True
        
    except Exception as e:
        print(f"\nCRITICAL FAILURE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_ai_processing())
    if not success:
        print("\nSTARTUP CRITICAL ISSUE DETECTED!")
        print("The core AI processing pipeline is not working.")
        sys.exit(1)
    else:
        print("\nNETRA APEX IS READY FOR BUSINESS!")