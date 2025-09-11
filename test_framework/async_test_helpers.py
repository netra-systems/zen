"""Async Test Helpers - SSOT Compatibility Module

CRITICAL TEST INFRASTRUCTURE COMPATIBILITY: This module provides compatibility imports
for tests that expect async test helpers at the top level of test_framework.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Test Infrastructure
- Business Goal: Enable Golden Path integration testing (protects $500K+ ARR)
- Value Impact: Maintains test infrastructure compatibility during SSOT refactoring
- Revenue Impact: Ensures async test functionality works reliably

COMPLIANCE NOTES:
- This is a COMPATIBILITY MODULE only - new code should import from ssot package
- Maintains backward compatibility for existing tests
- Follows SSOT principles by re-exporting from the canonical ssot location
- Provides proper async test helper functionality

IMPORT GUIDANCE:
- DEPRECATED: from test_framework.async_test_helpers import AsyncTestHelper
- RECOMMENDED: from test_framework.ssot.async_test_helpers import AsyncTestHelper
"""

from test_framework.ssot.async_test_helpers import *

# Re-export everything from the SSOT location for backward compatibility
import test_framework.ssot.async_test_helpers as _ssot_helpers

# Get all public attributes from the SSOT module
__all__ = getattr(_ssot_helpers, '__all__', [attr for attr in dir(_ssot_helpers) if not attr.startswith('_')])