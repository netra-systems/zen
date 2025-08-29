#!/usr/bin/env python3
"""
Verify that the Cloud Run logging fixes are properly configured.
This script checks both the Docker configuration and Python runtime settings.
"""
import os
import re
import sys
from pathlib import Path


def check_dockerfile_config():
    """Check that Dockerfile has the correct environment variables."""
    print("Checking Dockerfile configuration...")
    
    dockerfile_path = Path(__file__).parent.parent / "docker" / "backend.Dockerfile"
    
    if not dockerfile_path.exists():
        print(f"[ERROR] Dockerfile not found at {dockerfile_path}")
        return False
    
    with open(dockerfile_path, 'r') as f:
        content = f.read()
    
    required_envs = [
        'NO_COLOR=1',
        'FORCE_COLOR=0',
        'PY_COLORS=0',
        'PYTHONDONTWRITEBYTECODE=1',
        'PYTHONUNBUFFERED=1'
    ]
    
    missing = []
    for env_var in required_envs:
        if env_var not in content:
            missing.append(env_var)
    
    if missing:
        print(f"[FAIL] Missing environment variables in Dockerfile: {', '.join(missing)}")
        return False
    
    print("[PASS] Dockerfile has all required environment variables")
    return True


def check_logging_config():
    """Check that logging_config.py exists and has proper configuration."""
    print("\nChecking logging configuration module...")
    
    config_path = Path(__file__).parent.parent / "netra_backend" / "app" / "core" / "logging_config.py"
    
    if not config_path.exists():
        print(f"[ERROR] logging_config.py not found at {config_path}")
        return False
    
    with open(config_path, 'r') as f:
        content = f.read()
    
    required_functions = [
        'configure_cloud_run_logging',
        'setup_exception_handler'
    ]
    
    missing = []
    for func in required_functions:
        if func not in content:
            missing.append(func)
    
    if missing:
        print(f"[FAIL] Missing functions in logging_config.py: {', '.join(missing)}")
        return False
    
    # Check for ANSI code removal logic
    if not re.search(r"re\.sub\(r'\\x1b\\\[.*?\].*?m'", content):
        print("[WARNING] ANSI escape code removal pattern not found in logging_config.py")
    
    print("[PASS] Logging configuration module is properly configured")
    return True


def check_main_imports():
    """Check that main.py imports the logging configuration."""
    print("\nChecking main.py imports...")
    
    main_path = Path(__file__).parent.parent / "netra_backend" / "app" / "main.py"
    
    if not main_path.exists():
        print(f"[ERROR] main.py not found at {main_path}")
        return False
    
    with open(main_path, 'r') as f:
        content = f.read()
    
    if 'from netra_backend.app.core.logging_config import configure_cloud_run_logging' not in content:
        print("[FAIL] main.py does not import configure_cloud_run_logging")
        return False
    
    if 'configure_cloud_run_logging()' not in content:
        print("[FAIL] main.py does not call configure_cloud_run_logging()")
        return False
    
    print("[PASS] main.py properly imports and calls logging configuration")
    return True


def test_runtime_behavior():
    """Test that the configuration works at runtime."""
    print("\nTesting runtime behavior...")
    
    # Set production environment
    os.environ['ENVIRONMENT'] = 'production'
    
    # Import the logging config
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    try:
        from netra_backend.app.core.logging_config import configure_cloud_run_logging
        configure_cloud_run_logging()
        
        # Check that environment variables are set
        if os.environ.get('NO_COLOR') != '1':
            print("[FAIL] NO_COLOR not set to '1'")
            return False
        
        if os.environ.get('FORCE_COLOR') != '0':
            print("[FAIL] FORCE_COLOR not set to '0'")
            return False
        
        print("[PASS] Runtime configuration works correctly")
        return True
        
    except ImportError as e:
        print(f"[ERROR] Failed to import logging_config: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Runtime test failed: {e}")
        return False


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("Cloud Run Logging Fix Verification")
    print("=" * 60)
    
    results = {
        'Dockerfile': check_dockerfile_config(),
        'Logging Config': check_logging_config(),
        'Main Imports': check_main_imports(),
        'Runtime Behavior': test_runtime_behavior()
    }
    
    print("\n" + "=" * 60)
    print("Verification Results:")
    print("-" * 60)
    
    all_passed = True
    for check, passed in results.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {check:20} : {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("\n[SUCCESS] All checks passed! The Cloud Run logging fix is properly configured.")
        print("\nNext steps:")
        print("1. Build and test the Docker image locally")
        print("2. Deploy to staging environment")
        print("3. Monitor Cloud Run logs to verify ANSI codes are removed")
        return 0
    else:
        print("\n[ERROR] Some checks failed. Please review and fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())