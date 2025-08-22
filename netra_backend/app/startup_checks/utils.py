"""
Startup Check Utils

Utility functions for startup check execution and reporting.
Maintains 25-line function limit and focused functionality.
"""

from typing import Any, Dict

from fastapi import FastAPI

from netra_backend.app.core.configuration import unified_config_manager
from netra_backend.app.logging_config import central_logger as logger
from netra_backend.app.startup_checks.checker import StartupChecker


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
    config = unified_config_manager.get_config()
    skip_value = getattr(config, 'skip_startup_checks', '')
    return str(skip_value).lower() in ("true", "1", "yes")


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
    
    # In staging, treat ALL failures as critical
    config = unified_config_manager.get_config()
    is_staging = config.environment.lower() == "staging" or (hasattr(config, 'k_service') and config.k_service)
    
    if results['failed_critical'] > 0:
        _handle_critical_failures(results)
    elif is_staging and results['failed_non_critical'] > 0:
        # In staging, non-critical failures become critical
        logger.critical("Staging environment: Treating non-critical failures as critical")
        _handle_critical_failures(results)
    elif results['failed_non_critical'] > 0:
        _log_non_critical_failures(results)


def _handle_critical_failures(results: Dict[str, Any]) -> None:
    """Handle critical startup failures"""
    _log_critical_failures(results)
    
    # Collect all failure details for better observability
    failure_details = []
    for failure in results['failures']:
        if failure.critical or _is_staging_environment():
            failure_details.append(f"{failure.name}: {failure.message}")
    
    # Raise detailed error with all failure information
    error_msg = f"Startup failed: {len(failure_details)} critical checks failed\n" + "\n".join(failure_details)
    raise RuntimeError(error_msg)


def _is_staging_environment() -> bool:
    """Check if running in staging environment"""
    config = unified_config_manager.get_config()
    return config.environment.lower() == "staging" or (hasattr(config, 'k_service') and config.k_service)
