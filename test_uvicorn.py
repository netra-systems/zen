#!/usr/bin/env python3
"""Test running uvicorn directly to reproduce the recursion error."""

import sys
import uvicorn
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

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