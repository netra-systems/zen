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
from tests.unified.e2e.helpers.error_generators import ErrorCorrelationContext, ErrorPropagationMetrics, RealErrorPropagationTester, MockTokenGenerator, ErrorInjectionHelper, run_real_error_propagation_validation
    ErrorCorrelationContext,
    ErrorPropagationMetrics,
    RealErrorPropagationTester,
    MockTokenGenerator,
    ErrorInjectionHelper,
    run_real_error_propagation_validation
)

# Error Validation Components  
from tests.unified.e2e.helpers.error_validators import AuthServiceFailurePropagationValidator, AuthTokenValidator
    AuthServiceFailurePropagationValidator,
    AuthTokenValidator
)

# Database Error Handling
from tests.unified.e2e.helpers.database_error_helpers import DatabaseErrorHandlingValidator, DatabaseConnectionTester
    DatabaseErrorHandlingValidator,
    DatabaseConnectionTester
)

# Recovery and Retry Testing
from tests.unified.e2e.helpers.error_recovery_helpers import NetworkFailureSimulationValidator, NetworkLatencyTester
    NetworkFailureSimulationValidator,
    NetworkLatencyTester
)

# Network Retry and Pattern Testing
from tests.unified.e2e.helpers.network_retry_helpers import RetryPatternTester, RecoveryScenarioTester, NetworkResilienceTester, TimeoutPatternAnalyzer
    RetryPatternTester,
    RecoveryScenarioTester,
    NetworkResilienceTester,
    TimeoutPatternAnalyzer
)

# Correlation Testing
from tests.unified.e2e.helpers.error_correlation_helpers import ErrorCorrelationValidator, CorrelationTestHelper
    ErrorCorrelationValidator,
    CorrelationTestHelper
)

# User Message and Cross-Service Testing
from tests.unified.e2e.helpers.user_message_helpers import UserFriendlyMessageValidator, CrossServiceTrackingValidator, MessageQualityAnalyzer
    UserFriendlyMessageValidator,
    CrossServiceTrackingValidator,
    MessageQualityAnalyzer
)

# Main test class for pytest integration
from tests.unified.e2e.helpers.test_suite import TestRealErrorPropagation, create_real_error_propagation_test_suite


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
    'create_real_error_propagation_test_suite'
]
