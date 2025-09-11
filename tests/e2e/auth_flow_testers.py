"""Auth Flow Testers - Import Compatibility Module

This module provides backward compatibility for the import path:
from tests.e2e.auth_flow_testers import AuthFlowE2ETester

CRITICAL: This is an SSOT compatibility layer that re-exports the unified auth flow tester
to maintain existing import paths while consolidating the actual implementation.

Import Pattern:
- Legacy: from tests.e2e.auth_flow_testers import AuthFlowE2ETester
- SSOT: from tests.e2e.auth_flow_manager import AuthFlowTester

Business Justification:
- Maintains backward compatibility for existing E2E tests
- Prevents breaking changes during E2E test SSOT consolidation
- Supports Enterprise-level authentication testing ($100K+ MRR)
"""

from tests.e2e.auth_flow_manager import (
    AuthFlowTester,
    AuthFlowConfig
)

# Re-export for compatibility - AuthFlowE2ETester is an alias for AuthFlowTester
AuthFlowE2ETester = AuthFlowTester

# Export all necessary components
__all__ = [
    'AuthFlowE2ETester',
    'AuthFlowTester', 
    'AuthFlowConfig'
]