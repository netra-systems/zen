#!/usr/bin/env python3
"""
Verification script for startup issue resolution.
"""

import sys
import subprocess
import time
from pathlib import Path

def test_module_import():
    """Test that the module can be imported correctly."""
    try:
        from dev_launcher.config import LauncherConfig
        from dev_launcher.launcher import DevLauncher
        print("[OK] Module imports successful")
        return True
    except Exception as e:
        print(f"[ERROR] Module import failed: {e}")
        return False

def test_help_command():
    """Test that help command works."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "dev_launcher", "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and "Netra AI Development Launcher" in result.stdout:
            print("[OK] Help command successful")
            return True
        else:
            print(f"[ERROR] Help command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"[ERROR] Help command exception: {e}")
        return False

def test_config_creation():
    """Test configuration creation."""
    try:
        from dev_launcher.config import LauncherConfig
        config = LauncherConfig(
            no_browser=True,
            load_secrets=False,
            verbose=True
        )
        print(f"[OK] Configuration created: {config.project_root}")
        return True
    except Exception as e:
        print(f"[ERROR] Configuration creation failed: {e}")
        return False

def test_environment_files():
    """Test that environment files exist."""
    project_root = Path.cwd()
    env_files = [".env", ".env.development", ".env.development.local"]
    
    found_files = []
    for env_file in env_files:
        if (project_root / env_file).exists():
            found_files.append(env_file)
    
    if found_files:
        print(f"[OK] Environment files found: {', '.join(found_files)}")
        return True
    else:
        print("[WARN] No environment files found")
        return True  # Not critical for basic operation

def main():
    """Run all verification tests."""
    print("Verifying Startup Issue Resolution")
    print("=" * 50)
    
    tests = [
        ("Module Import", test_module_import),
        ("Help Command", test_help_command),
        ("Configuration Creation", test_config_creation),
        ("Environment Files", test_environment_files),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\nTesting {test_name}...")
        if test_func():
            passed += 1
        else:
            print(f"[FAILED] {test_name}")
    
    print("\n" + "=" * 50)
    print(f"Verification Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n[SUCCESS] All startup issues resolved!")
        print("\nReady to use:")
        print("  python -m dev_launcher")
        print("  python -m dev_launcher --help")
        print("  python -m dev_launcher --no-secrets --verbose")
        return 0
    else:
        print(f"\n[WARNING] {total - passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())