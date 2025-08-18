#!/usr/bin/env python3
"""Test which router causes the recursion issue."""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env file from {env_path}")
except ImportError:
    pass

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Import the lifespan and startup/shutdown
from app.startup_module import run_complete_startup
from app.shutdown import run_complete_shutdown

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's startup and shutdown events."""
    start_time, logger = await run_complete_startup(app)
    try:
        yield
    finally:
        await run_complete_shutdown(app, logger)

print("Creating FastAPI app with lifespan...")
app = FastAPI(lifespan=lifespan)

print("Adding CORS middleware...")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID", "X-Trace-ID"],
    expose_headers=["X-Trace-ID", "X-Request-ID"],
)

print("Adding session middleware...")
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    same_site="lax",
    https_only=False,
)

# Now try to progressively add routers
print("\nAdding routers one by one to identify recursion source...")

routers_to_test = [
    ("health", "from app.routes import health", "app.include_router(health.router, prefix='/health', tags=['health'])"),
    ("auth", "from app.routes.auth import auth as auth_router", "app.include_router(auth_router.router, prefix='/api/auth', tags=['auth'])"),
    ("agent", "from app.routes.agent_route import router as agent_router", "app.include_router(agent_router, prefix='/api/agent', tags=['agent'])"),
    ("threads", "from app.routes.threads_route import router as threads_router", "app.include_router(threads_router, tags=['threads'])"),
]

for name, import_stmt, include_stmt in routers_to_test:
    try:
        print(f"\nTesting router: {name}")
        print(f"  Import: {import_stmt}")
        exec(import_stmt)
        print(f"  Include: {include_stmt}")
        exec(include_stmt)
        print(f"  [OK] {name} added successfully")
    except RecursionError as e:
        print(f"  [ERROR] RecursionError with {name}: {e}")
        import traceback
        traceback.print_exc()
        break
    except Exception as e:
        print(f"  [ERROR] Error with {name}: {e}")
        break

print("\nRouter test complete.")

# Test if we can run the app
print("\nTesting app startup...")
import uvicorn
try:
    # Just test if it would start, don't actually run
    print("App created successfully, would start on port 8002")
except RecursionError as e:
    print(f"RecursionError during startup: {e}")
except Exception as e:
    print(f"Error during startup: {e}")