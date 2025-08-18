"""
Comprehensive E2E Model Selection Workflows Test Suite - Main Index Module
Re-exports all test classes from focused modules for backwards compatibility.
Maximum 300 lines, functions ≤8 lines.
"""

import pytest

# Import all test classes and fixtures from focused modules
from .model_setup_helpers import model_selection_setup
from .model_effectiveness_tests import TestModelEffectivenessAnalysis
from .gpt5_migration_tests import TestGPT5MigrationWorkflows
from .chat_optimization_tests import TestRealTimeChatOptimization
from .workflow_integrity_tests import (
    TestModelSelectionDataFlow,
    TestModelSelectionEdgeCases,
    TestWorkflowIntegrity
)
from .example_prompts_tests import TestExamplePromptsModelSelection

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