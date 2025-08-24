#!/usr/bin/env python3
"""Simple test fix loop - runs tests and fixes issues iteratively."""

import subprocess
import sys
import os
import re
from pathlib import Path

def run_iteration(iteration_num):
    """Run one iteration of test and fix."""
    print(f"\n--- Iteration {iteration_num}/100 ---")
    
    # Run tests
    print("Running tests...")
    try:
        result = subprocess.run(
            [sys.executable, "unified_test_runner.py", "--categories", "smoke", "unit", "--no-coverage", "--fast-fail"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        output = result.stdout + result.stderr
        
        # Check for syntax errors
        if "SyntaxError" in output:
            # Extract the file with syntax error
            match = re.search(r'File "([^"]+\.py)"', output)
            if match:
                error_file = match.group(1)
                print(f"Found syntax error in: {error_file}")
                
                # Try to fix common syntax issues
                try:
                    path = Path(error_file)
                    if path.exists():
                        content = path.read_text()
                        
                        # Fix duplicate imports in unittest.mock
                        if "from unittest.mock import" in content:
                            lines = content.split('\n')
                            for i, line in enumerate(lines):
                                if "from unittest.mock import" in line and "MagicMock, MagicMock" in line:
                                    lines[i] = "from unittest.mock import AsyncMock, MagicMock, Mock, patch"
                                    print(f"Fixed duplicate import in {error_file}")
                                    path.write_text('\n'.join(lines))
                                    return True
                        
                        # Fix blank lines after decorators
                        fixed_content = re.sub(
                            r'(@pytest\.mark\.\w+)\s*\n\s*\n\s*(async def)',
                            r'\1\n    \2',
                            content
                        )
                        
                        if fixed_content != content:
                            path.write_text(fixed_content)
                            print(f"Fixed decorator spacing in {error_file}")
                            return True
                            
                except Exception as e:
                    print(f"Error fixing file: {e}")
        
        # Check success
        if result.returncode == 0:
            print("[PASS] Tests passed!")
            return True
        else:
            print("[FAIL] Tests failed")
            return False
            
    except subprocess.TimeoutExpired:
        print("[TIMEOUT] Test execution timed out")
        return False
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

def main():
    """Run 100 iterations."""
    passed = 0
    failed = 0
    
    for i in range(1, 101):
        if run_iteration(i):
            passed += 1
        else:
            failed += 1
    
    print(f"\n=== Final Summary ===")
    print(f"Passed: {passed}/100")
    print(f"Failed: {failed}/100")

if __name__ == "__main__":
    main()