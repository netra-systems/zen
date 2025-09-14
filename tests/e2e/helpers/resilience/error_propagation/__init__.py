"""Error Propagation Testing Framework

This module provides comprehensive error propagation testing across service boundaries
with real service validation, correlation tracking, and user-friendly message validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Operational efficiency & Support cost reduction
- Value Impact: Reduces debugging time, improves system reliability
- Revenue Impact: $45K+ MRR (Reduced support burden, improved user experience)
- Strategic Impact: Platform stability, customer trust, operational scaling

Re-exports all public interfaces for backward compatibility.
"""

# Import all public classes and functions from the refactored modules

# Error Generation and Testing Infrastructure
from tests.e2e.helpers.resilience.error_propagation.error_generators import (
    ErrorCorrelationContext, ErrorPropagationMetrics, RealErrorPropagationTester, MockTokenGenerator, ErrorInjectionHelper, run_real_error_propagation_validation
)

# Error Validation Components  
from tests.e2e.helpers.resilience.error_propagation.error_validators import (
    AuthServiceFailurePropagationValidator, AuthTokenValidator
)

# Database Error Handling
from tests.e2e.helpers.resilience.error_propagation.database_error_helpers import (
    DatabaseErrorHandlingValidator, DatabaseConnectionTester
)

# Recovery and Retry Testing
from tests.e2e.helpers.resilience.error_propagation.error_recovery_helpers import (
    NetworkFailureSimulationValidator, NetworkLatencyTester
)

# Network Retry and Pattern Testing
from tests.e2e.helpers.resilience.error_propagation.network_retry_helpers import (
    RetryPatternTester, RecoveryScenarioTester, NetworkResilienceTester, TimeoutPatternAnalyzer
)

# Correlation Testing
from tests.e2e.helpers.resilience.error_propagation.error_correlation_helpers import (
    ErrorCorrelationValidator, CorrelationTestHelper
)

# User Message and Cross-Service Testing
from tests.e2e.helpers.resilience.error_propagation.user_message_helpers import (
    UserFriendlyMessageValidator, CrossServiceTrackingValidator, MessageQualityAnalyzer
)

# Main test class for pytest integration
from tests.e2e.helpers.resilience.error_propagation.test_suite import TestRealErrorPropagation


# Export all public symbols
__all__ = [
    # Core classes
    'ErrorCorrelationContext',
    'ErrorPropagationMetrics', 
    'RealErrorPropagationTester',
    
    # Validators
    'AuthServiceFailurePropagationValidator',
    'DatabaseErrorHandlingValidator',
    'NetworkFailureSimulationValidator',
    'ErrorCorrelationValidator',
    'UserFriendlyMessageValidator',
    'CrossServiceTrackingValidator',
    
    # Helpers
    'MockTokenGenerator',
    'ErrorInjectionHelper',
    'RetryPatternTester',
    'RecoveryScenarioTester',
    'CorrelationTestHelper',
    'MessageQualityAnalyzer',
    'AuthTokenValidator',
    'DatabaseConnectionTester',
    'NetworkLatencyTester',
    'NetworkResilienceTester',
    'TimeoutPatternAnalyzer',
    
    # Test Suite
    'TestRealErrorPropagation',
    
    # Utility Functions
    'run_real_error_propagation_validation',
    # 'create_real_error_propagation_test_suite'  # Function may not exist
]
