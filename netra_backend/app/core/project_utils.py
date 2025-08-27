"""Project-level utilities.

This module provides common utility functions that need to be shared
across multiple modules to maintain SSOT compliance.
"""

from pathlib import Path


def get_project_root() -> Path:
    """Get the project root path.
    
    SINGLE SOURCE OF TRUTH for project root detection.
    
    Returns:
        Path: The absolute path to the project root directory.
    """
    # This file is in netra_backend/app/core/, so project root is three levels up
    return Path(__file__).parent.parent.parent.parent


def get_app_root() -> Path:
    """Get the app root path (netra_backend/app/).
    
    Returns:
        Path: The absolute path to the app root directory.
    """
    # This file is in netra_backend/app/core/, so app root is one level up
    return Path(__file__).parent.parent


def is_test_environment() -> bool:
    """Check if we're in a test environment.
    
    SINGLE SOURCE OF TRUTH for test environment detection.
    Combines multiple detection methods for comprehensive coverage.
    
    Returns:
        bool: True if running in a test environment.
    """
    import os
    
    # Method 1: Check pytest-specific environment variables
    if os.environ.get('PYTEST_CURRENT_TEST') is not None:
        return True
    
    # Method 2: Check explicit testing flag
    if os.environ.get('TESTING') == '1':
        return True
        
    # Method 3: Check if pytest is in the command line  
    if 'pytest' in os.environ.get('_', ''):
        return True
    
    # Method 4: Check environment name
    env_name = os.environ.get('ENVIRONMENT', '').lower()
    if env_name in ['test', 'testing']:
        return True
        
    # Method 5: Check NETRA_ENV
    netra_env = os.environ.get('NETRA_ENV', '').lower()
    if netra_env in ['test', 'testing']:
        return True
    
    return False
