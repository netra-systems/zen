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
try:
    from netra_backend.tests.e2e.helpers.model_setup_helpers import (
        create_test_thread,
        create_test_user,
    )
    model_selection_setup = lambda: {"user": create_test_user(), "thread": create_test_thread()}
except ImportError:
    # Fallback if helpers not available
    def model_selection_setup():
        return {"user": {"id": "test-user", "email": "test@example.com"}, "thread": {"id": "test-thread"}}

__all__ = ['model_selection_setup']