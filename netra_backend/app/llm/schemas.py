"""LLM Schema Re-exports.

Provides convenient access to LLM-related schema types from their canonical locations.
This module acts as a single import point for commonly used LLM schemas.
"""

# Re-export request types
from netra_backend.app.schemas.llm_request_types import (
    LLMRequest,
    BatchLLMRequest,
    StructuredOutputSchema,
    LLMFunction,
    LLMTool
)

# Re-export response types  
from netra_backend.app.schemas.llm_response_types import (
    LLMResponse,
    LLMStreamChunk,
    BatchLLMResponse,
    LLMCache
)

# Re-export core types
from netra_backend.app.schemas.llm_types import (
    LLMProvider,
    LLMModel,
    LLMRole,
    TokenUsage,
    LLMMessage,
    LLMMetrics,
    LLMProviderStatus,
    LLMError,
    LLMHealthCheck,
    LLMConfigInfo,
    LLMManagerStats,
    GenerationConfig
)

# Re-export config types
from netra_backend.app.schemas.llm_config_types import (
    LLMConfig,
    LLMManagerConfig,
    CostMetrics,
    LatencyMetrics,
    UsageMetrics
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