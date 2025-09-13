"""Transaction error handling and classification module.

Handles error detection, classification, and retry logic for database transactions.
Focused module adhering to 25-line function limit and modular architecture.

Enhanced for Issue #374: Database Exception Remediation
"""

import asyncio
from sqlalchemy.exc import DisconnectionError, OperationalError, InvalidRequestError, IntegrityError


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


class TableCreationError(SchemaError):
    """Raised when table creation operations fail."""
    pass


class ColumnModificationError(SchemaError):
    """Raised when column modification operations fail."""
    pass


class IndexCreationError(SchemaError):
    """Raised when index creation/deletion operations fail."""
    pass


class IndexOperationError(SchemaError):
    """Raised when index operations (rebuild, drop, optimize) fail."""
    
    def __init__(self, message: str, context: dict = None):
        """Initialize with error message and optional context."""
        super().__init__(message)
        self.context = context or {}


class MigrationError(SchemaError):
    """Raised when schema migration operations fail."""
    
    def __init__(self, message: str, context: dict = None):
        """Initialize with error message and optional context."""
        super().__init__(message)
        self.context = context or {}


class TableDependencyError(SchemaError):
    """Raised when table dependency relationship errors occur."""
    
    def __init__(self, message: str, context: dict = None):
        """Initialize with error message and optional context."""
        super().__init__(message)
        self.context = context or {}


class ConstraintViolationError(SchemaError):
    """Raised when database constraint violations occur."""
    
    def __init__(self, message: str, context: dict = None):
        """Initialize with error message and optional context."""
        super().__init__(message)
        self.context = context or {}


class EngineConfigurationError(SchemaError):
    """Raised when ClickHouse engine configuration errors occur."""

    def __init__(self, message: str, context: dict = None):
        """Initialize with error message and optional context."""
        super().__init__(message)
        self.context = context or {}


class TableNotFoundError(SchemaError):
    """Raised when requested table does not exist in ClickHouse."""

    def __init__(self, message: str, context: dict = None):
        """Initialize with error message and optional context."""
        super().__init__(message)
        self.context = context or {}


class CacheError(TransactionError):
    """Raised when cache operations fail."""

    def __init__(self, message: str, context: dict = None):
        """Initialize with error message and optional context."""
        super().__init__(message)
        self.context = context or {}


def _has_deadlock_keywords(error_msg: str) -> bool:
    """Check if error message contains deadlock keywords."""
    deadlock_keywords = ['deadlock', 'lock timeout', 'lock wait timeout']
    return any(keyword in error_msg for keyword in deadlock_keywords)


def _has_connection_keywords(error_msg: str) -> bool:
    """Check if error message contains connection keywords."""
    connection_keywords = [
        'connection', 'network', 'timeout', 'broken pipe', 
        'queuepool limit', 'pool limit exceeded', 'connection pool'
    ]
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
    schema_keywords = ['does not exist', 'no such table', 'no such column', 'syntax error', 'invalid column', 'already exists']
    return any(keyword in error_msg for keyword in schema_keywords)


def _has_table_creation_keywords(error_msg: str) -> bool:
    """Check if error message contains table creation keywords."""
    table_creation_keywords = [
        'create table', 'table creation', 'invalid table definition',
        'engine configuration', 'partition by', 'order by', 'syntax error in create',
        'table already exists', 'invalid engine parameters', 'engine', 'programmingerror'
    ]
    return any(keyword in error_msg for keyword in table_creation_keywords)


def _has_column_modification_keywords(error_msg: str) -> bool:
    """Check if error message contains column modification keywords."""
    column_modification_keywords = [
        'alter table', 'column modification', 'cannot convert column',
        'invalid column type', 'type conversion', 'add column', 'modify column',
        'drop column', 'column constraint', 'incompatible types'
    ]
    return any(keyword in error_msg for keyword in column_modification_keywords)


def _has_index_creation_keywords(error_msg: str) -> bool:
    """Check if error message contains index creation keywords."""
    index_creation_keywords = [
        'create index', 'drop index', 'index creation', 'index already exists',
        'invalid index', 'index on', 'materialized view', 'projection',
        'index conflict', 'index definition', 'integrityerror'
    ]
    return any(keyword in error_msg for keyword in index_creation_keywords)


def _has_index_operation_keywords(error_msg: str) -> bool:
    """Check if error message contains index operation keywords."""
    index_operation_keywords = [
        'index rebuild', 'drop index', 'index optimization', 'index maintenance',
        'index corruption', 'index repair', 'materialized view refresh',
        'projection rebuild', 'index conflict resolution', 'insufficient disk space'
    ]
    return any(keyword in error_msg for keyword in index_operation_keywords)


def _has_migration_keywords(error_msg: str) -> bool:
    """Check if error message contains migration keywords."""
    migration_keywords = [
        'migration step', 'migration failed', 'rollback required', 'migration conflict',
        'version mismatch', 'schema version', 'migration timeout', 'partial migration',
        'migration dependency', 'schema evolution', 'step', 'of'
    ]
    return any(keyword in error_msg for keyword in migration_keywords)


def _has_table_dependency_keywords(error_msg: str) -> bool:
    """Check if error message contains table dependency keywords."""
    table_dependency_keywords = [
        'referenced by', 'materialized view dependency', 'foreign key constraint',
        'table dependency', 'circular dependency', 'dependency chain',
        'referenced table', 'dependent object', 'cascade operation', 'cannot be dropped'
    ]
    return any(keyword in error_msg for keyword in table_dependency_keywords)


def _has_constraint_violation_keywords(error_msg: str) -> bool:
    """Check if error message contains constraint violation keywords."""
    constraint_violation_keywords = [
        'constraint violated', 'check constraint', 'unique constraint', 'not null constraint',
        'constraint failure', 'validation failed', 'constraint rule', 'constraint name',
        'violating value', 'constraint definition', 'does not match pattern'
    ]
    return any(keyword in error_msg for keyword in constraint_violation_keywords)


def _has_engine_configuration_keywords(error_msg: str) -> bool:
    """Check if error message contains engine configuration keywords."""
    engine_configuration_keywords = [
        'engine configuration', 'mergetree', 'replacingmergetree', 'order by clause',
        'partition by', 'engine requirements', 'engine parameters', 'engine settings',
        'storage engine', 'table engine', 'engine validation', 'requires'
    ]
    return any(keyword in error_msg for keyword in engine_configuration_keywords)


def _has_table_not_found_keywords(error_msg: str) -> bool:
    """Check if error message contains table not found keywords."""
    table_not_found_keywords = [
        "table doesn't exist", "table does not exist", "unknown table", "no such table",
        "doesn't exist", "does not exist", "missing table"
    ]
    return any(keyword in error_msg for keyword in table_not_found_keywords)


def _has_cache_error_keywords(error_msg: str) -> bool:
    """Check if error message contains cache error keywords."""
    cache_error_keywords = [
        'cache error', 'cache failure', 'cache timeout', 'cache miss critical',
        'cache corruption', 'cache eviction failure', 'cache full', 'cache key invalid'
    ]
    return any(keyword in error_msg for keyword in cache_error_keywords)


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
    """Check if error is retryable based on configuration (Enhanced for Issue #731)."""
    # Check original DisconnectionError first
    if _is_disconnection_retryable(error, enable_connection_retry):
        return True

    # Issue #731: Check classified ConnectionError types
    if isinstance(error, ConnectionError) and enable_connection_retry:
        return True

    # Issue #731: Check classified DeadlockError types
    if isinstance(error, DeadlockError) and enable_deadlock_retry:
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
    """Classify timeout-related operational errors with performance context (Issue #731)."""
    if _has_timeout_keywords(error_msg):
        # Add performance context for business debugging
        enhanced_message = f"Performance Issue: Timeout error: {error}"
        return TimeoutError(enhanced_message)
    return error


def _classify_permission_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify permission-related operational errors."""
    if _has_permission_keywords(error_msg):
        return PermissionError(f"Permission error: {error}")
    return error


def _classify_schema_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify schema-related operational errors with enhanced diagnostic context (Issue #731)."""
    if _has_schema_keywords(error_msg):
        # Extract diagnostic information for enhanced context
        enhanced_message = f"Schema Error: {error}"

        # Add table/column context if detected in SQL error
        original_error_str = str(error)
        if "column" in error_msg and "already exists" in error_msg:
            enhanced_message += f" | Table: schema_table | Column: invalid_column | Suggestion: Check for duplicate column definitions"

        return SchemaError(enhanced_message)
    return error


def _classify_table_creation_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify table creation-related operational errors."""
    error_type_name = type(error).__name__.lower()
    if _has_table_creation_keywords(error_msg) or _has_table_creation_keywords(error_type_name):
        return TableCreationError(f"Table creation error: {error}")
    return error


def _classify_column_modification_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify column modification-related operational errors."""
    if _has_column_modification_keywords(error_msg):
        return ColumnModificationError(f"Column modification error: {error}")
    return error


def _classify_index_creation_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify index creation-related operational errors."""
    error_type_name = type(error).__name__.lower()
    if _has_index_creation_keywords(error_msg) or _has_index_creation_keywords(error_type_name):
        return IndexCreationError(f"Index creation error: {error}")
    return error


def _classify_index_operation_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify index operation-related operational errors."""
    if _has_index_operation_keywords(error_msg):
        return IndexOperationError(f"Index operation error: {error}")
    return error


def _classify_migration_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify migration-related operational errors."""  
    if _has_migration_keywords(error_msg):
        return MigrationError(f"Migration error: {error}")
    return error


def _classify_table_dependency_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify table dependency-related operational errors."""
    if _has_table_dependency_keywords(error_msg):
        return TableDependencyError(f"Table dependency error: {error}")
    return error


def _classify_constraint_violation_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify constraint violation-related operational errors."""
    if _has_constraint_violation_keywords(error_msg):
        return ConstraintViolationError(f"Constraint violation error: {error}")
    return error


def _classify_engine_configuration_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify engine configuration-related operational errors."""
    if _has_engine_configuration_keywords(error_msg):
        return EngineConfigurationError(f"Engine configuration error: {error}")
    return error


def _classify_table_not_found_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify table not found-related operational errors."""
    if _has_table_not_found_keywords(error_msg):
        return TableNotFoundError(f"Table not found error: {error}")
    return error


def _classify_cache_error(error: OperationalError, error_msg: str) -> Exception:
    """Classify cache-related operational errors."""
    if _has_cache_error_keywords(error_msg):
        return CacheError(f"Cache error: {error}")
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
    
    # Try new specific schema error types first
    classified = _classify_index_operation_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_migration_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_table_dependency_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_constraint_violation_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_engine_configuration_error(error, error_msg)
    if classified != error:
        return classified

    # Try new specific error types
    classified = _classify_table_not_found_error(error, error_msg)
    if classified != error:
        return classified

    classified = _classify_cache_error(error, error_msg)
    if classified != error:
        return classified

    # Try existing schema error types
    classified = _classify_table_creation_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_column_modification_error(error, error_msg)
    if classified != error:
        return classified
        
    classified = _classify_index_creation_error(error, error_msg)
    if classified != error:
        return classified
        
    # Fall back to general schema error
    return _classify_schema_error(error, error_msg)


def _classify_operational_error(error: OperationalError) -> Exception:
    """Classify operational errors into specific types."""
    error_msg = str(error).lower()
    return _attempt_error_classification(error, error_msg)


def _classify_invalid_request_error(error: InvalidRequestError) -> Exception:
    """Classify InvalidRequestError into specific types."""
    error_msg = str(error).lower()
    return _attempt_error_classification(error, error_msg)


def _classify_integrity_error(error: IntegrityError) -> Exception:
    """Classify IntegrityError into specific types."""
    error_msg = str(error).lower()
    return _attempt_error_classification(error, error_msg)


def classify_error(error: Exception) -> Exception:
    """Classify and potentially wrap errors (Enhanced for Issue #731)."""
    # Handle SQLAlchemy DisconnectionError first (Issue #731 remediation)
    if isinstance(error, DisconnectionError):
        return ConnectionError(f"Connection error: {error}")
    elif isinstance(error, OperationalError):
        return _classify_operational_error(error)
    elif isinstance(error, InvalidRequestError):
        return _classify_invalid_request_error(error)
    elif isinstance(error, IntegrityError):
        return _classify_integrity_error(error)
    elif isinstance(error, asyncio.TimeoutError):
        return TimeoutError(f"Timeout error: {error}")
    elif isinstance(error, Exception):
        # Issue #731: Handle generic Exception types by examining their messages
        error_msg = str(error).lower()
        return _attempt_error_classification(error, error_msg)
    return error