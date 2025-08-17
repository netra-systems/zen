"""
Error Classification Chain of Responsibility Pattern

This module implements chain of responsibility for error classification.
Each handler checks if it can handle the error type, otherwise passes to next handler.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict
from enum import Enum


class FailureType(Enum):
    """Types of LLM failures for error classification."""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit" 
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "auth_error"
    UNKNOWN = "unknown"


class ErrorClassificationHandler(ABC):
    """Abstract base class for error classification handlers."""
    
    def __init__(self):
        """Initialize handler."""
        self._next_handler: Optional['ErrorClassificationHandler'] = None
    
    def set_next(self, handler: 'ErrorClassificationHandler') -> 'ErrorClassificationHandler':
        """Set the next handler in the chain."""
        self._next_handler = handler
        return handler
    
    @abstractmethod
    def handle(self, error: Exception) -> Optional[FailureType]:
        """Handle error classification or pass to next handler."""
        pass
    
    def _handle_next(self, error: Exception) -> FailureType:
        """Pass to next handler or return unknown."""
        if self._next_handler:
            return self._next_handler.handle(error)
        return FailureType.UNKNOWN


class TimeoutErrorHandler(ErrorClassificationHandler):
    """Handler for timeout errors."""
    
    def handle(self, error: Exception) -> FailureType:
        """Handle timeout error classification."""
        if self._is_timeout_error(error):
            return FailureType.TIMEOUT
        return self._handle_next(error)
    
    def _is_timeout_error(self, error: Exception) -> bool:
        """Check if error is timeout-related."""
        import asyncio
        return isinstance(error, asyncio.TimeoutError) or "timeout" in str(error).lower()


class RateLimitErrorHandler(ErrorClassificationHandler):
    """Handler for rate limit errors."""
    
    def handle(self, error: Exception) -> FailureType:
        """Handle rate limit error classification."""
        if self._is_rate_limit_error(error):
            return FailureType.RATE_LIMIT
        return self._handle_next(error)
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if error is rate limit-related."""
        error_str = str(error).lower()
        return "rate limit" in error_str or "429" in error_str


class AuthenticationErrorHandler(ErrorClassificationHandler):
    """Handler for authentication errors."""
    
    def handle(self, error: Exception) -> FailureType:
        """Handle authentication error classification."""
        if self._is_auth_error(error):
            return FailureType.AUTHENTICATION_ERROR
        return self._handle_next(error)
    
    def _is_auth_error(self, error: Exception) -> bool:
        """Check if error is authentication-related."""
        error_str = str(error).lower()
        return "auth" in error_str or "401" in error_str or "403" in error_str


class NetworkErrorHandler(ErrorClassificationHandler):
    """Handler for network errors."""
    
    def handle(self, error: Exception) -> FailureType:
        """Handle network error classification."""
        if self._is_network_error(error):
            return FailureType.NETWORK_ERROR
        return self._handle_next(error)
    
    def _is_network_error(self, error: Exception) -> bool:
        """Check if error is network-related."""
        error_str = str(error).lower()
        return "network" in error_str or "connection" in error_str


class LLMValidationErrorHandler(ErrorClassificationHandler):
    """Handler for LLM validation errors."""
    
    def handle(self, error: Exception) -> FailureType:
        """Handle LLM validation error classification."""
        if self._is_validation_error(error):
            return FailureType.VALIDATION_ERROR
        return self._handle_next(error)
    
    def _is_validation_error(self, error: Exception) -> bool:
        """Check if error is LLM validation-related."""
        return "validation" in str(error).lower()


class APIErrorHandler(ErrorClassificationHandler):
    """Handler for API errors."""
    
    def handle(self, error: Exception) -> FailureType:
        """Handle API error classification."""
        if self._is_api_error(error):
            return FailureType.API_ERROR
        return self._handle_next(error)
    
    def _is_api_error(self, error: Exception) -> bool:
        """Check if error is API-related."""
        error_str = str(error).lower()
        return "api" in error_str or "500" in error_str


class ErrorClassificationChain:
    """Error classification chain builder and executor."""
    
    def __init__(self):
        """Initialize classification chain."""
        self.chain = self._build_classification_chain()
    
    def _build_classification_chain(self) -> ErrorClassificationHandler:
        """Build the chain of responsibility for error classification."""
        handlers = self._create_handler_instances()
        return self._chain_handlers_in_priority_order(handlers)
    
    def _create_core_handlers(self) -> Dict[str, ErrorClassificationHandler]:
        """Create core error handlers (timeout, rate limit, auth)."""
        return {
            'timeout': TimeoutErrorHandler(),
            'rate_limit': RateLimitErrorHandler(), 
            'auth': AuthenticationErrorHandler()
        }
    
    def _create_additional_handlers(self) -> Dict[str, ErrorClassificationHandler]:
        """Create additional error handlers (network, validation, api)."""
        return {
            'network': NetworkErrorHandler(),
            'validation': LLMValidationErrorHandler(),
            'api': APIErrorHandler()
        }
    
    def _create_handler_instances(self) -> Dict[str, ErrorClassificationHandler]:
        """Create all handler instances with strong typing."""
        handlers = self._create_core_handlers()
        handlers.update(self._create_additional_handlers())
        return handlers
    
    def _chain_handlers_in_priority_order(self, handlers: Dict[str, ErrorClassificationHandler]) -> ErrorClassificationHandler:
        """Chain handlers in priority order and return first handler."""
        handlers['timeout'].set_next(handlers['rate_limit']).set_next(handlers['auth']).set_next(
            handlers['network']).set_next(handlers['validation']).set_next(handlers['api'])
        return handlers['timeout']
    
    def classify_error(self, error: Exception) -> FailureType:
        """Classify error using chain of responsibility."""
        return self.chain.handle(error)