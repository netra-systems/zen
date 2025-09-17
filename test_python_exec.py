#!/usr/bin/env python
"""Simple script to test Python executable and basic imports."""

import sys
import os
from pathlib import Path

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Project root: {Path(__file__).parent.absolute()}")

# Test basic imports
try:
    import pytest
    print("✅ pytest imported successfully")
except ImportError as e:
    print(f"❌ pytest import failed: {e}")

try:
    import asyncio
    print("✅ asyncio imported successfully")
except ImportError as e:
    print(f"❌ asyncio import failed: {e}")

# Test project imports
sys.path.insert(0, str(Path(__file__).parent.absolute()))
try:
    from test_framework.ssot.base_test_case import SSotAsyncTestCase
    print("✅ SSotAsyncTestCase imported successfully")
except ImportError as e:
    print(f"❌ SSotAsyncTestCase import failed: {e}")

print("\nPython environment test complete.")