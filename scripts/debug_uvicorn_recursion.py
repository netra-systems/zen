#!/usr/bin/env python3
"""Debug script for reproducing uvicorn recursion errors.

This script was moved from tests/ to scripts/ to prevent pytest from
discovering it during test collection, which was causing port binding conflicts.

Usage: python scripts/debug_uvicorn_recursion.py"""

import os
import sys
from pathlib import Path

import uvicorn

# Add project root to path (parent of scripts directory)

# Set environment variables
os.environ['BACKEND_PORT'] = '8001'

print("Starting uvicorn directly...")
try:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        lifespan="on",
        log_level="debug"
    )
except RecursionError as e:
    print(f"RecursionError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()