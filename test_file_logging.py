#!/usr/bin/env python3
"""Test that file logging doesn't contain ANSI codes."""

import tempfile
import os
import re
from loguru import logger

def test_file_logging():
    """Test that file logging produces clean output without ANSI codes."""
    
    # Remove existing handlers
    logger.remove()
    
    # Create a temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as temp_file:
        temp_path = temp_file.name
    
    try:
        # Add file handler - should NOT have colorize=True for files
        logger.add(
            temp_path,
            format="{time} | {level} | {name}:{function}:{line} | {message}",
            level="DEBUG"
        )
        
        # Log some messages
        logger.info("Test file logging message")
        logger.error("Test error message") 
        logger.warning("Test warning message")
        
        # Read the file content
        with open(temp_path, 'r') as f:
            content = f.read()
        
        print("=== FILE CONTENT ===")
        print(repr(content))
        print("\n=== FORMATTED FILE CONTENT ===")
        print(content)
        
        # Check for ANSI escape codes (these should NOT exist in files)
        ansi_pattern = r'\x1b\[[0-9;]*m|\033\[[0-9;]*m'
        ansi_matches = re.findall(ansi_pattern, content)
        
        if ansi_matches:
            print(f"FAILED: Found ANSI codes in file: {ansi_matches}")
            return False
        else:
            print("SUCCESS: No ANSI codes found in file output")
            return True
            
    finally:
        # Clean up
        if os.path.exists(temp_path):
            os.unlink(temp_path)

if __name__ == "__main__":
    test_file_logging()