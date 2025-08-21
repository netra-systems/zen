"""Central testing utilities module.

Provides common utilities for all test files.
"""

import sys
from pathlib import Path


def setup_test_path():
    """Set up the project root in sys.path for test imports.
    
    This function ensures that the project root is in sys.path
    so that all tests can import from the netra_backend module.
    
    Returns:
        Path: The project root path
    """
    # Navigate from tests/ -> netra_backend/ -> project_root/
    project_root = Path(__file__).parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    return project_root