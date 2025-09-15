import sys
import os
from pathlib import Path

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).resolve().parent

"""
Error Propagation E2E Test Suite.

This package contains focused test modules for validating error propagation:
- Auth service failure handling
- Database error recovery
- Network failure simulation
- Error correlation tracking
- User-friendly error messages

All tests maintain <300 lines and <8 lines per test function.
"""
