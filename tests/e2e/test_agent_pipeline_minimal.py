"""
Minimal Agent Pipeline Test - Debug Version
Tests just the supervisor agent creation without complex dependencies.

This test validates basic supervisor agent functionality for e2e testing
with proper SSOT compliance and staging environment compatibility.
"""

import sys
import asyncio
import pytest
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import AsyncMock, MagicMock

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# SSOT Test Framework imports
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# SSOT compliant imports based on SSOT Import Registry
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.config import get_config
from netra_backend.app.websocket_core.canonical_import_patterns import WebSocketManager
from netra_backend.app.db.database_manager import DatabaseManager
from shared.isolated_environment import IsolatedEnvironment, get_env

# User execution context for proper isolation
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine

# Core types
from shared.types.core_types import UserID, ThreadID, RunID


class WebSocketConnectionTests:
    """Mock WebSocket connection for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.is_connected = True
        self._closed = False
        
    async def send_json(self, message: dict):
        """Send JSON message."""
        if self._closed:
            raise RuntimeError("WebSocket is closed")
        self.messages_sent.append(message)
        
    async def close(self, code: int = 1000, reason: str = "Normal closure"):
        """Close WebSocket connection."""
        self._closed = True
        self.is_connected = False
        
    def get_messages(self) -> list:
        """Get all sent messages."""
        return self.messages_sent.copy()


class AgentPipelineMinimalTests(SSotAsyncTestCase):
    """Minimal agent pipeline test using SSOT test framework."""
    
    def setup_method(self, method):
        """Set up test method with SSOT compliance."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()
        
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_supervisor_agent_creation_minimal(self):
        """Test that supervisor agent can be created successfully."""
        # Create required dependencies using SSOT patterns
        try:
            # Use test WebSocket connection
            test_websocket = WebSocketConnectionTests()
            
            # Get configuration
            config = get_config()
            
            # Create mocked dependencies using SSOT mock factory methods
            mock_db_session = self.mock_factory.create_database_session_mock()
            
            mock_llm_manager = self.mock_factory.create_mock_llm_manager(
                model="gpt-4",
                config={"temperature": 0.7}
            )
            
            mock_websocket_manager = self.mock_factory.create_websocket_manager_mock(
                manager_type="unified",
                user_isolation=True
            )
            mock_websocket_manager.get_connection.return_value = test_websocket
            
            # Create tool dispatcher mock using generic tool mock
            mock_tool_dispatcher = self.mock_factory.create_tool_mock(
                tool_name="dispatcher",
                execution_result={"status": "success", "result": "dispatched"}
            )
            
            # Create user execution context for proper isolation
            user_context = UserExecutionContext(
                user_id=UserID("test_user_123"),
                thread_id=ThreadID("test_thread_456"),
                run_id=RunID("test_run_789")
            )
            
            # Create supervisor agent with proper SSOT pattern
            supervisor = SupervisorAgent(
                llm_manager=mock_llm_manager,
                websocket_bridge=None,  # Using None for minimal test
                db_session_factory=mock_db_session,
                user_context=user_context,
                tool_dispatcher=mock_tool_dispatcher
            )
            
            # Basic validation
            assert supervisor is not None, "Supervisor agent should be created successfully"
            assert hasattr(supervisor, '_llm_manager'), "Supervisor should have _llm_manager attribute"
            assert hasattr(supervisor, 'websocket_bridge'), "Supervisor should have websocket_bridge attribute"
            assert hasattr(supervisor, 'agent_factory'), "Supervisor should have agent_factory attribute"
            
            # Verify proper initialization
            print(f"✅ Supervisor agent created successfully")
            print(f"📊 Supervisor type: {type(supervisor).__name__}")
            
            # Test basic agent properties
            assert supervisor._llm_manager is not None, "LLM manager should be set"
            assert supervisor.agent_factory is not None, "Agent factory should be set"
            assert supervisor._initialization_user_context is not None, "User context should be set"
            
            print(f"✅ All supervisor agent attributes validated successfully")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            print(f"📝 Error type: {type(e).__name__}")
            raise


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_supervisor_agent_creation_standalone():
    """Standalone test function for direct execution."""
    test_instance = AgentPipelineMinimalTests()
    test_instance.setup_method(test_supervisor_agent_creation_standalone)
    await test_instance.test_supervisor_agent_creation_minimal()


if __name__ == "__main__":
    # Direct execution support for debugging
    asyncio.run(test_supervisor_agent_creation_standalone())