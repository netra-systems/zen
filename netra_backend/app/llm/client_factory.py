"""LLM client factory and context managers.

Provides factory functions for creating LLM clients
and context managers for proper resource management.
"""

from contextlib import asynccontextmanager
from netra_backend.app.llm.client_core import LLMCoreClient
from netra_backend.app.llm.client_retry import RetryableLLMClient
from netra_backend.app.llm.llm_manager import LLMManager


def _create_client_instance(llm_manager: LLMManager, with_retry: bool) -> LLMCoreClient:
    """Create appropriate LLM client instance."""
    if with_retry:
        return RetryableLLMClient(llm_manager)
    return LLMCoreClient(llm_manager)


def _perform_client_cleanup(client: LLMCoreClient) -> None:
    """Perform client cleanup operations."""
    # Cleanup if needed
    pass


@asynccontextmanager
async def get_llm_client(llm_manager: LLMManager, with_retry: bool = False):
    """Context manager for getting LLM client with cleanup."""
    client = _create_client_instance(llm_manager, with_retry)
    
    try:
        yield client
    finally:
        _perform_client_cleanup(client)