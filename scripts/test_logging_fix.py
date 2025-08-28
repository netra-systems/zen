#!/usr/bin/env python3
"""Test script to verify logging shows correct source location."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netra_backend.app.logging_config import central_logger as logger


def test_function_level1():
    """Test function that calls another function."""
    logger.info("Test info message from level1 function")
    test_function_level2()
    

def test_function_level2():
    """Test function that logs an error."""
    logger.warning("Test warning message from level2 function")
    try:
        # Simulate an error similar to the langchain_google_genai import error
        raise ImportError("No module named 'test_module'")
    except ImportError as e:
        logger.error(f"Core logic failed: {e}")
        logger.warning("Using fallback optimization for test_run_id")


def main():
    """Main test function."""
    print("Testing logging with proper source location...")
    print("-" * 60)
    
    # Test direct logging
    logger.info("Direct info message from main")
    logger.warning("Direct warning message from main")
    logger.error("Direct error message from main")
    
    print("-" * 60)
    print("Testing nested function calls...")
    
    # Test nested function calls
    test_function_level1()
    
    print("-" * 60)
    print("Test complete. Check the log output above for proper file:line information.")
    print("Each log should show the actual source file and line, not unified_logging.py:202")


if __name__ == "__main__":
    main()