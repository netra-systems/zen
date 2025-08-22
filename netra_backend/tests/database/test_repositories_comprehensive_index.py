"""
Comprehensive Repository Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 521-line monolith
"""

# Import all test classes from focused modules

import sys
from pathlib import Path

from test_framework import setup_test_path

from netra_backend.tests.test_database_connections import (
    TestClickHouseConnectionPool,
    TestDatabaseHealthChecks,
    TestMigrationRunnerSafety,
)
from netra_backend.tests.test_message_repository import TestMessageRepositoryQueries
from netra_backend.tests.test_repository_auth import (
    TestMetricRepositoryAggregation,
    TestOptimizationRepositoryStorage,
    TestUserRepositoryAuth,
)
from netra_backend.tests.test_thread_repository import TestThreadRepositoryOperations

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