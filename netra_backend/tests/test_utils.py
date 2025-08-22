"""Central testing utilities module.

Provides common utilities for all test files.
"""

import sys
from pathlib import Path


def setup_test_path() -> Path:
    """Set up test path for imports.
    
    Adds the netra_backend directory to sys.path if it's not already there
    so that all tests can import from the netra_backend module.
    
    Handles Windows and Unix path differences automatically.
    
    Returns:
        Path: The project root path
    """
    # Navigate from tests/ -> netra_backend/ -> project_root/
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    netra_backend_dir = current_file.parent.parent
    
    netra_backend_str = str(netra_backend_dir)
    if netra_backend_str not in sys.path:
        sys.path.insert(0, netra_backend_str)
    
    return project_root