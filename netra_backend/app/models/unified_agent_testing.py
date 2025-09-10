"""Unified Agent Testing Models - Compatibility Layer

This module provides backward compatibility for unified agent testing model imports.
Redirects to the test framework implementation following SSOT principles.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Maintain test compatibility while following SSOT principles
- Value Impact: Ensures existing tests continue to work without breaking changes
- Strategic Impact: Maintains system stability during module consolidation
"""

from test_framework.agent_test_helpers import (
    AgentResultValidator,
    AgentTestExecutor,
    ResultAssertion,
    ValidationConfig,
    CommonValidators,
    create_standard_validation_config
)

from test_framework.fixtures.agent_fixtures import (
    agent_validator,
    agent_executor,
    result_assertion,
    triage_validation_config,
    optimization_validation_config,
    action_plan_validation_config,
    agent_test_helper
)

# Create compatibility aliases for unified agent testing
UnifiedAgentTestingValidator = AgentResultValidator
UnifiedAgentTestingExecutor = AgentTestExecutor
UnifiedAgentTestingAssertion = ResultAssertion
UnifiedAgentTestingConfig = ValidationConfig

# Re-export all functionality for backward compatibility
__all__ = [
    'AgentResultValidator',
    'AgentTestExecutor', 
    'ResultAssertion',
    'ValidationConfig',
    'CommonValidators',
    'create_standard_validation_config',
    'agent_validator',
    'agent_executor', 
    'result_assertion',
    'triage_validation_config',
    'optimization_validation_config',
    'action_plan_validation_config',
    'agent_test_helper',
    # Compatibility aliases
    'UnifiedAgentTestingValidator',
    'UnifiedAgentTestingExecutor',
    'UnifiedAgentTestingAssertion',
    'UnifiedAgentTestingConfig'
]