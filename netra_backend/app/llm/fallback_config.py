"""
LLM Fallback Configuration
Provides fallback configurations for LLM operations
"""

from typing import Dict, Any, Optional
from netra_backend.app.llm.llm_defaults import LLMModel, LLMConfig

class FallbackConfig:
    """Fallback configuration for LLM operations"""
    
    @staticmethod
    def get_fallback_model() -> LLMModel:
        """Get fallback LLM model"""
        return LLMModel.GPT_4
        
    @staticmethod
    def get_fallback_config() -> LLMConfig:
        """Get fallback LLM configuration"""
        config = LLMConfig()
        config.model = LLMModel.GPT_4
        return config
        
    @staticmethod
    def get_fallback_params() -> Dict[str, Any]:
        """Get fallback parameters"""
        return {
            "temperature": 0.7,
            "max_tokens": 4000,
            "timeout": 30.0
        }

class RetryHistoryManager:
    """Manages retry history for LLM operations"""
    
    def __init__(self):
        self.retry_history = []
        
    def add_retry(self, model: str, error: str):
        """Add a retry attempt to history"""
        self.retry_history.append({
            "model": model,
            "error": error,
            "timestamp": "2024-01-01T00:00:00Z"  # Placeholder
        })
        
    def get_retry_count(self, model: str) -> int:
        """Get retry count for a model"""
        return len([r for r in self.retry_history if r["model"] == model])

# Legacy exports
FALLBACK_MODEL = FallbackConfig.get_fallback_model()
FALLBACK_CONFIG = FallbackConfig.get_fallback_config()
