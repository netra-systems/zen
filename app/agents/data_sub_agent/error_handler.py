"""Error handler for Data Sub Agent operations.

This module has been refactored into smaller, focused modules:
- error_types.py: Custom exception classes
- clickhouse_recovery.py: ClickHouse-specific recovery strategies
- data_fetching_recovery.py: Data fetching failure recovery
- metrics_recovery.py: Metrics calculation recovery
- fallback_providers.py: Fallback data sources
- error_handler_refactored.py: Main coordination layer

This file maintains backward compatibility by re-exporting key components.
"""

# Re-export main components for backward compatibility
from .error_types import (
    DataSubAgentError,
    ClickHouseQueryError,
    DataFetchingError,
    MetricsCalculationError
)

from .error_handler_refactored import (
    DataSubAgentErrorHandler,
    DataAnalysisCompensation,
    data_sub_agent_error_handler
)

from .clickhouse_recovery import ClickHouseRecoveryManager
from .data_fetching_recovery import DataFetchingRecoveryManager
from .metrics_recovery import MetricsRecoveryManager
from .fallback_providers import FallbackDataProvider

# Maintain legacy interface
__all__ = [
    'DataSubAgentError',
    'ClickHouseQueryError', 
    'DataFetchingError',
    'MetricsCalculationError',
    'DataSubAgentErrorHandler',
    'DataAnalysisCompensation',
    'data_sub_agent_error_handler',
    'ClickHouseRecoveryManager',
    'DataFetchingRecoveryManager',
    'MetricsRecoveryManager',
    'FallbackDataProvider'
]