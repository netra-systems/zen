"""
Error Handler Module - Compatibility Alias

This module provides a compatibility alias for integration tests that expect
error_handler (singular) instead of error_handlers (plural).

CRITICAL ARCHITECTURAL COMPLIANCE:
- This is a COMPATIBILITY LAYER for integration tests
- Re-exports from error_handlers.py (SSOT)
- DO NOT add new functionality here

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: Test Infrastructure Stability
- Value Impact: Enables integration test collection and execution
- Strategic Impact: Maintains test coverage during system evolution
"""

# Re-export everything from the plural form (SSOT)
from netra_backend.app.core.error_handlers import *