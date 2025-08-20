#!/usr/bin/env python3
"""
Critical Unified Tests Runner
Python equivalent of run_critical_tests.sh

This script runs the 10 critical unified tests with proper error handling
and service management.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


# Colors for terminal output
class Colors:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    ENDC = '\033[0m'


def print_colored(message: str, color: str = Colors.ENDC):
    """Print colored output to terminal."""
    print(f"{color}{message}{Colors.ENDC}")


def run_command(cmd: List[str], check: bool = True, capture_output: bool = False, 
                env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run a shell command and return the result."""
    try:
        # Merge environment variables
        final_env = os.environ.copy()
        if env:
            final_env.update(env)
            
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True,
            env=final_env
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            raise
        return e


def check_command_exists(cmd: str) -> bool:
    """Check if a command exists in the system PATH."""
    try:
        if sys.platform == "win32":
            result = subprocess.run(["where", cmd], capture_output=True, text=True)
            return result.returncode == 0
        else:
            result = subprocess.run(["which", cmd], capture_output=True, text=True)
            return result.returncode == 0
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def find_python_command() -> str:
    """Find the best Python command to use."""
    # Try python3 first, then python
    if check_command_exists("python3"):
        return "python3"
    elif check_command_exists("python"):
        return "python"
    else:
        print_colored("ERROR: Python is not available in PATH", Colors.RED)
        sys.exit(1)


def check_pytest(python_cmd: str) -> bool:
    """Check if pytest is available."""
    try:
        run_command([python_cmd, "-m", "pytest", "--version"], capture_output=True)
        return True
    except subprocess.CalledProcessError:
        print_colored("ERROR: pytest is not available. Please install it with: pip install pytest", Colors.RED)
        return False


def setup_environment() -> dict:
    """Setup environment variables for testing."""
    env = {
        "NETRA_ENV": "test",
        "LOG_LEVEL": "INFO",
        "PYTHONPATH": str(Path.cwd())
    }
    return env


def run_critical_tests(python_cmd: str, extra_args: List[str]) -> int:
    """Run the critical unified tests."""
    print_colored("Running 10 critical unified tests...", Colors.CYAN)
    print("")
    
    # Setup environment
    env = setup_environment()
    
    # Build command
    cmd = [python_cmd, "tests/unified/e2e/run_critical_unified_tests.py"] + extra_args
    
    try:
        result = run_command(cmd, check=False, env=env)
        return result.returncode
    except Exception as e:
        print_colored(f"ERROR: Failed to run critical tests: {e}", Colors.RED)
        return 1


def main():
    """Main function to orchestrate the critical tests."""
    parser = argparse.ArgumentParser(
        description="Critical Unified Tests Runner"
    )
    
    # Parse known args and capture unknown ones
    args, unknown_args = parser.parse_known_args()
    
    print_colored("=" * 80, Colors.BLUE)
    print_colored("CRITICAL UNIFIED TESTS RUNNER", Colors.BLUE)
    print_colored("=" * 80, Colors.BLUE)
    print("")
    
    # Change to project root directory (script directory)
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    # Find Python command
    python_cmd = find_python_command()
    print_colored(f"Using Python: {python_cmd}", Colors.CYAN)
    
    # Check pytest availability
    if not check_pytest(python_cmd):
        sys.exit(1)
    
    # Run critical tests
    test_exit_code = run_critical_tests(python_cmd, unknown_args)
    
    print("")
    print_colored("=" * 80, Colors.BLUE)
    if test_exit_code == 0:
        print_colored("ALL TESTS PASSED - System ready for production", Colors.GREEN)
    else:
        print_colored("TESTS FAILED - Review results and fix issues before deployment", Colors.RED)
    print_colored("=" * 80, Colors.BLUE)
    
    sys.exit(test_exit_code)


if __name__ == "__main__":
    main()