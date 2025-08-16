"""
LLM Model Rebuilder - Resolves forward references after all models are defined.
Following Netra conventions with 300-line module limit.
"""

import logging

logger = logging.getLogger(__name__)


def rebuild_base_models():
    """Rebuild base LLM models to resolve forward references"""
    try:
        base_models = _import_base_models()
        _rebuild_base_model_list(base_models)
    except Exception as e:
        logger.warning(f"Base model rebuild failed: {e}")


def _import_base_models():
    """Import all base model classes."""
    from app.schemas.llm_types import (
        LLMMessage, LLMMetrics, LLMProviderStatus, LLMError,
        LLMHealthCheck, LLMConfigInfo, LLMManagerStats
    )
    return [LLMMessage, LLMMetrics, LLMProviderStatus, LLMError, 
            LLMHealthCheck, LLMConfigInfo, LLMManagerStats]


def _rebuild_base_model_list(models):
    """Rebuild all models in the provided list."""
    for model in models:
        model.model_rebuild()


def rebuild_response_models():
    """Rebuild response-related LLM models"""
    try:
        modules, response_models = _import_response_components()
        rebuild_ns = _create_combined_namespace(modules)
        _rebuild_response_model_list(response_models, rebuild_ns)
    except Exception as e:
        logger.warning(f"Response model rebuild failed: {e}")


def _import_response_components():
    """Import response model modules and classes."""
    import app.schemas.llm_types as llm_types
    import app.schemas.llm_request_types as request_types
    from app.schemas.llm_response_types import (
        LLMResponse, LLMStreamChunk, LLMCache, BatchLLMResponse
    )
    return (llm_types, request_types), [LLMResponse, LLMStreamChunk, LLMCache, BatchLLMResponse]


def _create_combined_namespace(modules):
    """Create combined namespace for forward reference resolution."""
    llm_types, request_types = modules
    return {**llm_types.__dict__, **request_types.__dict__}


def _rebuild_response_model_list(models, rebuild_ns):
    """Rebuild response models with namespace."""
    for model in models[:-1]:  # All except BatchLLMResponse
        model.model_rebuild(_types_namespace=rebuild_ns)
    models[-1].model_rebuild()  # BatchLLMResponse without namespace


def rebuild_request_models():
    """Rebuild request-related LLM models"""
    try:
        llm_types, request_models = _import_request_components()
        _rebuild_request_model_list(request_models, llm_types.__dict__)
    except Exception as e:
        logger.warning(f"Request model rebuild failed: {e}")


def _import_request_components():
    """Import request model modules and classes."""
    import app.schemas.llm_types as llm_types
    from app.schemas.llm_request_types import (
        LLMRequest, BatchLLMRequest, StructuredOutputSchema,
        LLMFunction, LLMTool
    )
    return llm_types, [LLMRequest, BatchLLMRequest, StructuredOutputSchema, LLMFunction, LLMTool]


def _rebuild_request_model_list(models, types_namespace):
    """Rebuild request models with proper context."""
    models[0].model_rebuild(_types_namespace=types_namespace)  # LLMRequest
    for model in models[1:]:  # Others without namespace
        model.model_rebuild()


def rebuild_config_models():
    """Rebuild configuration-related LLM models"""
    try:
        llm_types, config_models = _import_config_components()
        _rebuild_config_model_list(config_models, llm_types.__dict__)
    except Exception as e:
        logger.warning(f"Config model rebuild failed: {e}")


def _import_config_components():
    """Import config model modules and classes."""
    import app.schemas.llm_types as llm_types
    from app.schemas.llm_config_types import LLMConfig, LLMManagerConfig
    return llm_types, [LLMConfig, LLMManagerConfig]


def _rebuild_config_model_list(models, types_namespace):
    """Rebuild config models with types namespace."""
    for model in models:
        model.model_rebuild(_types_namespace=types_namespace)


def rebuild_all_llm_models():
    """Rebuild all LLM models to resolve forward references"""
    logger.debug("Starting LLM model rebuild process")
    _execute_all_rebuilds()
    logger.debug("LLM model rebuild process completed")


def _execute_all_rebuilds():
    """Execute all rebuild operations in sequence."""
    rebuild_base_models()
    rebuild_response_models()
    rebuild_request_models()
    rebuild_config_models()


# Do not auto-rebuild on import to avoid circular dependency issues
# Call rebuild_all_llm_models() explicitly when needed