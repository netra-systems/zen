#!/usr/bin/env python3
"""
Minimal backend startup script for Issue #1338 debugging.
This bypasses complex initialization to get basic service running.
"""

import uvicorn
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set minimal environment variables
os.environ['ENVIRONMENT'] = 'development'
os.environ['HOST'] = '0.0.0.0'
os.environ['PORT'] = '8000'
os.environ['SERVICE_SECRET'] = 'xNp9hKjT5mQ8w2fE7vR4yU3iO6aS1gL9cB0zZ8tN6wX2eR4vY7uI0pQ3s9dF5gH8'
os.environ['SECRET_KEY'] = '0B298LDq0ky1fxdtNpXuhEDr3wjJiTIF'
os.environ['JWT_SECRET_KEY'] = 'rsWwwvq8X6mCSuNv-TMXHDCfb96Xc-Dbay9MZy6EDCU'
os.environ['SERVICE_ID'] = 'netra-backend'
os.environ['AUTH_SERVICE_URL'] = 'http://localhost:8001'

if __name__ == "__main__":
    print("Starting minimal backend service on port 8000...")

    # Import the app after setting environment
    try:
        from netra_backend.app.main import app
        print("Successfully imported backend app")

        # Start uvicorn server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except Exception as e:
        print(f"Failed to start backend: {e}")
        import traceback
        traceback.print_exc()