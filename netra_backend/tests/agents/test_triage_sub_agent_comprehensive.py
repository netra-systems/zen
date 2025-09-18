"""
Comprehensive tests for TriageSubAgent - modular architecture compliant
Split into focused test modules to comply with 450-line file limit and 25-line function limit

This file serves as the main entry point that imports all the split test modules.
Each module focuses on a specific aspect of testing with functions  <= 8 lines.
"""
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment
import sys
from pathlib import Path
import pytest
from netra_backend.tests.agents.test_triage_caching_async import *
from netra_backend.tests.agents.test_triage_edge_performance import *
from netra_backend.tests.agents.test_triage_entity_intent import *
from netra_backend.tests.agents.test_triage_init_validation import *

def test_triage_modules_import_successfully():
    """Test that all triage test modules can be imported successfully."""
    # Test: Verify triage test modules are available
    try:
        # These imports should not raise exceptions
        import netra_backend.tests.agents.test_triage_caching_async
        import netra_backend.tests.agents.test_triage_edge_performance
        import netra_backend.tests.agents.test_triage_entity_intent
        import netra_backend.tests.agents.test_triage_init_validation

        # Verify: Modules have expected attributes
        modules = [
            netra_backend.tests.agents.test_triage_caching_async,
            netra_backend.tests.agents.test_triage_edge_performance,
            netra_backend.tests.agents.test_triage_entity_intent,
            netra_backend.tests.agents.test_triage_init_validation
        ]

        # Basic smoke test: verify modules are loaded
        for module in modules:
            assert module is not None
            assert hasattr(module, '__name__')

    except ImportError as e:
        pytest.fail(f"Critical triage test module import failed: {e}")
    if __name__ == '__main__':
        'MIGRATED: Use SSOT unified test runner'
        print('MIGRATION NOTICE: Please use SSOT unified test runner')
        print('Command: python tests/unified_test_runner.py --category <category>')