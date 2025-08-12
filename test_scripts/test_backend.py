#!/usr/bin/env python3
"""Test backend launch to debug multiprocessing issues."""

import os
import sys
import multiprocessing

# Set multiprocessing start method early
if sys.platform == "darwin":
    multiprocessing.set_start_method('spawn', force=True)

# Disable multiprocessing semaphore tracker warnings
import warnings
warnings.filterwarnings("ignore", message="resource_tracker")

# Set environment variables
os.environ["DEV_MODE_DISABLE_LLM"] = "true"
os.environ["DEV_MODE_DISABLE_REDIS"] = "true"
os.environ["DEV_MODE_DISABLE_CLICKHOUSE"] = "true"

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        loop="asyncio",
        log_level="info"
    )