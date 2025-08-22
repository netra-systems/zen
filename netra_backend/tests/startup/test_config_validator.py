"""
Config Validator Tests - Index
Central index for all configuration validation tests split across modules.
Compliance: <300 lines, 25-line max functions, modular design.
"""

# Import all config validator test modules

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from netra_backend.tests.startup.test_config_core import (
    # Add project root to path
    TestConfigStatus,
    TestConfigValidationResult,
    TestValidationContext,
)
from netra_backend.tests.startup.test_config_engine import (
    TestConfigDecisionEngine,
    TestMainValidationFunction,
    TestUtilityFunctions,
)
from netra_backend.tests.startup.test_config_validation import (
    TestConfigFileChecking,
    TestConfigLoading,
    TestEndpointValidation,
    TestServiceConfigValidatorInit,
    TestValidationWorkflow,
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