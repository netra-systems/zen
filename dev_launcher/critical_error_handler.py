"""
Critical error handling for startup process.

Defines and handles critical errors that should stop the entire startup process.
"""

import sys
import logging
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class CriticalErrorType(Enum):
    """Types of critical errors that stop startup."""
    DATABASE_CONNECTION = 1
    AUTH_SERVICE = 2
    MISSING_ENV_VAR = 3
    PORT_BINDING = 4
    DEPENDENCY_MISSING = 5
    PERMISSION_DENIED = 6


class CriticalError(Exception):
    """Exception for critical startup errors."""
    
    def __init__(self, error_type: CriticalErrorType, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize critical error."""
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(message)
    
    def get_exit_code(self) -> int:
        """Get appropriate exit code for error type."""
        exit_codes = {
            CriticalErrorType.DATABASE_CONNECTION: 2,
            CriticalErrorType.AUTH_SERVICE: 3,
            CriticalErrorType.MISSING_ENV_VAR: 4,
            CriticalErrorType.PORT_BINDING: 5,
            CriticalErrorType.DEPENDENCY_MISSING: 6,
            CriticalErrorType.PERMISSION_DENIED: 7,
        }
        return exit_codes.get(self.error_type, 1)


class CriticalErrorHandler:
    """Handler for critical startup errors."""
    
    def __init__(self):
        """Initialize error handler."""
        self.errors_encountered = []
    
    def check_database_connection(self, connection_result: bool, error_msg: Optional[str] = None) -> None:
        """Check database connection and raise if critical."""
        if not connection_result:
            msg = error_msg or "Database connection failed"
            self.handle_critical_error(
                CriticalErrorType.DATABASE_CONNECTION,
                f"CRITICAL: {msg}",
                {"suggestion": "Check database configuration and ensure database is running"}
            )
    
    def check_auth_service(self, auth_available: bool, port: int) -> None:
        """Check auth service availability."""
        if not auth_available:
            self.handle_critical_error(
                CriticalErrorType.AUTH_SERVICE,
                f"CRITICAL: Auth service failed to start on port {port}",
                {"suggestion": f"Check if port {port} is available and auth service logs"}
            )
    
    def check_env_var(self, var_name: str, value: Optional[str]) -> None:
        """Check required environment variable."""
        if value is None or value == "":
            self.handle_critical_error(
                CriticalErrorType.MISSING_ENV_VAR,
                f"CRITICAL: Required environment variable '{var_name}' is not set",
                {"suggestion": f"Set {var_name} in .env file or environment"}
            )
    
    def check_port_binding(self, port: int, available: bool) -> None:
        """Check if port can be bound."""
        if not available:
            self.handle_critical_error(
                CriticalErrorType.PORT_BINDING,
                f"CRITICAL: Cannot bind to port {port}",
                {"suggestion": f"Check if another process is using port {port}"}
            )
    
    def handle_critical_error(self, error_type: CriticalErrorType, message: str, 
                            details: Optional[Dict[str, Any]] = None) -> None:
        """Handle a critical error by logging and raising."""
        error = CriticalError(error_type, message, details)
        self.errors_encountered.append(error)
        
        # Log the error with details
        logger.critical(message)
        if details and "suggestion" in details:
            logger.critical(f"Suggestion: {details['suggestion']}")
        
        # Print to stderr for visibility
        print(f"\n{message}", file=sys.stderr)
        if details and "suggestion" in details:
            print(f"Suggestion: {details['suggestion']}\n", file=sys.stderr)
        
        # Raise the error to stop execution
        raise error
    
    def exit_on_critical(self, error: CriticalError) -> None:
        """Exit the process with appropriate code."""
        exit_code = error.get_exit_code()
        logger.critical(f"Exiting with code {exit_code} due to critical error")
        sys.exit(exit_code)


# Global instance for easy access
critical_handler = CriticalErrorHandler()