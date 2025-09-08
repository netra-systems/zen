"""
Exception hierarchy module for systematic warning-to-error remediation.

This module provides the foundation for Phase 1-5 remediation plan, enabling
business-value-protecting error escalation while maintaining backward compatibility.

Business Value:
- Prevents silent failures that could impact user chat experience
- Enables environment-aware error handling (dev warnings vs prod errors)
- Protects business-critical WebSocket notifications and agent executions
- Provides clear recovery guidance for operational issues
"""

from netra_backend.app.core.exceptions.websocket_exceptions import (
    WebSocketEventEmissionError,
    WebSocketNotificationError,
    WebSocketAgentEventError,
    WebSocketEventValidationError
)

from netra_backend.app.core.exceptions.agent_exceptions import (
    AgentLifecycleError,
    AgentStateTransitionError,
    AgentContextError,
    AgentRecoveryError,
    DeprecatedPatternError
)

from netra_backend.app.core.exceptions.deprecated_pattern_exceptions import (
    DeprecatedGlobalToolDispatcherError,
    DeprecatedFactoryPatternError,
    DeprecatedManagerPatternError
)

from netra_backend.app.core.exceptions.error_policy import (
    ErrorPolicy,
    EnvironmentAwareException,
    ProgressiveErrorHandler
)

# Import base exceptions from parent core directory
from netra_backend.app.core.exceptions_base import (
    NetraException,
    ErrorDetails,
    WebSocketValidationError,
    ValidationError,
    QualityGateException,
    StateRecoveryException,
    AuthorizationException,
    ServiceUnavailableException,
    PaymentException
)

# Import database exceptions from parent core directory  
from netra_backend.app.core.exceptions_database import (
    RecordNotFoundError,
    DatabaseError,
    DatabaseConnectionError,
    RecordAlreadyExistsError,
    DatabaseConstraintError
)

# Import service exceptions
from netra_backend.app.core.exceptions_service import (
    ServiceError,
    ServiceUnavailableError,
    ServiceTimeoutError,
    ExternalServiceError,
    LLMRequestError,
    LLMRateLimitError,
    ProcessingError
)

# Import agent exceptions from canonical location  
from netra_backend.app.core.exceptions_agent import (
    AgentError,
    AgentExecutionError,
    AgentTimeoutError,  # SSOT canonical location
    LLMError,
    AgentCoordinationError,
    AgentConfigurationError
)

# Import aliases for backward compatibility
from netra_backend.app.core.exceptions_database import (
    DatabaseConstraintError as ConstraintViolationError
)

__all__ = [
    # WebSocket exceptions
    "WebSocketEventEmissionError",
    "WebSocketNotificationError", 
    "WebSocketAgentEventError",
    "WebSocketEventValidationError",
    
    # Agent exceptions (from canonical location)
    "AgentError",
    "AgentExecutionError", 
    "AgentTimeoutError",
    "LLMError",
    "AgentCoordinationError",
    "AgentConfigurationError",
    
    # Specialized agent exceptions
    "AgentLifecycleError",
    "AgentStateTransitionError",
    "AgentContextError",
    "AgentRecoveryError",
    "DeprecatedPatternError",
    
    # Deprecated pattern exceptions
    "DeprecatedGlobalToolDispatcherError",
    "DeprecatedFactoryPatternError", 
    "DeprecatedManagerPatternError",
    
    # Error policy framework
    "ErrorPolicy",
    "EnvironmentAwareException",
    "ProgressiveErrorHandler",
    
    # Base exceptions  
    "NetraException",
    "ErrorDetails",
    "WebSocketValidationError",
    "ValidationError",
    "QualityGateException",
    "StateRecoveryException",
    "AuthorizationException", 
    "ServiceUnavailableException",
    "PaymentException",
    
    # Database exceptions
    "RecordNotFoundError",
    "DatabaseError",
    "DatabaseConnectionError",
    "RecordAlreadyExistsError",
    "DatabaseConstraintError",
    
    # Service exceptions
    "ServiceError",
    "ServiceUnavailableError",
    "ServiceTimeoutError", 
    "ExternalServiceError",
    "LLMRequestError",
    "LLMRateLimitError",
    "ProcessingError",
    
    # Aliases for backward compatibility
    "ConstraintViolationError"
]