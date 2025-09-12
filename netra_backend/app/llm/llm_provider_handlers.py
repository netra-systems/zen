"""LLM Provider Handlers Module

Handles provider-specific LLM initialization and configuration.
Each function must be  <= 8 lines as per module architecture requirements.
"""
from typing import Any, Dict, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app.schemas.llm_base_types import LLMProvider
from netra_backend.app.schemas.config import LLMConfig as GenerationConfig

logger = central_logger.get_logger(__name__)


def create_google_llm(model_name: str, api_key: str, 
                     generation_config: Dict[str, Any]) -> Any:
    """Create Google Gemini LLM instance."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=api_key,
        **generation_config
    )


def create_openai_llm(model_name: str, api_key: str, 
                     generation_config: Dict[str, Any]) -> Any:
    """Create OpenAI LLM instance."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model_name=model_name,
        api_key=api_key,
        **generation_config
    )


def create_anthropic_llm(model_name: str, api_key: str, 
                        generation_config: Dict[str, Any]) -> Any:
    """Create Anthropic LLM instance."""
    from langchain_anthropic import ChatAnthropic
    return ChatAnthropic(
        model=model_name,
        api_key=api_key,
        **generation_config
    )


def create_cohere_llm(model_name: str, api_key: str, 
                     generation_config: Dict[str, Any]) -> Any:
    """Create Cohere LLM instance."""
    from langchain_cohere import ChatCohere
    return ChatCohere(
        model=model_name,
        api_key=api_key,
        **generation_config
    )


def create_mistral_llm(model_name: str, api_key: str, 
                      generation_config: Dict[str, Any]) -> Any:
    """Create Mistral LLM instance."""
    from langchain_mistralai import ChatMistralAI
    return ChatMistralAI(
        model=model_name,
        api_key=api_key,
        **generation_config
    )


def create_vertexai_llm(model_name: str, api_key: str, 
                       generation_config: Dict[str, Any]) -> Any:
    """Create VertexAI LLM instance (uses Google Gemini)."""
    logger.info("Using Google Gemini for VertexAI provider")
    from langchain_google_genai import ChatGoogleGenerativeAI
    return ChatGoogleGenerativeAI(
        model=model_name,
        api_key=api_key,
        **generation_config
    )


def validate_provider_key(provider: LLMProvider, api_key: Optional[str]) -> bool:
    """Validate if API key is required for provider."""
    if not api_key:
        if provider in [LLMProvider.GOOGLE, LLMProvider.VERTEXAI]:
            return False
        logger.info(f"Skipping provider {provider.value} - no API key")
        return False
    return True


def _get_provider_handlers_map():
    """Get mapping of providers to their handler functions."""
    return {
        LLMProvider.GOOGLE: create_google_llm,
        LLMProvider.OPENAI: create_openai_llm,
        LLMProvider.ANTHROPIC: create_anthropic_llm,
        LLMProvider.COHERE: create_cohere_llm,
        LLMProvider.VERTEXAI: create_vertexai_llm,
        "mistral": create_mistral_llm
    }

def get_provider_handler(provider: LLMProvider):
    """Get provider-specific LLM creation handler."""
    handlers = _get_provider_handlers_map()
    return handlers.get(provider)


def create_llm_for_provider(provider: LLMProvider, model_name: str, 
                           api_key: str, generation_config: Dict[str, Any]) -> Optional[Any]:
    """Create LLM instance for specified provider."""
    handler = get_provider_handler(provider)
    if not handler:
        return _handle_unsupported_provider(provider)
    return handler(model_name, api_key, generation_config)

def _handle_unsupported_provider(provider: LLMProvider) -> None:
    """Handle unsupported provider error."""
    logger.warning(f"Unsupported provider: {provider}")
    return None