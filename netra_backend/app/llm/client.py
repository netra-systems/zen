"""Circuit breaker-enabled LLM client for reliable AI operations.

This module provides backward compatibility imports for the refactored
modular LLM client components.
"""

# Import from the new modular structure for backward compatibility
from app.llm.client_config import LLMClientConfig
from app.llm.client_unified import ResilientLLMClient, RetryableUnifiedClient as RetryableLLMClient
from app.llm.client_factory import get_llm_client

# Re-export for backward compatibility
__all__ = [
    'LLMClientConfig',
    'ResilientLLMClient', 
    'RetryableLLMClient',
    'get_llm_client'
]

