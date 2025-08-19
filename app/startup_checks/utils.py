"""
Startup Check Utils

Utility functions for startup check execution and reporting.
Maintains 8-line function limit and focused functionality.
"""

from typing import Dict, Any
from fastapi import FastAPI
from app.logging_config import central_logger as logger
from .checker import StartupChecker


async def run_startup_checks(app: FastAPI) -> Dict[str, Any]:
    """Run all startup checks with improved error handling and reporting"""
    if _should_skip_startup_checks():
        return _create_skipped_result()
    return await _perform_startup_checks(app)

async def _perform_startup_checks(app: FastAPI) -> Dict[str, Any]:
    """Perform actual startup checks and handle results"""
    results = await _execute_startup_checks(app)
    _handle_startup_results(results)
    return results


def _log_startup_results(results: Dict[str, Any]) -> None:
    """Log startup check results summary"""
    logger.info(f"Startup checks completed in {results['duration_ms']:.0f}ms")
    logger.info(f"Results: {results['passed']}/{results['total_checks']} passed")


def _log_critical_failures(results: Dict[str, Any]) -> None:
    """Log critical startup failures"""
    logger.error("Critical startup checks failed:")
    for failure in results['failures']:
        if failure.critical:
            logger.error(f"  - CRITICAL FAILURE: {failure.name}: {failure.message}")
            if hasattr(failure, 'duration_ms') and failure.duration_ms:
                logger.error(f"    Duration: {failure.duration_ms:.2f}ms")


def _log_non_critical_failures(results: Dict[str, Any]) -> None:
    """Log non-critical startup failures"""
    logger.warning("Non-critical startup checks failed:")
    for failure in results['failures']:
        if not failure.critical:
            logger.warning(f"  - {failure.name}: {failure.message}")


def _should_skip_startup_checks() -> bool:
    """Check if startup checks should be skipped"""
    import os
    return os.getenv("SKIP_STARTUP_CHECKS", "").lower() in ("true", "1", "yes")


def _create_skipped_result() -> Dict[str, Any]:
    """Create result for skipped startup checks"""
    logger.info("Startup checks skipped (SKIP_STARTUP_CHECKS=true)")
    return {
        "success": True, "total_checks": 0, "passed": 0, "failed_critical": 0,
        "failed_non_critical": 0, "duration_ms": 0, "results": [], "failures": []
    }


async def _execute_startup_checks(app: FastAPI) -> Dict[str, Any]:
    """Execute startup checks and return results"""
    checker = StartupChecker(app)
    return await checker.run_all_checks()


def _handle_startup_results(results: Dict[str, Any]) -> None:
    """Handle startup check results and log appropriately"""
    _log_startup_results(results)
    if results['failed_critical'] > 0:
        _handle_critical_failures(results)
    if results['failed_non_critical'] > 0:
        _log_non_critical_failures(results)


def _handle_critical_failures(results: Dict[str, Any]) -> None:
    """Handle critical startup failures"""
    _log_critical_failures(results)
    raise RuntimeError(f"Startup failed: {results['failed_critical']} critical checks failed")
