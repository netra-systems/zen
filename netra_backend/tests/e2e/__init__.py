"""
E2E Test Package

End-to-end tests for Netra Apex model selection workflows and agent orchestration.
Provides real integration testing with live LLM providers and system components.

Key modules:
- model_selection_workflows: Main test orchestration
- model_setup_helpers: Test environment setup
- workflow_integrity_tests: Data flow validation
- chat_optimization_tests: Real-time optimization
- gpt5_migration_tests: Model migration workflows
- example_prompts_tests: Prompt effectiveness validation
"""

__version__ = "1.0.0"

# Re-export key test utilities for easy access
from netra_backend.tests.model_setup_helpers import model_selection_setup

__all__ = ['model_selection_setup']