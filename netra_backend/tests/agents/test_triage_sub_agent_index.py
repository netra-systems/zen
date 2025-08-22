"""
Triage Sub Agent Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 500-line monolith
"""

# Import all test classes from focused modules

# Add project root to path

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

from .test_triage_agent_caching import (
    TestCaching,
    TestExecuteMethod,
    TestRequestHashing,
)
from .test_triage_agent_core import (
    TestEntityExtraction,
    TestIntentDetermination,
    TestRequestValidation,
    # Add project root to path
    TestTriageSubAgentInitialization,
)
from .test_triage_agent_models import TestCleanup, TestPydanticModels
from .test_triage_agent_validation import (
    TestEntryConditions,
    TestFallbackCategorization,
    TestJSONExtraction,
    TestToolRecommendation,
)

# Re-export for backward compatibility
__all__ = [
    'TestTriageSubAgentInitialization',
    'TestRequestValidation',
    'TestEntityExtraction',
    'TestIntentDetermination',
    'TestToolRecommendation',
    'TestFallbackCategorization',
    'TestJSONExtraction',
    'TestEntryConditions',
    'TestCaching',
    'TestExecuteMethod',
    'TestRequestHashing',
    'TestPydanticModels',
    'TestCleanup'
]