# AI AGENT MODIFICATION METADATA
# ================================
# Timestamp: 2025-08-10T21:05:00.000000+00:00
# Agent: Claude Opus 4.1 claude-opus-4-1-20250805
# Context: Creating CorpusAdminsubAgent for corpus management
# Git: v8 | dirty
# Change: New Feature | Scope: Component | Risk: Medium
# Session: corpus-admin-agent-creation | Seq: 1
# Review: Pending | Score: 85
# ================================

"""
Corpus Admin Sub Agent - Legacy Compatibility Module

This module maintains backward compatibility while delegating to the new
modular corpus_admin package. All functionality has been moved to focused
modules under 300 lines each.
"""

# Import from modular implementation
from .corpus_admin import (
    CorpusAdminSubAgent,
    CorpusOperation,
    CorpusType,
    CorpusMetadata,
    CorpusOperationRequest,
    CorpusOperationResult,
    CorpusStatistics
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