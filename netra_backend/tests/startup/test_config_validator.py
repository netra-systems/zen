"""
Config Validator Tests - Index
Central index for all configuration validation tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all config validator test modules
from netra_backend.tests.startup.test_config_core import (

# Add project root to path
from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

    TestConfigStatus,
    TestConfigValidationResult,
    TestValidationContext
)
from netra_backend.tests.startup.test_config_validation import (
    TestServiceConfigValidatorInit,
    TestConfigFileChecking,
    TestConfigLoading,
    TestEndpointValidation,
    TestValidationWorkflow
)
from netra_backend.tests.startup.test_config_engine import (
    TestConfigDecisionEngine,
    TestUtilityFunctions,
    TestMainValidationFunction
)

# Re-export all test classes for pytest discovery
__all__ = [
    "TestConfigStatus",
    "TestConfigValidationResult", 
    "TestValidationContext",
    "TestServiceConfigValidatorInit",
    "TestConfigFileChecking",
    "TestConfigLoading",
    "TestEndpointValidation",
    "TestValidationWorkflow",
    "TestConfigDecisionEngine",
    "TestUtilityFunctions",
    "TestMainValidationFunction"
]