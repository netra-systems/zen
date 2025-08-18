"""Synthetic Data Agent Module

Modern modular implementation of synthetic data generation agents.
Provides structured, testable components for data generation workflows.

Business Value: Customer-facing data generation - HIGH revenue impact
"""

from .core import (
    SyntheticDataAgentCore,
    SyntheticDataExecutionContext
)

__all__ = [
    'SyntheticDataAgentCore',
    'SyntheticDataExecutionContext'
]