"""Agent service backward compatibility functions.

Provides module-level functions for backward compatibility with existing
tests and code that depends on the legacy API.
"""

from typing import Any, AsyncGenerator, Dict, Optional

from netra_backend.app.config import get_config
settings = get_config()
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.services.agent_service_factory import get_agent_service


async def process_message(message: str, thread_id: Optional[str] = None) -> Dict[str, Any]:
    """Module-level wrapper for AgentService.process_message for test compatibility"""
    from netra_backend.app.dependencies import get_request_scoped_db_session, get_llm_manager
    async for db in get_request_scoped_db_session():
        return await _execute_module_process_message(db, message, thread_id)


async def _execute_module_process_message(db, message: str, thread_id: Optional[str]) -> Dict[str, Any]:
    """Execute module-level message processing."""
    llm_manager = get_llm_manager()
    agent_service = get_agent_service(db, llm_manager)
    return await agent_service.process_message(message, thread_id)


async def generate_stream(message: str, thread_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
    """Module-level wrapper for AgentService.generate_stream for test compatibility"""
    from netra_backend.app.dependencies import get_request_scoped_db_session
    async for db in get_request_scoped_db_session():
        async for chunk in _execute_module_generate_stream(db, message, thread_id):
            yield chunk


async def _execute_module_generate_stream(db, message: str, thread_id: Optional[str]) -> AsyncGenerator[Dict[str, Any], None]:
    """Execute module-level stream generation."""
    from netra_backend.app.llm.llm_manager import create_llm_manager
    llm_manager = create_llm_manager(None)  # Compatibility layer without user context
    agent_service = get_agent_service(db, llm_manager)
    async for chunk in agent_service.generate_stream(message, thread_id):
        yield chunk