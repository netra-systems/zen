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
        print("[INFO] Installing frontend dependencies...")
        result = subprocess.run(["npm", "install"], capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[ERROR] Failed to install dependencies: {result.stderr}")
            return False
    
    # Map test levels to Jest commands
    test_commands = {
        "smoke": ["npm", "run", "test:smoke", "--", "--passWithNoTests"],
        "unit": ["npm", "run", "test:unit", "--", "--passWithNoTests"],
        "integration": ["npm", "run", "test", "--", "--passWithNoTests"],
        "comprehensive": ["npm", "run", "test:coverage", "--", "--passWithNoTests"],
        "critical": ["npm", "run", "test:critical", "--", "--passWithNoTests"],
    }
    
    # Get the appropriate command
    cmd = test_commands.get(test_level, test_commands["unit"])
    
    # Add any additional arguments
    if args:
        cmd.extend(args)
    
    print(f"[INFO] Running frontend tests: {' '.join(cmd)}")
    
    # Run the tests
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    return result.returncode == 0


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