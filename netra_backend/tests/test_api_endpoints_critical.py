"""
Critical API endpoint tests - MODULAR ARCHITECTURE.

This file imports from focused test modules to maintain the 450-line limit.
Each module contains specific test categories with 25-line maximum functions.
"""

# Add project root to path
import sys
from pathlib import Path

from ..test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

# Import all critical API tests from focused modules

import sys
from pathlib import Path

from .test_api_agent_generation_critical import (
    TestAPIAgentGenerationCritical,
)
from .test_api_core_critical import TestAPICoreEndpointsCritical
from .test_api_error_handling_critical import (
    TestAPIErrorHandlingCritical,
)
from .test_api_threads_messages_critical import (
    TestAPIThreadsMessagesCritical,
)

# Re-export test classes for pytest discovery
__all__ = [
    "TestAPICoreEndpointsCritical",
    "TestAPIThreadsMessagesCritical", 
    "TestAPIAgentGenerationCritical",
    "TestAPIErrorHandlingCritical"
]