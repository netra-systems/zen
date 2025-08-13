#!/usr/bin/env python
"""
Simple frontend test runner for Netra AI Platform
Minimal dependencies for use by test_runner.py
"""

import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
sys.path.insert(0, str(PROJECT_ROOT))


def run_frontend_tests(test_level="smoke", args=None):
    """Run frontend tests at specified level"""
    
    # Ensure we're in frontend directory
    os.chdir(FRONTEND_DIR)
    
    # Check if node_modules exists
    if not (FRONTEND_DIR / "node_modules").exists():
        print("[WARNING] node_modules not found. Skipping frontend tests.")
        print("[INFO] To run frontend tests, install dependencies with: cd frontend && npm install")
        return True  # Don't fail the test suite for missing dependencies
    
    # Check if npm is available
    try:
        subprocess.run(["npm", "--version"], capture_output=True, timeout=5, shell=True)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("[WARNING] npm not available. Skipping frontend tests.")
        return True  # Don't fail for missing npm
    
    # Map test levels to Jest commands
    test_commands = {
        "smoke": ["npm", "run", "test", "--", "--passWithNoTests", "--maxWorkers=1"],
        "unit": ["npm", "run", "test", "--", "--passWithNoTests", "--maxWorkers=2"],
        "integration": ["npm", "run", "test", "--", "--passWithNoTests", "--maxWorkers=2"],
        "comprehensive": ["npm", "run", "test", "--", "--coverage", "--passWithNoTests"],
        "critical": ["npm", "run", "test", "--", "--passWithNoTests", "--maxWorkers=1"],
    }
    
    # Get the appropriate command
    cmd = test_commands.get(test_level, test_commands["unit"])
    
    # Add any additional arguments
    if args:
        cmd.extend(args)
    
    print(f"[INFO] Running frontend tests: {' '.join(cmd)}")
    
    # Run the tests with timeout
    try:
        result = subprocess.run(
            cmd, 
            capture_output=False, 
            text=True, 
            shell=True,
            timeout=30 if test_level == "smoke" else 120
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] Frontend tests timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to run frontend tests: {e}")
        return False


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Simple frontend test runner")
    parser.add_argument("--level", default="unit", 
                       choices=["smoke", "unit", "integration", "comprehensive", "critical"],
                       help="Test level to run")
    parser.add_argument("args", nargs="*", help="Additional arguments to pass to Jest")
    
    args = parser.parse_args()
    
    success = run_frontend_tests(args.level, args.args)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()