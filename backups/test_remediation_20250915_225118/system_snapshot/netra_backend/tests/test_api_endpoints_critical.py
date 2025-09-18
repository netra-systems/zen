"""
Critical API endpoint tests - MODULAR ARCHITECTURE.

This file imports from focused test modules to maintain the 450-line limit.
Each module contains specific test categories with 25-line maximum functions.
"""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Import all critical API tests from focused modules
from netra_backend.tests.test_api_agent_generation_critical import (
    TestAPIAgentGenerationCritical,
)
from netra_backend.tests.test_api_core_critical import TestAPICoreEndpointsCritical
from netra_backend.tests.test_api_error_handling_critical import (
    TestAPIErrorHandlingCritical,
)
from netra_backend.tests.test_api_threads_messages_critical import (
    TestAPIThreadsMessagesCritical,
)

# Re-export test classes for pytest discovery
__all__ = [
    "TestAPICoreEndpointsCritical",
    "TestAPIThreadsMessagesCritical", 
    "TestAPIAgentGenerationCritical",
    "TestAPIErrorHandlingCritical"
]