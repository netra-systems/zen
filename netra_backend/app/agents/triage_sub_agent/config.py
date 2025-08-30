"""Triage Agent Configuration

Centralized configuration for the Triage SubAgent LLM operations.
Ensures explicit use of Gemini 2.5 Pro with proper fallback handling.

Business Value Justification (BVJ):
- Segment: Enterprise, Mid
- Business Goal: Improve triage accuracy and reduce response times
- Value Impact: Faster, more accurate request categorization increases customer satisfaction
- Strategic Impact: Better triage reduces support costs and improves user experience
"""

from typing import Dict, Optional, Any

from netra_backend.app.llm.llm_defaults import LLMModel
from netra_backend.app.schemas.llm_types import LLMProvider
from netra_backend.app.core.isolated_environment import get_env


class TriageConfig:
    """Centralized triage agent configuration.
    
    SSOT for all triage-specific LLM settings and behaviors.
    """
    
    # Get environment through centralized management
    _env = get_env()
    
    # Model Selection (Use fast model for tests)
    _is_testing = _env.get('TESTING') == '1'
    _use_flash_model = _env.get('NETRA_DEFAULT_LLM_MODEL') == 'gemini-2.5-flash'
    
    if _is_testing or _use_flash_model:
        PRIMARY_MODEL = LLMModel.GEMINI_2_5_FLASH
        FALLBACK_MODEL = LLMModel.GEMINI_2_5_FLASH
    else:
        PRIMARY_MODEL = LLMModel.GEMINI_2_5_PRO
        FALLBACK_MODEL = LLMModel.GEMINI_2_5_FLASH
    PROVIDER = LLMProvider.GOOGLE
    
    # Triage-specific LLM Parameters
    TEMPERATURE = 0.0  # Deterministic for consistent categorization
    MAX_TOKENS = 4096
    # Use faster timeout for tests with flash model
    if _is_testing or _use_flash_model:
        TIMEOUT_SECONDS = 10.0  # Flash model timeout
    else:
        TIMEOUT_SECONDS = 17.0  # Pro model timeout (longer than Flash's 10s)
    MAX_RETRIES = 2
    
    # Output Configuration
    USE_STRUCTURED_OUTPUT = True
    ENABLE_CACHE = True
    CACHE_TTL_SECONDS = 3600
    
    # Circuit Breaker Configuration for Triage
    circuit_timeout = 10.0 if (_is_testing or _use_flash_model) else 17.0
    CIRCUIT_BREAKER_CONFIG = {
        "failure_threshold": 10,  # Open circuit after 10 failures
        "recovery_timeout": 10.0,  # Try recovery after 10 seconds
        "timeout_seconds": circuit_timeout,   # Same as request timeout
        "half_open_max_calls": 5,  # Max calls when half-open
    }
    
    # Fallback Configuration
    FALLBACK_CONFIG = {
        "enable_fallback_to_flash": True,
        "max_fallback_retries": 1,
        "fallback_timeout_seconds": 10.0,
        "preserve_structured_output": True,
    }
    
    # Response Format Requirements
    RESPONSE_SCHEMA_VALIDATION = {
        "require_category": True,
        "require_confidence_score": True,
        "require_priority": True,
        "require_extracted_entities": True,
        "require_tool_recommendations": True,
        "validate_confidence_range": (0.0, 1.0),
        "valid_priorities": ["low", "medium", "high", "urgent"],
    }
    
    # Performance Monitoring
    PERFORMANCE_TRACKING = {
        "log_model_selection": True,
        "log_response_time": True,
        "log_cache_hits": True,
        "log_circuit_breaker_state": True,
        "log_fallback_usage": True,
    }
    
    @classmethod
    def get_llm_config(cls) -> Dict[str, Any]:
        """Get LLM configuration dictionary for triage operations.
        
        Returns:
            Configuration dictionary compatible with LLM manager
        """
        return {
            "provider": cls.PROVIDER.value,
            "model_name": cls.PRIMARY_MODEL.value,
            "temperature": cls.TEMPERATURE,
            "max_tokens": cls.MAX_TOKENS,
            "timeout_seconds": cls.TIMEOUT_SECONDS,
            "max_retries": cls.MAX_RETRIES,
            "use_structured_output": cls.USE_STRUCTURED_OUTPUT,
            "enable_cache": cls.ENABLE_CACHE,
            "cache_ttl_seconds": cls.CACHE_TTL_SECONDS,
        }
    
    @classmethod
    def get_fallback_config(cls) -> Dict[str, Any]:
        """Get fallback configuration for triage operations.
        
        Returns:
            Fallback configuration dictionary
        """
        fallback_config = cls.FALLBACK_CONFIG.copy()
        fallback_config["fallback_model"] = cls.FALLBACK_MODEL.value
        fallback_config["fallback_provider"] = cls.PROVIDER.value
        return fallback_config
    
    @classmethod
    def get_circuit_breaker_config(cls) -> Dict[str, Any]:
        """Get circuit breaker configuration for triage operations.
        
        Returns:
            Circuit breaker configuration dictionary
        """
        return cls.CIRCUIT_BREAKER_CONFIG.copy()
    
    @classmethod
    def should_log_performance_metric(cls, metric_name: str) -> bool:
        """Check if a performance metric should be logged.
        
        Args:
            metric_name: Name of the metric to check
            
        Returns:
            True if metric should be logged
        """
        return cls.PERFORMANCE_TRACKING.get(f"log_{metric_name}", False)
    
    @classmethod
    def validate_response_format(cls, response: Dict[str, Any]) -> bool:
        """Validate triage response format against schema requirements.
        
        Args:
            response: Triage response to validate
            
        Returns:
            True if response meets all requirements
        """
        validation = cls.RESPONSE_SCHEMA_VALIDATION
        
        # Check required fields
        required_fields = [
            "category", "confidence_score", "priority", 
            "extracted_entities", "tool_recommendations"
        ]
        
        for field in required_fields:
            if validation.get(f"require_{field}", False) and field not in response:
                return False
        
        # Validate confidence score range
        if "confidence_score" in response:
            conf_min, conf_max = validation.get("validate_confidence_range", (0.0, 1.0))
            confidence = response.get("confidence_score", 0.0)
            if not (conf_min <= confidence <= conf_max):
                return False
        
        # Validate priority values
        if "priority" in response:
            valid_priorities = validation.get("valid_priorities", [])
            if response.get("priority") not in valid_priorities:
                return False
        
        return True
    
    @classmethod
    def get_model_display_name(cls) -> str:
        """Get human-readable model name for logging.
        
        Returns:
            Display name for the primary model
        """
        return f"{cls.PROVIDER.value.title()} {cls.PRIMARY_MODEL.value}"
    
    @classmethod
    def get_timeout_for_model(cls, model: Optional[LLMModel] = None) -> float:
        """Get appropriate timeout for the specified model.
        
        Args:
            model: LLM model to get timeout for, defaults to primary model
            
        Returns:
            Timeout in seconds
        """
        if model == cls.FALLBACK_MODEL:
            return cls.FALLBACK_CONFIG.get("fallback_timeout_seconds", 10.0)
        return cls.TIMEOUT_SECONDS


# Legacy support for backward compatibility
TRIAGE_LLM_MODEL = TriageConfig.PRIMARY_MODEL
TRIAGE_FALLBACK_MODEL = TriageConfig.FALLBACK_MODEL
TRIAGE_TEMPERATURE = TriageConfig.TEMPERATURE
TRIAGE_MAX_TOKENS = TriageConfig.MAX_TOKENS
TRIAGE_TIMEOUT = TriageConfig.TIMEOUT_SECONDS