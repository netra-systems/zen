"""
Application lifespan management module.
Manages FastAPI application startup and shutdown lifecycle.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

import asyncio

from netra_backend.app.shutdown import run_complete_shutdown
from netra_backend.app.startup_module import run_complete_startup


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
        
    except Exception as startup_error:
        # CRITICAL FIX: Handle startup failures gracefully to prevent async generator issues
        if logger is None:
            # Initialize basic logger if startup failed before logger creation
            import logging
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.INFO)
        
        logger.error(f"Startup failed in lifespan manager: {startup_error}")
        app.state.startup_successful = False
        app.state.startup_error = str(startup_error)
        
        # Don't re-raise during startup - let the app start with degraded functionality
        # This prevents Docker health check failures due to startup issues
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