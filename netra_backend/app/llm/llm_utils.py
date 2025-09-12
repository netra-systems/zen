"""LLM utilities module.

Provides utility functions for logging, token extraction, and response processing.
Each function must be  <= 8 lines as per architecture requirements.
"""

from typing import Any, Dict, Optional

from netra_backend.app.llm.observability import log_llm_input, log_llm_output
from netra_backend.app.services.llm_cache_service import llm_cache_service


class LLMUtils:
    """Utility functions for LLM operations."""
    
    @staticmethod
    def log_llm_input_data(agent_name: str, correlation_id: str, prompt: str, llm: Any) -> None:
        """Log LLM input data for debugging."""
        params = LLMUtils._extract_llm_params(llm)
        log_llm_input(agent_name, correlation_id, prompt, params)

    @staticmethod
    def log_llm_output_data(agent_name: str, correlation_id: str, response: Any, llm_response: Any) -> None:
        """Log LLM output data for debugging."""
        response_content = LLMUtils._extract_response_content(response)
        token_count = LLMUtils._extract_token_count_from_response(response, llm_response)
        log_llm_output(agent_name, correlation_id, response_content, token_count)

    @staticmethod
    def _extract_llm_params(llm: Any) -> Dict[str, Any]:
        """Extract parameters from LLM instance."""
        params = {}
        if hasattr(llm, 'model_name'):
            params['model'] = llm.model_name
        if hasattr(llm, 'temperature'):
            params['temperature'] = llm.temperature
        return params

    @staticmethod
    def _extract_response_content(response: Any) -> str:
        """Extract content from LLM response."""
        if hasattr(response, 'content'):
            return response.content
        if isinstance(response, str):
            return response
        return str(response)

    @staticmethod
    def _extract_token_count_from_response(response: Any, llm_response: Any) -> Optional[int]:
        """Extract token count from LLM response."""
        if hasattr(llm_response, 'token_count') and llm_response.token_count:
            return llm_response.token_count
        if hasattr(response, 'response_metadata'):
            metadata = response.response_metadata
            if isinstance(metadata, dict):
                return metadata.get('token_usage', {}).get('total_tokens')
        return None

    @staticmethod
    async def cache_response_if_needed(use_cache: bool, prompt: str, 
                                     response_content: str, llm_config_name: str) -> None:
        """Cache response if caching is enabled."""
        if use_cache:
            await llm_cache_service.cache_response(prompt, response_content, llm_config_name)