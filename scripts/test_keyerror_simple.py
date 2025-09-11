#!/usr/bin/env python3
"""
Simple script to reproduce the KeyError issue in Loguru JSON formatting.

This script demonstrates the exact bug that occurs when the JSON formatter
output is used as a Loguru format string in Cloud Run environments.
"""

import sys
from loguru import logger

def reproduce_keyerror():
    """Reproduce the KeyError issue."""
    
    # Remove any existing handlers
    logger.remove()
    
    # This is the JSON string that gets returned by _get_json_formatter()
    # in Cloud Run environments
    json_format_string = '{"timestamp":"2025-09-11T02:39:40.501320Z","severity":"INFO","service":"netra-service","logger":"test","message":"Test message"}'
    
    print("=== REPRODUCING KEYERROR ISSUE ===")
    print(f"JSON format string: {json_format_string}")
    print("\nAttempting to use this JSON string as a Loguru format...")
    
    try:
        # This line should cause the KeyError: '"timestamp"'
        # because Loguru interprets the JSON string as a format string
        # and tries to find format fields like {timestamp}, but finds "timestamp" instead
        logger.add(
            sys.stdout, 
            format=json_format_string,  # BUG: JSON string used as format
            level="INFO"
        )
        
        print("Logger configured. Now attempting to log a message...")
        
        # This should trigger the KeyError in Loguru's internal formatting
        logger.info("This message should trigger the KeyError")
        
        print("ERROR: No KeyError was raised - bug reproduction failed!")
        return False
        
    except KeyError as e:
        print("SUCCESS: KeyError reproduced!")
        print(f"Error: {e}")
        print(f"This proves that JSON strings cannot be used as Loguru format strings.")
        return True
        
    except Exception as e:
        print(f"UNEXPECTED ERROR: {type(e).__name__}: {e}")
        return False

def demonstrate_correct_usage():
    """Show what the correct format should look like."""
    
    logger.remove()
    
    print("\n=== CORRECT USAGE EXAMPLE ===")
    print("Loguru format strings should use {field} syntax, not JSON strings.")
    
    # This is what a proper Loguru format string looks like
    correct_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}"
    
    print(f"Correct format: {correct_format}")
    
    try:
        logger.add(
            sys.stdout,
            format=correct_format,
            level="INFO"
        )
        
        logger.info("This works correctly with proper Loguru format syntax")
        print("Correct format works as expected")
        return True
        
    except Exception as e:
        print(f"Unexpected error with correct format: {e}")
        return False

if __name__ == "__main__":
    print("KeyError Reproduction Script for Issue #252")
    print("=" * 50)
    
    # Reproduce the bug
    bug_reproduced = reproduce_keyerror()
    
    # Show correct usage
    correct_usage_works = demonstrate_correct_usage()
    
    print("\n" + "=" * 50)
    print("SUMMARY:")
    print(f"Bug reproduced: {'YES' if bug_reproduced else 'NO'}")
    print(f"Correct format works: {'YES' if correct_usage_works else 'NO'}")
    
    if bug_reproduced:
        print("\nROOT CAUSE CONFIRMED:")
        print("The _get_json_formatter() method returns JSON strings that")
        print("Loguru tries to interpret as format strings, causing KeyError.")
        print("\nSOLUTION:")
        print("The JSON formatter should return a callable that formats")
        print("records directly, not a JSON string for Loguru to parse.")
    
    sys.exit(0 if bug_reproduced else 1)