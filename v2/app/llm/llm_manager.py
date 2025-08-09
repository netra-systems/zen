from typing import Any, Dict, Optional
from app.schemas import AppConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

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
                raise ValueError(f"{config.api_key} Gemini API key not found in config.")

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