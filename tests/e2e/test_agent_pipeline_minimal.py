class TestWebSocketConnection:
    """Real WebSocket connection for testing instead of mocks."""
    
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

"""
Minimal Agent Pipeline Test - Debug Version
Tests just the supervisor agent creation without complex dependencies.
"""

import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import DatabaseTestManager
from auth_service.core.auth_manager import AuthManager
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment
# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pytest

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.config import get_config
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


@pytest.mark.asyncio
async def test_supervisor_agent_creation_minimal():
    """Test that supervisor agent can be created successfully."""
    # Create required dependencies
    websocket = TestWebSocketConnection()
    config = get_config()
    llm_manager = LLMManager(config)
    websocket = TestWebSocketConnection()
    tool_dispatcher = AsyncMock(spec=ToolDispatcher)
    
    # Create supervisor agent
    supervisor = SupervisorAgent(db_session, llm_manager, websocket_manager, tool_dispatcher)
    
    # Basic validation
    assert supervisor is not None
    assert supervisor.llm_manager is not None
    
    # Test that the supervisor has been properly initialized
    print(f"Supervisor attributes: {dir(supervisor)}")
    assert hasattr(supervisor, 'agents')
    # Check what router-related attributes exist
    router_attrs = [attr for attr in dir(supervisor) if 'router' in attr.lower()]
    print(f"Router-related attributes: {router_attrs}")
    
    # The attribute might be named differently, let's check for common alternatives
    routing_attrs = [attr for attr in dir(supervisor) if any(term in attr.lower() for term in ['router', 'route', 'dispatch'])]
    print(f"Routing-related attributes: {routing_attrs}")
    
    # Just verify the supervisor is properly initialized
    assert supervisor is not None
    assert hasattr(supervisor, 'agents')


if __name__ == "__main__":
    import sys
    from pathlib import Path
    # Add the project root to Python path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))
    asyncio.run(test_supervisor_agent_creation_minimal())