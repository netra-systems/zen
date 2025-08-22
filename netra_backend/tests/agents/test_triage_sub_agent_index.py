"""
Triage Sub Agent Tests - Modular Index
Redirects to focused test modules following 450-line architecture
COMPLIANCE: Modular split from 500-line monolith
"""

# Import all test classes from focused modules

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from netra_backend.tests.agents.test_triage_agent_caching import (
    TestCaching,
    TestExecuteMethod,
    TestRequestHashing,
)
from netra_backend.tests.agents.test_triage_agent_core import (
    TestEntityExtraction,
    TestIntentDetermination,
    TestRequestValidation,
    TestTriageSubAgentInitialization,
)
from netra_backend.tests.agents.test_triage_agent_models import TestCleanup, TestPydanticModels
from netra_backend.tests.test_triage_agent_validation import (
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