"""Automated test fix loop script.

This script runs test suite iterations and fixes issues automatically.
"""

import subprocess
import sys
import time
import re
from pathlib import Path
from typing import List, Tuple

def run_tests() -> Tuple[bool, str, List[str]]:
    """Run the test suite and return status, output, and failing tests."""
    try:
        result = subprocess.run(
            [sys.executable, "unified_test_runner.py", "--level", "integration", "--no-coverage", "--fast-fail"],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        output = result.stdout + result.stderr
        
        # Extract failing test files from syntax errors
        failing_files = []
        for line in output.split('\n'):
            if 'SyntaxError' in line or 'File "' in line:
                match = re.search(r'File "([^"]+\.py)"', line)
                if match:
                    failing_files.append(match.group(1))
        
        # Check for import errors
        if 'ImportError' in output or 'ModuleNotFoundError' in output:
            for line in output.split('\n'):
                if '.py' in line:
                    match = re.search(r'([^\s]+\.py)', line)
                    if match:
                        failing_files.append(match.group(1))
        
        return result.returncode == 0, output, list(set(failing_files))
    except subprocess.TimeoutExpired:
        return False, "Test run timed out", []
    except Exception as e:
        return False, str(e), []

def fix_syntax_error(file_path: str) -> bool:
    """Attempt to fix common syntax errors in a file."""
    try:
        path = Path(file_path)
        if not path.exists():
            return False
            
        content = path.read_text()
        original_content = content
        
        # Fix pattern: @pytest.mark.asyncio with blank line before async def
        content = re.sub(
            r'(@pytest\.mark\.\w+)\s*\n\s*\n\s*(async def)',
            r'\1\n    \2',
            content
        )
        
        # Fix duplicate imports
        lines = content.split('\n')
        seen_imports = set()
        fixed_lines = []
        for line in lines:
            if line.startswith('from unittest.mock import'):
                imports = re.findall(r'import\s+(.+)', line)[0].split(',')
                unique_imports = []
                for imp in imports:
                    imp = imp.strip()
                    if imp not in seen_imports:
                        seen_imports.add(imp)
                        unique_imports.append(imp)
                if unique_imports:
                    fixed_lines.append(f"from unittest.mock import {', '.join(unique_imports)}")
            else:
                fixed_lines.append(line)
        
        content = '\n'.join(fixed_lines)
        
        # Write back if changed
        if content != original_content:
            path.write_text(content)
            print(f"Fixed: {file_path}")
            return True
        return False
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False

def main():
    """Main execution loop."""
    print("Starting automated test fix loop...")
    
    iterations = 100
    fixes_made = 0
    successful_runs = 0
    
    for i in range(1, iterations + 1):
        print(f"\n{'='*60}")
        print(f"Iteration {i}/{iterations}")
        print(f"{'='*60}")
        
        # Run tests
        print("Running tests...")
        success, output, failing_files = run_tests()
        
        if success:
            successful_runs += 1
            print(f"[PASS] Tests passed! (Run {successful_runs})")
        else:
            print(f"[FAIL] Tests failed. Found {len(failing_files)} files with issues")
            
            # Fix one file if any issues found
            if failing_files:
                file_to_fix = failing_files[0]
                print(f"Attempting to fix: {file_to_fix}")
                if fix_syntax_error(file_to_fix):
                    fixes_made += 1
                    print(f"Fix #{fixes_made} applied")
            else:
                print("No specific files identified for fixing")
        
        # Brief pause between iterations
        time.sleep(0.5)
        
        # Summary every 10 iterations
        if i % 10 == 0:
            print(f"\n--- Progress Summary ---")
            print(f"Iterations: {i}/{iterations}")
            print(f"Fixes made: {fixes_made}")
            print(f"Successful test runs: {successful_runs}")
    
    print(f"\n{'='*60}")
    print("Final Summary")
    print(f"{'='*60}")
    print(f"Total iterations: {iterations}")
    print(f"Total fixes applied: {fixes_made}")
    print(f"Successful test runs: {successful_runs}")
    print(f"Success rate: {successful_runs/iterations*100:.1f}%")

if __name__ == "__main__":
    main()