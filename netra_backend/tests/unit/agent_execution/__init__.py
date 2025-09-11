"""
Agent Execution Unit Tests Package

This package contains comprehensive unit tests for the Agent Execution components
in the Netra backend system.

Test Modules:
- test_execution_state_transitions.py: Tests for ExecutionState enum transitions
- test_timeout_configuration.py: Tests for timeout logic and user tier calculations  
- test_circuit_breaker_logic.py: Tests for circuit breaker failure/recovery
- test_phase_validation_rules.py: Tests for execution phase validation
- test_context_validation.py: Tests for user context security validation

Business Value Justification:
These unit tests protect core agent execution functionality that delivers 90% of 
platform value through reliable chat interactions and agent responses.
"""

# Package imports for convenience
from .test_execution_state_transitions import TestExecutionStateTransitions
from .test_timeout_configuration import TestTimeoutConfiguration  
from .test_circuit_breaker_logic import TestCircuitBreakerLogic
from .test_phase_validation_rules import TestPhaseValidationRules
from .test_context_validation import TestContextValidation

__all__ = [
    'TestExecutionStateTransitions',
    'TestTimeoutConfiguration', 
    'TestCircuitBreakerLogic',
    'TestPhaseValidationRules',
    'TestContextValidation'
]