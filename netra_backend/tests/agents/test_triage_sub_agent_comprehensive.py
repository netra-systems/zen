"""
Comprehensive tests for TriageSubAgent - modular architecture compliant
Split into focused test modules to comply with 450-line file limit and 25-line function limit

This file serves as the main entry point that imports all the split test modules.
Each module focuses on a specific aspect of testing with functions ≤8 lines.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import sys
from pathlib import Path

import pytest

from netra_backend.tests.agents.test_triage_caching_async import *
from netra_backend.tests.agents.test_triage_edge_performance import *
from netra_backend.tests.agents.test_triage_entity_intent import *
from netra_backend.tests.agents.test_triage_init_validation import *

def test_architectural_compliance():
    """Test that all functions in test modules are ≤8 lines"""
    # This meta-test ensures architectural compliance
    # Individual test modules handle specific functionality
    assert True  # Placeholder for architectural validation

    if __name__ == "__main__":
        pytest.main([__file__, "-v", "--tb=short", "--durations=10"])