"""
Config Validator Tests - Index
Central index for all configuration validation tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all config validator test modules

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.tests.test_config_core import (
    ConfigStatusHelper as TestConfigStatus,
    ConfigValidationResultHelper as TestConfigValidationResult,
    ValidationContextHelper as TestValidationContext,
)
# TODO: Import from actual test files once they exist
# from netra_backend.tests.test_config_engine import (
#     TestConfigDecisionEngine,
#     TestMainValidationFunction,
#     TestUtilityFunctions,
# )
# from netra_backend.tests.test_config_validation import (
#     TestConfigFileChecking,
#     TestConfigLoading,
#     TestEndpointValidation,
#     TestServiceConfigValidatorInit,
#     TestValidationWorkflow,
# )

# Re-export all test classes for pytest discovery
__all__ = [
    "TestConfigStatus",
    "TestConfigValidationResult", 
    "TestValidationContext",
    # TODO: Add other classes once their files exist
    # "TestServiceConfigValidatorInit",
    # "TestConfigFileChecking",
    # "TestConfigLoading",
    # "TestEndpointValidation",
    # "TestValidationWorkflow",
    # "TestConfigDecisionEngine",
    # "TestUtilityFunctions",
    # "TestMainValidationFunction"
]