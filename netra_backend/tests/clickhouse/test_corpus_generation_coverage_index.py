"""
Corpus Generation Coverage Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 524-line monolith
"""

# Import all test classes from focused modules

# Add project root to path

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from netra_backend.tests.test_corpus_lifecycle import TestCorpusLifecycle, TestWorkloadTypesCoverage
from netra_backend.tests.test_corpus_content_ops import TestContentGeneration, TestBatchProcessing
from netra_backend.tests.test_corpus_validation import TestValidationAndSafety, TestCorpusCloning
from netra_backend.tests.test_corpus_metadata import TestMetadataTracking, TestErrorRecovery

# Add project root to path

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