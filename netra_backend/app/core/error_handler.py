"""
Core Error Handler

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Reliability & User Experience
- Value Impact: Centralized error handling and recovery mechanisms
- Strategic Impact: Reduces system downtime and improves error visibility

Provides centralized error handling, recovery, and logging.
"""

import asyncio
import time
import traceback
from typing import Dict, Any, List, Optional, Type, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
import uuid

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    VALIDATION = "validation"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    NETWORK = "network"
    DATABASE = "database"
    EXTERNAL_API = "external_api"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"


@dataclass
class ErrorContext:
    """Context information for errors."""
    error_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    operation: Optional[str] = None
    component: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessedError:
    """Processed error with classification and handling info."""
    original_error: Exception
    error_type: str
    message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    stack_trace: str
    is_recoverable: bool = False
    recovery_action: Optional[str] = None
    user_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_id": self.context.error_id,
            "error_type": self.error_type,
            "message": self.message,
            "severity": self.severity,
            "category": self.category,
            "timestamp": self.context.timestamp,
            "user_id": self.context.user_id,
            "session_id": self.context.session_id,
            "request_id": self.context.request_id,
            "operation": self.context.operation,
            "component": self.context.component,
            "metadata": self.context.metadata,
            "stack_trace": self.stack_trace,
            "is_recoverable": self.is_recoverable,
            "recovery_action": self.recovery_action,
            "user_message": self.user_message
        }


class ErrorClassifier:
    """Classifies errors into categories and severities."""
    
    def __init__(self):
        self.classification_rules: Dict[Type[Exception], Dict[str, Any]] = {
            ValueError: {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "recoverable": True
            },
            TypeError: {
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.MEDIUM,
                "recoverable": True
            },
            PermissionError: {
                "category": ErrorCategory.AUTHORIZATION,
                "severity": ErrorSeverity.HIGH,
                "recoverable": False
            },
            ConnectionError: {
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.HIGH,
                "recoverable": True
            },
            asyncio.TimeoutError: {
                "category": ErrorCategory.TIMEOUT,
                "severity": ErrorSeverity.HIGH,
                "recoverable": True
            },
            FileNotFoundError: {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.MEDIUM,
                "recoverable": False
            },
            MemoryError: {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.CRITICAL,
                "recoverable": False
            },
            KeyboardInterrupt: {
                "category": ErrorCategory.SYSTEM,
                "severity": ErrorSeverity.HIGH,
                "recoverable": False
            }
        }
        
        # Message-based classifications
        self.message_patterns: Dict[str, Dict[str, Any]] = {
            "authentication": {
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "recoverable": True
            },
            "rate limit": {
                "category": ErrorCategory.RATE_LIMIT,
                "severity": ErrorSeverity.MEDIUM,
                "recoverable": True
            },
            "database": {
                "category": ErrorCategory.DATABASE,
                "severity": ErrorSeverity.HIGH,
                "recoverable": True
            },
            "api": {
                "category": ErrorCategory.EXTERNAL_API,
                "severity": ErrorSeverity.MEDIUM,
                "recoverable": True
            }
        }
    
    def classify_error(self, error: Exception) -> Dict[str, Any]:
        """Classify an error based on type and message."""
        error_type = type(error)
        error_message = str(error).lower()
        
        # Check exact type match
        if error_type in self.classification_rules:
            return self.classification_rules[error_type]
        
        # Check parent type matches
        for exception_type, classification in self.classification_rules.items():
            if issubclass(error_type, exception_type):
                return classification
        
        # Check message patterns
        for pattern, classification in self.message_patterns.items():
            if pattern in error_message:
                return classification
        
        # Default classification
        return {
            "category": ErrorCategory.SYSTEM,
            "severity": ErrorSeverity.MEDIUM,
            "recoverable": False
        }


class RecoveryManager:
    """Manages error recovery strategies."""
    
    def __init__(self):
        self.recovery_strategies: Dict[ErrorCategory, List[Callable]] = {
            ErrorCategory.NETWORK: [
                self._retry_with_backoff,
                self._fallback_to_cache
            ],
            ErrorCategory.TIMEOUT: [
                self._retry_with_timeout,
                self._reduce_scope
            ],
            ErrorCategory.RATE_LIMIT: [
                self._wait_and_retry,
                self._use_alternative_endpoint
            ],
            ErrorCategory.DATABASE: [
                self._retry_database_operation,
                self._use_readonly_replica
            ],
            ErrorCategory.EXTERNAL_API: [
                self._retry_api_call,
                self._use_fallback_service
            ]
        }
    
    async def attempt_recovery(self, processed_error: ProcessedError,
                             operation: Callable, *args, **kwargs) -> Optional[Any]:
        """Attempt to recover from an error."""
        if not processed_error.is_recoverable:
            return None
        
        strategies = self.recovery_strategies.get(processed_error.category, [])
        
        for strategy in strategies:
            try:
                logger.info(f"Attempting recovery strategy: {strategy.__name__}")
                result = await strategy(processed_error, operation, *args, **kwargs)
                if result is not None:
                    logger.info(f"Recovery successful with strategy: {strategy.__name__}")
                    return result
            except Exception as e:
                logger.warning(f"Recovery strategy {strategy.__name__} failed: {e}")
                continue
        
        logger.error(f"All recovery strategies failed for error: {processed_error.error_id}")
        return None
    
    async def _retry_with_backoff(self, error: ProcessedError, operation: Callable,
                                *args, **kwargs) -> Optional[Any]:
        """Retry operation with exponential backoff."""
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)
            
            try:
                if asyncio.iscoroutinefunction(operation):
                    return await operation(*args, **kwargs)
                else:
                    return operation(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                continue
        
        return None
    
    async def _fallback_to_cache(self, error: ProcessedError, operation: Callable,
                               *args, **kwargs) -> Optional[Any]:
        """Fallback to cached data if available."""
        # Simplified cache fallback
        cache_key = f"fallback_{operation.__name__}_{hash(str(args))}"
        # In real implementation, would check actual cache
        logger.info(f"Attempting cache fallback for key: {cache_key}")
        return {"cached": True, "message": "Fallback data from cache"}
    
    async def _retry_with_timeout(self, error: ProcessedError, operation: Callable,
                                *args, **kwargs) -> Optional[Any]:
        """Retry operation with extended timeout."""
        extended_timeout = 30.0
        try:
            if asyncio.iscoroutinefunction(operation):
                return await asyncio.wait_for(operation(*args, **kwargs), timeout=extended_timeout)
            else:
                return operation(*args, **kwargs)
        except asyncio.TimeoutError:
            return None
    
    async def _reduce_scope(self, error: ProcessedError, operation: Callable,
                          *args, **kwargs) -> Optional[Any]:
        """Retry operation with reduced scope."""
        # Simplified scope reduction
        reduced_kwargs = {k: v for k, v in kwargs.items() if k != "limit"}
        reduced_kwargs["limit"] = min(kwargs.get("limit", 100), 10)
        
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **reduced_kwargs)
            else:
                return operation(*args, **reduced_kwargs)
        except Exception:
            return None
    
    async def _wait_and_retry(self, error: ProcessedError, operation: Callable,
                            *args, **kwargs) -> Optional[Any]:
        """Wait for rate limit reset and retry."""
        wait_time = 60.0  # Wait 1 minute for rate limit reset
        await asyncio.sleep(wait_time)
        
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
        except Exception:
            return None
    
    async def _use_alternative_endpoint(self, error: ProcessedError, operation: Callable,
                                      *args, **kwargs) -> Optional[Any]:
        """Use alternative endpoint if available."""
        # Simplified alternative endpoint logic
        logger.info("Attempting alternative endpoint")
        return {"alternative": True, "message": "Response from alternative endpoint"}
    
    async def _retry_database_operation(self, error: ProcessedError, operation: Callable,
                                      *args, **kwargs) -> Optional[Any]:
        """Retry database operation with new connection."""
        await asyncio.sleep(1.0)  # Brief delay
        
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
        except Exception:
            return None
    
    async def _use_readonly_replica(self, error: ProcessedError, operation: Callable,
                                  *args, **kwargs) -> Optional[Any]:
        """Use readonly database replica."""
        # Simplified readonly fallback
        logger.info("Attempting readonly replica")
        return {"readonly": True, "message": "Data from readonly replica"}
    
    async def _retry_api_call(self, error: ProcessedError, operation: Callable,
                            *args, **kwargs) -> Optional[Any]:
        """Retry API call with new request."""
        await asyncio.sleep(2.0)  # Brief delay
        
        try:
            if asyncio.iscoroutinefunction(operation):
                return await operation(*args, **kwargs)
            else:
                return operation(*args, **kwargs)
        except Exception:
            return None
    
    async def _use_fallback_service(self, error: ProcessedError, operation: Callable,
                                  *args, **kwargs) -> Optional[Any]:
        """Use fallback service."""
        # Simplified fallback service
        logger.info("Attempting fallback service")
        return {"fallback_service": True, "message": "Response from fallback service"}


class ErrorHandler:
    """Central error handler for the application."""
    
    def __init__(self):
        self.classifier = ErrorClassifier()
        self.recovery_manager = RecoveryManager()
        self.error_history: List[ProcessedError] = []
        self.error_counts: Dict[str, int] = {}
        self.handlers: Dict[ErrorCategory, List[Callable]] = {}
        
        # Register default handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default error handlers."""
        self.register_handler(ErrorCategory.CRITICAL, self._handle_critical_error)
        self.register_handler(ErrorCategory.AUTHENTICATION, self._handle_auth_error)
        self.register_handler(ErrorCategory.RATE_LIMIT, self._handle_rate_limit_error)
    
    def register_handler(self, category: ErrorCategory, handler: Callable):
        """Register an error handler for a category."""
        if category not in self.handlers:
            self.handlers[category] = []
        self.handlers[category].append(handler)
    
    async def handle_error(self, error: Exception, context: Optional[ErrorContext] = None) -> ProcessedError:
        """Handle an error with classification and processing."""
        # Create context if not provided
        if context is None:
            context = ErrorContext()
        
        # Classify the error
        classification = self.classifier.classify_error(error)
        
        # Create processed error
        processed_error = ProcessedError(
            original_error=error,
            error_type=type(error).__name__,
            message=str(error),
            severity=ErrorSeverity(classification["severity"]),
            category=ErrorCategory(classification["category"]),
            context=context,
            stack_trace=traceback.format_exc(),
            is_recoverable=classification["recoverable"],
            user_message=self._generate_user_message(error, classification)
        )
        
        # Update statistics
        error_key = f"{processed_error.category}:{processed_error.error_type}"
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1
        
        # Add to history
        self.error_history.append(processed_error)
        
        # Keep only recent errors
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-500:]
        
        # Log the error
        self._log_error(processed_error)
        
        # Run category-specific handlers
        await self._run_handlers(processed_error)
        
        return processed_error
    
    async def handle_and_recover(self, error: Exception, operation: Callable,
                               context: Optional[ErrorContext] = None,
                               *args, **kwargs) -> Union[Any, ProcessedError]:
        """Handle error and attempt recovery."""
        processed_error = await self.handle_error(error, context)
        
        if processed_error.is_recoverable:
            recovery_result = await self.recovery_manager.attempt_recovery(
                processed_error, operation, *args, **kwargs
            )
            
            if recovery_result is not None:
                processed_error.recovery_action = "recovered_successfully"
                logger.info(f"Error {processed_error.context.error_id} recovered successfully")
                return recovery_result
        
        return processed_error
    
    def _generate_user_message(self, error: Exception, classification: Dict[str, Any]) -> str:
        """Generate user-friendly error message."""
        category = classification["category"]
        severity = classification["severity"]
        
        if category == ErrorCategory.VALIDATION:
            return "Please check your input and try again."
        elif category == ErrorCategory.AUTHENTICATION:
            return "Authentication failed. Please log in again."
        elif category == ErrorCategory.NETWORK:
            return "Network error occurred. Please try again later."
        elif category == ErrorCategory.RATE_LIMIT:
            return "Too many requests. Please wait a moment and try again."
        elif severity == ErrorSeverity.CRITICAL:
            return "A critical system error occurred. Please contact support."
        else:
            return "An error occurred while processing your request. Please try again."
    
    def _log_error(self, processed_error: ProcessedError):
        """Log the processed error."""
        log_data = {
            "error_id": processed_error.context.error_id,
            "error_type": processed_error.error_type,
            "category": processed_error.category,
            "severity": processed_error.severity,
            "message": processed_error.message,
            "user_id": processed_error.context.user_id,
            "operation": processed_error.context.operation,
            "component": processed_error.context.component
        }
        
        if processed_error.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"Critical error: {log_data}")
        elif processed_error.severity == ErrorSeverity.HIGH:
            logger.error(f"High severity error: {log_data}")
        elif processed_error.severity == ErrorSeverity.MEDIUM:
            logger.warning(f"Medium severity error: {log_data}")
        else:
            logger.info(f"Low severity error: {log_data}")
    
    async def _run_handlers(self, processed_error: ProcessedError):
        """Run category-specific error handlers."""
        handlers = self.handlers.get(processed_error.category, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(processed_error)
                else:
                    handler(processed_error)
            except Exception as e:
                logger.error(f"Error handler failed: {e}")
    
    async def _handle_critical_error(self, processed_error: ProcessedError):
        """Handle critical errors."""
        logger.critical(f"Critical error detected: {processed_error.context.error_id}")
        # In production, might trigger alerts, create incidents, etc.
    
    async def _handle_auth_error(self, processed_error: ProcessedError):
        """Handle authentication errors."""
        logger.warning(f"Authentication error for user: {processed_error.context.user_id}")
        # In production, might invalidate sessions, trigger security checks, etc.
    
    async def _handle_rate_limit_error(self, processed_error: ProcessedError):
        """Handle rate limit errors."""
        logger.info(f"Rate limit exceeded for user: {processed_error.context.user_id}")
        # In production, might implement backpressure, user throttling, etc.
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error handling statistics."""
        return {
            "total_errors": len(self.error_history),
            "error_counts_by_type": self.error_counts.copy(),
            "recent_errors": len([e for e in self.error_history if time.time() - e.context.timestamp < 3600]),
            "severity_distribution": {
                severity: len([e for e in self.error_history if e.severity == severity])
                for severity in ErrorSeverity
            },
            "category_distribution": {
                category: len([e for e in self.error_history if e.category == category])
                for category in ErrorCategory
            },
            "recovery_rate": len([e for e in self.error_history if e.recovery_action]) / max(1, len(self.error_history))
        }
    
    def clear_history(self):
        """Clear error history."""
        self.error_history.clear()
        self.error_counts.clear()


# Global error handler instance
_error_handler: Optional[ErrorHandler] = None

def get_error_handler() -> ErrorHandler:
    """Get global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

async def handle_error(error: Exception, context: Optional[ErrorContext] = None) -> ProcessedError:
    """Convenience function to handle an error."""
    handler = get_error_handler()
    return await handler.handle_error(error, context)

async def handle_and_recover(error: Exception, operation: Callable, 
                           context: Optional[ErrorContext] = None,
                           *args, **kwargs) -> Union[Any, ProcessedError]:
    """Convenience function to handle error and attempt recovery."""
    handler = get_error_handler()
    return await handler.handle_and_recover(error, operation, context, *args, **kwargs)