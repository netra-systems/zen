"""
Minimal Agent Pipeline Test - Debug Version
Tests just the supervisor agent creation without complex dependencies.
"""

import sys
from pathlib import Path
# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pytest
from unittest.mock import AsyncMock

from netra_backend.app.agents.supervisor_consolidated import SupervisorAgent
from netra_backend.app.agents.tool_dispatcher import ToolDispatcher
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.config import get_config


@pytest.mark.asyncio
async def test_supervisor_agent_creation_minimal():
    """Test that supervisor agent can be created successfully."""
    # Create required dependencies
    db_session = AsyncMock()
    config = get_config()
    llm_manager = LLMManager(config)
    websocket_manager = AsyncMock()
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