"""
Application shutdown management module.
Handles cleanup of database connections, services, and resources.
"""
import asyncio
import logging

from fastapi import FastAPI

from netra_backend.app.logging_config import central_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.ws_manager import manager as websocket_manager
from netra_backend.app.utils.multiprocessing_cleanup import cleanup_multiprocessing
from netra_backend.app.services.background_task_manager import background_task_manager


def shutdown_cleanup(logger: logging.Logger) -> None:
    """Initialize shutdown process."""
    logger.info("Application shutdown initiated...")
    cleanup_multiprocessing()


async def _stop_performance_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Stop performance monitoring service."""
    if hasattr(app.state, 'performance_monitor'):
        await app.state.performance_monitor.stop_monitoring()
        logger.info("Performance monitoring stopped")

async def _stop_performance_manager(app: FastAPI, logger: logging.Logger) -> None:
    """Stop performance optimization manager."""
    if hasattr(app.state, 'performance_manager'):
        await app.state.performance_manager.shutdown()
        logger.info("Performance optimization manager stopped")

async def _stop_database_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Stop database monitoring task."""
    if hasattr(app.state, 'monitoring_task'):
        await _stop_monitoring_task(app, logger)

async def stop_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Stop comprehensive monitoring and optimization gracefully."""
    try:
        await _stop_performance_monitoring(app, logger)
        await _stop_performance_manager(app, logger)
        await _stop_database_monitoring(app, logger)
    except Exception as e:
        logger.error(f"Error stopping monitoring and optimizations: {e}")


async def _stop_monitoring_task(app: FastAPI, logger: logging.Logger) -> None:
    """Stop monitoring task and wait for completion."""
    from netra_backend.app.services.database.connection_monitor import (
        stop_connection_monitoring,
    )
    stop_connection_monitoring()
    app.state.monitoring_task.cancel()
    await _wait_for_monitoring_shutdown(app.state.monitoring_task)
    logger.info("Database monitoring stopped")


async def _wait_for_monitoring_shutdown(task: asyncio.Task) -> None:
    """Wait for monitoring task to shutdown."""
    try:
        await task
    except asyncio.CancelledError:
        pass


async def close_database_connections() -> None:
    """Close Redis connection."""
    await redis_manager.disconnect()


async def cleanup_resources(app: FastAPI) -> None:
    """Shutdown all application services."""
    await asyncio.sleep(0.1)
    
    # Shutdown background task manager with timeout
    try:
        await asyncio.wait_for(app.state.background_task_manager.shutdown(), timeout=5.0)
    except (asyncio.TimeoutError, AttributeError, Exception) as e:
        logger.warning(f"Background task manager shutdown timeout/error: {e}")
    
    # Shutdown agent supervisor with timeout  
    try:
        await asyncio.wait_for(app.state.agent_supervisor.shutdown(), timeout=5.0)
    except (asyncio.TimeoutError, AttributeError, Exception) as e:
        logger.warning(f"Agent supervisor shutdown timeout/error: {e}")
    
    # Shutdown WebSocket manager with timeout to prevent blocking
    try:
        await asyncio.wait_for(websocket_manager.shutdown(), timeout=3.0)
        logger.info("WebSocket manager shutdown completed")
    except asyncio.TimeoutError:
        logger.warning("WebSocket manager shutdown timed out - forcing cleanup")
    except Exception as e:
        logger.warning(f"WebSocket manager shutdown error: {e}")


async def finalize_shutdown() -> None:
    """Finalize shutdown process."""
    await central_logger.shutdown()


async def run_complete_shutdown(app: FastAPI, logger: logging.Logger) -> None:
    """Run complete shutdown sequence."""
    shutdown_cleanup(logger)
    
    # FIX: Shutdown background task manager to prevent hanging tasks
    try:
        if hasattr(app.state, 'background_task_manager'):
            logger.info("Shutting down background task manager...")
            await app.state.background_task_manager.shutdown()
            logger.info("Background task manager shutdown complete")
        else:
            # Fallback to global instance
            logger.info("Shutting down global background task manager...")
            await background_task_manager.shutdown()
            logger.info("Global background task manager shutdown complete")
    except Exception as e:
        logger.error(f"Error shutting down background task manager: {e}")
    
    await stop_monitoring(app, logger)
    await cleanup_resources(app)
    await close_database_connections()
    await finalize_shutdown()
    logger.info("Application shutdown complete.")