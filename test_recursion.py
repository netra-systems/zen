#!/usr/bin/env python3
"""Test script to reproduce the recursion error."""

import sys
import asyncio
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Test if the lifespan issue is reproducible
@asynccontextmanager
async def test_lifespan(app: FastAPI):
    """Test lifespan handler."""
    print("Starting test lifespan...")
    yield
    print("Ending test lifespan...")

# Create a minimal FastAPI app
app = FastAPI(lifespan=test_lifespan)

# Test importing the actual app
try:
    print("Importing app.main...")
    from app.main import app as real_app
    print("Successfully imported app.main")
    
    # Check lifespan handlers
    print(f"Real app lifespan: {real_app.router.lifespan_context}")
    
    # Check for multiple lifespan contexts
    if hasattr(real_app, 'router'):
        router = real_app.router
        print(f"Router type: {type(router)}")
        if hasattr(router, 'routes'):
            print(f"Number of routes: {len(router.routes)}")
            
except RecursionError as e:
    print(f"RecursionError during import: {e}")
    traceback.print_exc()
except Exception as e:
    print(f"Error during import: {e}")
    traceback.print_exc()

print("\nTest complete.")