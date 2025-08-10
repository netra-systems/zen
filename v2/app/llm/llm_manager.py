from typing import Any, Dict, Optional
from app.schemas import AppConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from app.services.llm_cache_service import llm_cache_service
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

class LLMManager:
    def __init__(self, settings: AppConfig):
        self.settings = settings
        self._llm_cache: Dict[str, Any] = {}

    def get_llm(self, name: str, generation_config: Optional[Dict[str, Any]] = None) -> Any:
        cache_key = name
        if generation_config:
            # Create a unique cache key for this combination of name and generation_config
            cache_key += str(sorted(generation_config.items()))

        if cache_key in self._llm_cache:
            return self._llm_cache[cache_key]

        config = self.settings.llm_configs.get(name)
        if not config:
            raise ValueError(f"LLM configuration for '{name}' not found.")

        # Merge the default generation config with the override
        final_generation_config = config.generation_config.copy()
        if generation_config:
            final_generation_config.update(generation_config)

        if config.provider == "google":
            if not config.api_key:
                raise ValueError(f"LLM '{name}': API key for provider 'google' is missing. Check Auth Refresh expires every 16 hours (e.g. gcloud auth application-default login)")

            # Defer genai.configure until a Google model is actually used
            llm = ChatGoogleGenerativeAI(
                model=config.model_name,
                api_key=config.api_key,
                **final_generation_config
            )
        elif config.provider == "openai":
            llm = ChatOpenAI(
                model_name=config.model_name,
                api_key=config.api_key,
                **final_generation_config,
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

        self._llm_cache[cache_key] = llm
        return llm

    async def ask_llm(self, prompt: str, llm_config_name: str, use_cache: bool = True) -> str:
        # Check cache first if enabled
        if use_cache:
            cached_response = await llm_cache_service.get_cached_response(prompt, llm_config_name)
            if cached_response:
                return cached_response
        
        # Make LLM call
        llm = self.get_llm(llm_config_name)
        response = await llm.ainvoke(prompt)
        response_content = response.content
        
        # Cache the response if appropriate
        if use_cache and llm_cache_service.should_cache_response(prompt, response_content):
            await llm_cache_service.cache_response(prompt, response_content, llm_config_name)
        
        return response_content

    async def stream_llm(self, prompt: str, llm_config_name: str):
        llm = self.get_llm(llm_config_name)
        async for chunk in llm.astream(prompt):
            yield chunk.content