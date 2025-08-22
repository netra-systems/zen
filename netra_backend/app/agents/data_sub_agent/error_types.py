"""Data Sub Agent specific error types.

Defines custom exception classes for data analysis operations including
ClickHouse queries, data fetching, and metrics calculations.
"""

from typing import Dict, Optional

from netra_backend.app.agents.error_handler import AgentError, ErrorContext
from netra_backend.app.core.error_codes import ErrorSeverity


class DataSubAgentError(AgentError):
    """Specific error type for data sub agent operations."""
    
    def __init__(
        self,
        message: str,
        operation: str,
        query_info: Optional[Dict] = None,
        context: Optional[ErrorContext] = None
    ):
        """Initialize data sub agent error."""
        super().__init__(
            message=message,
            severity=ErrorSeverity.MEDIUM,
            context=context,
            recoverable=True
        )
        self.operation = operation
        self.query_info = query_info or {}


class ClickHouseQueryError(DataSubAgentError):
    """Error when ClickHouse queries fail."""
    
    def __init__(
        self,
        query: str,
        error_details: str,
        context: Optional[ErrorContext] = None
    ):
        """Initialize ClickHouse query error."""
        super().__init__(
            message=f"ClickHouse query failed: {error_details}",
            operation="clickhouse_query",
            query_info={'query': query, 'error': error_details},
            context=context
        )
        self.query = query
        self.error_details = error_details


class DataFetchingError(DataSubAgentError):
    """Error when data fetching operations fail."""
    
    def __init__(
        self,
        data_source: str,
        time_range: Dict,
        context: Optional[ErrorContext] = None
    ):
        """Initialize data fetching error."""
        super().__init__(
            message=f"Data fetching failed from {data_source}",
            operation="data_fetching",
            query_info={'source': data_source, 'time_range': time_range},
            context=context
        )
        self.data_source = data_source
        self.time_range = time_range


class MetricsCalculationError(DataSubAgentError):
    """Error when metrics calculation fails."""
    
    def __init__(
        self,
        metric_type: str,
        data_size: int,
        context: Optional[ErrorContext] = None
    ):
        """Initialize metrics calculation error."""
        super().__init__(
            message=f"Metrics calculation failed for {metric_type}",
            operation="metrics_calculation",
            query_info={'metric_type': metric_type, 'data_size': data_size},
            context=context
        )
        self.metric_type = metric_type
        self.data_size = data_size