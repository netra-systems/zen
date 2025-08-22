"""LLM Schema Re-exports.

Provides convenient access to LLM-related schema types from their canonical locations.
This module acts as a single import point for commonly used LLM schemas.
"""

# Re-export request types
# Re-export config types
from netra_backend.app.schemas.llm_config_types import (
    CostMetrics,
    LatencyMetrics,
    LLMConfig,
    LLMManagerConfig,
    UsageMetrics,
)
from netra_backend.app.schemas.llm_request_types import (
    BatchLLMRequest,
    LLMFunction,
    LLMRequest,
    LLMTool,
    StructuredOutputSchema,
)

# Re-export response types  
from netra_backend.app.schemas.llm_response_types import (
    BatchLLMResponse,
    LLMCache,
    LLMResponse,
    LLMStreamChunk,
)

# Re-export core types
from netra_backend.app.schemas.llm_types import (
    GenerationConfig,
    LLMConfigInfo,
    LLMError,
    LLMHealthCheck,
    LLMManagerStats,
    LLMMessage,
    LLMMetrics,
    LLMModel,
    LLMProvider,
    LLMProviderStatus,
    LLMRole,
    TokenUsage,
)

# Commonly used type aliases for backward compatibility
LLMCacheEntry = LLMCache
StructuredLLMResponse = LLMResponse

__all__ = [
    # Request types
    "LLMRequest", "BatchLLMRequest", "StructuredOutputSchema", 
    "LLMFunction", "LLMTool",
    
    # Response types
    "LLMResponse", "LLMStreamChunk", "BatchLLMResponse", 
    "LLMCache",
    
    # Core types
    "LLMProvider", "LLMModel", "LLMRole", "TokenUsage", "LLMMessage",
    "LLMMetrics", "LLMProviderStatus", "LLMError", "LLMHealthCheck",
    "LLMConfigInfo", "LLMManagerStats", "GenerationConfig",
    
    # Config types
    "LLMConfig", "LLMManagerConfig", "CostMetrics", 
    "LatencyMetrics", "UsageMetrics",
    
    # Aliases
    "LLMCacheEntry", "StructuredLLMResponse"
]