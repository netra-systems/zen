# Test framework initialization
"""
Test Framework for Netra Core

This package provides utilities and helpers for testing,
especially for Docker container testing and stress testing.
"""

import sys
from pathlib import Path

__version__ = "1.0.0"


def setup_test_path() -> Path:
    """Set up test path for imports.
    
    Adds the project root directory to sys.path if it's not already there
    so that all tests can import from project modules.
    
    Handles Windows and Unix path differences automatically.
    
    Returns:
        Path: The project root path
    """
    # Navigate from test_framework/ -> project_root/
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent
    
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    return project_root
