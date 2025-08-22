"""
Comprehensive Repository Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 521-line monolith
"""

# Import all test classes from focused modules

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from .test_database_connections import (
    # Add project root to path
    TestClickHouseConnectionPool,
    TestDatabaseHealthChecks,
    TestMigrationRunnerSafety,
)
from .test_message_repository import TestMessageRepositoryQueries
from .test_repository_auth import (
    TestMetricRepositoryAggregation,
    TestOptimizationRepositoryStorage,
    TestUserRepositoryAuth,
)
from .test_thread_repository import TestThreadRepositoryOperations

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