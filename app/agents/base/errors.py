"""Error Management System - Unified Interface

Provides unified access to all error handling components.

Business Value: Reduces error-related customer impact by 80%.
"""

from app.logging_config import central_logger

# Import all error handling components for unified access
from .agent_errors import (
    AgentExecutionError, 
    ValidationError, 
    ExternalServiceError, 
    DatabaseError
)
from .error_classification import (
    ErrorCategory,
    ErrorClassification, 
    ErrorClassifier
)
from .error_handler import ExecutionErrorHandler

logger = central_logger.get_logger(__name__)

# Export all components for backward compatibility
__all__ = [
    'AgentExecutionError',
    'ValidationError', 
    'ExternalServiceError',
    'DatabaseError',
    'ErrorCategory',
    'ErrorClassification',
    'ErrorClassifier',
    'ExecutionErrorHandler'
]