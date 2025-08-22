"""
Comprehensive E2E Model Selection Workflows Test Suite - Main Index Module
Re-exports all test classes from focused modules for backwards compatibility.
Maximum 300 lines, functions ≤8 lines.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import pytest

from netra_backend.tests.chat_optimization_tests import TestRealTimeChatOptimization
from netra_backend.tests.example_prompts_tests import TestExamplePromptsModelSelection
from netra_backend.tests.gpt5_migration_tests import TestGPT5MigrationWorkflows
from netra_backend.tests.model_effectiveness_tests import TestModelEffectivenessAnalysis

# Import all test classes and fixtures from focused modules
from netra_backend.tests.model_setup_helpers import model_selection_setup
from netra_backend.tests.workflow_integrity_tests import (
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