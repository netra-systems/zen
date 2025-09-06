import pytest
"""
Corpus Generation Coverage Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 524-line monolith
"""""

# Import all test classes from focused modules

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

from netra_backend.tests.clickhouse.test_corpus_content_ops import (
TestBatchProcessing,
TestContentGeneration,
)
from netra_backend.tests.clickhouse.test_corpus_lifecycle import (
TestCorpusLifecycle,
TestWorkloadTypesCoverage,
)
from netra_backend.tests.test_corpus_metadata import (
TestErrorRecovery,
TestMetadataTracking,
)
from netra_backend.tests.test_corpus_validation import (
TestCorpusCloning,
TestValidationAndSafety,
)

# Re-export for backward compatibility
__all__ = [
'TestCorpusLifecycle',
'TestWorkloadTypesCoverage',
'TestContentGeneration',
'TestBatchProcessing',
'TestValidationAndSafety',
'TestCorpusCloning',
'TestMetadataTracking',
'TestErrorRecovery'
]