from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
"""
Test-specific logging patch to prevent I/O errors during pytest teardown.
"""

import sys
import os
import atexit


env = get_env()
def patch_loguru_for_tests():
    """Completely disable loguru handlers during tests to prevent I/O errors."""
    try:
        from loguru import logger
        
        # Store original methods
        if not hasattr(logger, '_original_add'):
            logger._original_add = logger.add
            logger._original_remove = logger.remove
            logger._original_bind = logger.bind
        
        # Replace add method with a no-op during tests
        def safe_add(*args, **kwargs):
            """No-op replacement for logger.add during tests."""
            return 1  # Return a fake handler ID
        
        def safe_remove(*args, **kwargs):
            """Safe replacement for logger.remove during tests."""
            try:
                logger._original_remove(*args, **kwargs)
            except (ValueError, OSError, AttributeError):
                pass
        
        def safe_bind(*args, **kwargs):
            """Safe replacement for logger.bind during tests."""
            return logger  # Return self to maintain method chaining
        
        # Replace the methods
        logger.add = safe_add
        logger.remove = safe_remove
        logger.bind = safe_bind
        
        # Remove any existing handlers to prevent issues
        try:
            logger._original_remove()
        except (ValueError, OSError, AttributeError):
            pass
            
        # Register cleanup at exit to prevent issues
        def cleanup_loguru():
            try:
                logger._original_remove()
            except (ValueError, OSError, AttributeError):
                pass
        
        atexit.register(cleanup_loguru)
            
    except ImportError:
        pass


def patch_pytest_capture():
    """Patch pytest capture to handle closed files gracefully."""
    try:
        import _pytest.capture
        
        # Store original methods
        if not hasattr(_pytest.capture.FDCapture, '_original_snap'):
            _pytest.capture.FDCapture._original_snap = _pytest.capture.FDCapture.snap
        
        def safe_snap(self):
            """Safe replacement for FDCapture.snap that handles closed files."""
            try:
                return self._original_snap()
            except (ValueError, OSError) as e:
                if "I/O operation on closed file" in str(e):
                    return ""  # Return empty string for closed files
                raise
        
        _pytest.capture.FDCapture.snap = safe_snap
        
    except (ImportError, AttributeError):
        pass


# Apply the patches when this module is imported during tests
if env.get('TESTING') == '1' or env.get('ENVIRONMENT') == 'testing' or 'pytest' in sys.modules:
    patch_loguru_for_tests()
    patch_pytest_capture()