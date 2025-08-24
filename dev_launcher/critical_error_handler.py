"""
Critical error handling for startup process.

Defines and handles critical errors that should stop the entire startup process.
"""

import logging
import sys
from enum import Enum
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class CriticalErrorType(Enum):
    """Types of critical errors that stop startup."""
    DATABASE_CONNECTION = 1
    AUTH_SERVICE = 2
    MISSING_ENV_VAR = 3
    PORT_BINDING = 4
    DEPENDENCY_MISSING = 5
    PERMISSION_DENIED = 6
    STARTUP_FAILURE = 7
    DOCKER_SERVICE_FAILURE = 8
    NETWORK_TIMEOUT = 9
    SERVICE_UNAVAILABLE = 10
    CONFIGURATION_ERROR = 11
    RACE_CONDITION = 12


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
            CriticalErrorType.STARTUP_FAILURE: 8,
            CriticalErrorType.DOCKER_SERVICE_FAILURE: 9,
            CriticalErrorType.NETWORK_TIMEOUT: 10,
            CriticalErrorType.SERVICE_UNAVAILABLE: 11,
            CriticalErrorType.CONFIGURATION_ERROR: 12,
            CriticalErrorType.RACE_CONDITION: 13,
        }
        return exit_codes.get(self.error_type, 1)
    
    def is_recoverable(self) -> bool:
        """Check if error is potentially recoverable."""
        recoverable_errors = {
            CriticalErrorType.NETWORK_TIMEOUT,
            CriticalErrorType.SERVICE_UNAVAILABLE,
            CriticalErrorType.DOCKER_SERVICE_FAILURE,
        }
        return self.error_type in recoverable_errors
    
    def get_retry_suggestion(self) -> Optional[str]:
        """Get retry suggestion for recoverable errors."""
        suggestions = {
            CriticalErrorType.NETWORK_TIMEOUT: "Retry with --verbose to see detailed timing",
            CriticalErrorType.SERVICE_UNAVAILABLE: "Check service status and retry",
            CriticalErrorType.DOCKER_SERVICE_FAILURE: "Restart Docker and try again",
        }
        return suggestions.get(self.error_type)


class CriticalErrorHandler:
    """Handler for critical startup errors with enhanced recovery capabilities."""
    
    def __init__(self, max_retries: int = 3, enable_graceful_degradation: bool = True):
        """Initialize error handler."""
        self.errors_encountered = []
        self.max_retries = max_retries
        self.enable_graceful_degradation = enable_graceful_degradation
        self.retry_counts = {}
        self.recovery_attempts = []
    
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
    
    def check_port_binding(self, port: int, available: bool, service_name: str = "service") -> None:
        """Check if port can be bound with enhanced conflict resolution."""
        if not available:
            # Try to identify what's using the port
            process_info = self._identify_port_user(port)
            suggestion = f"Port {port} is in use"
            
            if process_info:
                suggestion += f" by {process_info}. "
                # Provide specific remediation based on process
                if "node" in process_info.lower() or "npm" in process_info.lower():
                    suggestion += "Try: pkill -f node or taskkill /F /IM node.exe"
                elif "python" in process_info.lower() or "uvicorn" in process_info.lower():
                    suggestion += "Try: pkill -f uvicorn or taskkill /F /IM python.exe"
                else:
                    suggestion += f"Try using a different port or stopping the conflicting process"
            else:
                suggestion += f". Use 'lsof -i :{port}' (Unix) or 'netstat -ano | findstr :{port}' (Windows) to identify the process"
            
            self.handle_critical_error(
                CriticalErrorType.PORT_BINDING,
                f"CRITICAL: Cannot bind {service_name} to port {port}",
                {
                    "suggestion": suggestion,
                    "port": port,
                    "service": service_name,
                    "process_info": process_info
                }
            )
    
    def check_docker_service(self, service_name: str, available: bool, error_msg: Optional[str] = None) -> None:
        """Check Docker service availability with recovery suggestions."""
        if not available:
            suggestion = f"Docker service '{service_name}' is not available. "
            
            if error_msg and "connection refused" in error_msg.lower():
                suggestion += "Docker daemon may not be running. Try: 'docker ps' to verify Docker is accessible"
            elif error_msg and "permission denied" in error_msg.lower():
                suggestion += "Docker permission issue. Try: 'sudo docker ps' or add user to docker group"
            else:
                suggestion += "Check Docker installation and ensure the service container is running"
            
            # Check if this is a recoverable error with graceful degradation
            if self.enable_graceful_degradation:
                logger.warning(f"Docker service {service_name} unavailable - will attempt graceful degradation")
                return  # Don't raise critical error, allow degradation
            
            self.handle_critical_error(
                CriticalErrorType.DOCKER_SERVICE_FAILURE,
                f"CRITICAL: Docker service '{service_name}' failed - {error_msg or 'Service unavailable'}",
                {
                    "suggestion": suggestion,
                    "service_name": service_name,
                    "error_details": error_msg
                }
            )
    
    def check_network_timeout(self, operation: str, timeout_seconds: float, error_msg: Optional[str] = None) -> None:
        """Handle network timeout errors with retry suggestions."""
        suggestion = f"Network operation '{operation}' timed out after {timeout_seconds}s. "
        
        if timeout_seconds < 10:
            suggestion += "Try increasing timeout with --verbose flag or check network connectivity"
        else:
            suggestion += "Check if the target service is responding and network connectivity is stable"
        
        # Check for retry attempts
        retry_key = f"timeout_{operation}"
        current_retries = self.retry_counts.get(retry_key, 0)
        
        if current_retries < self.max_retries:
            self.retry_counts[retry_key] = current_retries + 1
            logger.warning(f"Network timeout for {operation} (attempt {current_retries + 1}/{self.max_retries}) - will retry")
            return  # Don't raise critical error yet, allow retry
        
        self.handle_critical_error(
            CriticalErrorType.NETWORK_TIMEOUT,
            f"CRITICAL: Network timeout for '{operation}' after {self.max_retries} retries",
            {
                "suggestion": suggestion,
                "operation": operation,
                "timeout_seconds": timeout_seconds,
                "retry_attempts": current_retries,
                "error_details": error_msg
            }
        )
    
    def check_race_condition(self, operation: str, component_a: str, component_b: str, details: Optional[str] = None) -> None:
        """Handle race condition detection."""
        suggestion = f"Race condition detected between {component_a} and {component_b} during {operation}. "
        suggestion += "This may be resolved by adjusting startup timing or using sequential mode (--no-parallel)"
        
        self.handle_critical_error(
            CriticalErrorType.RACE_CONDITION,
            f"CRITICAL: Race condition in {operation} between {component_a} and {component_b}",
            {
                "suggestion": suggestion,
                "operation": operation,
                "component_a": component_a,
                "component_b": component_b,
                "details": details
            }
        )
    
    def _identify_port_user(self, port: int) -> Optional[str]:
        """Identify what process is using a port."""
        import subprocess
        import sys
        
        try:
            if sys.platform == "win32":
                result = subprocess.run(
                    f"netstat -ano | findstr :{port}",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        parts = line.split()
                        if len(parts) >= 5 and f":{port}" in parts[1]:
                            pid = parts[-1]
                            # Get process name
                            proc_result = subprocess.run(
                                f'tasklist /FI "PID eq {pid}" /FO CSV',
                                shell=True, capture_output=True, text=True, timeout=3
                            )
                            if proc_result.stdout:
                                proc_lines = proc_result.stdout.strip().split('\n')
                                if len(proc_lines) > 1:
                                    return proc_lines[1].split(',')[0].strip('"')
            else:
                result = subprocess.run(
                    f"lsof -i :{port}",
                    shell=True, capture_output=True, text=True, timeout=5
                )
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # Skip header
                        parts = lines[1].split()
                        if len(parts) > 0:
                            return parts[0]  # Process name
        except Exception as e:
            logger.debug(f"Failed to identify port user: {e}")
        
        return None
    
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