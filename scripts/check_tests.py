#!/usr/bin/env python3
"""Check golden path test status and run basic validation"""

import sys
import os
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_test_files():
    """Check which golden path test files exist and are accessible"""
    test_dir = project_root / "tests" / "e2e"
    golden_path_files = list(test_dir.glob("*golden*path*.py"))
    
    print("GOLDEN PATH TEST FILES FOUND:")
    print("=" * 50)
    
    accessible_tests = []
    problem_tests = []
    
    for test_file in golden_path_files:
        print(f"📁 {test_file.name}")
        
        try:
            # Try to read the file and check for issues
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check for common issues
            issues = []
            if "@require_docker_services" in content and "@require_docker_services()" not in content:
                issues.append("Docker services required")
            if "import docker" in content:
                issues.append("Docker dependency")
            if "localhost" in content:
                issues.append("Localhost reference (may need staging URLs)")
            if "127.0.0.1" in content:
                issues.append("Local IP reference")
                
            if issues:
                print(f"   ⚠️  Issues: {', '.join(issues)}")
                problem_tests.append((test_file.name, issues))
            else:
                print(f"   ✅ No obvious issues detected")
                accessible_tests.append(test_file.name)
                
        except Exception as e:
            print(f"   ❌ Error reading file: {e}")
            problem_tests.append((test_file.name, [f"Read error: {e}"]))
    
    print(f"\nSUMMARY:")
    print(f"✅ Tests likely runnable against staging: {len(accessible_tests)}")
    print(f"⚠️  Tests with potential issues: {len(problem_tests)}")
    
    if accessible_tests:
        print(f"\nRECOMMENDED TESTS TO RUN:")
        for test in accessible_tests[:5]:  # Top 5
            print(f"   - {test}")
    
    if problem_tests:
        print(f"\nPROBLEMATIC TESTS:")
        for test, issues in problem_tests[:5]:  # Top 5
            print(f"   - {test}: {', '.join(issues)}")
    
    return accessible_tests, problem_tests

def check_staging_config():
    """Check if staging configuration is accessible"""
    print("\nSTAGING CONFIGURATION CHECK:")
    print("=" * 50)
    
    staging_env = project_root / "config" / "staging.env"
    if staging_env.exists():
        print("✅ staging.env found")
        try:
            with open(staging_env, 'r') as f:
                lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            print(f"   Contains {len(lines)} configuration lines")
        except Exception as e:
            print(f"❌ Error reading staging.env: {e}")
    else:
        print("❌ staging.env not found")
    
    # Check for staging test infrastructure
    staging_test_files = [
        "tests/e2e/staging_config.py",
        "tests/e2e/staging_test_base.py", 
        "tests/e2e/staging_auth_client.py"
    ]
    
    for file_path in staging_test_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"✅ {file_path} exists")
        else:
            print(f"❌ {file_path} missing")

def main():
    print("GOLDEN PATH E2E TEST ANALYSIS")
    print("=" * 80)
    print("Checking test files for GCP staging compatibility...")
    print("Mode: No Docker dependencies, fast failure analysis")
    print("=" * 80)
    
    accessible_tests, problem_tests = check_test_files()
    check_staging_config()
    
    print(f"\nRECOMMENDATION:")
    if accessible_tests:
        print(f"✅ Found {len(accessible_tests)} tests ready for staging execution")
        print(f"🎯 Focus on running these tests first for immediate feedback")
    else:
        print(f"⚠️  No immediately runnable tests found")
        print(f"🔧 May need configuration or dependency fixes")
    
    print(f"\nNEXT STEPS:")
    print(f"1. Run pytest on the accessible tests with staging environment")
    print(f"2. Focus on connection and authentication issues first") 
    print(f"3. Use fast failure mode (--maxfail=1) to get quick feedback")
    
if __name__ == "__main__":
    main()