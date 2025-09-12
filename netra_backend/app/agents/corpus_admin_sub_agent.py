# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-09-04T12:30:00.000000+00:00
# Agent: Claude Opus 4.1
# Context: SSOT Consolidation - Redirecting to UnifiedCorpusAdmin
# Git: critical-remediation-20250823
# Change: Refactor | Scope: Major | Risk: High
# Session: corpus-admin-ssot-consolidation | Seq: 1
# Review: Pending | Score: 90
# ================================

"""
Corpus Admin Sub Agent - SSOT Redirection Module

This module redirects all corpus admin imports to the new SSOT UnifiedCorpusAdmin.
Part of the corpus admin consolidation effort (30 files  ->  1 file).

CRITICAL: This is a compatibility layer during migration to UnifiedCorpusAdmin.
All functionality has been consolidated into netra_backend.app.admin.corpus.unified_corpus_admin
"""

import warnings

# Import from NEW SSOT unified implementation
from netra_backend.app.admin.corpus.compatibility import (
    CorpusAdminSubAgent,  # Compatibility wrapper
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
)

# CorpusStatistics is in UnifiedCorpusAdmin but not exported via compatibility
# Create a simple alias for backward compatibility
class CorpusStatistics:
    """Deprecated: Use CorpusMetadata from UnifiedCorpusAdmin instead."""
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CorpusStatistics is deprecated. Use CorpusMetadata instead.",
            DeprecationWarning,
            stacklevel=2
        )

# Maintain backward compatibility - all legacy code removed
# All classes and functions now imported from corpus_admin module

__all__ = [
    "CorpusAdminSubAgent",
    "CorpusOperation", 
    "CorpusType",
    "CorpusMetadata",
    "CorpusOperationRequest",
    "CorpusOperationResult",
    "CorpusStatistics"
]