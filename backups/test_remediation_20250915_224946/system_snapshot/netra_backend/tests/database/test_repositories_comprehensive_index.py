import pytest
"""
Comprehensive Repository Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 521-line monolith
"""""

# Import all test classes from focused modules

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from netra_backend.tests.database.test_database_connections import (
TestClickHouseConnectionPool,
TestDatabaseHealthChecks,
TestMigrationRunnerSafety,
)
from netra_backend.tests.database.test_message_repository import TestMessageRepositoryQueries
from netra_backend.tests.database.test_repository_auth import (
TestOptimizationRepositoryStorage,
)
# from netra_backend.tests.database.test_thread_repository import TestThreadRepositoryOperations  # File missing

# Re-export for backward compatibility
__all__ = [
# 'TestThreadRepositoryOperations',  # File missing
'TestMessageRepositoryQueries',
'TestClickHouseConnectionPool',
'TestMigrationRunnerSafety',
'TestDatabaseHealthChecks',
'TestOptimizationRepositoryStorage',
]