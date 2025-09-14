"""
REMEDIATION FIX: LLM Providers - Compatibility Module for Issue #861

This module was missing and causing integration test import failures.
It provides backward compatibility for tests expecting llm_providers imports.

The actual LLM implementation is in the 'llm' folder, which contains the SSOT version.
This module simply re-exports the LLM classes to maintain test compatibility.

Business Value:
- Segment: All - $500K+ ARR Protection
- Goal: Enable integration test execution
- Impact: Fixes missing llm_providers import failures
- Revenue Impact: Prevents test infrastructure gaps from blocking deployment
"""

# Re-export key LLM classes from the actual implementation
from netra_backend.app.llm.llm_manager import LLMManager
from netra_backend.app.llm.llm_provider_handlers import (
    LLMProviderHandler,
    OpenAIHandler,
    AnthropicHandler,
    GeminiHandler
)
from netra_backend.app.llm.llm_operations import LLMOperations
from netra_backend.app.llm.llm_response_processing import LLMResponseProcessor
from netra_backend.app.llm.client import LLMClient
from netra_backend.app.llm.client_factory import LLMClientFactory

# Backward compatibility aliases for tests that might expect different names
LLMProvider = LLMManager  # Some tests might use this name
LLMProviderManager = LLMManager

# Export all the classes tests might expect
__all__ = [
    'LLMManager',
    'LLMProvider',
    'LLMProviderManager',
    'LLMProviderHandler',
    'OpenAIHandler',
    'AnthropicHandler',
    'GeminiHandler',
    'LLMOperations',
    'LLMResponseProcessor',
    'LLMClient',
    'LLMClientFactory'
]