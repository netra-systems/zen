"""
Comprehensive Repository Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 521-line monolith
"""

# Import all test classes from focused modules
from .test_thread_repository import TestThreadRepositoryOperations
from .test_message_repository import TestMessageRepositoryQueries
from .test_database_connections import (
    TestClickHouseConnectionPool,
    TestMigrationRunnerSafety,
    TestDatabaseHealthChecks
)
from .test_repository_auth import (
    TestUserRepositoryAuth,
    TestOptimizationRepositoryStorage,
    TestMetricRepositoryAggregation
)

# Re-export for backward compatibility
__all__ = [
    'TestThreadRepositoryOperations',
    'TestMessageRepositoryQueries',
    'TestClickHouseConnectionPool',
    'TestMigrationRunnerSafety',
    'TestDatabaseHealthChecks',
    'TestUserRepositoryAuth',
    'TestOptimizationRepositoryStorage',
    'TestMetricRepositoryAggregation'
]