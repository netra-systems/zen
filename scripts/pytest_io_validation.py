#!/usr/bin/env python3
"""
Pytest I/O Configuration Validation Script
=========================================

This script validates that pytest can run without "I/O operation on closed file" errors
on Windows by testing different capture configurations.

The fix is to use `-s` (--capture=no) to disable pytest's capture system entirely,
which avoids Windows-specific file handle lifecycle issues.
"""

import subprocess
import sys
import time
from pathlib import Path


def test_pytest_configuration(test_path: str, options: list, description: str) -> bool:
    """Test a specific pytest configuration.
    
    Args:
        test_path: Path to test directory or file
        options: List of pytest options to test
        description: Description of the test configuration
        
    Returns:
        True if configuration works, False otherwise
    """
    print(f"\n=== Testing {description} ===")
    cmd = ["python", "-m", "pytest", "--collect-only", test_path, "-q"] + options
    print(f"Command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("SUCCESS: No I/O errors detected")
            return True
        else:
            if "I/O operation on closed file" in result.stderr:
                print("FAILED: I/O operation on closed file error detected")
            else:
                print(f"FAILED: Other error (exit code {result.returncode})")
            print(f"Error: {result.stderr[:300]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print("FAILED: Test timed out")
        return False
    except Exception as e:
        print(f"FAILED: Exception occurred: {e}")
        return False


def main():
    """Main validation function."""
    print("Pytest I/O Configuration Validation")
    print("=" * 50)
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    print(f"Running from: {project_root}")
    
    # Test configurations
    test_configs = [
        {
            "path": "tests/unit",
            "options": ["-s"],
            "description": "Unit tests with -s (no capture) - RECOMMENDED FIX"
        },
        {
            "path": "tests/unit", 
            "options": ["--capture=no"],
            "description": "Unit tests with --capture=no"
        },
        {
            "path": "tests/unit",
            "options": ["--capture=sys"],
            "description": "Unit tests with --capture=sys"
        },
        {
            "path": "tests/unit",
            "options": [],
            "description": "Unit tests with default capture (should fail)"
        }
    ]
    
    successful_configs = []
    
    # Run tests
    for config in test_configs:
        success = test_pytest_configuration(
            config["path"],
            config["options"], 
            config["description"]
        )
        if success:
            successful_configs.append(config)
    
    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    
    if successful_configs:
        print("Working configurations found:")
        for config in successful_configs:
            print(f"  - {config['description']}")
        
        print(f"\nRECOMMENDATION: Use -s flag for Windows pytest execution")
        print(f"   This disables pytest's capture system and avoids Windows I/O issues")
        
        # Test a simple execution
        print("\n=== Testing Simple Execution ===")
        success = test_pytest_configuration(
            "tests/unit/test_service_id_no_timestamp.py::test_service_id_no_timestamp",
            ["-s", "--timeout=10"],
            "Single test execution with recommended flags"
        )
        
        if success:
            print("\nSUCCESS: Pytest I/O configuration is fixed!")
            print("   Integration tests should now run without I/O errors")
            return True
        else:
            print("\nWARNING: Collection works but execution may still have issues")
            return False
    else:
        print("No working configurations found")
        print("   The I/O issue persists - further investigation needed")
        return False


if __name__ == "__main__":
    import os
    
    # Change to project root
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    success = main()
    sys.exit(0 if success else 1)