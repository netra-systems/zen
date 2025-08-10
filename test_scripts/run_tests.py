#!/usr/bin/env python
"""Test runner script with proper environment setup"""

import os
import sys
import asyncio

# Set testing environment
os.environ["TESTING"] = "1"
os.environ["REDIS_HOST"] = "localhost"
os.environ["CLICKHOUSE_HOST"] = "localhost"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

# Add project to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Configure asyncio for Windows
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def main():
    import pytest
    
    # Run pytest with appropriate options
    args = [
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "--asyncio-mode=auto",  # Auto async mode
        "-p", "no:warnings",  # Disable warnings
        "--disable-warnings",
        "tests/",  # Test directory
    ]
    
    # Add any command line arguments
    if len(sys.argv) > 1:
        args.extend(sys.argv[1:])
    
    # Run tests
    exit_code = pytest.main(args)
    sys.exit(exit_code)

if __name__ == "__main__":
    main()