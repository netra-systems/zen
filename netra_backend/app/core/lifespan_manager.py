"""
Application lifespan management module.
Manages FastAPI application startup and shutdown lifecycle.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

import asyncio

from netra_backend.app.shutdown import run_complete_shutdown
# CRITICAL FIX: Use deterministic startup to prevent agent_service AttributeError
# The regular startup_module has graceful mode which allows degraded startup
from netra_backend.app.smd import (
    run_deterministic_startup as run_complete_startup,
    DeterministicStartupError
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages the application's startup and shutdown events.
    
    Uses asyncio.shield to prevent async generator corruption during shutdown.
    Ensures single yield path to prevent "already running" errors.
    """
    import asyncio
    
    start_time = None
    logger = None
    startup_success = False
    yielded = False
    
    try:
        # BYPASS STARTUP FOR TESTING - Check environment variable for bypass
        from shared.isolated_environment import get_env
        env = get_env()
        if env.get("BYPASS_FULL_STARTUP", "").lower() == "true":
            import time
            import logging
            start_time = time.time()
            logger = logging.getLogger(__name__)
            logger.warning("BYPASSING FULL STARTUP FOR TESTING - MINIMAL INITIALIZATION ONLY")
            app.state.startup_successful = True
            app.state.database_available = False
            app.state.redis_available = False
            app.state.startup_bypassed = True
            startup_success = True
        else:
            # CRITICAL FIX: Wrap startup in try-catch to prevent generator corruption
            start_time, logger = await run_complete_startup(app)
            startup_success = True
        
        # Set a flag that startup completed successfully
        app.state.startup_successful = True
        
        # CRITICAL FIX: Ensure single yield to prevent generator corruption
        yielded = True
        yield
        
    except asyncio.CancelledError:
        # CRITICAL FIX: Handle task cancellation gracefully
        if logger:
            logger.warning("Lifespan cancelled during startup")
        
        # Set degraded state but still yield to prevent generator corruption
        app.state.startup_successful = False
        app.state.startup_error = "Startup cancelled"
        
        if not yielded:
            yielded = True
            yield
        
        # Re-raise to properly handle cancellation
        raise
        
    except (Exception, DeterministicStartupError) as startup_error:
        # CRITICAL FIX: With deterministic startup, we MUST fail fast on critical errors
        if logger is None:
            # Initialize basic logger if startup failed before logger creation
            import logging
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.INFO)
        
        # Check if this is a critical deterministic startup failure
        if isinstance(startup_error, DeterministicStartupError):
            # CRITICAL: Deterministic startup failures MUST halt the application
            logger.critical(f"DETERMINISTIC STARTUP FAILURE: {startup_error}")
            logger.critical("Application cannot start without critical services")
            
            # Issue #1278 FIX: Exit with code 3 for container health checks
            import sys
            logger.critical("Exiting with code 3 to signal startup failure")
            sys.exit(3)
        
        # For non-critical errors, log but continue (backward compatibility)
        logger.error(f"Startup failed in lifespan manager: {startup_error}")
        app.state.startup_successful = False
        app.state.startup_error = str(startup_error)
        
        # Only allow degraded startup for non-critical errors
        # CRITICAL FIX: Ensure single yield even on startup failure
        if not yielded:
            yielded = True
            yield
        
    finally:
        # CRITICAL FIX: Use asyncio.shield to protect cleanup operations from cancellation
        # This prevents "already running" errors during shutdown
        try:
            if logger is not None:
                await asyncio.shield(run_complete_shutdown(app, logger))
            elif startup_success:
                # If we had successful startup but lost logger, create minimal logger for shutdown
                import logging
                fallback_logger = logging.getLogger(__name__)
                await asyncio.shield(run_complete_shutdown(app, fallback_logger))
        except asyncio.CancelledError:
            # If shutdown gets cancelled, log but don't propagate to prevent generator corruption
            if logger:
                logger.warning("Shutdown cancelled, resources may not be fully cleaned up")
        except Exception as shutdown_error:
            if logger:
                logger.error(f"Shutdown error: {shutdown_error}")
            else:
                print(f"Final shutdown error: {shutdown_error}")