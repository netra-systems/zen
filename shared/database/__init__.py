"""Shared database utilities and SSOT patterns."""

from shared.database.ssot_query_executor import SSOTDatabaseQueryExecutor, ssot_query_executor, DatabaseQueryError

__all__ = [
    "SSOTDatabaseQueryExecutor",
    "ssot_query_executor", 
    "DatabaseQueryError"
]
