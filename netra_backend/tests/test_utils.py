"""Central testing utilities module.

Provides common utilities for all test files.
"""

import sys
from pathlib import Path


def setup_test_path():
    """Set up the project root in sys.path for test imports.
    
    This function ensures that the project root is in sys.path
    so that all tests can import from the netra_backend module.
    
    Handles Windows and Unix path differences automatically.
    
    Returns:
        Path: The project root path
    """
    # Navigate from tests/ -> netra_backend/ -> project_root/
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    netra_backend_dir = current_file.parent.parent
    
    # Add project root to sys.path (for main imports)
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    
    # Add netra_backend directory to sys.path (for direct module imports)
    netra_backend_str = str(netra_backend_dir)
    if netra_backend_str not in sys.path:
        sys.path.insert(0, netra_backend_str)
    
    return project_root