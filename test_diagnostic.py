#!/usr/bin/env python3
"""
Diagnostic script to test environment and basic imports
"""
import sys
import os
from pathlib import Path

def main():
    print("=== Environment Diagnostic ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")

    # Check if we can import basic modules
    try:
        import pytest
        print(f"✓ pytest version: {pytest.__version__}")
    except ImportError as e:
        print(f"✗ pytest import failed: {e}")

    try:
        import asyncio
        print("✓ asyncio available")
    except ImportError as e:
        print(f"✗ asyncio import failed: {e}")

    # Check if test framework is available
    try:
        from test_framework.ssot.base_test_case import SSotAsyncTestCase
        print("✓ SSOT test framework available")
    except ImportError as e:
        print(f"✗ SSOT test framework import failed: {e}")

    # Check if backend modules are available
    try:
        from netra_backend.app.config import get_config
        print("✓ Backend config available")
    except ImportError as e:
        print(f"✗ Backend config import failed: {e}")

    # Check if shared modules are available
    try:
        from shared.isolated_environment import get_env
        print("✓ Shared environment available")
    except ImportError as e:
        print(f"✗ Shared environment import failed: {e}")

    print("\n=== File Structure Check ===")
    current_dir = Path(os.getcwd())

    # Check key directories
    key_dirs = [
        "netra_backend",
        "tests",
        "test_framework",
        "shared",
        "auth_service"
    ]

    for dir_name in key_dirs:
        dir_path = current_dir / dir_name
        if dir_path.exists():
            print(f"✓ {dir_name}/ exists")
        else:
            print(f"✗ {dir_name}/ missing")

    # Check key test files
    key_test_files = [
        "tests/unified_test_runner.py",
        "tests/e2e/golden_path/test_simplified_golden_path_e2e.py",
        "netra_backend/tests/agents/test_supervisor_basic.py"
    ]

    for file_path in key_test_files:
        full_path = current_dir / file_path
        if full_path.exists():
            print(f"✓ {file_path} exists")
        else:
            print(f"✗ {file_path} missing")

    print("\n=== Environment Variables ===")
    env_vars = [
        "ENVIRONMENT",
        "TEST_MODE",
        "STAGING_ENV",
        "NETRA_BACKEND_URL",
        "AUTH_SERVICE_URL",
        "WEBSOCKET_URL"
    ]

    for var in env_vars:
        value = os.environ.get(var, "NOT SET")
        print(f"{var}: {value}")

if __name__ == "__main__":
    main()