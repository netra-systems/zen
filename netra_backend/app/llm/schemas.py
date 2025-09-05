"""LLM Schema Re-exports.

Provides convenient access to LLM-related schema types from their canonical locations.
This module acts as a single import point for commonly used LLM schemas.
"""

# Re-export request types
# Re-export config types from llm_config_types
from netra_backend.app.schemas.llm_config_types import (
    UsageMetrics,
)

# Re-export metrics types from llm_types
from netra_backend.app.schemas.llm_types import (
    CostMetrics,
    LatencyMetrics,
)

# Re-export config from config.py
from netra_backend.app.schemas.config import LLMConfig
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
    LLMHealthCheck,
    LLMManagerStats,
    LLMMetrics,
    LLMProvider,
    LLMProviderStatus,
    LLMValidationError,
    TokenUsage,
)

# Re-export LLMConfigInfo from config_types (canonical location)  
from netra_backend.app.schemas.config_types import LLMConfigInfo

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
    "LLMProvider", "TokenUsage", 
    "LLMMetrics", "LLMProviderStatus", "LLMValidationError", "LLMHealthCheck",
    "LLMConfigInfo", "LLMManagerStats", "GenerationConfig",
    
    # Config types
    "LLMConfig", "CostMetrics", 
    "LatencyMetrics", "UsageMetrics",
    
    # Aliases
    "LLMCacheEntry", "StructuredLLMResponse"
]