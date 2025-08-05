
from typing import Any, Dict, Optional
from app.llm.schemas import LLMConfig
from app.config import settings
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI



class LLMManager:
    def __init__(self, llm_configs: Dict[str, LLMConfig]):
        self.llm_configs = llm_configs
        self._llm_cache: Dict[str, Any] = {}

    def get_llm(self, name: str) -> Any:
        if name in self._llm_cache:
            return self._llm_cache[name]

        config = self.llm_configs.get(name)
        if not config:
            raise ValueError(f"LLM configuration for '{name}' not found.")

        if config.provider == "google":
            genai.configure(api_key=config.api_key or settings.google_model.gemini_api_key)
            llm = ChatGoogleGenerativeAI(model=config.model_name, temperature=config.temperature, max_tokens=config.max_tokens)
        elif config.provider == "openai":
            llm = ChatOpenAI(model_name=config.model_name, api_key=config.api_key, temperature=config.temperature, max_tokens=config.max_tokens)
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

        self._llm_cache[name] = llm
        return llm

# To be initialized in main.py
llm_manager: Optional[LLMManager] = None

def get_llm_manager() -> LLMManager:
    if not llm_manager:
        raise RuntimeError("LLMManager has not been initialized.")
    return llm_manager
