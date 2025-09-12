"""
SSOT REDIRECTION MODULE - PHASE 1 EMERGENCY STABILIZATION
==========================================================
CRITICAL BUSINESS PROTECTION: This module redirects to canonical SSOT UnifiedTestRunner
while maintaining zero business disruption during the SSOT violation remediation.

 WARNING: [U+FE0F]  SSOT VIOLATION ALERT  WARNING: [U+FE0F]
This duplicate UnifiedTestRunner implementation violates SSOT principle.
CANONICAL SSOT: tests/unified_test_runner.py:UnifiedTestRunner

BUSINESS PROTECTION STRATEGY:
- Immediate redirection to compatibility layer
- Zero API changes for Golden Path validation
- $500K+ ARR chat functionality testing preserved
- Rollback capability if issues detected

REMEDIATION PHASES:
Phase 1:  PASS:  Emergency stabilization (current)
Phase 2: Infrastructure preparation and CI/CD restoration  
Phase 3: Gradual migration with Golden Path priority
Phase 4: SSOT consolidation and duplicate removal

MIGRATION GUIDANCE:
OLD: from test_framework.runner import UnifiedTestRunner
NEW: from tests.unified_test_runner import UnifiedTestRunner
"""

import warnings
from pathlib import Path

# CRITICAL: Emit SSOT violation warning
warnings.warn(
    "CRITICAL SSOT VIOLATION: test_framework.runner.UnifiedTestRunner duplicates canonical SSOT. "
    "This module is deprecated and will be removed. "
    "Use: from tests.unified_test_runner import UnifiedTestRunner",
    FutureWarning,
    stacklevel=2
)

# CRITICAL: Import compatibility layer to maintain business continuity
from test_framework.runner_legacy import LegacyUnifiedTestRunnerWrapper

# CRITICAL: Redirect to compatibility layer for zero business impact
UnifiedTestRunner = LegacyUnifiedTestRunnerWrapper

# Export for backward compatibility
__all__ = ['UnifiedTestRunner']