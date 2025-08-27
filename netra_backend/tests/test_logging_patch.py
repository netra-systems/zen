"""
Test-specific logging patch to prevent I/O errors during pytest teardown.
"""

import sys
import os
from unittest.mock import MagicMock


def patch_loguru_for_tests():
    """Completely disable loguru handlers during tests."""
    try:
        from loguru import logger
        
        # Store original methods
        if not hasattr(logger, '_original_add'):
            logger._original_add = logger.add
            logger._original_remove = logger.remove
        
        # Replace add method with a no-op during tests
        def safe_add(*args, **kwargs):
            """No-op replacement for logger.add during tests."""
            return 1  # Return a fake handler ID
        
        def safe_remove(*args, **kwargs):
            """Safe replacement for logger.remove during tests."""
            try:
                logger._original_remove(*args, **kwargs)
            except (ValueError, OSError):
                pass
        
        # Replace the methods
        logger.add = safe_add
        logger.remove = safe_remove
        
        # Remove any existing handlers to prevent issues
        try:
            logger._original_remove()
        except (ValueError, OSError):
            pass
            
    except ImportError:
        pass


# Apply the patch when this module is imported during tests
if os.environ.get('TESTING') == '1' or os.environ.get('ENVIRONMENT') == 'testing':
    patch_loguru_for_tests()