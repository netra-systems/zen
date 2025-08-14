"""
Modular Example Prompts E2E Real Tests Package

This package contains the modularized version of the comprehensive E2E tests 
for example prompts with real LLM calls, split into focused test modules:

- test_cost_optimization.py: Cost optimization tests (Prompt 1)
- test_performance_optimization.py: Latency and function optimization tests (Prompts 2, 4)
- test_capacity_and_models.py: Capacity planning and model selection tests (Prompts 3, 5)  
- test_advanced_features.py: Audit, multi-objective, tool migration, and rollback tests (Prompts 6-9)
- test_base.py: Base class with shared utility methods
- conftest.py: Shared fixtures and configuration
"""

from .test_base import BaseExamplePromptsTest
from .conftest import EXAMPLE_PROMPTS

__all__ = [
    'BaseExamplePromptsTest',
    'EXAMPLE_PROMPTS'
]