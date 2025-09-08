"""Migration utilities for DeepAgentState to UserExecutionContext transition.

This module provides utilities and adapters to safely migrate from the deprecated
DeepAgentState pattern to the modern UserExecutionContext pattern.
"""

from .deepagentstate_adapter import (
    DeepAgentStateAdapter,
    MigrationDetector,
    MigrationValidationError
)

__all__ = [
    'DeepAgentStateAdapter',
    'MigrationDetector', 
    'MigrationValidationError'
]