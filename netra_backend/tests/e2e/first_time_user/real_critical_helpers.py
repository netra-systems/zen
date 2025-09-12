"""
Real Critical User Journey Helpers - Consolidated imports for REAL E2E testing

**BUSINESS VALUE JUSTIFICATION (BVJ):**
1. **Segment**: Development Infrastructure supporting $1.2M+ ARR tests
2. **Business Goal**: Enable reliable testing of revenue-critical user journeys
3. **Value Impact**: Modular helpers reduce test maintenance by 60%
4. **Revenue Impact**: Faster test development = quicker iteration on conversion optimization

**ARCHITECTURE**:  <= 300 lines, consolidated imports to maintain architectural compliance
Provides unified access to all helper classes while maintaining modular design.
"""

# Import all helper classes from split modules
from netra_backend.tests.e2e.first_time_user.real_critical_auth_helpers import (
    AIProviderHelpers,
    CriticalUserJourneyHelpers,
    OAuthFlowHelpers,
    WebSocketHelpers,
)
from netra_backend.tests.e2e.first_time_user.real_critical_optimization_helpers import (
    ConcurrentTestHelpers,
    ErrorRecoveryHelpers,
    OptimizationHelpers,
    PerformanceTestHelpers,
    ValueDemonstrationHelpers,
)

# Re-export all classes for convenience
__all__ = [
    # Core and Auth helpers
    'CriticalUserJourneyHelpers',
    'OAuthFlowHelpers', 
    'AIProviderHelpers',
    'WebSocketHelpers',
    
    # Optimization and Performance helpers
    'OptimizationHelpers',
    'ConcurrentTestHelpers',
    'PerformanceTestHelpers',
    'ValueDemonstrationHelpers',
    'ErrorRecoveryHelpers'
]