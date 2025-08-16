"""Transaction error handling and classification module.

Handles error detection, classification, and retry logic for database transactions.
Focused module adhering to 8-line function limit and modular architecture.
"""

from sqlalchemy.exc import OperationalError, DisconnectionError


class TransactionError(Exception):
    """Base exception for transaction-related errors."""
    pass


class DeadlockError(TransactionError):
    """Raised when a deadlock is detected."""
    pass


class ConnectionError(TransactionError):
    """Raised when connection issues occur."""
    pass


def _has_deadlock_keywords(error_msg: str) -> bool:
    """Check if error message contains deadlock keywords."""
    deadlock_keywords = ['deadlock', 'lock timeout', 'lock wait timeout']
    return any(keyword in error_msg for keyword in deadlock_keywords)


def _has_connection_keywords(error_msg: str) -> bool:
    """Check if error message contains connection keywords."""
    connection_keywords = ['connection', 'network', 'timeout', 'broken pipe']
    return any(keyword in error_msg for keyword in connection_keywords)


def _is_disconnection_retryable(error: Exception, enable_connection_retry: bool) -> bool:
    """Check if disconnection error is retryable."""
    return (isinstance(error, DisconnectionError) and 
            enable_connection_retry)


def _is_operational_error_retryable(error: OperationalError, enable_deadlock_retry: bool, enable_connection_retry: bool) -> bool:
    """Check if operational error is retryable."""
    error_msg = str(error).lower()
    
    if _has_deadlock_keywords(error_msg):
        return enable_deadlock_retry
    
    if _has_connection_keywords(error_msg):
        return enable_connection_retry
    
    return False


def is_retryable_error(error: Exception, enable_deadlock_retry: bool, enable_connection_retry: bool) -> bool:
    """Check if error is retryable based on configuration."""
    if _is_disconnection_retryable(error, enable_connection_retry):
        return True
    
    if isinstance(error, OperationalError):
        return _is_operational_error_retryable(error, enable_deadlock_retry, enable_connection_retry)
    
    return False


def _classify_deadlock_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify deadlock-related operational errors."""
    if _has_deadlock_keywords(error_msg):
        return DeadlockError(f"Deadlock detected: {error}")
    return error


def _classify_connection_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify connection-related operational errors."""
    if _has_connection_keywords(error_msg):
        return ConnectionError(f"Connection error: {error}")
    return error


def _classify_operational_error(error: OperationalError) -> Exception:
    """Classify operational errors into specific types."""
    error_msg = str(error).lower()
    
    classified = _classify_deadlock_error(error, error_msg)
    if classified != error:
        return classified
        
    return _classify_connection_error(error, error_msg)


def classify_error(error: Exception) -> Exception:
    """Classify and potentially wrap errors."""
    if isinstance(error, OperationalError):
        return _classify_operational_error(error)
    return error