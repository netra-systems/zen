"""
LLM Model Rebuilder - Resolves forward references after all models are defined.
Following Netra conventions with 300-line module limit.
"""

import logging

logger = logging.getLogger(__name__)


def rebuild_base_models():
    """Rebuild base LLM models to resolve forward references"""
    try:
        from app.schemas.llm_types import (
            LLMMessage, LLMMetrics, LLMProviderStatus, LLMError,
            LLMHealthCheck, LLMConfigInfo, LLMManagerStats
        )
        
        LLMMessage.model_rebuild()
        LLMMetrics.model_rebuild()
        LLMProviderStatus.model_rebuild()
        LLMError.model_rebuild()
        LLMHealthCheck.model_rebuild()
        LLMConfigInfo.model_rebuild()
        LLMManagerStats.model_rebuild()
        
    except Exception as e:
        logger.warning(f"Base model rebuild failed: {e}")


def rebuild_response_models():
    """Rebuild response-related LLM models"""
    try:
        # Import all modules to ensure all types are available
        import app.schemas.llm_types as llm_types
        import app.schemas.llm_request_types as request_types
        from app.schemas.llm_response_types import (
            LLMResponse, LLMStreamChunk, LLMCache,
            BatchLLMResponse
        )
        
        # Combine namespace for forward reference resolution
        rebuild_ns = {**llm_types.__dict__, **request_types.__dict__}
        
        LLMResponse.model_rebuild(_types_namespace=rebuild_ns)
        LLMStreamChunk.model_rebuild(_types_namespace=rebuild_ns)
        LLMCache.model_rebuild(_types_namespace=rebuild_ns)
        BatchLLMResponse.model_rebuild()
        
    except Exception as e:
        logger.warning(f"Response model rebuild failed: {e}")


def rebuild_request_models():
    """Rebuild request-related LLM models"""
    try:
        # Import both modules to ensure all types are available
        import app.schemas.llm_types as llm_types
        from app.schemas.llm_request_types import (
            LLMRequest, BatchLLMRequest, StructuredOutputSchema,
            LLMFunction, LLMTool
        )
        
        # Rebuild with proper context
        LLMRequest.model_rebuild(_types_namespace=llm_types.__dict__)
        BatchLLMRequest.model_rebuild()
        StructuredOutputSchema.model_rebuild()
        LLMFunction.model_rebuild()
        LLMTool.model_rebuild()
        
    except Exception as e:
        logger.warning(f"Request model rebuild failed: {e}")


def rebuild_config_models():
    """Rebuild configuration-related LLM models"""
    try:
        # Import types module to resolve forward references
        import app.schemas.llm_types as llm_types
        from app.schemas.llm_config_types import (
            LLMConfig, LLMManagerConfig
        )
        
        LLMConfig.model_rebuild(_types_namespace=llm_types.__dict__)
        LLMManagerConfig.model_rebuild(_types_namespace=llm_types.__dict__)
        
    except Exception as e:
        logger.warning(f"Config model rebuild failed: {e}")


def rebuild_all_llm_models():
    """Rebuild all LLM models to resolve forward references"""
    logger.debug("Starting LLM model rebuild process")
    
    rebuild_base_models()
    rebuild_response_models()
    rebuild_request_models()
    rebuild_config_models()
    
    logger.debug("LLM model rebuild process completed")


# Do not auto-rebuild on import to avoid circular dependency issues
# Call rebuild_all_llm_models() explicitly when needed