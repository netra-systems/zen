"""Circuit breaker-enabled LLM client for reliable AI operations.

This module provides backward compatibility imports for the refactored
modular LLM client components.
"""

# Import from the new modular structure for backward compatibility
from netra_backend.app.llm.client_config import LLMClientConfig
from netra_backend.app.llm.client_factory import get_llm_client
from netra_backend.app.llm.client_unified import ResilientLLMClient
from netra_backend.app.llm.client_unified import (
    RetryableUnifiedClient as RetryableLLMClient,
)

# Re-export for backward compatibility
__all__ = [
    'LLMClientConfig',
    'ResilientLLMClient', 
    'RetryableLLMClient',
    'get_llm_client'
]

