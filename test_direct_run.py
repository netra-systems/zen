#!/usr/bin/env python3
"""Test running the app directly without uvicorn lifespan parameter."""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Set environment variables
os.environ['BACKEND_PORT'] = '8003'

print("Starting uvicorn without lifespan parameter...")
import uvicorn

try:
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=False,
        log_level="info"
        # Note: No lifespan parameter here
    )
except RecursionError as e:
    print(f"RecursionError: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()