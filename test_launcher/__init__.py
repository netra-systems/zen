"""
Test Launcher - Testing-focused service launcher for Netra platform.

This package provides a test-centric alternative to dev_launcher,
optimized for running tests with proper service isolation and resource management.
"""

from test_launcher.launcher import TestLauncher
from test_launcher.config import TestConfig, TestProfile

__version__ = "1.0.0"

__all__ = [
    "TestLauncher",
    "TestConfig", 
    "TestProfile"
]