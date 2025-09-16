"""
Application shutdown management module.
Handles cleanup of database connections, services, and resources.
"""
import asyncio
import logging

from fastapi import FastAPI

from shared.logging.unified_logging_ssot import get_logger
from netra_backend.app.redis_manager import redis_manager
from netra_backend.app.utils.multiprocessing_cleanup import cleanup_multiprocessing
from netra_backend.app.services.background_task_manager import background_task_manager


def shutdown_cleanup(logger: logging.Logger) -> None:
    """Initialize shutdown process."""
    logger.info("Application shutdown initiated...")
    cleanup_multiprocessing()


async def _stop_performance_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Stop performance monitoring service."""
    if hasattr(app.state, 'performance_monitor'):
        try:
            await app.state.performance_monitor.stop_monitoring()
            logger.info("Performance monitoring stopped")
        except asyncio.CancelledError:
            logger.info("Performance monitoring stop cancelled during shutdown")
            raise

async def _stop_performance_manager(app: FastAPI, logger: logging.Logger) -> None:
    """Stop performance optimization manager."""
    if hasattr(app.state, 'performance_manager'):
        try:
            await app.state.performance_manager.shutdown()
            logger.info("Performance optimization manager stopped")
        except asyncio.CancelledError:
            logger.info("Performance manager stop cancelled during shutdown")
            raise

async def _stop_database_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Stop database monitoring task."""
    if hasattr(app.state, 'monitoring_task'):
        try:
            await _stop_monitoring_task(app, logger)
        except asyncio.CancelledError:
            logger.info("Database monitoring stop cancelled during shutdown")
            raise

async def stop_monitoring(app: FastAPI, logger: logging.Logger) -> None:
    """Stop comprehensive monitoring and optimization gracefully."""
    try:
        await _stop_performance_monitoring(app, logger)
        await _stop_performance_manager(app, logger)
        await _stop_database_monitoring(app, logger)
    except asyncio.CancelledError:
        logger.info("Monitoring shutdown cancelled - this is expected during application shutdown")
        # Re-raise to allow proper cancellation propagation
        raise
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
        # This is expected when cancelling monitoring tasks during shutdown
        central_logger.get_logger(__name__).info("Monitoring task cancelled successfully during shutdown")
        pass


async def close_database_connections() -> None:
    """Close Redis connection."""
    try:
        await redis_manager.shutdown()
    except asyncio.CancelledError:
        central_logger.get_logger(__name__).info("Redis disconnection cancelled during shutdown")
        # Re-raise to allow proper cancellation propagation if needed
        raise


async def cleanup_resources(app: FastAPI) -> None:
    """Shutdown all application services."""
    logger = central_logger.get_logger(__name__)
    await asyncio.sleep(0.1)
    
    # Shutdown background task manager with timeout
    try:
        if hasattr(app.state, 'background_task_manager') and app.state.background_task_manager is not None:
            await asyncio.wait_for(app.state.background_task_manager.shutdown(), timeout=5.0)
        else:
            logger.info("Background task manager not initialized, skipping shutdown")
    except asyncio.CancelledError:
        logger.info("Background task manager shutdown cancelled during application shutdown")
        # Continue cleanup despite cancellation
    except asyncio.TimeoutError:
        logger.warning("Background task manager shutdown timed out after 5 seconds")
    except (AttributeError, Exception) as e:
        logger.warning(f"Background task manager shutdown error: {e}")
    
    # Shutdown agent supervisor with timeout  
    try:
        if hasattr(app.state, 'agent_supervisor') and app.state.agent_supervisor is not None:
            await asyncio.wait_for(app.state.agent_supervisor.shutdown(), timeout=5.0)
        else:
            logger.info("Agent supervisor not initialized, skipping shutdown")
    except asyncio.CancelledError:
        logger.info("Agent supervisor shutdown cancelled during application shutdown")
        # Continue cleanup despite cancellation
    except asyncio.TimeoutError:
        logger.warning("Agent supervisor shutdown timed out after 5 seconds")
    except (AttributeError, Exception) as e:
        logger.warning(f"Agent supervisor shutdown error: {e}")
    
    # WebSocket manager shutdown is handled per-context now with factory pattern
    # No global websocket_manager to shutdown - each connection handles its own cleanup
    logger.info("WebSocket connections handled by factory pattern - individual cleanup via context")


async def _shutdown_infrastructure_resilience(app: FastAPI, logger: logging.Logger) -> None:
    """Shutdown infrastructure resilience monitoring and circuit breakers."""
    try:
        logger.info("Shutting down infrastructure resilience components...")

        # Stop infrastructure resilience monitoring
        if hasattr(app.state, 'resilience_manager'):
            try:
                from netra_backend.app.services.infrastructure_resilience import shutdown_infrastructure_resilience
                await shutdown_infrastructure_resilience()
                logger.info("Infrastructure resilience monitoring stopped")
            except Exception as e:
                logger.error(f"Error stopping infrastructure resilience monitoring: {e}")

        # Reset circuit breakers to closed state for clean shutdown
        if hasattr(app.state, 'circuit_breakers'):
            try:
                for name, circuit_breaker in app.state.circuit_breakers.items():
                    circuit_breaker.reset()
                logger.info("Circuit breakers reset for clean shutdown")
            except Exception as e:
                logger.error(f"Error resetting circuit breakers: {e}")

        # Clear circuit breaker manager
        if hasattr(app.state, 'circuit_breaker_manager'):
            try:
                app.state.circuit_breaker_manager.reset_all()
                logger.info("Circuit breaker manager reset")
            except Exception as e:
                logger.error(f"Error resetting circuit breaker manager: {e}")

        logger.info("Infrastructure resilience shutdown complete")

    except Exception as e:
        logger.error(f"Error during infrastructure resilience shutdown: {e}")


async def finalize_shutdown() -> None:
    """Finalize shutdown process."""
    try:
        await central_logger.shutdown()
    except asyncio.CancelledError:
        # Logger shutdown cancelled - this is expected during forced shutdown
        # Don't re-raise here as it's the final step
        pass


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
    except asyncio.CancelledError:
        logger.info("Background task manager shutdown cancelled - continuing with remaining cleanup")
        # Continue with the rest of the shutdown sequence
    except Exception as e:
        logger.error(f"Error shutting down background task manager: {e}")
    
    # Continue shutdown sequence even if individual components are cancelled
    try:
        await stop_monitoring(app, logger)
    except asyncio.CancelledError:
        logger.info("Monitoring shutdown cancelled - continuing with infrastructure resilience cleanup")

    # Shutdown infrastructure resilience monitoring
    try:
        await _shutdown_infrastructure_resilience(app, logger)
    except asyncio.CancelledError:
        logger.info("Infrastructure resilience shutdown cancelled - continuing with resource cleanup")
    
    try:
        await cleanup_resources(app)
    except asyncio.CancelledError:
        logger.info("Resource cleanup cancelled - continuing with database connections")
    
    try:
        await close_database_connections()
    except asyncio.CancelledError:
        logger.info("Database connection cleanup cancelled - continuing with finalization")
    
    try:
        await finalize_shutdown()
    except asyncio.CancelledError:
        logger.info("Shutdown finalization cancelled")
    
    logger.info("Application shutdown complete.")