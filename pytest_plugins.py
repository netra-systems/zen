"""
Pytest plugins to fix I/O operation on closed file errors.
"""

import sys
import warnings
from typing import Generator
import pytest


@pytest.fixture(scope="session", autouse=True)
def patch_pytest_capture_on_startup():
    """Patch pytest capture mechanism to handle closed files gracefully."""
    try:
        import _pytest.capture
        import os
        
        # Patch FDCapture methods
        if not hasattr(_pytest.capture.FDCapture, '_original_snap'):
            _pytest.capture.FDCapture._original_snap = _pytest.capture.FDCapture.snap
            _pytest.capture.FDCapture._original_resume = _pytest.capture.FDCapture.resume
            _pytest.capture.FDCapture._original_suspend = _pytest.capture.FDCapture.suspend
        
        def safe_snap(self):
            """Safe replacement for FDCapture.snap that handles closed files."""
            try:
                return self._original_snap()
            except (ValueError, OSError) as e:
                if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                    return ""  # Return empty string for closed files
                raise
        
        def safe_resume(self):
            """Safe replacement for FDCapture.resume that handles closed files."""
            try:
                # Check if tmpfile is closed before attempting resume
                if hasattr(self, 'tmpfile') and hasattr(self.tmpfile, 'closed'):
                    if self.tmpfile.closed:
                        return  # Skip resume for closed files
                return self._original_resume()
            except (ValueError, OSError) as e:
                if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                    return  # Skip resume for closed files
                raise
        
        def safe_suspend(self):
            """Safe replacement for FDCapture.suspend that handles closed files."""
            try:
                # Check if tmpfile is closed before attempting suspend
                if hasattr(self, 'tmpfile') and hasattr(self.tmpfile, 'closed'):
                    if self.tmpfile.closed:
                        return ""  # Return empty string for closed files
                return self._original_suspend()
            except (ValueError, OSError) as e:
                if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                    return ""  # Return empty string for closed files
                raise
        
        # Replace the methods
        _pytest.capture.FDCapture.snap = safe_snap
        _pytest.capture.FDCapture.resume = safe_resume
        _pytest.capture.FDCapture.suspend = safe_suspend
        
        # Patch MultiCapture methods which are causing the actual error
        if hasattr(_pytest.capture, 'MultiCapture'):
            if not hasattr(_pytest.capture.MultiCapture, '_original_resume_capturing'):
                _pytest.capture.MultiCapture._original_resume_capturing = _pytest.capture.MultiCapture.resume_capturing
                _pytest.capture.MultiCapture._original_suspend_capturing = _pytest.capture.MultiCapture.suspend_capturing
                _pytest.capture.MultiCapture._original_readouterr = _pytest.capture.MultiCapture.readouterr
                if hasattr(_pytest.capture.MultiCapture, 'pop_outerr_to_orig'):
                    _pytest.capture.MultiCapture._original_pop_outerr_to_orig = _pytest.capture.MultiCapture.pop_outerr_to_orig
            
            def safe_resume_capturing(self):
                """Safe replacement for MultiCapture.resume_capturing that handles closed files."""
                try:
                    return self._original_resume_capturing()
                except (ValueError, OSError) as e:
                    if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                        # Try to recreate the capture if possible
                        try:
                            if hasattr(self, 'out') and hasattr(self.out, 'tmpfile'):
                                if self.out.tmpfile.closed:
                                    # Skip resume - capture is broken
                                    return
                            if hasattr(self, 'err') and hasattr(self.err, 'tmpfile'):
                                if self.err.tmpfile.closed:
                                    # Skip resume - capture is broken  
                                    return
                        except (AttributeError, ValueError, OSError):
                            pass
                        return  # Skip resume for closed files
                    raise
            
            def safe_suspend_capturing(self, *args, **kwargs):
                """Safe replacement for MultiCapture.suspend_capturing that handles closed files."""
                try:
                    return self._original_suspend_capturing(*args, **kwargs)
                except (ValueError, OSError) as e:
                    if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                        return ("", "")  # Return empty strings for closed files
                    raise
            
            def safe_readouterr(self):
                """Safe replacement for MultiCapture.readouterr that handles closed files."""
                try:
                    return self._original_readouterr()
                except (ValueError, OSError) as e:
                    if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                        return ("", "")  # Return empty strings for closed files
                    raise
            
            def safe_pop_outerr_to_orig(self):
                """Safe replacement for MultiCapture.pop_outerr_to_orig that handles closed files."""
                try:
                    return self._original_pop_outerr_to_orig()
                except (ValueError, OSError) as e:
                    if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                        return  # Skip pop operation for closed files
                    raise
            
            _pytest.capture.MultiCapture.resume_capturing = safe_resume_capturing
            _pytest.capture.MultiCapture.suspend_capturing = safe_suspend_capturing
            _pytest.capture.MultiCapture.readouterr = safe_readouterr
            if hasattr(_pytest.capture.MultiCapture, 'pop_outerr_to_orig'):
                _pytest.capture.MultiCapture.pop_outerr_to_orig = safe_pop_outerr_to_orig
        
        # Also patch the specific capture classes that are causing the getvalue error
        if hasattr(_pytest.capture, 'SysCapture'):
            if not hasattr(_pytest.capture.SysCapture, '_original_snap'):
                _pytest.capture.SysCapture._original_snap = _pytest.capture.SysCapture.snap
            
            def safe_sys_snap(self):
                """Safe replacement for SysCapture.snap that handles closed files."""
                try:
                    return self._original_snap()
                except (ValueError, OSError) as e:
                    if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                        return ""  # Return empty string for closed files
                    raise
            
            _pytest.capture.SysCapture.snap = safe_sys_snap
        
        # Patch the buffer classes that cause the getvalue error
        if hasattr(_pytest.capture, 'EncodedFile'):
            if not hasattr(_pytest.capture.EncodedFile, '_original_getvalue'):
                _pytest.capture.EncodedFile._original_getvalue = _pytest.capture.EncodedFile.getvalue
            
            def safe_getvalue(self):
                """Safe replacement for EncodedFile.getvalue that handles closed files."""
                try:
                    # Check if buffer is closed before accessing it
                    if hasattr(self, 'buffer') and hasattr(self.buffer, 'closed'):
                        if self.buffer.closed:
                            return ""  # Return empty string for closed buffer
                    return self._original_getvalue()
                except (ValueError, OSError) as e:
                    if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                        return ""  # Return empty string for closed files
                    raise
            
            _pytest.capture.EncodedFile.getvalue = safe_getvalue
        
        # Also patch the StringIO buffer directly if it exists
        try:
            from io import StringIO
            if not hasattr(StringIO, '_original_getvalue_patched'):
                StringIO._original_getvalue = StringIO.getvalue
                StringIO._original_getvalue_patched = True
                
                def safe_stringio_getvalue(self):
                    """Safe replacement for StringIO.getvalue that handles closed files."""
                    try:
                        if hasattr(self, 'closed') and self.closed:
                            return ""  # Return empty string for closed StringIO
                        return self._original_getvalue()
                    except (ValueError, OSError) as e:
                        if "I/O operation on closed file" in str(e) or "closed file" in str(e):
                            return ""  # Return empty string for closed files
                        raise
                
                StringIO.getvalue = safe_stringio_getvalue
        except (ImportError, AttributeError):
            pass
        
    except (ImportError, AttributeError):
        pass
    
    yield  # Session continues
    
    # Cleanup - restore original methods
    try:
        import _pytest.capture
        if hasattr(_pytest.capture.FDCapture, '_original_snap'):
            _pytest.capture.FDCapture.snap = _pytest.capture.FDCapture._original_snap
            _pytest.capture.FDCapture.resume = _pytest.capture.FDCapture._original_resume
            _pytest.capture.FDCapture.suspend = _pytest.capture.FDCapture._original_suspend
        
        if hasattr(_pytest.capture, 'MultiCapture') and hasattr(_pytest.capture.MultiCapture, '_original_resume_capturing'):
            _pytest.capture.MultiCapture.resume_capturing = _pytest.capture.MultiCapture._original_resume_capturing
            _pytest.capture.MultiCapture.suspend_capturing = _pytest.capture.MultiCapture._original_suspend_capturing
            _pytest.capture.MultiCapture.readouterr = _pytest.capture.MultiCapture._original_readouterr
            if hasattr(_pytest.capture.MultiCapture, '_original_pop_outerr_to_orig'):
                _pytest.capture.MultiCapture.pop_outerr_to_orig = _pytest.capture.MultiCapture._original_pop_outerr_to_orig
        
        if hasattr(_pytest.capture, 'SysCapture') and hasattr(_pytest.capture.SysCapture, '_original_snap'):
            _pytest.capture.SysCapture.snap = _pytest.capture.SysCapture._original_snap
            
        if hasattr(_pytest.capture, 'EncodedFile') and hasattr(_pytest.capture.EncodedFile, '_original_getvalue'):
            _pytest.capture.EncodedFile.getvalue = _pytest.capture.EncodedFile._original_getvalue
        
        # Restore StringIO if patched
        try:
            from io import StringIO
            if hasattr(StringIO, '_original_getvalue_patched') and hasattr(StringIO, '_original_getvalue'):
                StringIO.getvalue = StringIO._original_getvalue
                delattr(StringIO, '_original_getvalue_patched')
        except (ImportError, AttributeError):
            pass
    except (ImportError, AttributeError):
        pass


def pytest_configure(config):
    """Configure pytest to handle I/O errors gracefully."""
    # Suppress warnings about closed files during collection
    warnings.filterwarnings(
        "ignore", 
        message=".*I/O operation on closed file.*",
        category=Warning
    )
    
    # Suppress other common warnings during collection
    warnings.filterwarnings(
        "ignore", 
        message=".*closed file.*",
        category=Warning
    )
    
    warnings.filterwarnings(
        "ignore",
        message=".*invalid escape sequence.*",
        category=DeprecationWarning
    )
    
    # If the capture is causing too many issues, disable it entirely for problematic tests
    try:
        # Check if --no-capture is already specified
        if not any(arg in ['--capture=no', '-s'] for arg in config.args):
            # Don't force --capture=no here as it might affect legitimate capture needs
            pass
    except AttributeError:
        pass


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    # Additional setup if needed
    pass


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished, right before returning the exit status to the system."""
    # Clean up any remaining loguru handlers
    try:
        from loguru import logger
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            logger.remove()
    except (ImportError, ValueError, OSError):
        pass


def pytest_unconfigure(config):
    """Called before test process is exited."""
    # Final cleanup
    try:
        from loguru import logger
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            logger.remove()
    except (ImportError, ValueError, OSError):
        pass