"""
Comprehensive E2E Model Selection Workflows Test Suite - Main Index Module
Re-exports all test classes from focused modules for backwards compatibility.
Maximum 300 lines, functions ≤8 lines.
"""""

import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

# Test framework import - using pytest fixtures instead

import pytest

from netra_backend.tests.e2e.chat_optimization_tests import TestRealTimeChatOptimization
from netra_backend.tests.e2e.example_prompts_tests import TestExamplePromptsModelSelection
from netra_backend.tests.e2e.gpt5_migration_tests import TestGPT5MigrationWorkflows
from netra_backend.tests.e2e.model_effectiveness_tests import TestModelEffectivenessAnalysis

# Import all test classes and fixtures from focused modules
from netra_backend.tests.e2e.model_setup_helpers import model_selection_setup
from netra_backend.tests.e2e.workflow_integrity_tests import (
TestModelSelectionDataFlow,
TestModelSelectionEdgeCases,
TestWorkflowIntegrity,
)

# Re-export all test classes for backwards compatibility
__all__ = [
'TestModelEffectivenessAnalysis',
'TestGPT5MigrationWorkflows', 
'TestRealTimeChatOptimization',
'TestModelSelectionDataFlow',
'TestModelSelectionEdgeCases',
'TestWorkflowIntegrity',
'TestExamplePromptsModelSelection',
'model_selection_setup'
]

if __name__ == "__main__":
    pytest.main([__file__, "-v"])