#!/usr/bin/env python
"""Debug script to test supervisor configuration issues."""

import asyncio
import os
import sys

# Set up environment before any imports
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
# Use central config manager per database_connectivity_architecture.xml
os.environ["USE_MEMORY_DB"] = "true"  # Tell DatabaseURLBuilder to use SQLite memory
os.environ["CLICKHOUSE_URL"] = "http://localhost:8123/test"
os.environ["CLICKHOUSE_HOST"] = "localhost"
os.environ["CLICKHOUSE_ENABLED"] = "false"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"
os.environ["NETRA_REAL_LLM_ENABLED"] = "false"
os.environ["USE_REAL_LLM"] = "false"
os.environ["TEST_LLM_MODE"] = "mock"

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print(f"Python path: {sys.path[0]}")
print(f"Testing environment vars:")
print(f"  DATABASE_URL: {os.environ.get('DATABASE_URL')}")
print(f"  CLICKHOUSE_URL: {os.environ.get('CLICKHOUSE_URL')}")
print(f"  USE_REAL_LLM: {os.environ.get('USE_REAL_LLM')}")

try:
    from netra_backend.app.config import get_config
    print("[OK] Config import successful")
    config = get_config()
    print(f"[OK] Config loaded: {type(config).__name__}")
    print(f"  Database URL: {getattr(config, 'database_url', 'Not set')}")
    print(f"  ClickHouse URL: {getattr(config, 'clickhouse_url', 'Not set')}")
except Exception as e:
    print(f"[ERROR] Config error: {e}")
    import traceback
    traceback.print_exc()

try:
    from netra_backend.app.llm.llm_manager import LLMManager
    print("[OK] LLM Manager import successful")
    llm_manager = LLMManager(config)
    print("[OK] LLM Manager created successfully")
except Exception as e:
    print(f"[ERROR] LLM Manager error: {e}")
    import traceback
    traceback.print_exc()

try:
    from netra_backend.app.db.session import DatabaseSessionManager
    print("[OK] Database Session Manager import successful")
    db_manager = DatabaseSessionManager()
    print("[OK] Database Session Manager created successfully")
except Exception as e:
    print(f"[ERROR] Database Session Manager error: {e}")
    import traceback
    traceback.print_exc()

try:
    from netra_backend.app.websocket_core.manager import WebSocketManager
    print("[OK] WebSocket Manager import successful")
    ws_manager = WebSocketManager()
    print("[OK] WebSocket Manager created successfully")
except Exception as e:
    print(f"[ERROR] WebSocket Manager error: {e}")
    import traceback
    traceback.print_exc()

try:
    from netra_backend.app.agents.tool_dispatcher_core import ToolDispatcher
    print("[OK] Tool Dispatcher import successful")
    dispatcher = ToolDispatcher()
    print("[OK] Tool Dispatcher created successfully")
except Exception as e:
    print(f"[ERROR] Tool Dispatcher error: {e}")
    import traceback
    traceback.print_exc()

async def test_supervisor():
    """Test supervisor creation and basic functionality."""
    try:
        # Create supervisor with all dependencies
        async with db_manager.get_session() as db_session:
            from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
            print("[OK] Supervisor import successful")
            
            supervisor = SupervisorAgent(
                db_session,
                llm_manager,
                ws_manager,
                dispatcher
            )
            print("[OK] Supervisor created successfully")
            
            # Test basic functionality
            health = supervisor.get_health_status()
            print(f"[OK] Health status retrieved: {type(health)}")
            
            # Test simple state
            from netra_backend.app.agents.state import DeepAgentState
            state = DeepAgentState()
            state.user_request = "Test request"
            state.user_id = "test_user"
            state.chat_thread_id = "test_thread"
            
            # Try to execute
            print("Attempting supervisor execution...")
            try:
                await supervisor.execute(state, "test_run", stream_updates=False)
                print("[OK] Supervisor execution completed successfully")
            except Exception as e:
                print(f"[ERROR] Supervisor execution error: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"[ERROR] Supervisor error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if 'db_manager' in locals():
        asyncio.run(test_supervisor())
    else:
        print("Cannot run supervisor test due to dependency errors")