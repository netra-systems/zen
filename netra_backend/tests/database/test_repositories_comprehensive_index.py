"""
Comprehensive Repository Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 521-line monolith
"""

# Import all test classes from focused modules
from netra_backend.tests.test_thread_repository import TestThreadRepositoryOperations
from netra_backend.tests.test_message_repository import TestMessageRepositoryQueries
from netra_backend.tests.test_database_connections import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    TestClickHouseConnectionPool,
    TestMigrationRunnerSafety,
    TestDatabaseHealthChecks
)
from netra_backend.tests.test_repository_auth import (
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