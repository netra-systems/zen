#!/usr/bin/env python
"""Quick frontend test runner that handles no-tests case properly"""

import os
import subprocess
import sys
from pathlib import Path
from shared.isolated_environment import IsolatedEnvironment

PROJECT_ROOT = Path(__file__).parent.parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"

def run_frontend_tests():
    """Run frontend tests with npm"""
    os.chdir(FRONTEND_DIR)
    
    # Run tests with passWithNoTests flag
    cmd = "npm test -- --passWithNoTests --ci --silent"
    
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            timeout=30
        )
        
        if "No tests found" in result.stdout:
            print("[INFO] No frontend tests found - passing")
            return 0
        
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
            
        return result.returncode
        
    except subprocess.TimeoutExpired:
        print("[ERROR] Frontend tests timed out after 30 seconds")
        return 1
    except Exception as e:
        print(f"[ERROR] Failed to run frontend tests: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(run_frontend_tests())