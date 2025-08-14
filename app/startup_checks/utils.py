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
    checker = StartupChecker(app)
    results = await checker.run_all_checks()
    
    _log_startup_results(results)
    
    if results['failed_critical'] > 0:
        _log_critical_failures(results)
        raise RuntimeError(f"Startup failed: {results['failed_critical']} critical checks failed")
    
    if results['failed_non_critical'] > 0:
        _log_non_critical_failures(results)
    
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
            logger.error(f"  - {failure.name}: {failure.message}")


def _log_non_critical_failures(results: Dict[str, Any]) -> None:
    """Log non-critical startup failures"""
    logger.warning("Non-critical startup checks failed:")
    for failure in results['failures']:
        if not failure.critical:
            logger.warning(f"  - {failure.name}: {failure.message}")
