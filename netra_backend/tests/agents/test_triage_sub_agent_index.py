"""
Triage Sub Agent Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 500-line monolith
"""

# Import all test classes from focused modules

# Add project root to path

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

from netra_backend.tests.test_triage_agent_core import (

# Add project root to path
    TestTriageSubAgentInitialization,
    TestRequestValidation,
    TestEntityExtraction,
    TestIntentDetermination
)
from netra_backend.tests.test_triage_agent_validation import (
    TestToolRecommendation,
    TestFallbackCategorization,
    TestJSONExtraction,
    TestEntryConditions
)
from netra_backend.tests.test_triage_agent_caching import (
    TestCaching,
    TestExecuteMethod,
    TestRequestHashing
)
from netra_backend.tests.test_triage_agent_models import (
    TestPydanticModels,
    TestCleanup
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