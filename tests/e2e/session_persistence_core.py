"""Session Persistence Core - Import Compatibility Module

This module provides backward compatibility for session persistence testing components.

CRITICAL: This is an SSOT compatibility layer that re-exports session persistence classes
to maintain existing import paths while consolidating the actual implementation.

Import Pattern:
- Legacy: from tests.e2e.session_persistence_core import SessionPersistenceManager
- SSOT: Various existing implementations consolidated

Business Justification:
- Maintains backward compatibility for existing E2E session tests
- Prevents breaking changes during session persistence SSOT consolidation  
- Supports Enterprise customer session management testing ($50K+ MRR)
"""

# Import existing session persistence implementations
from tests.e2e.helpers.auth.session_test_helpers import (
    SessionPersistenceManager
)

from tests.e2e.test_context_cross_service_failures import (
    ServiceRestartSimulator
)

# Import existing performance tracking capabilities
from tests.e2e.agent_startup_performance_measurer import (
    PerformanceMeasurer
)

# Alias PerformanceMeasurer as PerformanceTracker for compatibility
PerformanceTracker = PerformanceMeasurer

# Export all necessary components
__all__ = [
    'SessionPersistenceManager',
    'ServiceRestartSimulator', 
    'PerformanceTracker'
]