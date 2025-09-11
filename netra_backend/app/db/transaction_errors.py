"""Transaction error handling and classification module.

Handles error detection, classification, and retry logic for database transactions.
Focused module adhering to 25-line function limit and modular architecture.

Enhanced for Issue #374: Database Exception Remediation
"""

from sqlalchemy.exc import DisconnectionError, OperationalError


class TransactionError(Exception):
    """Base exception for transaction-related errors."""
    pass


class DeadlockError(TransactionError):
    """Raised when a deadlock is detected."""
    pass


class ConnectionError(TransactionError):
    """Raised when connection issues occur."""
    pass


class TimeoutError(TransactionError):
    """Raised when database operations timeout."""
    pass


class PermissionError(TransactionError):
    """Raised when database permission issues occur."""
    pass


class SchemaError(TransactionError):
    """Raised when database schema issues occur."""
    pass


def _has_deadlock_keywords(error_msg: str) -> bool:
    """Check if error message contains deadlock keywords."""
    deadlock_keywords = ['deadlock', 'lock timeout', 'lock wait timeout']
    return any(keyword in error_msg for keyword in deadlock_keywords)


def _has_connection_keywords(error_msg: str) -> bool:
    """Check if error message contains connection keywords."""
    connection_keywords = ['connection', 'network', 'timeout', 'broken pipe']
    return any(keyword in error_msg for keyword in connection_keywords)


def _has_timeout_keywords(error_msg: str) -> bool:
    """Check if error message contains timeout keywords."""
    timeout_keywords = ['timeout', 'timed out', 'time limit exceeded']
    return any(keyword in error_msg for keyword in timeout_keywords)


def _has_permission_keywords(error_msg: str) -> bool:
    """Check if error message contains permission keywords."""
    permission_keywords = ['permission denied', 'access denied', 'insufficient privileges', 'authentication failed']
    return any(keyword in error_msg for keyword in permission_keywords)


def _has_schema_keywords(error_msg: str) -> bool:
    """Check if error message contains schema keywords."""
    schema_keywords = ['does not exist', 'no such table', 'no such column', 'syntax error', 'invalid column']
    return any(keyword in error_msg for keyword in schema_keywords)


def _is_disconnection_retryable(error: Exception, enable_connection_retry: bool) -> bool:
    """Check if disconnection error is retryable."""
    return (isinstance(error, DisconnectionError) and 
            enable_connection_retry)


def _check_deadlock_retry_eligibility(error_msg: str, enable_deadlock_retry: bool) -> bool:
    """Check if deadlock error is eligible for retry."""
    if _has_deadlock_keywords(error_msg):
        return enable_deadlock_retry
    return False


def _check_connection_retry_eligibility(error_msg: str, enable_connection_retry: bool) -> bool:
    """Check if connection error is eligible for retry."""
    if _has_connection_keywords(error_msg):
        return enable_connection_retry
    return False


def _is_operational_error_retryable(error: OperationalError, enable_deadlock_retry: bool, enable_connection_retry: bool) -> bool:
    """Check if operational error is retryable."""
    error_msg = str(error).lower()
    
    if _check_deadlock_retry_eligibility(error_msg, enable_deadlock_retry):
        return True
    
    return _check_connection_retry_eligibility(error_msg, enable_connection_retry)


def _check_operational_error_retry(error: Exception, enable_deadlock_retry: bool, enable_connection_retry: bool) -> bool:
    """Check if operational error is retryable."""
    if isinstance(error, OperationalError):
        return _is_operational_error_retryable(error, enable_deadlock_retry, enable_connection_retry)
    return False


def is_retryable_error(error: Exception, enable_deadlock_retry: bool, enable_connection_retry: bool) -> bool:
    """Check if error is retryable based on configuration."""
    if _is_disconnection_retryable(error, enable_connection_retry):
        return True
    
    return _check_operational_error_retry(error, enable_deadlock_retry, enable_connection_retry)


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


def _classify_timeout_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify timeout-related operational errors."""
    if _has_timeout_keywords(error_msg):
        return TimeoutError(f"Timeout error: {error}")
    return error


def _classify_permission_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify permission-related operational errors."""
    if _has_permission_keywords(error_msg):
        return PermissionError(f"Permission error: {error}")
    return error


def _classify_schema_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify schema-related operational errors."""
    if _has_schema_keywords(error_msg):
        return SchemaError(f"Schema error: {error}")
    return error


def _attempt_error_classification(error: OperationalError, error_msg: str) -> Exception:
    """Attempt to classify error, returning original if no match."""
    # Try each classification in priority order
    classified = _classify_deadlock_error(error, error_msg)
    if classified != error:
        return classified
    
    classified = _classify_connection_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_timeout_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_permission_error(error, error_msg)
    if classified != error:
        return classified
        
    return _classify_schema_error(error, error_msg)


def _classify_operational_error(error: OperationalError) -> Exception:
    """Classify operational errors into specific types."""
    error_msg = str(error).lower()
    return _attempt_error_classification(error, error_msg)


def classify_error(error: Exception) -> Exception:
    """Classify and potentially wrap errors."""
    if isinstance(error, OperationalError):
        return _classify_operational_error(error)
    return error