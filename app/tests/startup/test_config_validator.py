"""
Config Validator Tests - Index
Central index for all configuration validation tests split across modules.
Compliance: <300 lines, 8-line max functions, modular design.
"""

# Import all config validator test modules
from app.tests.startup.test_config_core import (
    TestConfigStatus,
    TestConfigValidationResult,
    TestValidationContext
)
from app.tests.startup.test_config_validation import (
    TestServiceConfigValidatorInit,
    TestConfigFileChecking,
    TestConfigLoading,
    TestEndpointValidation,
    TestValidationWorkflow
)
from app.tests.startup.test_config_engine import (
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