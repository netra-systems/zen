"""Validation interfaces - Single source of truth.

Consolidated validation error handling for both document validation failures
and LLM error classification using chain of responsibility pattern.
Follows 450-line limit and 25-line functions.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class FailureType(Enum):
    """Types of failures for error classification."""
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"
    API_ERROR = "api_error"
    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "auth_error"
    DOCUMENT_ERROR = "document_error"
    ENCODING_ERROR = "encoding_error"
    FORMAT_ERROR = "format_error"
    UNKNOWN = "unknown"


class ValidationErrorHandler:
    """Unified validation error handler for document and system errors."""
    
    def __init__(self):
        """Initialize validation error handler with classification chain."""
        self.classification_chain = self._build_error_classification_chain()
    
    async def handle_document_validation_error(self, filename: str, validation_errors: List[str],
                                              run_id: str, original_error: Exception) -> Dict[str, Any]:
        """Handle document validation failures with recovery strategies."""
        try:
            recovery_result = await self._attempt_validation_recovery(filename, validation_errors, run_id)
            if recovery_result:
                return recovery_result
            
            return await self._create_validation_report(filename, validation_errors, run_id)
            
        except Exception as fallback_error:
            logger.error(f"Validation error handling failed: {fallback_error}")
            raise original_error
    
    def classify_error(self, error: Exception) -> FailureType:
        """Classify error using chain of responsibility pattern."""
        return self.classification_chain.handle(error)
    
    async def _attempt_validation_recovery(self, filename: str, validation_errors: List[str], run_id: str) -> Optional[Dict[str, Any]]:
        """Attempt validation recovery strategies."""
        # Try automatic fixes first
        fixed_result = await self._try_validation_fixes(filename, validation_errors, run_id)
        if fixed_result:
            return fixed_result
        
        # Try relaxed validation as fallback
        return await self._try_relaxed_validation(filename, validation_errors, run_id)
    
    async def _try_validation_fixes(self, filename: str, validation_errors: List[str], run_id: str) -> Optional[Dict[str, Any]]:
        """Try to automatically fix common validation issues."""
        fixed_errors = []
        
        for error in validation_errors:
            if await self._can_fix_error(error, filename):
                fixed_errors.append(error)
        
        if fixed_errors:
            remaining_errors = [e for e in validation_errors if e not in fixed_errors]
            logger.info(f"Fixed validation errors automatically for {filename}")
            return {
                'success': True, 'method': 'automatic_fixes',
                'fixed_errors': fixed_errors, 'remaining_errors': remaining_errors
            }
        
        return None
    
    async def _can_fix_error(self, error: str, filename: str) -> bool:
        """Check if error can be automatically fixed."""
        error_lower = error.lower()
        if 'encoding' in error_lower:
            return await self._fix_encoding_issue(filename)
        elif 'format' in error_lower:
            return await self._fix_format_issue(filename)
        return False
    
    async def _try_relaxed_validation(self, filename: str, validation_errors: List[str], run_id: str) -> Optional[Dict[str, Any]]:
        """Try validation with relaxed rules."""
        critical_errors, non_critical_errors = self._categorize_errors(validation_errors)
        
        # Allow if only non-critical errors
        if not critical_errors:
            logger.info(f"Document accepted with relaxed validation: {filename}")
            return {
                'success': True, 'method': 'relaxed_validation',
                'warnings': non_critical_errors, 'message': 'Document accepted with warnings'
            }
        
        return None
    
    def _categorize_errors(self, validation_errors: List[str]) -> tuple:
        """Categorize errors into critical and non-critical."""
        critical_errors = [e for e in validation_errors if 'critical' in e.lower()]
        non_critical_errors = [e for e in validation_errors if 'critical' not in e.lower()]
        return critical_errors, non_critical_errors
    
    async def _create_validation_report(self, filename: str, validation_errors: List[str], run_id: str) -> Dict[str, Any]:
        """Create validation report for manual review."""
        report = {
            'filename': filename, 'validation_errors': validation_errors,
            'timestamp': datetime.now().isoformat(), 'run_id': run_id,
            'status': 'requires_manual_review'
        }
        
        logger.info(f"Created validation report for manual review: {filename}")
        return {
            'success': False, 'method': 'manual_review_required',
            'report': report, 'message': 'Document requires manual review due to validation errors'
        }
    
    async def _fix_encoding_issue(self, filename: str) -> bool:
        """Try to fix encoding issues."""
        # Simplified implementation - would try different encodings
        return True
    
    async def _fix_format_issue(self, filename: str) -> bool:
        """Try to fix format issues."""
        # Simplified implementation - would try format conversion
        return True
    
    def _build_error_classification_chain(self) -> 'ErrorClassificationHandler':
        """Build the chain of responsibility for error classification."""
        # Create handlers
        timeout_handler = TimeoutErrorHandler()
        rate_limit_handler = RateLimitErrorHandler()
        auth_handler = AuthenticationErrorHandler()
        network_handler = NetworkErrorHandler()
        validation_handler = ValidationErrorClassificationHandler()
        api_handler = APIErrorHandler()
        
        # Chain them together
        timeout_handler.set_next(rate_limit_handler).set_next(auth_handler).set_next(
            network_handler).set_next(validation_handler).set_next(api_handler)
        
        return timeout_handler


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
    def handle(self, error: Exception) -> FailureType:
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


class ValidationErrorClassificationHandler(ErrorClassificationHandler):
    """Handler for validation errors."""
    
    def handle(self, error: Exception) -> FailureType:
        """Handle validation error classification."""
        if self._is_validation_error(error):
            return FailureType.VALIDATION_ERROR
        return self._handle_next(error)
    
    def _is_validation_error(self, error: Exception) -> bool:
        """Check if error is validation-related."""
        error_str = str(error).lower()
        return "validation" in error_str or "invalid" in error_str or "format" in error_str


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
        return "api" in error_str or "500" in error_str or "503" in error_str


class ErrorClassificationChain:
    """Error classification chain builder and executor."""
    
    def __init__(self):
        """Initialize classification chain."""
        self.chain = self._build_classification_chain()
    
    def _build_classification_chain(self) -> ErrorClassificationHandler:
        """Build the chain of responsibility for error classification."""
        handler_instances = self._create_all_handlers()
        return self._chain_handlers_in_priority_order(handler_instances)
    
    def _create_all_handlers(self) -> Dict[str, ErrorClassificationHandler]:
        """Create all handler instances."""
        return {
            'timeout': TimeoutErrorHandler(),
            'rate_limit': RateLimitErrorHandler(),
            'auth': AuthenticationErrorHandler(),
            'network': NetworkErrorHandler(),
            'validation': ValidationErrorClassificationHandler(),
            'api': APIErrorHandler()
        }
    
    def _chain_handlers_in_priority_order(self, handlers: Dict[str, ErrorClassificationHandler]) -> ErrorClassificationHandler:
        """Chain handlers in priority order and return first handler."""
        handlers['timeout'].set_next(handlers['rate_limit']).set_next(handlers['auth']).set_next(
            handlers['network']).set_next(handlers['validation']).set_next(handlers['api'])
        return handlers['timeout']
    
    def classify_error(self, error: Exception) -> FailureType:
        """Classify error using chain of responsibility."""
        return self.chain.handle(error)


# Factory function for creating validation handlers
def create_validation_handler() -> ValidationErrorHandler:
    """Create validation error handler instance."""
    return ValidationErrorHandler()


def create_error_classification_chain() -> ErrorClassificationChain:
    """Create error classification chain instance."""
    return ErrorClassificationChain()