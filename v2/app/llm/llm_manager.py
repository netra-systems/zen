from typing import Any, Dict, Optional
from app.llm.schemas import LLMConfig
from app.config import AppConfig
import google.generativeai as genai
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
            # It's assumed the google api key is set in the "google" config
            google_api_key = self.settings.llm_configs.get("google").api_key
            api_key = config.api_key or google_api_key
            
            if not api_key:
                 raise ValueError("Gemini API key not found in config.")

            genai.configure(api_key=api_key)
            llm = ChatGoogleGenerativeAI(
                model=config.model_name, **final_generation_config
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