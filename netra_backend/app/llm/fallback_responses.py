"""
LLM Fallback Response Builders

This module creates default responses for different LLM operations.
Each function is  <= 8 lines with strong typing and single responsibility.
"""

import time
from typing import Any, Dict, Optional, Type, TypeVar

from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class TriageResponseBuilder:
    """Builds default triage responses with  <= 8 line methods."""
    
    @staticmethod
    def create_base_response() -> Dict[str, Any]:
        """Create base triage response structure."""
        return {
            "category": "General Inquiry",
            "confidence_score": 0.5,
            "priority": "medium",
            "extracted_entities": {},
            "tool_recommendations": []
        }
    
    @staticmethod
    def add_fallback_metadata(response: Dict[str, Any], retry_count: int = 0) -> Dict[str, Any]:
        """Add fallback metadata to triage response."""
        response["metadata"] = {
            "triage_duration_ms": 0,
            "fallback_used": True,
            "llm_tokens_used": 0,
            "cache_hit": False,
            "retry_count": retry_count
        }
        return response
    
    @classmethod
    def build_complete_response(cls, retry_count: int = 0) -> Dict[str, Any]:
        """Build complete triage fallback response."""
        response = cls.create_base_response()
        return cls.add_fallback_metadata(response, retry_count)


class DataAnalysisResponseBuilder:
    """Builds default data analysis responses with  <= 8 line methods."""
    
    @staticmethod
    def create_base_response() -> Dict[str, Any]:
        """Create base data analysis response structure."""
        return {
            "insights": ["Analysis unavailable due to system limitations"],
            "recommendations": ["Please try again later"],
            "confidence": 0.3
        }
    
    @staticmethod
    def add_fallback_metadata(response: Dict[str, Any]) -> Dict[str, Any]:
        """Add fallback metadata to data analysis response."""
        response["metadata"] = {"fallback_used": True}
        return response
    
    @classmethod
    def build_complete_response(cls) -> Dict[str, Any]:
        """Build complete data analysis fallback response."""
        response = cls.create_base_response()
        return cls.add_fallback_metadata(response)


class FallbackResponseFactory:
    """Factory for creating different types of fallback responses."""
    
    DEFAULT_GENERAL_MESSAGE = "I apologize, but I'm experiencing technical difficulties. Please try again in a few moments."
    
    def __init__(self):
        """Initialize response factory with response builders."""
        self.default_responses = self._build_default_responses()
    
    def _build_default_responses(self) -> Dict[str, Any]:
        """Build dictionary of default responses by type."""
        return {
            "triage": TriageResponseBuilder.build_complete_response(),
            "data_analysis": DataAnalysisResponseBuilder.build_complete_response(),
            "general": self.DEFAULT_GENERAL_MESSAGE
        }
    
    def create_response(self, fallback_type: str, error: Optional[Exception] = None) -> Any:
        """Create fallback response with optional error context."""
        if fallback_type in self.default_responses:
            return self._enhance_response_with_error(fallback_type, error)
        return self.default_responses["general"]
        
    def create_circuit_breaker_response(self, fallback_type: str, error: Optional[Exception] = None) -> Any:
        """Create fallback response specifically for circuit breaker open scenarios."""
        if fallback_type == "triage":
            return self._create_circuit_breaker_triage_response()
        elif fallback_type == "data_analysis":
            return self._create_circuit_breaker_data_analysis_response()
        else:
            return "Service temporarily unavailable due to circuit breaker protection. Please try again in a few moments."
    
    def _enhance_response_with_error(self, fallback_type: str, error: Optional[Exception]) -> Any:
        """Enhance response with error information."""
        response = self.default_responses[fallback_type]
        # Only copy if response is a dict, not a string
        if isinstance(response, dict):
            response = response.copy()
            if "metadata" in response:
                self._add_error_metadata(response, error)
        return response
    
    def _add_error_metadata(self, response: Dict[str, Any], error: Optional[Exception]) -> None:
        """Add error metadata to response."""
        response["metadata"]["error"] = str(error) if error else "Unknown error"
        response["metadata"]["timestamp"] = time.time()
        
    def _create_circuit_breaker_triage_response(self) -> Dict[str, Any]:
        """Create triage response for circuit breaker scenarios."""
        response = TriageResponseBuilder.create_base_response()
        response["category"] = "System_Unavailable"
        response["confidence_score"] = 0.1
        response["priority"] = "low"
        response["metadata"] = {
            "triage_duration_ms": 0,
            "fallback_used": True,
            "circuit_breaker_triggered": True,
            "llm_tokens_used": 0,
            "cache_hit": False,
            "retry_count": 0
        }
        return response
        
    def _create_circuit_breaker_data_analysis_response(self) -> Dict[str, Any]:
        """Create data analysis response for circuit breaker scenarios."""
        response = DataAnalysisResponseBuilder.create_base_response()
        response["insights"] = ["Analysis service temporarily unavailable due to system protection"]
        response["recommendations"] = ["Please try again in a few moments", "Check system status for updates"]
        response["confidence"] = 0.1
        response["metadata"] = {
            "fallback_used": True,
            "circuit_breaker_triggered": True
        }
        return response


class StructuredFallbackBuilder:
    """Builder for structured fallback instances using Pydantic schemas."""
    
    def __init__(self, schema: Type[T]):
        """Initialize builder with schema type."""
        self.schema = schema
        self.field_defaults: Dict[str, Any] = {}
    
    def build_field_defaults(self) -> 'StructuredFallbackBuilder':
        """Build default values for schema fields."""
        for field_name, field_info in self.schema.model_fields.items():
            self._set_field_default(field_name, field_info)
        return self
    
    def _set_field_default(self, field_name: str, field_info: Any) -> None:
        """Set default value for a specific field."""
        if field_info.default is not None:
            self.field_defaults[field_name] = field_info.default
        else:
            self.field_defaults[field_name] = TypeDefaultProvider.get_default(field_info.annotation)
    
    def build(self) -> T:
        """Build the structured fallback instance."""
        try:
            return self.schema(**self.field_defaults)
        except Exception:
            return self._create_empty_fallback()
    
    def _create_empty_fallback(self) -> T:
        """Create empty fallback instance as last resort."""
        try:
            return self.schema()
        except Exception:
            raise ValueError(f"Cannot create fallback instance for {self.schema.__name__}")


class TypeDefaultProvider:
    """Provides type-based default values for structured fallbacks."""
    
    TYPE_DEFAULTS = {
        str: "Unavailable due to system error",
        int: 0,
        float: 0.0,
        bool: False
    }
    
    @classmethod
    def get_default(cls, annotation: Type) -> Any:
        """Get default value based on type annotation."""
        if annotation in cls.TYPE_DEFAULTS:
            return cls.TYPE_DEFAULTS[annotation]
        return cls._get_container_default(annotation)
    
    @staticmethod
    def _get_container_default(annotation: Type) -> Any:
        """Get default for container types like list and dict."""
        if hasattr(annotation, '__origin__'):
            if annotation.__origin__ == list:
                return []
            elif annotation.__origin__ == dict:
                return {}
        return None