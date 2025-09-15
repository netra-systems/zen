import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent

"""
Rapid Message Succession Test Suite

This module provides infrastructure and tests for validating message ordering,
idempotency, and state consistency under rapid message succession scenarios.
"""
