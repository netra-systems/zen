#!/usr/bin/env python3
"""
Debug script to test the exact subprocess environment issue
"""

import subprocess
import sys
import os

# Add paths like test runner
sys.path.insert(0, 'shared')

def test_with_isolated_environment():
    """Test subprocess with the isolated environment manager"""
    print("=== TESTING WITH ISOLATED ENVIRONMENT ===")

    try:
        # Import without circular dependency
        from isolated_environment import IsolatedEnvironment

        # Create instance directly to avoid circular import
        env_manager = IsolatedEnvironment()
        subprocess_env = env_manager.get_subprocess_env()

        print(f"Environment isolation enabled: {env_manager._isolation_enabled}")
        print(f"Subprocess env keys: {sorted(subprocess_env.keys())}")
        print(f"PATH in subprocess_env: {'PATH' in subprocess_env}")

        if 'PATH' in subprocess_env:
            print(f"PATH value: {subprocess_env['PATH']}")

        # Add Windows specific env vars like test runner
        if sys.platform == "win32":
            subprocess_env.update({
                'PYTHONLEGACYWINDOWSSTDIO': '0',
                'PYTHONDONTWRITEBYTECODE': '1',
            })

        # Test the exact command from test runner
        cmd = "python -m pytest --version"
        print(f"\nTesting command: {cmd}")
        print(f"Working directory: {os.getcwd()}")

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10,
            env=subprocess_env,
            cwd=os.getcwd()
        )

        print(f"Return code: {result.returncode}")
        print(f"Stdout: {repr(result.stdout)}")
        print(f"Stderr: {repr(result.stderr)}")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

def test_with_current_environment():
    """Test subprocess with current environment (for comparison)"""
    print("\n=== TESTING WITH CURRENT ENVIRONMENT ===")

    cmd = "python -m pytest --version"
    print(f"Testing command: {cmd}")

    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=True,
        text=True,
        timeout=10,
        cwd=os.getcwd()
    )

    print(f"Return code: {result.returncode}")
    print(f"Stdout: {repr(result.stdout)}")
    print(f"Stderr: {repr(result.stderr)}")

if __name__ == "__main__":
    test_with_current_environment()
    test_with_isolated_environment()