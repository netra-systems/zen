"""
Unified State Persistence - Backward Compatibility Module

This module exists for backward compatibility with test files that expect
a unified state persistence implementation. It re-exports the SSOT
StatePersistenceService from the main state_persistence.py module.

Issue #762 Phase 2 Remediation: Resolves module import mismatches in Golden Path tests.
"""

# Import the SSOT implementation
from netra_backend.app.services.state_persistence import (
    StatePersistenceService,
    StateCacheManager,
    UnifiedStatePersistence  # This is an alias to StatePersistenceService
)

# Re-export for backward compatibility
__all__ = ['UnifiedStatePersistence', 'StatePersistenceService', 'StateCacheManager']