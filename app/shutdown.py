"""
Application shutdown management module.
Handles cleanup of database connections, services, and resources.
"""
import asyncio
import logging
from fastapi import FastAPI

from app.logging_config import central_logger
from app.redis_manager import redis_manager
from app.utils.multiprocessing_cleanup import cleanup_multiprocessing
from app.ws_manager import manager as websocket_manager


def shutdown_cleanup(logger: logging.Logger) -> None:
    """Initialize shutdown process."""
    logger.info("Application shutdown initiated...")
    cleanup_multiprocessing()


async def stop_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Stop database monitoring gracefully."""
    if hasattr(app.state, 'monitoring_task'):
        try:
            await _stop_monitoring_task(app, logger)
        except Exception as e:
            logger.error(f"Error stopping database monitoring: {e}")


async def _stop_monitoring_task(app: FastAPI, logger: logging.Logger) -> None:
    """Stop monitoring task and wait for completion."""
    from app.services.database.connection_monitor import stop_connection_monitoring
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
    await app.state.background_task_manager.shutdown()
    await app.state.agent_supervisor.shutdown()
    await websocket_manager.shutdown()


async def finalize_shutdown() -> None:
    """Finalize shutdown process."""
    await central_logger.shutdown()


async def run_complete_shutdown(app: FastAPI, logger: logging.Logger) -> None:
    """Run complete shutdown sequence."""
    shutdown_cleanup(logger)
    await stop_monitoring(app, logger)
    await cleanup_resources(app)
    await close_database_connections()
    await finalize_shutdown()
    logger.info("Application shutdown complete.")