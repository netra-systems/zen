"""
Corpus Generation Coverage Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 524-line monolith
"""

# Import all test classes from focused modules
from .test_corpus_lifecycle import TestCorpusLifecycle, TestWorkloadTypesCoverage
from .test_corpus_content_ops import TestContentGeneration, TestBatchProcessing
from .test_corpus_validation import TestValidationAndSafety, TestCorpusCloning
from .test_corpus_metadata import TestMetadataTracking, TestErrorRecovery

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