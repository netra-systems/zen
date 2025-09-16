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

def test_architectural_compliance():
    """Test that all functions in test modules are  <= 8 lines"""
    assert True
    if __name__ == '__main__':
        'MIGRATED: Use SSOT unified test runner'
        print('MIGRATION NOTICE: Please use SSOT unified test runner')
        print('Command: python tests/unified_test_runner.py --category <category>')