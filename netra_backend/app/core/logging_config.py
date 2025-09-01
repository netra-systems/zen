"""
Logging configuration for Cloud Run compatibility.

This module ensures that logs are properly formatted for Cloud Run
without ANSI escape codes that can corrupt log output.
"""
import os
import sys
import logging
from shared.isolated_environment import IsolatedEnvironment


def configure_cloud_run_logging():
    """
    Configure logging for Cloud Run environments to prevent ANSI escape codes.
    
    Python 3.11+ adds colored tracebacks by default which can cause issues
    in Cloud Run logs. This disables all color output.
    """
    # Get environment manager instance
    env = IsolatedEnvironment.get_instance()
    
    # Disable colored output in environment variables
    os.environ['NO_COLOR'] = '1'
    os.environ['FORCE_COLOR'] = '0'
    os.environ['PY_COLORS'] = '0'
    
    # Disable colored tracebacks in Python 3.11+
    if hasattr(sys, '_xoptions'):
        sys._xoptions['no_debug_ranges'] = True
    
    # Set up basic logging configuration without colors
    environment = env.get('ENVIRONMENT', 'development').lower()
    
    if environment in ['staging', 'production', 'prod']:
        # For Cloud Run, use structured logging without colors
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Disable any rich/colorama imports if they exist
        try:
            import colorama
            colorama.init(strip=True, convert=False)
        except ImportError:
            pass
        
        # Disable rich traceback if it's installed
        try:
            from rich.traceback import install
            # Don't install rich traceback in production
        except ImportError:
            pass
    else:
        # Development can use standard logging
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )


def setup_exception_handler():
    """
    Set up a custom exception handler that doesn't use ANSI codes.
    """
    import traceback
    
    def exception_handler(exc_type, exc_value, exc_traceback):
        """Custom exception handler without colors."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Format exception without colors
        tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
        # Remove any ANSI escape codes that might have been added
        clean_lines = []
        for line in tb_lines:
            # Remove ANSI escape sequences
            import re
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            clean_lines.append(clean_line)
        
        sys.stderr.write(''.join(clean_lines))
    
    env = IsolatedEnvironment.get_instance()
    environment = env.get('ENVIRONMENT', 'development').lower()
    if environment in ['staging', 'production', 'prod']:
        sys.excepthook = exception_handler


# Initialize on module import
configure_cloud_run_logging()
setup_exception_handler()